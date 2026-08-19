import os
import re
import time
import json
import logging
import threading
import requests
from typing import Any, Dict, List, Optional, Tuple
from dotenv import load_dotenv

load_dotenv("/home/ubuntu/Rasa/.env")
logger = logging.getLogger(__name__)

# User-facing fail-safe message when all free LLM providers/routes fail
ALL_PROVIDERS_FAILED_MSG = "«Free AI service is temporarily unavailable. Please try again shortly.»"


def clean_llm_output(text: Optional[str]) -> str:
    """Strips <think> tags and reasoning blocks from model output."""
    if not text:
        return ""
    if "</think>" in text:
        text = text.split("</think>")[-1].strip()
    elif "<think>" in text:
        text = re.sub(r"<think>.*", "", text, flags=re.DOTALL).strip()
    return text.strip()


class ProviderHealth:
    """
    Tracks provider and model health status, per-model and per-provider cooldown,
    circuit breaker, and consecutive error counts.
    """
    def __init__(self):
        self._lock = threading.Lock()
        self._health: Dict[str, Dict[str, Any]] = {}

    def is_healthy(self, name: str) -> bool:
        with self._lock:
            state = self._health.get(name)
            if not state:
                return True
            until = state.get("unhealthy_until", 0)
            if time.time() < until:
                return False
            return True

    def record_success(self, name: str, model: Optional[str] = None):
        with self._lock:
            self._health[name] = {"unhealthy_until": 0, "consecutive_429": 0, "consecutive_errors": 0}
            if model:
                self._health[f"{name}:{model}"] = {"unhealthy_until": 0, "consecutive_429": 0, "consecutive_errors": 0}

    def record_429(self, name: str, model: Optional[str] = None, cooldown_seconds: int = 60):
        with self._lock:
            target_key = f"{name}:{model}" if model else name
            state = self._health.setdefault(target_key, {"unhealthy_until": 0, "consecutive_429": 0, "consecutive_errors": 0})
            state["consecutive_429"] += 1
            multiplier = min(2 ** (state["consecutive_429"] - 1), 8)
            duration = cooldown_seconds * multiplier
            state["unhealthy_until"] = time.time() + duration
            logger.warning(f"⚠️ [CircuitBreaker] `{target_key}` cooldown for {duration}s due to HTTP 429.")

    def record_auth_failure(self, name: str):
        """Disables provider for a long duration (1 hour) on 401/403 invalid key."""
        with self._lock:
            state = self._health.setdefault(name, {"unhealthy_until": 0, "consecutive_429": 0, "consecutive_errors": 0})
            state["unhealthy_until"] = time.time() + 3600
            logger.error(f"❌ [CircuitBreaker] Provider `{name}` marked UNAVAILABLE for 1hr due to Auth failure (401/403).")

    def record_error(self, name: str, model: Optional[str] = None, cooldown_seconds: int = 30):
        with self._lock:
            target_key = f"{name}:{model}" if model else name
            state = self._health.setdefault(target_key, {"unhealthy_until": 0, "consecutive_429": 0, "consecutive_errors": 0})
            state["consecutive_errors"] += 1
            if state["consecutive_errors"] >= 3:
                state["unhealthy_until"] = time.time() + cooldown_seconds
                logger.warning(f"⚠️ [CircuitBreaker] `{target_key}` temporary cooldown for {cooldown_seconds}s after repeated errors.")


health_tracker = ProviderHealth()


class RoutePricing:
    """Pricing and modality metadata for an LLM route."""
    def __init__(
        self,
        provider: str,
        model_id: str,
        api_route: str,
        price_per_1m_prompt: float,
        price_per_1m_completion: float,
        is_explicitly_free: bool,
        requires_paid_credits: bool,
        has_usage_limits: bool,
        supports_vision: bool,
        notes: str = ""
    ):
        self.provider = provider
        self.model_id = model_id
        self.api_route = api_route
        self.price_per_1m_prompt = price_per_1m_prompt
        self.price_per_1m_completion = price_per_1m_completion
        self.is_explicitly_free = is_explicitly_free
        self.requires_paid_credits = requires_paid_credits
        self.has_usage_limits = has_usage_limits
        self.supports_vision = supports_vision
        self.notes = notes

    @property
    def is_zero_cost(self) -> bool:
        return (
            self.is_explicitly_free
            and not self.requires_paid_credits
            and self.price_per_1m_prompt == 0.0
            and self.price_per_1m_completion == 0.0
        )


