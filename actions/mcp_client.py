"""
MCP Client and OpenCode Integration for Alya.
Connects to headless OpenCode MCP server (Port 4096), GitHub MCP (Port 4097),
and provides direct, genuine shell execution without synthetic placeholder responses.
"""

import os
import re
import json
import logging
import subprocess
from typing import Any, Dict, List, Optional, Tuple
import requests
from requests.auth import HTTPBasicAuth
from dotenv import load_dotenv

load_dotenv("/home/ubuntu/Rasa/.env")
logger = logging.getLogger(__name__)

# MCP Server Endpoints / Configurations
GITHUB_MCP_URL = os.getenv("GITHUB_MCP_SERVER_URL", "http://127.0.0.1:4097")
OPENCODE_MCP_URL = os.getenv("OPENCODE_MCP_SERVER_URL", "http://127.0.0.1:4096")
OPENCODE_PASSWORD = os.getenv("OPENCODE_SERVER_PASSWORD", "Faijal@1626")
DEFAULT_WORKING_DIR = "/home/ubuntu/Rasa"


def execute_shell_command(
    command: str,
    cwd: Optional[str] = None,
    timeout: int = 30
) -> Dict[str, Any]:
    """
    Executes a shell command directly on the host system within the requested working directory.
    Returns real stdout, stderr, exit code, and execution status.
    """
    effective_cwd = cwd or DEFAULT_WORKING_DIR
    
    # 1. Validate working directory
    if not os.path.exists(effective_cwd):
        return {
            "stdout": "",
            "stderr": f"Error: Configured working directory '{effective_cwd}' does not exist.",
            "exit_code": 1,
            "status": "error",
            "cwd": effective_cwd
        }
    if not os.path.isdir(effective_cwd):
        return {
            "stdout": "",
            "stderr": f"Error: Configured working directory '{effective_cwd}' is not a directory.",
            "exit_code": 1,
            "status": "error",
            "cwd": effective_cwd
        }

    # 2. Execute process with safety timeout
    try:
        proc = subprocess.run(
            command,
            shell=True,
            cwd=effective_cwd,
            capture_output=True,
            text=True,
            timeout=timeout
        )
        return {
            "stdout": proc.stdout,
            "stderr": proc.stderr,
            "exit_code": proc.returncode,
            "status": "success" if proc.returncode == 0 else "failed",
            "cwd": effective_cwd
        }
    except subprocess.TimeoutExpired:
        return {
            "stdout": "",
            "stderr": f"Execution timed out after {timeout} seconds.",
            "exit_code": 124,
            "status": "timeout",
            "cwd": effective_cwd
        }
    except PermissionError:
        return {
            "stdout": "",
            "stderr": "Shell execution unavailable/denied: insufficient permissions.",
            "exit_code": 126,
            "status": "denied",
            "cwd": effective_cwd
        }
    except Exception as e:
        return {
            "stdout": "",
            "stderr": f"Subprocess execution error: {str(e)}",
            "exit_code": 1,
            "status": "error",
            "cwd": effective_cwd
        }


def format_shell_response(result: Dict[str, Any], command: str) -> str:
    """Formats real execution output into clean markdown response."""
    exit_code = result.get("exit_code", 0)
    stdout = result.get("stdout", "")
    stderr = result.get("stderr", "")
    cwd = result.get("cwd", DEFAULT_WORKING_DIR)

    lines = []
    status_icon = "✅" if exit_code == 0 else "❌"
    lines.append(f"💻 **OpenCode Shell Execution** {status_icon} (Exit Code: `{exit_code}`)")
    lines.append(f"• **Directory**: `{cwd}`")
    lines.append(f"• **Command**: `{command}`\n")

    if stdout:
        lines.append("```bash\n" + stdout.rstrip() + "\n```")
    if stderr:
        if stdout:
            lines.append("**Errors / Stderr:**")
        lines.append("```bash\n" + stderr.rstrip() + "\n```")

    if not stdout and not stderr:
        lines.append("*(Command completed with no output)*")

    return "\n".join(lines)


def is_explicit_explanation_request(text: str) -> bool:
    """Detects if user is asking to explain or teach rather than execute."""
    t = text.lower().strip()
    explanation_triggers = [
        "explain", "what does", "what is", "how does", "tutorial", "meaning of",
        "describe", "teach me", "syntax of", "difference between"
    ]
    return any(t.startswith(trig) or f" {trig} " in t for trig in explanation_triggers)


def is_code_generation_request(text: str) -> bool:
    """Detects if user is asking to write/generate a full software script or module."""
    t = text.lower().strip()
    code_triggers = [
        "write a script", "write a python", "create a function", "generate code",
        "build an app", "implement a class", "write an algorithm"
    ]
    return any(trig in t for trig in code_triggers)


