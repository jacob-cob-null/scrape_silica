import time
import json
import httpx
from core.config import BRONZE_AUTO_DIR, ALL_KEYWORDS

def run():
    print("Running Hacker News Extractor (Algolia API)...")
    
    for keyword in ALL_KEYWORDS:
        url = f"http://hn.algolia.com/api/v1/search?query={keyword.replace(' ', '+')}"
        try:
            response = httpx.get(url, timeout=10.0)
            if response.status_code == 200:
                data = response.json()
                hits = data.get("hits", [])
                
                if not hits:
                    print(f"No HN hits for {keyword}")
                    continue
                    
                for hit in hits:
                    source_id = str(hit.get("objectID"))
                    title = hit.get("title") or ""
                    comment = hit.get("comment_text") or ""
                    
                    raw_content = f"{title}\n{comment}".strip()
                    if not raw_content:
                        continue
                        
                    record = {
                        "platform": "hacker_news",
                        "tier": "contextual",
                        "source_id": f"hn_{source_id}",
                        "raw_content": raw_content,
                        "timestamp_utc": int(time.time())
                    }
                    filename = BRONZE_AUTO_DIR / f"hacker_news_{source_id}.json"
                    with open(filename, 'w', encoding='utf-8') as f:
                        json.dump(record, f)
            time.sleep(1.0) # Be nice to the API
        except Exception as e:
            print(f"Error fetching HN for {keyword}: {e}")
            
    print("Hacker News extraction complete.")
