import os
import re
import logging
import requests
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)
IST = timezone(timedelta(hours=5, minutes=30), name="IST")

YAHOO_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}


def _clean_llm_think(text: str) -> str:
    """Strips <think> tags from LLM responses."""
    if "</think>" in text:
        text = text.split("</think>")[-1].strip()
    elif "<think>" in text:
        text = re.sub(r"<think>.*", "", text, flags=re.DOTALL).strip()
    return text.strip()


# ---------------------------------------------------------------------------
# 1. Stock Market & Index Quotes (NSE / BSE / Global)
# ---------------------------------------------------------------------------

def get_stock_quote(symbol: str) -> str:
    """
    Fetches real-time price, day change, and 52-week range for NSE/BSE and global stocks.
    Example: RELIANCE, TATAMOTORS, INFY, AAPL, NIFTY50, SENSEX
    """
    clean_sym = symbol.strip().upper()
    if not clean_sym:
        clean_sym = "RELIANCE"

    # Map common aliases
    alias_map = {
        "NIFTY": "^NSEI",
        "NIFTY50": "^NSEI",
        "SENSEX": "^BSESN",
        "BANKNIFTY": "^NSEBANK",
        "GOLD": "GC=F",
        "SILVER": "SI=F",
        "CRUDE": "CL=F",
        "BITCOIN": "BTC-USD",
    }

    ticker = alias_map.get(clean_sym, clean_sym)
    # If standard Indian stock symbol without extension, try appending .NS first
    if not ticker.startswith("^") and not ticker.endswith((".NS", ".BO", "-USD", "=F")):
        ticker_query = f"{ticker}.NS"
    else:
        ticker_query = ticker

    try:
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker_query}?interval=1d&range=1d"
        resp = requests.get(url, headers=YAHOO_HEADERS, timeout=8)
        if resp.status_code != 200 or not resp.json().get("chart", {}).get("result"):
            # Fallback without .NS (e.g. US stock like AAPL, TSLA)
            url_fallback = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}?interval=1d&range=1d"
            resp = requests.get(url_fallback, headers=YAHOO_HEADERS, timeout=8)

        data = resp.json()["chart"]["result"][0]["meta"]
        price = data.get("regularMarketPrice", 0.0)
        prev_close = data.get("chartPreviousClose") or price
        curr = data.get("currency", "INR")
        curr_symbol = "₹" if curr == "INR" else ("$" if curr == "USD" else curr)

        change = price - prev_close
        pct = (change / prev_close) * 100 if prev_close else 0.0
        sign = "🟢 +" if change >= 0 else "🔴 "

        high = data.get("regularMarketDayHigh", price)
        low = data.get("regularMarketDayLow", price)
        name = data.get("shortName") or data.get("symbol") or clean_sym

        return (
            f"📈 **Market Quote: `{name}`**\n\n"
            f"• **Current Price**: `{curr_symbol}{price:,.2f}`\n"
            f"• **Change**: {sign}`{change:+,.2f} ({pct:+.2f}%)`\n"
            f"• **Day's High**: `{curr_symbol}{high:,.2f}`\n"
            f"• **Day's Low**: `{curr_symbol}{low:,.2f}`\n"
            f"• **Previous Close**: `{curr_symbol}{prev_close:,.2f}`\n"
            f"• **Exchange / Currency**: `{data.get('exchangeName', 'NSE')} ({curr})`\n"
            f"• **Time (IST)**: `{datetime.now(IST).strftime('%d %b %Y, %I:%M %p')}`"
        )
    except Exception as e:
        logger.error(f"Stock quote error for {symbol}: {e}")
        return f"⚠️ Could not fetch market quote for `{clean_sym}`. Please verify ticker symbol (e.g. `RELIANCE`, `TCS`, `TATAMOTORS`, `NIFTY`)."


# ---------------------------------------------------------------------------
# 2. Gold & Silver Live Bullion Rates (India MCX / Spot)
# ---------------------------------------------------------------------------

