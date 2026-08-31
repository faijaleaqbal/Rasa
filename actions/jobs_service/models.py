"""
Normalized Data Models for Jobs & Scholarships Notification Module.
"""

from dataclasses import dataclass, field, asdict
from typing import Optional, Dict, Any, List
from datetime import datetime


@dataclass
class NotificationItem:
    category: str  # scholarship | job_wb | job_central | psu | aadhaar_supervisor
    title: str
    organization: str = ""
    location: str = ""
    start_date: str = ""  # YYYY-MM-DD
    end_date: str = ""    # YYYY-MM-DD
    eligibility: str = ""
    documents: str = ""
    apply_link: str = ""
    source: str = ""
    source_url: str = ""
    fingerprint: str = ""
    detected_at: Optional[str] = None
    id: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        if self.id is None:
            d.pop("id", None)
        if self.detected_at is None:
            d.pop("detected_at", None)
        return d


@dataclass
class ScraperResult:
    source_name: str
    items: List[NotificationItem] = field(default_factory=list)
    success: bool = True
    error_message: Optional[str] = None
    execution_time_seconds: float = 0.0
