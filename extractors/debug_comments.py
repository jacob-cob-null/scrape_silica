"""
Diagnostic script to investigate why comment scraping returns 0 comments.
Visits a single Reddit post URL and dumps debug info about the page.
"""
import json
import time
from playwright.sync_api import sync_playwright

TEST_URL = "https://www.reddit.com/r/Philippines/comments/1up3iue/why_are_people_so_against_pax_silica_personally_i/"

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    context = browser.new_context(
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        viewport={"width": 1280, "height": 720}
    )
    page = context.new_page()
    page.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

    print(f"Navigating to: {TEST_URL}")
    page.goto(TEST_URL, wait_until="domcontentloaded", timeout=20000)
    print(f"Page title: {page.title()}")

    # Wait for page to settle
    page.wait_for_timeout(3000)

    # Scroll like the real scraper does
    for _ in range(5):
        page.evaluate("window.scrollBy(0, 600)")
        time.sleep(1)

    print("\n=== DIAGNOSTIC 1: Page URL after navigation ===")
    print(f"Current URL: {page.url}")

    print("\n=== DIAGNOSTIC 2: Check for login/block walls ===")
    # Check for common Reddit blockers
    login_wall = page.locator("[id='login'], [data-testid='login-modal'], .loginModal").count()
    print(f"Login wall elements found: {login_wall}")
    
    captcha = page.locator("[class*='captcha'], [id*='captcha'], iframe[src*='captcha']").count()
    print(f"Captcha elements found: {captcha}")

    print("\n=== DIAGNOSTIC 3: Search for shreddit-comment elements ===")
    shreddit_comments = page.locator("shreddit-comment").all()
    print(f"shreddit-comment elements: {len(shreddit_comments)}")

    if shreddit_comments:
        first = shreddit_comments[0]
        print(f"  First comment attrs: depth={first.get_attribute('depth')}, author={first.get_attribute('author')}")
        # Check for body content
        body_slot = first.locator("[slot='comment-content'] p").all()
        print(f"  Body <p> elements in [slot='comment-content']: {len(body_slot)}")
        if body_slot:
            print(f"  First <p> text: {body_slot[0].text_content()[:100]}")
        # Try other body selectors
        body_div = first.locator("div[id*='comment-body'], div[class*='comment']").all()
        print(f"  div elements with 'comment' in id/class: {len(body_div)}")
        all_p = first.locator("p").all()
        print(f"  All <p> elements inside shreddit-comment: {len(all_p)}")
        if all_p:
            for i, pp in enumerate(all_p[:3]):
                print(f"    p[{i}]: {pp.text_content()[:100]}")

    print("\n=== DIAGNOSTIC 4: Check for alternative comment structures ===")
    # Maybe Reddit changed the tag name
    for selector in [
        "shreddit-comment",
        "[data-testid='comment']",
        "[slot='comments']",
        "div.Comment",
        "div[class*='Comment']",
        ".comment",
        "#comment-tree",
        "faceplate-partial[loading='comments']",
        "faceplate-partial",
        "comment-body-header",
    ]:
        count = page.locator(selector).count()
        if count > 0:
            print(f"  ✅ '{selector}' → {count} elements")
        else:
            print(f"  ❌ '{selector}' → 0")

    print("\n=== DIAGNOSTIC 5: Sample of the page HTML (comment area) ===")
    # Get the full page HTML and search for comment-related strings
    html = page.content()
    
    # Check for specific strings
    for keyword in ["shreddit-comment", "comment-content", "comment-body", "commentTree", "comment_tree", "CommentsPage"]:
        count = html.count(keyword)
        print(f"  '{keyword}' appears {count} times in HTML")

    print(f"\n=== DIAGNOSTIC 6: HTML snippet (first 2000 chars after 'comment' keyword) ===")
    idx = html.lower().find("comment")
    if idx >= 0:
        print(html[max(0,idx-100):idx+2000])
    else:
        print("No 'comment' found in HTML at all!")
        print("\nFirst 3000 chars of page HTML:")
        print(html[:3000])

    browser.close()
    print("\n=== DIAGNOSTIC COMPLETE ===")
