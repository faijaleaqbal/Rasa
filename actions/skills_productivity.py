import os
import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import requests

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# 1. Google Account Integration (Gmail, Google Drive, Google Calendar)
# ---------------------------------------------------------------------------

def get_google_credentials():
    """Builds and returns Google OAuth credentials from token.json or env vars."""
    try:
        from google.oauth2.credentials import Credentials
        from google.auth.transport.requests import Request

        token_file = os.path.join(os.path.dirname(__file__), "..", "storage", "auth", "google_token.json")
        scopes = [
            "https://www.googleapis.com/auth/gmail.readonly",
            "https://www.googleapis.com/auth/gmail.send",
            "https://www.googleapis.com/auth/drive",
            "https://www.googleapis.com/auth/calendar"
        ]

        if os.path.exists(token_file):
            creds = Credentials.from_authorized_user_file(token_file, scopes)
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            return creds

        # Try from environment variables
        refresh_token = os.getenv("GOOGLE_REFRESH_TOKEN")
        client_id = os.getenv("GOOGLE_CLIENT_ID")
        client_secret = os.getenv("GOOGLE_CLIENT_SECRET")

        if refresh_token and client_id and client_secret:
            creds = Credentials(
                None,
                refresh_token=refresh_token,
                token_uri="https://oauth2.googleapis.com/token",
                client_id=client_id,
                client_secret=client_secret
            )
            creds.refresh(Request())
            return creds

    except Exception as e:
        logger.warning(f"Error loading Google credentials: {e}")

    return None


def list_gmail_messages(query: str = "is:unread", max_results: int = 5) -> str:
    """Fetches and summarizes recent Gmail messages."""
    creds = get_google_credentials()
    if not creds:
        return (
            "⚠️ Google OAuth not fully configured yet.\n"
            "To connect Gmail, set `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, and `GOOGLE_REFRESH_TOKEN` "
            "in `.env` or place `google_token.json` in `storage/auth/`."
        )

    try:
        from googleapiclient.discovery import build
        service = build("gmail", "v1", credentials=creds)
        results = service.users().messages().list(userId="me", q=query, maxResults=max_results).execute()
        messages = results.get("messages", [])

        if not messages:
            return f"📧 No emails found matching query '{query}'."

        email_list = []
        for msg_summary in messages:
            msg = service.users().messages().get(userId="me", id=msg_summary["id"], format="metadata").execute()
            headers = {h["name"].lower(): h["value"] for h in msg.get("payload", {}).get("headers", [])}
            subject = headers.get("subject", "(No Subject)")
            sender = headers.get("from", "Unknown")
            snippet = msg.get("snippet", "")
            date_str = headers.get("date", "")
            email_list.append(f"📩 **{subject}**\n• From: `{sender}`\n• Date: {date_str}\n• Preview: {snippet}")

        return "📬 **Recent Gmail Messages:**\n\n" + "\n\n".join(email_list)

    except Exception as e:
        logger.error(f"Gmail fetch error: {e}")
        return f"❌ Failed to fetch Gmail messages: {str(e)}"


def send_gmail(to: str, subject: str, body: str) -> str:
    """Sends an email via Gmail API."""
    creds = get_google_credentials()
    if not creds:
        return (
            "⚠️ Google OAuth credentials required to send emails. "
            "Please configure `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, and `GOOGLE_REFRESH_TOKEN` in `.env`."
        )

    try:
        import base64
        from email.mime.text import MIMEText
        from googleapiclient.discovery import build

        message = MIMEText(body)
        message["to"] = to
        message["subject"] = subject
        raw = base64.urlsafe_b64encode(message.as_bytes()).decode()

        service = build("gmail", "v1", credentials=creds)
        sent_msg = service.users().messages().send(userId="me", body={"raw": raw}).execute()
        return f"✅ Email successfully sent to `{to}` (ID: `{sent_msg.get('id')}`)."

    except Exception as e:
        logger.error(f"Gmail send error: {e}")
        return f"❌ Failed to send email via Gmail: {str(e)}"


