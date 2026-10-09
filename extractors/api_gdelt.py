import json
import time
import requests
import hashlib
from core.config import BRONZE_AUTO_DIR, TIER_1_BRAND, TIER_2_ANCHORS

def run():
    print("Running GDELT Project API (Global News)...")
    
    # We only use Tier 1 and Tier 2 for GDELT, as news articles are broad
    queries = TIER_1_BRAND + TIER_2_ANCHORS
    
    headers = {
        "User-Agent": "PaxSilicaResearch/1.0 (Academic Research Pipeline)"
    }
    
    success_count = 0
    
    for query in queries:
        # Wrap query in quotes for exact match if it has spaces
        q_param = f'"{query}"' if " " in query else query
        
        url = f"https://api.gdeltproject.org/api/v2/doc/doc?query={q_param}&mode=artlist&maxrecords=250&format=json&sort=DateDesc"
        
        try:
            resp = requests.get(url, headers=headers, timeout=15)
            if resp.status_code == 200:
                data = resp.json()
                articles = data.get("articles", [])
                
                for art in articles:
                    url_link = art.get("url", "")
                    title = art.get("title", "")
                    domain = art.get("domain", "")
                    
                    if not url_link:
                        continue
                        
                    # Hash URL for unique ID
                    url_hash = hashlib.md5(url_link.encode()).hexdigest()
                    out_file = BRONZE_AUTO_DIR / f"gdelt_{url_hash}.json"
                    
                    if out_file.exists():
                        continue
                        
                    content = f"{title}\n{domain}\n{url_link}"
                    
                    record = {
                        "platform": "gdelt_news",
                        "tier": "broad",
                        "source_id": f"gdelt_{url_hash}",
                        "raw_content": content,
                        "url": url_link,
                        "timestamp_utc": int(time.time()),
                        "keyword": query
                    }
                    
                    with open(out_file, 'w', encoding='utf-8') as fh:
                        json.dump(record, fh)
                        
                    success_count += 1
                    
            print(f"  ✓ {query} -> Found {len(articles)} articles")
            
        except Exception as e:
            print(f"  ⚠️ Error fetching {query}: {e}")
            
        # GDELT limit is roughly 1 request per second
        time.sleep(2)
        
    print(f"Finished GDELT News. Saved {success_count} new news records.")

if __name__ == "__main__":
    run()
