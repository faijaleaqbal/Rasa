---
title: Alya AI Bot
emoji: 🤖
colorFrom: purple
colorTo: indigo
sdk: docker
app_port: 7860
pinned: false
---

# 🤖 Alya — Autonomous Hinglish AI Telegram Assistant

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Telegram Bot](https://img.shields.io/badge/Telegram-@Alya__Rasa__Bot-blue.svg)](https://t.me/Alya_Rasa_Bot)
[![Rasa 3.6](https://img.shields.io/badge/Rasa-3.6.21-purple.svg)](https://rasa.com)
[![Groq LLM](https://img.shields.io/badge/LLM-Groq%20Qwen%20%2F%20Llama-orange.svg)](https://groq.com)

**Alya** is an enterprise-grade, conversational AI personal assistant on Telegram built with **Rasa 3.6**, **Groq Fast LLM Inference**, **Model Context Protocol (MCP)**, **Google OAuth**, and **Microsoft Graph API**.

---

## 🌟 Key Capabilities & Skills (37+ Skills)

### 🌤️ 1. Real-Time Free APIs
- **Weather (`/weather`)**: Real-time temperature, humidity, and conditions (default: Malda, West Bengal, India) via OpenWeatherMap & WeatherAPI.
- **News (`/news`)**: English top headlines & categorized updates via NewsAPI, GNews & DuckDuckGo.
- **Currency (`/currency`)**: Real-time FX exchange conversion via ExchangeRate-API V6.
- **Crypto (`/crypto`)**: Live token prices with symbol resolution (`ltc`, `btc`, `eth`, etc.) via CoinGecko & Etherscan V2 gas tracker.
- **Wiki (`/wiki`)**: Instant encyclopedia summary & OpenLibrary book lookups.
- **Movies (`/movie`)**: IMDb ratings, plot summaries & directors via OMDb & TMDB.
- **Holidays (`/holiday`)**: Upcoming gazetted holidays via Calendarific & Nager.Date.
- **Stock Photos (`/image`)**: High-res photography via Unsplash & Pexels.
- **Breach Check (`/breach`)**: Email exposure check via XposedOrNot & password leak checks via HaveIBeenPwned SHA-1 k-anonymity.
- **Math & Science (`/math`, `/science`)**: WolframAlpha calculus/algebra solver & NASA Astronomy Picture of the Day.

### 📋 2. Utilities & Personal Management
- **Reminders & Medicine (`/remind`, `/medremind`)**: Thread-safe background scheduler with automated Telegram alerts.
- **Notes & To-Dos (`/note`, `/notes`, `/todo`, `/todos`)**: SQLite persistent storage.
- **Expense Tracker & Bills (`/expense`, `/expenses`, `/bill`)**: Monthly financial analytics and bill alerts.
- **Commute & Cabs (`/traffic`, `/ride`)**: OpenRouteService Matrix API routing, travel ETA, and Uber/Ola fare estimators.
- **Server Health & Speedtest (`/serverstatus`, `/speedtest`)**: EC2 diagnostics & network speed tests.

### 📁 3. Productivity & Document Engines
- **PDF Engine (`/pdf`)**: ReportLab professional document styling sent directly to chat.
- **Excel Engine (`/excel`)**: openpyxl automated data tables with totals and formatting.
- **Word Engine (`/doc`)**: python-docx styled executive memos and reports.
- **Google Workspace (`/gmail`, `/drive`, `/calendar`)**: Live OAuth token refresh & query engine.
- **Microsoft Outlook (`/outlook`)**: MS Graph OAuth token refresh & email reader.
- **GitHub & OpenCode (`/github`, `/code`)**: Official GitHub MCP Server (port 4097) and headless OpenCode MCP Server (port 4096).

---

## 🛠️ Architecture & Setup

```
Rasa Agent (Port 5005) <---> Action Server (Port 5055)
         ^                               ^
         |                               |
    Nginx Reverse Proxy           GitHub MCP Server (Port 4097)
(rasaagent.duckdns.org)           OpenCode MCP Server (Port 4096)
```

---

## 📄 License
This project is licensed under the [MIT License](LICENSE).
Copyright (c) 2026 Md Faijal Eaqbal.