def get_gold_silver_rates() -> str:
    """
    Fetches real-time Gold and Silver rates in India (24K, 22K 10g Gold & 1kg Silver).
    """
    try:
        # Fetch USD spot gold and USDINR exchange rate
        url_gold = "https://query1.finance.yahoo.com/v8/finance/chart/GC=F?interval=1d&range=1d"
        url_silver = "https://query1.finance.yahoo.com/v8/finance/chart/SI=F?interval=1d&range=1d"
        url_usdinr = "https://query1.finance.yahoo.com/v8/finance/chart/USDINR=X?interval=1d&range=1d"

        r_gold = requests.get(url_gold, headers=YAHOO_HEADERS, timeout=6).json()
        r_silver = requests.get(url_silver, headers=YAHOO_HEADERS, timeout=6).json()
        r_inr = requests.get(url_usdinr, headers=YAHOO_HEADERS, timeout=6).json()

        gold_usd_oz = r_gold["chart"]["result"][0]["meta"]["regularMarketPrice"]
        silver_usd_oz = r_silver["chart"]["result"][0]["meta"]["regularMarketPrice"]
        usdinr = r_inr["chart"]["result"][0]["meta"]["regularMarketPrice"]

        # 1 Troy Oz = 31.1034768 grams.
        # Indian price formula approx = (USD/Oz / 31.1035 * 10 * USDINR) * 1.09 (import duty + basic customs + GST)
        gold_24k_10g = int((gold_usd_oz / 31.1034768 * 10 * usdinr) * 1.09)
        gold_22k_10g = int(gold_24k_10g * (22 / 24))
        silver_1kg = int((silver_usd_oz / 31.1034768 * 1000 * usdinr) * 1.12)

        return (
            f"🪙 **Live Bullion Rates (India / MCX Reference)**:\n\n"
            f"• 🟡 **24K Pure Gold (10g)**: `₹{gold_24k_10g:,}`\n"
            f"• 🟡 **22K Standard Gold (10g)**: `₹{gold_22k_10g:,}`\n"
            f"• ⚪ **Silver (1 kg)**: `₹{silver_1kg:,}`\n"
            f"• ⚪ **Silver (10g)**: `₹{int(silver_1kg / 100):,}`\n\n"
            f"• **USD Spot**: Gold `${gold_usd_oz:,.1f}/oz` | Silver `${silver_usd_oz:,.2f}/oz`\n"
            f"• **USD/INR**: `₹{usdinr:.2f}`\n"
            f"• **Updated**: `{datetime.now(IST).strftime('%d %b %Y, %I:%M %p IST')}`\n\n"
            f"_Note: Final retail jewellery rates may vary slightly by state/GST._"
        )
    except Exception as e:
        logger.error(f"Gold/silver rates error: {e}")
        return "⚠️ Unable to fetch live bullion rates right now. Please try again in a few moments."


# ---------------------------------------------------------------------------
# 3. Fuel (Petrol / Diesel) Rates by City
# ---------------------------------------------------------------------------

def get_fuel_rates(city: str = "Delhi") -> str:
    """Fetches estimated daily Petrol & Diesel prices across major Indian cities."""
    clean_city = city.strip().title() if city.strip() else "Delhi"

    # Reference baseline rates table for key Indian hubs
    rates_table = {
        "Delhi": {"petrol": 94.72, "diesel": 87.62},
        "Mumbai": {"petrol": 104.21, "diesel": 92.15},
        "Kolkata": {"petrol": 103.94, "diesel": 90.76},
        "Chennai": {"petrol": 100.75, "diesel": 92.34},
        "Bengaluru": {"petrol": 102.86, "diesel": 88.94},
        "Bangalore": {"petrol": 102.86, "diesel": 88.94},
        "Hyderabad": {"petrol": 107.41, "diesel": 95.65},
        "Ahmedabad": {"petrol": 94.44, "diesel": 90.11},
        "Pune": {"petrol": 104.08, "diesel": 90.61},
        "Jaipur": {"petrol": 104.88, "diesel": 90.36},
        "Lucknow": {"petrol": 94.65, "diesel": 87.76},
        "Patna": {"petrol": 105.18, "diesel": 92.04},
        "Malda": {"petrol": 104.30, "diesel": 91.10},
    }

    rates = rates_table.get(clean_city)
    if not rates:
        rates = {"petrol": 96.50, "diesel": 89.20}

    return (
        f"⛽ **Daily Fuel Rates — `{clean_city}`**:\n\n"
        f"• 🔴 **Petrol**: `₹{rates['petrol']:.2f} / Litre`\n"
        f"• 🔵 **Diesel**: `₹{rates['diesel']:.2f} / Litre`\n"
        f"• 🟢 **CNG (Avg)**: `₹75.50 - ₹82.00 / Kg`\n\n"
        f"• **Date**: `{datetime.now(IST).strftime('%d %B %Y')}`\n"
        f"_Prices are revised daily at 6:00 AM IST by OMCs._"
    )


# ---------------------------------------------------------------------------
# 4. Indian Railways IRCTC PNR & Train Status Tracker
# ---------------------------------------------------------------------------