def list_drive_files(query: Optional[str] = None, max_results: int = 6) -> str:
    """Lists files from Google Drive."""
    creds = get_google_credentials()
    if not creds:
        return (
            "⚠️ Google Drive integration requires OAuth credentials in `.env` "
            "(`GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `GOOGLE_REFRESH_TOKEN`)."
        )

    try:
        from googleapiclient.discovery import build
        service = build("drive", "v3", credentials=creds)
        q_filter = f"name contains '{query}' and trashed = false" if query else "trashed = false"
        results = service.files().list(
            q=q_filter,
            pageSize=max_results,
            fields="files(id, name, mimeType, webViewLink, size)"
        ).execute()
        files = results.get("files", [])

        if not files:
            return "📁 No files found in Google Drive."

        items = []
        for f in files:
            name = f.get("name")
            link = f.get("webViewLink", "#")
            mime = f.get("mimeType", "")
            items.append(f"📄 [{name}]({link}) (`{mime}`)")

        return "📂 **Google Drive Files:**\n\n" + "\n".join(items)

    except Exception as e:
        return f"❌ Failed to list Google Drive files: {str(e)}"


def list_calendar_events(max_results: int = 5) -> str:
    """Lists upcoming Google Calendar events."""
    creds = get_google_credentials()
    if not creds:
        return (
            "⚠️ Google Calendar integration requires OAuth credentials in `.env` "
            "(`GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `GOOGLE_REFRESH_TOKEN`)."
        )

    try:
        from googleapiclient.discovery import build
        service = build("calendar", "v3", credentials=creds)
        now = datetime.now(timezone.utc).isoformat()
        events_result = service.events().list(
            calendarId="primary",
            timeMin=now,
            maxResults=max_results,
            singleEvents=True,
            orderBy="startTime"
        ).execute()
        events = events_result.get("items", [])

        if not events:
            return "📅 No upcoming events found in your Google Calendar."

        event_lines = []
        for event in events:
            start = event.get("start", {}).get("dateTime", event.get("start", {}).get("date", "N/A"))
            summary = event.get("summary", "(No Title)")
            link = event.get("htmlLink", "")
            event_lines.append(f"🗓️ **{summary}**\n• Time: `{start}`\n• Link: {link}")

        return "📅 **Upcoming Calendar Events:**\n\n" + "\n\n".join(event_lines)

    except Exception as e:
        return f"❌ Failed to fetch Calendar events: {str(e)}"


def create_calendar_event(summary: str, start_iso: str, end_iso: str, description: str = "") -> str:
    """Creates a new Google Calendar event."""
    creds = get_google_credentials()
    if not creds:
        return "⚠️ Google Calendar OAuth credentials required in `.env`."

    try:
        from googleapiclient.discovery import build
        service = build("calendar", "v3", credentials=creds)
        body = {
            "summary": summary,
            "description": description,
            "start": {"dateTime": start_iso},
            "end": {"dateTime": end_iso}
        }
        event = service.events().insert(calendarId="primary", body=body).execute()
        return f"✅ Calendar event created: **{summary}** at `{start_iso}` ([View Event]({event.get('htmlLink')}))"
    except Exception as e:
        return f"❌ Failed to create Calendar event: {str(e)}"


# ---------------------------------------------------------------------------
# 2. Microsoft Outlook / Graph API Integration
# ---------------------------------------------------------------------------

def get_ms_graph_token() -> Optional[str]:
    """Acquires Microsoft Graph API access token via OAuth refresh token."""
    client_id = os.getenv("MICROSOFT_CLIENT_ID")
    client_secret = os.getenv("MICROSOFT_CLIENT_SECRET")
    tenant_id = os.getenv("MICROSOFT_TENANT_ID", "common")
    refresh_token = os.getenv("MICROSOFT_REFRESH_TOKEN")

    if not client_id or not client_secret:
        return None

    if refresh_token:
        try:
            url = f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token"
            data = {
                "client_id": client_id,
                "client_secret": client_secret,
                "grant_type": "refresh_token",
                "refresh_token": refresh_token,
                "scope": "offline_access Mail.Read Mail.Send Calendars.Read"
            }
            resp = requests.post(url, data=data, timeout=10)
            if resp.status_code == 200:
                res_data = resp.json()
                # If a new refresh token is returned, update .env
                if "refresh_token" in res_data and res_data["refresh_token"] != refresh_token:
                    os.environ["MICROSOFT_REFRESH_TOKEN"] = res_data["refresh_token"]
                return res_data.get("access_token")
            else:
                logger.warning(f"Failed to refresh MS Graph token: {resp.status_code} {resp.text}")
        except Exception as e:
            logger.warning(f"Error acquiring MS Graph token: {e}")

    try:
        from msal import ConfidentialClientApplication
        authority = f"https://login.microsoftonline.com/{tenant_id}"
        app = ConfidentialClientApplication(client_id, client_credential=client_secret, authority=authority)
        result = app.acquire_token_for_client(scopes=["https://graph.microsoft.com/.default"])
        if "access_token" in result:
            return result["access_token"]
    except Exception as e:
        logger.warning(f"Error with MSAL client credentials: {e}")

    return None


