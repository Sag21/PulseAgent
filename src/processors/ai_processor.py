"""
src/processors/ai_processor.py
================================
Handles all Gemini API calls:
  - Summarize YouTube videos (using direct URL input)
  - Summarize news articles
  - Categorize content
  - Detect if content is breaking news
"""

import google.generativeai as genai # type: ignore
import logging
import time
from config.settings import GEMINI_API_KEY, GEMINI_MODEL, NEWS_CATEGORIES

logger = logging.getLogger(__name__)

# Configure Gemini once at import
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel(GEMINI_MODEL)

RATE_LIMIT_DELAY = 3  # seconds between API calls to avoid hitting rate limits


def _call_gemini(prompt: str, retries: int = 2) -> str:
    """Safe wrapper around Gemini API with retries."""
    for attempt in range(retries + 1):
        try:
            response = model.generate_content(prompt)
            time.sleep(RATE_LIMIT_DELAY)
            return response.text.strip()
        except Exception as e:
            error_str = str(e)
            logger.error(f"Gemini API error (attempt {attempt + 1}): {error_str[:200]}")
            # If quota exhausted (429), stop retrying immediately - no point waiting
            if "429" in error_str or "quota" in error_str.lower():
                logger.warning("Gemini quota exhausted - skipping retries, using fallback.")
                return ""
            if attempt < retries:
                time.sleep(10)
    return ""


def make_fallback_summary(title: str, snippet: str = "") -> dict:
    """
    When Gemini is unavailable, build a basic summary from
    the article title and NewsAPI description snippet directly.
    No AI needed.
    """
    if snippet and len(snippet) > 20:
        summary = f"• {snippet[:300]}"
    else:
        summary = f"• {title}"

    return {
        "summary": summary,
        "category": _guess_category(title),
        "is_breaking": any(kw in title.lower() for kw in [
            "breaking", "urgent", "alert", "attack", "disaster",
            "earthquake", "explosion", "crash", "emergency"
        ])
    }


def _guess_category(title: str) -> str:
    """Guess category from title keywords when Gemini is unavailable."""
    title_lower = title.lower()
    if any(w in title_lower for w in ["stock", "market", "sensex", "nifty", "nasdaq", "economy", "trade", "gdp"]):
        return "Stock & Market"
    if any(w in title_lower for w in ["cricket", "football", "ipl", "fifa", "sport", "match", "tournament", "player"]):
        return "Sports"
    if any(w in title_lower for w in ["film", "movie", "actor", "actress", "bollywood", "hollywood", "cinema"]):
        return "Films & Entertainment"
    if any(w in title_lower for w in ["music", "song", "album", "singer", "concert"]):
        return "Music"
    if any(w in title_lower for w in ["tech", "ai ", "software", "apple", "google", "microsoft", "startup", "cyber"]):
        return "Technology"
    if any(w in title_lower for w in ["health", "hospital", "disease", "vaccine", "cancer", "medical", "doctor"]):
        return "Health"
    if any(w in title_lower for w in ["science", "space", "nasa", "climate", "environment", "planet"]):
        return "Science"
    return "World News"


def summarize_youtube_video(video_url: str, title: str) -> dict:
    """
    Summarizes a YouTube video using Gemini's native YouTube URL support.
    Returns: {summary, category, is_breaking}
    """
    prompt = f"""You are a concise news summarizer. Analyze this YouTube video and provide:

1. A 3-5 bullet point summary of the key points discussed.
2. The best category from this list: {', '.join(NEWS_CATEGORIES)}
3. Whether this is BREAKING NEWS (true/false) - only true for urgent, time-sensitive events.

Video URL: {video_url}
Video Title: {title}

Respond in this EXACT format:
SUMMARY:
• [point 1]
• [point 2]
• [point 3]
CATEGORY: [category name]
BREAKING: [true/false]
"""
    raw = _call_gemini(prompt)
    return _parse_ai_response(raw, fallback_title=title)


def summarize_article(url: str, title: str, snippet: str = "") -> dict:
    """
    Summarizes a news article using its URL and available snippet.
    Returns: {summary, category, is_breaking}
    """
    prompt = f"""You are a concise news summarizer. Based on the article details below, provide:

1. A 2-4 bullet point summary of the key points.
2. The best category from: {', '.join(NEWS_CATEGORIES)}
3. Whether this is BREAKING NEWS (true/false) - only for urgent/critical events.

Article Title: {title}
Article URL: {url}
Snippet: {snippet[:500] if snippet else "No snippet available."}

Respond in this EXACT format:
SUMMARY:
• [point 1]
• [point 2]
CATEGORY: [category name]
BREAKING: [true/false]
"""
    raw = _call_gemini(prompt)
    return _parse_ai_response(raw, fallback_title=title)


def summarize_custom_query(query: str) -> str:
    """
    Generate a quick summary/overview for a user-requested category or topic.
    Used when user clicks a category button in the bot.
    """
    prompt = f"""Provide a brief, 3-5 bullet point overview of the latest developments in: {query}

Focus on the most recent and important updates. Be concise and factual.

Format:
📌 Latest in {query}:
• [point 1]
• [point 2]
• [point 3]

End with: "⏰ Summary generated at [current time]"
"""
    return _call_gemini(prompt) or f"Could not fetch updates for '{query}' right now."


def batch_summarize(items: list[dict], source_type: str) -> list[dict]:
    """
    Process a batch of items with rate limiting.
    Falls back to snippet-based summary if Gemini is unavailable.
    """
    processed = []
    for i, item in enumerate(items):
        logger.info(f"Processing [{i+1}/{len(items)}]: {item['title'][:60]}")

        if source_type == "youtube":
            result = summarize_youtube_video(item["url"], item["title"])
        else:
            result = summarize_article(
                item["url"], item["title"], item.get("summary_hint", "")
            )

        # If Gemini failed (empty summary), use fallback directly from snippet
        if not result.get("summary") or result["summary"] == f"📄 {item.get('title', '')}":
            result = make_fallback_summary(
                item["title"],
                item.get("summary_hint", "")
            )
            logger.info(f"  Used fallback summary for: {item['title'][:50]}")

        item["ai_summary"] = result.get("summary", f"• {item['title']}")
        item["category"] = result.get("category", "World News")
        item["is_breaking"] = result.get("is_breaking", False)
        processed.append(item)

        # Batch pause every 5 items
        if (i + 1) % 5 == 0:
            logger.info("Rate limit pause (12 seconds)...")
            time.sleep(12)

    return processed


# ── Private Helpers ───────────────────────────────────────────────────────────

def _parse_ai_response(raw: str, fallback_title: str = "") -> dict:
    """Parse structured Gemini response into a clean dict."""
    result = {
        "summary": f"📄 {fallback_title}",
        "category": "World News",
        "is_breaking": False
    }

    if not raw:
        return result

    lines = raw.split("\n")
    summary_lines = []
    in_summary = False

    for line in lines:
        line = line.strip()
        if line.startswith("SUMMARY:"):
            in_summary = True
        elif line.startswith("CATEGORY:"):
            in_summary = False
            cat = line.replace("CATEGORY:", "").strip()
            result["category"] = cat if cat else "World News"
        elif line.startswith("BREAKING:"):
            in_summary = False
            val = line.replace("BREAKING:", "").strip().lower()
            result["is_breaking"] = val == "true"
        elif in_summary and line.startswith("•"):
            summary_lines.append(line)

    if summary_lines:
        result["summary"] = "\n".join(summary_lines)

    return result
