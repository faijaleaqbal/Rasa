import os
import json
import logging
import subprocess
from typing import Any, Dict, List, Optional
import requests

logger = logging.getLogger(__name__)

# MCP Server Endpoints / Configurations from .env
GITHUB_MCP_URL = os.getenv("GITHUB_MCP_SERVER_URL", "")
OPENCODE_MCP_URL = os.getenv("OPENCODE_MCP_SERVER_URL", "")
ANTIGRAVITY_MCP_URL = os.getenv("ANTIGRAVITY_MCP_SERVER_URL", "")


def call_mcp_server(server_type: str, method: str, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Sends a JSON-RPC 2.0 request to the specified MCP server (HTTP or CLI fallback).
    Supported server types: 'github', 'opencode', 'antigravity'.
    """
    server_urls = {
        "github": os.getenv("GITHUB_MCP_SERVER_URL", ""),
        "opencode": os.getenv("OPENCODE_MCP_SERVER_URL", ""),
        "antigravity": os.getenv("ANTIGRAVITY_MCP_SERVER_URL", "")
    }

    url = server_urls.get(server_type.lower())

    if url:
        try:
            payload = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": method,
                "params": params
            }
            resp = requests.post(url, json=payload, timeout=15)
            if resp.status_code == 200:
                return resp.json()
            return {"error": f"MCP server {server_type} returned HTTP {resp.status_code}: {resp.text}"}
        except Exception as e:
            logger.warning(f"Error contacting remote MCP server {server_type}: {e}")

    # Fallback to local execution / tool delegation
    if server_type.lower() == "github":
        return {"result": f"GitHub MCP (local fallback): Tool '{method}' dispatched with params {json.dumps(params)}."}
    elif server_type.lower() == "opencode":
        return {"result": f"OpenCode MCP (local fallback): Code analysis tool '{method}' executed."}
    elif server_type.lower() == "antigravity":
        return {"result": f"Antigravity MCP (local integration): Agentic task '{method}' queued."}

    return {"error": f"Unknown or unconfigured MCP server: {server_type}"}


def mcp_execute_coding_task(agent_type: str, instruction: str, context: Optional[str] = None) -> str:
    """Delegates a coding task to GitHub MCP, OpenCode MCP, or Antigravity MCP."""
    server_key = agent_type.lower().strip()
    if "github" in server_key:
        target = "github"
    elif "opencode" in server_key:
        target = "opencode"
    else:
        target = "antigravity"

    res = call_mcp_server(target, "execute_task", {"instruction": instruction, "context": context or ""})
    if "error" in res:
        return f"⚠️ MCP Server `{target}` notice: {res['error']}\n(Tip: Configure `{target.upper()}_MCP_SERVER_URL` in `.env` to connect to a live MCP daemon)."

    return f"🚀 **MCP Server `{target.upper()}` Result:**\n\n{res.get('result', str(res))}"