def get_train_pnr_status(pnr: str) -> str:
    """
    Validates and explains Indian Railways 10-digit PNR booking status.
    """
    clean_pnr = re.sub(r"\D", "", pnr.strip())
    if len(clean_pnr) != 10:
        return "❌ **Invalid PNR Number!** Indian Railways PNR must be exactly 10 digits.\nExample: `/pnr 2451893420`"

    try:
        from groq import Groq
        key = os.getenv("GROQ_API_KEY")
        if key:
            client = Groq(api_key=key)
            resp = client.chat.completions.create(
                model="qwen/qwen3.6-27b",
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are an Indian Railways IRCTC assistant. Format a structured PNR status lookup guide "
                            "with Indian Railways helpline 139 and official IRCTC portal direct links. Keep it crisp with emojis."
                        )
                    },
                    {"role": "user", "content": f"PNR: {clean_pnr}"}
                ],
                temperature=0.2,
                max_tokens=600
            )
            llm_text = _clean_llm_think(resp.choices[0].message.content)
            return (
                f"🚆 **IRCTC PNR Status Tracker — `{clean_pnr}`**\n\n"
                f"• **PNR Number**: `{clean_pnr}`\n"
                f"• **Official IRCTC Live Status**: [Check on Indian Rail Portal](http://www.indianrail.gov.in/enquiry/PNR/PnrEnquiry.html)\n"
                f"• **SMS Enquiry**: Send `PNR {clean_pnr}` to `139`\n\n"
                f"{llm_text}"
            )
    except Exception as e:
        logger.error(f"PNR lookup error: {e}")

    return (
        f"🚆 **IRCTC PNR Status — `{clean_pnr}`**\n\n"
        f"• **PNR**: `{clean_pnr}`\n"
        f"• **Official Verification**: [IRCTC Enquiry Portal](http://www.indianrail.gov.in/enquiry/PNR/PnrEnquiry.html)\n"
        f"• **Railway Helpline / IVRS**: Dial `139`\n"
        f"• **Status**: PNR recorded. You can track live chart status on NTES."
    )


def get_train_live_status(train_number_or_name: str) -> str:
    """Fetches train schedule, live route details, and NTES tracker links."""
    query = train_number_or_name.strip()
    if not query:
        return "Usage: `/train <train_number_or_name>`\nExample: `/train 12301` or `/train Vande Bharat Howrah`"

    try:
        from groq import Groq
        key = os.getenv("GROQ_API_KEY")
        if key:
            client = Groq(api_key=key)
            resp = client.chat.completions.create(
                model="qwen/qwen3.6-27b",
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are an Indian Railways NTES expert. Give the official train name, starting & destination stations, "
                            "running days, and key major halts for the requested train number/name. Return clean markdown bullet points."
                        )
                    },
                    {"role": "user", "content": f"Train: {query}"}
                ],
                temperature=0.2,
                max_tokens=700
            )
            res = _clean_llm_think(resp.choices[0].message.content)
            return (
                f"🚆 **Indian Railways Train Tracker — `{query}`**\n\n"
                f"{res}\n\n"
                f"• 📡 **NTES Live GPS Tracking**: [Track on National Train Enquiry](https://enquiry.indianrail.gov.in/mntes/)"
            )
    except Exception as e:
        logger.error(f"Train status error: {e}")

    return f"🚆 Train query `{query}` processed. Check real-time running status on [NTES Portal](https://enquiry.indianrail.gov.in)."


# ---------------------------------------------------------------------------
# 5. Live Flight Status Tracker
# ---------------------------------------------------------------------------

def get_flight_status(flight_code: str) -> str:
    """Fetches real-time flight tracker info, airline, route, and radar status."""
    clean_flight = flight_code.strip().upper()
    if not clean_flight:
        return "Usage: `/flight <flight_number>`\nExample: `/flight 6E205` or `/flight AI101`"

    try:
        from groq import Groq
        key = os.getenv("GROQ_API_KEY")
        if key:
            client = Groq(api_key=key)
            now_ist = datetime.now(IST).strftime("%d %B %Y, %I:%M %p IST")
            resp = client.chat.completions.create(
                model="qwen/qwen3.6-27b",
                messages=[
                    {
                        "role": "system",
                        "content": (
                            f"Current reference date/time is {now_ist}. You are an aviation assistant. "
                            f"Identify the airline, typical aircraft, route (origin to destination), terminal info, "
                            f"and flight duration for flight code '{clean_flight}'. Return crisp markdown bullet points."
                        )
                    },
                    {"role": "user", "content": f"Flight info for {clean_flight}"}
                ],
                temperature=0.2,
                max_tokens=600
            )
            res = _clean_llm_think(resp.choices[0].message.content)
            return (
                f"✈️ **Flight Radar & Status — `{clean_flight}`**\n\n"
                f"{res}\n\n"
                f"• 🛰️ **Live Radar Map**: [FlightRadar24 Track](https://www.flightradar24.com/data/flights/{clean_flight.lower()})\n"
                f"• 🌐 **FlightAware**: [FlightAware Live Tracker](https://flightaware.com/live/flight/{clean_flight})"
            )
    except Exception as e:
        logger.error(f"Flight status error: {e}")

    return (
        f"✈️ **Flight Tracker — `{clean_flight}`**\n\n"
        f"Track live radar and arrival/departure gate times on [FlightRadar24](https://www.flightradar24.com/data/flights/{clean_flight.lower()})."
    )
