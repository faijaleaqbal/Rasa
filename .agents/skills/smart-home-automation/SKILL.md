---
name: smart-home-automation
description: Home Assistant integration (lights, AC, smart plugs via REST/MQTT) and local device system control (apps, volume, window management).
---

# Smart Home & Device Automation Skill

Controls IoT smart home appliances and manages local operating system commands and background automation.

## Home Assistant Integration (REST / WebSocket)
* **Base URL**: `http://homeassistant.local:8123/api`
* **Authentication**: Long-Lived Access Token via `Authorization: Bearer <token>`
* **Service Triggers**:
  * Turn on lights: `POST /api/services/light/turn_on` with `{"entity_id": "light.living_room", "brightness": 255}`
  * Set Thermostat/AC: `POST /api/services/climate/set_temperature` with `{"entity_id": "climate.ac", "temperature": 24}`
  * Trigger Scenes: `POST /api/services/scene/turn_on` with `{"entity_id": "scene.movie_night"}`

## Local OS System Control
* Control system volume, media playback, application launches, and screen lock.
* Automated folder organization (e.g. archiving old downloads into date-based subfolders).
