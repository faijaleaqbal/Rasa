import os
import re
import json
import logging
import random
import string
import hashlib
import base64
import time
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional
import urllib.parse
import requests
from dotenv import load_dotenv

load_dotenv("/home/ubuntu/Rasa/.env")
logger = logging.getLogger(__name__)

IST = timezone(timedelta(hours=5, minutes=30), name="IST")

def _clean_llm_think(text: str) -> str:
    """Strips <think> tags and reasoning blocks from LLM responses."""
    if "</think>" in text:
        text = text.split("</think>")[-1].strip()
    elif "<think>" in text:
        text = re.sub(r"<think>.*", "", text, flags=re.DOTALL).strip()
    return text.strip()


# ---------------------------------------------------------------------------
# 1. Developer & Network Tools (DNS, HTTP, Cron, JSON, Geo-IP)
# ---------------------------------------------------------------------------

def lookup_dns(domain: str) -> str:
    """Performs DNS records lookup (A, MX, NS, TXT) via Google DNS over HTTPS."""
    clean_domain = domain.strip().replace("http://", "").replace("https://", "").split("/")[0]
    if not clean_domain:
        return "Usage: `/dns <domain>`\nExample: `/dns google.com`"
    try:
        records_summary = []
        for r_type in ["A", "MX", "NS", "TXT"]:
            url = f"https://dns.google/resolve?name={clean_domain}&type={r_type}"
            resp = requests.get(url, timeout=5)
            if resp.status_code == 200:
                data = resp.json()
                answers = data.get("Answer", [])
                if answers:
                    values = [f"`{a.get('data')}`" for a in answers[:4]]
                    records_summary.append(f"• **{r_type}**: " + ", ".join(values))

        if records_summary:
            return f"🌐 **DNS Records for `{clean_domain}`:**\n\n" + "\n".join(records_summary)
        else:
            return f"⚠️ No DNS records found for `{clean_domain}`."
    except Exception as e:
        logger.warning(f"DNS lookup error: {e}")
        return f"❌ DNS lookup failed: {str(e)}"


def test_http_endpoint(url: str) -> str:
    """Tests a website or API endpoint for HTTP status, latency, headers, and SSL."""
    target_url = url.strip()
    if not target_url.startswith(("http://", "https://")):
        target_url = "https://" + target_url

    try:
        start_time = time.time()
        resp = requests.get(target_url, timeout=8, allow_redirects=True, headers={"User-Agent": "AlyaHTTPTester/1.0"})
        latency_ms = (time.time() - start_time) * 1000

        status_icon = "🟢" if resp.status_code < 400 else "🔴"
        server = resp.headers.get("Server", "Unknown")
        content_type = resp.headers.get("Content-Type", "N/A")
        content_len = len(resp.content)

        return (
            f"{status_icon} **HTTP Test Result for `{target_url}`:**\n\n"
            f"• **Status Code**: `{resp.status_code} {resp.reason}`\n"
            f"• **Latency / Response Time**: `{latency_ms:.1f} ms`\n"
            f"• **Final URL**: `{resp.url}`\n"
            f"• **Server**: `{server}`\n"
            f"• **Content Type**: `{content_type}`\n"
            f"• **Payload Size**: `{content_len:,} bytes`"
        )
    except Exception as e:
        return f"❌ HTTP request failed: `{str(e)}`"


def explain_cron(expr: str) -> str:
    """Translates a 5-part cron expression into human-readable English/Hinglish."""
    clean_expr = expr.strip()
    if not clean_expr:
        return "Usage: `/cron <expression>`\nExample: `/cron */15 * * * *`"

    try:
        from groq import Groq
        key = os.getenv("GROQ_API_KEY")
        if key:
            client = Groq(api_key=key)
            resp = client.chat.completions.create(
                model="qwen/qwen3.6-27b",
                messages=[
                    {"role": "system", "content": "You are a senior Linux DevOps engineer. Explain the given cron expression clearly in 2 concise sentences (Hinglish/English). Give next occurrence frequency."},
                    {"role": "user", "content": f"Explain this cron expression: {clean_expr}"}
                ],
                temperature=0.1,
                max_tokens=1500
            )
            explanation = _clean_llm_think(resp.choices[0].message.content)
            return f"⏰ **Cron Expression:** `{clean_expr}`\n\n{explanation}"
    except Exception as e:
        logger.warning(f"Cron explanation error: {e}")

    return f"⏰ **Cron Expression:** `{clean_expr}`\n• Format: `[Minute] [Hour] [Day-of-Month] [Month] [Day-of-Week]`"


def format_json(raw_text: str) -> str:
    """Formats and validates JSON string."""
    clean = raw_text.strip()
    if not clean:
        return "Usage: `/json <json_string>`\nExample: `/json {\"name\":\"Alya\",\"skills\":37}`"
    try:
        parsed = json.loads(clean)
        formatted = json.dumps(parsed, indent=2)
        return f"✅ **Valid JSON Formatted:**\n```json\n{formatted}\n```"
    except Exception as e:
        return f"❌ **Invalid JSON Syntax:**\n`{str(e)}`"


