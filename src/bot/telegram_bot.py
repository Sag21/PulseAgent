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
            InlineKeyboardButton("Status", callback_data="menu_status"),
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
    _app.add_handler(CallbackQueryHandler(handle_callback))
    _app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_input))
    logger.info("Telegram app built successfully.")
    return _app