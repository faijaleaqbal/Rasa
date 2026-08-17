import os
import re
import json
import logging
import requests
from typing import Any, Dict, List, Optional, Tuple
from dotenv import load_dotenv

load_dotenv("/home/ubuntu/Rasa/.env")
logger = logging.getLogger(__name__)


def clean_llm_output(text: Optional[str]) -> str:
    """Strips <think> tags and reasoning blocks from model output."""
    if not text:
        return ""
    if "</think>" in text:
        text = text.split("</think>")[-1].strip()
    elif "<think>" in text:
        text = re.sub(r"<think>.*", "", text, flags=re.DOTALL).strip()
    return text.strip()


class LLMProviderManager:
    """
    Unified Multi-Provider LLM Fallback Chain:
      1. Primary: Groq (Fastest Inference)
      2. Fallback 1: NVIDIA NIM (Enterprise GPU Cloud)
      3. Fallback 2: OpenRouter (Multi-Model Free Router)
    """

    @classmethod
    def call_chat_completion(
        cls,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        temperature: float = 0.3,
        max_tokens: int = 1500,
        timeout: int = 12
    ) -> Tuple[Optional[str], Optional[List[Dict[str, Any]]], str]:
        """
        Executes chat completion with automatic failover.
        Returns:
            (content_text, tool_calls_list, provider_name)
        """
        providers = [
            {
                "name": "Groq",
                "url": "https://api.groq.com/openai/v1/chat/completions",
                "key": os.getenv("GROQ_API_KEY", ""),
                "models": [os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile"), "qwen/qwen3.6-27b", "openai/gpt-oss-120b"],
                "headers": lambda k: {"Authorization": f"Bearer {k}"}
            },
            {
                "name": "NVIDIA NIM",
                "url": "https://integrate.api.nvidia.com/v1/chat/completions",
                "key": os.getenv("NVIDIA_NIM_API_KEY", ""),
                "models": [os.getenv("NVIDIA_NIM_MODEL", "z-ai/glm-5.2"), "meta/llama-3.3-70b-instruct"],
                "headers": lambda k: {"Authorization": f"Bearer {k}"}
            },
            {
                "name": "OpenRouter",
                "url": "https://openrouter.ai/api/v1/chat/completions",
                "key": os.getenv("OPENROUTER_API_KEY", ""),
                "models": [
                    os.getenv("OPENROUTER_MODEL", "nvidia/nemotron-3-ultra-550b-a55b:free"),
                    "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free"
                ],
                "headers": lambda k: {
                    "Authorization": f"Bearer {k}",
                    "HTTP-Referer": "https://rasaagent.duckdns.org",
                    "X-Title": "Alya AI Bot"
                }
            }
        ]

        last_error = ""

        for p in providers:
            p_name = p["name"]
            p_key = p["key"]

            if not p_key or "placeholder" in p_key.lower():
                logger.debug(f"Skipping LLM provider `{p_name}`: Key not configured.")
                continue

            for p_model in p["models"]:
                logger.info(f"🔄 [LLM Chain] Attempting: {p_name} (Model: {p_model})...")

                payload = {
                    "model": p_model,
                    "messages": messages,
                    "temperature": temperature,
                    "max_tokens": max_tokens
                }
                if tools:
                    payload["tools"] = tools
                    payload["tool_choice"] = "auto"

                try:
                    headers = {**p["headers"](p_key), "Content-Type": "application/json"}
                    resp = requests.post(
                        p["url"],
                        json=payload,
                        headers=headers,
                        timeout=timeout
                    )

                    if resp.status_code == 400 and tools and "tool" in resp.text.lower():
                        # Retry without tools if model doesn't support OpenAI tools format
                        payload_no_tools = dict(payload)
                        payload_no_tools.pop("tools", None)
                        payload_no_tools.pop("tool_choice", None)
                        resp = requests.post(p["url"], json=payload_no_tools, headers=headers, timeout=timeout)

                    if resp.status_code == 200:
                        res_json = resp.json()
                        choices = res_json.get("choices", [])
                        if choices:
                            msg = choices[0].get("message", {})
                            raw_content = msg.get("content")
                            cleaned_content = clean_llm_output(raw_content)
                            tool_calls = msg.get("tool_calls")

                            logger.info(f"✅ [LLM Chain] Success via {p_name} ({p_model})!")
                            return cleaned_content, tool_calls, f"{p_name} ({p_model})"
                        else:
                            last_error = f"{p_name} ({p_model}) returned empty choices list"
                            logger.warning(f"⚠️ [LLM Chain] {last_error}")
                    else:
                        last_error = f"{p_name} ({p_model}) HTTP {resp.status_code}: {resp.text[:120]}"
                        logger.warning(f"⚠️ [LLM Chain] {last_error}")

                except requests.exceptions.Timeout:
                    last_error = f"{p_name} ({p_model}) request timed out ({timeout}s)"
                    logger.warning(f"⚠️ [LLM Chain] Timeout: {last_error}")
                except Exception as e:
                    last_error = f"{p_name} ({p_model}) exception: {str(e)}"
                    logger.warning(f"⚠️ [LLM Chain] Error: {last_error}")

        logger.error(f"❌ [LLM Chain] All 3 LLM providers failed. Last error: {last_error}")
        return None, None, "None"