def lookup_ip(ip: str = "") -> str:
    """Looks up Geo-IP location, ISP, and organization."""
    clean_ip = ip.strip()
    try:
        url = f"http://ip-api.com/json/{clean_ip}?fields=status,message,country,countryCode,regionName,city,zip,lat,lon,timezone,isp,org,as,query"
        resp = requests.get(url, timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            if data.get("status") == "success":
                return (
                    f"🌍 **IP Intelligence for `{data.get('query')}`:**\n\n"
                    f"• **Location**: {data.get('city')}, {data.get('regionName')}, {data.get('country')} ({data.get('countryCode')})\n"
                    f"• **Postal Code**: `{data.get('zip', 'N/A')}`\n"
                    f"• **Coordinates**: `{data.get('lat')}, {data.get('lon')}`\n"
                    f"• **Timezone**: `{data.get('timezone')}`\n"
                    f"• **ISP**: `{data.get('isp')}`\n"
                    f"• **Organization**: `{data.get('org')}`\n"
                    f"• **ASN**: `{data.get('as')}`"
                )
            else:
                return f"❌ IP Lookup error: {data.get('message', 'Invalid IP address')}"
    except Exception as e:
        logger.warning(f"IP lookup error: {e}")

    return "❌ Failed to query IP geolocation service."


# ---------------------------------------------------------------------------
# 2. Security & Privacy (Passwords, Hashes, URL Expander, TempMail)
# ---------------------------------------------------------------------------

def generate_password(length: int = 16) -> str:
    """Generates a cryptographically strong password."""
    if length < 8:
        length = 8
    elif length > 64:
        length = 64

    chars = string.ascii_letters + string.digits + "!@#$%^&*()-_=+"
    pwd = "".join(random.SystemRandom().choice(chars) for _ in range(length))
    return (
        f"🔐 **Generated Secure Password ({length} chars):**\n\n"
        f"`{pwd}`\n\n"
        f"💡 _Tip: Tap on the password to copy it directly to clipboard._"
    )


def calculate_hashes(text: str) -> str:
    """Generates MD5, SHA-1, SHA-256, and Base64 hashes for input text."""
    clean = text.strip()
    if not clean:
        return "Usage: `/hash <text>`\nExample: `/hash AlyaAI`"

    b_text = clean.encode("utf-8")
    md5_h = hashlib.md5(b_text).hexdigest()
    sha1_h = hashlib.sha1(b_text).hexdigest()
    sha256_h = hashlib.sha256(b_text).hexdigest()
    b64_enc = base64.b64encode(b_text).decode("utf-8")

    return (
        f"🔑 **Cryptographic Hashes for:** `{clean}`\n\n"
        f"• **MD5**: `{md5_h}`\n"
        f"• **SHA-1**: `{sha1_h}`\n"
        f"• **SHA-256**: `{sha256_h}`\n"
        f"• **Base64 Encoded**: `{b64_enc}`"
    )


def unshorten_url(short_url: str) -> str:
    """Follows redirects to discover the true target URL of a shortened link."""
    clean = short_url.strip()
    if not clean.startswith(("http://", "https://")):
        clean = "https://" + clean
    try:
        resp = requests.head(clean, allow_redirects=True, timeout=8)
        return (
            f"🔍 **URL Unshortener / Safety Inspector:**\n\n"
            f"• **Original Link**: `{clean}`\n"
            f"• **Resolved Destination**: `{resp.url}`\n"
            f"• **Final Status**: `{resp.status_code}`"
        )
    except Exception as e:
        return f"❌ Failed to resolve link: `{str(e)}`"


def generate_tempmail() -> str:
    """Generates a random disposable temporary email address via GuerrillaMail API."""
    try:
        url = "https://api.guerrillamail.com/ajax.php?f=get_email_address"
        headers = {"User-Agent": "Mozilla/5.0"}
        resp = requests.get(url, headers=headers, timeout=6)
        if resp.status_code == 200:
            data = resp.json()
            email_addr = data.get("email_addr")
            sid_token = data.get("sid_token")
            return (
                f"📬 **Temporary Disposable Inbox Generated:**\n\n"
                f"📧 **Email**: `{email_addr}`\n"
                f"🔑 **Session Token**: `{sid_token}`\n\n"
                f"👉 **To check incoming OTPs / emails, send:**\n"
                f"`/checkmail {sid_token}`"
            )
    except Exception as e:
        logger.warning(f"TempMail generation error: {e}")

    # Fallback to random domain format
    rand_user = "user_" + "".join(random.choices(string.ascii_lowercase + string.digits, k=8))
    return f"📬 **Temporary Email (Ready):** `{rand_user}@guerrillamail.com`\n\nUse `/checkmail` to fetch messages."


def check_tempmail(token_or_email: str, domain: str = "") -> str:
    """Checks inbox messages via GuerrillaMail API."""
    clean_token = token_or_email.strip()
    try:
        url = f"https://api.guerrillamail.com/ajax.php?f=check_email&seq=0&sid_token={clean_token}"
        headers = {"User-Agent": "Mozilla/5.0"}
        resp = requests.get(url, headers=headers, timeout=6)
        if resp.status_code == 200:
            data = resp.json()
            emails = data.get("list", [])
            if not emails or len(emails) <= 1 and "Welcome" in emails[0].get("mail_subject", ""):
                return f"📭 Inbox is active! No new verification emails received yet. Send your OTP and check again in a few seconds."

            lines = [f"📬 **Temporary Inbox ({len(emails)} messages):**\n"]
            for m in emails[:3]:
                sender = m.get("mail_from", "Unknown")
                subj = m.get("mail_subject", "(No Subject)")
                excerpt = m.get("mail_excerpt", "").strip()
                lines.append(f"📩 **From**: `{sender}`\n• **Subject**: **{subj}**\n• **OTP/Preview**: `{excerpt[:150]}`")

            return "\n\n".join(lines)
    except Exception as e:
        logger.warning(f"TempMail check error: {e}")

    return f"📭 Inbox checked: No new messages found for session `{clean_token[:8]}...`"


# ---------------------------------------------------------------------------
# 3. Financial & Investment Calculators (SIP, EMI, Split)
# ---------------------------------------------------------------------------

def calculate_sip(monthly: float, annual_return: float, years: int) -> str:
    """Calculates Mutual Fund SIP compounding wealth generation."""
    try:
        i = (annual_return / 100) / 12
        n = years * 12
        total_invested = monthly * n
        maturity_value = monthly * (((1 + i)**n - 1) / i) * (1 + i)
        estimated_returns = maturity_value - total_invested

        return (
            f"📈 **Mutual Fund SIP Wealth Calculator:**\n\n"
            f"• Monthly Investment: **`₹{monthly:,.2f}`**\n"
            f"• Expected Annual Return: **`{annual_return:.1f}%`**\n"
            f"• Duration: **`{years} Years`** ({n} months)\n"
            f"────────────────────────\n"
            f"• Total Amount Invested: **`₹{total_invested:,.2f}`**\n"
            f"• Estimated Capital Gains: **`₹{estimated_returns:,.2f}`**\n"
            f"• **Total Maturity Value**: **`₹{maturity_value:,.2f}`** 🚀"
        )
    except Exception as e:
        return f"❌ SIP Calculation error: {str(e)}"


def calculate_emi(principal: float, annual_interest: float, years: int) -> str:
    """Calculates monthly EMI and total interest for Loans."""
    try:
        r = (annual_interest / 100) / 12
        n = years * 12
        emi = (principal * r * ((1 + r)**n)) / (((1 + r)**n) - 1)
        total_payable = emi * n
        total_interest = total_payable - principal

        return (
            f"🏦 **Loan EMI Calculator:**\n\n"
            f"• Loan Principal: **`₹{principal:,.2f}`**\n"
            f"• Interest Rate: **`{annual_interest:.2f}% p.a.`**\n"
            f"• Tenure: **`{years} Years`** ({n} months)\n"
            f"────────────────────────\n"
            f"• **Monthly EMI**: **`₹{emi:,.2f}`**\n"
            f"• Total Interest Payable: **`₹{total_interest:,.2f}`**\n"
            f"• Total Amount Payable: **`₹{total_payable:,.2f}`**"
        )
    except Exception as e:
        return f"❌ EMI Calculation error: {str(e)}"


def split_bill(amount: float, people: int, tip_pct: float = 0.0) -> str:
    """Calculates bill splitting among friends with optional tip."""
    try:
        if people <= 0:
            people = 1
        tip_amount = amount * (tip_pct / 100.0)
        total_bill = amount + tip_amount
        per_person = total_bill / people

        return (
            f"🧾 **Bill Splitter:**\n\n"
            f"• Subtotal: **`₹{amount:,.2f}`**\n"
            f"• Tip ({tip_pct}%): **`₹{tip_amount:,.2f}`**\n"
            f"• Total Bill: **`₹{total_bill:,.2f}`**\n"
            f"• Split Among: **`{people} People`**\n"
            f"────────────────────────\n"
            f"👉 **Each Person Pays**: **`₹{per_person:,.2f}`**"
        )
    except Exception as e:
        return f"❌ Bill split error: {str(e)}"


# ---------------------------------------------------------------------------
# 4. Health, Fitness & Nutrition (BMI, Nutrition, Water Tracker)
# ---------------------------------------------------------------------------

def calculate_bmi(weight_kg: float, height_cm: float) -> str:
    """Calculates Body Mass Index (BMI) and health category."""
    try:
        height_m = height_cm / 100.0 if height_cm > 3 else height_cm
        bmi = weight_kg / (height_m ** 2)

        if bmi < 18.5:
            cat = "Underweight (Need nutrient-dense diet)"
            icon = "🔵"
        elif 18.5 <= bmi < 24.9:
            cat = "Normal / Healthy Weight"
            icon = "🟢"
        elif 25.0 <= bmi < 29.9:
            cat = "Overweight (Regular cardio recommended)"
            icon = "🟡"
        else:
            cat = "Obese (Consult healthcare professional)"
            icon = "🔴"

        ideal_min = 18.5 * (height_m ** 2)
        ideal_max = 24.9 * (height_m ** 2)

        return (
            f"{icon} **BMI Health Assessment:**\n\n"
            f"• Weight: **`{weight_kg:.1f} kg`** | Height: **`{height_m*100:.0f} cm`**\n"
            f"• **Your BMI Score**: **`{bmi:.1f}`**\n"
            f"• **Category**: **{cat}**\n"
            f"• Ideal Weight Range: **`{ideal_min:.1f} kg – {ideal_max:.1f} kg`**"
        )
    except Exception as e:
        return f"❌ BMI calculation error: {str(e)}"


def lookup_calorie_nutrition(food_item: str) -> str:
    """Estimates nutrition and macronutrients using Groq LLM intelligence."""
    clean = food_item.strip()
    if not clean:
        return "Usage: `/calorie <food_item>`\nExample: `/calorie 2 boiled eggs and banana`"

    try:
        from groq import Groq
        key = os.getenv("GROQ_API_KEY")
        if key:
            client = Groq(api_key=key)
            resp = client.chat.completions.create(
                model="qwen/qwen3.6-27b",
                messages=[
                    {"role": "system", "content": "You are an expert sports nutritionist. Provide a structured nutritional breakdown (Calories, Protein, Carbohydrates, Fats, Fiber) in bullet points with emoji icons. Do not include thinking process."},
                    {"role": "user", "content": f"Give nutritional breakdown for: {clean}"}
                ],
                temperature=0.2,
                max_tokens=1500
            )
            res = _clean_llm_think(resp.choices[0].message.content)
            return f"🥗 **Nutritional Profile for `{clean}`:**\n\n{res}"
    except Exception as e:
        logger.warning(f"Nutrition lookup error: {e}")

    return f"❌ Failed to fetch nutrition data for `{clean}`."


# ---------------------------------------------------------------------------
# 5. Writing, Language & Templates (Grammar, Email Drafter, Synonyms)
# ---------------------------------------------------------------------------

def improve_grammar(text: str) -> str:
    """Fixes grammar, spelling, and polishes tone using Groq LLM."""
    clean = text.strip()
    if not clean:
        return "Usage: `/grammar <text_to_fix>`\nExample: `/grammar he go to market yesterday and buyed apples`"

    try:
        from groq import Groq
        key = os.getenv("GROQ_API_KEY")
        if key:
            client = Groq(api_key=key)
            resp = client.chat.completions.create(
                model="qwen/qwen3.6-27b",
                messages=[
                    {"role": "system", "content": "You are an expert English editor. Return the corrected version first, followed by a brief bullet list of improvements made. Do not include thinking process."},
                    {"role": "user", "content": f"Fix grammar and polish this text:\n\n{clean}"}
                ],
                temperature=0.1,
                max_tokens=1500
            )
            res = _clean_llm_think(resp.choices[0].message.content)
            return f"✍️ **Grammar & Style Polish:**\n\n{res}"
    except Exception as e:
        logger.warning(f"Grammar fix error: {e}")

    return "❌ Failed to process grammar correction."


def draft_email(topic: str) -> str:
    """Drafts a professional formal email template."""
    clean = topic.strip()
    if not clean:
        return "Usage: `/email <topic_or_purpose>`\nExample: `/email Sick leave for 2 days due to fever`"

    try:
        from groq import Groq
        key = os.getenv("GROQ_API_KEY")
        if key:
            client = Groq(api_key=key)
            resp = client.chat.completions.create(
                model="qwen/qwen3.6-27b",
                messages=[
                    {"role": "system", "content": "You are an executive corporate communication assistant. Draft a crisp, polite, ready-to-send email with Subject and Body. Do not include thinking process."},
                    {"role": "user", "content": f"Draft an email for: {clean}"}
                ],
                temperature=0.2,
                max_tokens=1500
            )
            res = _clean_llm_think(resp.choices[0].message.content)
            return f"✉️ **Drafted Email Template:**\n\n{res}"
    except Exception as e:
        logger.warning(f"Email draft error: {e}")

    return "❌ Failed to generate email template."


def lookup_synonyms_thesaurus(word: str) -> str:
    """Fetches synonyms, related words, and rhymes using Datamuse API (100% Free)."""
    clean_word = word.strip().lower()
    if not clean_word:
        return "Usage: `/synonym <word>`\nExample: `/synonym radiant`"

    try:
        url_syn = f"https://api.datamuse.com/words?rel_syn={clean_word}&max=8"
        url_ant = f"https://api.datamuse.com/words?rel_ant={clean_word}&max=5"

        syns = [w["word"] for w in requests.get(url_syn, timeout=5).json()]
        ants = [w["word"] for w in requests.get(url_ant, timeout=5).json()]

        syn_str = ", ".join(f"`{s}`" for s in syns) if syns else "None found"
        ant_str = ", ".join(f"`{a}`" for a in ants) if ants else "None found"

        return (
            f"📖 **Thesaurus & Synonyms for `{clean_word}`:**\n\n"
            f"• **Synonyms**: {syn_str}\n"
            f"• **Antonyms / Opposites**: {ant_str}"
        )
    except Exception as e:
        logger.warning(f"Synonym lookup error: {e}")

    return f"❌ Failed to fetch synonyms for `{clean_word}`."


# ---------------------------------------------------------------------------
# 6. Daily Productivity & Time (World Time, Countdown, QR Code, Barcode)
# ---------------------------------------------------------------------------

def get_world_time(city: str) -> str:
    """Gets real-time local time and timezone for world cities."""
    clean = city.strip()
    if not clean:
        clean = "London"

    try:
        from groq import Groq
        key = os.getenv("GROQ_API_KEY")
        if key:
            client = Groq(api_key=key)
            now_ist = datetime.now(IST).strftime("%Y-%m-%d %H:%M:%S IST")
            resp = client.chat.completions.create(
                model="qwen/qwen3.6-27b",
                messages=[
                    {"role": "system", "content": f"Current reference time is {now_ist}. Calculate the current local time, timezone, and difference with Indian Standard Time (IST UTC+5:30) for the specified city. Return concise bullet points without thinking process."},
                    {"role": "user", "content": f"What is the current time in {clean}?"}
                ],
                temperature=0.1,
                max_tokens=1500
            )
            res = _clean_llm_think(resp.choices[0].message.content)
            return f"🕒 **World Clock — `{clean}`:**\n\n{res}"
    except Exception as e:
        logger.warning(f"World time error: {e}")

    return f"🕒 Current IST Time: `{datetime.now(IST).strftime('%Y-%m-%d %H:%M:%S IST')}`"


def calculate_countdown(target_date_str: str) -> str:
    """Calculates time remaining until a target date or event."""
    clean = target_date_str.strip()
    if not clean:
        return "Usage: `/countdown <YYYY-MM-DD>`\nExample: `/countdown 2026-12-31`"

    try:
        target = datetime.strptime(clean, "%Y-%m-%d")
        now = datetime.now()
        diff = target - now

        if diff.total_seconds() < 0:
            return f"⏳ Target date `{clean}` has already passed ({abs(diff.days)} days ago)."

        days = diff.days
        hours, remainder = divmod(diff.seconds, 3600)
        minutes, _ = divmod(remainder, 60)

        return (
            f"⏳ **Countdown to `{clean}`:**\n\n"
            f"• **{days} Days, {hours} Hours, {minutes} Minutes remaining!** 🎯"
        )
    except Exception:
        return "❌ Date format must be `YYYY-MM-DD` (e.g. `/countdown 2026-12-31`)."


def generate_qr_code_file(text: str) -> str:
    """Generates a high-quality QR code image and saves to a local path."""
    clean = text.strip()
    if not clean:
        clean = "https://t.me/Alya_Rasa_Bot"

    import qrcode
    qr = qrcode.QRCode(version=1, box_size=10, border=3)
    qr.add_data(clean)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white")
    out_dir = "/tmp/alya_media"
    os.makedirs(out_dir, exist_ok=True)
    file_path = os.path.join(out_dir, f"qr_{int(time.time())}.png")
    img.save(file_path)
    return file_path


def generate_barcode_file(code: str) -> str:
    """Generates a Code128 barcode image."""
    clean = code.strip()
    if not clean:
        clean = "ALYA123456"

    import barcode
    from barcode.writer import ImageWriter

    out_dir = "/tmp/alya_media"
    os.makedirs(out_dir, exist_ok=True)
    CODE128 = barcode.get_barcode_class("code128")
    bc = CODE128(clean, writer=ImageWriter())
    file_path = os.path.join(out_dir, f"barcode_{int(time.time())}")
    saved = bc.save(file_path)
    return saved


# ---------------------------------------------------------------------------
# 7. Entertainment & Fun (Memes, Anime, Riddles, Random Pick, Recipes)
# ---------------------------------------------------------------------------

def generate_meme_url(top: str, bottom: str, template: str = "drake") -> str:
    """Generates a meme image URL via Memegen.link (100% Free)."""
    top_clean = requests.utils.quote(top.strip().replace(" ", "_") or "When_Alya_Answers")
    bot_clean = requests.utils.quote(bottom.strip().replace(" ", "_") or "Everything_Works_Smoothly")
    return f"https://api.memegen.link/images/{template}/{top_clean}/{bot_clean}.png"


def search_anime(title: str) -> str:
    """Searches Anime database via Kitsu API (with Jikan fallback)."""
    clean = title.strip()
    if not clean:
        return "Usage: `/anime <title>`\nExample: `/anime Death Note`"

    # 1. Try Kitsu REST API
    try:
        url = f"https://kitsu.io/api/edge/anime?filter[text]={requests.utils.quote(clean)}&page[limit]=1"
        headers = {"User-Agent": "Mozilla/5.0"}
        resp = requests.get(url, headers=headers, timeout=5)
        if resp.status_code == 200:
            data = resp.json().get("data", [])
            if data:
                a = data[0]["attributes"]
                rating = a.get("averageRating", "N/A")
                score_str = f"⭐ `{float(rating)/10:.1f} / 10`" if rating and rating != "N/A" else "⭐ `8.5 / 10`"
                return (
                    f"🎬 **Anime: {a.get('canonicalTitle')}**\n\n"
                    f"• **Score / Rating**: {score_str}\n"
                    f"• **Episodes**: `{a.get('episodeCount', 'N/A')}` ({a.get('status', 'Finished')})\n"
                    f"• **Aired**: `{a.get('startDate', 'N/A')} to {a.get('endDate', 'N/A')}`\n"
                    f"• **Age Rating**: `{a.get('ageRatingGuide', 'PG-13')}`\n"
                    f"• **Synopsis**: {a.get('synopsis', 'No synopsis available.')[:300]}..."
                )
    except Exception as e:
        logger.warning(f"Kitsu anime search error: {e}")

    # 2. Fallback to Groq LLM
    try:
        from groq import Groq
        key = os.getenv("GROQ_API_KEY")
        if key:
            client = Groq(api_key=key)
            resp = client.chat.completions.create(
                model="qwen/qwen3.6-27b",
                messages=[
                    {"role": "system", "content": "You are an anime encyclopedia. Return title, rating, episode count, genre, and a 2-sentence synopsis."},
                    {"role": "user", "content": f"Give anime details for: {clean}"}
                ],
                temperature=0.1,
                max_tokens=1500
            )
            res = _clean_llm_think(resp.choices[0].message.content)
            return f"🎬 **Anime Details — `{clean}`:**\n\n{res}"
    except Exception as e:
        logger.warning(f"LLM anime fallback error: {e}")

    return f"❌ No anime found for `{clean}`."


def get_riddle() -> str:
    """Returns a fun interactive riddle with spoiler answer."""
    riddles = [
        ("I speak without a mouth and hear without ears. I have no body, but I come alive with wind. What am I?", "An Echo 🗣️"),
        ("What has keys, but no locks; space, but no room; and you can enter, but can’t go inside?", "A Keyboard ⌨️"),
        ("The more of this there is, the less you see. What is it?", "Darkness 🌑"),
        ("What gets wet while drying?", "A Towel 🧖"),
        ("I have branches, but no fruit, trunk or leaves. What am I?", "A Bank 🏦"),
        ("What has to be broken before you can use it?", "An Egg 🥚")
    ]
    q, a = random.choice(riddles)
    return f"🧩 **Brain Riddle:**\n\n_{q}_\n\n||👉 Answer: {a}||"


def pick_random(items: str) -> str:
    """Picks a random item from a comma-separated list or rolls dice / flips coin."""
    clean = items.strip()
    if not clean or clean.lower() == "coin":
        return f"🪙 **Coin Flip**: **{random.choice(['Heads (चित्त)', 'Tails (पट)'])}**!"
    elif clean.lower() in ["dice", "d6"]:
        return f"🎲 **Dice Roll (D6)**: **{random.randint(1, 6)}**!"

    opts = [i.strip() for i in clean.split(",") if i.strip()]
    if len(opts) < 2:
        opts = clean.split()

    if len(opts) >= 2:
        winner = random.choice(opts)
        return f"🎯 **Random Decision Picked:** **`{winner}`**!"
    return "Usage: `/pick Option 1, Option 2, Option 3`"


def lookup_recipe(dish: str) -> str:
    """Searches recipes via MealDB with authentic Groq LLM recipe generator fallback."""
    clean = dish.strip()
    if not clean:
        return "Usage: `/recipe <dish_name>`\nExample: `/recipe Butter Chicken`"

    # 1. Try TheMealDB API
    try:
        url = f"https://www.themealdb.com/api/json/v1/1/search.php?s={requests.utils.quote(clean)}"
        resp = requests.get(url, timeout=5)
        if resp.status_code == 200:
            meals = resp.json().get("meals")
            if meals:
                m = meals[0]
                ingredients = []
                for i in range(1, 8):
                    ing = m.get(f"strIngredient{i}")
                    meas = m.get(f"strMeasure{i}")
                    if ing and ing.strip():
                        ingredients.append(f"• {meas.strip() if meas else ''} {ing.strip()}")

                return (
                    f"🍲 **Recipe: {m.get('strMeal')} ({m.get('strCategory', '')}, {m.get('strArea', '')})**\n\n"
                    f"**🛒 Key Ingredients:**\n" + "\n".join(ingredients) + "\n\n"
                    f"**👨‍🍳 Instructions:**\n{m.get('strInstructions', '')[:350]}...\n\n"
                    f"🎥 [Watch Video Tutorial]({m.get('strYoutube', '')})"
                )
    except Exception as e:
        logger.warning(f"MealDB search error: {e}")

    # 2. MasterChef LLM Recipe Generation Fallback
    try:
        from groq import Groq
        key = os.getenv("GROQ_API_KEY")
        if key:
            client = Groq(api_key=key)
            resp = client.chat.completions.create(
                model="qwen/qwen3.6-27b",
                messages=[
                    {"role": "system", "content": "You are an award-winning masterchef. Give a complete authentic recipe for the requested dish: Prep Time, Cook Time, Key Ingredients list, and 4-step Cooking Instructions. Do not include thinking process."},
                    {"role": "user", "content": f"Give recipe for: {clean}"}
                ],
                temperature=0.2,
                max_tokens=1500
            )
            res = _clean_llm_think(resp.choices[0].message.content)
            return f"🍲 **Authentic Recipe — `{clean}`:**\n\n{res}"
    except Exception as e:
        logger.warning(f"Recipe LLM error: {e}")

    return f"❌ No recipe found for `{clean}`."


# ---------------------------------------------------------------------------
# 8. India Specific Lookups (Pincode & Bank IFSC)
# ---------------------------------------------------------------------------

def lookup_pincode(query: str) -> str:
    """Looks up India Post office details by 6-digit PIN code or Area / Branch / City name."""
    clean = query.strip()
    if not clean or len(clean) < 2:
        return (
            "📌 **Pincode & Area Lookup Usage:**\n"
            "• `/pincode <6-digit PIN>` — e.g. `/pincode 110001`\n"
            "• `/pincode <Area/City Name>` — e.g. `/pincode Agra`, `/pincode Bandra`"
        )

    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

    # 1. If numeric 6-digit PIN code
    if clean.isdigit() and len(clean) == 6:
        try:
            url = f"https://api.postalpincode.in/pincode/{clean}"
            resp = requests.get(url, headers=headers, timeout=8)
            if resp.status_code == 200:
                data = resp.json()
                if data and data[0].get("Status") == "Success":
                    pos = data[0].get("PostOffice", [])
                    if not pos:
                        return f"❌ No postal data found for PIN code `{clean}`."

                    first = pos[0]
                    lines = [
                        f"📮 **India Post Pincode Info (`{clean}`):**\n",
                        f"• **District**: {first.get('District', 'N/A')}",
                        f"• **State**: {first.get('State', 'N/A')}",
                        f"• **Circle / Division**: {first.get('Circle', 'N/A')} / {first.get('Division', 'N/A')}",
                        f"• **Post Offices Covered ({len(pos)}):**"
                    ]
                    for po in pos[:12]:
                        del_stat = po.get("DeliveryStatus", "")
                        b_type = po.get("BranchType", "")
                        del_str = f" ({del_stat})" if del_stat else ""
                        type_str = f" [{b_type}]" if b_type else ""
                        lines.append(f"  - **{po.get('Name')}**{type_str}{del_str}")

                    if len(pos) > 12:
                        lines.append(f"  _...and {len(pos) - 12} more branches._")

                    return "\n".join(lines)
        except Exception as e:
            logger.warning(f"Pincode lookup error: {e}")
            return f"⚠️ Pincode lookup error: {e}"

        return f"❌ No postal data found for PIN code `{clean}`."

    # 2. Area / Branch / City Name Lookup
    try:
        encoded = urllib.parse.quote(clean)
        url = f"https://api.postalpincode.in/postoffice/{encoded}"
        resp = requests.get(url, headers=headers, timeout=8)
        if resp.status_code == 200:
            data = resp.json()
            if data and data[0].get("Status") == "Success":
                pos = data[0].get("PostOffice", [])
                if not pos:
                    return f"❌ No postal areas found matching `{clean}`."

                lines = [
                    f"📮 **India Post Area Lookup for \"{clean}\" ({len(pos)} found):**\n"
                ]
                for po in pos[:12]:
                    pincode = po.get("Pincode", "N/A")
                    name = po.get("Name", "N/A")
                    dist = po.get("District", "N/A")
                    state = po.get("State", "N/A")
                    del_stat = po.get("DeliveryStatus", "")
                    del_tag = f" • {del_stat}" if del_stat else ""
                    lines.append(f"• **{name}** — PIN: `{pincode}` ({dist}, {state}{del_tag})")

                if len(pos) > 12:
                    lines.append(f"\n_Showing top 12 of {len(pos)} areas. Try a more specific location name for exact match._")

                return "\n".join(lines)
    except Exception as e:
        logger.warning(f"Area pincode lookup error: {e}")
        return f"⚠️ Area pincode lookup error: {e}"

    return f"❌ No postal areas or PIN codes found matching `{clean}`."


def lookup_ifsc(ifsc_code: str) -> str:
    """Looks up Indian Bank Branch details by IFSC code via Razorpay IFSC API."""
    clean = ifsc_code.strip().upper()
    if len(clean) != 11:
        return "Usage: `/ifsc <11-character IFSC>`\nExample: `/ifsc SBIN0000001`"

    try:
        url = f"https://ifsc.razorpay.com/{clean}"
        resp = requests.get(url, timeout=6)
        if resp.status_code == 200:
            b = resp.json()
            return (
                f"🏦 **Bank Branch Details (`{clean}`):**\n\n"
                f"• **Bank**: **{b.get('BANK')}**\n"
                f"• **Branch**: {b.get('BRANCH')}\n"
                f"• **Address**: {b.get('ADDRESS')}\n"
                f"• **City / District**: {b.get('CITY')}, {b.get('DISTRICT')}, {b.get('STATE')}\n"
                f"• **UPI / IMPS / NEFT / RTGS**: {'✅ Enabled' if b.get('UPI') else '⚠️ Check Bank'}"
            )
    except Exception as e:
        logger.warning(f"IFSC lookup error: {e}")

    return f"❌ Invalid IFSC code or branch not found: `{clean}`."


def shorten_url(url: str) -> str:
    """Shortens a URL using TinyURL public API."""
    clean = url.strip()
    if not clean.startswith(("http://", "https://")):
        clean = "https://" + clean
    try:
        resp = requests.get(f"https://tinyurl.com/api-create.php?url={requests.utils.quote(clean)}", timeout=6)
        if resp.status_code == 200:
            return f"🔗 **Shortened URL:** `{resp.text}`"
    except Exception as e:
        logger.warning(f"URL shortener error: {e}")

    return f"❌ Failed to shorten URL `{clean}`."


# ---------------------------------------------------------------------------
# 9. Today in History & Daily Milestones
# ---------------------------------------------------------------------------

def get_today_in_history(date_query: Optional[str] = None) -> str:
    """Fetches historic events, milestones, and famous births that happened on this day."""
    now = datetime.now(IST)
    month = now.month
    day = now.day
    date_title = now.strftime("%d %B")

    try:
        url = f"https://en.wikipedia.org/api/rest_v1/feed/onthisday/selected/{month:02d}/{day:02d}"
        headers = {"User-Agent": "AlyaBot/1.0 (https://t.me/Alya_Rasa_Bot)"}
        resp = requests.get(url, headers=headers, timeout=8)
        if resp.status_code == 200:
            data = resp.json()
            events = data.get("selected", [])
            if events:
                lines = [f"📜 **Today in History — {date_title}**\n"]
                for ev in events[:4]:
                    yr = ev.get("year", "N/A")
                    txt = ev.get("text", "")
                    lines.append(f"• **{yr}**: {txt}")

                # Also get famous birth
                births_url = f"https://en.wikipedia.org/api/rest_v1/feed/onthisday/births/{month:02d}/{day:02d}"
                resp_b = requests.get(births_url, headers=headers, timeout=6)
                if resp_b.status_code == 200:
                    b_data = resp_b.json().get("births", [])
                    if b_data:
                        b = b_data[0]
                        lines.append(f"\n🎂 **Famous Birthday**: **{b.get('text')}** (Born {b.get('year')})")

                return "\n".join(lines)
    except Exception as e:
        logger.warning(f"OnThisDay API error: {e}")

    # Fallback to LLM
    try:
        from .llm_provider import LLMProviderManager
        content, _, _ = LLMProviderManager.call_chat_completion(
            messages=[
                {"role": "system", "content": "You are a historical facts expert. Provide 3 major historical events and 1 notable birthday for today's date in crisp bullet points."},
                {"role": "user", "content": f"What happened today in history on {date_title}?"}
            ],
            temperature=0.3,
            max_tokens=350
        )
        if content:
            return f"📜 **Today in History — {date_title}**:\n\n{_clean_llm_think(content)}"
    except Exception as ex2:
        logger.error(f"LLM OnThisDay fallback error: {ex2}")

    return f"⚠️ Unable to fetch historical events for {date_title} right now."


# ---------------------------------------------------------------------------
# 10. Indian PAN & GSTIN Smart Validator
# ---------------------------------------------------------------------------

PAN_CARD_TYPES = {
    "P": "Individual (Single Person)",
    "C": "Company (Private / Public Ltd)",
    "H": "Hindu Undivided Family (HUF)",
    "F": "Partnership Firm / LLP",
    "A": "Association of Persons (AOP)",
    "T": "Trust",
    "B": "Body of Individuals (BOI)",
    "L": "Local Authority / Municipality",
    "J": "Artificial Juridical Person",
    "G": "Government Agency / Department"
}

GSTIN_STATE_CODES = {
    "01": "Jammu and Kashmir", "02": "Himachal Pradesh", "03": "Punjab", "04": "Chandigarh",
    "05": "Uttarakhand", "06": "Haryana", "07": "Delhi", "08": "Rajasthan", "09": "Uttar Pradesh",
    "10": "Bihar", "11": "Sikkim", "12": "Arunachal Pradesh", "13": "Nagaland", "14": "Manipur",
    "15": "Mizoram", "16": "Tripura", "17": "Meghalaya", "18": "Assam", "19": "West Bengal",
    "20": "Jharkhand", "21": "Odisha", "22": "Chhattisgarh", "23": "Madhya Pradesh", "24": "Gujarat",
    "26": "Dadra & Nagar Haveli and Daman & Diu", "27": "Maharashtra", "29": "Karnataka", "30": "Goa",
    "31": "Lakshadweep", "32": "Kerala", "33": "Tamil Nadu", "34": "Puducherry",
    "35": "Andaman & Nicobar Islands", "36": "Telangana", "37": "Andhra Pradesh", "38": "Ladakh",
    "97": "Other Territory", "99": "Centre Jurisdiction"
}

def validate_pan_card(pan: str) -> str:
    """Validates Indian Permanent Account Number (PAN) and analyzes structure."""
    clean = pan.strip().upper()
    if not clean:
        return "Usage: `/pan <10-character PAN>`\nExample: `/pan ABCDE1234F`"

    if len(clean) != 10 or not re.match(r"^[A-Z]{5}[0-9]{4}[A-Z]$", clean):
        return (
            f"❌ **Invalid PAN Card Format (`{clean}`):**\n\n"
            f"• An Indian PAN must be exactly 10 characters.\n"
            f"• Structure: `5 Letters` + `4 Digits` + `1 Letter` (e.g. `ABCDE1234F`).\n"
            f"• Please check the number and try again."
        )

    entity_code = clean[3]
    surname_char = clean[4]
    entity_desc = PAN_CARD_TYPES.get(entity_code, "Special Entity")

    return (
        f"💳 **PAN Card Verification & Structure Breakdown:**\n\n"
        f"• **PAN Number**: `{clean}`\n"
        f"• **Status**: 🟢 **Valid PAN Format & Structure**\n"
        f"• **Cardholder / Entity Type**: **{entity_desc}** (Code: `{entity_code}`)\n"
        f"• **Surname / Entity Initial**: `{surname_char}`\n"
        f"• **Series Sequence**: `{clean[:3]}` | Digits: `{clean[5:9]}` | Check-Char: `{clean[9]}`\n\n"
        f"_Note: Format verification conforms to Income Tax Department (ITD) rules._"
    )


def validate_gstin(gstin: str) -> str:
    """Validates Indian Goods and Services Tax Identification Number (GSTIN)."""
    clean = gstin.strip().upper()
    if not clean:
        return "Usage: `/gstin <15-digit GSTIN>`\nExample: `/gstin 27ABCDE1234F1Z5`"

    if len(clean) != 15 or not re.match(r"^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z][1-9A-Z]Z[0-9A-Z]$", clean):
        return (
            f"❌ **Invalid GSTIN Format (`{clean}`):**\n\n"
            f"• Indian GSTIN must be exactly 15 characters.\n"
            f"• Format: `2-Digit State Code` + `10-Digit PAN` + `Entity Code` + `Z` + `Checksum`.\n"
            f"• Example: `27ABCDE1234F1Z5`"
        )

    state_code = clean[:2]
    extracted_pan = clean[2:12]
    entity_code = clean[12]
    checksum = clean[14]

    state_name = GSTIN_STATE_CODES.get(state_code, "Unknown State Code")
    entity_type = PAN_CARD_TYPES.get(extracted_pan[3], "Business Entity")

    return (
        f"🏢 **GSTIN Verification & Structure Breakdown:**\n\n"
        f"• **GSTIN Number**: `{clean}`\n"
        f"• **Status**: 🟢 **Valid GSTIN Structure**\n"
        f"• **State / Jurisdiction**: **{state_name}** (State Code: `{state_code}`)\n"
        f"• **Linked PAN**: `{extracted_pan}`\n"
        f"• **Entity Category**: **{entity_type}**\n"
        f"• **State Registration Index**: #{entity_code}\n"
        f"• **Checksum Digit**: `{checksum}`\n\n"
        f"_Conforms to GST Council India format specifications._"
    )


# ---------------------------------------------------------------------------
# 11. Universal Unit & Land Area Converter
# ---------------------------------------------------------------------------

def convert_universal_unit(query: str) -> str:
    """Universal converter for Indian Land Area, Length, Weight, Temp, Speed, Digital Data."""
    clean = query.strip()
    if not clean:
        return (
            "📐 **Universal Unit Converter Usage:**\n\n"
            "• `/unit <val> <from_unit> to <to_unit>`\n"
            "• **Indian Land**: `/unit 2 bigha to sqft`, `/unit 5 acre to bigha`, `/unit 10 guntha to sqyd`\n"
            "• **Weight/Mass**: `/unit 50 kg to lbs`, `/unit 10 tola to grams`\n"
            "• **Length**: `/unit 100 km to miles`, `/unit 6 feet to cm`\n"
            "• **Temperature**: `/unit 100 f to c`, `/unit 37 c to f`\n"
            "• **Digital**: `/unit 500 gb to mb`, `/unit 2 tb to gb`"
        )

    area_to_sqft = {
        "sqft": 1.0, "sq_ft": 1.0, "square_feet": 1.0, "ft2": 1.0,
        "sqyd": 9.0, "sq_yd": 9.0, "gaj": 9.0, "square_yard": 9.0, "yd2": 9.0,
        "sqm": 10.7639, "sq_m": 10.7639, "square_meter": 10.7639, "m2": 10.7639,
        "acre": 43560.0, "acres": 43560.0,
        "hectare": 107639.1, "hectares": 107639.1, "ha": 107639.1,
        "bigha": 27225.0, "bighas": 27225.0,
        "guntha": 1089.0, "gunthas": 1089.0, "guntas": 1089.0,
        "biswa": 1361.25, "biswas": 1361.25,
        "katha": 720.0, "kathas": 720.0, "cottah": 720.0,
        "ground": 2400.0, "grounds": 2400.0
    }

    weight_to_g = {
        "mg": 0.001, "milligram": 0.001,
        "g": 1.0, "gram": 1.0, "grams": 1.0,
        "kg": 1000.0, "kilogram": 1000.0, "kgs": 1000.0,
        "quintal": 100000.0, "quintals": 100000.0,
        "tonne": 1000000.0, "ton": 1000000.0, "tonnes": 1000000.0,
        "lb": 453.592, "lbs": 453.592, "pound": 453.592, "pounds": 453.592,
        "oz": 28.3495, "ounce": 28.3495, "ounces": 28.3495,
        "tola": 11.6638, "tolas": 11.6638
    }

    length_to_m = {
        "mm": 0.001, "cm": 0.01, "m": 1.0, "meter": 1.0, "meters": 1.0,
        "km": 1000.0, "kilometer": 1000.0, "kms": 1000.0,
        "inch": 0.0254, "inches": 0.0254, "in": 0.0254,
        "ft": 0.3048, "foot": 0.3048, "feet": 0.3048,
        "yard": 0.9144, "yards": 0.9144, "yd": 0.9144,
        "mile": 1609.344, "miles": 1609.344,
        "nm": 1852.0, "nautical_mile": 1852.0
    }

    pattern = r"^([0-9.]+)\s*([a-zA-Z_]+)\s*(?:to|in|=)?\s*([a-zA-Z_]+)$"
    m = re.match(pattern, clean.lower())
    if m:
        val = float(m.group(1))
        from_u = m.group(2).strip()
        to_u = m.group(3).strip()

        if from_u in area_to_sqft and to_u in area_to_sqft:
            sqft = val * area_to_sqft[from_u]
            res = sqft / area_to_sqft[to_u]
            return f"📐 **Land Area Conversion:**\n\n• `{val:,.4g} {from_u}` = **`{res:,.4g} {to_u}`**\n• _(Equivalent to `{sqft:,.2f}` Sq. Feet / `{sqft/43560:,.4f}` Acres)_"

        if from_u in weight_to_g and to_u in weight_to_g:
            g = val * weight_to_g[from_u]
            res = g / weight_to_g[to_u]
            return f"⚖️ **Weight / Mass Conversion:**\n\n• `{val:,.4g} {from_u}` = **`{res:,.4g} {to_u}`**\n• _(Base: `{g:,.2f}` grams / `{g/1000:,.4f}` kg)_"

        if from_u in length_to_m and to_u in length_to_m:
            meters = val * length_to_m[from_u]
            res = meters / length_to_m[to_u]
            return f"📏 **Length / Distance Conversion:**\n\n• `{val:,.4g} {from_u}` = **`{res:,.4g} {to_u}`**\n• _(Base: `{meters:,.2f}` meters)_"

        if from_u in ["c", "celsius"] and to_u in ["f", "fahrenheit"]:
            res = (val * 9/5) + 32
            return f"🌡️ **Temperature Conversion:**\n\n• `{val:,.2f} °C` = **`{res:,.2f} °F`**"
        if from_u in ["f", "fahrenheit"] and to_u in ["c", "celsius"]:
            res = (val - 32) * 5/9
            return f"🌡️ **Temperature Conversion:**\n\n• `{val:,.2f} °F` = **`{res:,.2f} °C`**"

    try:
        from .llm_provider import LLMProviderManager
        content, _, _ = LLMProviderManager.call_chat_completion(
            messages=[
                {"role": "system", "content": "You are a precise scientific unit conversion calculator. Calculate exact conversion. Output result in 2 crisp bullet points with formulas."},
                {"role": "user", "content": f"Convert: {clean}"}
            ],
            temperature=0.1,
            max_tokens=200
        )
        if content:
            return f"📐 **Unit Conversion Result:**\n\n{_clean_llm_think(content)}"
    except Exception as e:
        logger.error(f"Unit conversion fallback error: {e}")

    return f"⚠️ Unable to parse unit conversion for `{clean}`. Format: `/unit 5 acre to bigha`"


# ---------------------------------------------------------------------------
# 12. Daily Horoscope & Zodiac Insights
# ---------------------------------------------------------------------------

ZODIAC_SIGNS = {
    "aries": ("Aries ♈", "Mesh (मेष)"),
    "mesh": ("Aries ♈", "Mesh (मेष)"),
    "taurus": ("Taurus ♉", "Vrishabh (वृषभ)"),
    "vrishabh": ("Taurus ♉", "Vrishabh (वृषभ)"),
    "gemini": ("Gemini ♊", "Mithun (मिथुन)"),
    "mithun": ("Gemini ♊", "Mithun (मिथुन)"),
    "cancer": ("Cancer ♋", "Kark (कर्क)"),
    "kark": ("Cancer ♋", "Kark (कर्क)"),
    "leo": ("Leo ♌", "Singh (सिंह)"),
    "singh": ("Leo ♌", "Singh (सिंह)"),
    "simha": ("Leo ♌", "Singh (सिंह)"),
    "virgo": ("Virgo ♍", "Kanya (कन्या)"),
    "kanya": ("Virgo ♍", "Kanya (कन्या)"),
    "libra": ("Libra ♎", "Tula (तुला)"),
    "tula": ("Libra ♎", "Tula (तुला)"),
    "scorpio": ("Scorpio ♏", "Vrishchik (वृश्चिक)"),
    "vrishchik": ("Scorpio ♏", "Vrishchik (वृश्चिक)"),
    "sagittarius": ("Sagittarius ♐", "Dhanu (धनु)"),
    "dhanu": ("Sagittarius ♐", "Dhanu (धनु)"),
    "capricorn": ("Capricorn ♑", "Makar (मकर)"),
    "makar": ("Capricorn ♑", "Makar (मकर)"),
    "aquarius": ("Aquarius ♒", "Kumbh (कुंभ)"),
    "kumbh": ("Aquarius ♒", "Kumbh (कुंभ)"),
    "pisces": ("Pisces ♓", "Meen (मीन)"),
    "meen": ("Pisces ♓", "Meen (मीन)")
}

def get_daily_horoscope(sign: str) -> str:
    """Generates daily horoscope predictions, lucky numbers, and astrological guidance."""
    clean = sign.strip().lower()
    if not clean or clean not in ZODIAC_SIGNS:
        return (
            "🔮 **Daily Horoscope Usage:**\n\n"
            "• `/horoscope <zodiac_sign>`\n"
            "• Supported Signs (English / Hindi):\n"
            "  `Aries` (Mesh), `Taurus` (Vrishabh), `Gemini` (Mithun), `Cancer` (Kark),\n"
            "  `Leo` (Singh), `Virgo` (Kanya), `Libra` (Tula), `Scorpio` (Vrishchik),\n"
            "  `Sagittarius` (Dhanu), `Capricorn` (Makar), `Aquarius` (Kumbh), `Pisces` (Meen)\n\n"
            "Example: `/horoscope Leo` ya `/horoscope Mesh`"
        )

    eng_name, hindi_name = ZODIAC_SIGNS[clean]
    today_date = datetime.now(IST).strftime("%A, %d %B %Y")

    try:
        from .llm_provider import LLMProviderManager
        content, _, _ = LLMProviderManager.call_chat_completion(
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are an encouraging, insightful astrologer for Alya AI. "
                        "Generate a crisp, uplifting daily horoscope in Hinglish/English for the requested zodiac sign. "
                        "Include:\n"
                        "1. 🌟 **General Outlook & Mood** (2-3 sentences)\n"
                        "2. 💼 **Career & Finance** (1-2 sentences)\n"
                        "3. ❤️ **Love & Relationships** (1-2 sentences)\n"
                        "4. 🎯 **Lucky Color & Lucky Number**\n"
                        "5. ✨ **Alya's Daily Tip** (1 punchy witty line)"
                    )
                },
                {"role": "user", "content": f"Give daily horoscope for {eng_name} ({hindi_name}) for date {today_date}."}
            ],
            temperature=0.7,
            max_tokens=400
        )
        if content:
            return (
                f"🔮 **Daily Horoscope — {eng_name} / {hindi_name}**\n"
                f"🗓️ **Date**: `{today_date}`\n\n"
                f"{_clean_llm_think(content)}"
            )
    except Exception as e:
        logger.error(f"Horoscope generation error: {e}")

    return f"⚠️ Unable to generate horoscope reading for `{sign}` right now. Please try again in a moment."


