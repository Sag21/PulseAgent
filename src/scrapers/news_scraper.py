"""
src/scrapers/news_scraper.py
=============================
Fetches articles from:
  1. Custom RSS feeds (websites you add)
  2. NewsAPI for category-based news
"""

import feedparser
import requests
import logging
from config.settings import CUSTOM_RSS_FEEDS, NEWS_API_KEY, BREAKING_KEYWORDS
from src.database.db import is_already_sent

logger = logging.getLogger(__name__)
NEWSAPI_ENDPOINT = "https://newsapi.org/v2/top-headlines"


# ── RSS Feed Scraper ──────────────────────────────────────────────────────────

def fetch_rss_articles() -> list[dict]:
    """Fetch new articles from custom RSS feeds."""
    articles = []

    for feed_url in CUSTOM_RSS_FEEDS:
        feed_url = feed_url.strip()
        if not feed_url:
            continue

        try:
            feed = feedparser.parse(feed_url)
            source_name = feed.feed.get("title", feed_url)

            for entry in feed.entries[:10]:
                url = entry.get("link", "")
                title = entry.get("title", "")

                if not url or is_already_sent(url):
                    continue

                articles.append({
                    "id": url,
                    "title": title,
                    "url": url,
                    "summary_hint": entry.get("summary", ""),
                    "source": source_name,
                    "source_type": "rss"
                })

        except Exception as e:
            logger.error(f"RSS error for {feed_url}: {e}")

    logger.info(f"📰 RSS: Found {len(articles)} new articles.")
    return articles


# ── NewsAPI Scraper ───────────────────────────────────────────────────────────

def fetch_news_by_category(category: str = "general", country: str = "in") -> list[dict]:
    """Fetch top headlines for a specific category from NewsAPI."""
    if not NEWS_API_KEY:
        logger.warning("No NEWS_API_KEY set. Skipping NewsAPI.")
        return []

    try:
        resp = requests.get(NEWSAPI_ENDPOINT, params={
            "apiKey": NEWS_API_KEY,
            "category": category.lower(),
            "country": country,
            "pageSize": 10
        }, timeout=10)
        resp.raise_for_status()
        articles_raw = resp.json().get("articles", [])

        articles = []
        for art in articles_raw:
            url = art.get("url", "")
            title = art.get("title", "")
            if not url or is_already_sent(url):
                continue
            articles.append({
                "id": url,
                "title": title,
                "url": url,
                "summary_hint": art.get("description", ""),
                "source": art.get("source", {}).get("name", "NewsAPI"),
                "source_type": "news",
                "category_hint": category
            })

        return articles

    except Exception as e:
        logger.error(f"NewsAPI error for category {category}: {e}")
        return []


def fetch_breaking_news_candidates() -> list[dict]:
    """Search NewsAPI for potential breaking news using keywords."""
    if not NEWS_API_KEY:
        return []

    results = []
    try:
        resp = requests.get("https://newsapi.org/v2/everything", params={
            "apiKey": NEWS_API_KEY,
            "q": " OR ".join(BREAKING_KEYWORDS[:6]),  # API limit
            "sortBy": "publishedAt",
            "pageSize": 15,
            "language": "en"
        }, timeout=10)
        resp.raise_for_status()

        for art in resp.json().get("articles", []):
            url = art.get("url", "")
            title = art.get("title", "")
            if not url or is_already_sent(url):
                continue

            # Only flag if title actually contains a breaking keyword
            title_lower = title.lower()
            if any(kw in title_lower for kw in BREAKING_KEYWORDS):
                results.append({
                    "id": url,
                    "title": title,
                    "url": url,
                    "summary_hint": art.get("description", ""),
                    "source": art.get("source", {}).get("name", "NewsAPI"),
                    "source_type": "breaking_news",
                    "is_breaking": True
                })

    except Exception as e:
        logger.error(f"Breaking news fetch error: {e}")

    logger.info(f"🚨 Breaking News candidates: {len(results)}")
    return results


def fetch_all_category_news() -> list[dict]:
    """Fetch news for all major NewsAPI categories."""
    # NewsAPI supported categories
    api_categories = ["general", "technology", "sports", "entertainment",
                      "business", "health", "science"]
    all_articles = []
    for cat in api_categories:
        all_articles.extend(fetch_news_by_category(cat))
    return all_articles
