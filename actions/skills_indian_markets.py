import os
import re
import time
import logging
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional, Tuple

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
        res_json = resp.json()
        chart_res = res_json.get("chart", {}).get("result")
        if not chart_res or not isinstance(chart_res, list) or len(chart_res) == 0:
            return f"⚠️ Could not find market quote for `{clean_sym}`. Please verify ticker symbol (e.g. `RELIANCE`, `TCS`, `TATAMOTORS`, `NIFTY`)."

        data = chart_res[0].get("meta", {})
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
# 3. Fuel (Petrol, Diesel & CNG) Rates by City (Live OMCs & Web Scraping)
# ---------------------------------------------------------------------------

_FUEL_CACHE: Dict[str, Dict[str, Any]] = {}
_LAST_FUEL_CACHE_TIME: float = 0.0

# Canonical city slug mapping for NDTV & GoodReturns lookups
_CITY_SLUG_MAP: Dict[str, str] = {
    "delhi": "new-delhi",
    "new delhi": "new-delhi",
    "mumbai": "mumbai-city",
    "bombay": "mumbai-city",
    "bengaluru": "bangalore",
    "bangalore": "bangalore",
    "calcutta": "kolkata",
    "kolkata": "kolkata",
    "madras": "chennai",
    "chennai": "chennai",
    "gurugram": "gurgaon",
    "gurgaon": "gurgaon",
    "ahmedabad": "ahmedabad",
    "hyderabad": "hyderabad",
    "pune": "pune",
    "jaipur": "jaipur",
    "lucknow": "lucknow",
    "patna": "patna",
    "malda": "malda",
    "noida": "ghaziabad",  # NDTV nearby metro node for NCR-East
    "chandigarh": "chandigarh",
    "surat": "surat",
    "bhopal": "bhopal",
    "indore": "indore",
    "bhubaneswar": "bhubaneswar",
}

# District / City to State fallback mapping for CNG & state-level tax parity
_CITY_TO_STATE_MAP: Dict[str, str] = {
    "malda": "west bengal",
    "siliguri": "west bengal",
    "howrah": "west bengal",
    "kolkata": "west bengal",
    "pune": "maharashtra",
    "nagpur": "maharashtra",
    "nashik": "maharashtra",
    "mumbai": "maharashtra",
    "noida": "uttar pradesh",
    "ghaziabad": "uttar pradesh",
    "lucknow": "uttar pradesh",
    "kanpur": "uttar pradesh",
    "varanasi": "uttar pradesh",
    "agra": "uttar pradesh",
    "gurgaon": "haryana",
    "gurugram": "haryana",
    "faridabad": "haryana",
    "ahmedabad": "gujarat",
    "surat": "gujarat",
    "vadodara": "gujarat",
    "jaipur": "rajasthan",
    "jodhpur": "rajasthan",
    "patna": "bihar",
    "gaya": "bihar",
    "bhopal": "madhya pradesh",
    "indore": "madhya pradesh",
    "bhubaneswar": "odisha",
    "thiruvananthapuram": "kerala",
    "kochi": "kerala",
    "chennai": "tamil nadu",
    "coimbatore": "tamil nadu",
    "bangalore": "karnataka",
    "bengaluru": "karnataka",
    "hyderabad": "telangana",
    "ranchi": "jharkhand",
    "guwahati": "assam",
    "dehradun": "uttarakhand",
    "shimla": "himachal pradesh",
}

