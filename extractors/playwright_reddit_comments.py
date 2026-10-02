"""
playwright_reddit_comments.py

Stage 2: Comment enrichment.
Reads reddit_posts_*.ndjson files from the drop folder,
visits each post URL, and extracts top-level + depth-1 reply comments.
Outputs reddit_comments_<timestamp>.ndjson to the same drop folder.
"""
import time
import json
import random
from pathlib import Path
from playwright.sync_api import sync_playwright
from core.config import BRONZE_DROP_DIR

def load_posts():
    """Load all unique post URLs from reddit_posts_*.ndjson files."""
    posts = []
    seen = set()
    for f in sorted(BRONZE_DROP_DIR.glob("reddit_posts_*.ndjson")):
        with open(f, encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    record = json.loads(line)
                    url = record.get("url")
                    if url and url not in seen:
                        seen.add(url)
                        posts.append(record)
                except Exception:
                    pass
    return posts


def scrape_comments(page, post):
    """Visit a post page and extract depth-0 and depth-1 comments."""
    comments = []
    url = post["url"]

    # Ensure we hit the comment page, not a crosspost or external link
    if not url.startswith("https://www.reddit.com"):
        url = "https://www.reddit.com" + url if url.startswith("/r/") else None
    if not url:
        return comments

    try:
        page.goto(url, wait_until="domcontentloaded", timeout=20000)
        page.wait_for_timeout(2000)

        # Light scroll to reveal more comments
        for _ in range(5):
            page.evaluate("window.scrollBy(0, 600)")
            time.sleep(random.uniform(0.8, 1.5))

        comment_els = page.locator("shreddit-comment").all()

        for el in comment_els:
            depth = el.get_attribute("depth") or "0"
            # Only capture depth 0 (top-level) and depth 1 (direct replies)
            if int(depth) > 1:
                continue

            author = el.get_attribute("author") or "unknown"
            score = el.get_attribute("score") or ""

            # Comment body lives inside the slot content
            body_el = el.locator("[slot='comment-content'] p").all()
            body = " ".join(p.text_content().strip() for p in body_el if p.text_content()).strip()

            if body:
                comments.append({
                    "platform": "reddit",
                    "type": "comment",
                    "post_url": url,
                    "post_title": post.get("title", ""),
                    "keyword": post.get("keyword", ""),
                    "subreddit": post.get("subreddit", ""),
                    "depth": int(depth),
                    "author": author,
                    "score": score,
                    "body": body[:1000],
                    "scraped_at": int(time.time())
                })

    except Exception as e:
        print(f"  ⚠️  Error on {url}: {e}")

    return comments


def run():
    posts = load_posts()
    if not posts:
        print("[Reddit Comments] No post files found. Run playwright_reddit.py first.")
        return

    print(f"[Reddit Comments] Found {len(posts)} unique posts to visit...")

    all_comments = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 720}
        )
        page = context.new_page()
        page.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

        for i, post in enumerate(posts, 1):
            print(f"[{i}/{len(posts)}] {post['title'][:70]}...")
            comments = scrape_comments(page, post)
            all_comments.extend(comments)
            print(f"  → {len(comments)} comments (total: {len(all_comments)})")
            time.sleep(random.uniform(2.0, 4.0))

        browser.close()

    if all_comments:
        out_file = BRONZE_DROP_DIR / f"reddit_comments_{int(time.time())}.ndjson"
        with open(out_file, "w", encoding="utf-8") as f:
            for c in all_comments:
                f.write(json.dumps(c) + "\n")
        print(f"\n[Reddit Comments] Done. Saved {len(all_comments)} comments → {out_file}")
    else:
        print("[Reddit Comments] No comments captured.")


if __name__ == "__main__":
    run()
