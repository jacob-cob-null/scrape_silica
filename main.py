import argparse
import json
import time

from core.config import BRONZE_AUTO_DIR, BRONZE_DROP_DIR, BRONZE_ZEESCHUIMER_DIR
from core.database import get_connection
from extractors import (
    api_youtube, api_bluesky, api_hacker_news, 
    parser_zeeschuimer,
    api_mastodon, api_rss, scraper_forums, 
    playwright_reddit, api_gdelt, api_youtube_transcripts
)
from extractors.parser_zeeschuimer import iter_ndjson_records
from transforms.deduplicator import clean_and_hash_record, insert_records_batch
from transforms import ai_filter
from transforms.exporter import export_gold

def ingest_automated(skip_transcripts=False):
    print("Running Automated API Ingestion...")
    api_youtube.run()
    api_bluesky.run()
    api_hacker_news.run()
    api_mastodon.run()
    api_rss.run()
    scraper_forums.run()
    api_gdelt.run()
    if not skip_transcripts:
        api_youtube_transcripts.run()
    else:
        print("Skipping YouTube Transcript Extractor (--skip-transcripts specified).")
    playwright_reddit.run()

def ingest_drop_folder():
    print("Running Drop Folder Ingestion...")
    parser_zeeschuimer.run()

def transform_data(skip_ai=False, ai_limit=None):
    print("Running Transform (Silver Cleaning and Gold Export)...")
    conn = get_connection()
    
    processed_count = 0
    scanned_count = 0
    batch = []
    BATCH_SIZE = 2000
    start_time = time.time()
    
    # 1. Ingest Automated API JSON files
    print("\n--- [Stage 1/3] Ingesting Automated Bronze JSON files ---")
    json_files = list(BRONZE_AUTO_DIR.glob("*.json"))
    print(f"Found {len(json_files):,} JSON files in {BRONZE_AUTO_DIR.name}...")
    for json_file in json_files:
        scanned_count += 1
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                record = json.load(f)
                row = clean_and_hash_record(record)
                if row:
                    batch.append(row)
        except Exception:
            continue
            
        if len(batch) >= BATCH_SIZE:
            processed_count += insert_records_batch(batch, conn)
            batch.clear()

        if scanned_count % 10000 == 0:
            elapsed = time.time() - start_time
            speed = scanned_count / elapsed if elapsed > 0 else 0
            print(f"Scanned {scanned_count:,}/{len(json_files):,} files | Ingested: {processed_count:,} | Speed: {speed:.1f} files/sec")
            
    if batch:
        processed_count += insert_records_batch(batch, conn)
        batch.clear()

    # 2. Ingest Drop Folder NDJSON files (Reddit comments & posts)
    print("\n--- [Stage 2/3] Ingesting Drop Folder NDJSON files (Reddit) ---")
    drop_files = sorted(BRONZE_DROP_DIR.glob("*.ndjson"))
    for df in drop_files:
        file_count = 0
        file_inserted = 0
        for rec in iter_ndjson_records(df):
            scanned_count += 1
            file_count += 1
            row = clean_and_hash_record(rec)
            if row:
                batch.append(row)
            if len(batch) >= BATCH_SIZE:
                file_inserted += insert_records_batch(batch, conn)
                batch.clear()
        if batch:
            file_inserted += insert_records_batch(batch, conn)
            batch.clear()
        processed_count += file_inserted
        print(f"  Processed {df.name}: {file_count:,} raw records ({file_inserted:,} valid)")

    # 3. Ingest Zeeschuimer NDJSON files (TikTok comments & posts)
    print("\n--- [Stage 3/3] Ingesting Zeeschuimer NDJSON files (TikTok) ---")
    zee_files = sorted(BRONZE_ZEESCHUIMER_DIR.glob("*.ndjson"))
    for zf in zee_files:
        file_count = 0
        file_inserted = 0
        for rec in iter_ndjson_records(zf):
            scanned_count += 1
            file_count += 1
            row = clean_and_hash_record(rec)
            if row:
                batch.append(row)
            if len(batch) >= BATCH_SIZE:
                file_inserted += insert_records_batch(batch, conn)
                batch.clear()
        if batch:
            file_inserted += insert_records_batch(batch, conn)
            batch.clear()
        processed_count += file_inserted
        print(f"  Processed {zf.name}: {file_count:,} raw records ({file_inserted:,} valid)")

    conn.close()
    elapsed = time.time() - start_time
    print(f"\nFinished Silver ingestion: scanned {scanned_count:,} items, processed {processed_count:,} valid records in {elapsed:.1f}s.")
    
    if not skip_ai:
        # Run the AI Semantic Filter
        ai_filter.run(limit=ai_limit)
    else:
        print("Skipping AI Semantic Filter as requested.")
        
    export_gold()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Pax Silica Data Pipeline")
    subparsers = parser.add_subparsers(dest="command")

    ingest_parser = subparsers.add_parser("ingest")
    ingest_parser.add_argument("--track", choices=["automated", "drop_folder"], required=True)
    ingest_parser.add_argument("--trial", action="store_true", help="Run with only 2 keywords for a quick test")
    ingest_parser.add_argument("--skip-transcripts", action="store_true", help="Skip the YouTube transcript extractor")

    transform_parser = subparsers.add_parser("transform")
    transform_parser.add_argument("--skip-ai", action="store_true", help="Skip the AI semantic filter stage")
    transform_parser.add_argument("--ai-limit", type=int, help="Limit the number of records the AI processes in this run")

    args = parser.parse_args()

    if args.command == "ingest":
        if getattr(args, 'trial', False):
            print("--- TRIAL MODE: Limiting to 2 keywords ---")
            from core.config import ALL_KEYWORDS
            ALL_KEYWORDS[:] = ALL_KEYWORDS[:2]
            
        if args.track == "automated":
            ingest_automated(skip_transcripts=getattr(args, 'skip_transcripts', False))
        elif args.track == "drop_folder":
            ingest_drop_folder()
    elif args.command == "transform":
        transform_data(skip_ai=getattr(args, 'skip_ai', False), ai_limit=getattr(args, 'ai_limit', None))
    else:
        parser.print_help()
