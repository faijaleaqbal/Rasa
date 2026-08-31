"""
Classification and Tagging Engine for Vacancies & Scholarships.
Expanded with specialized categories: Railway, Banking, Defence, Teaching, Admit Cards, Results, and Multi-Tier Scholarships.
"""

import re
from typing import Tuple, List, Optional

# PSU Organizations list
PSU_ORGS = [
    "sail", "steel authority of india",
    "ongc", "oil and natural gas corporation",
    "ntpc", "national thermal power corporation",
    "coal india", "cil", "eastern coalfields", "ecl", "bccnl", "ccl", "wcl", "secl", "mcl", "cmpdil",
    "bhel", "bharat heavy electricals",
    "bpcl", "bharat petroleum",
    "hpcl", "hindustan petroleum",
    "iocl", "indian oil",
    "gail", "gas authority of india",
    "powergrid", "pgcil", "power grid corporation",
    "bel", "bharat electronics",
    "hal", "hindustan aeronautics",
    "nhpc", "nlc", "neyveli lignite",
    "nmdc", "national mineral development",
    "posoco", "grid-india",
    "sjvn", "rec", "rural electrification",
    "pfc", "power finance",
    "oil india", "oil",
    "rinl", "rashtriya ispat nigam",
    "ecil", "mdl", "mazagon dock",
    "grse", "garden reach shipbuilders",
    "bdl", "bharat dynamics",
    "nalco", "national aluminium",
    "mecl", "mineral exploration",
    "concor", "container corporation",
    "nbcc", "irctc", "irfc", "ircon", "rites", "rvnl", "bapco", "midhani"
]

WB_KEYWORDS = [
    "west bengal", "wbpsc", "wb public service", "wbmdfc", "aikyashree",
    "wbhrb", "wb police", "wbprb", "wbpdcl", "wbsetcl", "wbsedcl",
    "employment bank", "yuvasree", "kolkata police", "wb health",
    "swami vivekananda merit", "svmcm", "kanyashree", "oasis scholarship",
    "wbssc", "wbbpe", "wb municipal", "wbmsc", "wb court", "calcutta high court",
    "alipore", "malda", "murshidabad", "howrah", "hooghly", "north 24 parganas",
    "south 24 parganas", "darjeeling", "siliguri", "jalpaiguri", "purba medinipur",
    "paschim medinipur", "bankura", "purulia", "birbhum", "bardhaman", "nadia"
]

RAILWAY_KEYWORDS = [
    "railway", "rrb", "rrc", "indian railways", "loco pilot", "alp", "technician",
    "group d", "rpf", "railway protection force", "ntpc", "station master", "goods guard",
    "clerk cum typist", "rail wheel plant", "rail coach factory", "clw", "dlw", "icf"
]

BANK_KEYWORDS = [
    "bank", "ibps", "sbi", "state bank of india", "rbi", "reserve bank of india",
    "nabard", "sebi", "sidbi", "probationary officer", "po", "clerk", "specialist officer",
    "gramin bank", "rrb po", "punjab national bank", "pnb", "bank of baroda", "bob",
    "canara bank", "union bank", "indian bank", "central bank of india", "uco bank"
]

DEFENCE_KEYWORDS = [
    "army", "indian army", "navy", "indian navy", "air force", "indian air force", "iaf",
    "nda", "cds", "afcat", "capf", "crpf", "bsf", "cisf", "ssb", "itbp", "assam rifles",
    "coast guard", "indian coast guard", "police", "constable", "sub inspector", "si",
    "head constable", "commando", "agniveer", "soldier", "havildar"
]

TEACHING_KEYWORDS = [
    "teacher", "teaching", "ctet", "tet", "wb tet", "kvs", "kendriya vidyalaya",
    "nvs", "navodaya vidyalaya", "dsssb", "prt", "tgt", "pgt", "professor",
    "assistant professor", "associate professor", "lecturer", "ugc net", "csir net",
    "headmaster", "primary teacher", "upper primary"
]

ADMIT_CARD_KEYWORDS = [
    "admit card", "hall ticket", "call letter", "e-admit card", "exam city slip",
    "download admit", "entry pass", "intimation slip"
]

EXAM_RESULT_KEYWORDS = [
    "result", "merit list", "cut off", "cutoff", "score card", "final selection",
    "declared result", "marksheet", "rank card", "provisional list"
]

ANSWER_KEY_KEYWORDS = [
    "answer key", "response sheet", "question paper objection", "tentative answer key",
    "final answer key", "master question paper"
]

SCHOLARSHIP_KEYWORDS = [
    "scholarship", "fellowship", "stipend", "grant", "financial assistance",
    "national scholarship portal", "nsp", "aikyashree", "buddy4study",
    "svmcm", "kanyashree", "oasis", "medhabruti", "post-matric scholarship",
    "pre-matric scholarship", "merit-cum-means", "pragati scholarship", "tata capital",
    "hdfc badhte kadam", "reliance foundation scholarship", "lic golden jubilee"
]

# Genuine Aadhaar Supervisor patterns
AADHAAR_SUPERVISOR_PATTERNS = [
    re.compile(r'\b(?:aadhaar|uidai)\s+(?:supervisor|superviser|supervisor[- ]cum[- ]operator|operator[- ]cum[- ]supervisor|enrollment\s+supervisor|enrolment\s+supervisor)\b', re.IGNORECASE),
    re.compile(r'\b(?:supervisor|superviser|supervisor[- ]cum[- ]operator|operator[- ]cum[- ]supervisor|enrollment\s+supervisor|enrolment\s+supervisor)\s+(?:for\s+)?(?:aadhaar|uidai|enrolment|enrollment)\b', re.IGNORECASE),
    re.compile(r'\b(?:aadhaar|uidai|ecmp)\s+(?:examination|certification|recruitment)\s+(?:for\s+)?(?:supervisor|superviser)\b', re.IGNORECASE),
    re.compile(r'\baadhaar\s+(?:supervisors?|operators?)\b', re.IGNORECASE),
]

