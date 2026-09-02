# 🚀 Alya Bot ko Render par Deploy karne ka Step-by-Step Guide

Yeh guide aapko Alya AI Telegram Bot ko **Render (render.com)** par Docker ke through easily host karne me madad karegi.

---

## 🏗️ Architecture & Files Created
Render par Rasa Core aur Rasa Action Server dono ko ek sath ek hi container me chalane ke liye zaroori files repo me ready kar di gayi hain:
1. **`Dockerfile`**: Python 3.10-slim par based container with all dependencies (`ffmpeg`, `tesseract-ocr`, etc.).
2. **`start.sh`**: Automatic startup script jo pehle Action Server (port 5055) start karega, phir main Rasa Bot (Render ke dynamic `$PORT` par).
3. **`render.yaml`**: 1-Click Render Blueprint configuration.
4. **`requirements.txt`**: Sabhi pinned Python packages.
5. **`.dockerignore`**: Large files (Android app, caches) ko filter karke fast build ensure karta hai.

---

## 📋 Steps to Deploy on Render

### Step 1: Changes ko GitHub par Push karein
Apne server terminal se changes ko commit aur push karein:
```bash
cd /home/ubuntu/alya
git add .gitignore .dockerignore Dockerfile start.sh render.yaml requirements.txt models/alya-model.tar.gz RENDER_DEPLOYMENT.md
git commit -m "feat(deploy): add Render deployment configuration with Docker & Blueprint"
git push origin main
```

---

### Step 2: Render par Service Create karein (2 Options)

#### Option A: Blueprint se (Sabse Aasan - Recommended)
1. [Render Dashboard](https://dashboard.render.com/) par login karein.
2. Top right par **New +** par click karke **Blueprint** chunein.
3. Apna GitHub repository connect karein: `faijaleaqbal/Rasa`.
4. Render automatically `render.yaml` ko padh lega aur service configure kar dega.
5. Jo Environment Variables blank dikhenge (e.g. `TELEGRAM_BOT_TOKEN`, `OPENROUTER_API_KEY`, etc.), unki value paste karein.
6. **Apply** par click karein!

---

#### Option B: Manual Web Service
1. Render Dashboard par **New +** -> **Web Service** par click karein.
2. Repo select karein: `faijaleaqbal/Rasa` (Branch: `main`).
3. Settings:
   - **Name**: `alya-bot` (ya koi bhi pasand ka naam)
   - **Region**: Singapore (ya nearest region)
   - **Runtime**: `Docker`
   - **Plan**: `Free` (ya `Starter` $7/mo agar 24/7 bina sleep ke chahiye)
   - **Health Check Path**: `/`
4. **Environment Variables** section me jaakar neeche diye gaye variables add karein.

---

### Step 3: Environment Variables Configure karein

Render Dashboard me **Environment** tab me yeh variables set karein:

| Variable Name | Description / Example Value |
| :--- | :--- |
| `PORT` | `5005` |
| `TELEGRAM_BOT_TOKEN` | Aapka Telegram Bot Token (`BotFather` se) |
| `TELEGRAM_BOT_USERNAME` | `Alya_Rasa_Bot` |
| `TELEGRAM_WEBHOOK_URL` | `https://<your-render-subdomain>.onrender.com/webhooks/telegram/webhook` |
| `ALLOWED_TELEGRAM_USER_ID` | Aapka numeric Telegram User ID |
| `FREE_ONLY` | `true` |
| `OPENROUTER_API_KEY` | Aapka OpenRouter API key |
| `GROQ_API_KEY` | Groq key (Whisper audio transcription ke liye) |
| `TAVILY_API_KEY` | Web search ke liye |
| `WEATHER_API_KEY` / `OPENWEATHERMAP_API_KEY` | Weather updates ke liye |

> ⚠️ **Important (Webhook URL)**: 
> Jab Render service create hoti hai, Render aapko ek domain deta hai jaise `https://alya-bot.onrender.com`.
> Aapko `TELEGRAM_WEBHOOK_URL` variable me dalna hoga:
> `https://alya-bot.onrender.com/webhooks/telegram/webhook`
> (Apne actual Render URL ke hisaab se replace karein).

---

### Step 4: Render Free Tier Anti-Sleep (24/7 Active Rakhna)
Render ka Free plan 15 minutes tak koi request na aane par service ko sleep mode me daal deta hai (cold start me ~50s lagte hain).

Isko 24/7 active rakhne ka **100% Free tareeqa**:
1. [cron-job.org](https://cron-job.org) ya [UptimeRobot](https://uptimerobot.com) par free account banayein.
2. Ek monitor / cron job banayein:
   - **URL**: `https://alya-bot.onrender.com/`
   - **Interval**: Every `10 minutes`
3. Yeh service aapke Render bot ko har 10 minute me ping karegi, jisse Render free container kabhi sleep nahi hoga!

---

### Step 5: Verify & Test
Jab deployment complete ho jaye:
1. Browser me open karein: `https://alya-bot.onrender.com/`
   - Response aana chahiye: `Hello from Rasa: 3.6.21`
2. Telegram par `@Alya_Rasa_Bot` ko message bhejein: `/help` ya `/start`
3. Bot instantly reply karega!
