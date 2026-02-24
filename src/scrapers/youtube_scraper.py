"""
src/scrapers/youtube_scraper.py
================================
Fetches new videos from YouTube channels via RSS feeds.
No API key needed for basic RSS scraping!
"""

import feedparser
import logging
from datetime import datetime, timezone
from config.settings import YOUTUBE_CHANNEL_IDS
from src.database.db import is_already_sent

logger = logging.getLogger(__name__)

RSS_BASE = "https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"


def fetch_new_youtube_videos() -> list[dict]:
    """
    Returns list of new (unseen) videos from subscribed channels.
    Each item: {id, title, url, channel, published}
    """
    new_videos = []

    for channel_id in YOUTUBE_CHANNEL_IDS:
        channel_id = channel_id.strip()
        if not channel_id:
            continue

        rss_url = RSS_BASE.format(channel_id=channel_id)
        try:
            feed = feedparser.parse(rss_url)
            channel_name = feed.feed.get("title", channel_id)

            for entry in feed.entries[:5]:  # Only check latest 5 videos
                video_id = entry.get("yt_videoid", entry.get("id", ""))
                video_url = f"https://www.youtube.com/watch?v={video_id}"
                title = entry.get("title", "Untitled")

                if is_already_sent(video_url):
                    continue

                new_videos.append({
                    "id": video_url,
                    "title": title,
                    "url": video_url,
                    "channel": channel_name,
                    "published": entry.get("published", ""),
                    "source_type": "youtube"
                })

            logger.debug(f"Checked channel: {channel_name}")

        except Exception as e:
            logger.error(f"Error fetching YouTube RSS for {channel_id}: {e}")

    logger.info(f"📺 YouTube: Found {len(new_videos)} new videos.")
    return new_videos
