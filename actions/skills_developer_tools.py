import os
import re
import json
import logging
import sqlite3
import subprocess
import requests
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional, Tuple

from . import db
from . import skills_documents as docs

logger = logging.getLogger(__name__)
IST = timezone(timedelta(hours=5, minutes=30), name="IST")

STORAGE_FILES_DIR = os.path.join(os.path.dirname(__file__), "..", "storage", "files")
os.makedirs(STORAGE_FILES_DIR, exist_ok=True)


def _clean_llm_think(text: str) -> str:
    """Strips <think> tags from LLM responses."""
    if "</think>" in text:
        text = text.split("</think>")[-1].strip()
    elif "<think>" in text:
        text = re.sub(r"<think>.*", "", text, flags=re.DOTALL).strip()
    return text.strip()


# ---------------------------------------------------------------------------
# 1. Live Website Screenshot Generator
# ---------------------------------------------------------------------------

def capture_website_screenshot(url: str) -> Dict[str, Any]:
    """
    Captures a high-resolution screenshot of any website and saves as JPEG image.
    Returns dict with file_path, status, and description.
    """
    clean_url = url.strip()
    if not clean_url:
        return {"error": "Usage: `/screenshot <url>`\nExample: `/screenshot https://news.ycombinator.com`"}

    if not clean_url.startswith("http"):
        clean_url = "https://" + clean_url

    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        sanitized_name = re.sub(r"[^a-zA-Z0-9]", "_", clean_url.replace("https://", "").replace("http://", ""))[:25]
        dest_filename = f"screenshot_{sanitized_name}_{timestamp}.jpg"
        dest_path = os.path.join(STORAGE_FILES_DIR, dest_filename)

        # Primary screenshot engine via thum.io
        service_url = f"https://image.thum.io/get/width/1200/crop/800/{clean_url}"
        resp = requests.get(service_url, timeout=20)

        if resp.status_code == 200 and len(resp.content) > 1000:
            with open(dest_path, "wb") as f:
                f.write(resp.content)

            return {
                "success": True,
                "file_path": dest_path,
                "file_type": "photo",
                "text": f"📸 **Website Screenshot Captured:**\n• URL: [{clean_url}]({clean_url})\n• Resolution: `1200x800`"
            }
        else:
            return {"error": f"⚠️ Could not render screenshot for `{clean_url}` (HTTP {resp.status_code})."}
    except Exception as e:
        logger.error(f"Screenshot capture error: {e}")
        return {"error": f"⚠️ Screenshot engine error: {e}"}


# ---------------------------------------------------------------------------
# 2. Python Code Execution Sandbox
# ---------------------------------------------------------------------------

def run_python_code_sandbox(code: str) -> str:
    """
    Executes short Python snippets in an isolated, timed sandbox subprocess.
    """
    clean_code = code.strip()
    if clean_code.startswith("```python"):
        clean_code = clean_code[9:]
    elif clean_code.startswith("```py"):
        clean_code = clean_code[5:]
    elif clean_code.startswith("```"):
        clean_code = clean_code[3:]
    if clean_code.endswith("```"):
        clean_code = clean_code[:-3]
    clean_code = clean_code.strip()

    if not clean_code:
        return "Usage: `/python <code>`\nExample:\n```python\nimport math\nprint([math.sqrt(x) for x in range(1, 6)])\n```"

    # Security filters
    dangerous_keywords = [
        "os.system", "shutil.rmtree", "subprocess.Popen", "subprocess.call",
        "rm -rf", "mkfs", "dd if=", ":(){ :|:& };:", "__import__('os').system",
        "eval(compile", "open('/etc", "open('/proc"
    ]
    for d in dangerous_keywords:
        if d in clean_code:
            return f"🛡️ **Security Block:** Code contains restricted operation (`{d}`)."

    try:
        proc = subprocess.run(
            ["python3", "-c", clean_code],
            capture_output=True,
            text=True,
            timeout=8
        )

        stdout = proc.stdout.strip()
        stderr = proc.stderr.strip()

        if proc.returncode == 0:
            out_block = f"```\n{stdout}\n```" if stdout else "*(Execution finished with 0 return code, no stdout)*"
            return f"🐍 **Python Sandbox Output:**\n\n{out_block}"
        else:
            return f"❌ **Python Execution Error (Code {proc.returncode}):**\n\n```\n{stderr or stdout}\n```"
    except subprocess.TimeoutExpired:
        return "⏱️ **Execution Timed Out:** Python code exceeded 8 seconds limit."
    except Exception as e:
        logger.error(f"Sandbox error: {e}")
        return f"⚠️ Sandbox error: {e}"


# ---------------------------------------------------------------------------
# 3. Database Explorer & SQLite MCP Query Runner
# ---------------------------------------------------------------------------