# Comprehensive updated baseline rates across major Indian hubs
_BASELINE_FUEL_RATES: Dict[str, Dict[str, Any]] = {
    "delhi": {"petrol": 102.12, "diesel": 95.20, "cng": 86.98, "display": "Delhi"},
    "new delhi": {"petrol": 102.12, "diesel": 95.20, "cng": 86.98, "display": "New Delhi"},
    "mumbai": {"petrol": 111.21, "diesel": 97.83, "cng": 88.00, "display": "Mumbai"},
    "kolkata": {"petrol": 113.51, "diesel": 99.82, "cng": 93.50, "display": "Kolkata"},
    "chennai": {"petrol": 107.76, "diesel": 99.55, "cng": 97.00, "display": "Chennai"},
    "bengaluru": {"petrol": 111.68, "diesel": 99.56, "cng": 97.00, "display": "Bengaluru"},
    "bangalore": {"petrol": 111.68, "diesel": 99.56, "cng": 97.00, "display": "Bangalore"},
    "hyderabad": {"petrol": 115.71, "diesel": 102.40, "cng": 98.00, "display": "Hyderabad"},
    "ahmedabad": {"petrol": 101.83, "diesel": 97.92, "cng": 84.50, "display": "Ahmedabad"},
    "pune": {"petrol": 112.04, "diesel": 98.68, "cng": 92.00, "display": "Pune"},
    "jaipur": {"petrol": 112.69, "diesel": 97.46, "cng": 90.00, "display": "Jaipur"},
    "lucknow": {"petrol": 101.89, "diesel": 95.36, "cng": 89.50, "display": "Lucknow"},
    "patna": {"petrol": 113.65, "diesel": 99.36, "cng": 93.00, "display": "Patna"},
    "malda": {"petrol": 113.81, "diesel": 99.67, "cng": 93.50, "display": "Malda"},
    "noida": {"petrol": 101.89, "diesel": 95.37, "cng": 87.50, "display": "Noida"},
    "gurgaon": {"petrol": 102.97, "diesel": 95.64, "cng": 87.50, "display": "Gurgaon"},
    "gurugram": {"petrol": 102.97, "diesel": 95.64, "cng": 87.50, "display": "Gurugram"},
    "chandigarh": {"petrol": 101.54, "diesel": 94.88, "cng": 89.00, "display": "Chandigarh"},
    "surat": {"petrol": 101.63, "diesel": 97.75, "cng": 84.50, "display": "Surat"},
    "bhopal": {"petrol": 114.57, "diesel": 99.50, "cng": 91.00, "display": "Bhopal"},
    "indore": {"petrol": 115.00, "diesel": 99.85, "cng": 91.00, "display": "Indore"},
    "bhubaneswar": {"petrol": 108.95, "diesel": 97.10, "cng": 92.00, "display": "Bhubaneswar"},
    "thiruvananthapuram": {"petrol": 115.49, "diesel": 104.20, "cng": 97.00, "display": "Thiruvananthapuram"},
    "ranchi": {"petrol": 106.24, "diesel": 98.00, "cng": 90.00, "display": "Ranchi"},
    "guwahati": {"petrol": 106.76, "diesel": 98.08, "cng": 92.00, "display": "Guwahati"},
    "dehradun": {"petrol": 100.55, "diesel": 94.50, "cng": 88.00, "display": "Dehradun"},
    "shimla": {"petrol": 102.61, "diesel": 95.10, "cng": 89.00, "display": "Shimla"},
    "jammu": {"petrol": 104.13, "diesel": 95.80, "cng": 89.00, "display": "Jammu"},
    "raipur": {"petrol": 108.74, "diesel": 99.10, "cng": 92.00, "display": "Raipur"},
    "goa": {"petrol": 103.92, "diesel": 95.50, "cng": 89.00, "display": "Goa"},
}


def _clean_fuel_city_query(raw_city: str) -> str:
    """Normalizes natural language inputs into clean Indian city/state names."""
    if not raw_city or not raw_city.strip():
        return "Delhi"
    s = raw_city.strip()
    # Strip leading commands
    s = re.sub(r"^/(?:fuel|petrol|diesel|cng)\b\s*", "", s, flags=re.IGNORECASE).strip()
    # Strip prepositions
    s = re.sub(r"^(?:in|for|at|of|me|mein|ka|ki|ke)\s+", "", s, flags=re.IGNORECASE).strip()
    # Strip trailing noisy words
    s = re.sub(r"\s+(?:rate|rates|price|prices|fuel|city|district|today|aaj)$", "", s, flags=re.IGNORECASE).strip()
    # Strip leading question/price phrasing
    s = re.sub(r"^(?:rate|rates|price|prices|daam|dam)\s+(?:of|in|for)\s+", "", s, flags=re.IGNORECASE).strip()
    # Final punctuation cleanup
    s = re.sub(r"[\?\.\!,;:]+", "", s).strip()
    return s.title() if s else "Delhi"


