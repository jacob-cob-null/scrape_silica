import json
import time
import feedparser
import urllib.parse
from core.config import BRONZE_AUTO_DIR, ALL_KEYWORDS

def run():
    print("Running RSS Feeds Extractor (Google News)...")
    for keyword in ALL_KEYWORDS:
        try:
            encoded_kw = urllib.parse.quote(keyword)
            # Fetch Google News RSS for the Philippines
            feed_url = f"https://news.google.com/rss/search?q={encoded_kw}&hl=en-PH&gl=PH&ceid=PH:en"
            feed = feedparser.parse(feed_url)
            
            for entry in feed.entries:
                title = entry.title
                summary = entry.get('summary', '')
                raw_content = f"{title}\n{summary}"
                
                # Google News IDs are extremely long and break Windows MAX_PATH limits. 
                # We hash them to ensure safe filename lengths.
                import hashlib
                safe_id = hashlib.md5(entry.id.encode('utf-8')).hexdigest()
                
                data = {
                    "platform": "rss",
                    "tier": "contextual",
                    "source_id": f"rss_{safe_id}",
                    "raw_content": raw_content,
                    "timestamp_utc": int(time.time())
                }
                filename = BRONZE_AUTO_DIR / f"rss_{safe_id}.json"
                with open(filename, 'w', encoding='utf-8') as f:
                    json.dump(data, f)
            time.sleep(1.0)
        except Exception as e:
            print(f"Error parsing RSS for {keyword}: {e}")

    print("RSS extraction complete.")
