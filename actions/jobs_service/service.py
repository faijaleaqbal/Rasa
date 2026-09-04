"""
High-Level Facade Service for Jobs & Scholarships Module.
Expanded with Railway, Bank, Defence, Teaching, Qualifications, Admit Cards, Results, Answer Keys, and Scholarships Suite.
"""

import logging
import re
from typing import Optional, Dict, Any, List
from .models import NotificationItem
from .formatter import format_notification, format_job_full, format_job_short, format_scholarship_full, format_scholarship_short
from .search_engine import search_vacancies
from .scrapers.scraper_manager import run_all_scrapers
from .dispatcher import dispatch_new_notifications

logger = logging.getLogger(__name__)


def get_user_format(db_module: Any, user_id: Optional[str]) -> str:
    """Gets format preference for user from DB, default 'short'."""
    if not user_id:
        return "short"
    try:
        user_rec = db_module.get_job_alert_user(str(user_id))
        if user_rec and user_rec.get("format_pref"):
            return user_rec["format_pref"]
    except Exception as e:
        logger.warning(f"Error fetching user format pref: {e}")
    return "short"


def get_latest_jobs_text(db_module: Any, user_id: Optional[str] = None, limit: int = 5) -> str:
    """Returns formatted text for latest open WB and Central government jobs."""
    fmt = get_user_format(db_module, user_id)
    jobs = db_module.get_recent_notifications(
        category=["job_wb", "job_central", "aadhaar_supervisor", "job_railway", "job_bank", "job_defence", "job_teaching"],
        limit=limit,
        days=20,
        open_only=True
    )

    if not jobs:
        return "💼 **Government Jobs Alert**\n\nNo active government job vacancies found in the current index. Please check back shortly or run `/status`."

    lines = ["💼 **Latest Open Government Jobs (West Bengal & Central)**\n"]
    for i, job in enumerate(jobs, 1):
        formatted = format_notification(job, format_pref=fmt)
        if fmt == "full":
            lines.append(f"{formatted}\n")
        else:
            lines.append(f"{i}. {formatted}")

    lines.append("\n💡 _Use `/search <query>` to find specific roles, `/railway`, `/bank`, or `/eligible <degree>`._")
    return "\n".join(lines).strip()


def get_latest_scholarships_text(db_module: Any, user_id: Optional[str] = None, limit: int = 5) -> str:
    """Returns formatted text for latest open scholarships."""
    fmt = get_user_format(db_module, user_id)
    scholarships = db_module.get_recent_notifications(
        category="scholarship",
        limit=limit,
        days=20,
        open_only=True
    )

    if not scholarships:
        return "🎓 **Scholarships Alert**\n\nNo active scholarship notifications found in the current index. Type `/svmcm`, `/aikyashree`, or `/nsp` for specific schemes."

    lines = ["🎓 **Latest Open Scholarships (National & West Bengal)**\n"]
    for i, sch in enumerate(scholarships, 1):
        formatted = format_notification(sch, format_pref=fmt)
        if fmt == "full":
            lines.append(f"{formatted}\n")
        else:
            lines.append(f"{i}. {formatted}")

    lines.append("\n💡 _Check `/svmcm`, `/aikyashree`, `/nsp`, `/girlschol`, `/studyabroad`, or `/scholeligible` for guides._")
    return "\n".join(lines).strip()


def get_latest_psu_text(db_module: Any, user_id: Optional[str] = None, limit: int = 5) -> str:
    """Returns formatted text for latest open PSU vacancies with #PSU tags."""
    fmt = get_user_format(db_module, user_id)
    psu_jobs = db_module.get_recent_notifications(
        category="psu",
        limit=limit,
        days=20,
        open_only=True
    )

    if not psu_jobs:
        return "🏢 **PSU Recruitment Alert**\n\nNo active PSU vacancies found in the current index. Check back soon!"

    lines = ["🏢 **Latest Open PSU Recruitment (SAIL, ONGC, NTPC, Coal India, etc.)** #PSU\n"]
    for i, psu in enumerate(psu_jobs, 1):
        formatted = format_notification(psu, format_pref=fmt)
        if fmt == "full":
            lines.append(f"{formatted}\n")
        else:
            lines.append(f"{i}. {formatted}")

    lines.append("\n💡 _Use `/format full` for complete eligibility criteria._")
    return "\n".join(lines).strip()


# ---------------------------------------------------------------------------
# Specialized Categories: Railway, Bank, Defence, Teaching
# ---------------------------------------------------------------------------

