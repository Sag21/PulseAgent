"""
config/settings.py
==================
Central configuration. All secrets come from .env file.
"""

import os
from dotenv import load_dotenv # type: ignore

load_dotenv()

# ── Telegram ──────────────────────────────────────────────────────────────────
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
ALLOWED_USER_IDS = [
    int(uid.strip())
    for uid in os.getenv("ALLOWED_USER_IDS", "").split(",")
    if uid.strip()
]  # Only these Telegram user IDs can interact with the bot

# ── Gemini AI ─────────────────────────────────────────────────────────────────
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = "gemini-2.0-flash"  # Free tier model (use gemini-1.5-pro if you have Pro)

# ── NewsAPI ───────────────────────────────────────────────────────────────────
NEWS_API_KEY = os.getenv("NEWS_API_KEY", "")  # Free at newsapi.org

# ── Scheduling ────────────────────────────────────────────────────────────────
EVENING_DIGEST_HOUR = 19      # 7:00 PM
EVENING_DIGEST_MINUTE = 0
MORNING_MARKET_HOUR = 8       # 8:00 AM
MORNING_MARKET_MINUTE = 0
BREAKING_NEWS_INTERVAL_MIN = 30   # Check for breaking news every 30 minutes
NEWS_FETCH_INTERVAL_MIN = 15

# ── RSS / YouTube Channels (add channel IDs here) ────────────────────────────
# To find a channel ID: go to the channel → view page source → search "channel_id"
YOUTUBE_CHANNEL_IDS = os.getenv("YOUTUBE_CHANNEL_IDS", "").split(",")
# Example: ["UCVHFbw7woebKtfT3s8T4Hcg", "UC-lHJZR3Gqxm24_Vd_AJ5Yw"]

CUSTOM_RSS_FEEDS = os.getenv("CUSTOM_RSS_FEEDS", "").split(",")
# Example: ["https://feeds.bbci.co.uk/news/rss.xml", "https://techcrunch.com/feed/"]

# ── Breaking News Keywords ────────────────────────────────────────────────────
BREAKING_KEYWORDS = [
    "breaking", "urgent", "alert", "disaster", "earthquake", "attack",
    "explosion", "crash", "assassination", "war declared", "emergency",
    "tsunami", "flood", "fire", "hostage", "coup", "missile"
]

# ── News Categories ───────────────────────────────────────────────────────────
NEWS_CATEGORIES = [
    "World News", "Politics", "Technology", "Science",
    "Sports", "Music", "Films & Entertainment",
    "Stock & Market", "Business", "Health", "Environment"
]

# ── Logging ───────────────────────────────────────────────────────────────────
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
