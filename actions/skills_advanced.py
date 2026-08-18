import os
import re
import time
import json
import socket
import ssl
import logging
import urllib.parse
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional, Tuple

import requests
from dotenv import load_dotenv
import qrcode
from PIL import Image, ImageDraw, ImageFont, ImageEnhance
import pytesseract

from . import llm_provider

load_dotenv("/home/ubuntu/Rasa/.env")
logger = logging.getLogger(__name__)

IST = timezone(timedelta(hours=5, minutes=30), name="IST")


# ===========================================================================
# 1. ⚡ UPI Payment QR Code Generator
# ===========================================================================

def generate_upi_qr(
    vpa: str,
    amount: Optional[float] = None,
    payee_name: Optional[str] = None,
    note: Optional[str] = None
) -> Dict[str, Any]:
    """
    Generates a high-resolution, branded UPI scan-and-pay QR code image.
    Supports GPay, PhonePe, Paytm, BHIM, Cred, Amazon Pay, etc.
    """
    clean_vpa = vpa.strip()
    if not clean_vpa or "@" not in clean_vpa:
        return {
            "handled": True,
            "text": (
                "⚠️ **Invalid UPI ID (VPA)**\n\n"
                "Please provide a valid UPI ID (e.g. `username@okhdfcbank`, `9876543210@paytm`).\n\n"
                "**Usage:** `/upi <vpa_id> [amount] [name] [note]`\n"
                "**Example:** `/upi user@okaxis 499 \"Md Faijal\" \"Dinner\"`"
            )
        }

    p_name = payee_name.strip() if payee_name else "Merchant/Payee"
    p_note = note.strip() if note else "Payment via Alya Assistant"

    # Build NPCI Standard UPI Intent URI
    params = {
        "pa": clean_vpa,
        "pn": p_name,
        "cu": "INR",
        "tn": p_note
    }
    if amount is not None and amount > 0:
        params["am"] = f"{amount:.2f}"

    upi_uri = "upi://pay?" + urllib.parse.urlencode(params)

    # Generate Styled QR Code
    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=10,
        border=4,
    )
    qr.add_data(upi_uri)
    qr.make(fit=True)

    img = qr.make_image(fill_color="#1e1b4b", back_color="#ffffff").convert("RGB")
    
    # Save Image
    os.makedirs("/tmp/alya_assets", exist_ok=True)
    out_path = f"/tmp/alya_assets/upi_qr_{int(time.time() * 1000)}.png"
    img.save(out_path, format="PNG")

    amount_str = f"₹{amount:,.2f}" if (amount and amount > 0) else "Open Amount (User Entered)"
    msg = (
        "⚡ **UPI Payment QR Code Generated** ⚡\n\n"
        f"• **Payee UPI ID:** `{clean_vpa}`\n"
        f"• **Payee Name:** {p_name}\n"
        f"• **Amount:** **{amount_str}**\n"
        f"• **Payment Note:** _{p_note}_\n\n"
        "📲 *Scan with Google Pay, PhonePe, Paytm, BHIM, or any UPI App to pay instantly.*"
    )

    return {
        "handled": True,
        "text": msg,
        "file_path": out_path,
        "file_type": "photo"
    }


# ===========================================================================
# 2. 🔍 Real-Time AI Web Search & Synthesis
# ===========================================================================