def get_railway_jobs_text(db_module: Any, user_id: Optional[str] = None, limit: int = 5) -> str:
    """Returns latest Indian Railway (RRB / RRC / RPF) vacancies."""
    fmt = get_user_format(db_module, user_id)
    # Fetch all recent and filter by railway keywords or category
    all_notifs = db_module.get_recent_notifications(days=30, open_only=False, limit=200)
    from .tagger import is_railway_job
    railway_jobs = [j for j in all_notifs if j.get("category") == "job_railway" or is_railway_job(j.get("title", ""), j.get("organization", ""))][:limit]

    if not railway_jobs:
        return (
            "🚂 **Indian Railways Recruitment (RRB / RRC / RPF)** #RailwayJobs\n\n"
            "• **Current Cycle:** RRB NTPC, Group D, ALP & Technician, RPF Constable/SI.\n"
            "• _No newly indexed Railway notifications in the last 20 days._\n\n"
            "🔗 Official Portal: [indianrailways.gov.in](https://indianrailways.gov.in) & [rrbcdg.gov.in](https://www.rrbcdg.gov.in)\n"
            "💡 _Use `/search rrb` to search historical notifications or `/admitcard` for exam slips._"
        )

    lines = ["🚂 **Latest Indian Railways Vacancies (RRB / RRC / RPF)** #RailwayJobs\n"]
    for i, job in enumerate(railway_jobs, 1):
        formatted = format_notification(job, format_pref=fmt)
        lines.append(f"{i}. {formatted}" if fmt != "full" else f"{formatted}\n")
    return "\n".join(lines).strip()


def get_banking_jobs_text(db_module: Any, user_id: Optional[str] = None, limit: int = 5) -> str:
    """Returns latest Banking & Financial Institution vacancies (SBI, IBPS, RBI)."""
    fmt = get_user_format(db_module, user_id)
    all_notifs = db_module.get_recent_notifications(days=30, open_only=False, limit=200)
    from .tagger import is_bank_job
    bank_jobs = [j for j in all_notifs if j.get("category") == "job_bank" or is_bank_job(j.get("title", ""), j.get("organization", ""))][:limit]

    if not bank_jobs:
        return (
            "🏦 **Banking & Financial Sector Recruitment** #BankJobs\n\n"
            "• **Key Boards:** SBI (PO/Clerk), IBPS (PO/Clerk/SO/RRB), RBI Grade B, NABARD, SEBI.\n"
            "• _No newly indexed banking notifications in current 20-day window._\n\n"
            "🔗 Official Portals: [ibps.in](https://www.ibps.in) & [sbi.co.in/careers](https://sbi.co.in/web/careers)\n"
            "💡 _Use `/search ibps` or `/search sbi` to search previous updates._"
        )

    lines = ["🏦 **Latest Banking & Financial Jobs (IBPS, SBI, RBI, NABARD)** #BankJobs\n"]
    for i, job in enumerate(bank_jobs, 1):
        formatted = format_notification(job, format_pref=fmt)
        lines.append(f"{i}. {formatted}" if fmt != "full" else f"{formatted}\n")
    return "\n".join(lines).strip()


def get_defence_jobs_text(db_module: Any, user_id: Optional[str] = None, limit: int = 5) -> str:
    """Returns latest Defence, Police & Paramilitary vacancies (Army, Navy, Air Force, CAPF)."""
    fmt = get_user_format(db_module, user_id)
    all_notifs = db_module.get_recent_notifications(days=30, open_only=False, limit=200)
    from .tagger import is_defence_job
    defence_jobs = [j for j in all_notifs if j.get("category") == "job_defence" or is_defence_job(j.get("title", ""), j.get("organization", ""))][:limit]

    if not defence_jobs:
        return (
            "🪖 **Defence, Police & Armed Forces Recruitment** #DefenceJobs\n\n"
            "• **Forces:** Indian Army (Agniveer/TGC), Navy, Air Force (IAF), NDA/CDS, CAPF (CRPF, BSF, CISF, ITBP, SSB).\n"
            "• _No newly indexed defence notifications in current 20-day window._\n\n"
            "🔗 Portals: [joinindianarmy.nic.in](https://joinindianarmy.nic.in) | [joinindiannavy.gov.in](https://www.joinindiannavy.gov.in)\n"
            "💡 _Use `/search army` or `/search crpf` to search active recruitment drives._"
        )

    lines = ["🪖 **Latest Defence & Paramilitary Jobs (Army, Navy, Air Force, CAPF, Police)** #DefenceJobs\n"]
    for i, job in enumerate(defence_jobs, 1):
        formatted = format_notification(job, format_pref=fmt)
        lines.append(f"{i}. {formatted}" if fmt != "full" else f"{formatted}\n")
    return "\n".join(lines).strip()


