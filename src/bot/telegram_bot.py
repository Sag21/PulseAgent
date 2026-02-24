"""
src/bot/telegram_bot.py

"""

import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, BotCommand # type: ignore
from telegram.ext import ( # type: ignore
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, ContextTypes, filters
)
from telegram.constants import ParseMode # type: ignore

from config.settings import TELEGRAM_BOT_TOKEN, ALLOWED_USER_IDS, NEWS_CATEGORIES
from src.processors.ai_processor import summarize_custom_query
from src.processors.message_formatter import format_category_update
from src.database.db import init_db

logger = logging.getLogger(__name__)
_app: Application = None


def get_app() -> Application:
    return _app


def is_authorized(update: Update) -> bool:
    if not ALLOWED_USER_IDS:
        return True
    return update.effective_user.id in ALLOWED_USER_IDS


async def unauthorized_reply(update: Update):
    await update.effective_message.reply_text("You are not authorized to use this bot.")


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        return await unauthorized_reply(update)
    await update.message.reply_text(
        "*Welcome to PulseAgent\\!*\n\n"
        "I'm your personal AI news assistant\\.\n\n"
        "\\- Monitor your YouTube channels\n"
        "\\- Fetch news from subscribed sites\n"
        "\\- Evening Digest at 7 PM\n"
        "\\- Market news at 8 AM\n"
        "\\- Instant breaking news alerts\n\n"
        "Use /menu to see all options\\.",
        parse_mode=ParseMode.MARKDOWN_V2
    )


async def cmd_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        return await unauthorized_reply(update)
    keyboard = [
        [
            InlineKeyboardButton("Category Update", callback_data="menu_category"),
            InlineKeyboardButton("Breaking News Now", callback_data="menu_breaking"),
        ],
        [
            InlineKeyboardButton("Complete Day Summary", callback_data="menu_day_summary"),
            InlineKeyboardButton("Status", callback_data="menu_status"),
        ],
        [
            InlineKeyboardButton("Help", callback_data="menu_help"),
        ]
    ]
    await update.message.reply_text(
        "*PulseAgent Menu*\n\nChoose an option:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode=ParseMode.MARKDOWN_V2
    )


async def cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        return await unauthorized_reply(update)
    from src.database.db import get_unsent_digest_items
    pending = len(get_unsent_digest_items())
    await update.message.reply_text(
        f"*Bot Status*\n\n"
        f"Bot is running\n"
        f"Items in digest queue: {pending}\n"
        f"Evening digest at: 7:00 PM\n"
        f"Market briefing at: 8:00 AM\n"
        f"Breaking news check: every 30 min",
        parse_mode=ParseMode.MARKDOWN_V2
    )