def list_outlook_emails(max_results: int = 5) -> str:
    """Lists recent emails from Outlook via Microsoft Graph API."""
    token = get_ms_graph_token()
    if not token:
        return (
            "⚠️ Microsoft Outlook access requires `MICROSOFT_CLIENT_ID`, `MICROSOFT_CLIENT_SECRET`, "
            "and `MICROSOFT_REFRESH_TOKEN` / `MICROSOFT_TENANT_ID` in `.env`."
        )

    try:
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        resp = requests.get(
            f"https://graph.microsoft.com/v1.0/me/messages?$top={max_results}&$select=subject,from,receivedDateTime,bodyPreview",
            headers=headers,
            timeout=10
        )
        if resp.status_code == 200:
            data = resp.json()
            messages = data.get("value", [])
            if not messages:
                return "📧 No Outlook emails found."

            lines = []
            for m in messages:
                sender = m.get("from", {}).get("emailAddress", {}).get("name", "Unknown")
                lines.append(f"📩 **{m.get('subject')}**\n• From: `{sender}`\n• Date: {m.get('receivedDateTime')}\n• Preview: {m.get('bodyPreview', '')[:100]}...")
            return "📬 **Recent Outlook Emails:**\n\n" + "\n\n".join(lines)
        else:
            return f"❌ Outlook API error ({resp.status_code}): {resp.text}"

    except Exception as e:
        return f"❌ Failed to fetch Outlook emails: {str(e)}"


def send_outlook_email(to: str, subject: str, body: str) -> str:
    """Sends an email via Microsoft Graph API."""
    token = get_ms_graph_token()
    if not token:
        return "⚠️ Microsoft Outlook credentials required in `.env`."

    try:
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        payload = {
            "message": {
                "subject": subject,
                "body": {"contentType": "Text", "content": body},
                "toRecipients": [{"emailAddress": {"address": to}}]
            },
            "saveToSentItems": "true"
        }
        resp = requests.post("https://graph.microsoft.com/v1.0/me/sendMail", headers=headers, json=payload, timeout=10)
        if resp.status_code in [200, 202]:
            return f"✅ Outlook email sent successfully to `{to}`."
        return f"❌ Failed to send Outlook email ({resp.status_code}): {resp.text}"

    except Exception as e:
        return f"❌ Outlook send error: {str(e)}"


# ---------------------------------------------------------------------------
# 3. GitHub Account Integration (Repos, Issues, PRs)
# ---------------------------------------------------------------------------

def get_github_headers() -> Dict[str, str]:
    token = os.getenv("GITHUB_PERSONAL_ACCESS_TOKEN") or os.getenv("GITHUB_TOKEN") or ""
    headers = {
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "Alya-Rasa-Bot/1.0"
    }
    if token:
        headers["Authorization"] = f"token {token}"
    return headers