class FreeRouteRegistry:
    """
    Maintains verified provider metadata and pricing catalog.
    Enforces strict zero-cost validation when FREE_ONLY=true.
    """

    # Catalog of known routes and their pricing classification
    KNOWN_ROUTES: Dict[str, RoutePricing] = {
        # OpenRouter Verified :free routes ($0.00 / prompt, $0.00 / completion)
        "openrouter/google/gemma-4-26b-a4b-it:free": RoutePricing(
            provider="OpenRouter",
            model_id="google/gemma-4-26b-a4b-it:free",
            api_route="https://openrouter.ai/api/v1/chat/completions",
            price_per_1m_prompt=0.0,
            price_per_1m_completion=0.0,
            is_explicitly_free=True,
            requires_paid_credits=False,
            has_usage_limits=True,
            supports_vision=True,
            notes="Zero-cost multimodal route on OpenRouter"
        ),
        "openrouter/nvidia/nemotron-3-ultra-550b-a55b:free": RoutePricing(
            provider="OpenRouter",
            model_id="nvidia/nemotron-3-ultra-550b-a55b:free",
            api_route="https://openrouter.ai/api/v1/chat/completions",
            price_per_1m_prompt=0.0,
            price_per_1m_completion=0.0,
            is_explicitly_free=True,
            requires_paid_credits=False,
            has_usage_limits=True,
            supports_vision=False,
            notes="Zero-cost large text route on OpenRouter"
        ),
        "openrouter/dots-studio/dots-3-note-preview:free": RoutePricing(
            provider="OpenRouter",
            model_id="dots-studio/dots-3-note-preview:free",
            api_route="https://openrouter.ai/api/v1/chat/completions",
            price_per_1m_prompt=0.0,
            price_per_1m_completion=0.0,
            is_explicitly_free=True,
            requires_paid_credits=False,
            has_usage_limits=True,
            supports_vision=True,
            notes="Zero-cost multimodal route on OpenRouter"
        ),
        "openrouter/openrouter/free": RoutePricing(
            provider="OpenRouter",
            model_id="openrouter/free",
            api_route="https://openrouter.ai/api/v1/chat/completions",
            price_per_1m_prompt=0.0,
            price_per_1m_completion=0.0,
            is_explicitly_free=True,
            requires_paid_credits=False,
            has_usage_limits=True,
            supports_vision=True,
            notes="Zero-cost auto-router for free endpoints"
        ),
        "openrouter/z-ai/glm-5.2:free": RoutePricing(
            provider="OpenRouter",
            model_id="z-ai/glm-5.2:free",
            api_route="https://openrouter.ai/api/v1/chat/completions",
            price_per_1m_prompt=0.0,
            price_per_1m_completion=0.0,
            is_explicitly_free=True,
            requires_paid_credits=False,
            has_usage_limits=True,
            supports_vision=False,
            notes="Zero-cost text route on OpenRouter"
        ),
        "openrouter/google/gemma-4-31b-it:free": RoutePricing(
            provider="OpenRouter",
            model_id="google/gemma-4-31b-it:free",
            api_route="https://openrouter.ai/api/v1/chat/completions",
            price_per_1m_prompt=0.0,
            price_per_1m_completion=0.0,
            is_explicitly_free=True,
            requires_paid_credits=False,
            has_usage_limits=True,
            supports_vision=True,
            notes="Zero-cost multimodal route on OpenRouter"
        ),

        # Groq Routes - Paid/Token-Metered API Platform
        "groq/openai/gpt-oss-20b": RoutePricing(
            provider="Groq",
            model_id="openai/gpt-oss-20b",
            api_route="https://api.groq.com/openai/v1/chat/completions",
            price_per_1m_prompt=0.10,
            price_per_1m_completion=0.20,
            is_explicitly_free=False,
            requires_paid_credits=True,
            has_usage_limits=True,
            supports_vision=False,
            notes="Groq metered token pricing"
        ),
        "groq/openai/gpt-oss-120b": RoutePricing(
            provider="Groq",
            model_id="openai/gpt-oss-120b",
            api_route="https://api.groq.com/openai/v1/chat/completions",
            price_per_1m_prompt=0.30,
            price_per_1m_completion=0.60,
            is_explicitly_free=False,
            requires_paid_credits=True,
            has_usage_limits=True,
            supports_vision=False,
            notes="Groq metered token pricing"
        ),
        "groq/qwen/qwen3.6-27b": RoutePricing(
            provider="Groq",
            model_id="qwen/qwen3.6-27b",
            api_route="https://api.groq.com/openai/v1/chat/completions",
            price_per_1m_prompt=0.15,
            price_per_1m_completion=0.30,
            is_explicitly_free=False,
            requires_paid_credits=True,
            has_usage_limits=True,
            supports_vision=False,
            notes="Groq metered token pricing"
        ),

        # NVIDIA NIM Routes - Credit/Evaluation Tier
        "nvidia/meta/llama-3.2-11b-vision-instruct": RoutePricing(
            provider="NVIDIA NIM",
            model_id="meta/llama-3.2-11b-vision-instruct",
            api_route="https://integrate.api.nvidia.com/v1/chat/completions",
            price_per_1m_prompt=0.20,
            price_per_1m_completion=0.40,
            is_explicitly_free=False,
            requires_paid_credits=True,
            has_usage_limits=True,
            supports_vision=True,
            notes="NVIDIA NIM credit-metered evaluation endpoint"
        ),
        "nvidia/z-ai/glm-5.2": RoutePricing(
            provider="NVIDIA NIM",
            model_id="z-ai/glm-5.2",
            api_route="https://integrate.api.nvidia.com/v1/chat/completions",
            price_per_1m_prompt=0.20,
            price_per_1m_completion=0.40,
            is_explicitly_free=False,
            requires_paid_credits=True,
            has_usage_limits=True,
            supports_vision=False,
            notes="NVIDIA NIM credit-metered endpoint"
        ),
    }

    @classmethod
    def normalize_provider(cls, provider: str) -> str:
        p = provider.strip().lower()
        if p.startswith("openrouter"):
            return "OpenRouter"
        elif p.startswith("groq"):
            return "Groq"
        elif p.startswith("nvidia"):
            return "NVIDIA"
        return provider.strip()

    @classmethod
    def lookup_route(cls, provider: str, model_id: str) -> Optional[RoutePricing]:
        norm_provider = cls.normalize_provider(provider)
        key = f"{norm_provider.lower()}/{model_id.lower()}"
        if key in cls.KNOWN_ROUTES:
            return cls.KNOWN_ROUTES[key]

        # Dynamic check for OpenRouter: any model with :free suffix or openrouter/free
        if norm_provider.lower() == "openrouter":
            if model_id.endswith(":free") or model_id == "openrouter/free":
                return RoutePricing(
                    provider="OpenRouter",
                    model_id=model_id,
                    api_route="https://openrouter.ai/api/v1/chat/completions",
                    price_per_1m_prompt=0.0,
                    price_per_1m_completion=0.0,
                    is_explicitly_free=True,
                    requires_paid_credits=False,
                    has_usage_limits=True,
                    supports_vision=True if ("gemma-4" in model_id or "dots" in model_id or "free" in model_id) else False,
                    notes="Dynamically validated OpenRouter free model"
                )
            else:
                # OpenRouter paid model without :free
                return RoutePricing(
                    provider="OpenRouter",
                    model_id=model_id,
                    api_route="https://openrouter.ai/api/v1/chat/completions",
                    price_per_1m_prompt=0.50,
                    price_per_1m_completion=1.50,
                    is_explicitly_free=False,
                    requires_paid_credits=True,
                    has_usage_limits=True,
                    supports_vision=False,
                    notes="Paid OpenRouter model"
                )

        return None

    @classmethod
    def validate_route(
        cls,
        provider: str,
        model_id: str,
        is_free_only: bool,
        is_vision: bool = False
    ) -> Tuple[bool, str]:
        """
        Validates whether a provider + model route is permitted.
        Returns (is_valid, reason).
        """
        norm_provider = cls.normalize_provider(provider)
        route_meta = cls.lookup_route(norm_provider, model_id)

        if not route_meta:
            reason = f"REJECTED: Unknown or unverified route `{provider}/{model_id}`"
            logger.warning(f"⛔ [RouteVerifier] {reason}")
            return False, reason

        if is_free_only and not route_meta.is_zero_cost:
            reason = (
                f"REJECTED: Paid/credit-metered route `{provider}/{model_id}` "
                f"(Price: ${route_meta.price_per_1m_prompt}/1M prompt, "
                f"${route_meta.price_per_1m_completion}/1M completion, "
                f"Requires credits: {route_meta.requires_paid_credits})"
            )
            logger.warning(f"⛔ [RouteVerifier] {reason}")
            return False, reason

        if is_vision and not route_meta.supports_vision:
            reason = f"REJECTED: Model `{provider}/{model_id}` does not support multimodal vision/image input"
            logger.warning(f"⛔ [RouteVerifier] {reason}")
            return False, reason

        return True, "ACCEPTED: Verified zero-cost free route"


