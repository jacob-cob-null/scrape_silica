import os
import json
import time
from atproto import Client
from core.config import BRONZE_AUTO_DIR, ALL_KEYWORDS

def run():
    print("Running Bluesky API Extractor...")
    handle = os.getenv('BLUESKY_HANDLE', '').strip().lstrip('@')
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

    try:
        client = Client()
        client.login(handle, password)
        
        for keyword in ALL_KEYWORDS:
            try:
                # Search posts
                res = client.app.bsky.feed.search_posts({'q': keyword, 'limit': 25})
                for post in res.posts:
                    source_id = f"bsky_{post.uri.split('/')[-1]}"
                    data = {
                        "platform": "bluesky",
                        "tier": "contextual",
                        "source_id": source_id,
                        "raw_content": post.record.text,
                        "timestamp_utc": int(time.time())
                    }
                    filename = BRONZE_AUTO_DIR / f"bluesky_{source_id}.json"
                    with open(filename, 'w', encoding='utf-8') as f:
                        json.dump(data, f)
                time.sleep(0.5)
            except Exception as e:
                print(f"Bluesky search error for {keyword}: {e}")
                
    except Exception as e:
        print(f"Bluesky login failed: {e}")

    print("Bluesky extraction complete.")
