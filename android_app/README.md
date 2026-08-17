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
2. **Set Server IP**:
   - Enter your EC2 Public IP or Domain (e.g. `http://YOUR_EC2_IP:5005` or Ngrok URL) and tap **Save Server IP**.
3. **Set as Default Android Digital Assistant**:
   - Go to Phone **Settings ➔ Apps ➔ Default Apps ➔ Digital Assistant App**.
   - Select **Alya AI Assistant**.
   - Now, holding your phone's Power Button or swiping up from bottom corner will immediately launch Alya!
