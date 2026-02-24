"""
src/scheduler/scheduler.py
Attaches APScheduler to the bot's event loop via post_init hook.
This avoids the "event loop already running" crash on Windows.
"""

import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler # type: ignore
from apscheduler.triggers.cron import CronTrigger # type: ignore
from apscheduler.triggers.interval import IntervalTrigger # type: ignore
from telegram.ext import Application # type: ignore

from config.settings import (
    EVENING_DIGEST_HOUR, EVENING_DIGEST_MINUTE,
    MORNING_MARKET_HOUR, MORNING_MARKET_MINUTE,
    BREAKING_NEWS_INTERVAL_MIN
)

logger = logging.getLogger(__name__)


def attach_scheduler(app: Application):
    from src.scheduler.jobs import (
        run_breaking_news_check,
        run_evening_digest,
        run_morning_market,
        run_youtube_monitor,
        run_news_collector
    )

    scheduler = AsyncIOScheduler(timezone="Asia/Kolkata")

    scheduler.add_job(
        run_breaking_news_check,
        trigger=IntervalTrigger(minutes=BREAKING_NEWS_INTERVAL_MIN),
        id="breaking_news", name="Breaking News Check", replace_existing=True
    )
    scheduler.add_job(
        run_youtube_monitor,
        trigger=IntervalTrigger(minutes=60),
        id="youtube_monitor", name="YouTube Monitor", replace_existing=True
    )
    scheduler.add_job(
        run_news_collector,
        trigger=IntervalTrigger(minutes=60, start_date="2024-01-01 00:30:00"),
        id="news_collector", name="News Collector", replace_existing=True
    )
    scheduler.add_job(
        run_evening_digest,
        trigger=CronTrigger(hour=EVENING_DIGEST_HOUR, minute=EVENING_DIGEST_MINUTE),
        id="evening_digest", name="Evening Digest", replace_existing=True
    )
    from config.settings import NEWS_FETCH_INTERVAL_MIN
    scheduler.add_job(
        run_news_collector,
        trigger=IntervalTrigger(minutes=NEWS_FETCH_INTERVAL_MIN),
        id="news_collector", name="News Collector", replace_existing=True
    )

    async def on_startup(application: Application):
        scheduler.start()
        logger.info("Scheduler started with jobs:")
        for job in scheduler.get_jobs():
            logger.info(f"  - {job.name} | next run: {job.next_run_time}")
        
        # Register bot commands so they show in Telegram menu
        await application.bot.set_my_commands([
            ("start", "Welcome message"),
            ("menu", "Open main menu"),
            ("status", "Check bot status"),
            ("fetch_now", "Fetch latest news right now"),
            ("day_summary", "Complete summary of all news collected today"),
        ])

    async def on_shutdown(application: Application):
        if scheduler.running:  # Only shutdown if it actually started
            scheduler.shutdown(wait=False)
            logger.info("Scheduler stopped.")

    app.post_init = on_startup
    app.post_shutdown = on_shutdown