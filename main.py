"""
PulseAgent - Your Personal AI News & Update Bot
================================================
Run this file to start the bot and all background schedulers.
"""

import asyncio
import logging
from src.bot.telegram_bot import start_bot
from src.scheduler.scheduler import start_scheduler
from config.settings import LOG_LEVEL

logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.FileHandler("logs/pulseagent.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("PulseAgent")


async def main():
    logger.info("🚀 PulseAgent is starting...")

    # Start scheduler in background
    scheduler = await start_scheduler()

    # Start Telegram bot (blocking)
    logger.info("🤖 Telegram Bot is live!")
    await start_bot()


if __name__ == "__main__":
    asyncio.run(main())
