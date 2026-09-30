import json
import time
import httpx
from core.config import BRONZE_AUTO_DIR, ALL_KEYWORDS

def run():
    print("Running Mastodon Extractor...")
    for keyword in ALL_KEYWORDS:
        try:
            url = f"https://mastodon.social/api/v2/search?q={keyword}&type=statuses"
            response = httpx.get(url, timeout=10.0)
            if response.status_code == 200:
                statuses = response.json().get('statuses', [])
                for status in statuses:
                    # Mastodon returns HTML content, we'll store it raw
                    raw_content = status.get('content', '')
                    if not raw_content:
                        continue
                        
                    data = {
                        "platform": "mastodon",
                        "tier": "contextual",
                        "source_id": f"masto_{status['id']}",
                        "raw_content": raw_content,
                        "timestamp_utc": int(time.time())
                    }
                    filename = BRONZE_AUTO_DIR / f"mastodon_{status['id']}.json"
                    with open(filename, 'w', encoding='utf-8') as f:
                        json.dump(data, f)
            time.sleep(1.0) # rate limit courtesy
        except Exception as e:
            print(f"Error fetching Mastodon for {keyword}: {e}")
            
    print("Mastodon extraction complete.")
