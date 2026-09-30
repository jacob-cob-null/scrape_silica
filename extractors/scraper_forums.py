import time
import json
import httpx
import urllib.parse
from bs4 import BeautifulSoup
from core.config import BRONZE_AUTO_DIR, ALL_KEYWORDS

def run():
    print("Running Forums Scraper (DuckDuckGo -> SkyscraperCity)...")
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    
    for keyword in ALL_KEYWORDS:
        try:
            # Search SkyscraperCity specifically via DuckDuckGo HTML
            encoded_kw = urllib.parse.quote(f"site:skyscrapercity.com {keyword}")
            url = f"https://html.duckduckgo.com/html/?q={encoded_kw}"
            
            res = httpx.get(url, headers=headers, timeout=15.0)
            if res.status_code == 200:
                soup = BeautifulSoup(res.text, 'html.parser')
                results = soup.find_all('a', class_='result__snippet')
                
                for idx, result in enumerate(results):
                    snippet_text = result.get_text(strip=True)
                    if not snippet_text:
                        continue
                        
                    safe_kw = keyword.replace(' ', '_').replace('"', '').replace(':', '')
                    data = {
                        "platform": "skyscrapercity",
                        "tier": "contextual",
                        "source_id": f"ssc_{safe_kw}_{idx}_{int(time.time())}",
                        "raw_content": snippet_text,
                        "timestamp_utc": int(time.time())
                    }
                    filename = BRONZE_AUTO_DIR / f"forum_{safe_kw}_{idx}_{int(time.time())}.json"
                    with open(filename, 'w', encoding='utf-8') as f:
                        json.dump(data, f)
            time.sleep(2.0) # Be very gentle with DDG
        except Exception as e:
            print(f"Error scraping forums for {keyword}: {e}")
            
    print("Forums extraction complete.")