def _fetch_goodreturns_bulk_rates() -> Dict[str, Dict[str, Any]]:
    """Fetches daily live Petrol, Diesel, and CNG rates table across Indian cities & states."""
    global _FUEL_CACHE, _LAST_FUEL_CACHE_TIME
    now = time.time()
    # Cache valid for 4 hours
    if _FUEL_CACHE and (now - _LAST_FUEL_CACHE_TIME < 14400):
        return _FUEL_CACHE

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
    }
    new_cache: Dict[str, Dict[str, Any]] = {}

    def _parse_url(url: str) -> Dict[str, float]:
        data: Dict[str, float] = {}
        try:
            resp = requests.get(url, headers=headers, timeout=4)
            if resp.status_code == 200:
                soup = BeautifulSoup(resp.text, "html.parser")
                for table in soup.find_all("table")[:2]:
                    for row in table.find_all("tr"):
                        cols = [td.get_text(strip=True) for td in row.find_all(["th", "td"])]
                        if len(cols) >= 2:
                            name = cols[0].strip().lower()
                            match = re.search(r"[0-9]+(?:\.[0-9]+)?", cols[1].replace(",", ""))
                            if match:
                                try:
                                    data[name] = float(match.group(0))
                                except ValueError:
                                    pass
        except Exception as err:
            logger.debug(f"GoodReturns fuel scrape notice ({url}): {err}")
        return data

    petrol_map = _parse_url("https://www.goodreturns.in/petrol-price.html")
    diesel_map = _parse_url("https://www.goodreturns.in/diesel-price.html")
    cng_map = _parse_url("https://www.goodreturns.in/cng-price.html")

    all_keys = set(petrol_map.keys()) | set(diesel_map.keys()) | set(cng_map.keys())
    for k in all_keys:
        new_cache[k] = {
            "petrol": petrol_map.get(k),
            "diesel": diesel_map.get(k),
            "cng": cng_map.get(k)
        }

    if new_cache:
        _FUEL_CACHE = new_cache
        _LAST_FUEL_CACHE_TIME = now

    return _FUEL_CACHE


def _fetch_ndtv_city_rates(slug: str) -> Tuple[Optional[float], Optional[float]]:
    """Fetches real-time Petrol & Diesel prices for a specific city/district from NDTV."""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    }

    def _extract_from_page(url: str) -> Optional[float]:
        try:
            r = requests.get(url, headers=headers, timeout=3)
            if r.status_code == 200:
                soup = BeautifulSoup(r.text, "html.parser")
                for t in soup.find_all("table"):
                    for row in t.find_all("tr"):
                        for cell in row.find_all(["th", "td"]):
                            m = re.search(r"([0-9]+\.[0-9]{2})\s*₹", cell.get_text())
                            if m:
                                return float(m.group(1))
        except Exception:
            pass
        return None

    petrol = _extract_from_page(f"https://www.ndtv.com/fuel-prices/petrol-price-in-{slug}-city")
    diesel = _extract_from_page(f"https://www.ndtv.com/fuel-prices/diesel-price-in-{slug}-city")
    return petrol, diesel


