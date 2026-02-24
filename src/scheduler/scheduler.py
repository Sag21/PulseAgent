"""
src/scheduler/scheduler.py
===========================
Sets up APScheduler with all cron jobs.
"""

import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from config.settings import (
    EVENING_DIGEST_HOUR, EVENING_DIGEST_MINUTE,
    MORNING_MARKET_HOUR, MORNING_MARKET_MINUTE,
    BREAKING_NEWS_INTERVAL_MIN
)

logger = logging.getLogger(__name__)


async def start_scheduler() -> AsyncIOScheduler:
    """Initialize and start all scheduled jobs."""
    from src.scheduler.jobs import (
        run_breaking_news_check,
        run_evening_digest,
        run_morning_market,
        run_youtube_monitor,
        run_news_collector
    )

    scheduler = AsyncIOScheduler(timezone="Asia/Kolkata")  # IST timezone

    # 🚨 Breaking news — every 30 minutes
    scheduler.add_job(
        run_breaking_news_check,
        trigger=IntervalTrigger(minutes=BREAKING_NEWS_INTERVAL_MIN),
        id="breaking_news",
        name="Breaking News Check",
        replace_existing=True
    )

    # 📺 YouTube monitor — every 60 minutes
    scheduler.add_job(
        run_youtube_monitor,
        trigger=IntervalTrigger(minutes=60),
        id="youtube_monitor",
        name="YouTube Monitor",
        replace_existing=True
    )

    # 📰 News collector — every 60 minutes (offset by 30 min from YouTube)
    scheduler.add_job(
        run_news_collector,
        trigger=IntervalTrigger(minutes=60, start_date="2024-01-01 00:30:00"),
        id="news_collector",
        name="News Collector",
        replace_existing=True
    )

    # 🌙 Evening digest — daily at 7:00 PM IST
    scheduler.add_job(
        run_evening_digest,
        trigger=CronTrigger(
            hour=EVENING_DIGEST_HOUR,
            minute=EVENING_DIGEST_MINUTE
        ),
        id="evening_digest",
        name="Evening Digest",
        replace_existing=True
    )

    # ☀️ Morning market briefing — daily at 8:00 AM IST
    scheduler.add_job(
        run_morning_market,
        trigger=CronTrigger(
            hour=MORNING_MARKET_HOUR,
            minute=MORNING_MARKET_MINUTE
        ),
        id="morning_market",
        name="Morning Market Briefing",
        replace_existing=True
    )

    scheduler.start()

    logger.info("✅ Scheduler started with jobs:")
    for job in scheduler.get_jobs():
        logger.info(f"   📅 {job.name} — next run: {job.next_run_time}")

    return scheduler
