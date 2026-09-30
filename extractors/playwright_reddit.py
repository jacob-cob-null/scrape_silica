import time
import json
import random
from playwright.sync_api import sync_playwright
from core.config import BRONZE_DROP_DIR, TIER_1_BRAND, TIER_2_ANCHORS

PLAYWRIGHT_SAFE_KEYWORDS = list(TIER_1_BRAND) + list(TIER_2_ANCHORS)

def run():
    print("Running Playwright Reddit Interceptor...")
    
    with sync_playwright() as p:
        # Launching visibly (headless=False) looks much more human to Cloudflare
        browser = p.chromium.launch(headless=False)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 720}
        )
        page = context.new_page()
        page.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
        captured_payloads = []
        
        def handle_response(response):
            if "gql.reddit.com" in response.url or "graphql" in response.url:
                try:
                    text = response.text()
                    if text:
                        data = json.loads(text)
                        # Store the raw intercepted JSON in our ndjson format
                        ndjson_record = {
                            "platform": "reddit_playwright",
                            "url": response.url,
                            "raw_json": data
                        }
                        captured_payloads.append(ndjson_record)
                except Exception:
                    pass

        page.on("response", handle_response)
        
        for keyword in PLAYWRIGHT_SAFE_KEYWORDS:
            print(f"Searching Reddit for: {keyword}")
            search_url = f"https://www.reddit.com/search/?q={keyword.replace(' ', '+')}"
            try:
                page.goto(search_url, wait_until="domcontentloaded", timeout=15000)
                
                # Slower, more human-like scrolling
                for i in range(15):
                    page.evaluate("window.scrollBy(0, 1000)")
                    time.sleep(random.uniform(3.0, 6.0))
                    
                # Pause between keyword searches so we don't hammer the server
                time.sleep(random.uniform(5.0, 10.0))
            except Exception as e:
                print(f"Timeout or error on {keyword}: {e}")
                
        browser.close()
        
        if captured_payloads:
            out_file = BRONZE_DROP_DIR / f"playwright_reddit_{int(time.time())}.ndjson"
            with open(out_file, "w", encoding="utf-8") as f:
                for payload in captured_payloads:
                    f.write(json.dumps(payload) + "\n")
            print(f"Saved {len(captured_payloads)} intercepted payloads to {out_file}")
            
            # Let's print a sample to see what we caught
            print("Sample payload keys:", captured_payloads[0]["raw_json"].keys())
        else:
            print("No payloads intercepted.")

if __name__ == "__main__":
    run()
