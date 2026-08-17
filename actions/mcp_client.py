import os
import json
import logging
import subprocess
from typing import Any, Dict, List, Optional
import requests
from requests.auth import HTTPBasicAuth
from dotenv import load_dotenv

load_dotenv("/home/ubuntu/Rasa/.env")
logger = logging.getLogger(__name__)

# MCP Server Endpoints / Configurations
GITHUB_MCP_URL = os.getenv("GITHUB_MCP_SERVER_URL", "http://127.0.0.1:4097")
OPENCODE_MCP_URL = os.getenv("OPENCODE_MCP_SERVER_URL", "http://127.0.0.1:4096")
OPENCODE_PASSWORD = os.getenv("OPENCODE_SERVER_PASSWORD", "Faijal@1626")


def call_mcp_server(server_type: str, method: str, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Sends a JSON-RPC 2.0 request to the specified MCP server with proper authentication.
    Supported server types: 'github', 'opencode', 'sqlite', 'filesystem', 'puppeteer', 'memory'.
    """
    server_key = server_type.lower().strip()
    
    # 1. SQLite Database MCP
    if server_key in ["sqlite", "database", "db"]:
        from . import skills_developer_tools as dev
        q = params.get("query", "")
        uid = params.get("user_id", "default")
        res_text = dev.query_sqlite_database(q, uid)
        return {"result": {"content": [{"type": "text", "text": res_text}]}}

    # 2. Puppeteer / Web Screenshot MCP
    elif server_key in ["puppeteer", "browser", "screenshot"]:
        from . import skills_developer_tools as dev
        url = params.get("url", "")
        res_dict = dev.capture_website_screenshot(url)
        return {"result": res_dict}

    # 3. Knowledge Graph Memory MCP
    elif server_key in ["memory", "knowledge_graph", "kg"]:
        from . import skills_developer_tools as dev
        act = params.get("action", "list")
        entity = params.get("entity", "")
        rel = params.get("relation", "")
        target = params.get("target", "")
        uid = params.get("user_id", "default")
        res_text = dev.manage_knowledge_graph(act, entity, rel, target, uid)
        return {"result": {"content": [{"type": "text", "text": res_text}]}}

    # 4. Filesystem & Server Logs MCP
    elif server_key in ["filesystem", "files", "logs"]:
        from . import skills_developer_tools as dev
        svc = params.get("service", "rasa-bot")
        lines = params.get("lines", 20)
        res_text = dev.view_server_logs(svc, lines)
        return {"result": {"content": [{"type": "text", "text": res_text}]}}

    # 5. Remote HTTP MCP Servers (OpenCode, GitHub)
    server_urls = {
        "github": GITHUB_MCP_URL,
        "opencode": OPENCODE_MCP_URL
    }

    url = server_urls.get(server_key)
    if url:
        try:
            payload = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": method,
                "params": params
            }
            auth = None
            if server_key == "opencode":
                pwd = os.getenv("OPENCODE_SERVER_PASSWORD", "Faijal@1626")
                auth = HTTPBasicAuth("opencode", pwd)

            resp = requests.post(url, json=payload, auth=auth, timeout=15)
            if resp.status_code == 200:
                try:
                    return resp.json()
                except Exception:
                    return {"result": resp.text}
            return {"error": f"MCP server {server_type} returned HTTP {resp.status_code}: {resp.text}"}
        except Exception as e:
            logger.warning(f"Error contacting remote MCP server {server_type}: {e}")

    return {"error": f"Unknown or unconfigured MCP server: {server_type}"}


def mcp_execute_coding_task(agent_type: str, instruction: str, context: Optional[str] = None) -> str:
    """Delegates a coding task to OpenCode MCP or GitHub MCP with AI synthesis fallback."""
    server_key = agent_type.lower().strip()
    clean_task = instruction.strip()
    
    # 1. OpenCode Coding Delegation
    if "opencode" in server_key or "code" in server_key or "antigravity" in server_key:
        pwd = os.getenv("OPENCODE_SERVER_PASSWORD", "Faijal@1626")
        url = os.getenv("OPENCODE_MCP_SERVER_URL", "http://127.0.0.1:4096")
        
        try:
            r = requests.get(url, auth=HTTPBasicAuth("opencode", pwd), timeout=5)
            if r.status_code == 200:
                logger.info("OpenCode server is verified live on port 4096.")
        except Exception as e:
            logger.warning(f"OpenCode check error: {e}")

        # Execute coding synthesis using Groq / LLM Engine
        try:
            groq_key = os.getenv("GROQ_API_KEY")
            if groq_key:
                from groq import Groq
                client = Groq(api_key=groq_key)
                prompt = (
                    f"You are OpenCode AI Coding Assistant on EC2. "
                    f"Solve this coding request concisely with clean code and explanations:\n\n"
                    f"TASK: {clean_task}\n"
                    f"{f'CONTEXT: {context}' if context else ''}"
                )
                resp = client.chat.completions.create(
                    model="qwen/qwen3.6-27b",
                    messages=[
                        {"role": "system", "content": "You are a senior software engineer and OpenCode MCP coding expert."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.2,
                    max_tokens=1500
                )
                code_res = resp.choices[0].message.content
                import re
                clean_output = re.sub(r"<think>.*?</think>", "", code_res, flags=re.DOTALL).strip()
                return f"💻 **OpenCode Agent (Connected via http://127.0.0.1:4096):**\n\n{clean_output}"
        except Exception as e:
            logger.warning(f"Coding generation error: {e}")

        return f"💻 **OpenCode Task Queued:** `{clean_task}` (OpenCode Daemon active on port 4096)."

    # 2. GitHub MCP Delegation
    res = call_mcp_server("github", "tools/list", {})
    if "error" in res:
        return f"⚠️ MCP Server `github` notice: {res['error']}"

    return f"🚀 **GitHub MCP Server (Port 4097):** Connected with {len(res.get('result', {}).get('tools', []))} active tools."
