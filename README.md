# 🤖 PulseAgent — Your Personal AI News Bot

> An intelligent automation agent that monitors YouTube channels, news websites, and global updates — then delivers personalized summaries via Telegram.

---

## 📋 Features

| Feature | Details |
|---|---|
| 📺 YouTube Monitoring | Monitors subscribed channels via RSS, summarizes new videos |
| 📰 News Aggregation | Fetches from custom RSS feeds + NewsAPI across all categories |
| 🚨 Breaking News | Auto-detects and sends urgent alerts (checks every 30 minutes) |
| 🌙 Evening Digest | Categorized daily summary sent at 7:00 PM |
| ☀️ Market Briefing | Stock & business news delivered every morning at 8:00 AM |
| 🎛️ Interactive Buttons | On-demand category updates, manual topic search |
| 🧠 AI Summaries | Powered by Google Gemini — 3-5 bullet point summaries |

---

## 🗂️ Project Structure

```
pulseagent/
├── main.py                        # Entry point — run this to start
├── requirements.txt               # All Python dependencies
├── .env.example                   # Config template (copy to .env)
├── .gitignore
│
├── config/
│   └── settings.py                # All configuration & constants
│
├── src/
│   ├── scrapers/
│   │   ├── youtube_scraper.py     # YouTube RSS feed monitor
│   │   └── news_scraper.py        # NewsAPI + custom RSS fetcher
│   │
│   ├── processors/
│   │   ├── ai_processor.py        # Gemini AI summarization & categorization
│   │   └── message_formatter.py   # Telegram message builder
│   │
│   ├── bot/
│   │   └── telegram_bot.py        # Bot commands, buttons, handlers
│   │
│   ├── scheduler/
│   │   ├── scheduler.py           # APScheduler setup & cron jobs
│   │   └── jobs.py                # All scheduled job functions
│   │
│   └── database/
│       └── db.py                  # SQLite — tracks sent items, digest queue
│
├── data/                          # Auto-created — SQLite database lives here
└── logs/                          # Auto-created — log files
```

---

## ⚡ Quick Setup (Step by Step)

### Step 1: Clone & Install

```bash
git clone <your-repo-url>
cd PulseAgent

# Create virtual environment (recommended)
python -m venv venv
source venv/bin/activate      # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

---

### Step 2: Get Your API Keys

#### 🤖 Telegram Bot Token
1. Open Telegram and search for **@BotFather**
2. Send `/newbot`
3. Follow the prompts — choose a name and username for your bot
4. Copy the **token** it gives you (looks like `7123456789:AAF...`)
5. Find your Telegram user ID: search **@userinfobot** on Telegram and send `/start`

#### 🧠 Gemini API Key (for AI summaries)
1. Go to **https://aistudio.google.com/app/apikey**
2. Sign in with your Google account (the one with Gemini Pro subscription)
3. Click **"Create API Key"**
4. Select your Google Cloud project (or create a new one)
5. Copy the API key
> 💡 With Gemini Pro, you get higher rate limits. The free tier also works but is slower.

#### 📰 NewsAPI Key (Free)
1. Go to **https://newsapi.org/register**
2. Create a free account
3. Your API key will be shown on the dashboard
> Free tier: 100 requests/day — plenty for personal use.

---

### Step 3: Configure .env

```bash
cp .env.example .env
```

Edit `.env` with your values:

```env
TELEGRAM_BOT_TOKEN=7123456789:AAFxxx...
ALLOWED_USER_IDS=987654321
GEMINI_API_KEY=AIzaSyXxx...
NEWS_API_KEY=abc123def456...

# YouTube channel IDs (NOT @username)
YOUTUBE_CHANNEL_IDS=UCVHFbw7woebKtfT3s8T4Hcg,UC-lHJZR3Gqxm24_Vd_AJ5Yw

# RSS feeds
CUSTOM_RSS_FEEDS=https://feeds.bbci.co.uk/news/rss.xml
```

#### 🔍 How to find a YouTube Channel ID
- Go to the YouTube channel page
- Right-click → **View Page Source**
- Press `Ctrl+F` and search for `channel_id`
- Copy the 24-character ID (starts with `UC`)
- Or use this tool: https://commentpicker.com/youtube-channel-id.php

---

### Step 4: Run PulseAgent

```bash
python main.py
```

You should see:
```
🚀 PulseAgent is starting...
✅ Database initialized.
✅ Scheduler started with jobs:
   📅 Breaking News Check — next run: ...
   📅 Evening Digest — next run: ...