class ContextManager:
    """
    Enforces maximum context size, trims conversation history,
    and compresses/resizes images before sending to LLM providers.
    Prevents HTTP 413 (Payload Too Large).
    """
    MAX_CHAR_BUDGET = 12000  # Truncate total text content to ~3000 tokens

    @classmethod
    def sanitize_messages(cls, messages: List[Dict[str, Any]], max_chars: int = MAX_CHAR_BUDGET) -> List[Dict[str, Any]]:
        if not messages:
            return []

        sanitized = []
        for msg in messages:
            msg_copy = dict(msg)
            content = msg_copy.get("content")
            if isinstance(content, str) and len(content) > 4000:
                msg_copy["content"] = content[:3800] + "\n...[Truncated for length]..."
            sanitized.append(msg_copy)

        total_len = sum(len(str(m.get("content", ""))) for m in sanitized)
        if total_len > max_chars and len(sanitized) > 2:
            system_msg = sanitized[0] if sanitized[0].get("role") == "system" else None
            recent_msgs = sanitized[1:] if system_msg else sanitized
            while total_len > max_chars and len(recent_msgs) > 1:
                removed = recent_msgs.pop(0)
                total_len -= len(str(removed.get("content", "")))
            sanitized = ([system_msg] if system_msg else []) + recent_msgs

        return sanitized

    @classmethod
    def compress_image_data_uri(cls, data_uri: str, max_dimension: int = 800) -> str:
        """Resizes Base64 image payload if oversized to prevent 413 payload errors."""
        if not data_uri or not data_uri.startswith("data:image"):
            return data_uri

        try:
            import base64
            from io import BytesIO
            from PIL import Image

            header, b64data = data_uri.split(",", 1)
            img_bytes = base64.b64decode(b64data)

            if len(img_bytes) < 400000:  # Skip compression if already < 400KB
                return data_uri

            with Image.open(BytesIO(img_bytes)) as img:
                img.thumbnail((max_dimension, max_dimension), Image.Resampling.LANCZOS)
                out_buffer = BytesIO()
                fmt = img.format if img.format in ["PNG", "JPEG", "WEBP"] else "JPEG"
                img.save(out_buffer, format=fmt, quality=75, optimize=True)
                compressed_b64 = base64.b64encode(out_buffer.getvalue()).decode("utf-8")
                mime = f"data:image/{fmt.lower()};base64"
                return f"{mime},{compressed_b64}"
        except Exception as e:
            logger.debug(f"Image compression skipped or failed: {e}")
            return data_uri


