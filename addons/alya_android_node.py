#!/usr/bin/env python3
"""
Alya Android Node — Complete Mobile AI Agent Bridge
Runs natively on Android (inside Termux or Python app) and connects to Alya AI Brain on EC2.

Requirements on Android (Termux):
  pkg install python termux-api
  pip install requests flask
"""

import os
import sys
import json
import subprocess
import requests
from flask import Flask, request, jsonify

app = Flask(__name__)

# Rasa EC2 Server Endpoint (Change to your public IP / Domain / Ngrok URL)
EC2_RASA_URL = os.getenv("RASA_SERVER_URL", "http://127.0.0.1:5005")


def run_termux_cmd(cmd_list):
    """Executes termux-api CLI commands on Android."""
    try:
        proc = subprocess.run(cmd_list, capture_output=True, text=True, timeout=10)
        return proc.stdout.strip()
    except Exception as e:
        return f"Error: {e}"


@app.route("/", methods=["GET"])
def index():
    return jsonify({
        "status": "online",
        "service": "Alya Android Node",
        "device": "Android Smartphone",
        "capabilities": ["make_call", "send_sms", "read_sms", "set_alarm", "set_timer", "open_target", "tts_speak", "voice_assistant"]
    })


@app.route("/execute", methods=["POST"])
def execute_action():
    """Receives commands from EC2 Rasa Server and executes on Android phone."""
    data = request.json or {}
    action = data.get("action")
    params = data.get("params", {})

    print(f"[*] Received Action: {action} with params: {params}")

    # 1. Make Phone Call
    if action == "make_call":
        phone = params.get("phone", "")
        run_termux_cmd(["termux-telephony-call", phone])
        return jsonify({"status": "executed", "action": "make_call", "phone": phone})

    # 2. Send SMS
    elif action == "send_sms":
        phone = params.get("phone", "")
        msg = params.get("message", "")
        run_termux_cmd(["termux-sms-send", "-n", phone, msg])
        return jsonify({"status": "executed", "action": "send_sms", "to": phone})

    # 3. Read SMS Inbox
    elif action == "read_sms":
        limit = str(params.get("limit", 5))
        out = run_termux_cmd(["termux-sms-list", "-l", limit])
        try:
            sms_list = json.loads(out)
            return jsonify({"status": "success", "messages": sms_list})
        except Exception:
            return jsonify({"status": "success", "raw": out})

    # 4. Set System Alarm
    elif action == "set_alarm":
        hour = str(params.get("hour", 7))
        minute = str(params.get("minute", 0))
        label = params.get("label", "Alya Alarm")
        # Trigger Android Alarm Intent
        cmd = [
            "am", "start", "-a", "android.intent.action.SET_ALARM",
            "--ei", "android.intent.extra.alarm.HOUR", hour,
            "--ei", "android.intent.extra.alarm.MINUTES", minute,
            "--es", "android.intent.extra.alarm.MESSAGE", label,
            "--ez", "android.intent.extra.alarm.SKIP_UI", "true"
        ]
        run_termux_cmd(cmd)
        run_termux_cmd(["termux-tts-speak", f"Alarm set for {hour}:{minute}"])
        return jsonify({"status": "executed", "alarm": f"{hour}:{minute}", "label": label})

    # 5. Set Timer
    elif action == "set_timer":
        seconds = str(params.get("seconds", 300))
        label = params.get("label", "Alya Timer")
        cmd = [
            "am", "start", "-a", "android.intent.action.SET_TIMER",
            "--ei", "android.intent.extra.alarm.LENGTH", seconds,
            "--es", "android.intent.extra.alarm.MESSAGE", label,
            "--ez", "android.intent.extra.alarm.SKIP_UI", "true"
        ]
        run_termux_cmd(cmd)
        return jsonify({"status": "executed", "timer_seconds": seconds})

    # 6. Open File / App
    elif action == "open_target":
        target = params.get("target", "")
        run_termux_cmd(["termux-open", target])
        return jsonify({"status": "executed", "target": target})

    # 7. Speak out loud (TTS)
    elif action == "tts_speak":
        text = params.get("text", "Hello")
        run_termux_cmd(["termux-tts-speak", text])
        return jsonify({"status": "spoken", "text": text})

    return jsonify({"status": "unknown_action", "action": action}), 400


def voice_loop():
    """Interactive Voice Loop on Phone: Tap Mic -> Speak -> Alya Brain -> Phone Action."""
    print("==================================================")
    print("       Alya Voice Agent — Android Console         ")
    print("==================================================")
    while True:
        try:
            input("\n👉 Press ENTER to Speak to Alya (or Ctrl+C to stop)... ")
            print("🎙️ Listening...")
            speech_out = run_termux_cmd(["termux-speech-to-text"])
            recognized_text = speech_out.strip()
            if not recognized_text:
                print("⚠️ No speech detected.")
                continue

            print(f"🗣️ You Said: '{recognized_text}'")

            # Send to Rasa EC2
            payload = {"sender": "android_phone_user", "message": recognized_text}
            resp = requests.post(f"{EC2_RASA_URL}/webhooks/rest/webhook", json=payload, timeout=20)
            if resp.status_code == 200:
                replies = resp.json()
                for r in replies:
                    txt = r.get("text", "")
                    if txt:
                        print(f"🤖 Alya: {txt}\n")
                        run_termux_cmd(["termux-tts-speak", txt])
        except KeyboardInterrupt:
            print("\nExiting voice agent...")
            break
        except Exception as e:
            print(f"Error: {e}")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "voice":
        voice_loop()
    else:
        print("[*] Starting Alya Android Node Server on port 8088...")
        print("[*] Tip: Run 'python alya_android_node.py voice' to launch hands-free voice mode!")
        app.run(host="0.0.0.0", port=8088)