def search_live_web(query: str, max_results: int = 4) -> str:
    """
    Performs live web search using Tavily API (with DuckDuckGo fallback)
    and synthesizes an intelligent, structured response using LLM.
    """
    clean_query = query.strip()
    if not clean_query:
        return "Usage: `/search <topic or query>`\nExample: `/search latest ISRO mission updates 2026`"

    search_snippets: List[Dict[str, str]] = []
    tavily_key = os.getenv("TAVILY_API_KEY", "").strip()

    # 1. Try Tavily API
    if tavily_key and "placeholder" not in tavily_key.lower():
        try:
            url = "https://api.tavily.com/search"
            payload = {
                "api_key": tavily_key,
                "query": clean_query,
                "search_depth": "basic",
                "max_results": max_results,
                "include_answer": True
            }
            resp = requests.post(url, json=payload, timeout=8)
            if resp.status_code == 200:
                data = resp.json()
                for r in data.get("results", []):
                    search_snippets.append({
                        "title": r.get("title", "Web Result"),
                        "snippet": r.get("content", ""),
                        "url": r.get("url", "")
                    })
        except Exception as e:
            logger.warning(f"Tavily search exception: {e}")

    # 2. Fallback to DuckDuckGo Search if needed
    if not search_snippets:
        try:
            from duckduckgo_search import DDGS
            with DDGS() as ddgs:
                results = list(ddgs.text(clean_query, max_results=max_results))
                for r in results:
                    search_snippets.append({
                        "title": r.get("title", ""),
                        "snippet": r.get("body", ""),
                        "url": r.get("href", "")
                    })
        except Exception as e:
            logger.warning(f"DuckDuckGo search exception: {e}")

    if not search_snippets:
        return f"⚠️ Unable to fetch live web search results for `{clean_query}` right now. Please try again."

    # Format search context for LLM
    context_text = ""
    for i, s in enumerate(search_snippets, start=1):
        context_text += f"[{i}] {s['title']}\nSnippet: {s['snippet']}\nURL: {s['url']}\n\n"

    # LLM Synthesis
    prompt = (
        f"You are Alya, a brilliant AI researcher. A user asked the following web search query: '{clean_query}'.\n"
        f"Here are the live real-time search results from the internet:\n\n"
        f"{context_text}\n"
        f"Synthesize a clear, accurate, concise, and structured summary in crisp Markdown (use bullet points, bold key stats, and easy-to-read sections in Hinglish/English). Do not mention 'based on snippet 1'. Provide direct actionable information."
    )

    try:
        ans, _, _ = llm_provider.LLMProviderManager.call_chat_completion(
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
            max_tokens=700
        )
        ans = llm_provider.clean_llm_output(ans)
    except Exception as e:
        logger.error(f"LLM synthesis error: {e}")
        ans = "\n".join([f"• **{s['title']}**: {s['snippet'][:150]}..." for s in search_snippets[:3]])

    # Append Sources
    sources_md = "\n\n🔗 **Sources & References:**\n" + "\n".join(
        [f"• [{s['title']}]({s['url']})" for s in search_snippets if s.get("url")]
    )

    return f"🔍 **Live Web Search: `{clean_query}`**\n\n{ans}{sources_md}"


# ===========================================================================
# 3. 🎙️ Voice & Audio Transcriber (Groq Whisper API)
# ===========================================================================