async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if not is_authorized(update):
        await query.edit_message_text("Not authorized.")
        return

    data = query.data

    if data == "menu_category":
        await show_category_keyboard(query)

    elif data == "menu_breaking":
        await query.edit_message_text("Checking for breaking news now...")
        from src.scheduler.jobs import run_breaking_news_check
        count = await run_breaking_news_check()
        msg = "No breaking news at this moment\\. All clear\\!" if count == 0 else f"Sent {count} breaking news alert\\(s\\)\\!"
        await query.edit_message_text(msg, parse_mode=ParseMode.MARKDOWN_V2)

    elif data == "menu_status":
        from src.database.db import get_unsent_digest_items
        pending = len(get_unsent_digest_items())
        await query.edit_message_text(
            f"*Status*\n\nRunning\nQueue: {pending} items",
            parse_mode=ParseMode.MARKDOWN_V2
        )

    elif data == "menu_help":
        await query.edit_message_text(
            "*Help*\n\n"
            "/start \\- Welcome message\n"
            "/menu \\- Open this menu\n"
            "/status \\- Check bot status\n\n"
            "Auto sends:\n"
            "\\- Evening Digest at 7 PM\n"
            "\\- Market Briefing at 8 AM\n"
            "\\- Breaking news instantly",
            parse_mode=ParseMode.MARKDOWN_V2
        )

    elif data.startswith("cat_"):
        category = data[4:]
        if category == "OTHER":
            await query.edit_message_text("Please type the category or topic you want updates on:")
            context.user_data["awaiting_category"] = True
        else:
            await query.edit_message_text(f"Fetching updates for *{category}*\\.\\.\\.", parse_mode=ParseMode.MARKDOWN_V2)
            content = summarize_custom_query(category)
            msg = format_category_update(category, content)
            await query.edit_message_text(msg, parse_mode=ParseMode.MARKDOWN_V2, disable_web_page_preview=True)

    elif data == "menu_day_summary":
        await query.edit_message_text("Preparing complete day summary...")
        from src.database.db import get_todays_all_items
        from src.processors.message_formatter import format_evening_digest, format_youtube_update

        items = get_todays_all_items()
        if not items:
            await query.edit_message_text(
                "No items collected today yet. Use /fetch\\_now first.",
                parse_mode="MarkdownV2"
            )
            return

        youtube_items = [i for i in items if i["source_type"] == "youtube"]
        news_items = [i for i in items if i["source_type"] != "youtube"]

        await query.edit_message_text(
            f"Found {len(news_items)} news + {len(youtube_items)} videos today. Sending now..."
        )

        if news_items:
            formatted = [{
                "id": i["item_id"],
                "title": i["title"],
                "ai_summary": i["summary"] or f"• {i['title']}",
                "category": i["category"] or "World News",
                "url": i["source_url"],
                "source_type": i["source_type"]
            } for i in news_items]

            messages = format_evening_digest(formatted)
            for msg in messages:
                try:
                    await _app.bot.send_message(
                        chat_id=query.message.chat_id,
                        text=msg, parse_mode="MarkdownV2",
                        disable_web_page_preview=True
                    )
                except Exception:
                    import re
                    plain = re.sub(r'\\(.)', r'\1', msg)
                    await _app.bot.send_message(
                        chat_id=query.message.chat_id,
                        text=plain, disable_web_page_preview=True
                    )

        if youtube_items:
            for i in youtube_items:
                item = {
                    "title": i["title"],
                    "ai_summary": i["summary"] or f"• {i['title']}",
                    "category": i["category"] or "General",
                    "url": i["source_url"],
                    "channel": "YouTube"
                }
                try:
                    msg = format_youtube_update(item)
                    await _app.bot.send_message(
                        chat_id=query.message.chat_id,
                        text=msg, parse_mode="MarkdownV2",
                        disable_web_page_preview=True
                    )
                except Exception:
                    await _app.bot.send_message(
                        chat_id=query.message.chat_id,
                        text=f"Video: {i['title']}\n{i['source_url']}",
                        disable_web_page_preview=True
                    )

async def show_category_keyboard(query):
    buttons = []
    row = []
    for cat in NEWS_CATEGORIES:
        row.append(InlineKeyboardButton(cat, callback_data=f"cat_{cat}"))
        if len(row) == 2:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    buttons.append([InlineKeyboardButton("Other - Type your own", callback_data="cat_OTHER")])
    await query.edit_message_text(
        "*Choose a Category:*",
        reply_markup=InlineKeyboardMarkup(buttons),
        parse_mode=ParseMode.MARKDOWN_V2
    )


async def handle_text_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.user_data.get("awaiting_category"):
        return
    category = update.message.text.strip()
    context.user_data["awaiting_category"] = False
    await update.message.reply_text(f"Fetching updates for *{category}*\\.\\.\\.", parse_mode=ParseMode.MARKDOWN_V2)
    content = summarize_custom_query(category)
    msg = format_category_update(category, content)
    await update.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN_V2, disable_web_page_preview=True)


async def send_message_to_all_users(text: str, parse_mode=ParseMode.MARKDOWN_V2):
    global _app
    if not _app or not ALLOWED_USER_IDS:
        logger.warning("No app or no users configured.")
        return
    for user_id in ALLOWED_USER_IDS:
        try:
            await _app.bot.send_message(
                chat_id=user_id, text=text,
                parse_mode=parse_mode, disable_web_page_preview=True
            )
        except Exception as e:
            logger.error(f"Failed to send to {user_id}: {e}")