def call_mcp_server(server_type: str, method: str, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Sends a request to the specified MCP server with proper authentication and execution.
    Supported server types: 'opencode', 'shell', 'exec', 'github', 'sqlite', 'puppeteer', 'memory'.
    """
    server_key = server_type.lower().strip()

    # 1. Shell Execution MCP Tool
    if server_key in ["shell", "exec", "terminal", "bash", "sh"]:
        cmd = params.get("command", "")
        cwd = params.get("cwd")
        timeout = int(params.get("timeout", 30))
        exec_res = execute_shell_command(cmd, cwd=cwd, timeout=timeout)
        return {
            "result": {
                "content": [{"type": "text", "text": format_shell_response(exec_res, cmd)}],
                "details": exec_res
            }
        }

    # 2. SQLite Database MCP
    if server_key in ["sqlite", "database", "db"]:
        from . import skills_developer_tools as dev
        q = params.get("query", "")
        uid = params.get("user_id", "default")
        res_text = dev.query_sqlite_database(q, uid)
        return {"result": {"content": [{"type": "text", "text": res_text}]}}

    # 3. Puppeteer / Web Screenshot MCP
    elif server_key in ["puppeteer", "browser", "screenshot"]:
        from . import skills_developer_tools as dev
        url = params.get("url", "")
        res_dict = dev.capture_website_screenshot(url)
        return {"result": res_dict}

    # 4. Knowledge Graph Memory MCP
    elif server_key in ["memory", "knowledge_graph", "kg"]:
        from . import skills_developer_tools as dev
        act = params.get("action", "list")
        entity = params.get("entity", "")
        rel = params.get("relation", "")
        target = params.get("target", "")
        uid = params.get("user_id", "default")
        res_text = dev.manage_knowledge_graph(act, entity, rel, target, uid)
        return {"result": {"content": [{"type": "text", "text": res_text}]}}

    # 5. Filesystem & Server Logs MCP
    elif server_key in ["filesystem", "files", "logs"]:
        from . import skills_developer_tools as dev
        svc = params.get("service", "rasa-bot")
        lines = params.get("lines", 20)
        res_text = dev.view_server_logs(svc, lines)
        return {"result": {"content": [{"type": "text", "text": res_text}]}}

    # 6. Remote HTTP MCP Servers (OpenCode, GitHub)
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


def mcp_execute_coding_task(
    agent_type: str,
    instruction: str,
    context: Optional[str] = None,
    cwd: Optional[str] = None
) -> str:
    """
    Handles OpenCode and GitHub MCP requests.
    If the instruction is a direct shell command (e.g. 'ls -la', 'pwd', 'whoami', 'uname -a'),
    it EXECUTES the command directly and returns genuine process results.
    """
    server_key = agent_type.lower().strip()
    clean_task = instruction.strip()

    if not clean_task:
        return "Usage: `/code <command or task>` (e.g. `/code ls -la`, `/code git status`)"

    # 1. OpenCode Direct Command / Shell Execution vs Explanation
    if "opencode" in server_key or "code" in server_key or "antigravity" in server_key or "shell" in server_key:
        # Check if user explicitly asked for an explanation
        if is_explicit_explanation_request(clean_task):
            try:
                groq_key = os.getenv("GROQ_API_KEY")
                if groq_key:
                    from groq import Groq
                    client = Groq(api_key=groq_key)
                    resp = client.chat.completions.create(
                        model="qwen/qwen3.6-27b",
                        messages=[
                            {"role": "system", "content": "You are a Linux and OpenCode expert. Provide a concise explanation with clear syntax breakdown."},
                            {"role": "user", "content": f"Explain this command or concept clearly: {clean_task}"}
                        ],
                        temperature=0.2,
                        max_tokens=800
                    )
                    explanation = resp.choices[0].message.content
                    clean_expl = re.sub(r"<think>.*?</think>", "", explanation, flags=re.DOTALL).strip()
                    return f"📖 **Command Explanation:**\n\n{clean_expl}"
            except Exception as e:
                logger.warning(f"Explanation generation error: {e}")

        # Check if user is asking to synthesize new code
        elif is_code_generation_request(clean_task):
            try:
                groq_key = os.getenv("GROQ_API_KEY")
                if groq_key:
                    from groq import Groq
                    client = Groq(api_key=groq_key)
                    resp = client.chat.completions.create(
                        model="qwen/qwen3.6-27b",
                        messages=[
                            {"role": "system", "content": "You are a senior software engineer. Write clean, modular, production-ready code with minimal preamble."},
                            {"role": "user", "content": f"TASK: {clean_task}\n{f'CONTEXT: {context}' if context else ''}"}
                        ],
                        temperature=0.2,
                        max_tokens=1500
                    )
                    code_res = resp.choices[0].message.content
                    clean_output = re.sub(r"<think>.*?</think>", "", code_res, flags=re.DOTALL).strip()
                    return f"💻 **OpenCode Generated Code:**\n\n{clean_output}"
            except Exception as e:
                logger.warning(f"Coding generation error: {e}")

        # Otherwise: ACTUAL SHELL EXECUTION
        exec_res = execute_shell_command(clean_task, cwd=cwd)
        return format_shell_response(exec_res, clean_task)

    # 2. GitHub MCP Delegation
    res = call_mcp_server("github", "tools/list", {})
    if "error" in res:
        return f"⚠️ MCP Server `github` notice: {res['error']}"

    return f"🚀 **GitHub MCP Server (Port 4097):** Connected with {len(res.get('result', {}).get('tools', []))} active tools."
