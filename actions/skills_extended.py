import os
import json
import logging
import random
import string
import hashlib
import base64
import time
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional
import requests
from dotenv import load_dotenv

load_dotenv("/home/ubuntu/Rasa/.env")
logger = logging.getLogger(__name__)

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

    # Use Groq LLM for natural translation
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
                max_tokens=200
            )
            explanation = resp.choices[0].message.content
            import re
            explanation = re.sub(r"<think>.*?</think>", "", explanation, flags=re.DOTALL).strip()
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
    """Generates a random disposable temporary email address via 1secmail API."""
    try:
        resp = requests.get("https://www.1secmail.com/api/v1/?action=genRandomMailbox&count=1", timeout=6)
        if resp.status_code == 200:
            mails = resp.json()
            if mails:
                email_addr = mails[0]
                login, domain = email_addr.split("@")
                return (
                    f"📬 **Temporary Disposable Inbox Generated:**\n\n"
                    f"📧 **Email**: `{email_addr}`\n\n"
                    f"👉 **To check OTP / incoming emails, send:**\n"
                    f"`/checkmail {login} {domain}`"
                )
    except Exception as e:
        logger.warning(f"TempMail generation error: {e}")

    return "❌ Failed to generate temporary email."


def check_tempmail(login: str, domain: str) -> str:
    """Checks inbox messages for 1secmail temporary email."""
    try:
        url = f"https://www.1secmail.com/api/v1/?action=getMessages&login={login}&domain={domain}"
        resp = requests.get(url, timeout=6)
        if resp.status_code == 200:
            msgs = resp.json()
            if not msgs:
                return f"📭 Inbox for `{login}@{domain}` is currently empty. Send your verification email and check again."

            lines = [f"📬 **Inbox for `{login}@{domain}` ({len(msgs)} messages):**\n"]
            for m in msgs[:3]:
                msg_id = m.get("id")
                # fetch message body
                msg_url = f"https://www.1secmail.com/api/v1/?action=readMessage&login={login}&domain={domain}&id={msg_id}"
                m_resp = requests.get(msg_url, timeout=6).json()
                from_addr = m_resp.get("from", "Unknown")
                subj = m_resp.get("subject", "(No Subject)")
                body = m_resp.get("textBody", "").strip()
                lines.append(f"📩 **From**: {from_addr}\n• **Subject**: {subj}\n• **Body/OTP**: {body[:250]}...")

            return "\n\n".join(lines)
    except Exception as e:
        logger.warning(f"TempMail check error: {e}")

    return "❌ Failed to fetch emails for this temporary inbox."


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
                    {"role": "system", "content": "You are an expert sports nutritionist. Provide a structured nutritional breakdown (Calories, Protein, Carbohydrates, Fats, Fiber) in bullet points with emoji icons."},
                    {"role": "user", "content": f"Give nutritional breakdown for: {clean}"}
                ],
                temperature=0.2,
                max_tokens=350
            )
            res = resp.choices[0].message.content
            import re
            res = re.sub(r"<think>.*?</think>", "", res, flags=re.DOTALL).strip()
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
                    {"role": "system", "content": "You are an expert English editor. Return the corrected version first, followed by a brief bullet list of what was improved and why."},
                    {"role": "user", "content": f"Fix grammar and polish this text:\n\n{clean}"}
                ],
                temperature=0.1,
                max_tokens=400
            )
            res = resp.choices[0].message.content
            import re
            res = re.sub(r"<think>.*?</think>", "", res, flags=re.DOTALL).strip()
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
                    {"role": "system", "content": "You are an executive corporate communication assistant. Draft a crisp, polite, ready-to-send email with Subject and Body."},
                    {"role": "user", "content": f"Draft an email for: {clean}"}
                ],
                temperature=0.2,
                max_tokens=500
            )
            res = resp.choices[0].message.content
            import re
            res = re.sub(r"<think>.*?</think>", "", res, flags=re.DOTALL).strip()
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
            now_utc = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
            resp = client.chat.completions.create(
                model="qwen/qwen3.6-27b",
                messages=[
                    {"role": "system", "content": f"Current reference time is {now_utc}. Calculate the current local time, timezone, and difference with Indian Standard Time (IST UTC+5:30) for the specified city."},
                    {"role": "user", "content": f"What is the current time in {clean}?"}
                ],
                temperature=0.1,
                max_tokens=200
            )
            res = resp.choices[0].message.content
            import re
            res = re.sub(r"<think>.*?</think>", "", res, flags=re.DOTALL).strip()
            return f"🕒 **World Clock — `{clean}`:**\n\n{res}"
    except Exception as e:
        logger.warning(f"World time error: {e}")

    return f"🕒 Current UTC Time: `{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')}`"


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
    """Searches MyAnimeList database via Jikan REST API (100% Free)."""
    clean = title.strip()
    if not clean:
        return "Usage: `/anime <title>`\nExample: `/anime Death Note`"

    try:
        url = f"https://api.jikan.moe/v4/anime?q={requests.utils.quote(clean)}&limit=1"
        resp = requests.get(url, timeout=6)
        if resp.status_code == 200:
            data = resp.json().get("data", [])
            if data:
                a = data[0]
                return (
                    f"🎬 **Anime: {a.get('title')} ({a.get('title_japanese', '')})**\n\n"
                    f"• **Score / Rating**: ⭐ `{a.get('score', 'N/A')} / 10`\n"
                    f"• **Episodes**: `{a.get('episodes', 'N/A')}` ({a.get('status', '')})\n"
                    f"• **Aired**: `{a.get('aired', {}).get('string', 'N/A')}`\n"
                    f"• **Synopsis**: {a.get('synopsis', 'No synopsis available.')[:300]}...\n\n"
                    f"🔗 [View on MyAnimeList]({a.get('url')})"
                )
    except Exception as e:
        logger.warning(f"Anime search error: {e}")

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
    """Searches meal recipes via Free MealDB API."""
    clean = dish.strip()
    if not clean:
        return "Usage: `/recipe <dish_name>`\nExample: `/recipe Butter Chicken`"

    try:
        url = f"https://www.themealdb.com/api/json/v1/1/search.php?s={requests.utils.quote(clean)}"
        resp = requests.get(url, timeout=6)
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
        logger.warning(f"Recipe lookup error: {e}")

    return f"❌ No recipe found for `{clean}`."


