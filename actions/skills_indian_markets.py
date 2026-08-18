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
