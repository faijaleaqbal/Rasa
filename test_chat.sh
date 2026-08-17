#!/usr/bin/env bash
# Interactive CLI Tester for Alya Hinglish AI Assistant

SERVER_URL="http://localhost:5005/webhooks/rest/webhook"
SENDER_ID="cli_tester_$(date +%s)"

echo "=========================================================="
echo "      Alya AI Chatbot CLI Tester (@Alya_Rasa_Bot)         "
echo "    Type your message and press ENTER. Type 'exit' to quit"
echo "=========================================================="

while true; do
    echo -n -e "\n\033[1;34mYou:\033[0m "
    read -r USER_INPUT
    if [ "$USER_INPUT" = "exit" ] || [ "$USER_INPUT" = "quit" ]; then
        echo "Goodbye!"
        break
    fi

    if [ -z "$USER_INPUT" ]; then
        continue
    fi

    RESPONSE=$(curl -s -X POST "$SERVER_URL" \
        -H "Content-Type: application/json" \
        -d "{\"sender\": \"$SENDER_ID\", \"message\": \"$USER_INPUT\"}")

    echo -e "\033[1;32mAlya:\033[0m"
    echo "$RESPONSE" | python3 -c '
import sys, json
try:
    data = json.load(sys.stdin)
    if isinstance(data, list) and len(data) > 0:
        for item in data:
            if "text" in item:
                print(" ", item["text"])
            if "image" in item:
                print("  [Image]:", item["image"])
    else:
        print("  (No response from bot)")
except Exception as e:
    print("  Error parsing response:", e)
'
done