def get_teaching_jobs_text(db_module: Any, user_id: Optional[str] = None, limit: int = 5) -> str:
    """Returns latest Teaching, Professor, and TET vacancies."""
    fmt = get_user_format(db_module, user_id)
    all_notifs = db_module.get_recent_notifications(days=30, open_only=False, limit=200)
    from .tagger import is_teaching_job
    teaching_jobs = [j for j in all_notifs if j.get("category") == "job_teaching" or is_teaching_job(j.get("title", ""), j.get("organization", ""))][:limit]

    if not teaching_jobs:
        return (
            "📚 **Teaching & Academic Recruitment (TET, KVS, NVS, Assistant Professor)** #TeachingJobs\n\n"
            "• **Exams:** CTET, State TET (WB TET), KVS/NVS (PRT/TGT/PGT), UGC NET, College Service Commission.\n"
            "• _No newly indexed teaching notifications in current 20-day window._\n\n"
            "🔗 Portals: [ctet.nic.in](https://ctet.nic.in) & [kvsangathan.nic.in](https://kvsangathan.nic.in)\n"
            "💡 _Use `/search tet` or `/search professor` for specific positions._"
        )

    lines = ["📚 **Latest Teaching & Academic Vacancies (CTET, KVS, NVS, Assistant Professor)** #TeachingJobs\n"]
    for i, job in enumerate(teaching_jobs, 1):
        formatted = format_notification(job, format_pref=fmt)
        lines.append(f"{i}. {formatted}" if fmt != "full" else f"{formatted}\n")
    return "\n".join(lines).strip()


def get_jobs_by_qualification_text(db_module: Any, qualification: str, user_id: Optional[str] = None, limit: int = 5) -> str:
    """Filters vacancies based on user educational qualification (10th, 12th, Graduate, BTech, Diploma)."""
    clean_q = qualification.strip().lower()
    if not clean_q:
        return "Usage: `/eligible <qualification>`\nExample: `/eligible 10th pass` or `/eligible 12th pass` or `/eligible graduate` or `/eligible btech`"

    # Search with keyword in title or eligibility
    all_recent = db_module.get_recent_notifications(category=None, limit=200, days=30, open_only=True)
    matches = []
    for item in all_recent:
        comb = f"{item.get('title', '')} {item.get('eligibility', '')} {item.get('organization', '')}".lower()
        if any(term in comb for term in clean_q.split()):
            matches.append(item)
        if len(matches) >= limit:
            break

    if not matches:
        return f"🎯 **Qualification Filter:** `{qualification.upper()}`\n\nNo active vacancies currently matching `{qualification}` in the database.\n💡 Try running `/jobs` for general openings or `/search <keyword>`."

    fmt = get_user_format(db_module, user_id)
    lines = [f"🎯 **Active Vacancies Matching Qualification:** `{qualification.upper()}`\n"]
    for i, job in enumerate(matches, 1):
        formatted = format_notification(job, format_pref=fmt)
        lines.append(f"{i}. {formatted}" if fmt != "full" else f"{formatted}\n")
    return "\n".join(lines).strip()


# ---------------------------------------------------------------------------
# Exam Lifecycle: Admit Cards, Results, Answer Keys
# ---------------------------------------------------------------------------

def get_admit_cards_text(db_module: Any, user_id: Optional[str] = None, limit: int = 5) -> str:
    """Returns latest released Admit Cards & Hall Tickets."""
    all_notifs = db_module.get_recent_notifications(days=30, open_only=False, limit=200)
    from .tagger import is_admit_card
    cards = [j for j in all_notifs if j.get("category") == "admit_card" or is_admit_card(j.get("title", ""))][:limit]

    if not cards:
        return (
            "🎟️ **Exam Admit Cards & Hall Tickets Portal** #AdmitCard\n\n"
            "• SSC (CGL, CHSL, MTS, GD), UPSC, RRB, IBPS, WBPSC & State Police Admit Cards.\n"
            "• Direct Official Portals:\n"
            "   - SSC: [ssc.gov.in](https://ssc.gov.in)\n"
            "   - UPSC: [upsconline.nic.in](https://upsconline.nic.in)\n"
            "   - WBPSC: [psc.wb.gov.in](https://psc.wb.gov.in)\n\n"
            "💡 _Use `/search admit` to search newly released exam city slips and call letters._"
        )

    lines = ["🎟️ **Latest Released Exam Admit Cards & Hall Tickets** #AdmitCard\n"]
    for i, c in enumerate(cards, 1):
        title = c.get("title", "Admit Card")
        link = c.get("apply_link") or c.get("source_url") or "https://sarkariresult.com"
        lines.append(f"{i}. 🎟️ **{title}**\n   🔗 Download: {link}\n")
    return "\n".join(lines).strip()