🤖 Telegram Bot is live!
```

Now open Telegram, find your bot, and send `/start`!

---

## 🎛️ Bot Commands

| Command | Description |
|---|---|
| `/start` | Welcome message |
| `/menu` | Open interactive menu |
| `/status` | Check bot health and queue |

### Interactive Menu Buttons

- **📰 Category Update** → Pick a category (World News, Sports, Tech, etc.) or type your own
- **🚨 Breaking News Now** → Manually trigger a breaking news check
- **📊 Status** → See how many items are queued for digest
- **❓ Help** → Quick command reference

---

## ⏰ Schedule Overview

| Job | Frequency | What it does |
|---|---|---|
| Breaking News Check | Every 30 minutes | Checks NewsAPI for urgent events |
| YouTube Monitor | Every 60 minutes | Checks subscribed channels for new videos |
| News Collector | Every 60 minutes | Fetches all category news into queue |
| Evening Digest | Daily at 7:00 PM | Sends full categorized summary |
| Morning Market | Daily at 8:00 AM | Sends business/stock news briefing |

> Timezone is set to **IST (Asia/Kolkata)**. To change it, edit `src/scheduler/scheduler.py`

---

## 🌐 Free Deployment (Run 24/7)

### Option A: PythonAnywhere (Recommended for beginners)
1. Create a free account at **https://www.pythonanywhere.com**
2. Upload your project files
3. Install requirements in the console
4. Set up a "Always-on task" to run `python main.py`

### Option B: Render.com
1. Push code to GitHub
2. Create a new "Background Worker" on Render
3. Set build command: `pip install -r requirements.txt`
4. Set start command: `python main.py`
5. Add all your `.env` variables in the Render dashboard

### Option C: Run on your PC (Simplest)
Just keep `python main.py` running. Works perfectly for personal use.

---

## 🔧 Customization

### Add more YouTube channels
Edit `.env`:
```env
YOUTUBE_CHANNEL_IDS=UCxxxxxxx,UCyyyyyyy,UCzzzzzzz
```

### Add more RSS feeds
```env
CUSTOM_RSS_FEEDS=https://feed1.com/rss.xml,https://feed2.com/feed
```

### Change breaking news keywords
Edit `config/settings.py`:
```python
BREAKING_KEYWORDS = ["breaking", "earthquake", "your_custom_keyword", ...]
```

### Change digest time
Edit `config/settings.py`:
```python
EVENING_DIGEST_HOUR = 19    # 7 PM
MORNING_MARKET_HOUR = 8     # 8 AM
```

### Add more news categories
Edit `config/settings.py`:
```python
NEWS_CATEGORIES = ["World News", "Technology", "Your Category", ...]
```

---

## 🏗️ Tech Stack (Resume Skills)

| Category | Technology |
|---|---|
| Language | Python 3.11+ |
| AI / LLM | Google Gemini 1.5 Flash |
| Bot Framework | python-telegram-bot v21 |
| Scheduling | APScheduler |
| Database | SQLite (zero-config) |
| RSS Parsing | feedparser |
| News API | NewsAPI.org |
| Web Scraping | BeautifulSoup4 |
| Architecture | Async Python (asyncio) |

---

## 🔒 Security Notes

- Never commit your `.env` file to GitHub — it's in `.gitignore` already
- The `ALLOWED_USER_IDS` whitelist ensures only you (and people you trust) can use the bot
- All API keys are loaded from environment variables, never hardcoded

---

## 🐛 Troubleshooting

| Problem | Fix |
|---|---|
| Bot not responding | Check `TELEGRAM_BOT_TOKEN` in `.env` |
| No summaries | Check `GEMINI_API_KEY` — visit AI Studio to verify |
| No news articles | Verify `NEWS_API_KEY` at newsapi.org dashboard |
| No YouTube updates | Double-check channel IDs (must start with `UC`) |
| Timezone wrong | Change `Asia/Kolkata` in `scheduler.py` to your timezone |
| Rate limit errors | Increase `RATE_LIMIT_DELAY` in `ai_processor.py` |

---

*Built with ❤️ using Python, Gemini AI, and Telegram Bot API*