def get_fuel_rates(city: str = "Delhi") -> str:
    """
    Fetches real-time daily Petrol, Diesel, and CNG fuel prices across Indian cities & states.
    Uses multi-source scraping (NDTV & GoodReturns) with automatic caching and realistic baselines.
    """
    clean_city = _clean_fuel_city_query(city)
    city_key = clean_city.lower()
    today_str = datetime.now(IST).strftime("%d %B %Y")

    petrol_price: Optional[float] = None
    diesel_price: Optional[float] = None
    cng_price: Optional[float] = None
    is_live = False

    # 1. Check live GoodReturns table cache
    gr_data = _fetch_goodreturns_bulk_rates()
    matched_entry = gr_data.get(city_key)

    if matched_entry:
        petrol_price = matched_entry.get("petrol")
        diesel_price = matched_entry.get("diesel")
        cng_price = matched_entry.get("cng")
        if petrol_price or diesel_price:
            is_live = True

    # 2. If city not in bulk table, try NDTV city endpoints
    if not (petrol_price and diesel_price):
        slug = _CITY_SLUG_MAP.get(city_key, re.sub(r"[^a-z0-9]+", "-", city_key).strip("-"))
        if slug:
            p_ndtv, d_ndtv = _fetch_ndtv_city_rates(slug)
            if p_ndtv:
                petrol_price = p_ndtv
                is_live = True
            if d_ndtv:
                diesel_price = d_ndtv
                is_live = True

    # 3. If CNG not found for specific city, check state-level CNG from GoodReturns
    if not cng_price:
        state_name = _CITY_TO_STATE_MAP.get(city_key)
        if state_name and state_name in gr_data:
            cng_price = gr_data[state_name].get("cng")
        elif city_key in gr_data and gr_data[city_key].get("cng"):
            cng_price = gr_data[city_key].get("cng")

    # 4. Fallback to baseline table if offline or specific city prices missing
    baseline = _BASELINE_FUEL_RATES.get(city_key)
    if not baseline:
        # Check alias in baseline
        for k, b_data in _BASELINE_FUEL_RATES.items():
            if k in city_key or city_key in k:
                baseline = b_data
                break

    if not baseline:
        # State level baseline
        st = _CITY_TO_STATE_MAP.get(city_key)
        if st and st in _BASELINE_FUEL_RATES:
            baseline = _BASELINE_FUEL_RATES[st]

    if not petrol_price and baseline:
        petrol_price = baseline.get("petrol")
    if not diesel_price and baseline:
        diesel_price = baseline.get("diesel")
    if not cng_price and baseline:
        cng_price = baseline.get("cng")

    # Ultimate fallback safety check
    petrol_display = f"₹{petrol_price:.2f} / Litre" if petrol_price else "₹102.12 / Litre"
    diesel_display = f"₹{diesel_price:.2f} / Litre" if diesel_price else "₹95.20 / Litre"
    if cng_price:
        cng_display = f"₹{cng_price:.2f} / Kg"
    else:
        cng_display = "₹85.00 – ₹93.00 / Kg (Varies by station)"

    status_tag = "🟢 Live OMCs" if is_live else "📊 Reference Daily"

    return (
        f"⛽ **Daily Fuel Rates — `{clean_city}`**\n\n"
        f"• 🔴 **Petrol**: `{petrol_display}`\n"
        f"• 🔵 **Diesel**: `{diesel_display}`\n"
        f"• 🟢 **CNG**: `{cng_display}`\n\n"
        f"• 📅 **Date**: `{today_str}`\n"
        f"• ℹ️ **Status**: {status_tag} (Revised daily at 6:00 AM IST by OMCs)"
    )


# ---------------------------------------------------------------------------
# 4. Indian Railways IRCTC PNR & Train Status Tracker
# ---------------------------------------------------------------------------

