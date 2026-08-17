#!/usr/bin/env bash
# Quick script to configure credentials and restart services for Alya Bot

ENV_FILE="/home/ubuntu/Rasa/.env"

echo "=== Alya Bot Credential Setup ==="

read -p "Enter Groq API Key (leave empty to keep current): " GROQ_KEY
read -p "Enter Telegram Bot Token (e.g. 123456:ABC-DEF...) (leave empty to keep current): " TG_TOKEN
read -p "Enter Telegram Webhook URL (e.g. https://rasaagent.duckdns.org/webhooks/telegram/webhook): " TG_WEBHOOK
read -p "Enter Tavily API Key (optional for web search): " TAVILY_KEY

if [ -n "$GROQ_KEY" ]; then
    sed -i "s|^GROQ_API_KEY=.*|GROQ_API_KEY=$GROQ_KEY|" "$ENV_FILE"
fi

if [ -n "$TG_TOKEN" ]; then
    sed -i "s|^TELEGRAM_BOT_TOKEN=.*|TELEGRAM_BOT_TOKEN=$TG_TOKEN|" "$ENV_FILE"
fi

if [ -n "$TG_WEBHOOK" ]; then
    sed -i "s|^TELEGRAM_WEBHOOK_URL=.*|TELEGRAM_WEBHOOK_URL=$TG_WEBHOOK|" "$ENV_FILE"
fi

if [ -n "$TAVILY_KEY" ]; then
    sed -i "s|^TAVILY_API_KEY=.*|TAVILY_API_KEY=$TAVILY_KEY|" "$ENV_FILE"
fi

echo "[*] Restarting Alya Bot and Action services..."
sudo systemctl restart rasa-actions.service
sudo systemctl restart rasa-bot.service

echo "[+] Done! Services restarted. Checking status:"
sudo systemctl status rasa-actions.service --no-pager
sudo systemctl status rasa-bot.service --no-pager