def list_github_repos(username_or_org: Optional[str] = None, max_results: int = 6) -> str:
    """Lists repositories for a user/org or authenticated user."""
    headers = get_github_headers()
    token = os.getenv("GITHUB_PERSONAL_ACCESS_TOKEN") or os.getenv("GITHUB_TOKEN")

    try:
        if username_or_org:
            url = f"https://api.github.com/users/{username_or_org}/repos?sort=updated&per_page={max_results}"
        elif token:
            url = f"https://api.github.com/user/repos?sort=updated&per_page={max_results}"
        else:
            return (
                "⚠️ GitHub access requires either specifying a public username (e.g. `list repos for octocat`) "
                "or adding `GITHUB_PERSONAL_ACCESS_TOKEN` to `.env`."
            )

        resp = requests.get(url, headers=headers, timeout=10)
        if resp.status_code == 200:
            repos = resp.json()
            if not repos:
                return "🐙 No repositories found."

            lines = []
            for r in repos:
                desc = r.get("description") or "No description"
                stars = r.get("stargazers_count", 0)
                forks = r.get("forks_count", 0)
                lang = r.get("language") or "Code"
                lines.append(f"📁 [{r.get('name')}]({r.get('html_url')}) ⭐ {stars} | 🍴 {forks} | `{lang}`\n   _{desc}_")
            return f"🐙 **GitHub Repositories ({username_or_org or 'Authenticated User'}):**\n\n" + "\n\n".join(lines)
        else:
            return f"❌ GitHub API Error ({resp.status_code}): {resp.json().get('message', resp.text)}"

    except Exception as e:
        return f"❌ Failed to fetch GitHub repos: {str(e)}"


def list_github_issues(repo: str, state: str = "open", max_results: int = 5) -> str:
    """Lists issues in a repository (owner/repo)."""
    headers = get_github_headers()
    try:
        url = f"https://api.github.com/repos/{repo}/issues?state={state}&per_page={max_results}"
        resp = requests.get(url, headers=headers, timeout=10)
        if resp.status_code == 200:
            issues = resp.json()
            # Filter out pull requests
            issues = [i for i in issues if "pull_request" not in i]
            if not issues:
                return f"🐙 No {state} issues found in `{repo}`."

            lines = []
            for i in issues:
                lines.append(f"🐞 [#{i.get('number')} {i.get('title')}]({i.get('html_url')}) by @{i.get('user', {}).get('login')} ({i.get('state')})")
            return f"🐙 **GitHub Issues for `{repo}`:**\n\n" + "\n".join(lines)
        return f"❌ GitHub API error ({resp.status_code}): {resp.text}"
    except Exception as e:
        return f"❌ Failed to list GitHub issues: {str(e)}"


def create_github_issue(repo: str, title: str, body: str = "") -> str:
    """Creates a new issue in a GitHub repository."""
    headers = get_github_headers()
    token = os.getenv("GITHUB_PERSONAL_ACCESS_TOKEN") or os.getenv("GITHUB_TOKEN")
    if not token:
        return "⚠️ `GITHUB_PERSONAL_ACCESS_TOKEN` is required in `.env` to create GitHub issues."

    try:
        url = f"https://api.github.com/repos/{repo}/issues"
        payload = {"title": title, "body": body}
        resp = requests.post(url, headers=headers, json=payload, timeout=10)
        if resp.status_code == 201:
            data = resp.json()
            return f"✅ GitHub issue created: [#{data.get('number')} {title}]({data.get('html_url')})"
        return f"❌ Failed to create issue ({resp.status_code}): {resp.text}"
    except Exception as e:
        return f"❌ GitHub issue error: {str(e)}"


def list_github_prs(repo: str, state: str = "open", max_results: int = 5) -> str:
    """Lists pull requests for a repository."""
    headers = get_github_headers()
    try:
        url = f"https://api.github.com/repos/{repo}/pulls?state={state}&per_page={max_results}"
        resp = requests.get(url, headers=headers, timeout=10)
        if resp.status_code == 200:
            prs = resp.json()
            if not prs:
                return f"🐙 No {state} pull requests in `{repo}`."
            lines = []
            for pr in prs:
                lines.append(f"🔀 [#{pr.get('number')} {pr.get('title')}]({pr.get('html_url')}) by @{pr.get('user', {}).get('login')} (`{pr.get('head', {}).get('ref')}` -> `{pr.get('base', {}).get('ref')}`)")
            return f"🐙 **GitHub Pull Requests for `{repo}`:**\n\n" + "\n".join(lines)
        return f"❌ GitHub API error ({resp.status_code}): {resp.text}"
    except Exception as e:
        return f"❌ Failed to fetch PRs: {str(e)}"
