#!/usr/bin/env bash
set -e

# Usage: ./start_ngrok.sh [YOUR_NGROK_AUTHTOKEN] [OPTIONAL_STATIC_DOMAIN]
NGROK_TOKEN="$1"
STATIC_DOMAIN="$2"

if [ -n "$NGROK_TOKEN" ]; then
    echo "[*] Configuring ngrok authtoken..."
    ngrok config add-authtoken "$NGROK_TOKEN"
fi

if [ -n "$STATIC_DOMAIN" ]; then
    echo "[*] Starting ngrok with static domain: $STATIC_DOMAIN"
    ngrok http 5005 --url "$STATIC_DOMAIN"
else
    echo "[*] Starting ngrok on port 5005..."
    ngrok http 5005
fi
