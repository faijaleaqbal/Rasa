---
name: api-tester
description: Automated API verification, REST endpoint testing, webhook debugging, and payload assertion strategies.
---

# API Tester Skill

Automated testing guide for Rasa REST webhooks, Custom Actions endpoints, and integration APIs.

## Rasa REST Webhook Testing

### Endpoint: `POST /webhooks/rest/webhook`
* **URL**: `http://localhost:5005/webhooks/rest/webhook`
* **Payload Format**:
  ```json
  {
    "sender": "user_session_id",
    "message": "User query or intent trigger"
  }
  ```
* **Expected Response**:
  ```json
  [
    {
      "recipient_id": "user_session_id",
      "text": "Bot response text"
    }
  ]
  ```

### Quick Verification via cURL
```bash
curl -s -X POST http://localhost:5005/webhooks/rest/webhook \
  -H "Content-Type: application/json" \
  -d '{"sender": "tester", "message": "greet"}' | jq .
```

## Custom Action Server Endpoint Testing

### Endpoint: `POST /webhook`
* **URL**: `http://localhost:5055/webhook`
* **Payload Format**:
  ```json
  {
    "next_action": "action_custom_name",
    "sender_id": "tester",
    "tracker": {
      "sender_id": "tester",
      "slots": {},
      "latest_message": {"text": "test"}
    },
    "domain": {}
  }
  ```

## Health Check Endpoints
```bash
# Check Rasa Core status
curl -s http://localhost:5005/status | jq .

# Check Action Server health
curl -s http://localhost:5055/health | jq .
```