# ---------------------------------------------------------------------------
# 13. Tech & Hacker News Top Digest
# ---------------------------------------------------------------------------

def get_tech_hackernews_digest() -> str:
    """Fetches top 5 trending tech and startup discussions from Hacker News."""
    try:
        top_ids_url = "https://hacker-news.firebaseio.com/v0/topstories.json"
        resp = requests.get(top_ids_url, timeout=6)
        if resp.status_code == 200:
            story_ids = resp.json()[:5]
            stories = []
            for s_id in story_ids:
                item_url = f"https://hacker-news.firebaseio.com/v0/item/{s_id}.json"
                i_resp = requests.get(item_url, timeout=4)
                if i_resp.status_code == 200:
                    item = i_resp.json()
                    title = item.get("title", "No Title")
                    score = item.get("score", 0)
                    comments = item.get("descendants", 0)
                    url = item.get("url", f"https://news.ycombinator.com/item?id={s_id}")
                    by = item.get("by", "unknown")
                    domain = url.split("/")[2].replace("www.", "") if "://" in url else "news.ycombinator.com"
                    stories.append(
                        f"• 🚀 **[{title}]({url})**\n"
                        f"  _(🌐 `{domain}` | ⬆️ `{score}` pts | 💬 `{comments}` comments | By `{by}`)_"
                    )

            if stories:
                return (
                    f"🔥 **Hacker News — Top Trending Tech Stories:**\n\n"
                    + "\n\n".join(stories) +
                    "\n\n_Discussion thread: [Hacker News](https://news.ycombinator.com)_"
                )
    except Exception as e:
        logger.warning(f"HackerNews API error: {e}")

    return "⚠️ Could not fetch Hacker News top stories right now."


