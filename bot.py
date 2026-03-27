import os
import time
import requests
import feedparser
import yfinance as yf
from datetime import datetime, timezone
import json

# ── Config ────────────────────────────────────────────────────────────────────
TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
TELEGRAM_CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]
CHECK_INTERVAL = 300  # seconds (5 min)

# Keywords that trigger a geopolitical alert
GEO_KEYWORDS = [
    "iran", "ceasefire", "cease-fire", "nuclear deal", "strait of hormuz",
    "oil embargo", "middle east", "escalation", "airstrike", "sanctions",
    "trump iran", "iran deal", "persian gulf", "tehran"
]

# Stocks to monitor
WATCHLIST = {
    "NCLH": {"name": "Norwegian Cruise Line", "spike_pct": 3.0},
    "UAL":  {"name": "United Airlines",        "spike_pct": 3.0},
    "CCL":  {"name": "Carnival Cruise",        "spike_pct": 3.0},
    "AAL":  {"name": "American Airlines",      "spike_pct": 3.0},
}

# Oil thresholds
OIL_TICKER = "BZ=F"
OIL_ALERT_ABOVE = 110.0
OIL_ALERT_BELOW = 95.0

# RSS feeds
RSS_FEEDS = [
    {"name": "Reuters World", "url": "https://feeds.reuters.com/Reuters/worldNews"},
    {"name": "Reuters Business","url": "https://feeds.reuters.com/reuters/businessNews"},
    {"name": "Bloomberg Markets","url": "https://feeds.bloomberg.com/markets/news.rss"},
    {"name": "Reddit WorldNews", "url": "https://www.reddit.com/r/worldnews/.rss"},
    {"name": "Reddit Investing",  "url": "https://www.reddit.com/r/investing/.rss"},
]

# ── State (in-memory dedup) ────────────────────────────────────────────────────
seen_articles = set()
last_prices = {}
last_oil_alert = None  # "above" | "below" | None

# ── Telegram ──────────────────────────────────────────────────────────────────
def send_telegram(message: str):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "HTML"}
    try:
        r = requests.post(url, json=payload, timeout=10)
        r.raise_for_status()
    except Exception as e:
        print(f"[Telegram error] {e}")

# ── News / Reddit ─────────────────────────────────────────────────────────────
def check_news():
    alerts = []
    for feed in RSS_FEEDS:
        try:
            parsed = feedparser.parse(feed["url"])
            for entry in parsed.entries[:15]:
                title = entry.get("title", "")
                link  = entry.get("link", "")
                uid   = link or title
                if uid in seen_articles:
                    continue
                seen_articles.add(uid)
                title_lower = title.lower()
                matched = [kw for kw in GEO_KEYWORDS if kw in title_lower]
                if matched:
                    alerts.append({
                        "source": feed["name"],
                        "title": title,
                        "link": link,
                        "keywords": matched,
                    })
        except Exception as e:
            print(f"[Feed error] {feed['name']}: {e}")
    return alerts

# ── Stock prices ──────────────────────────────────────────────────────────────
def check_stocks():
    alerts = []
    tickers = list(WATCHLIST.keys())
    try:
        data = yf.download(tickers, period="2d", interval="5m",
                           group_by="ticker", progress=False, auto_adjust=True)
        for ticker, info in WATCHLIST.items():
            try:
                closes = data[ticker]["Close"].dropna()
                if len(closes) < 2:
                    continue
                prev_close = closes.iloc[-2]
                curr_price = closes.iloc[-1]
                pct_change = ((curr_price - prev_close) / prev_close) * 100
                last_key = f"{ticker}_last_pct"
                last_pct = last_prices.get(last_key, 0)
                threshold = info["spike_pct"]
                # Alert on new crossing (avoid repeat spam)
                if abs(pct_change) >= threshold and abs(last_pct) < threshold:
                    direction = "🟢 UP" if pct_change > 0 else "🔴 DOWN"
                    alerts.append({
                        "ticker": ticker,
                        "name": info["name"],
                        "price": round(float(curr_price), 2),
                        "pct": round(float(pct_change), 2),
                        "direction": direction,
                    })
                last_prices[last_key] = pct_change
            except Exception as e:
                print(f"[Stock error] {ticker}: {e}")
    except Exception as e:
        print(f"[Download error] {e}")
    return alerts

# ── Oil price ─────────────────────────────────────────────────────────────────
def check_oil():
    global last_oil_alert
    try:
        oil = yf.Ticker(OIL_TICKER)
        hist = oil.history(period="1d", interval="5m")
        if hist.empty:
            return None
        price = round(float(hist["Close"].dropna().iloc[-1]), 2)
        if price >= OIL_ALERT_ABOVE and last_oil_alert != "above":
            last_oil_alert = "above"
            return {"price": price, "signal": "🔴 ABOVE", "threshold": OIL_ALERT_ABOVE,
                    "note": "War premium elevated — puts risk on peace trade"}
        elif price <= OIL_ALERT_BELOW and last_oil_alert != "below":
            last_oil_alert = "below"
            return {"price": price, "signal": "🟢 BELOW", "threshold": OIL_ALERT_BELOW,
                    "note": "Peace trade heating up — NCLH/UAL calls favorable"}
    except Exception as e:
        print(f"[Oil error] {e}")
    return None

# ── Format messages ───────────────────────────────────────────────────────────
def format_news_alert(a):
    kws = ", ".join(a["keywords"][:3])
    return (
        f"🚨 <b>GEOPOLITICAL ALERT</b>\n"
        f"📰 <b>{a['source']}</b>\n"
        f"📌 {a['title']}\n"
        f"🔑 Keywords: <i>{kws}</i>\n"
        f"🔗 {a['link']}\n\n"
        f"👀 Watch: NCLH, UAL, CCL, AAL\n"
        f"⏰ {datetime.now(timezone.utc).strftime('%H:%M UTC')}"
    )

def format_stock_alert(a):
    return (
        f"📈 <b>STOCK SPIKE ALERT</b>\n"
        f"{a['direction']} <b>{a['ticker']}</b> ({a['name']})\n"
        f"💰 ${a['price']} ({a['pct']:+.2f}%)\n"
        f"⏰ {datetime.now(timezone.utc).strftime('%H:%M UTC')}"
    )

def format_oil_alert(o):
    return (
        f"🛢️ <b>OIL PRICE ALERT</b>\n"
        f"{o['signal']} threshold ${o['threshold']}\n"
        f"Current: <b>${o['price']}/barrel (Brent)</b>\n"
        f"📊 {o['note']}\n"
        f"⏰ {datetime.now(timezone.utc).strftime('%H:%M UTC')}"
    )

# ── Main loop ─────────────────────────────────────────────────────────────────
def main():
    send_telegram(
        "✅ <b>Trading Alert Bot is LIVE</b>\n"
        "Monitoring: Reuters, Bloomberg, Reddit, NCLH/UAL/CCL/AAL, Brent Crude\n"
        f"Check interval: every {CHECK_INTERVAL//60} minutes\n"
        "You'll be alerted on geopolitical headlines, stock spikes, and oil thresholds."
    )
    print("[Bot started]")

    while True:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Checking...")

        # News
        for alert in check_news():
            send_telegram(format_news_alert(alert))
            time.sleep(1)

        # Stocks
        for alert in check_stocks():
            send_telegram(format_stock_alert(alert))
            time.sleep(1)

        # Oil
        oil_alert = check_oil()
        if oil_alert:
            send_telegram(format_oil_alert(oil_alert))

        time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    main()
