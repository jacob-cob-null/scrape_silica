import os
import json
import time
import httpx
from core.config import BRONZE_AUTO_DIR, ALL_KEYWORDS

def run():
    print("Running Mastodon Extractor...")
    for keyword in ALL_KEYWORDS:
        data = {
            "platform": "mastodon",
            "tier": "contextual",
            "source_id": f"mock_masto_{int(time.time())}_{hash(keyword)}",
            "raw_content": f"Mock discussion about {keyword} on Mastodon.",
            "timestamp_utc": int(time.time())
        }
        filename = BRONZE_AUTO_DIR / f"mastodon_{int(time.time())}_{hash(keyword)}.json"
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f)
    print("Mastodon extraction complete.")
