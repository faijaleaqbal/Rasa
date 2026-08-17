import os
import re
import json
import logging
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)
IST = timezone(timedelta(hours=5, minutes=30), name="IST")

# Memory store for pending user confirmations: user_id -> {action, params, expires_at}
PENDING_VERIFICATIONS: Dict[str, Dict[str, Any]] = {}

# High-Risk Actions that MUST require user verification
HIGH_RISK_ACTIONS = {
    "make_phone_call": "📞 Outgoing Phone Call",
    "send_phone_sms": "💬 Sending Physical SMS",
    "execute_sql_query": "🗄️ Raw SQLite Database Modification",
    "run_python_sandbox": "🐍 Server Code Execution Sandbox",
    "delete_all_records": "🗑️ Deleting Stored User Data"
}


def check_and_request_verification(action_name: str, params: Dict[str, Any], user_id: str) -> Optional[Dict[str, Any]]:
    """
    Checks if an action is high-risk. If yes and unconfirmed, records pending state and returns a verification prompt.
    Returns None if action is safe to execute immediately.
    """
    if action_name not in HIGH_RISK_ACTIONS:
        return None

    action_label = HIGH_RISK_ACTIONS[action_name]
    summary = ""

    if action_name == "make_phone_call":
        summary = f"Dialing number `{params.get('phone_number') or params.get('phone')}`"
    elif action_name == "send_phone_sms":
        summary = f"Sending SMS to `{params.get('phone_number') or params.get('phone')}` with text: *\"{params.get('message')}\"*"
    elif action_name == "execute_sql_query":
        summary = f"Running SQL Query: `{params.get('query')}`"
    elif action_name == "run_python_sandbox":
        summary = f"Executing Python Script: `{params.get('code', '')[:80]}...`"
    else:
        summary = f"Executing sensitive operation: {json.dumps(params)}"

    # Store pending verification valid for 2 minutes
    PENDING_VERIFICATIONS[user_id] = {
        "action": action_name,
        "params": params,
        "expires_at": datetime.now(IST) + timedelta(minutes=2)
    }

    verification_msg = (
        f"🔒 **Security Verification Required! (High-Risk Action)**\n\n"
        f"• **Action**: {action_label}\n"
        f"• **Target / Details**: {summary}\n\n"
        f"⚠️ Security Guardrail Active: Phone call, SMS, ya server command bina confirmation execute nahi hoga.\n\n"
        f"👉 **Execute karne ke liye bolein ya likhein:**\n"
        f"• *'Haan Confirm'* ya *'Yes'* (Action execute karne ke liye)\n"
        f"• *'Cancel'* ya *'Nahi'* (Action drop karne ke liye)"
    )

    return {
        "needs_verification": True,
        "text": verification_msg
    }


def handle_user_verification_response(user_text: str, user_id: str) -> Tuple[bool, Optional[Dict[str, Any]], str]:
    """
    Checks if user is answering a pending high-risk verification.
    Returns (was_verification_response, confirmed_action_data_or_None, response_message).
    """
    pending = PENDING_VERIFICATIONS.get(user_id)
    if not pending:
        return False, None, ""

    # Check expiration
    if datetime.now(IST) > pending["expires_at"]:
        del PENDING_VERIFICATIONS[user_id]
        return False, None, "⏱️ Verification timeout ho gaya tha. Kripya command dobara dein."

    clean_txt = user_text.lower().strip()

    # Affirmative triggers
    if clean_txt in ["haan", "yes", "confirm", "haan confirm", "yes confirm", "kar do", "kardo", "ha", "ok confirm", "proceed"]:
        action_data = PENDING_VERIFICATIONS.pop(user_id)
        return True, action_data, f"✅ **Security Verification Verified!** Executing {action_data['action']}..."

    # Negative triggers
    elif clean_txt in ["cancel", "no", "nahi", "mat karo", "abort", "stop", "reject", "nahi karo"]:
        del PENDING_VERIFICATIONS[user_id]
        return True, None, "❌ **Action Cancelled.** High-risk operation ko drop kar diya gaya hai."

    return False, None, ""
