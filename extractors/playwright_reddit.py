import time
import json
import random
from playwright.sync_api import sync_playwright
from core.config import BRONZE_DROP_DIR, ALL_KEYWORDS

def run():
    print(f"[Reddit Posts] Starting scrape for {len(ALL_KEYWORDS)} keywords...")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 720}
        )
        page = context.new_page()
        page.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

        seen_urls = set()
        captured_posts = []

        for i, keyword in enumerate(ALL_KEYWORDS, 1):
            print(f"[{i}/{len(ALL_KEYWORDS)}] Searching: {keyword}")
            import urllib.parse
            encoded_query = urllib.parse.quote_plus(keyword)
            search_url = f"https://www.reddit.com/search/?q={encoded_query}&sort=relevance&t=all"
            try:
                page.goto(search_url, wait_until="domcontentloaded", timeout=20000)
                page.wait_for_timeout(2000)

                # Slow, steady scroll to load more posts
                for _ in range(12):
                    page.evaluate("window.scrollBy(0, 400)")
                    time.sleep(random.uniform(1.0, 2.0))

                posts = page.locator("shreddit-post, faceplate-tracker, a[data-testid='post-title']").all()

                new_posts = 0
                for post in posts:
                    title = post.get_attribute("post-title") or post.text_content().strip()
                    author = post.get_attribute("author") or "unknown"
                    post_url = post.get_attribute("content-href") or post.get_attribute("href")
                    subreddit = post.get_attribute("subreddit-prefixed-name") or ""
                    score = post.get_attribute("score") or ""
                    comment_count = post.get_attribute("comment-count") or ""

                    if title and post_url and post_url not in seen_urls:
                        seen_urls.add(post_url)
                        captured_posts.append({
                            "platform": "reddit",
                            "type": "post",
                            "keyword": keyword,
                            "title": title[:200],
                            "author": author,
                            "subreddit": subreddit,
                            "score": score,
                            "comment_count": comment_count,
                            "url": post_url,
                            "scraped_at": int(time.time())
                        })
                        new_posts += 1
                        print(f"  ✅ {title[:80].replace(chr(10), ' ')}")

                print(f"  → {new_posts} new posts (total: {len(captured_posts)})")

            except Exception as e:
                print(f"  ⚠️  Error on '{keyword}': {e}")

            # Pause between keyword searches
            time.sleep(random.uniform(3.0, 6.0))

        browser.close()

    if captured_posts:
        out_file = BRONZE_DROP_DIR / f"reddit_posts_{int(time.time())}.ndjson"
        with open(out_file, "w", encoding="utf-8") as f:
            for post in captured_posts:
                f.write(json.dumps(post) + "\n")
        print(f"\n[Reddit Posts] Done. Saved {len(captured_posts)} unique posts → {out_file}")
    else:
        print("[Reddit Posts] No posts captured.")

if __name__ == "__main__":
    run()
