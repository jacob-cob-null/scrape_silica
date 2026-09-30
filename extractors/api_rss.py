import os
import json
import time
import feedparser
from core.config import BRONZE_AUTO_DIR, ALL_KEYWORDS

def run():
    print("Running RSS Feeds Extractor...")
    for keyword in ALL_KEYWORDS:
        data = {
            "platform": "rss",
            "tier": "contextual",
            "source_id": f"mock_rss_{int(time.time())}_{hash(keyword)}",
            "raw_content": f"News: RSS feed update discussing {keyword}.",
            "timestamp_utc": int(time.time())
        }
        filename = BRONZE_AUTO_DIR / f"rss_{int(time.time())}_{hash(keyword)}.json"
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f)
    print("RSS extraction complete.")
