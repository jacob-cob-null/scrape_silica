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

CHECKPOINT_FILE = Path(".reddit_checkpoint.txt")

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
        
    # Append ?sort=new to grab fresh comments that we haven't seen before
    if url and "?" not in url:
        url += "?sort=new"
    if not url:
        return comments

    try:
        page.goto(url, wait_until="domcontentloaded", timeout=20000)
        # Wait for comments to actually render (up to 10s)
        try:
            page.wait_for_selector("shreddit-comment", timeout=10000)
        except Exception:
            pass  # No comments on this post, continue gracefully
        page.wait_for_timeout(1000)  # Brief settle time after comments appear

        # Light scroll to reveal more comments
        for _ in range(5):
            page.evaluate("window.scrollBy(0, 600)")
            time.sleep(random.uniform(0.8, 1.5))

        comment_els = page.locator("shreddit-comment").all()

        if not comment_els:
            print(f"    [debug] No comment elements found. Title: {page.title()}, URL: {page.url[:80]}")


        for el in comment_els:
            depth = el.get_attribute("depth") or "0"
            # Capture depth 0-3 (top-level through nested replies)
            if int(depth) > 3:
                continue

            author = el.get_attribute("author") or "unknown"
            score = el.get_attribute("score") or ""
            thing_id = el.get_attribute("thingid") or ""

            # Comment body: grab all <p> tags directly inside the comment element
            body_el = el.locator("p").all()
            body = " ".join(
                p.text_content().strip() 
                for p in body_el 
                if p.text_content() and p.text_content().strip()
            ).strip()

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
                    "thing_id": thing_id,
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

    # --- CHECKPOINT LOGIC ---
    completed_urls = set()
    if CHECKPOINT_FILE.exists():
        with open(CHECKPOINT_FILE, "r", encoding="utf-8") as cf:
            completed_urls = set(line.strip() for line in cf if line.strip())
            
    posts = [p for p in posts if p["url"] not in completed_urls]
    
    if not posts:
        print("[Reddit Comments] All posts have already been processed (based on checkpoint).")
        # Clean up checkpoint so the next fresh run starts from scratch
        CHECKPOINT_FILE.unlink(missing_ok=True)
        return

    if completed_urls:
        print(f"[Reddit Comments] Resuming from checkpoint. Skipped {len(completed_urls)} already processed posts.")
        
    print(f"[Reddit Comments] Found {len(posts)} posts left to visit...")

    all_comments = []
    
    # Open file at the start to stream results and prevent data loss on crash
    out_file = BRONZE_DROP_DIR / f"reddit_comments_{int(time.time())}.ndjson"
    
    with sync_playwright() as p, open(out_file, "w", encoding="utf-8") as f:
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
            
            # Save immediately to prevent data loss!
            for c in comments:
                f.write(json.dumps(c) + "\n")
            f.flush()
            
            # Record this URL in the checkpoint file so we don't visit it again if we crash
            with open(CHECKPOINT_FILE, "a", encoding="utf-8") as cf:
                cf.write(post["url"] + "\n")
            
            print(f"  → {len(comments)} comments (total: {len(all_comments)})")
            # Increased wait time to 6-12 seconds to prevent Reddit IP bans (CAPTCHAs)
            time.sleep(random.uniform(6.0, 12.0))

        browser.close()

    if all_comments:
        print(f"\n[Reddit Comments] Done. Saved {len(all_comments)} comments → {out_file}")
    else:
        print("[Reddit Comments] No comments captured.")
        # Clean up empty file
        if out_file.exists():
            out_file.unlink()
            
    # If we reached the end successfully, delete the checkpoint file
    # so tomorrow's run starts fresh.
    if CHECKPOINT_FILE.exists():
        CHECKPOINT_FILE.unlink()


if __name__ == "__main__":
    run()