# ---------------------------------------------------------------------------
# 8. India Specific Lookups (Pincode & Bank IFSC)
# ---------------------------------------------------------------------------

def lookup_pincode(pincode: str) -> str:
    """Looks up India Post office details by 6-digit PIN code."""
    clean = pincode.strip()
    if not (clean.isdigit() and len(clean) == 6):
        return "Usage: `/pincode <6-digit PIN>`\nExample: `/pincode 732101`"

    try:
        url = f"https://api.postalpincode.in/pincode/{clean}"
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        resp = requests.get(url, headers=headers, timeout=6)
        if resp.status_code == 200:
            data = resp.json()
            if data and data[0].get("Status") == "Success":
                po = data[0].get("PostOffice", [])[0]
                return (
                    f"📮 **India Post Pincode Info (`{clean}`):**\n\n"
                    f"• **Post Office**: {po.get('Name')}\n"
                    f"• **District**: {po.get('District')}\n"
                    f"• **State**: {po.get('State')}\n"
                    f"• **Branch Type**: {po.get('BranchType')} ({po.get('DeliveryStatus')})\n"
                    f"• **Circle / Region**: {po.get('Circle')} / {po.get('Region')}"
                )
    except Exception as e:
        logger.warning(f"Pincode lookup error: {e}")

    return f"❌ No postal data found for PIN code `{clean}`."


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
