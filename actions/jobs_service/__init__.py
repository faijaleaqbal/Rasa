"""
Alya Jobs & Scholarship Notification Service Package.
"""

from .models import NotificationItem, ScraperResult
from .service import (
    get_latest_jobs_text,
    get_latest_scholarships_text,
    get_latest_psu_text,
    get_railway_jobs_text,
    get_banking_jobs_text,
    get_defence_jobs_text,
    get_teaching_jobs_text,
    get_jobs_by_qualification_text,
    get_admit_cards_text,
    get_exam_results_text,
    get_answer_keys_text,
    get_svmcm_guide_text,
    get_aikyashree_guide_text,
    get_nsp_guide_text,
    get_girls_scholarships_text,
    get_study_abroad_scholarships_text,
    check_scholarship_eligibility_text,
    get_scholarship_help_guide_text,
    search_vacancies_text,
    set_user_format_pref,
    subscribe_user,
    unsubscribe_user,
    get_status_text,
    execute_scheduled_scrape_and_dispatch,
    execute_daily_cleanup
)

__all__ = [
    "NotificationItem",
    "ScraperResult",
    "get_latest_jobs_text",
    "get_latest_scholarships_text",
    "get_latest_psu_text",
    "get_railway_jobs_text",
    "get_banking_jobs_text",
    "get_defence_jobs_text",
    "get_teaching_jobs_text",
    "get_jobs_by_qualification_text",
    "get_admit_cards_text",
    "get_exam_results_text",
    "get_answer_keys_text",
    "get_svmcm_guide_text",
    "get_aikyashree_guide_text",
    "get_nsp_guide_text",
    "get_girls_scholarships_text",
    "get_study_abroad_scholarships_text",
    "check_scholarship_eligibility_text",
    "get_scholarship_help_guide_text",
    "search_vacancies_text",
    "set_user_format_pref",
    "subscribe_user",
    "unsubscribe_user",
    "get_status_text",
    "execute_scheduled_scrape_and_dispatch",
    "execute_daily_cleanup"
]