def transcribe_audio(file_path_or_url: str, prompt: Optional[str] = None) -> str:
    """
    Transcribes audio / voice notes using Groq Whisper API (whisper-large-v3-turbo).
    Supports MP3, M4A, OGG, WAV, MP4, FLAC.
    """
    input_str = file_path_or_url.strip()
    if not input_str:
        return "Usage: `/transcribe <audio_url_or_path>`\nExample: `/transcribe https://example.com/recording.mp3` or send a voice note directly in chat!"

    target_file = input_str

    # If URL, download to temporary file
    if input_str.startswith(("http://", "https://")):
        try:
            os.makedirs("/tmp/alya_audio", exist_ok=True)
            ext = os.path.splitext(input_str.split("?")[0])[1] or ".mp3"
            target_file = f"/tmp/alya_audio/download_{int(time.time())}{ext}"
            resp = requests.get(input_str, timeout=20)
            if resp.status_code == 200:
                with open(target_file, "wb") as f:
                    f.write(resp.content)
            else:
                return f"❌ Failed to download audio from URL (HTTP {resp.status_code})."
        except Exception as e:
            return f"❌ Error downloading audio file: {str(e)}"

    if not os.path.exists(target_file):
        return f"⚠️ Audio file not found at `{target_file}`."

    groq_key = os.getenv("GROQ_API_KEY", "").strip()
    if not groq_key or "placeholder" in groq_key.lower():
        return "⚠️ Groq API key is not configured for Whisper transcription."

    try:
        from groq import Groq
        client = Groq(api_key=groq_key)

        file_size_mb = os.path.getsize(target_file) / (1024 * 1024)
        if file_size_mb > 25:
            return f"⚠️ Audio file is too large ({file_size_mb:.1f} MB). Groq Whisper max limit is 25 MB."

        with open(target_file, "rb") as audio_f:
            transcription = client.audio.transcriptions.create(
                file=(os.path.basename(target_file), audio_f),
                model="whisper-large-v3-turbo",
                response_format="verbose_json",
                language=None, # auto-detect
                temperature=0.0
            )

        text = getattr(transcription, "text", "") or transcription.get("text", "")
        detected_lang = getattr(transcription, "language", "auto")
        duration = getattr(transcription, "duration", 0)

        if not text:
            return "⚠️ No speech could be detected or transcribed in the provided audio."

        # Quick summary if transcript is long (> 80 words)
        words = text.split()
        summary_section = ""
        if len(words) > 80:
            try:
                sum_prompt = f"Summarize the following audio transcript in 3-4 bullet points in English/Hinglish:\n\n{text}"
                sum_text, _, _ = llm_provider.LLMProviderManager.call_chat_completion(
                    messages=[{"role": "user", "content": sum_prompt}],
                    temperature=0.2,
                    max_tokens=300
                )
                sum_text = llm_provider.clean_llm_output(sum_text)
                if sum_text:
                    summary_section = f"\n\n📌 **Key Highlights / Summary:**\n{sum_text}"
            except Exception:
                pass

        duration_str = f"{int(duration // 60)}m {int(duration % 60)}s" if duration else "N/A"

        return (
            "🎙️ **Audio Transcription Complete**\n\n"
            f"• **Detected Language:** `{str(detected_lang).upper()}`\n"
            f"• **Duration:** `{duration_str}`\n"
            f"• **Word Count:** `{len(words)} words`\n\n"
            "📝 **Verbatim Transcript:**\n"
            f"\"{text.strip()}\""
            f"{summary_section}"
        )

    except Exception as e:
        logger.error(f"Groq Whisper transcription error: {e}")
        return f"❌ Transcription failed: {str(e)}"


# ===========================================================================
# 4. 🏥 Medicine & Generic Salt Info / Interaction Checker
# ===========================================================================

def lookup_medicine_info(medicine_name: str) -> str:
    """
    Provides clinical pharmacology details, active salts, uses, warnings,
    side effects, and cost-effective generic alternatives in India.
    """
    med = medicine_name.strip()
    if not med:
        return "Usage: `/med <medicine_name>` or `/medicine <name>`\nExample: `/med Dolo 650` or `/med Augmentin 625`"

    prompt = (
        f"You are a clinical pharmacology reference assistant.\n"
        f"Provide a comprehensive, accurate guide for the medicine/salt: '{med}'.\n\n"
        f"Structure your response strictly with the following sections in clean Markdown:\n"
        f"1. 💊 **Active Salt & Drug Class** (e.g. Paracetamol 650mg, Analgesic/Antipyretic)\n"
        f"2. 🎯 **Primary Medical Uses** (What ailments/symptoms it treats)\n"
        f"3. 📋 **Dosage & Administration Tips** (e.g. with/without food, standard schedule)\n"
        f"4. ⚠️ **Critical Warnings & Contraindications** (Pregnancy, Liver/Kidney caution, Alcohol interaction)\n"
        f"5. 🤢 **Common Side Effects**\n"
        f"6. 💡 **Low-Cost Generic Substitutes in India** (Jan Aushadhi equivalents or common affordable brands)\n"
        f"7. 🩺 **Medical Disclaimer** (Strict note to consult a licensed physician/pharmacist)\n\n"
        f"Keep the output structured with bullet points and clear emojis."
    )

    try:
        guide, _, _ = llm_provider.LLMProviderManager.call_chat_completion(
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
            max_tokens=900
        )
        guide = llm_provider.clean_llm_output(guide)
        if guide:
            return f"🏥 **Medical Information: `{med}`**\n\n{guide}"
    except Exception as e:
        logger.error(f"Medicine lookup error: {e}")

    return f"⚠️ Unable to fetch medical details for `{med}` right now. Please verify spelling."


# ===========================================================================
# 5. 🔒 SSL Certificate & Domain WHOIS Inspector
# ===========================================================================