def get_exam_results_text(db_module: Any, user_id: Optional[str] = None, limit: int = 5) -> str:
    """Returns latest declared Exam Results, Cut-offs & Merit Lists."""
    all_notifs = db_module.get_recent_notifications(days=30, open_only=False, limit=200)
    from .tagger import is_exam_result
    results = [j for j in all_notifs if j.get("category") == "exam_result" or is_exam_result(j.get("title", ""))][:limit]

    if not results:
        return (
            "🏆 **Sarkari Exam Results & Cut-off Marks** #ExamResult\n\n"
            "• Track results for UPSC, SSC, IBPS, RRB, WBPSC, NEET, JEE & Board Exams.\n"
            "• Direct Official Result Links:\n"
            "   - SSC Results: [ssc.gov.in/results](https://ssc.gov.in)\n"
            "   - UPSC Results: [upsc.gov.in](https://upsc.gov.in)\n"
            "   - WB Results: [wbresults.nic.in](https://wbresults.nic.in)\n\n"
            "💡 _Use `/search result` to check recent merit list announcements._"
        )

    lines = ["🏆 **Latest Declared Exam Results & Merit Lists** #ExamResult\n"]
    for i, r in enumerate(results, 1):
        title = r.get("title", "Exam Result")
        link = r.get("apply_link") or r.get("source_url") or "https://sarkariresult.com"
        lines.append(f"{i}. 🏆 **{title}**\n   🔗 View Scorecard / PDF: {link}\n")
    return "\n".join(lines).strip()


def get_answer_keys_text(db_module: Any, user_id: Optional[str] = None, limit: int = 5) -> str:
    """Returns latest official Answer Keys & Objection trackers."""
    all_notifs = db_module.get_recent_notifications(days=30, open_only=False, limit=200)
    from .tagger import is_answer_key
    keys = [j for j in all_notifs if j.get("category") == "answer_key" or is_answer_key(j.get("title", ""))][:limit]

    if not keys:
        return (
            "🔑 **Official Exam Answer Keys & Response Sheets** #AnswerKey\n\n"
            "• Check provisional & final answer keys for SSC, CTET, RRB, NTA, and State Exams.\n"
            "• Raise objections on contested questions before deadline.\n\n"
            "💡 _Use `/search answer key` to find released question keys._"
        )

    lines = ["🔑 **Latest Official Answer Keys & Response Sheets** #AnswerKey\n"]
    for i, k in enumerate(keys, 1):
        title = k.get("title", "Answer Key")
        link = k.get("apply_link") or k.get("source_url") or "https://sarkariresult.com"
        lines.append(f"{i}. 🔑 **{title}**\n   🔗 Check Answer Key: {link}\n")
    return "\n".join(lines).strip()


# ---------------------------------------------------------------------------
# Comprehensive Scholarship Suite: SVMCM, Aikyashree, NSP, Girls, Abroad
# ---------------------------------------------------------------------------