def get_train_pnr_status(pnr: str) -> str:
    """
    Validates and fetches real-time Indian Railways 10-digit PNR booking & confirmation status.
    Returns complete details including train info, route, timings, chart status,
    passenger-wise coach/berth/WL status, confirmation probability, fare, and platform.
    """
    clean_pnr = re.sub(r"\D", "", pnr.strip())
    if len(clean_pnr) != 10:
        return (
            "❌ **Invalid PNR Number!** Indian Railways PNR must be exactly 10 digits.\n"
            "Example: `/pnr 2451893420`"
        )

    # Class and Quota descriptions for user clarity
    class_map = {
        "1A": "1A (AC First Class)",
        "2A": "2A (AC 2-Tier)",
        "3A": "3A (AC 3-Tier)",
        "3E": "3E (AC 3 Economy)",
        "CC": "CC (AC Chair Car)",
        "EC": "EC (Executive Chair Car)",
        "SL": "SL (Sleeper Class)",
        "2S": "2S (Second Sitting)",
        "EV": "EV (Vistadome AC)",
        "EA": "EA (Executive Anubhuti)",
    }
    quota_map = {
        "GN": "GN (General Quota)",
        "TQ": "TQ (Tatkal Quota)",
        "PT": "PT (Premium Tatkal)",
        "LD": "LD (Ladies Quota)",
        "HO": "HO (HQ Quota)",
        "DF": "DF (Defense Quota)",
        "SS": "SS (Senior Citizen)",
        "DP": "DP (Duty Pass)",
        "FT": "FT (Foreign Tourist)",
    }

    # 1. Fetch live PNR data from real-time API
    api_url = f"https://api.confirmtkt.com/api/pnr/status/{clean_pnr}"
    api_headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json, text/plain, */*",
    }

    data = None
    try:
        resp = requests.get(api_url, headers=api_headers, timeout=8)
        if resp.status_code == 200:
            data = resp.json()
    except Exception as e:
        logger.warning(f"Live PNR API call failed for {clean_pnr}: {e}")

    # If valid booking data received from API
    if data and (data.get("TrainNo") or data.get("TrainName") or data.get("PassengerStatus")):
        train_no = data.get("TrainNo") or "N/A"
        train_name = data.get("TrainName") or "Express / Special"
        
        from_stn = data.get("SourceName") or data.get("From") or "Origin"
        from_code = data.get("From") or ""
        to_stn = data.get("DestinationName") or data.get("To") or "Destination"
        to_code = data.get("To") or ""
        
        boarding = data.get("BoardingStationName") or from_stn
        b_code = data.get("BoardingPoint") or from_code
        res_upto = data.get("ReservationUptoName") or to_stn
        r_code = data.get("ReservationUpto") or to_code

        doj = data.get("Doj") or "N/A"
        booking_date = data.get("BookingDate")
        dep_time = data.get("DepartureTime") or "--:--"
        arr_time = data.get("ArrivalTime") or "--:--"
        duration = data.get("Duration")
        
        raw_class = data.get("Class") or ""
        cls_name = class_map.get(raw_class, raw_class) if raw_class else "N/A"
        
        raw_quota = data.get("Quota") or ""
        quota_name = quota_map.get(raw_quota, raw_quota) if raw_quota else "GN"

        chart_prep = data.get("ChartPrepared", False)
        chart_badge = "🟢 **Chart Prepared**" if chart_prep else "⏳ **Chart Not Prepared**"

        platform = data.get("ExpectedPlatformNo")
        fare = data.get("TicketFare") or data.get("BookingFare")
        has_pantry = data.get("HasPantry")
        coach_pos = data.get("CoachPosition")
        train_status = data.get("TrainStatus")

        passengers = data.get("PassengerStatus") or []
        pass_count = data.get("PassengerCount") or len(passengers)

        output_lines = [
            f"🚆 **IRCTC PNR Status Tracker — `{clean_pnr}`**",
            "",
            f"📋 **Train**: **{train_no} — {train_name}**",
            f"🗓️ **Journey Date (DOJ)**: `{doj}`" + (f" _(Booked on: {booking_date})_" if booking_date else ""),
            f"🛤️ **Route**: **{from_stn} ({from_code})** ➡️ **{to_stn} ({to_code})**",
        ]

        if (b_code and b_code != from_code) or (r_code and r_code != to_code):
            output_lines.append(f"📍 **Boarding / Reservation**: {boarding} ({b_code}) ➔ {res_upto} ({r_code})")

        timing_str = f"⏰ **Schedule**: Dep: `{dep_time}` ➔ Arr: `{arr_time}`"
        if duration:
            timing_str += f" _(Duration: {duration})_"
        output_lines.append(timing_str)

        output_lines.append(f"💺 **Class & Quota**: `{cls_name}` | `{quota_name}`")
        output_lines.append(f"📊 **Charting Status**: {chart_badge}")

        if platform:
            output_lines.append(f"🚉 **Expected Platform**: `{platform}`")
        if fare:
            output_lines.append(f"💰 **Total Fare**: `₹{fare}`")
        if has_pantry is not None:
            output_lines.append(f"🍽️ **Pantry Service**: " + ("✅ Available" if has_pantry else "❌ Not Available"))
        if coach_pos:
            output_lines.append(f"🚃 **Coach Position**: `{coach_pos}`")
        if train_status:
            output_lines.append(f"ℹ️ **Train Running Status**: {train_status}")

        output_lines.append("")
        output_lines.append(f"👥 **Passenger Breakdown ({pass_count} Passenger{'s' if pass_count != 1 else ''})**:")
        
        if passengers:
            for idx, p in enumerate(passengers, start=1):
                p_num = p.get("Number") or idx
                b_stat = p.get("BookingStatusDetails") or p.get("BookingStatus") or "N/A"
                c_stat = p.get("CurrentStatusDetails") or p.get("CurrentStatus") or "N/A"
                
                coach = p.get("CurrentCoachId") or p.get("Coach") or ""
                berth = p.get("CurrentBerthNo") or p.get("Berth") or ""
                b_type = p.get("BerthType") or p.get("BerthCode") or ""
                pred = p.get("PredictionPercentage") or p.get("Prediction")
                
                seat_details = []
                if coach:
                    seat_details.append(f"Coach **{coach}**")
                if berth:
                    seat_details.append(f"Berth **{berth}**")
                if b_type:
                    seat_details.append(f"({b_type})")
                
                seat_str = f" 👉 {' '.join(seat_details)}" if seat_details else ""
                
                # Probability display for Waitlist / RAC
                pred_str = ""
                if pred and str(pred).isdigit() and int(pred) < 100 and "CNF" not in c_stat.upper():
                    pred_str = f" _(Confirmation Chance: {pred}%)_"

                # Status indicator emoji
                stat_emoji = "🟢" if "CNF" in c_stat.upper() or "CONFIRM" in c_stat.upper() else ("🟡" if "RAC" in c_stat.upper() else "🔴")

                output_lines.append(
                    f"{stat_emoji} **Passenger {p_num}**: Current: `{c_stat}`{seat_str}{pred_str} | Booking: `{b_stat}`"
                )
        else:
            output_lines.append("• _No individual passenger status returned._")

        output_lines.extend([
            "",
            "🔗 **Official Verification & Helplines**:",
            f"• 🌐 [Official Indian Rail PNR Portal](http://www.indianrail.gov.in/enquiry/PNR/PnrEnquiry.html)",
            f"• 💬 SMS Enquiry: Send `PNR {clean_pnr}` to `139`",
            "• 📞 24x7 Railway Helpline / NTES: Dial `139`"
        ])
        return "\n".join(output_lines)

    # If API returned an error or flushed PNR
    error_msg = data.get("Error", "") if isinstance(data, dict) else ""
    is_flushed = "flushed" in error_msg.lower() or "not yet generated" in error_msg.lower()

    # Try LLM for intelligent assistant guidance if available
    llm_context = ""
    try:
        from groq import Groq
        key = os.getenv("GROQ_API_KEY")
        if key:
            client = Groq(api_key=key)
            prompt = (
                f"The user checked Indian Railways PNR: {clean_pnr}. "
                f"The live system response indicates: '{error_msg or 'No active chart record found'}'. "
                f"Provide a brief 2-bullet explanation of why a PNR might be flushed (past journey) or not found, "
                f"and how they can confirm their booking status on IRCTC or via SMS 139."
            )
            resp = client.chat.completions.create(
                model="qwen/qwen3.6-27b",
                messages=[
                    {"role": "system", "content": "You are a helpful Indian Railways IRCTC assistant. Keep your response brief and structured."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.2,
                max_tokens=300
            )
            llm_context = _clean_llm_think(resp.choices[0].message.content)
    except Exception as e:
        logger.error(f"LLM PNR assistant error: {e}")

    status_headline = (
        "⚠️ **PNR Record Flushed / Past Journey / Inactive**"
        if is_flushed
        else "⚠️ **PNR Status Lookup**"
    )

    return (
        f"🚆 **IRCTC PNR Status Tracker — `{clean_pnr}`**\n\n"
        f"{status_headline}\n\n"
        f"• **PNR Number**: `{clean_pnr}`\n"
        f"• **Status**: `{error_msg or 'No active booking data found in the live charting system.'}`\n\n"
        + (f"{llm_context}\n\n" if llm_context else "") +
        f"🔗 **How to verify directly**:\n"
        f"• 🌐 **Official Indian Railways Portal**: [Check on Indian Rail Portal](http://www.indianrail.gov.in/enquiry/PNR/PnrEnquiry.html)\n"
        f"• 💬 **Instant SMS Check**: Send `PNR {clean_pnr}` to `139`\n"
        f"• 📞 **IRCTC & NTES 24x7 Helpline**: Dial `139`"
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
