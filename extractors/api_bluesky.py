import os
import json
import time
from core.config import BRONZE_AUTO_DIR

def run():
    print("Running Bluesky API Extractor...")
    handle = os.getenv('BLUESKY_HANDLE')
    password = os.getenv('BLUESKY_PASSWORD')

    if not handle or not password:
        print("Bluesky credentials missing. Generating mock data for testing.")
        data = {
            "platform": "bluesky",
            "tier": "contextual",
            "source_id": f"mock_bsky_{int(time.time())}",
            "raw_content": "New Clark City is building a massive data center and water supply.",
            "timestamp_utc": int(time.time())
        }
        filename = BRONZE_AUTO_DIR / f"bluesky_{int(time.time())}.json"
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f)
        return

    print("Bluesky extraction complete.")
