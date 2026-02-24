"""
src/bot/telegram_bot.py
========================
Main Telegram bot — handles all user interactions, buttons, and message delivery.
"""

import logging
from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup, BotCommand
)
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, ContextTypes, ConversationHandler, filters
)
from telegram.constants import ParseMode

from config.settings import (
    TELEGRAM_BOT_TOKEN, ALLOWED_USER_IDS, NEWS_CATEGORIES
)
from src.processors.ai_processor import summarize_custom_query
from src.processors.message_formatter import format_category_update

logger = logging.getLogger(__name__)

# ConversationHandler states
WAITING_FOR_CUSTOM_CATEGORY = 1

# Global reference to the bot application (used by scheduler to send messages)
_app: Application = None


def get_app() -> Application:
    return _app


# ── Auth Guard ────────────────────────────────────────────────────────────────

def is_authorized(update: Update) -> bool:
    if not ALLOWED_USER_IDS:
        return True  # If no whitelist set, allow everyone (useful for testing)
    return update.effective_user.id in ALLOWED_USER_IDS


async def unauthorized_reply(update: Update):
    await update.effective_message.reply_text(
        "🔒 You are not authorized to use this bot."
    )


# ── Commands ──────────────────────────────────────────────────────────────────

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        return await unauthorized_reply(update)

    await update.message.reply_text(
        "👋 *Welcome to PulseAgent\\!*\n\n"
        "I'm your personal AI news assistant\\. Here's what I do:\n\n"
        "📺 Monitor your YouTube channels\n"
        "📰 Fetch news from your subscribed sites\n"
        "🌙 Send you an Evening Digest at 7 PM\n"
        "☀️ Send Market news every morning at 8 AM\n"
        "🚨 Alert you instantly for breaking news\n\n"
        "Use /menu to see all options\\.",
        parse_mode=ParseMode.MARKDOWN_V2
    )


