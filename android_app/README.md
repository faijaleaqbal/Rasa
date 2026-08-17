# 📱 Alya Android AI Voice Assistant (Native Mobile App)

A native Android Voice Assistant app that connects your smartphone directly to your **Alya AI Cloud Brain (Rasa 3.6 + Groq LLM + 100+ Skills)**.

---

## 🌟 Key Features (Gemini / Jarvis Style):

1. **🎙️ Voice-First Interface**:
   - Tap-to-Speak or set as Android's default **Voice Assistant** (activates by holding Power Button or swiping from corner).
2. **📞 Direct Phone Calling (`ACTION_CALL`)**:
   - Voice command: *"Call Rahul"* or *"Dial 9876543210"* triggers native phone dialer.
3. **💬 SMS & WhatsApp Automation**:
   - Voice command: *"Send WhatsApp to Amit: Reaching in 10 minutes"*.
4. **⏰ Real System Alarms & Timers**:
   - Voice command: *"Set alarm for 6:30 AM tomorrow"* or *"Set 10 minute timer"*.
5. **🧠 100+ Enterprise Skills Access**:
   - Stocks, Gold bullion rates, IRCTC PNR status, Weather, Flight radar, PDF generation, Document reading, Calculations, Notes & Reminders.
6. **🔊 Natural Hinglish Voice Replies**:
   - Uses Android Neural Hindi/Indian English Text-To-Speech engine.

---

## 🛠️ Quick Build & Install (2 Methods)

### Method A: Build APK in Android Studio / VS Code
1. Open the `/android_app` directory in **Android Studio**.
2. Click **Build ➔ Build Bundle(s) / APK(s) ➔ Build APK(s)**.
3. Transfer `app-debug.apk` to your phone and tap **Install**.

### Method B: Automated GitHub Actions / Cloud Build
Push this repo to GitHub; GitHub Actions will automatically compile and provide a downloadable `.apk` file under Releases.

---

## ⚙️ Mobile Setup in 3 Simple Steps:

1. **Open Alya App on Phone**:
   - Grant permissions for **Microphone, Phone Calls, SMS, and Contacts**.
2. **Server IP Configuration**:
   - The default URL is set to your EC2 Server: `http://3.90.20.247:5005`
   - *(Note: Do NOT use `127.0.0.1` on a physical phone, as `127.0.0.1` means the phone itself).*
   - Tap **"⚡ Test Connect"** to verify that your phone can reach the EC2 Rasa server.
   - Tap **"💾 Save URL"** to store your configuration.
3. **Set as Default Android Digital Assistant**:
   - Go to Phone **Settings ➔ Apps ➔ Default Apps ➔ Digital Assistant App**.
   - Select **Alya AI Assistant**.
   - Now, holding your phone's Power Button or swiping up from bottom corner will immediately launch Alya!

---

## 🔒 Important EC2 & Network Requirements

1. **AWS EC2 Security Group (Port 5005)**:
   - In AWS EC2 Console ➔ Security Groups ➔ Edit Inbound Rules:
     - **Type**: Custom TCP
     - **Port Range**: `5005`
     - **Source**: `0.0.0.0/0` (Anywhere)
2. **Cleartext Traffic (HTTP)**:
   - `android:usesCleartextTraffic="true"` is enabled in `AndroidManifest.xml` to allow standard `http://` communication directly to port 5005.
3. **Optional (HTTPS / Domain / Ngrok)**:
   - If you want HTTPS encryption, you can use the Nginx reverse proxy configured on port 443 or run `./start_ngrok.sh` and enter the `https://xxxx.ngrok-free.app` URL into the app.