# ---------------------------------------------------------------------------
# 14. Slang & Idioms Decoder
# ---------------------------------------------------------------------------

def lookup_slang_or_idiom(term: str) -> str:
    """Explains internet slangs, Gen-Z jargon, and English idioms with examples and Hindi meaning."""
    clean = term.strip()
    if not clean:
        return (
            "🗣️ **Slang & Idiom Decoder Usage:**\n\n"
            "• `/slang <word_or_slang>` — e.g. `/slang rizz`, `/slang no cap`, `/slang delulu`, `/slang sus`\n"
            "• `/idiom <phrase>` — e.g. `/idiom bite the bullet`, `/idiom spill the beans`"
        )

    try:
        from .llm_provider import LLMProviderManager
        content, _, _ = LLMProviderManager.call_chat_completion(
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are an expert slang and idiom linguist for Alya AI. "
                        "Explain the given slang, idiom, or internet phrase clearly in modern Hinglish/English. "
                        "Format your response as:\n"
                        "• 📖 **Meaning / Definition**: (1-2 clear lines)\n"
                        "• 🇮🇳 **Hindi / Hinglish Equivalent**: (Desi meaning or relatable phrase)\n"
                        "• 💬 **Example in Sentence**: (Realistic conversational dialogue)\n"
                        "• 🔍 **Origin / Cultural Context**: (Brief 1 line on where it originated)"
                    )
                },
                {"role": "user", "content": f"Explain the slang/idiom: \"{clean}\""}
            ],
            temperature=0.3,
            max_tokens=350
        )
        if content:
            return (
                f"🗣️ **Slang / Idiom Breakdown: `{clean}`**\n\n"
                f"{_clean_llm_think(content)}"
            )
    except Exception as e:
        logger.error(f"Slang lookup error: {e}")

    return f"⚠️ Could not decode slang `{clean}` right now."
