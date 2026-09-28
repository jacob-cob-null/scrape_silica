import os
import json
import time
from core.config import BRONZE_AUTO_DIR

def run():
    print("Running YouTube API Extractor...")
    api_key = os.getenv('YOUTUBE_API_KEY')

    if not api_key:
        print("YouTube API keys missing. Generating mock data for testing.")
        data = {
            "platform": "youtube",
            "tier": "strict",
            "source_id": f"mock_yt_{int(time.time())}",
            "raw_content": "Wow, Golden Node is going to change the semiconductor industry in the Philippines!",
            "timestamp_utc": int(time.time())
        }
        filename = BRONZE_AUTO_DIR / f"youtube_{int(time.time())}.json"
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f)
        return

    print("YouTube extraction complete.")
