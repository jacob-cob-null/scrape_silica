import json
import time
from pathlib import Path
from core.config import BRONZE_DROP_DIR, BRONZE_AUTO_DIR

def parse_ndjson(file_path):
    print(f"Parsing {file_path}")
    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            try:
                data = json.loads(line)
                platform = data.get("platform", "facebook")
                raw_content = data.get("node", {}).get("text", "No text found")
                source_id = data.get("id", str(time.time()))
                
                bronze_record = {
                    "platform": platform,
                    "tier": "contextual",
                    "source_id": source_id,
                    "raw_content": raw_content,
                    "timestamp_utc": int(time.time())
                }
                
                out_filename = BRONZE_AUTO_DIR / f"{platform}_{int(time.time()*1000)}.json"
                with open(out_filename, 'w', encoding='utf-8') as out_f:
                    json.dump(bronze_record, out_f)
            except json.JSONDecodeError:
                continue

def run():
    print("Watching Zeeschuimer drop folder for NDJSON files...")
    for file_path in BRONZE_DROP_DIR.glob("*.ndjson"):
        parse_ndjson(file_path)
    print("Drop folder processing complete.")