class LLMProviderManager:
    """
    Centralized Free-Only Multi-Provider LLM Fallback Service for Alya.
    Strictly enforces ZERO paid API routes when FREE_ONLY=true.
    """

    @classmethod
    def is_free_only_mode(cls) -> bool:
        val = os.getenv("FREE_ONLY", "true").strip().lower()
        return val in ["true", "1", "yes"]

    @classmethod
    def get_text_fallback_chain(cls) -> List[Dict[str, Any]]:
        """
        Constructs the free-only text provider & model list.
        Validates every candidate route against FreeRouteRegistry.
        Rejects all paid/credit-metered routes when FREE_ONLY=true.
        """
        is_free_only = cls.is_free_only_mode()
        openrouter_key = os.getenv("OPENROUTER_API_KEY", "")
        groq_key = os.getenv("GROQ_API_KEY", "")

        chain = []

        # 1. Groq Check (Paid / token-metered platform)
        if groq_key and not "placeholder" in groq_key.lower():
            groq_primary = os.getenv("GROQ_MODEL", os.getenv("TEXT_PRIMARY_MODEL", "openai/gpt-oss-20b"))
            groq_candidates = [groq_primary, "openai/gpt-oss-120b", "qwen/qwen3.6-27b"]
            valid_groq_models = []
            for m in groq_candidates:
                allowed, reason = FreeRouteRegistry.validate_route("Groq", m, is_free_only=is_free_only, is_vision=False)
                if allowed:
                    valid_groq_models.append(m)
                else:
                    logger.info(f"🚫 [ChainBuilder] Skipped Groq route `{m}`: {reason}")

            if valid_groq_models:
                chain.append({
                    "name": "Groq",
                    "url": "https://api.groq.com/openai/v1/chat/completions",
                    "key": groq_key,
                    "models": valid_groq_models,
                    "headers": lambda k: {"Authorization": f"Bearer {k}"}
                })

        # 2. OpenRouter Free Routes (100% Zero-Cost :free models)
        if openrouter_key and not "placeholder" in openrouter_key.lower():
            or_primary = os.getenv("TEXT_PRIMARY_MODEL", os.getenv("OPENROUTER_PRIMARY_MODEL", "google/gemma-4-26b-a4b-it:free"))
            fallback_raw = os.getenv(
                "TEXT_FALLBACK_MODELS",
                os.getenv("OPENROUTER_FALLBACK_MODELS", "nvidia/nemotron-3-ultra-550b-a55b:free, dots-studio/dots-3-note-preview:free, openrouter/free")
            )
            or_candidates = [or_primary] + [m.strip() for m in fallback_raw.split(",") if m.strip()]

            # Deduplicate while preserving fallback priority order
            seen = set()
            ordered_candidates = []
            for m in or_candidates:
                if m not in seen:
                    seen.add(m)
                    ordered_candidates.append(m)

            # Ensure openrouter/free auto-router is present at the end of the chain
            if "openrouter/free" not in ordered_candidates:
                ordered_candidates.append("openrouter/free")

            valid_or_models = []
            for m in ordered_candidates:
                allowed, reason = FreeRouteRegistry.validate_route("OpenRouter", m, is_free_only=is_free_only, is_vision=False)
                if allowed:
                    valid_or_models.append(m)
                else:
                    logger.info(f"🚫 [ChainBuilder] Skipped OpenRouter route `{m}`: {reason}")

            if valid_or_models:
                chain.append({
                    "name": "OpenRouter",
                    "url": "https://openrouter.ai/api/v1/chat/completions",
                    "key": openrouter_key,
                    "models": valid_or_models,
                    "headers": lambda k: {
                        "Authorization": f"Bearer {k}",
                        "HTTP-Referer": "https://rasaagent.duckdns.org",
                        "X-Title": "Alya AI Bot"
                    }
                })

        return chain

    @classmethod
    def get_vision_fallback_chain(cls) -> List[Dict[str, Any]]:
        """
        Constructs the free-only vision provider & model list.
        Validates every candidate route against FreeRouteRegistry.
        Rejects all paid/credit-metered and non-vision routes when FREE_ONLY=true.
        """
        is_free_only = cls.is_free_only_mode()
        openrouter_key = os.getenv("OPENROUTER_API_KEY", "")
        nvidia_key = os.getenv("NVIDIA_NIM_API_KEY", "")

        chain = []

        # 1. OpenRouter Multimodal Free Routes
        if openrouter_key and not "placeholder" in openrouter_key.lower():
            vis_primary = os.getenv("VISION_PRIMARY_MODEL", "google/gemma-4-26b-a4b-it:free")
            vis_fallbacks_raw = os.getenv("VISION_FALLBACK_MODELS", "dots-studio/dots-3-note-preview:free, openrouter/free")
            vis_candidates = [vis_primary] + [m.strip() for m in vis_fallbacks_raw.split(",") if m.strip()]

            seen = set()
            ordered_candidates = []
            for m in vis_candidates:
                if m not in seen:
                    seen.add(m)
                    ordered_candidates.append(m)

            if "openrouter/free" not in ordered_candidates:
                ordered_candidates.append("openrouter/free")

            valid_vis_models = []
            for m in ordered_candidates:
                allowed, reason = FreeRouteRegistry.validate_route("OpenRouter", m, is_free_only=is_free_only, is_vision=True)
                if allowed:
                    valid_vis_models.append(m)
                else:
                    logger.info(f"🚫 [ChainBuilder] Skipped vision route `{m}`: {reason}")

            if valid_vis_models:
                chain.append({
                    "name": "OpenRouter Vision",
                    "url": "https://openrouter.ai/api/v1/chat/completions",
                    "key": openrouter_key,
                    "models": valid_vis_models,
                    "headers": lambda k: {
                        "Authorization": f"Bearer {k}",
                        "HTTP-Referer": "https://rasaagent.duckdns.org",
                        "X-Title": "Alya AI Bot"
                    }
                })

        # 2. NVIDIA NIM Check (Credit-metered evaluation endpoint)
        if nvidia_key and not "placeholder" in nvidia_key.lower():
            nvidia_model = os.getenv("NVIDIA_NIM_MODEL", "meta/llama-3.2-11b-vision-instruct")
            allowed, reason = FreeRouteRegistry.validate_route("NVIDIA", nvidia_model, is_free_only=is_free_only, is_vision=True)
            if allowed:
                chain.append({
                    "name": "NVIDIA NIM Vision",
                    "url": "https://integrate.api.nvidia.com/v1/chat/completions",
                    "key": nvidia_key,
                    "models": [nvidia_model],
                    "headers": lambda k: {"Authorization": f"Bearer {k}"}
                })
            else:
                logger.info(f"🚫 [ChainBuilder] Skipped NVIDIA NIM route `{nvidia_model}`: {reason}")

        return chain

    @classmethod
    def call_chat_completion(
        cls,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        temperature: float = 0.3,
        max_tokens: int = 1200,
        timeout: int = 10
    ) -> Tuple[Optional[str], Optional[List[Dict[str, Any]]], str]:
        """
        Executes text chat completion with automatic failover across verified free routes,
        smart retries, circuit breaker tracking, and context trimming.
        """
        for msg in messages:
            c = msg.get("content")
            if isinstance(c, list):
                for item in c:
                    if isinstance(item, dict) and item.get("type") == "image_url":
                        logger.error("❌ Text completion called with image content! Redirecting to Vision.")
                        return ALL_PROVIDERS_FAILED_MSG, None, "InvalidCall"

        sanitized_msgs = ContextManager.sanitize_messages(messages)
        providers = cls.get_text_fallback_chain()

        last_error = ""

        for p in providers:
            p_name = p["name"]
            p_key = p["key"]

            if not health_tracker.is_healthy(p_name):
                logger.info(f"⏭️ Skipping `{p_name}`: Temporarily marked unhealthy (cooldown).")
                continue

            for p_model in p["models"]:
                if not health_tracker.is_healthy(p_name):
                    logger.info(f"⏭️ Breaking model loop for `{p_name}`: Provider marked unhealthy.")
                    break

                if not health_tracker.is_healthy(f"{p_name}:{p_model}"):
                    logger.info(f"⏭️ Skipping model `{p_model}` on `{p_name}`: Model in 429 cooldown.")
                    continue

                # Hard Safety Rule check before dispatching request
                allowed, reason = FreeRouteRegistry.validate_route(
                    p_name, p_model, is_free_only=cls.is_free_only_mode(), is_vision=False
                )
                if not allowed:
                    logger.error(f"🛑 [HardSafetyGuard] BLOCKED request to `{p_name}/{p_model}`: {reason}")
                    continue

                logger.info(f"🔄 [LLM Chain] Attempting verified free route: {p_name} ({p_model})...")

                payload = {
                    "model": p_model,
                    "messages": sanitized_msgs,
                    "temperature": temperature,
                    "max_tokens": max_tokens
                }
                if tools:
                    payload["tools"] = tools
                    payload["tool_choice"] = "auto"

                headers = {**p["headers"](p_key), "Content-Type": "application/json"}

                for attempt in range(2):
                    try:
                        resp = requests.post(p["url"], json=payload, headers=headers, timeout=timeout)
                        status = resp.status_code

                        if status == 200:
                            res_json = resp.json()
                            choices = res_json.get("choices", [])
                            if choices:
                                msg = choices[0].get("message", {})
                                raw_content = msg.get("content")
                                cleaned_content = clean_llm_output(raw_content)
                                tool_calls = msg.get("tool_calls")

                                health_tracker.record_success(p_name, p_model)
                                logger.info(f"✅ [LLM Chain] Success via verified free route {p_name} ({p_model})!")
                                return cleaned_content, tool_calls, f"{p_name} ({p_model})"
                            else:
                                last_error = f"{p_name} ({p_model}) empty choices"

                        elif status == 429:
                            last_error = f"{p_name} ({p_model}) HTTP 429 Rate Limit"
                            health_tracker.record_429(p_name, p_model)
                            break

                        elif status == 413:
                            last_error = f"{p_name} ({p_model}) HTTP 413 Request Too Large"
                            if attempt == 0:
                                logger.warning(f"⚠️ HTTP 413 received. Aggressively trimming context and retrying...")
                                sanitized_msgs = ContextManager.sanitize_messages(sanitized_msgs, max_chars=4000)
                                payload["messages"] = sanitized_msgs
                                payload["max_tokens"] = min(max_tokens, 500)
                                continue
                            break

                        elif status in [401, 403]:
                            last_error = f"{p_name} ({p_model}) Auth Error {status}"
                            health_tracker.record_auth_failure(p_name)
                            break

                        elif status == 400:
                            last_error = f"{p_name} ({p_model}) HTTP 400: {resp.text[:100]}"
                            if tools and "tool" in resp.text.lower() and attempt == 0:
                                payload.pop("tools", None)
                                payload.pop("tool_choice", None)
                                continue
                            break

                        elif status >= 500:
                            last_error = f"{p_name} ({p_model}) HTTP {status}"
                            if attempt == 0:
                                time.sleep(0.5)
                                continue
                            break

                        else:
                            last_error = f"{p_name} ({p_model}) HTTP {status}: {resp.text[:100]}"
                            break

                    except requests.exceptions.Timeout:
                        last_error = f"{p_name} ({p_model}) timed out after {timeout}s"
                        health_tracker.record_error(p_name, p_model)
                        break

                    except Exception as e:
                        last_error = f"{p_name} ({p_model}) exception: {str(e)}"
                        health_tracker.record_error(p_name, p_model)
                        break

        logger.error(f"❌ [LLM Chain] All verified free LLM routes failed. Last error: {last_error}")
        return ALL_PROVIDERS_FAILED_MSG, None, "None"

    @classmethod
    def call_vision_completion(
        cls,
        image_path_or_url: str,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.1,
        max_tokens: int = 1000,
        timeout: int = 15
    ) -> Tuple[Optional[str], str]:
        """
        Executes vision-capable multimodal LLM completion with verified free-only providers,
        automatic payload compression, and smart fallbacks.
        """
        import base64

        data_uri = None
        clean_target = image_path_or_url.strip()

        if clean_target.startswith(("http://", "https://")):
            try:
                os.makedirs("/tmp/alya_vision", exist_ok=True)
                local_file = f"/tmp/alya_vision/img_{int(time.time())}.png"
                r = requests.get(clean_target, timeout=10)
                if r.status_code == 200:
                    with open(local_file, "wb") as f_out:
                        f_out.write(r.content)
                    clean_target = local_file
                else:
                    data_uri = clean_target
            except Exception as e_dl:
                logger.warning(f"Failed to download image URL for vision: {e_dl}")
                data_uri = clean_target

        if not data_uri and os.path.exists(clean_target):
            try:
                ext = "png" if clean_target.lower().endswith(".png") else "jpeg"
                if clean_target.lower().endswith(".webp"):
                    ext = "webp"
                with open(clean_target, "rb") as f_img:
                    b64 = base64.b64encode(f_img.read()).decode("utf-8")
                data_uri = f"data:image/{ext};base64,{b64}"
            except Exception as e_b64:
                logger.error(f"Failed to encode image to base64: {e_b64}")
                return ALL_PROVIDERS_FAILED_MSG, "Error"

        if not data_uri:
            return ALL_PROVIDERS_FAILED_MSG, "InvalidImage"

        data_uri = ContextManager.compress_image_data_uri(data_uri)

        vision_providers = cls.get_vision_fallback_chain()
        last_error = ""

        for p in vision_providers:
            p_name = p["name"]
            p_key = p["key"]

            if not health_tracker.is_healthy(p_name):
                logger.info(f"⏭️ Skipping vision provider `{p_name}`: In cooldown state.")
                continue

            for p_model in p["models"]:
                if not health_tracker.is_healthy(f"{p_name}:{p_model}"):
                    logger.info(f"⏭️ Skipping vision model `{p_model}` on `{p_name}`: In cooldown.")
                    continue

                allowed, reason = FreeRouteRegistry.validate_route(
                    p_name, p_model, is_free_only=cls.is_free_only_mode(), is_vision=True
                )
                if not allowed:
                    logger.error(f"🛑 [HardSafetyGuard] BLOCKED vision request to `{p_name}/{p_model}`: {reason}")
                    continue

                logger.info(f"🔄 [Vision Chain] Attempting verified free vision route: {p_name} ({p_model})...")

                messages: List[Dict[str, Any]] = []
                if system_prompt:
                    messages.append({"role": "system", "content": system_prompt[:1000]})
                messages.append({
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt[:2000]},
                        {"type": "image_url", "image_url": {"url": data_uri}}
                    ]
                })

                payload = {
                    "model": p_model,
                    "messages": messages,
                    "temperature": temperature,
                    "max_tokens": max_tokens
                }

                headers = {**p["headers"](p_key), "Content-Type": "application/json"}

                try:
                    resp = requests.post(p["url"], json=payload, headers=headers, timeout=timeout)
                    status = resp.status_code

                    if status == 200:
                        res_json = resp.json()
                        choices = res_json.get("choices", [])
                        if choices:
                            raw_content = choices[0].get("message", {}).get("content", "")
                            cleaned = clean_llm_output(raw_content)
                            if cleaned:
                                health_tracker.record_success(p_name, p_model)
                                logger.info(f"✅ [Vision Chain] Success via verified free route {p_name} ({p_model})!")
                                return cleaned, f"{p_name} ({p_model})"
                    elif status == 429:
                        health_tracker.record_429(p_name, p_model)
                        last_error = f"{p_name} ({p_model}) HTTP 429 Rate Limit"
                    elif status in [401, 403]:
                        health_tracker.record_auth_failure(p_name)
                        last_error = f"{p_name} ({p_model}) Auth Error {status}"
                    else:
                        last_error = f"{p_name} ({p_model}) HTTP {status}: {resp.text[:100]}"
                except requests.exceptions.Timeout:
                    last_error = f"{p_name} ({p_model}) timed out"
                    health_tracker.record_error(p_name, p_model)
                except Exception as e:
                    last_error = f"{p_name} ({p_model}) exception: {str(e)}"
                    health_tracker.record_error(p_name, p_model)

        logger.error(f"❌ [Vision Chain] All verified free vision routes failed. Last error: {last_error}")
        return ALL_PROVIDERS_FAILED_MSG, "None"
