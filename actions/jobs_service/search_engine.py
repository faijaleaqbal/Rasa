"""
Fuzzy Search Engine for Retained Vacancies & Scholarships (Last 20 Days).
"""

import re
import difflib
from typing import List, Dict, Any, Optional
from datetime import datetime
from .date_parser import is_deadline_passed, normalize_date
from .formatter import format_job_full, format_scholarship_full


def normalize_search_query(query: str) -> str:
    """Normalizes query text by removing punctuation, extra spaces, and lowercase."""
    if not query:
        return ""
    clean = re.sub(r'[^\w\s]', ' ', query.lower())
    return " ".join(clean.split())


def search_vacancies(
    query: str,
    notifications: List[Dict[str, Any]],
    similarity_threshold: float = 0.55
) -> str:
    """
    Executes search over retained notifications:
    1. Normalizes query.
    2. Fuzzy/partial-matches title and organization.
    3. If matches found:
       - For open vacancies: returns full details.
       - For closed vacancies: returns deadline passed message.
    4. If no match found: returns clear 'not found/not indexed' message.
    """
    norm_q = normalize_search_query(query)
    if not norm_q:
        return "🔍 Please provide a keyword to search.\n_Example: `/search WBPSC` or `/search NSP Scholarship`_"

    q_tokens = [t for t in norm_q.split() if len(t) > 1]
    if not q_tokens:
        q_tokens = [norm_q]

    matched_items = []

    for item in notifications:
        title = item.get("title", "")
        org = item.get("organization", "")
        cat = item.get("category", "")
        comb_text = f"{title} {org} {cat}".lower()
        norm_comb = normalize_search_query(comb_text)

        # 1. Exact substring match of query
        if norm_q in norm_comb:
            score = 1.0
            matched_items.append((score, item))
            continue

        # 2. Token overlap score
        matches = sum(1 for t in q_tokens if t in norm_comb)
        token_ratio = matches / len(q_tokens) if q_tokens else 0.0

        # 3. SequenceMatcher fuzzy score on title and org
        fuzzy_title = difflib.SequenceMatcher(None, norm_q, normalize_search_query(title)).ratio()
        fuzzy_org = difflib.SequenceMatcher(None, norm_q, normalize_search_query(org)).ratio()
        max_fuzzy = max(fuzzy_title, fuzzy_org)

        score = max(token_ratio, max_fuzzy)
        if score >= similarity_threshold or token_ratio >= 0.5:
            matched_items.append((score, item))

    if not matched_items:
        return (
            f"🔍 No open or recent jobs/scholarships matching '**{query.strip()}**' were found in the last 20 days of indexing.\n\n"
            f"_Tip: Try searching with broader terms like 'WBPSC', 'SSC', 'NSP', 'SAIL', 'Aadhaar', 'Police', etc., or check `/jobs` / `/scholarships`._"
        )

    # Sort by score DESC, then id DESC
    matched_items.sort(key=lambda x: (x[0], x[1].get("id", 0)), reverse=True)

    # Take top 3 best matching results
    top_matches = [m[1] for m in matched_items[:3]]
    output_blocks = []

    for item in top_matches:
        end_date = item.get("end_date")
        is_closed = is_deadline_passed(end_date)
        title = item.get("title")
        org = item.get("organization") or "Govt"

        if is_closed:
            closed_block = (
                f"⚠️ **APPLICATION CLOSED (Deadline Passed)**\n"
                f"📌 **{title}**\n"
                f"🏢 Organization: {org}\n"
                f"📅 Deadline was: {end_date or 'Expired'}\n"
                f"Applications for this vacancy are no longer accepted."
            )
            output_blocks.append(closed_block)
        else:
            is_scholarship = item.get("category") == "scholarship"
            full_details = format_scholarship_full(item) if is_scholarship else format_job_full(item)
            output_blocks.append(f"🟢 **STATUS: OPEN**\n{full_details}")

    header = f"🔍 **Search Results for:** _{query.strip()}_\n\n"
    return header + "\n\n---\n\n".join(output_blocks)
