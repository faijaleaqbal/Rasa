---
name: mobile-app-dev
description: Android Kotlin and hybrid mobile app development, background assistant services, Audio STT/TTS pipelines, boot receivers, and permissions.
---

# Mobile App Dev Skill (Android & Assistant Nodes)

Guidelines for developing, building, and debugging Android applications and voice assistant clients.

## Architecture
* **Directory**: `android_app/`
* **Language**: Kotlin (`app/src/main/java/com/alya/aiagent/`)
* **Key Components**:
  * `MainActivity.kt`: User UI, permissions, speech recognizer, settings.
  * `AlyaAssistantService.kt`: Persistent foreground assistant service.
  * `BootReceiver.kt`: Device boot trigger to automatically initialize service.

## Core Procedures

### 1. Permissions Management
Ensure all required permissions are declared in `AndroidManifest.xml` and requested at runtime:
* `RECORD_AUDIO` (Microphone for voice input)
* `INTERNET` (API communication with EC2 server)
* `RECEIVE_BOOT_COMPLETED` (Autostart on boot)
* `FOREGROUND_SERVICE` / `FOREGROUND_SERVICE_MICROPHONE`

### 2. Building APK with Gradle
```bash
cd android_app
./gradlew assembleDebug
```
Release build:
```bash
./gradlew assembleRelease
```

### 3. Server URL Sanitization & Fallback
Always validate the configured server URL:
* Auto-prefix `http://` or `https://` if omitted.
* Strip trailing slashes.
* Handle network timeouts gracefully with informative error messages.