def inspect_ssl_certificate(domain: str) -> str:
    """
    Performs real-time TLS handshake to inspect SSL certificate validity,
    issuer authority, expiration dates, days remaining, cipher and TLS version.
    """
    clean_domain = domain.strip().replace("https://", "").replace("http://", "").split("/")[0].split(":")[0]
    if not clean_domain:
        return "Usage: `/ssl <domain>`\nExample: `/ssl google.com` or `/ssl github.com`"

    try:
        ctx = ssl.create_default_context()
        with socket.create_connection((clean_domain, 443), timeout=6) as sock:
            with ctx.wrap_socket(sock, server_hostname=clean_domain) as ssock:
                cert = ssock.getpeercert()
                tls_version = ssock.version()
                cipher = ssock.cipher()

        if not cert:
            return f"⚠️ No SSL certificate presented by `{clean_domain}`."

        # Extract Subject & Issuer
        subject_dict = dict(x[0] for x in cert.get("subject", []))
        issuer_dict = dict(x[0] for x in cert.get("issuer", []))

        common_name = subject_dict.get("commonName", clean_domain)
        issuer_org = issuer_dict.get("organizationName", issuer_dict.get("commonName", "Unknown CA"))
        issuer_cn = issuer_dict.get("commonName", "")

        # Dates & Expiry
        not_before_str = cert.get("notBefore", "")
        not_after_str = cert.get("notAfter", "")

        # Format: 'Sep 30 23:59:59 2026 GMT'
        expiry_dt = datetime.strptime(not_after_str, "%b %d %H:%M:%S %Y %Z").replace(tzinfo=timezone.utc)
        now_dt = datetime.now(timezone.utc)
        days_left = (expiry_dt - now_dt).days

        # SANs (Subject Alternative Names)
        sans = [v for k, v in cert.get("subjectAltName", []) if k == "DNS"]
        san_preview = ", ".join(sans[:4]) + (f" (+{len(sans)-4} more)" if len(sans) > 4 else "")

        if days_left > 30:
            status_badge = f"🟢 **VALID & SECURE** ({days_left} days remaining)"
        elif days_left > 0:
            status_badge = f"🟡 **EXPIRING SOON** ({days_left} days remaining)"
        else:
            status_badge = f"🔴 **EXPIRED** ({abs(days_left)} days ago)"

        return (
            f"🔒 **SSL Certificate Status for `{clean_domain}`**\n\n"
            f"• **Status:** {status_badge}\n"
            f"• **Common Name (CN):** `{common_name}`\n"
            f"• **Issuer CA:** `{issuer_org}` ({issuer_cn})\n"
            f"• **Issued On:** `{not_before_str}`\n"
            f"• **Expires On:** `{not_after_str}`\n"
            f"• **Protocol:** `{tls_version}`\n"
            f"• **Cipher Suite:** `{cipher[0] if cipher else 'N/A'}`\n"
            f"• **Alternative Names (SAN):** `{san_preview}`"
        )

    except socket.gaierror:
        return f"❌ Hostname resolution failed for `{clean_domain}`. Check the domain name."
    except socket.timeout:
        return f"⏱️ Connection timed out reaching `{clean_domain}:443`."
    except ssl.SSLCertVerificationError as e:
        return f"🔴 **SSL Certificate Invalid / Untrusted for `{clean_domain}`**\n\n• **Error:** `{e.verify_message}`"
    except Exception as e:
        return f"❌ SSL check failed for `{clean_domain}`: {str(e)}"


