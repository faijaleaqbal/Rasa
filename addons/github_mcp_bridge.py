#!/usr/bin/env python3
"""
GitHub MCP HTTP Bridge Server
Wraps the official @modelcontextprotocol/server-github stdio server in a fast HTTP JSON-RPC 2.0 API on port 4097.
"""

import os
import json
import logging
import subprocess
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from dotenv import load_dotenv

load_dotenv("/home/ubuntu/Rasa/.env")

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("github_mcp_bridge")

PORT = int(os.getenv("GITHUB_MCP_PORT", 4097))
HOST = "0.0.0.0"

class GitHubMCPProcess:
    def __init__(self):
        self.lock = threading.Lock()
        self.proc = None
        self._start_process()

    def _start_process(self):
        token = os.getenv("GITHUB_PERSONAL_ACCESS_TOKEN", "")
        env = os.environ.copy()
        env["GITHUB_PERSONAL_ACCESS_TOKEN"] = token
        
        logger.info("Starting GitHub MCP stdio process (/usr/bin/mcp-server-github)...")
        self.proc = subprocess.Popen(
            ["/usr/bin/mcp-server-github"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
            env=env
        )

        # Send initialize request
        init_req = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "AlyaMCPBridge", "version": "1.0"}
            }
        }
        self.proc.stdin.write(json.dumps(init_req) + "\n")
        self.proc.stdin.flush()
        init_resp = self.proc.stdout.readline()
        logger.info(f"GitHub MCP Initialized: {init_resp.strip()[:100]}")

    def call_rpc(self, payload: dict) -> dict:
        with self.lock:
            try:
                if self.proc.poll() is not None:
                    logger.warning("GitHub MCP process died, restarting...")
                    self._start_process()

                req_str = json.dumps(payload)
                self.proc.stdin.write(req_str + "\n")
                self.proc.stdin.flush()

                res_str = self.proc.stdout.readline()
                if not res_str:
                    return {"jsonrpc": "2.0", "error": {"code": -32603, "message": "Empty response from MCP server"}, "id": payload.get("id", 1)}
                
                return json.loads(res_str)
            except Exception as e:
                logger.error(f"RPC communication error: {e}")
                return {"jsonrpc": "2.0", "error": {"code": -32603, "message": str(e)}, "id": payload.get("id", 1)}

mcp_process = GitHubMCPProcess()


class MCPHTTPHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path in ["/", "/health", "/status"]:
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({
                "status": "healthy",
                "service": "GitHub MCP Server Bridge",
                "mcp_version": "0.6.2",
                "protocol_version": "2024-11-05"
            }).encode("utf-8"))
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        try:
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length).decode("utf-8")
            payload = json.loads(body)

            resp_data = mcp_process.call_rpc(payload)

            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(resp_data).encode("utf-8"))
        except Exception as e:
            logger.error(f"HTTP Handler error: {e}")
            self.send_response(500)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"error": str(e)}).encode("utf-8"))

    def log_message(self, format, *args):
        # Suppress verbose default access logs
        pass


def run_server():
    server = HTTPServer((HOST, PORT), MCPHTTPHandler)
    logger.info(f"GitHub MCP HTTP Server listening on http://{HOST}:{PORT}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    run_server()