async def cmd_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        return await unauthorized_reply(update)

    keyboard = [
        [
            InlineKeyboardButton("📰 Category Update", callback_data="menu_category"),
            InlineKeyboardButton("🚨 Breaking News Now", callback_data="menu_breaking"),
        ],
        [
            InlineKeyboardButton("📊 Status", callback_data="menu_status"),
            InlineKeyboardButton("❓ Help", callback_data="menu_help"),
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        "🎛️ *PulseAgent Menu*\n\nChoose an option below:",
        reply_markup=reply_markup,
        parse_mode=ParseMode.MARKDOWN_V2
    )


async def cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        return await unauthorized_reply(update)

    from src.database.db import get_unsent_digest_items
    pending = len(get_unsent_digest_items())

    await update.message.reply_text(
        f"📊 *Bot Status*\n\n"
        f"✅ Bot is running\n"
        f"📬 Items in digest queue: {pending}\n"
        f"🕐 Evening digest at: 7:00 PM\n"
        f"☀️ Market briefing at: 8:00 AM\n"
        f"🔁 Breaking news check: every 30 min",
        parse_mode=ParseMode.MARKDOWN_V2
    )


# ── Callback Query Handlers ───────────────────────────────────────────────────

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if not is_authorized(update):
        await query.edit_message_text("🔒 Not authorized.")
        return

    data = query.data

    if data == "menu_category":
        await show_category_keyboard(query)

    elif data == "menu_breaking":
        await query.edit_message_text("🔍 Checking for breaking news now...")
        from src.scheduler.jobs import run_breaking_news_check
        count = await run_breaking_news_check()
        if count == 0:
            await query.edit_message_text(
                "✅ No breaking news found at this moment\\. All clear\\!",
                parse_mode=ParseMode.MARKDOWN_V2
            )
        else:
            await query.edit_message_text(
                f"🚨 Sent {count} breaking news alert\\(s\\)\\!",
                parse_mode=ParseMode.MARKDOWN_V2
            )

    elif data == "menu_status":
        from src.database.db import get_unsent_digest_items
        pending = len(get_unsent_digest_items())
        await query.edit_message_text(
            f"📊 *Status*\n\n✅ Running\n📬 Queue: {pending} items",
            parse_mode=ParseMode.MARKDOWN_V2
        )

    elif data == "menu_help":
        await query.edit_message_text(
            "❓ *Help*\n\n"
            "/start \\- Welcome message\n"
            "/menu \\- Open this menu\n"
            "/status \\- Check bot status\n\n"
            "The bot automatically sends:\n"
            "• 🌙 Evening Digest at 7 PM\n"
            "• ☀️ Market Briefing at 8 AM\n"
            "• 🚨 Breaking news alerts immediately",
            parse_mode=ParseMode.MARKDOWN_V2
        )

    elif data.startswith("cat_"):
        category = data[4:]  # Strip "cat_" prefix
        if category == "OTHER":
            await query.edit_message_text(
                "✏️ Please type the category or topic you want updates on:"
            )
            context.user_data["awaiting_category"] = True
            return WAITING_FOR_CUSTOM_CATEGORY
        else:
            await query.edit_message_text(f"🔍 Fetching updates for *{category}*\\.\\.\\.", parse_mode=ParseMode.MARKDOWN_V2)
            content = summarize_custom_query(category)
            msg = format_category_update(category, content)
            await query.edit_message_text(msg, parse_mode=ParseMode.MARKDOWN_V2, disable_web_page_preview=True)


async def show_category_keyboard(query):
    """Show category selection buttons."""
    buttons = []
    row = []
    for i, cat in enumerate(NEWS_CATEGORIES):
        row.append(InlineKeyboardButton(cat, callback_data=f"cat_{cat}"))
        if len(row) == 2:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    buttons.append([InlineKeyboardButton("✏️ Other (Type your own)", callback_data="cat_OTHER")])

    await query.edit_message_text(
        "📰 *Choose a Category:*",
        reply_markup=InlineKeyboardMarkup(buttons),
        parse_mode=ParseMode.MARKDOWN_V2
    )


# ── Custom Category Input ─────────────────────────────────────────────────────

async def handle_custom_category_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle freeform category text from user."""
    if not context.user_data.get("awaiting_category"):
        return  # Not in custom category mode

    category = update.message.text.strip()
    context.user_data["awaiting_category"] = False

    await update.message.reply_text(f"🔍 Fetching updates for *{category}*\\.\\.\\.", parse_mode=ParseMode.MARKDOWN_V2)
    content = summarize_custom_query(category)
    msg = format_category_update(category, content)
    await update.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN_V2, disable_web_page_preview=True)


# ── Public API for Scheduler ──────────────────────────────────────────────────

async def send_message_to_all_users(text: str, parse_mode=ParseMode.MARKDOWN_V2):
    """Send a message to all authorized users. Called by the scheduler."""
    global _app
    if not _app or not ALLOWED_USER_IDS:
        logger.warning("No app or no users configured to send messages to.")
        return

    for user_id in ALLOWED_USER_IDS:
        try:
            await _app.bot.send_message(
                chat_id=user_id,
                text=text,
                parse_mode=parse_mode,
                disable_web_page_preview=True
            )
        except Exception as e:
            logger.error(f"Failed to send message to {user_id}: {e}")


# ── App Builder ───────────────────────────────────────────────────────────────

async def start_bot():
    global _app

    _app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    # Register handlers
    _app.add_handler(CommandHandler("start", cmd_start))
    _app.add_handler(CommandHandler("menu", cmd_menu))
    _app.add_handler(CommandHandler("status", cmd_status))
    _app.add_handler(CallbackQueryHandler(handle_callback))
    _app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_custom_category_input))

    # Set bot commands (shows up in Telegram menu)
    await _app.bot.set_my_commands([
        BotCommand("start", "Welcome message"),
        BotCommand("menu", "Open main menu"),
        BotCommand("status", "Check bot status"),
    ])

    logger.info("✅ Telegram bot started. Polling for messages...")
    await _app.run_polling(drop_pending_updates=True)
