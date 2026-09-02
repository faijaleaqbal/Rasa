# 🤗 Alya Bot ko Hugging Face Spaces par Deploy karne ka Guide

Hugging Face Spaces par aapko **2 vCPU + 16 GB RAM** bilkul **FREE (Lifetime)** milti hai, jisse Rasa + TensorFlow aur chhota Local LLM bina kisi memory issue ke chalta hai.

---

## 🤖 Kya Local LLM Hugging Face par chal sakta hai?
**Haan, bilkul!**
- Hugging Face Spaces me **16 GB RAM** hoti hai.
- Isme aap **GGUF format** ke lightweight quantized models jaise:
  - `Llama-3.2-1B-Instruct` (~1.5 GB RAM)
  - `Qwen2.5-3B-Instruct` (~2.5 GB RAM)
  - `Phi-3.5-mini` (~3 GB RAM)
  CPU par aasaani se run kar sakte hain.
- **Speed**: CPU par ~10-15 tokens/second aati hai, jo chatbot ke liye kaafi theek hai.
- **Best Strategy**: OpenRouter / Groq API (300+ tokens/sec) ko primary rakhein, aur agar kabhi internet/API limit khatam ho toh local model fallback ban jaye!

---

## 🚀 Hugging Face par Deploy karne ke Steps:

### Step 1: Hugging Face par Naya Space Banayein
1. [huggingface.co](https://huggingface.co) par login karein (agar account nahi hai toh free sign-up karein).
2. [huggingface.co/new-space](https://huggingface.co/new-space) par jayein.
3. Space details fill karein:
   - **Space name**: `alya-bot` (ya koi bhi naam)
   - **License**: `mit`
   - **Select the Space SDK**: **Docker** (Blank)
   - **Space hardware**: **CPU basic · 2 vCPU · 16 GB RAM · Free**
   - **Privacy**: **Public** (Telegram webhook connect karne ke liye Public zaroori hai)
4. **Create Space** par click karein.

---

### Step 2: Code ko Hugging Face Space par Push karein
Apne server terminal se direct Hugging Face remote add karke push karein:

```bash
cd /home/ubuntu/alya

# 1. Hugging Face Space ka git remote add karein (apne username se replace karein)
git remote add space https://huggingface.co/spaces/<Aapka-HF-Username>/alya-bot

# 2. Changes commit karein
git add Dockerfile start.sh README.md requirements.txt
git commit -m "feat(deploy): optimize Dockerfile & start script for Hugging Face Spaces"

# 3. Space par push karein
git push --force space main
```
*(Push karte waqt Hugging Face username aur Access Token mangega, jo aap [HF Settings -> Access Tokens](https://huggingface.co/settings/tokens) se le sakte hain).*

---

### Step 3: Space Settings me Secrets (API Keys) Dalein
1. Apne Space page par jayein aur **Settings** tab par click karein.
2. Niche scroll karke **Variables and secrets** section me jayein.
3. **New secret** par click karke yeh add karein:

| Secret Name | Value |
| :--- | :--- |
| `TELEGRAM_BOT_TOKEN` | `<your_telegram_bot_token_here>` |
| `TELEGRAM_BOT_USERNAME` | `Alya_Rasa_Bot` |
| `TELEGRAM_WEBHOOK_URL` | `https://<hf-username>-alya-bot.hf.space/webhooks/telegram/webhook` |
| `ALLOWED_TELEGRAM_USER_ID` | `8433855679` |
| `FREE_ONLY` | `true` |
| `OPENROUTER_API_KEY` | `<your_openrouter_api_key_here>` |
| `GROQ_API_KEY` | `<your_groq_api_key_here>` |
| `TAVILY_API_KEY` | `<your_tavily_api_key_here>` |

> 📌 **Webhook URL Note**:
> Hugging Face ka domain format hota hai:
> `https://<hf-username>-<space-name>.hf.space`
> Iske aage `/webhooks/telegram/webhook` laga kar `TELEGRAM_WEBHOOK_URL` me dalna hai.

---

### Step 4: Build & Live!
Hugging Face Docker image build karega (16 GB RAM ke sath yeh 2-3 minute me complete ho jata hai) aur status **Running** ho jayega!
