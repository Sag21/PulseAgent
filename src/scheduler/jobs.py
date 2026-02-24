"""
src/scheduler/jobs.py
======================
All scheduled job functions:
  - run_breaking_news_check()  → every 30 minutes
  - run_evening_digest()       → daily at 7:00 PM
  - run_morning_market()       → daily at 8:00 AM
  - run_youtube_monitor()      → every 60 minutes
"""

import logging
from src.scrapers.youtube_scraper import fetch_new_youtube_videos
from src.scrapers.news_scraper import (
    fetch_breaking_news_candidates, fetch_all_category_news,
    fetch_rss_articles, fetch_news_by_category
)
from src.processors.ai_processor import batch_summarize
from src.processors.message_formatter import (
    format_breaking_news, format_youtube_update,
    format_evening_digest, format_morning_market_digest
)
from src.database.db import (
    is_already_sent, mark_as_sent, add_to_digest_queue,
    get_unsent_digest_items, mark_digest_items_sent, clear_old_digest
)

logger = logging.getLogger(__name__)


# ── Breaking News Check (every 30 min) ───────────────────────────────────────

async def run_breaking_news_check() -> int:
    """
    Fetches and sends breaking news immediately.
    Returns count of breaking news items sent.
    """
    from src.bot.telegram_bot import send_message_to_all_users

    logger.info("🚨 Running breaking news check...")
    candidates = fetch_breaking_news_candidates()

    if not candidates:
        return 0

    processed = batch_summarize(candidates, source_type="news")
    sent_count = 0

    for item in processed:
        if item.get("is_breaking") and not is_already_sent(item["id"]):
            msg = format_breaking_news(item)
            await send_message_to_all_users(msg)
            mark_as_sent(item["id"], item["source_type"], item["title"], is_breaking=True)
            sent_count += 1

    logger.info(f"🚨 Sent {sent_count} breaking news alerts.")
    return sent_count


# ── YouTube Monitor (every 60 min) ───────────────────────────────────────────

async def run_youtube_monitor():
    """Check YouTube channels for new videos and add to digest queue."""
    logger.info("📺 Running YouTube monitor...")
    new_videos = fetch_new_youtube_videos()

    if not new_videos:
        logger.info("📺 No new YouTube videos.")
        return

    processed = batch_summarize(new_videos, source_type="youtube")

    for item in processed:
        # If breaking/urgent, send immediately
        if item.get("is_breaking"):
            from src.bot.telegram_bot import send_message_to_all_users
            msg = format_youtube_update(item)
            await send_message_to_all_users(msg)
            mark_as_sent(item["id"], "youtube", item["title"], is_breaking=True)
        else:
            # Add to evening digest queue
            add_to_digest_queue(
                item_id=item["id"],
                title=item["title"],
                summary=item["ai_summary"],
                category=item["category"],
                source_url=item["url"],
                source_type="youtube"
            )
            mark_as_sent(item["id"], "youtube", item["title"])


# ── News Collector (every 60 min, feeds digest) ───────────────────────────────

async def run_news_collector():
    """Collect all news and RSS articles into the digest queue."""
    logger.info("📰 Collecting news articles...")

    # Combine RSS + NewsAPI
    rss_items = fetch_rss_articles()
    news_items = fetch_all_category_news()
    all_items = rss_items + news_items

    if not all_items:
        return

    processed = batch_summarize(all_items, source_type="news")

    for item in processed:
        if item.get("is_breaking"):
            from src.bot.telegram_bot import send_message_to_all_users
            from src.processors.message_formatter import format_breaking_news
            msg = format_breaking_news(item)
            await send_message_to_all_users(msg)
            mark_as_sent(item["id"], item["source_type"], item["title"], is_breaking=True)
        else:
            add_to_digest_queue(
                item_id=item["id"],
                title=item["title"],
                summary=item.get("ai_summary", ""),
                category=item.get("category", "World News"),
                source_url=item.get("url", ""),
                source_type=item["source_type"]
            )
            mark_as_sent(item["id"], item["source_type"], item["title"])

    logger.info(f"📰 Collected {len(processed)} news items into queue.")


# ── Evening Digest (7:00 PM daily) ───────────────────────────────────────────

async def run_evening_digest():
    """Send the full evening digest to all users."""
    from src.bot.telegram_bot import send_message_to_all_users

    logger.info("🌙 Sending evening digest...")

    items = get_unsent_digest_items()

    # Filter out market items (they go in morning digest)
    evening_items = [i for i in items if i.get("category", "") != "Stock & Market"]

    messages = format_evening_digest(evening_items)
    for msg in messages:
        await send_message_to_all_users(msg)

    # Mark all as sent
    all_ids = [i["item_id"] for i in items]
    if all_ids:
        mark_digest_items_sent(all_ids)

    clear_old_digest()
    logger.info(f"🌙 Evening digest sent with {len(evening_items)} items.")


# ── Morning Market Briefing (8:00 AM daily) ───────────────────────────────────

async def run_morning_market():
    """Send stock & market briefing each morning."""
    from src.bot.telegram_bot import send_message_to_all_users

    logger.info("☀️ Sending morning market briefing...")

    # Fetch fresh market news
    market_articles = fetch_news_by_category("business")
    if market_articles:
        processed = batch_summarize(market_articles, source_type="news")
        for item in processed:
            mark_as_sent(item["id"], "news", item["title"])
    else:
        processed = []

    msg = format_morning_market_digest(processed)
    await send_message_to_all_users(msg)
    logger.info("☀️ Morning market briefing sent.")