def get_svmcm_guide_text() -> str:
    """Returns detailed guide & eligibility for Swami Vivekananda Merit-cum-Means (SVMCM) Scholarship."""
    return (
        "🌟 **Swami Vivekananda Merit-cum-Means Scholarship (SVMCM / Bikash Bhavan)** #Scholarship\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "🔹 **Eligibility Criteria:**\n"
        "• **Domicile:** West Bengal permanent resident.\n"
        "• **Minimum Marks Required:**\n"
        "   - Class 11 & 12: **60%** in Madhyamik (10th)\n"
        "   - Undergraduation (BA/BSc/BCom): **60%** in Higher Secondary (12th)\n"
        "   - Engineering / Medical (B.Tech / MBBS): **60%** in 12th\n"
        "   - Postgraduation (MA/MSc/MCom): **53%** in Honours Graduation\n"
        "• **Family Annual Income:** Maximum **₹2,50,000 / year**.\n\n"
        "💰 **Scholarship Amount:**\n"
        "• Higher Secondary (11-12): **₹1,000/month (₹12,000/year)**\n"
        "• UG (Arts / Commerce / Science): **₹1,000 - ₹1,500/month**\n"
        "• B.Tech / MBBS / Pharmacy: **₹5,000/month (₹60,000/year)**\n"
        "• PG (MA/MSc/MCom): **₹2,000 - ₹2,500/month**\n\n"
        "📄 **Mandatory Documents:**\n"
        "1. Madhyamik & Last Qualifying Marksheet (Both Sides)\n"
        "2. Income Certificate from BDO / SDO / Executive Officer\n"
        "3. Admission Receipt & Bonafide Certificate\n"
        "4. Bank Passbook First Page (Aadhaar Seeding / NPCI Active mandatory)\n"
        "5. Domicile Certificate (Aadhaar / Voter ID / Ration Card)\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "🔗 **Official Apply / Renewal Portal:** [svmcm.wbhed.gov.in](https://svmcm.wbhed.gov.in)\n"
        "📞 _Helpdesk: 1800-102-8014 (Toll-Free)_"
    )


def get_aikyashree_guide_text() -> str:
    """Returns detailed guide & eligibility for WBMDFC Aikyashree Minority Scholarship."""
    return (
        "🕌 **WBMDFC Aikyashree Minority Scholarship Portal** #Scholarship #WBMDFC\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "🔹 **Eligible Communities:** Muslim, Christian, Sikh, Buddhist, Jain & Parsi students of West Bengal.\n\n"
        "🔹 **Scholarship Schemes under Aikyashree:**\n"
        "1️⃣ **Pre-Matric Scholarship (Class 1 to 10):**\n"
        "   - Min 50% marks in previous exam.\n"
        "   - Family income < ₹2 Lakh/year.\n"
        "2️⃣ **Post-Matric Scholarship (Class 11 to Ph.D.):**\n"
        "   - Min 50% marks.\n"
        "   - Family income < ₹2 Lakh/year.\n"
        "3️⃣ **Merit-cum-Means (MCM) Scholarship (Technical & Professional Courses):**\n"
        "   - For B.Tech, MBBS, MBA, Law, MCA, BCA, Nursing.\n"
        "   - Grant: Up to **₹33,000/year** (Course fee + Maintenance allowance).\n"
        "   - Family income < ₹2.5 Lakh/year.\n"
        "4️⃣ **Talent Support Stipend (TSP):**\n"
        "   - For students with < 50% marks studying in Class 11 to Ph.D.\n"
        "5️⃣ **Swami Vivekananda MCM for Minorities (SVMCM):**\n"
        "   - Min 60% marks in 10th/12th. Grant up to ₹60,000/year.\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "🔗 **Official Portal:** [wbmdfcscholarship.in](https://www.wbmdfcscholarship.in)\n"
        "📞 _WBMDFC Helpline: 1800-120-2130_"
    )


def get_nsp_guide_text() -> str:
    """Returns overview & guide for National Scholarship Portal (NSP Central Schemes)."""
    return (
        "🏛️ **National Scholarship Portal (NSP) — Central Government Schemes** #Scholarship #NSP\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "🔹 **Major Central Schemes on NSP:**\n"
        "• **Central Sector Scheme (CSSS):** For college/university students scoring > 80 percentile in 12th board.\n"
        "• **UGC / AICTE Schemes:** AICTE Pragati, Saksham, Swanath, PG Scholarship for GATE.\n"
        "• **Ministry of Tribal Affairs:** National Fellowship & Higher Education for ST Students.\n"
        "• **Ministry of Social Justice:** Top Class Education for SC Students.\n"
        "• **Department of Empowerment of Persons with Disabilities:** Pre/Post Matric & Top Class for Divyangjan.\n\n"
        "⚠️ **Important NSP Rule (OTR & Aadhaar Mandatory):**\n"
        "• One-Time Registration (OTR) is required via Face Authentication App.\n"
        "• Bank account must be mapped with Aadhaar on NPCI Mapper (Aadhaar Enabled Payment System - DBT).\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "🔗 **Official NSP Portal:** [scholarships.gov.in](https://scholarships.gov.in)\n"
        "📞 _NSP Helpdesk: 0120-6619540_"
    )


def get_girls_scholarships_text() -> str:
    """Returns guide for Girl Students Scholarships (Kanyashree, Pragati, Begum Hazrat Mahal, L'Oréal)."""
    return (
        "👧 **Dedicated Scholarships for Girl Students & Women in STEM** #Scholarship\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "1️⃣ **Kanyashree Prakalpa (West Bengal):**\n"
        "   • **K1 (Annual):** ₹1,000/year (Class 8-12, age 13-18).\n"
        "   • **K2 (One-Time Grant):** **₹25,000** on turning 18 & unmarried continuing education.\n"
        "   • **K3 (Postgraduation):** ₹2,000-₹2,500/month for PG science/arts.\n\n"
        "2️⃣ **AICTE Pragati Scholarship for Girls:**\n"
        "   • For girls admitted to 1st year Degree / Diploma in AICTE approved engineering college.\n"
        "   • Grant: **₹50,000 per year** for all 4 years of B.Tech / 3 years Diploma.\n\n"
        "3️⃣ **Begum Hazrat Mahal National Scholarship:**\n"
        "   • For minority girl students (Class 9 to 12) scoring min 50% marks.\n"
        "   • Grant: ₹5,000 - ₹6,000/year.\n\n"
        "4️⃣ **L'Oréal India For Young Women in Science:**\n"
        "   • For 12th passed girls (PCM/PCB min 85%) pursuing higher education in scientific fields.\n"
        "   • Grant: Up to **₹2.5 Lakh** for graduation.\n\n"
        "5️⃣ **Santoor Women's Scholarship:**\n"
        "   • For girls from underprivileged backgrounds pursuing undergraduate studies. Grant: ₹24,000/year.\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "💡 _Type `/scholeligible girl btech` to check your matching schemes._"
    )


def get_study_abroad_scholarships_text() -> str:
    """Returns list of top International Fully Funded Study Abroad Scholarships."""
    return (
        "✈️ **Top International Fully Funded Study Abroad Scholarships** #Scholarship #StudyAbroad\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "1️⃣ **Chevening Scholarship (United Kingdom 🇬🇧):**\n"
        "   • Full tuition fees, monthly living allowance, return economy flight to UK for 1-year Master's degree.\n"
        "   • Open to Indian graduates with 2+ years work experience.\n"
        "   • Portal: [chevening.org](https://www.chevening.org)\n\n"
        "2️⃣ **DAAD Scholarships (Germany 🇩🇪):**\n"
        "   • Free tuition at public German universities + €934/month stipend + travel allowance.\n"
        "   • Portal: [daad.de](https://www.daad.de)\n\n"
        "3️⃣ **Fulbright-Nehru Master's Fellowships (USA 🇺🇸):**\n"
        "   • J-1 visa support, round-trip airfare, tuition & living stipend for master's degree in US universities.\n"
        "   • Portal: [usief.org.in](https://www.usief.org.in)\n\n"
        "4️⃣ **Commonwealth Scholarships (UK & Commonwealth Countries 🇬🇧):**\n"
        "   • For Master's and Ph.D. studies in UK universities for talented developing country students.\n\n"
        "5️⃣ **Inlaks Shivdasani Foundation Scholarship:**\n"
        "   • Up to $100,000 funding for top global universities (Oxford, Cambridge, Harvard, MIT, Imperial).\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "💡 _Application cycles usually open annually between August to December._"
    )


def check_scholarship_eligibility_text(user_query: str) -> str:
    """Intelligently matches user profile with government and private scholarships."""
    clean = user_query.lower()
    if not clean:
        return (
            "**Usage:** `/scholeligible <class_or_course> [percentage%] [income] [category]`\n\n"
            "**Examples:**\n"
            "• `/scholeligible 12th 85% wb`\n"
            "• `/scholeligible btech minority income 2 lakh`\n"
            "• `/scholeligible girl btech`\n"
            "• `/scholeligible 10th pass sc category`"
        )

    matched_schemes = []

    # Check SVMCM
    if ("wb" in clean or "bengal" in clean or "12th" in clean or "10th" in clean or "btech" in clean or "graduation" in clean):
        if any(pct in clean for pct in ["60", "65", "70", "75", "80", "85", "90", "95"]) or "svmcm" in clean or "merit" in clean:
            matched_schemes.append(
                "🌟 **Swami Vivekananda Merit-cum-Means (SVMCM):**\n"
                "   • Eligibility: WB Resident, Min 60% marks in 10th/12th, Income < ₹2.5 Lakh/yr.\n"
                "   • Fund: **₹12,000 - ₹60,000 per year**.\n"
                "   • Portal: [svmcm.wbhed.gov.in](https://svmcm.wbhed.gov.in)"
            )

    # Check Minority / Aikyashree
    if any(k in clean for k in ["minority", "muslim", "christian", "aikyashree", "wbmdfc"]):
        matched_schemes.append(
            "🕌 **WBMDFC Aikyashree (Pre/Post/MCM/SVMCM):**\n"
            "   • Eligibility: Minority student in WB, Min 50-60% marks, Income < ₹2.5 Lakh.\n"
            "   • Fund: **₹1,500 to ₹33,000/year** (Up to ₹60,000 for technical courses).\n"
            "   • Portal: [wbmdfcscholarship.in](https://www.wbmdfcscholarship.in)"
        )

    # Check Girls
    if any(k in clean for k in ["girl", "female", "woman", "daughter", "kanyashree", "pragati"]):
        matched_schemes.append(
            "👧 **AICTE Pragati Scholarship for Girls:**\n"
            "   • Eligibility: 1st year B.Tech / Diploma in AICTE college, Income < ₹8 Lakh/yr.\n"
            "   • Fund: **₹50,000 per year** (Full course duration).\n"
            "   • Portal: [scholarships.gov.in](https://scholarships.gov.in)"
        )
        matched_schemes.append(
            "👧 **Kanyashree K2 Grant (West Bengal):**\n"
            "   • Eligibility: Unmarried girl student turning 18 in WB.\n"
            "   • Fund: **₹25,000 one-time grant**."
        )

    # Check SC/ST/OBC (Oasis)
    if any(k in clean for k in ["sc", "st", "obc", "oasis"]):
        matched_schemes.append(
            "🏛️ **Oasis Scholarship (West Bengal SC/ST/OBC):**\n"
            "   • Eligibility: SC/ST/OBC students studying from Class 9 to PG.\n"
            "   • Fund: ₹1,500 - ₹12,000/year.\n"
            "   • Portal: [oasis.gov.in](https://oasis.gov.in)"
        )

    # Private CSR Scholarships (Tata, HDFC, Reliance)
    matched_schemes.append(
        "🏢 **HDFC Badhte Kadam & Tata Capital Pankh Scholarship:**\n"
        "   • Eligibility: Class 11, 12, UG, General & Professional degree students (Min 60% marks).\n"
        "   • Fund: **₹10,000 - ₹1,00,000/year**.\n"
        "   • Portal: [buddy4study.com](https://www.buddy4study.com)"
    )

    lines = [
        f"🎯 **Matching Scholarships for Profile:** `{user_query}`\n",
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
    ]
    lines.extend([f"{i}. {s}\n" for i, s in enumerate(matched_schemes, 1)])
    lines.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n💡 _Type `/scholhelp` for document checklist and bank Aadhaar-NPCI seeding instructions._")
    return "\n".join(lines).strip()


def get_scholarship_help_guide_text() -> str:
    """Returns document checklist & NPCI Bank Aadhaar Seeding check guide."""
    return (
        "📑 **Scholarship Success Guide: Documents & NPCI Aadhaar Seeding**\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "⚠️ **Why 90% Scholarship Applications Get Rejected:**\n"
        "1. Bank Account not mapped with **NPCI / DBT (Aadhaar Seeding)**.\n"
        "2. Income Certificate not issued by designated authority (BDO/SDO).\n"
        "3. Bonafide certificate missing institute seal or current academic year.\n\n"
        "✅ **Mandatory Document Checklist:**\n"
        "• Marksheets of all previous qualifying examinations (Both sides).\n"
        "• Current Year Admission Fee Receipt & Institution Bonafide Certificate.\n"
        "• Family Income Certificate (Issued within last 6 months by BDO / SDO / Joint BDO).\n"
        "• Bank Passbook First Page (Name, Account No, IFSC clearly visible).\n"
        "• Domicile Proof (Aadhaar Card, Voter ID, Ration Card).\n"
        "• Caste / Minority Certificate (if applicable).\n\n"
        "💳 **How to Check Bank NPCI Aadhaar Seeding Status:**\n"
        "1. Visit UIDAI Bank Seeding Checker: [resident.uidai.gov.in/bank-mapper](https://resident.uidai.gov.in/bank-mapper)\n"
        "2. Enter Aadhaar number and OTP.\n"
        "3. Check if status says: `Banking Status: ACTIVE`.\n"
        "4. If inactive, visit your bank branch and submit the **'Aadhaar Mandate / NPCI DBT Linking Form'** immediately.\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "💡 _Ensure your name in Aadhaar, Marksheet, and Bank Passbook matches exactly._"
    )


# ---------------------------------------------------------------------------
# Search, Preference & Scheduled Dispatch Utilities
# ---------------------------------------------------------------------------

def search_vacancies_text(db_module: Any, query: str, user_id: Optional[str] = None) -> str:
    """Fuzzy searches active notifications by title or organization."""
    clean_q = query.strip()
    if not clean_q:
        return "Usage: `/search <keyword>`\nExample: `/search wbpsc` or `/search railway`"

    all_recent = db_module.get_recent_notifications(category=None, limit=200, days=30, open_only=False)
    return search_vacancies(clean_q, all_recent, limit=5)


def set_user_format_pref(db_module: Any, user_id: str, format_pref: str) -> str:
    """Updates user notification format preference (full or short)."""
    pref = format_pref.strip().lower()
    if pref not in ("full", "short"):
        return "Usage: `/format full` or `/format short`\n(Default format is **short**)."

    if hasattr(db_module, "set_job_alert_format_pref"):
        success = db_module.set_job_alert_format_pref(str(user_id), pref)
    else:
        success = getattr(db_module, "set_job_alert_format")(str(user_id), pref)
    if success:
        return f"✅ **Notification Format Updated!** Your alerts will now be formatted in **{pref.upper()}** view."
    return "⚠️ Failed to update format preference."


def subscribe_user(db_module: Any, user_id: str, chat_id: Optional[str] = None) -> str:
    """Subscribes a user to daily job alerts."""
    if hasattr(db_module, "subscribe_job_alert_user"):
        success = db_module.subscribe_job_alert_user(str(user_id))
    else:
        success = getattr(db_module, "subscribe_job_alerts")(str(user_id), str(chat_id or user_id))
    if success:
        return "🔔 **Subscribed to Daily Job & Scholarship Alerts!** You will receive instant notifications when new vacancies are detected."
    return "⚠️ Subscription failed or you are already subscribed."


def unsubscribe_user(db_module: Any, user_id: str) -> str:
    """Unsubscribes a user from job alerts."""
    if hasattr(db_module, "unsubscribe_job_alert_user"):
        success = db_module.unsubscribe_job_alert_user(str(user_id))
    else:
        success = getattr(db_module, "unsubscribe_job_alerts")(str(user_id))
    if success:
        return "🔕 **Unsubscribed from Job Alerts.** You will no longer receive proactive notifications. You can still use `/jobs` or `/scholarships` anytime."
    return "ℹ️ You are not currently subscribed to job alerts."


def get_status_text(db_module: Any, user_id: Optional[str] = None) -> str:
    """Returns telemetry statistics for scrapers and database volume."""
    if user_id and hasattr(db_module, "is_admin_user") and not db_module.is_admin_user(str(user_id)):
        return "⛔ **Access Restricted:** This command is reserved for Bot Administrators."

    all_notifs = db_module.get_recent_notifications(days=30, open_only=False, limit=500)
    open_notifs = db_module.get_recent_notifications(days=30, open_only=True, limit=500)

    cats = {}
    for n in all_notifs:
        c = n.get("category", "other")
        cats[c] = cats.get(c, 0) + 1

    cat_str = "\n".join([f"   • `{k}`: {v} items" for k, v in cats.items()])

    return (
        f"📊 **Alya Job & Scholarship Engine Telemetry — Scraper Status Dashboard**\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"• **Active Retained Items (30 Days):** `{len(all_notifs)}`\n"
        f"• **Currently Open Vacancies:** `{len(open_notifs)}`\n"
        f"• **Category Breakdown:**\n{cat_str or '   • No data yet'}\n\n"
        f"• **Source Health & Active Modules:** FreeJobAlert, SarkariResult, WBPSC, WBMDFC, Buddy4Study, Scholarships.gov, PSU Careers\n"
        f"• **Scraper Schedule:** Daily at 08:00 AM & 06:00 PM IST\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    )


def execute_scheduled_scrape_and_dispatch(db_module: Any) -> Dict[str, Any]:
    """Executes all scraper spiders, saves deduplicated items to DB, and dispatches live alerts to subscribers every 3 hours."""
    logger.info("Executing scheduled Job & Scholarship scrape cycle (Every 3 Hours)...")
    new_items_list = run_all_scrapers(db_module)

    dispatch_res = {"dispatched": 0, "failed": 0, "unsubscribed_blocked": 0}
    if new_items_list:
        dispatch_res = dispatch_new_notifications(new_items_list, db_module)
        logger.info(f"Dispatched {len(new_items_list)} new notifications to subscribers: {dispatch_res}")

    return {
        "new_items": len(new_items_list),
        "dispatch": dispatch_res
    }


def execute_daily_cleanup(db_module: Any, retention_days: int = 30, days: Optional[int] = None) -> int:
    """Purges notifications older than retention_days."""
    target_days = days if days is not None else retention_days
    return db_module.cleanup_old_notifications(target_days)
