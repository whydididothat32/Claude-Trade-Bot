# 📱 Trading Alert Bot — Setup Guide

## What this bot does
- Monitors Reuters, Bloomberg, Reddit (r/worldnews, r/investing) every 5 minutes
- Alerts you when Iran/geopolitical keywords appear in headlines
- Alerts you when NCLH, UAL, CCL, or AAL move ±3% intraday
- Alerts you when Brent crude crosses $110 (danger) or $95 (peace trade)
- All alerts sent instantly to your Telegram

---

## Step 1: Create your Telegram Bot (5 min)

1. Open Telegram, search for **@BotFather**
2. Send: `/newbot`
3. Name it anything, e.g. `TradeAlertBot`
4. BotFather gives you a **token** like: `7123456789:AAFxxx...`  → save this
5. Search for your new bot in Telegram and press **Start**
6. Get your **Chat ID**: visit this URL in your browser (replace YOUR_TOKEN):
   `https://api.telegram.org/botYOUR_TOKEN/getUpdates`
7. Send any message to your bot first, then refresh that URL
8. Look for `"chat":{"id":XXXXXXXXX}` → that number is your Chat ID

---

## Step 2: Deploy to Railway (free, runs 24/7)

1. Go to **railway.app** and sign up (free)
2. Click **New Project → Deploy from GitHub repo**
   - Or use **Deploy from local** and upload these 3 files:
     - `bot.py`
     - `requirements.txt`
     - `railway.toml`
3. Once deployed, click your service → **Variables** tab
4. Add two environment variables:
   - `TELEGRAM_TOKEN` = your token from Step 1
   - `TELEGRAM_CHAT_ID` = your chat ID from Step 1
5. Railway will auto-restart the bot and keep it running 24/7

---

## Step 3: Confirm it's working

Within 30 seconds of deploying, you'll get a Telegram message:
> ✅ Trading Alert Bot is LIVE

That's it. You're covered.

---

## Customize (optional)

Open `bot.py` and edit these at the top:

| Variable | Default | What it does |
|---|---|---|
| `CHECK_INTERVAL` | 300 (5 min) | How often it checks |
| `GEO_KEYWORDS` | Iran-focused list | Add any keywords |
| `WATCHLIST` | NCLH/UAL/CCL/AAL | Add/remove tickers |
| `OIL_ALERT_ABOVE` | $110 | Oil danger threshold |
| `OIL_ALERT_BELOW` | $95 | Oil peace threshold |
| `spike_pct` | 3.0% | Stock move alert threshold |

---

## Example alerts you'll receive

**Geopolitical:**
> 🚨 GEOPOLITICAL ALERT
> 📰 Reuters World
> 📌 Iran rejects ceasefire talks, threatens Strait of Hormuz
> 🔑 Keywords: iran, ceasefire, strait of hormuz

**Stock spike:**
> 📈 STOCK SPIKE ALERT
> 🟢 UP NCLH (Norwegian Cruise Line)
> 💰 $18.42 (+4.7%)

**Oil:**
> 🛢️ OIL PRICE ALERT
> 🟢 BELOW threshold $95
> Current: $93.10/barrel (Brent)
> 📊 Peace trade heating up — NCLH/UAL calls favorable