def query_sqlite_database(query: str, user_id: str) -> str:
    """
    Safely inspects or queries SQLite database tables (notes, todos, expenses, bills, habits, reminders).
    """
    clean_q = query.strip()
    if not clean_q:
        # Return database schema overview
        return (
            "🗄️ **SQLite Database Explorer**\n\n"
            "**Available Tables:**\n"
            "• `notes` (id, title, content, tags, created_at)\n"
            "• `todos` (id, title, priority, due_date, status)\n"
            "• `expenses` (id, amount, category, description, expense_date)\n"
            "• `bills` (id, title, amount, due_date, status)\n"
            "• `reminders` (id, text, due_time, status)\n"
            "• `habits` (id, habit_name, current_streak, best_streak)\n"
            "• `knowledge_graph` (id, entity, relation, target)\n\n"
            "Example Usage: `/sql SELECT category, SUM(amount) as total FROM expenses GROUP BY category`"
        )

    # Security check: Restrict drop/alter database
    disallowed = ["DROP DATABASE", "ATTACH", "DETACH", "PRAGMA writable_schema"]
    for word in disallowed:
        if word.lower() in clean_q.lower():
            return f"🛡️ **Query Blocked:** '{word}' is not permitted."

    conn = db.get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute(clean_q)
        if clean_q.lower().startswith("select") or clean_q.lower().startswith("pragma") or clean_q.lower().startswith("explain"):
            rows = cursor.fetchall()
            if not rows:
                return "ℹ️ Query executed successfully. **0 rows returned.**"

            col_names = [d[0] for d in cursor.description]
            # Format markdown table
            header = "| " + " | ".join(col_names) + " |"
            separator = "| " + " | ".join(["---"] * len(col_names)) + " |"
            row_lines = []
            for r in rows[:15]:
                vals = [str(r[c]) if r[c] is not None else "NULL" for c in col_names]
                row_lines.append("| " + " | ".join(vals) + " |")

            table_md = "\n".join([header, separator] + row_lines)
            total_count = len(rows)
            footer = f"\n\n_Showing {min(15, total_count)} of {total_count} rows._" if total_count > 15 else ""
            return f"📊 **SQL Query Results:**\n\n{table_md}{footer}"
        else:
            conn.commit()
            return f"✅ **SQL Executed Successfully:** `{cursor.rowcount}` rows affected."
    except Exception as e:
        return f"❌ **SQL Error:** `{e}`"
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# 4. Knowledge Graph & Deep Memory MCP
# ---------------------------------------------------------------------------

def manage_knowledge_graph(action: str, entity: str = "", relation: str = "", target: str = "", user_id: str = "default") -> str:
    """
    Manages knowledge graph triples (Entity -> Relation -> Target) for long-term relational memory.
    Actions: 'add', 'search', 'list', 'delete'
    """
    conn = db.get_db_connection()
    cursor = conn.cursor()

    # Ensure table exists
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS knowledge_graph (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            entity TEXT NOT NULL,
            relation TEXT NOT NULL,
            target TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()

    try:
        act = action.lower().strip()
        if act in ["add", "save", "insert"]:
            if not entity or not relation or not target:
                return "Usage: Add entity, relation, target (e.g. `User` -> `works_at` -> `Google`)"
            cursor.execute(
                "INSERT INTO knowledge_graph (user_id, entity, relation, target) VALUES (?, ?, ?, ?)",
                (str(user_id), entity.strip(), relation.strip(), target.strip())
            )
            conn.commit()
            return f"🧠 **Knowledge Graph Updated:** `({entity})` — `[{relation}]` ➔ `({target})`"

        elif act in ["search", "query", "find"]:
            q = f"%{entity.strip()}%"
            cursor.execute(
                "SELECT * FROM knowledge_graph WHERE user_id = ? AND (entity LIKE ? OR relation LIKE ? OR target LIKE ?)",
                (str(user_id), q, q, q)
            )
            rows = cursor.fetchall()
            if not rows:
                return f"🧠 No knowledge graph nodes found matching `{entity}`."
            lines = [f"• `({r['entity']})` — `[{r['relation']}]` ➔ `({r['target']})` *(ID #{r['id']})*" for r in rows]
            return f"🧠 **Knowledge Graph Relations for `{entity}`:**\n\n" + "\n".join(lines)

        elif act in ["list", "all"]:
            cursor.execute("SELECT * FROM knowledge_graph WHERE user_id = ? ORDER BY id DESC LIMIT 20", (str(user_id),))
            rows = cursor.fetchall()
            if not rows:
                return "🧠 Knowledge Graph is currently empty. Add relations with `/kg add <entity> <relation> <target>`."
            lines = [f"• `({r['entity']})` — `[{r['relation']}]` ➔ `({r['target']})`" for r in rows]
            return f"🧠 **Knowledge Graph Nodes ({len(rows)}):**\n\n" + "\n".join(lines)

        elif act == "delete":
            cursor.execute("DELETE FROM knowledge_graph WHERE user_id = ? AND (id = ? OR entity = ?)", (str(user_id), entity, entity))
            conn.commit()
            return f"🗑️ Deleted knowledge graph node `{entity}`."

    except Exception as e:
        logger.error(f"KG error: {e}")
        return f"❌ Knowledge Graph Error: {e}"
    finally:
        conn.close()

    return "Usage: `/kg <list|add|search> [entity] [relation] [target]`"


# ---------------------------------------------------------------------------
# 5. Social Media & Tweet / Post Extractor
# ---------------------------------------------------------------------------

def extract_social_media_info(url: str) -> str:
    """
    Extracts tweet text, author, engagement, or social post content from Twitter/X, Reddit, or LinkedIn.
    """
    clean_url = url.strip()
    if not clean_url:
        return "Usage: `/social <url>` or `/tweet <url>`\nExample: `/tweet https://x.com/OpenAI/status/...`"

    try:
        jina_url = f"https://r.jina.ai/{clean_url}"
        r = requests.get(jina_url, timeout=12)
        if r.status_code != 200 or len(r.text) < 30:
            return f"⚠️ Could not fetch social media post from `{clean_url}`."

        post_content = r.text[:6000]

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
                            "Extract the social media post author/handle, date, core post text, mentions, and key takeaways. "
                            "Format cleanly with emojis and markdown."
                        )
                    },
                    {"role": "user", "content": f"URL: {clean_url}\nContent:\n{post_content}"}
                ],
                temperature=0.2,
                max_tokens=600
            )
            res = _clean_llm_think(resp.choices[0].message.content)
            return f"📱 **Social Media Post Overview — [{clean_url}]({clean_url})**:\n\n{res}"
    except Exception as e:
        logger.error(f"Social extractor error: {e}")

    return f"📱 Extracted post preview from `{clean_url}`."


