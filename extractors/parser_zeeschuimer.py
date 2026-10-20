import json
import time
from pathlib import Path
from core.config import BRONZE_DROP_DIR, BRONZE_ZEESCHUIMER_DIR, BRONZE_AUTO_DIR

def extract_record(data: dict) -> dict | None:
    """
    Normalizes raw record into {platform, raw_content, source_id, timestamp_utc}.
    Handles:
    - Reddit comments (body, post_title, etc.)
    - Reddit posts (title, selftext)
    - TikTok comments (data.text, cid)
    - TikTok posts/videos (data.desc, id)
    - Facebook/Instagram/Generic Zeeschuimer exports (node.text, text)
    - Standard Reddit API format (kind: t1/t3)
    """
    if not isinstance(data, dict):
        return None

    # 1. Direct Reddit comments (from playwright_reddit_comments.py)
    if data.get("type") == "comment" and "body" in data:
        body = data.get("body", "").strip()
        if not body or body in ["[deleted]", "[removed]"]:
            return None
        return {
            "platform": data.get("platform", "reddit"),
            "raw_content": body,
            "source_id": str(data.get("thing_id") or data.get("id") or ""),
            "timestamp_utc": data.get("scraped_at", int(time.time()))
        }

    # 2. Direct Reddit posts (from playwright_reddit.py)
    if data.get("type") == "post" and "title" in data:
        title = data.get("title", "").strip()
        selftext = data.get("selftext", "").strip()
        content = f"{title}\n{selftext}".strip() if selftext else title
        if not content:
            return None
        return {
            "platform": data.get("platform", "reddit"),
            "raw_content": content,
            "source_id": str(data.get("url") or data.get("id") or ""),
            "timestamp_utc": data.get("scraped_at", int(time.time()))
        }

    # 3. Zeeschuimer TikTok exports
    source_platform = str(data.get("source_platform", "")).lower()
    inner_data = data.get("data") if isinstance(data.get("data"), dict) else {}

    if "tiktok-comments" in source_platform or ("tiktok" in source_platform and "text" in inner_data):
        text = inner_data.get("text", "").strip()
        if not text:
            return None
        return {
            "platform": "tiktok",
            "raw_content": text,
            "source_id": str(inner_data.get("cid") or data.get("id") or ""),
            "timestamp_utc": inner_data.get("create_time", int(time.time()))
        }

    if "tiktok" in source_platform or "desc" in inner_data:
        desc = inner_data.get("desc", "").strip()
        if not desc:
            return None
        return {
            "platform": "tiktok",
            "raw_content": desc,
            "source_id": str(inner_data.get("id") or data.get("id") or ""),
            "timestamp_utc": inner_data.get("createTime", int(time.time()))
        }

    # 4. Standard Reddit API format (kind: t1 / t3)
    kind = data.get("kind")
    if kind in ["t1", "t3"]:
        reddit_data = data.get("data", {})
        if kind == "t3":
            title = reddit_data.get("title", "")
            selftext = reddit_data.get("selftext", "")
            raw_content = f"{title}\n{selftext}".strip()
        else:
            raw_content = reddit_data.get("body", "")
        if not raw_content or raw_content in ["[deleted]", "[removed]"]:
            return None
        return {
            "platform": "reddit",
            "raw_content": raw_content,
            "source_id": str(data.get("id") or reddit_data.get("id") or ""),
            "timestamp_utc": data.get("created_utc", int(time.time()))
        }

    # 5. Facebook / Instagram / generic node.text
    if "node" in data and isinstance(data["node"], dict):
        text = data["node"].get("text", "").strip()
        if text:
            platform = data.get("platform", "facebook")
            return {
                "platform": platform,
                "raw_content": text,
                "source_id": str(data.get("id") or ""),
                "timestamp_utc": data.get("timestamp", int(time.time()))
            }

    return None

def iter_ndjson_records(file_path: Path):
    """Yields extracted records from an ndjson file."""
    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                data = json.loads(line)
                rec = extract_record(data)
                if rec and rec["raw_content"]:
                    yield rec
            except Exception:
                continue

def parse_ndjson(file_path: Path):
    """Parses an NDJSON file and saves individual records to BRONZE_AUTO_DIR (if run standalone)."""
    print(f"Parsing {file_path.name} into Bronze JSONs...")
    count = 0
    for idx, rec in enumerate(iter_ndjson_records(file_path)):
        platform = rec["platform"]
        source_id = rec.get("source_id") or f"{int(time.time())}_{idx}"
        safe_id = "".join(c for c in source_id if c.isalnum() or c in ("-", "_"))[:50]
        out_filename = BRONZE_AUTO_DIR / f"{platform}_{safe_id}_{idx}.json"
        with open(out_filename, "w", encoding="utf-8") as out_f:
            json.dump(rec, out_f)
        count += 1
    print(f"  → Converted {count} records from {file_path.name}")
    return count

def run():
    print("Watching drop folders (drop_folder & zeeschuimer) for NDJSON files...")
    total_parsed = 0
    for file_path in BRONZE_DROP_DIR.glob("*.ndjson"):
        if "playwright" not in file_path.name:
            total_parsed += parse_ndjson(file_path)
            
    for file_path in BRONZE_ZEESCHUIMER_DIR.glob("*.ndjson"):
        total_parsed += parse_ndjson(file_path)
        
    print(f"Drop folder & Zeeschuimer processing complete: {total_parsed} records.")
