import json
import time
from pathlib import Path
from core.config import BRONZE_DROP_DIR, BRONZE_AUTO_DIR

def extract_strings(obj):
    """Recursively extract all string values from a complex JSON object."""
    texts = []
    if isinstance(obj, dict):
        for key, value in obj.items():
            if key not in ['__typename', 'id', 'traceID', 'operation', 'url']: # Skip known metadata
                texts.extend(extract_strings(value))
    elif isinstance(obj, list):
        for item in obj:
            texts.extend(extract_strings(item))
    elif isinstance(obj, str):
        if len(obj) > 30: # Only grab strings long enough to be text
            texts.append(obj)
    return texts

def parse_playwright_ndjson(file_path):
    print(f"Parsing Playwright {file_path}")
    with open(file_path, 'r', encoding='utf-8') as f:
        for idx, line in enumerate(f):
            try:
                data = json.loads(line)
                platform = data.get("platform", "reddit_playwright")
                
                # Extract all readable text from the GraphQL payload
                raw_json = data.get("raw_json", {})
                extracted_texts = extract_strings(raw_json)
                raw_content = "\n".join(extracted_texts).strip()
                
                if not raw_content:
                    continue

                source_id = f"pw_{int(time.time())}_{idx}"
                
                bronze_record = {
                    "platform": platform,
                    "tier": "contextual",
                    "source_id": source_id,
                    "raw_content": raw_content,
                    "timestamp_utc": int(time.time())
                }
                
                out_filename = BRONZE_AUTO_DIR / f"{platform}_{source_id}.json"
                with open(out_filename, 'w', encoding='utf-8') as out_f:
                    json.dump(bronze_record, out_f)
            except json.JSONDecodeError:
                continue

def run():
    print("Watching drop folder for Playwright NDJSON files...")
    for file_path in BRONZE_DROP_DIR.glob("playwright_reddit_*.ndjson"):
        parse_playwright_ndjson(file_path)
    print("Playwright parser complete.")
