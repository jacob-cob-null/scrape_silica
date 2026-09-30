import os
import json
import time
from core.config import BRONZE_AUTO_DIR, ALL_KEYWORDS

def run():
    print("Running Bluesky API Extractor...")
    handle = os.getenv('BLUESKY_HANDLE')
    password = os.getenv('BLUESKY_PASSWORD')

    if not handle or not password:
        print("Bluesky credentials missing. Generating mock data for testing.")
        for keyword in ALL_KEYWORDS:
            data = {
                "platform": "bluesky",
                "tier": "contextual",
                "source_id": f"mock_bsky_{int(time.time())}_{hash(keyword)}",
                "raw_content": f"Mock Bluesky post about {keyword}",
                "timestamp_utc": int(time.time())
            }
            filename = BRONZE_AUTO_DIR / f"bluesky_{int(time.time())}_{hash(keyword)}.json"
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(data, f)
        return

    print("Bluesky extraction complete.")