async def cmd_fetch_now(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Fetch all news and send directly to user — no queue, instant output."""
    if not is_authorized(update):
        return await unauthorized_reply(update)

    await update.message.reply_text(
        "Fetching latest news now... sending results directly. This may take 2-3 minutes."
    )

    from src.scrapers.news_scraper import fetch_rss_articles, fetch_all_category_news
    from src.scrapers.youtube_scraper import fetch_new_youtube_videos
    from src.processors.ai_processor import batch_summarize
    from src.processors.message_formatter import format_evening_digest, format_youtube_update
    from src.database.db import mark_as_sent

    # Fetch all sources
    rss_items = fetch_rss_articles()
    news_items = fetch_all_category_news()
    youtube_items = fetch_new_youtube_videos()
    all_news = rss_items + news_items

    if not all_news and not youtube_items:
        await update.message.reply_text("No new articles or videos found right now.")
        return

    await update.message.reply_text(
        f"Found {len(all_news)} news articles and {len(youtube_items)} YouTube videos. Summarizing..."
    )

    # Send news digest directly
    if all_news:
        processed_news = batch_summarize(all_news, source_type="news")
        messages = format_evening_digest(processed_news)
        for msg in messages:
            try:
                await update.message.reply_text(
                    msg, parse_mode="MarkdownV2", disable_web_page_preview=True
                )
            except Exception:
                # Strip markdown and send as plain text if formatting fails
                import re
                plain = re.sub(r'\\(.)', r'\1', msg)
                await update.message.reply_text(plain, disable_web_page_preview=True)
        for item in processed_news:
            mark_as_sent(item["id"], item["source_type"], item["title"])

    # Send YouTube updates directly
    if youtube_items:
        processed_yt = batch_summarize(youtube_items, source_type="youtube")
        for item in processed_yt:
            try:
                msg = format_youtube_update(item)
                await update.message.reply_text(
                    msg, parse_mode="MarkdownV2", disable_web_page_preview=True
                )
            except Exception:
                await update.message.reply_text(
                    f"New Video: {item['title']}\n{item.get('url', '')}",
                    disable_web_page_preview=True
                )
            mark_as_sent(item["id"], "youtube", item["title"])

    await update.message.reply_text("All done! Everything above is your latest update.")

async def cmd_day_summary(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send complete summary of everything collected today."""
    if not is_authorized(update):
        return await unauthorized_reply(update)

    await update.message.reply_text(
        "Preparing your complete day summary... fetching everything collected today."
    )

    from src.database.db import get_todays_all_items
    from src.processors.message_formatter import format_evening_digest, format_youtube_update

    items = get_todays_all_items()

    if not items:
        await update.message.reply_text(
            "No items collected today yet. Use /fetch_now to fetch latest news first."
        )
        return

    # Separate youtube and news
    youtube_items = [i for i in items if i["source_type"] == "youtube"]
    news_items = [i for i in items if i["source_type"] != "youtube"]

    await update.message.reply_text(
        f"Today's collection: {len(news_items)} news articles + {len(youtube_items)} YouTube videos."
    )

    # Send news digest
    if news_items:
        # Convert db rows to format expected by formatter
        formatted = [{
            "id": i["item_id"],
            "title": i["title"],
            "ai_summary": i["summary"] or f"• {i['title']}",
            "category": i["category"] or "World News",
            "url": i["source_url"],
            "source_type": i["source_type"]
        } for i in news_items]

        messages = format_evening_digest(formatted)
        for msg in messages:
            try:
                await update.message.reply_text(
                    msg, parse_mode="MarkdownV2", disable_web_page_preview=True
                )
            except Exception:
                import re
                plain = re.sub(r'\\(.)', r'\1', msg)
                await update.message.reply_text(plain, disable_web_page_preview=True)

    # Send YouTube items
    if youtube_items:
        await update.message.reply_text("--- YouTube Videos Today ---")
        for i in youtube_items:
            item = {
                "title": i["title"],
                "ai_summary": i["summary"] or f"• {i['title']}",
                "category": i["category"] or "General",
                "url": i["source_url"],
                "channel": "YouTube"
            }
            try:
                msg = format_youtube_update(item)
                await update.message.reply_text(
                    msg, parse_mode="MarkdownV2", disable_web_page_preview=True
                )
            except Exception:
                await update.message.reply_text(
                    f"Video: {i['title']}\n{i['source_url']}",
                    disable_web_page_preview=True
                )

    from datetime import datetime
    time_str = datetime.now().strftime("%I:%M %p")
    await update.message.reply_text(
        f"Complete day summary done. All news collected from midnight till {time_str}."
    )

def build_app() -> Application:
    global _app
    init_db()
    from telegram.request import HTTPXRequest # type: ignore
    request = HTTPXRequest(
        connect_timeout=30.0,
        read_timeout=30.0,
        write_timeout=30.0,
        pool_timeout=30.0,
    )
    _app = Application.builder().token(TELEGRAM_BOT_TOKEN).request(request).build()
    _app.add_handler(CommandHandler("start", cmd_start))
    _app.add_handler(CommandHandler("menu", cmd_menu))
    _app.add_handler(CommandHandler("status", cmd_status))
    _app.add_handler(CommandHandler("fetch_now", cmd_fetch_now))
    _app.add_handler(CommandHandler("day_summary", cmd_day_summary))
    _app.add_handler(CallbackQueryHandler(handle_callback))
    _app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_input))
    logger.info("Telegram app built successfully.")
    return _app