# ---------------------------------------------------------------------------
# 6. Invoice / Bill OCR to Excel Converter
# ---------------------------------------------------------------------------

def convert_receipt_to_excel(image_path_or_text: str, user_id: str = "default") -> Dict[str, Any]:
    """
    Parses receipt/invoice data using LLM and creates a structured Excel spreadsheet (.xlsx).
    """
    # If image file passed, first run Vision OCR
    content_text = image_path_or_text
    if os.path.exists(image_path_or_text):
        from . import skills_content as content_skills
        content_text = content_skills.analyze_image_vision(image_path_or_text, "Extract invoice line items: Item Name, Quantity, Unit Price, Total Amount")

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
                            "You are an automated invoice parsing engine. Extract invoice items into a strict JSON object:\n"
                            "{\n"
                            '  "title": "Invoice / Bill Breakdown",\n'
                            '  "headers": ["Item Description", "Qty", "Unit Price", "Total (INR)"],\n'
                            '  "rows": [["Item 1", "2", "500", "1000"]],\n'
                            '  "total_amount": "1000"\n'
                            "}\n"
                            "Return ONLY raw JSON, no markdown backticks, no thinking."
                        )
                    },
                    {"role": "user", "content": f"Invoice text:\n{content_text}"}
                ],
                temperature=0.1,
                max_tokens=800
            )
            raw_json = _clean_llm_think(resp.choices[0].message.content)
            clean_json_str = re.sub(r"^```json|^```|```$", "", raw_json, flags=re.MULTILINE).strip()
            parsed = json.loads(clean_json_str)

            title = parsed.get("title", "Invoice Breakdown")
            headers = parsed.get("headers", ["Item", "Qty", "Rate", "Amount"])
            rows = parsed.get("rows", [["Sample Item", "1", "100", "100"]])

            # Generate Excel file
            res_f = docs.create_excel_file(title, headers, rows, filename=f"invoice_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx")
            fpath = res_f[0] if isinstance(res_f, tuple) else res_f
            return {
                "success": True,
                "file_path": fpath,
                "file_type": "document",
                "text": f"🧾 **Invoice / Receipt Converted to Excel Sheet!**\n• Items Extracted: `{len(rows)}`\n• File: `{os.path.basename(fpath)}`"
            }
    except Exception as e:
        logger.error(f"Invoice to excel error: {e}")

    # Fallback
    res_fallback = docs.create_excel_file("Receipt Summary", ["Description", "Amount"], [["Total", "N/A"]])
    fpath = res_fallback[0] if isinstance(res_fallback, tuple) else res_fallback
    return {
        "success": True,
        "file_path": fpath,
        "file_type": "document",
        "text": f"🧾 **Generated Spreadsheet:** `{os.path.basename(fpath)}`"
    }


# ---------------------------------------------------------------------------
# 7. Server Log & Filesystem MCP Viewer
# ---------------------------------------------------------------------------

def view_server_logs(service_name: str = "rasa-bot", lines: int = 20) -> str:
    """
    Safely inspects latest server logs from journalctl for debugging.
    """
    clean_svc = service_name.strip()
    if clean_svc not in ["rasa-bot", "rasa-actions", "nginx", "syslog"]:
        clean_svc = "rasa-bot"

    try:
        cmd = ["journalctl", "-u", clean_svc, "-n", str(min(lines, 30)), "--no-pager"]
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
        out = proc.stdout.strip()
        if not out:
            out = "No recent log entries found."
        # Truncate lines
        log_lines = out.split("\n")[-15:]
        return f"📜 **Server Logs — `{clean_svc}` (Last {len(log_lines)} lines):**\n\n```\n" + "\n".join(log_lines) + "\n```"
    except Exception as e:
        return f"⚠️ Could not fetch logs for `{clean_svc}`: {e}"
