"""
PulseAgent - Your Personal AI News & Update Bot

"""

import sys
import os
import logging

# Fix Windows console Unicode/emoji issue - MUST be first
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

from src.bot.telegram_bot import build_app
from src.scheduler.scheduler import attach_scheduler
from src.database.db import init_db
from config.settings import LOG_LEVEL

os.makedirs("logs", exist_ok=True)

logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.FileHandler("logs/pulseagent.log", encoding="utf-8"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("PulseAgent")


def main():
    logger.info("PulseAgent is starting...")
    init_db()

    app = build_app()
    attach_scheduler(app)

    logger.info("Telegram Bot is starting. Polling for messages...")
    # run_polling manages its own event loop - do NOT wrap in asyncio.run()
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()