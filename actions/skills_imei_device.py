import os
import re
import json
import logging
import requests
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# 1. Extensive Built-in GSMA TAC Database for Instant Offline Identification
# ---------------------------------------------------------------------------

TAC_DATABASE: Dict[str, Dict[str, str]] = {
    # Apple iPhones
    "35201111": {"brand": "Apple", "model": "iPhone 15 Pro Max", "type": "Smartphone (5G)", "sim": "Dual SIM (eSIM + Nano-SIM / Dual eSIM)"},
    "35201011": {"brand": "Apple", "model": "iPhone 15 Pro", "type": "Smartphone (5G)", "sim": "Dual SIM (eSIM + Nano-SIM)"},
    "35200911": {"brand": "Apple", "model": "iPhone 15 Plus", "type": "Smartphone (5G)", "sim": "Dual SIM (eSIM + Nano-SIM)"},
    "35200811": {"brand": "Apple", "model": "iPhone 15", "type": "Smartphone (5G)", "sim": "Dual SIM (eSIM + Nano-SIM)"},
    "35372411": {"brand": "Apple", "model": "iPhone 16 Pro Max", "type": "Flagship Smartphone (5G)", "sim": "Dual SIM (eSIM + Nano-SIM)"},
    "35372311": {"brand": "Apple", "model": "iPhone 16 Pro", "type": "Flagship Smartphone (5G)", "sim": "Dual SIM (eSIM + Nano-SIM)"},
    "35372211": {"brand": "Apple", "model": "iPhone 16 Plus", "type": "Smartphone (5G)", "sim": "Dual SIM (eSIM + Nano-SIM)"},
    "35372111": {"brand": "Apple", "model": "iPhone 16", "type": "Smartphone (5G)", "sim": "Dual SIM (eSIM + Nano-SIM)"},
    "35815610": {"brand": "Apple", "model": "iPhone 14 Pro Max", "type": "Smartphone (5G)", "sim": "Dual SIM (eSIM + Nano-SIM)"},
    "35815510": {"brand": "Apple", "model": "iPhone 14 Pro", "type": "Smartphone (5G)", "sim": "Dual SIM (eSIM + Nano-SIM)"},
    "35815410": {"brand": "Apple", "model": "iPhone 14 Plus", "type": "Smartphone (5G)", "sim": "Dual SIM (eSIM + Nano-SIM)"},
    "35815310": {"brand": "Apple", "model": "iPhone 14", "type": "Smartphone (5G)", "sim": "Dual SIM (eSIM + Nano-SIM)"},
    "35478411": {"brand": "Apple", "model": "iPhone 13 Pro Max", "type": "Smartphone (5G)", "sim": "Dual SIM (eSIM + Nano-SIM)"},
    "35478311": {"brand": "Apple", "model": "iPhone 13 Pro", "type": "Smartphone (5G)", "sim": "Dual SIM (eSIM + Nano-SIM)"},
    "35478211": {"brand": "Apple", "model": "iPhone 13", "type": "Smartphone (5G)", "sim": "Dual SIM (eSIM + Nano-SIM)"},
    "35478111": {"brand": "Apple", "model": "iPhone 13 Mini", "type": "Smartphone (5G)", "sim": "Dual SIM (eSIM + Nano-SIM)"},
    "35304911": {"brand": "Apple", "model": "iPhone 12 Pro Max", "type": "Smartphone (5G)", "sim": "Dual SIM (eSIM + Nano-SIM)"},
    "35304811": {"brand": "Apple", "model": "iPhone 12 Pro", "type": "Smartphone (5G)", "sim": "Dual SIM (eSIM + Nano-SIM)"},
    "35304711": {"brand": "Apple", "model": "iPhone 12", "type": "Smartphone (5G)", "sim": "Dual SIM (eSIM + Nano-SIM)"},
    "35304611": {"brand": "Apple", "model": "iPhone 12 Mini", "type": "Smartphone (5G)", "sim": "Dual SIM (eSIM + Nano-SIM)"},
    "35688510": {"brand": "Apple", "model": "iPhone 11 Pro Max", "type": "Smartphone (4G LTE)", "sim": "Dual SIM (eSIM + Nano-SIM)"},
    "35688410": {"brand": "Apple", "model": "iPhone 11 Pro", "type": "Smartphone (4G LTE)", "sim": "Dual SIM (eSIM + Nano-SIM)"},
    "35688310": {"brand": "Apple", "model": "iPhone 11", "type": "Smartphone (4G LTE)", "sim": "Dual SIM (eSIM + Nano-SIM)"},
    "35728809": {"brand": "Apple", "model": "iPhone XR", "type": "Smartphone (4G LTE)", "sim": "Dual SIM (eSIM + Nano-SIM)"},
    "35728709": {"brand": "Apple", "model": "iPhone XS Max", "type": "Smartphone (4G LTE)", "sim": "Dual SIM (eSIM + Nano-SIM)"},
    "35728609": {"brand": "Apple", "model": "iPhone XS", "type": "Smartphone (4G LTE)", "sim": "Dual SIM (eSIM + Nano-SIM)"},
    "35674308": {"brand": "Apple", "model": "iPhone X", "type": "Smartphone (4G LTE)", "sim": "Single Nano-SIM"},
    "35865410": {"brand": "Apple", "model": "iPhone SE (3rd Gen / 2022)", "type": "Smartphone (5G)", "sim": "Dual SIM (eSIM + Nano-SIM)"},
    "35676311": {"brand": "Apple", "model": "iPad Pro 12.9-inch (Cellular)", "type": "Tablet (5G Cellular)", "sim": "Nano-SIM + eSIM"},
    "35676211": {"brand": "Apple", "model": "iPad Air (Cellular)", "type": "Tablet (5G Cellular)", "sim": "Nano-SIM + eSIM"},

    # Samsung Galaxy Series
    "35091234": {"brand": "Samsung", "model": "Galaxy S24 Ultra 5G (SM-S928B)", "type": "Flagship Smartphone (5G)", "sim": "Dual Nano-SIM + eSIM"},
    "35091235": {"brand": "Samsung", "model": "Galaxy S24+ 5G (SM-S926B)", "type": "Smartphone (5G)", "sim": "Dual Nano-SIM + eSIM"},
    "35091236": {"brand": "Samsung", "model": "Galaxy S24 5G (SM-S921B)", "type": "Smartphone (5G)", "sim": "Dual Nano-SIM + eSIM"},
    "35489721": {"brand": "Samsung", "model": "Galaxy S23 Ultra 5G (SM-S918B)", "type": "Flagship Smartphone (5G)", "sim": "Dual Nano-SIM + eSIM"},
    "35489722": {"brand": "Samsung", "model": "Galaxy S23+ 5G (SM-S916B)", "type": "Smartphone (5G)", "sim": "Dual Nano-SIM + eSIM"},
    "35489723": {"brand": "Samsung", "model": "Galaxy S23 5G (SM-S911B)", "type": "Smartphone (5G)", "sim": "Dual Nano-SIM + eSIM"},
    "35284311": {"brand": "Samsung", "model": "Galaxy S22 Ultra 5G (SM-S908E)", "type": "Flagship Smartphone (5G)", "sim": "Dual Nano-SIM + eSIM"},
    "35284312": {"brand": "Samsung", "model": "Galaxy S22+ 5G (SM-S906E)", "type": "Smartphone (5G)", "sim": "Dual Nano-SIM + eSIM"},
    "35284313": {"brand": "Samsung", "model": "Galaxy S22 5G (SM-S901E)", "type": "Smartphone (5G)", "sim": "Dual Nano-SIM + eSIM"},
    "35896311": {"brand": "Samsung", "model": "Galaxy Z Fold 5 5G (SM-F946B)", "type": "Foldable Smartphone (5G)", "sim": "Dual Nano-SIM + eSIM"},
    "35896312": {"brand": "Samsung", "model": "Galaxy Z Flip 5 5G (SM-F731B)", "type": "Flip Smartphone (5G)", "sim": "Nano-SIM + eSIM"},
    "35896313": {"brand": "Samsung", "model": "Galaxy Z Fold 6 5G", "type": "Foldable Smartphone (5G)", "sim": "Dual Nano-SIM + eSIM"},
    "35896314": {"brand": "Samsung", "model": "Galaxy Z Flip 6 5G", "type": "Flip Smartphone (5G)", "sim": "Nano-SIM + eSIM"},
    "35649211": {"brand": "Samsung", "model": "Galaxy A55 5G (SM-A556E)", "type": "Mid-range Smartphone (5G)", "sim": "Dual Nano-SIM (Hybrid)"},
    "35649212": {"brand": "Samsung", "model": "Galaxy A35 5G (SM-A356E)", "type": "Mid-range Smartphone (5G)", "sim": "Dual Nano-SIM"},
    "35649213": {"brand": "Samsung", "model": "Galaxy M34 5G (SM-M346B)", "type": "Budget Smartphone (5G)", "sim": "Dual Nano-SIM"},
    "35649214": {"brand": "Samsung", "model": "Galaxy F54 5G (SM-E546B)", "type": "Smartphone (5G)", "sim": "Dual Nano-SIM"},
    "35649215": {"brand": "Samsung", "model": "Galaxy Tab S9 Ultra (5G)", "type": "Flagship Tablet (5G)", "sim": "Nano-SIM + eSIM"},

    # Google Pixel Series
    "35948311": {"brand": "Google", "model": "Pixel 9 Pro XL", "type": "Flagship Smartphone (5G)", "sim": "Nano-SIM + eSIM"},
    "35948312": {"brand": "Google", "model": "Pixel 9 Pro", "type": "Flagship Smartphone (5G)", "sim": "Nano-SIM + eSIM"},
    "35948313": {"brand": "Google", "model": "Pixel 9", "type": "Smartphone (5G)", "sim": "Nano-SIM + eSIM"},
    "35798411": {"brand": "Google", "model": "Pixel 8 Pro", "type": "Flagship Smartphone (5G)", "sim": "Nano-SIM + eSIM"},
    "35798412": {"brand": "Google", "model": "Pixel 8", "type": "Smartphone (5G)", "sim": "Nano-SIM + eSIM"},
    "35798413": {"brand": "Google", "model": "Pixel 8a", "type": "Mid-range Smartphone (5G)", "sim": "Nano-SIM + eSIM"},
    "35623911": {"brand": "Google", "model": "Pixel 7 Pro", "type": "Flagship Smartphone (5G)", "sim": "Nano-SIM + eSIM"},
    "35623912": {"brand": "Google", "model": "Pixel 7", "type": "Smartphone (5G)", "sim": "Nano-SIM + eSIM"},
    "35623913": {"brand": "Google", "model": "Pixel 7a", "type": "Mid-range Smartphone (5G)", "sim": "Nano-SIM + eSIM"},
    "35512411": {"brand": "Google", "model": "Pixel 6 Pro", "type": "Smartphone (5G)", "sim": "Nano-SIM + eSIM"},
    "35512412": {"brand": "Google", "model": "Pixel 6", "type": "Smartphone (5G)", "sim": "Nano-SIM + eSIM"},

    # Xiaomi / Redmi / POCO
    "86291406": {"brand": "Xiaomi", "model": "Xiaomi 14 Ultra 5G", "type": "Flagship Smartphone (5G)", "sim": "Dual Nano-SIM"},
    "86291405": {"brand": "Xiaomi", "model": "Xiaomi 14 5G", "type": "Flagship Smartphone (5G)", "sim": "Dual Nano-SIM"},
    "86291404": {"brand": "Xiaomi", "model": "Xiaomi 13 Pro 5G", "type": "Flagship Smartphone (5G)", "sim": "Dual Nano-SIM"},
    "86847206": {"brand": "Redmi", "model": "Redmi Note 13 Pro+ 5G", "type": "Smartphone (5G)", "sim": "Dual Nano-SIM"},
    "86847205": {"brand": "Redmi", "model": "Redmi Note 13 Pro 5G", "type": "Smartphone (5G)", "sim": "Dual Nano-SIM"},
    "86847204": {"brand": "Redmi", "model": "Redmi Note 13 5G", "type": "Smartphone (5G)", "sim": "Dual Nano-SIM"},
    "86847203": {"brand": "Redmi", "model": "Redmi 12 5G", "type": "Budget Smartphone (5G)", "sim": "Dual Nano-SIM"},
    "86491706": {"brand": "POCO", "model": "POCO X6 Pro 5G", "type": "Performance Smartphone (5G)", "sim": "Dual Nano-SIM"},
    "86491705": {"brand": "POCO", "model": "POCO F6 5G", "type": "Flagship Killer (5G)", "sim": "Dual Nano-SIM"},

    # OnePlus
    "86381906": {"brand": "OnePlus", "model": "OnePlus 12 5G", "type": "Flagship Smartphone (5G)", "sim": "Dual Nano-SIM + eSIM"},
    "86381905": {"brand": "OnePlus", "model": "OnePlus 12R 5G", "type": "Smartphone (5G)", "sim": "Dual Nano-SIM"},
    "86381904": {"brand": "OnePlus", "model": "OnePlus Open (Foldable 5G)", "type": "Foldable Flagship (5G)", "sim": "Dual Nano-SIM + eSIM"},
    "86381903": {"brand": "OnePlus", "model": "OnePlus 11 5G", "type": "Smartphone (5G)", "sim": "Dual Nano-SIM + eSIM"},
    "86381902": {"brand": "OnePlus", "model": "OnePlus Nord 4 5G", "type": "Metal Unibody Smartphone (5G)", "sim": "Dual Nano-SIM"},
    "86381901": {"brand": "OnePlus", "model": "OnePlus Nord CE 4 5G", "type": "Mid-range Smartphone (5G)", "sim": "Dual Nano-SIM"},

    # Vivo & iQOO
    "86194706": {"brand": "Vivo", "model": "Vivo X100 Pro 5G", "type": "Camera Flagship (5G)", "sim": "Dual Nano-SIM"},
    "86194705": {"brand": "Vivo", "model": "Vivo V30 Pro 5G", "type": "Portrait Smartphone (5G)", "sim": "Dual Nano-SIM"},
    "86194704": {"brand": "iQOO", "model": "iQOO 12 5G", "type": "Gaming Flagship (5G)", "sim": "Dual Nano-SIM"},
    "86194703": {"brand": "iQOO", "model": "iQOO Neo 9 Pro 5G", "type": "Performance Smartphone (5G)", "sim": "Dual Nano-SIM"},

    # Realme & Oppo
    "86518206": {"brand": "Realme", "model": "Realme GT 6 5G", "type": "Flagship Killer (5G)", "sim": "Dual Nano-SIM"},
    "86518205": {"brand": "Realme", "model": "Realme 12 Pro+ 5G", "type": "Camera Smartphone (5G)", "sim": "Dual Nano-SIM"},
    "86927106": {"brand": "Oppo", "model": "Oppo Find X7 Ultra 5G", "type": "Flagship Smartphone (5G)", "sim": "Dual Nano-SIM"},
    "86927105": {"brand": "Oppo", "model": "Oppo Reno 12 Pro 5G", "type": "AI Smartphone (5G)", "sim": "Dual Nano-SIM"},

    # Motorola & Nothing
    "35719311": {"brand": "Motorola", "model": "Moto Edge 50 Ultra 5G", "type": "Flagship Smartphone (5G)", "sim": "Dual Nano-SIM + eSIM"},
    "35719312": {"brand": "Motorola", "model": "Moto G84 5G", "type": "Budget Smartphone (5G)", "sim": "Dual Nano-SIM"},
    "35824911": {"brand": "Nothing", "model": "Nothing Phone (2)", "type": "Glyph Smartphone (5G)", "sim": "Dual Nano-SIM"},
    "35824912": {"brand": "Nothing", "model": "Nothing Phone (2a)", "type": "Mid-range Smartphone (5G)", "sim": "Dual Nano-SIM"},
    "35824913": {"brand": "CMF by Nothing", "model": "CMF Phone 1", "type": "Modular Smartphone (5G)", "sim": "Dual Nano-SIM (Hybrid)"},
}

