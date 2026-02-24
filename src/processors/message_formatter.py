"""
src/processors/message_formatter.py
=====================================
Builds nicely formatted Telegram messages from processed items.
Uses Telegram's MarkdownV2 formatting.
"""

from datetime import datetime
from config.settings import NEWS_CATEGORIES


def escape_md(text: str) -> str:
    """Escape special characters for Telegram MarkdownV2."""
    special = r'_*[]()~`>#+-=|{}.!'
    return "".join(f"\\{c}" if c in special else c for c in str(text))


def format_breaking_news(item: dict) -> str:
    """Format a single breaking news item."""
    title = escape_md(item.get("title", "Breaking News"))
    summary = escape_md(item.get("ai_summary", ""))
    url = item.get("url", "")
    source = escape_md(item.get("source", item.get("channel", "Unknown")))
    timestamp = datetime.now().strftime("%H:%M")

    return (
        f"🚨 *BREAKING NEWS* 🚨\n"
        f"🕐 {escape_md(timestamp)}\n\n"
        f"*{title}*\n\n"
        f"{summary}\n\n"
        f"📡 Source: {source}\n"
        f"🔗 [Read Full Story]({url})"
    )


def format_youtube_update(item: dict) -> str:
    """Format a new YouTube video notification."""
    title = escape_md(item.get("title", "New Video"))
    channel = escape_md(item.get("channel", "Unknown Channel"))
    summary = escape_md(item.get("ai_summary", ""))
    url = item.get("url", "")
    category = escape_md(item.get("category", "General"))

    return (
        f"📺 *New YouTube Video*\n"
        f"Channel: {channel}\n"
        f"Category: {category}\n\n"
        f"*{title}*\n\n"
        f"{summary}\n\n"
        f"🔗 [Watch Video]({url})"
    )


def format_evening_digest(items: list[dict]) -> list[str]:
    """
    Format the full evening digest grouped by category.
    Returns a list of messages (Telegram limit is 4096 chars per message).
    """
    if not items:
        return ["📭 No new updates collected today\\. Check back tomorrow\\!"]

    # Group by category
    categories: dict[str, list] = {}
    for item in items:
        cat = item.get("category", "World News")
        categories.setdefault(cat, []).append(item)

    date_str = escape_md(datetime.now().strftime("%A, %d %B %Y"))
    messages = []
    current_msg = f"📰 *PULSE AGENT — EVENING DIGEST*\n{date_str}\n{'=' * 30}\n\n"

    for category, cat_items in sorted(categories.items()):
        section = f"🏷️ *{escape_md(category)}*\n"

        for item in cat_items[:3]:  # Max 3 items per category in digest
            title = escape_md(item.get("title", "")[:80])
            summary_first_line = escape_md(
                item.get("ai_summary", "").split("\n")[0][:120]
            )
            url = item.get("url", "")
            section += f"\n• *{title}*\n  {summary_first_line}\n  🔗 [Read more]({url})\n"

        section += "\n"

        # Telegram max message length safety check
        if len(current_msg) + len(section) > 3800:
            messages.append(current_msg)
            current_msg = section
        else:
            current_msg += section

    messages.append(current_msg)
    return messages


def format_morning_market_digest(items: list[dict]) -> str:
    """Format the morning stock & market digest."""
    date_str = escape_md(datetime.now().strftime("%A, %d %B %Y"))

    if not items:
        return (
            f"📈 *MORNING MARKET BRIEFING*\n{date_str}\n\n"
            f"No market updates collected\\. Markets may be closed today\\."
        )

    msg = f"📈 *MORNING MARKET BRIEFING*\n{date_str}\n{'=' * 30}\n\n"
    for item in items[:5]:
        title = escape_md(item.get("title", "")[:80])
        summary = escape_md(item.get("ai_summary", "").split("\n")[0][:120])
        url = item.get("url", "")
        msg += f"• *{title}*\n  {summary}\n  🔗 [More]({url})\n\n"

    return msg


def format_category_update(category: str, content: str) -> str:
    """Format an on-demand category update requested by user."""
    cat_escaped = escape_md(category)
    content_escaped = escape_md(content)
    timestamp = escape_md(datetime.now().strftime("%H:%M, %d %b"))

    return (
        f"🔍 *Category Update: {cat_escaped}*\n"
        f"🕐 {timestamp}\n\n"
        f"{content_escaped}"
    )