AADHAAR_EXCLUDE_PATTERNS = [
    re.compile(r'\b(?:director|deputy director|assistant director|section officer|accountant|software|developer|consultant|legal|architect)\b', re.IGNORECASE)
]


def is_aadhaar_supervisor(text: str) -> bool:
    lower = text.lower()
    if not ("aadhaar" in lower or "uidai" in lower):
        return False
    matched = any(pat.search(text) for pat in AADHAAR_SUPERVISOR_PATTERNS)
    if not matched:
        return False
    for expat in AADHAAR_EXCLUDE_PATTERNS:
        if expat.search(text) and not re.search(r'\bsupervisor\b', text, re.I):
            return False
    return True


def is_psu_job(text: str, org: str = "") -> bool:
    comb = f"{text} {org}".lower()
    for psu in PSU_ORGS:
        if re.search(rf'\b{re.escape(psu)}\b', comb):
            return True
    return "psu" in comb or "public sector undertaking" in comb


def is_railway_job(text: str, org: str = "") -> bool:
    comb = f"{text} {org}".lower()
    return any(kw in comb for kw in RAILWAY_KEYWORDS)


def is_bank_job(text: str, org: str = "") -> bool:
    comb = f"{text} {org}".lower()
    return any(kw in comb for kw in BANK_KEYWORDS)


def is_defence_job(text: str, org: str = "") -> bool:
    comb = f"{text} {org}".lower()
    return any(kw in comb for kw in DEFENCE_KEYWORDS)


def is_teaching_job(text: str, org: str = "") -> bool:
    comb = f"{text} {org}".lower()
    return any(kw in comb for kw in TEACHING_KEYWORDS)


def is_admit_card(text: str) -> bool:
    comb = text.lower()
    return any(kw in comb for kw in ADMIT_CARD_KEYWORDS)


def is_exam_result(text: str) -> bool:
    comb = text.lower()
    return any(kw in comb for kw in EXAM_RESULT_KEYWORDS)


def is_answer_key(text: str) -> bool:
    comb = text.lower()
    return any(kw in comb for kw in ANSWER_KEY_KEYWORDS)


def is_scholarship(text: str, source: str = "") -> bool:
    comb = f"{text} {source}".lower()
    return any(kw in comb for kw in SCHOLARSHIP_KEYWORDS)


def is_wb_job(text: str, org: str = "", loc: str = "") -> bool:
    comb = f"{text} {org} {loc}".lower()
    return any(kw in comb for kw in WB_KEYWORDS)


def classify_category(
    title: str,
    org: str = "",
    loc: str = "",
    source: str = "",
    default_cat: Optional[str] = None
) -> str:
    """
    Classifies a notification into one of the specialized categories.
    """
    comb = f"{title} {org} {loc} {source}"

    # 1. Admit Card / Result / Answer Key Lifecycle
    if is_admit_card(comb):
        return "admit_card"
    if is_exam_result(comb):
        return "exam_result"
    if is_answer_key(comb):
        return "answer_key"

    # 2. Aadhaar Supervisor check
    if is_aadhaar_supervisor(comb):
        return "aadhaar_supervisor"

    # 3. Railway check
    if is_railway_job(comb, org):
        return "job_railway"

    # 4. Bank check
    if is_bank_job(comb, org):
        return "job_bank"

    # 5. Defence & Police check
    if is_defence_job(comb, org):
        return "job_defence"

    # 6. Teaching check
    if is_teaching_job(comb, org):
        return "job_teaching"

    # 7. PSU check
    if is_psu_job(comb, org):
        return "psu"

    # 8. Scholarship check
    if is_scholarship(comb, source) or default_cat == "scholarship":
        return "scholarship"

    # 9. West Bengal Job check
    if is_wb_job(comb, org, loc) or default_cat == "job_wb":
        return "job_wb"

    # 10. Central Job check default
    return "job_central"


def get_tags_for_category(category: str, title: str = "", org: str = "") -> List[str]:
    """Returns hashtag labels required for notifications."""
    tags = []
    comb = f"{title} {org}".lower()

    if category == "job_railway" or is_railway_job(title, org):
        tags.append("#RailwayJobs")
    elif category == "job_bank" or is_bank_job(title, org):
        tags.append("#BankJobs")
    elif category == "job_defence" or is_defence_job(title, org):
        tags.append("#DefenceJobs")
    elif category == "job_teaching" or is_teaching_job(title, org):
        tags.append("#TeachingJobs")
    elif category == "psu" or is_psu_job(title, org):
        tags.append("#PSU")
    elif category == "aadhaar_supervisor" or is_aadhaar_supervisor(comb):
        tags.append("#AadhaarSupervisor")
    elif category == "job_wb" or is_wb_job(title, org):
        tags.append("#WBJobs")
    elif category == "admit_card":
        tags.append("#AdmitCard")
    elif category == "exam_result":
        tags.append("#ExamResult")
    elif category == "answer_key":
        tags.append("#AnswerKey")
    elif category == "scholarship":
        tags.append("#Scholarship")
    else:
        tags.append("#GovtJobs")

    return tags
