---
name: omnichannel-communication
description: Multi-channel bot connectivity across Telegram, WhatsApp, SMS/Voice call APIs (Twilio), and bi-directional audio STT/TTS.
---

# Omnichannel Communication Skill

Integrates voice and chat channels into a unified assistant experience across Telegram, WhatsApp, SMS, and Android.

## Channel Gateways

### 1. Telegram Bot Gateway (`addons/telegram_channel.py`)
* Full support for rich menus, inline buttons, custom keyboards, and voice message processing.
* Native command registration for quick actions.

### 2. WhatsApp Business API / Webhooks
* Inbound message webhook processing (`/webhooks/whatsapp/webhook`).
* Interactive reply buttons, media attachments, and template notifications.

### 3. Voice & Telephony Automation (Twilio / WebRTC)
* Automated outbound voice reminders for critical alarms or urgent calendar events.
* Bidirectional speech streaming: Audio input -> Whisper STT -> LLM/Rasa -> Piper/Edge TTS -> Audio output.