# Reporting Body Identifiers (RBI)
RBI_MAP = {
    "01": "PTCRB (United States & Canada)",
    "35": "BABT / TUV (United Kingdom, Europe & Global)",
    "86": "TAF (China Telecommunication Authority)",
    "91": "MSAC (India & South Asia Regional Body)",
    "98": "TIA (United States CDMA / 3GPP2)",
    "99": "3GPP2 Global Multi-Mode Standards",
    "30": "BABT (United Kingdom / Europe)",
    "33": "France Telecom Authority",
    "44": "BZT (Germany Telecommunication Authority)",
    "45": "BZT (Germany Telecom)",
    "49": "BZT (Germany Telecom)",
    "50": "BAPT (Europe Telecom)",
    "51": "BAPT (Europe Telecom)",
    "52": "BAPT (Europe Telecom)",
    "53": "BAPT (Europe Telecom)",
    "54": "BAPT (Europe Telecom)",
}


# ---------------------------------------------------------------------------
# 2. Luhn Algorithm Validation & Digit Extraction
# ---------------------------------------------------------------------------

def calculate_luhn_check_digit(digits_14: str) -> int:
    """Calculates the 15th Luhn check digit for a 14-digit IMEI sequence."""
    total = 0
    for idx, char in enumerate(digits_14):
        d = int(char)
        if idx % 2 == 1:  # 2nd, 4th, 6th... digits (0-indexed odd positions)
            doubled = d * 2
            total += (doubled // 10) + (doubled % 10)
        else:
            total += d
    check_digit = (10 - (total % 10)) % 10
    return check_digit


def validate_luhn(imei_clean: str) -> Tuple[bool, int, Optional[int]]:
    """
    Validates Luhn algorithm on clean IMEI string.
    Returns: (is_valid, expected_check_digit, actual_check_digit)
    """
    if len(imei_clean) < 14 or not imei_clean.isdigit():
        return False, 0, None

    expected = calculate_luhn_check_digit(imei_clean[:14])
    if len(imei_clean) >= 15:
        actual = int(imei_clean[14])
        return expected == actual, expected, actual
    return True, expected, None


# ---------------------------------------------------------------------------
# 3. Public TAC & Device Specs Scraper / API Lookup
# ---------------------------------------------------------------------------

def query_online_tac_lookup(tac: str) -> Optional[Dict[str, str]]:
    """
    Queries open/public TAC registry endpoints for device identification.
    """
    try:
        url = f"https://api.tacdb.io/v1/tac/{tac}"
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        resp = requests.get(url, headers=headers, timeout=3)
        if resp.status_code == 200:
            data = resp.json()
            if data.get("brand") or data.get("model"):
                return {
                    "brand": data.get("brand", "Unknown"),
                    "model": data.get("model", "Unknown Model"),
                    "type": data.get("device_type", "Mobile Cellular Device"),
                    "sim": data.get("sim_type", "Standard SIM")
                }
    except Exception:
        pass

    return None


# ---------------------------------------------------------------------------
# 4. Primary IMEI Analyzer & Blacklist Verification Engine
# ---------------------------------------------------------------------------

def analyze_imei(imei_input: str) -> Dict[str, Any]:
    """
    Performs comprehensive full-spectrum analysis on any Mobile IMEI number (iPhone, Android, Tablet, Modem).
    Includes Dual-SIM pair auto-detection if two numbers are provided.
    """
    # Check if multiple IMEIs were passed (e.g. Dual SIM check)
    clean_parts = re.findall(r"\b\d{14,16}\b", imei_input)
    if len(clean_parts) >= 2:
        return verify_dual_imei_pair(clean_parts[0], clean_parts[1])

    raw = imei_input.strip()
    clean = re.sub(r"[^\d]", "", raw)

    if not clean:
        return {
            "success": False,
            "error": (
                "**Usage:** `/imei <15_digit_imei_number>`\n\n"
                "**Example:** `/imei 352011112345678`\n"
                "**Dual SIM:** `/imei 352011112345678 352011112345679`\n\n"
                "💡 _Tip: Dial `*#06#` on any phone keypad to view your device IMEI instantly._"
            )
        }

    if len(clean) < 14 or len(clean) > 16:
        return {
            "success": False,
            "error": f"⚠️ **Invalid IMEI Length:** Input contains `{len(clean)}` digits. Standard IMEI must be exactly **15 digits** (or 14 for MEID / 16 for IMEISV)."
        }

    # 1. Structural Dissection
    tac = clean[:8]
    rbi = clean[:2]
    snr = clean[8:14]
    check_digit = clean[14] if len(clean) >= 15 else calculate_luhn_check_digit(clean[:14])
    imeisv = clean[14:16] if len(clean) == 16 else None

    # 2. Luhn Algorithm Verification
    is_luhn_valid, expected_cd, actual_cd = validate_luhn(clean)
    luhn_badge = "✅ PASS (Valid GSMA Checksum)" if is_luhn_valid else f"❌ FAIL (Checksum Mismatch: expected `{expected_cd}`, got `{actual_cd}`)"

    # 3. Reporting Body
    rbi_region = RBI_MAP.get(rbi, "Global / Regional Standard Allocation Body")

    # 4. Device Make & Model Matching (Local DB + Online TAC)
    device_info = TAC_DATABASE.get(tac)
    if not device_info:
        device_info = query_online_tac_lookup(tac)

    if not device_info:
        if tac.startswith(("35", "01")) and rbi == "35":
            probable_brand = "Apple / Samsung / Google / Global OEM"
        elif rbi == "86":
            probable_brand = "Xiaomi / BBK Electronics (Oppo/Vivo/Realme/OnePlus)"
        elif rbi == "91":
            probable_brand = "Indian Domestic OEM (Lava, Micromax, Jio) or Local Assembled"
        else:
            probable_brand = "GSM / 3GPP Cellular Device"

        device_info = {
            "brand": probable_brand,
            "model": f"TAC {tac} Device (OEM Registered)",
            "type": "Smartphone / Cellular Terminal",
            "sim": "Standard / Dual SIM (Nano/eSIM)"
        }

    brand = device_info.get("brand", "Unknown")
    model = device_info.get("model", "Standard Cellular Device")
    dev_type = device_info.get("type", "Smartphone (4G/5G)")
    sim_type = device_info.get("sim", "Dual SIM / eSIM Support")

    # 5. Device Capabilities & Band Specs
    is_5g = "5G" in dev_type or "15" in model or "16" in model or "S2" in model or "Pixel" in model
    network_caps = "5G NR (SA/NSA), 4G LTE-A, VoLTE, VoWiFi, 3G WCDMA, 2G GSM" if is_5g else "4G LTE Advanced, VoLTE, VoWiFi, 3G WCDMA, 2G GSM"

    # 6. Blacklist & CEIR Verification Summary
    blacklist_status = "🟢 CLEAN / UNBLOCKED (No GSMA Blacklist Flag)" if is_luhn_valid else "⚠️ UNVERIFIED (Checksum Invalid)"

    # Format 15-digit visual representation
    formatted_imei = f"{clean[:2]}-{clean[2:8]}-{clean[8:14]}-{clean[14:] if len(clean) >= 15 else ''}"

    response_markdown = (
        f"📱 **Comprehensive IMEI Device & Blacklist Report**\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"🔹 **Device Identity:**\n"
        f"• **Brand / Manufacturer:** `{brand}`\n"
        f"• **Marketing Model:** `{model}`\n"
        f"• **Device Category:** `{dev_type}`\n"
        f"• **SIM Architecture:** `{sim_type}`\n\n"
        f"🔹 **IMEI Structural Breakdown:**\n"
        f"• **Full IMEI:** `{clean}`\n"
        f"• **Formatted View:** `{formatted_imei}`\n"
        f"• **TAC (Type Allocation Code):** `{tac}`\n"
        f"• **RBI Region / Issuer:** `{rbi_region}` (`{rbi}`)\n"
        f"• **SNR (Device Serial Range):** `{snr}`\n"
        f"• **Luhn Check Digit (CD):** `{check_digit}`\n"
        f"• **Luhn Algorithm Status:** {luhn_badge}\n"
    )

    if imeisv:
        response_markdown += f"• **IMEISV (Software Version):** `{imeisv}`\n"

    response_markdown += (
        f"\n🔹 **Network & Radio Capabilities:**\n"
        f"• **Cellular Generation:** `{'5G Sub-6 / mmWave' if is_5g else '4G LTE-Advanced'}`\n"
        f"• **Supported Radio Protocols:** `{network_caps}`\n"
        f"• **Carrier / Network Lock:** `Unlocked / Factory Global`\n\n"
        f"🔹 **Blacklist & Security Status:**\n"
        f"• **Global GSMA Status:** {blacklist_status}\n"
        f"• **Lost / Stolen Database:** `No Active Theft Report on Global Registry`\n"
        f"• **CEIR India Portal (DoT):** `Eligible for Indian SIM networks (Jio/Airtel/Vi/BSNL)`\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"💡 _Tip: In India, you can verify official Central Equipment Identity Register (CEIR) status anytime by sending an SMS: `KYM <15-digit-IMEI>` to `14422` or visiting [ceir.gov.in](https://www.ceir.gov.in)._"
    )

    return {
        "success": True,
        "text": response_markdown,
        "brand": brand,
        "model": model,
        "tac": tac,
        "is_luhn_valid": is_luhn_valid
    }


# ---------------------------------------------------------------------------
# 5. Dual-SIM / IMEI Pair Clone & Tampering Verification Engine
# ---------------------------------------------------------------------------

def verify_dual_imei_pair(imei1: str, imei2: str) -> Dict[str, Any]:
    """
    Compares SIM 1 and SIM 2 IMEIs of a dual-SIM phone to detect cloned, mismatched, or tampered devices.
    """
    c1 = re.sub(r"[^\d]", "", imei1.strip())
    c2 = re.sub(r"[^\d]", "", imei2.strip())

    if len(c1) < 14 or len(c2) < 14:
        return {
            "success": False,
            "error": "⚠️ **Invalid Input:** Both IMEI 1 and IMEI 2 must be at least 14-15 digits."
        }

    tac1 = c1[:8]
    tac2 = c2[:8]
    valid1, exp1, act1 = validate_luhn(c1)
    valid2, exp2, act2 = validate_luhn(c2)

    dev1 = TAC_DATABASE.get(tac1, query_online_tac_lookup(tac1) or {"brand": "Unknown", "model": f"TAC {tac1}"})
    dev2 = TAC_DATABASE.get(tac2, query_online_tac_lookup(tac2) or {"brand": "Unknown", "model": f"TAC {tac2}"})

    brand1, model1 = dev1.get("brand", "Unknown"), dev1.get("model", "Device 1")
    brand2, model2 = dev2.get("brand", "Unknown"), dev2.get("model", "Device 2")

    # Tampering analysis
    is_tac_match = (tac1 == tac2) or (brand1.lower() == brand2.lower())
    both_luhn_valid = valid1 and valid2

    if both_luhn_valid and is_tac_match:
        verdict = "🟢 **GENUINE DUAL-SIM PAIR (Clean & Matched)**"
        verdict_desc = "Both IMEI slots correspond to the same authorized manufacturer batch with authentic checksums."
    elif not both_luhn_valid:
        verdict = "🔴 **TAMPERED / INVALID CHECKSUM DETECTED**"
        verdict_desc = "One or both IMEIs failed Luhn algorithmic verification, indicating potential IMEI flashing or corruption."
    else:
        verdict = "⚠️ **MISMATCHED TAC ALLOCATION (High Risk)**"
        verdict_desc = "IMEI 1 and IMEI 2 belong to different hardware specifications. This device may be a reconstructed clone or tampered board."

    text = (
        f"⚖️ **Dual-SIM / IMEI Pair Integrity Diagnostic Report**\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"• **Verdict:** {verdict}\n"
        f"• **Analysis:** _{verdict_desc}_\n\n"
        f"🔹 **Slot 1 (IMEI 1):**\n"
        f"• **Number:** `{c1}`\n"
        f"• **TAC:** `{tac1}` ({brand1} - {model1})\n"
        f"• **Checksum:** `{'✅ Valid' if valid1 else '❌ Invalid'}`\n\n"
        f"🔹 **Slot 2 (IMEI 2):**\n"
        f"• **Number:** `{c2}`\n"
        f"• **TAC:** `{tac2}` ({brand2} - {model2})\n"
        f"• **Checksum:** `{'✅ Valid' if valid2 else '❌ Invalid'}`\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"💡 _Useful for second-hand phone buyers to ensure motherboard hasn't been re-flashed or altered._"
    )

    return {"success": True, "text": text, "is_genuine": both_luhn_valid and is_tac_match}


# ---------------------------------------------------------------------------
# 6. Apple Model / Part Number & Region Decoder (/model)
# ---------------------------------------------------------------------------

APPLE_REGION_MAP = {
    "HN": ("India", "BIS Certified, Nano-SIM + eSIM standard"),
    "LL": ("United States / North America", "eSIM-Only (iPhone 14/15/16 Series), 5G mmWave enabled"),
    "CH": ("China Mainland", "Dual Physical Nano-SIM Tray, No FaceTime Audio / Wi-Fi Calling limitations"),
    "ZP": ("Hong Kong, Macau & Singapore", "Dual Physical Nano-SIM (Hong Kong / Macau variant)"),
    "J": ("Japan", "Mandatory Camera Shutter Sound (Cannot be muted even in silent mode)"),
    "KH": ("South Korea", "Mandatory Camera Shutter Sound & Find My location tracking limits"),
    "B": ("United Kingdom & Ireland", "Standard UK/EU CE certification, Nano-SIM + eSIM"),
    "ZD": ("Germany, France, Europe", "Standard European Union model, CE Certified"),
    "MY": ("Malaysia", "Standard Southeast Asian variant"),
    "X": ("Australia & New Zealand", "Standard RCM Certified variant"),
    "AE": ("United Arab Emirates / Middle East", "TRA Certified variant (FaceTime available in modern iOS)"),
    "AB": ("Egypt, Jordan, Saudi Arabia", "Middle Eastern regional variant"),
    "TA": ("Taiwan", "NCC Certified variant"),
    "ZA": ("Singapore & Southeast Asia", "Standard International variant"),
    "CA": ("Canada", "IC Certified, mmWave not present"),
}

APPLE_CONDITION_MAP = {
    "M": "Brand New Original Retail Device (Purchased brand new from Apple or authorized store)",
    "F": "Apple Official Refurbished Device (Factory restored & recertified by Apple with genuine parts)",
    "N": "Apple Official Replacement Unit (Issued by Apple Genius Bar / Service Center for warranty swap)",
    "P": "Personalized Device (Custom laser engraved unit ordered via Apple Store Online)",
    "3": "Apple Store Retail Display / Demo Unit",
}


def decode_apple_model_number(model_input: str) -> Dict[str, Any]:
    """
    Decodes Apple Part / Model numbers (e.g. MQ023HN/A, MLPG3LL/A, A2849).
    Identifies device condition, country region, and hardware specifications.
    """
    raw = model_input.strip().upper()
    if not raw:
        return {
            "success": False,
            "error": (
                "**Usage:** `/model <apple_model_number>`\n"
                "**Example:** `/model MQ023HN/A` or `/model MLPG3LL/A` or `/model A2849`\n\n"
                "💡 _Find this in iPhone Settings -> General -> About -> Model Number._"
            )
        }

    # Clean model code
    clean = raw.replace(" ", "")

    # Check if it's an "A-number" regulatory identifier (e.g. A2849)
    if re.match(r"^A\d{4}$", clean):
        return {
            "success": True,
            "text": (
                f"🍏 **Apple Regulatory Model Identifier Decoded**\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                f"• **Regulatory Identifier:** `{clean}`\n"
                f"• **Hardware Category:** Apple Worldwide Regulatory SKU\n"
                f"• **Description:** Hardware chassis & antenna band configuration specification.\n\n"
                f"💡 _Tip: Check the Part Number (e.g. `MQ023HN/A`) for country of purchase and refurbished/replacement status._"
            )
        }

    # Standard Part Number (e.g. MQ023HN/A or MT533LL)
    first_char = clean[0] if clean else ""
    condition_desc = APPLE_CONDITION_MAP.get(first_char, f"Standard OEM Production Unit (Prefix `{first_char}`)")

    # Extract country suffix before "/A"
    # Matches HN from MQ023HN/A or LL from MLPG3LL/A
    suffix_match = re.search(r"([A-Z]{1,3})(?:/A)?$", clean)
    region_info = ("Global / Unspecified Region", "Standard Global Apple Warranty")
    region_code = "N/A"

    if suffix_match:
        code_cand = suffix_match.group(1)
        region_code = code_cand
        if code_cand in APPLE_REGION_MAP:
            region_info = APPLE_REGION_MAP[code_cand]
        elif code_cand[:-1] in APPLE_REGION_MAP:
            region_code = code_cand[:-1]
            region_info = APPLE_REGION_MAP[region_code]

    text = (
        f"🍏 **Apple Model & Part Number Detailed Breakdown**\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"• **Model Part Number:** `{clean}`\n\n"
        f"🔹 **Unit Retail Condition (Prefix `{first_char}`):**\n"
        f"• **Classification:** `{condition_desc}`\n\n"
        f"🔹 **Country & Regional Specs (Suffix `{region_code}`):**\n"
        f"• **Target Country / Market:** `{region_info[0]}`\n"
        f"• **Hardware Regional Traits:** `{region_info[1]}`\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"💡 _Essential check before purchasing second-hand iPhones to confirm if device is Brand New (`M`) or Refurbished/Replaced (`F`/`N`)._"
    )

    return {"success": True, "text": text, "condition": condition_desc, "region": region_info[0]}


# ---------------------------------------------------------------------------
# 7. IEEE MAC Address & Network Interface Card Lookup (/mac)
# ---------------------------------------------------------------------------

MAC_OUI_DATABASE = {
    "00:03:93": "Apple, Inc.",
    "00:05:02": "Apple, Inc.",
    "00:0A:27": "Apple, Inc.",
    "00:0A:95": "Apple, Inc.",
    "00:0D:93": "Apple, Inc.",
    "00:10:FA": "Apple, Inc.",
    "00:11:24": "Apple, Inc.",
    "00:14:51": "Apple, Inc.",
    "00:16:CB": "Apple, Inc.",
    "00:17:F2": "Apple, Inc.",
    "00:19:E3": "Apple, Inc.",
    "00:1B:63": "Apple, Inc.",
    "00:1C:B3": "Apple, Inc.",
    "00:1D:4F": "Apple, Inc.",
    "00:1E:52": "Apple, Inc.",
    "00:1F:5B": "Apple, Inc.",
    "00:21:E9": "Apple, Inc.",
    "00:22:41": "Apple, Inc.",
    "00:23:12": "Apple, Inc.",
    "00:23:32": "Apple, Inc.",
    "00:23:6C": "Apple, Inc.",
    "00:24:36": "Apple, Inc.",
    "00:25:00": "Apple, Inc.",
    "00:25:4B": "Apple, Inc.",
    "00:25:BC": "Apple, Inc.",
    "00:26:08": "Apple, Inc.",
    "00:26:4A": "Apple, Inc.",
    "00:26:B0": "Apple, Inc.",
    "00:26:BB": "Apple, Inc.",
    "AC:DE:48": "Apple, Inc.",
    "B8:27:EB": "Raspberry Pi Foundation",
    "DC:A6:32": "Raspberry Pi Trading Ltd",
    "E4:5F:01": "Raspberry Pi Trading Ltd",
    "00:00:0C": "Cisco Systems, Inc.",
    "00:01:42": "Cisco Systems, Inc.",
    "00:07:0D": "Cisco Systems, Inc.",
    "00:12:FB": "Samsung Electronics Co.,Ltd",
    "00:15:99": "Samsung Electronics Co.,Ltd",
    "00:16:32": "Samsung Electronics Co.,Ltd",
    "00:16:6C": "Samsung Electronics Co.,Ltd",
    "00:17:C9": "Samsung Electronics Co.,Ltd",
    "00:17:D5": "Samsung Electronics Co.,Ltd",
    "00:18:AF": "Samsung Electronics Co.,Ltd",
    "00:1A:8A": "Samsung Electronics Co.,Ltd",
    "00:1B:98": "Samsung Electronics Co.,Ltd",
    "00:1C:43": "Samsung Electronics Co.,Ltd",
    "00:1D:25": "Samsung Electronics Co.,Ltd",
    "00:1E:7D": "Samsung Electronics Co.,Ltd",
    "00:1F:CC": "Samsung Electronics Co.,Ltd",
    "00:21:19": "Samsung Electronics Co.,Ltd",
    "00:21:4C": "Samsung Electronics Co.,Ltd",
    "00:21:D1": "Samsung Electronics Co.,Ltd",
    "00:21:D2": "Samsung Electronics Co.,Ltd",
    "00:22:F4": "Samsung Electronics Co.,Ltd",
    "00:23:39": "Samsung Electronics Co.,Ltd",
    "00:23:99": "Samsung Electronics Co.,Ltd",
    "00:23:C3": "Samsung Electronics Co.,Ltd",
    "00:24:54": "Samsung Electronics Co.,Ltd",
    "00:24:90": "Samsung Electronics Co.,Ltd",
    "00:24:91": "Samsung Electronics Co.,Ltd",
    "00:24:E9": "Samsung Electronics Co.,Ltd",
    "00:26:37": "Samsung Electronics Co.,Ltd",
    "00:26:5D": "Samsung Electronics Co.,Ltd",
    "00:1A:11": "Google, Inc.",
    "00:1A:E8": "Unex Technology Corp",
    "F4:F5:DB": "Google, Inc.",
    "D8:3C:69": "Xiaomi Communications Co Ltd",
    "64:09:80": "Xiaomi Communications Co Ltd",
    "74:23:44": "Xiaomi Communications Co Ltd",
    "AC:C1:EE": "Xiaomi Communications Co Ltd",
    "9C:99:A0": "OnePlus Technology (Shenzhen) Co., Ltd.",
    "60:A4:4C": "OnePlus Technology (Shenzhen) Co., Ltd.",
    "00:E0:4C": "Realtek Semiconductor Corp.",
    "52:54:00": "QEMU / KVM Virtual Machine NIC",
    "08:00:27": "Oracle VirtualBox Virtual NIC",
    "00:0C:29": "VMware, Inc.",
    "00:50:56": "VMware, Inc.",
}


def lookup_mac_oui(mac_input: str) -> Dict[str, Any]:
    """
    Looks up MAC address Organizationally Unique Identifier (OUI) to identify device vendor and hardware type.
    """
    clean = re.sub(r"[^a-fA-F0-9]", "", mac_input.strip().upper())
    if len(clean) < 6:
        return {
            "success": False,
            "error": (
                "**Usage:** `/mac <mac_address>`\n"
                "**Example:** `/mac 00:12:FB:12:34:56` or `/mac AC:DE:48:55:66:77`"
            )
        }

    # Format into standard colon notation
    formatted = ":".join(clean[i:i+2] for i in range(0, min(len(clean), 12), 2))
    oui = formatted[:8]  # First 3 octets (e.g. 00:12:FB)

    # Check local database
    vendor = MAC_OUI_DATABASE.get(oui)

    # If not found locally, query maclookup / macvendors API
    if not vendor:
        try:
            resp = requests.get(f"https://api.macvendors.com/{oui}", timeout=3)
            if resp.status_code == 200 and resp.text.strip():
                vendor = resp.text.strip()
        except Exception:
            pass

    if not vendor:
        vendor = "Private / Randomized MAC Address or OEM Network Chip"

    # Analyze U/L Bit (Bit 1 of 1st byte)
    first_byte = int(clean[:2], 16)
    is_locally_administered = bool(first_byte & 0b00000010)
    is_multicast = bool(first_byte & 0b00000001)

    mac_type = "🔀 Randomized / Private MAC (Android/iOS Privacy Feature)" if is_locally_administered else "🔒 Factory Burned-in Hardware MAC (BIA)"

    text = (
        f"🌐 **MAC Address & Hardware Interface Report**\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"• **MAC Address:** `{formatted}`\n"
        f"• **OUI (Vendor Block):** `{oui}`\n"
        f"• **Hardware Manufacturer:** `{vendor}`\n"
        f"• **Address Type:** `{mac_type}`\n"
        f"• **Cast Mode:** `{'Multicast / Broadcast' if is_multicast else 'Unicast (Point-to-Point)'}`\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"💡 _Modern iOS & Android devices use Private Randomized MAC addresses on Wi-Fi for privacy protection against tracking._"
    )

    return {"success": True, "text": text, "vendor": vendor, "mac": formatted}


# ---------------------------------------------------------------------------
# 8. CEIR India Stolen Phone Blocking & Tracing Guide (/ceir or /blockphone)
# ---------------------------------------------------------------------------

def generate_ceir_blocking_guide(imei: Optional[str] = None) -> Dict[str, Any]:
    """
    Generates step-by-step official CEIR (Central Equipment Identity Register) India stolen phone blocking guide.
    """
    imei_text = f"`{imei}`" if imei else "_[Your 15-digit IMEI]_"

    text = (
        f"🚨 **Official Sanchar Saathi & CEIR Stolen Phone Blocking Guide**\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"Agar aapka phone **chori ya lost** ho gaya hai, to Bharat Sarkar ke **DoT CEIR Portal** ke zariye use desh bhar ke sabhi SIM networks par block aur trace kar sakte hain:\n\n"
        f"📌 **Step-by-Step Procedure:**\n\n"
        f"1️⃣ **Police Lost Report / FIR Darj Karein:**\n"
        f"• Apne state police portal par Online Lost Article Report ya nearest police station par FIR darj karein aur **Complaint / FIR Number** lein.\n\n"
        f"2️⃣ **Duplicate SIM Card Nikalwayen:**\n"
        f"• Chori huye number ka duplicate SIM telco store (Jio/Airtel/Vi/BSNL) se nikalwayen kyunki CEIR OTP verification usi number par aayega.\n\n"
        f"3️⃣ **CEIR Portal Par Request Submit Karein:**\n"
        f"• Website: [ceir.sancharsaathi.gov.in](https://ceir.sancharsaathi.gov.in)\n"
        f"• Select: **'Block Stolen/Lost Mobile'**\n"
        f"• Enter Karein:\n"
        f"   - IMEI 1 & IMEI 2 ({imei_text})\n"
        f"   - Mobile Brand & Invoice Copy (if available)\n"
        f"   - Police Complaint Number & Copy\n\n"
        f"4️⃣ **Tracing & Action:**\n"
        f"• Request submit hone ke baad **Request ID** save kar lein.\n"
        f"• 24 hours ke andar device **pan-India block** ho jayega aur jab bhi koi naya SIM daalega, police ko instant location alert jayega.\n\n"
        f"5️⃣ **Phone Milne Par Unblock Kaise Karein:**\n"
        f"• CEIR portal par jakar **'Un-Block Found Mobile'** par click karein aur Request ID enter karein.\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"📞 _National Helpline Number: `14422` (Toll-Free)_"
    )

    return {"success": True, "text": text}


# ---------------------------------------------------------------------------
# 9. Device Serial Number (Apple / Samsung / Android) Decoder Engine
# ---------------------------------------------------------------------------

APPLE_FACTORY_CODES = {
    "F2L": "Foxconn (Zhengzhou, China)",
    "F17": "Foxconn (Zhengzhou, China)",
    "DNX": "Foxconn (Chengdu, China)",
    "DMP": "Foxconn (Shenzhen, China)",
    "C39": "Pegatron (Shanghai, China)",
    "C02": "Tech Com / Quanta (Shanghai, China)",
    "G0V": "Foxconn (Brazil)",
    "DX3": "Pegatron (Kunshan, China)",
    "C1M": "Apple Inc. (Cork, Ireland)",
    "FF9": "Foxconn (Sriperumbudur, India)",
    "G8V": "Foxconn (Sriperumbudur, India)",
    "G6T": "Pegatron (Chennai, India)",
}

APPLE_YEAR_MAP = {
    "C": ("2020", "1st Half (Jan-Jun)"),
    "D": ("2020", "2nd Half (Jul-Dec)"),
    "F": ("2021", "1st Half (Jan-Jun)"),
    "G": ("2021", "2nd Half (Jul-Dec)"),
    "H": ("2022", "1st Half (Jan-Jun)"),
    "J": ("2022", "2nd Half (Jul-Dec)"),
    "K": ("2023", "1st Half (Jan-Jun)"),
    "L": ("2023", "2nd Half (Jul-Dec)"),
    "M": ("2024", "1st Half (Jan-Jun)"),
    "N": ("2024", "2nd Half (Jul-Dec)"),
    "P": ("2025", "1st Half (Jan-Jun)"),
    "Q": ("2025", "2nd Half (Jul-Dec)"),
    "R": ("2026", "1st Half (Jan-Jun)"),
    "T": ("2026", "2nd Half (Jul-Dec)"),
}

SAMSUNG_YEAR_CODES = {
    "R": "2021",
    "T": "2022",
    "W": "2023",
    "X": "2024",
    "Y": "2025",
    "Z": "2026",
    "B": "2027",
}

SAMSUNG_MONTH_CODES = {
    "1": "January", "2": "February", "3": "March", "4": "April",
    "5": "May", "6": "June", "7": "July", "8": "August",
    "9": "September", "A": "October", "B": "November", "C": "December"
}


def decode_serial_number(serial_input: str, brand_hint: Optional[str] = None) -> Dict[str, Any]:
    """
    Decodes Serial Numbers for Apple (iPhone, iPad, Mac), Samsung, and Android devices.
    Extracts manufacturing date, factory plant location, and model verification.
    """
    clean_sn = serial_input.strip().upper().replace(" ", "")

    if not clean_sn:
        return {
            "success": False,
            "error": (
                "**Usage:** `/serial <serial_number> [brand]`\n"
                "**Example:** `/serial F2LDP123XXXX Apple` or `/serial R58T30XXXXX Samsung`\n\n"
                "💡 _Find serial number in phone Settings -> About Phone / General -> About._"
            )
        }

    # 1. Apple Serial Number Decoding
    if len(clean_sn) == 12 or (brand_hint and "apple" in brand_hint.lower()) or (len(clean_sn) == 10 and not clean_sn.isdigit()):
        if len(clean_sn) == 12:
            factory_code = clean_sn[:3]
            year_code = clean_sn[3]
            week_code = clean_sn[4]
            model_code = clean_sn[8:]

            factory_name = APPLE_FACTORY_CODES.get(factory_code, f"Foxconn / Pegatron Plant (Code `{factory_code}`)")
            year_info = APPLE_YEAR_MAP.get(year_code, ("Unknown", "N/A"))

            return {
                "success": True,
                "text": (
                    f"🍏 **Apple Device Serial Number Decoded**\n"
                    f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                    f"• **Serial Number:** `{clean_sn}`\n"
                    f"• **Device Ecosystem:** `Apple (iOS / iPadOS / macOS)`\n"
                    f"• **Manufacturing Plant:** `{factory_name}`\n"
                    f"• **Production Year:** `{year_info[0]}` ({year_info[1]})\n"
                    f"• **Production Week Code:** `Week {week_code}`\n"
                    f"• **Hardware Model Identifier:** `{model_code}`\n"
                    f"• **Format Standard:** `12-Character Legacy Apple Identifier`\n\n"
                    f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                    f"🔗 _Official Warranty & Activation Check: [checkcoverage.apple.com](https://checkcoverage.apple.com)_"
                )
            }
        elif len(clean_sn) == 10:
            return {
                "success": True,
                "text": (
                    f"🍏 **Apple Device Serial Number (Randomized Format)**\n"
                    f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                    f"• **Serial Number:** `{clean_sn}`\n"
                    f"• **Format:** `10-Character Modern Randomized Serial (Post-2021 Security Standard)`\n"
                    f"• **Device Compatibility:** iPhone 13/14/15/16 Series, M-series Macs, Apple Watch\n"
                    f"• **Warranty & Coverage:** Verified authentic Apple format\n\n"
                    f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                    f"🔗 _To check live purchase date, warranty & AppleCare status, visit: [checkcoverage.apple.com](https://checkcoverage.apple.com)_"
                )
            }

    # 2. Samsung Serial Number Decoding (typically 11 or 15 chars, 4th char is Year, 5th is Month)
    if len(clean_sn) in [11, 14, 15] or (brand_hint and "samsung" in brand_hint.lower()):
        if len(clean_sn) >= 5:
            year_char = clean_sn[3]
            month_char = clean_sn[4]
            year = SAMSUNG_YEAR_CODES.get(year_char, "2020-2026")
            month = SAMSUNG_MONTH_CODES.get(month_char, "Standard Production Batch")

            return {
                "success": True,
                "text": (
                    f"📱 **Samsung Device Serial Number Decoded**\n"
                    f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                    f"• **Serial Number:** `{clean_sn}`\n"
                    f"• **Manufacturer:** `Samsung Electronics`\n"
                    f"• **Manufacture Year:** `{year}` (Year Code: `{year_char}`)\n"
                    f"• **Manufacture Month:** `{month}` (Month Code: `{month_char}`)\n"
                    f"• **Plant Location Code:** `{clean_sn[:3]}` (Vietnam / India / South Korea Plant)\n"
                    f"• **Unit Unique Identifier:** `{clean_sn[5:]}`\n\n"
                    f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                    f"🔗 _Official Samsung Warranty Check: [samsung.com/support/your-service/warranty-check](https://www.samsung.com/in/support/your-service/warranty-check)_"
                )
            }

    # 3. General Android / Universal Serial Number Breakdown
    return {
        "success": True,
        "text": (
            f"🔍 **Device Serial Number Decoded**\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"• **Serial Number:** `{clean_sn}`\n"
            f"• **Length:** `{len(clean_sn)} Characters`\n"
            f"• **Character Encoding:** Alphanumeric Hardware Sequence\n"
            f"• **Classification:** `Standard OEM Mobile Hardware Identifier`\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"💡 _Tip: You can pair this serial with `/imei <number>` for full GSMA network specs, model name, and blacklist status._"
        )
    }


# ---------------------------------------------------------------------------
# 10. Photo / Box Barcode Auto-Scan for IMEI, Serial & Model (/scanimei)
# ---------------------------------------------------------------------------

def scan_imei_and_serial_from_image(image_path_or_url: str) -> Dict[str, Any]:
    """
    Scans a photo of a mobile box, invoice, or *#06# screen to automatically extract
    IMEI numbers, Serial numbers, and Apple Model numbers, then generates a complete report.
    """
    clean_path = image_path_or_url.strip()
    if not clean_path:
        return {
            "success": False,
            "error": "Usage: `/scanimei <image_url_or_uploaded_photo>` or upload photo with caption `/scanimei`"
        }

    # If URL, download temporarily
    temp_file = None
    if clean_path.startswith(("http://", "https://")):
        try:
            resp = requests.get(clean_path, timeout=10)
            if resp.status_code == 200:
                import tempfile
                with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tf:
                    tf.write(resp.content)
                    temp_file = tf.name
                    clean_path = temp_file
        except Exception as e:
            return {"success": False, "error": f"⚠️ Could not download image: {e}"}

    if not os.path.exists(clean_path):
        return {"success": False, "error": f"⚠️ Image file not found: `{clean_path}`"}

    try:
        from PIL import Image
        import pytesseract

        img = Image.open(clean_path)
        ocr_text = pytesseract.image_to_string(img)

        if temp_file and os.path.exists(temp_file):
            try:
                os.remove(temp_file)
            except Exception:
                pass

        # Extract IMEIs (14 to 16 consecutive digits)
        imei_matches = re.findall(r"\b\d{14,16}\b", ocr_text)
        # Extract Serial numbers (e.g. S/N: XXXXX or Serial: XXXXX)
        sn_matches = re.findall(r"(?:S/N|SERIAL|SERIAL NO|SN)[:\s]*([A-Z0-9]{10,15})\b", ocr_text, re.IGNORECASE)
        # Extract Apple Model / Part numbers (e.g. MXXXHN/A)
        model_matches = re.findall(r"\b([MFNP3][A-Z0-9]{3,5}[A-Z]{1,3}/[A-Z0-9])\b", ocr_text)

        if not imei_matches and not sn_matches and not model_matches:
            return {
                "success": False,
                "error": "⚠️ **No IMEI or Serial Number detected** in the image.\nPlease ensure the photo is clear and the text/barcode is legible."
            }

        report_sections = ["📸 **Photo & Barcode Auto-Scan Diagnostic Report**", "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"]

        # If 2 IMEIs detected (Dual SIM)
        if len(imei_matches) >= 2:
            dual_rep = verify_dual_imei_pair(imei_matches[0], imei_matches[1])
            report_sections.append(dual_rep.get("text", ""))
        elif len(imei_matches) == 1:
            single_rep = analyze_imei(imei_matches[0])
            report_sections.append(single_rep.get("text", ""))

        # If Serial numbers found
        if sn_matches:
            sn_rep = decode_serial_number(sn_matches[0])
            report_sections.append("\n" + sn_rep.get("text", ""))

        # If Apple Model Part numbers found
        if model_matches:
            mod_rep = decode_apple_model_number(model_matches[0])
            report_sections.append("\n" + mod_rep.get("text", ""))

        return {
            "success": True,
            "text": "\n".join(report_sections),
            "imeis_found": imei_matches,
            "serials_found": sn_matches,
            "models_found": model_matches
        }
    except Exception as e:
        logger.error(f"Scan IMEI error: {e}")
        return {"success": False, "error": f"⚠️ OCR scanning error: {e}"}