def inspect_domain_whois(domain: str) -> str:
    """
    Queries ICANN RDAP protocol to inspect domain registrar, creation,
    expiration, name servers, and registration status.
    """
    clean_domain = domain.strip().replace("https://", "").replace("http://", "").split("/")[0].split(":")[0]
    if not clean_domain:
        return "Usage: `/whois <domain>`\nExample: `/whois github.com` or `/whois openai.com`"

    try:
        url = f"https://rdap.org/domain/{clean_domain}"
        resp = requests.get(url, timeout=7, headers={"Accept": "application/json"})
        if resp.status_code != 200:
            return f"⚠️ RDAP WHOIS lookup returned HTTP {resp.status_code} for `{clean_domain}`."

        data = resp.json()
        domain_name = data.get("ldhName", clean_domain.upper())
        status_list = data.get("status", [])

        # Extract Events (Registration, Expiration, Last Changed)
        events = {e.get("eventAction"): e.get("eventDate") for e in data.get("events", [])}
        created = events.get("registration", "N/A")
        expires = events.get("expiration", "N/A")
        updated = events.get("last changed", events.get("last update of RDAP database", "N/A"))

        # Extract Registrar Name
        registrar = "Unknown Registrar"
        for entity in data.get("entities", []):
            if "registrar" in entity.get("roles", []):
                vcard = entity.get("vcardArray", [None, []])[1]
                for field in vcard:
                    if field[0] == "fn":
                        registrar = field[3]
                        break

        # Nameservers
        ns_list = [ns.get("ldhName") for ns in data.get("nameservers", []) if ns.get("ldhName")]
        ns_str = ", ".join(ns_list[:4]) if ns_list else "N/A"

        return (
            f"🌐 **WHOIS / RDAP Record for `{domain_name}`**\n\n"
            f"• **Registrar:** `{registrar}`\n"
            f"• **Created Date:** `{created}`\n"
            f"• **Expiry Date:** `{expires}`\n"
            f"• **Last Updated:** `{updated}`\n"
            f"• **Domain Status:** `{', '.join(status_list[:3]) if status_list else 'Active'}`\n"
            f"• **Nameservers:** `{ns_str}`"
        )

    except Exception as e:
        logger.warning(f"RDAP WHOIS error: {e}")
        return f"❌ WHOIS lookup failed for `{clean_domain}`: {str(e)}"


# ===========================================================================
# 6. 📸 OCR / Image-to-Text Extractor
# ===========================================================================

def extract_ocr_text(image_path_or_url: str) -> str:
    """
    Extracts text from images (receipts, handwritten notes, documents, photos)
    using Tesseract OCR Engine and AI cleaning.
    """
    input_str = image_path_or_url.strip()
    if not input_str:
        return "Usage: `/ocr <image_url_or_file>`\nExample: `/ocr https://example.com/receipt.png` or send a photo directly in chat!"

    target_file = input_str

    if input_str.startswith(("http://", "https://")):
        try:
            os.makedirs("/tmp/alya_ocr", exist_ok=True)
            target_file = f"/tmp/alya_ocr/img_{int(time.time())}.png"
            resp = requests.get(input_str, timeout=15)
            if resp.status_code == 200:
                with open(target_file, "wb") as f:
                    f.write(resp.content)
            else:
                return f"❌ Failed to download image from URL (HTTP {resp.status_code})."
        except Exception as e:
            return f"❌ Error downloading image: {str(e)}"

    if not os.path.exists(target_file):
        return f"⚠️ Image file not found at `{target_file}`."

    try:
        img = Image.open(target_file)
        # Preprocessing: convert to grayscale & enhance contrast
        gray = img.convert("L")
        enhancer = ImageEnhance.Contrast(gray)
        enhanced = enhancer.enhance(1.8)

        raw_text = pytesseract.image_to_string(enhanced)
        clean_text = raw_text.strip()

        if not clean_text or len(clean_text) < 3:
            # Try raw image without enhancement
            clean_text = pytesseract.image_to_string(img).strip()

        if not clean_text:
            return "⚠️ No readable text could be recognized in the image."

        # Polish and structure text with LLM if multiline
        if "\n" in clean_text or len(clean_text) > 50:
            prompt = (
                f"Below is raw OCR extracted text from an image. Clean up typos, fix formatting, and output the clean text in structured Markdown:\n\n"
                f"{clean_text}"
            )
            try:
                polished, _, _ = llm_provider.LLMProviderManager.call_chat_completion(
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.1,
                    max_tokens=600
                )
                polished = llm_provider.clean_llm_output(polished)
                if polished:
                    clean_text = polished
            except Exception:
                pass

        return f"📸 **OCR Extracted Text:**\n\n```text\n{clean_text}\n```"

    except Exception as e:
        logger.error(f"OCR processing error: {e}")
        return f"❌ OCR extraction failed: {str(e)}"
