---
name: websocket-realtime
description: Real-time bi-directional streaming, Socket.IO channels, Server-Sent Events (SSE), event listeners, and reconnection handling.
---

# WebSocket & Real-Time Streaming Skill

Procedures for implementing fast, resilient, bi-directional communication channels between chat widgets, voice nodes, and AI backends.

## Protocol Comparison
* **WebSockets / Socket.IO**: Full-duplex communication ideal for real-time voice, live chat, and instant interactive notifications.
* **Server-Sent Events (SSE)**: Lightweight one-way server streaming ideal for LLM token-by-token text streaming.
* **REST Polling**: Fallback mechanism when persistent socket connections are blocked by strict corporate firewalls.

## Socket.IO Integration with Rasa
* **Endpoint**: `http://localhost:5005/socket.io/`
* **Incoming Event**: `user_uttered` -> `{"message": "user query", "session_id": "uuid"}`
* **Outgoing Event**: `bot_uttered` -> `{"text": "reply", "buttons": []}`

## Resilience Best Practices
1. **Exponential Backoff**: Reconnect attempts should progressively back off (e.g. 1s, 2s, 4s, 8s, up to 30s max).
2. **Heartbeat / Ping-Pong**: Monitor keep-alive packets to detect zombie connections early.
3. **Message Queuing**: Queue user messages locally during network disconnects and flush them immediately upon reconnection.
