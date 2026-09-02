#!/bin/bash
set -e

echo "============================================="
echo "   🤖 Starting Alya AI Assistant on Render   "
echo "============================================="

# Ensure directories exist
mkdir -p storage/files storage/auth storage/notes /tmp/alya_image_tools_storage

BOT_PORT="${PORT:-5005}"
ACTION_PORT=5055

cleanup() {
    echo "⚠️ Shutting down child processes..."
    kill -TERM "$ACTION_PID" 2>/dev/null || true
    kill -TERM "$IMG_PID" 2>/dev/null || true
    exit 0
}
trap cleanup SIGTERM SIGINT

# 1. Start Image Tools Server
echo "🖼️ Starting Alya Image Tools Server..."
python3 -m addons.image_tools.server &
IMG_PID=$!

# 2. Start Action Server
echo "⚡ Starting Rasa Action Server on port ${ACTION_PORT}..."
rasa run actions --port "${ACTION_PORT}" &
ACTION_PID=$!

# Wait for Action Server to be healthy
echo "⏳ Waiting for Action Server to initialize..."
for i in $(seq 1 45); do
    if curl -s "http://127.0.0.1:${ACTION_PORT}/actions" > /dev/null 2>&1; then
        echo "✅ Action Server is online!"
        break
    fi
    sleep 1
done

# 3. Start Main Rasa Core Bot Server on $PORT
echo "🚀 Starting Rasa Bot Server on port ${BOT_PORT}..."
echo "📡 Webhook URL configured: ${TELEGRAM_WEBHOOK_URL:-'(Not set)'}"

exec rasa run \
    --enable-api \
    --cors "*" \
    --port "${BOT_PORT}" \
    --endpoints endpoints.yml \
    --credentials credentials.yml
