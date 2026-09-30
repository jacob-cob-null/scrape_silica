import argparse
import json
from pathlib import Path

from core.config import BRONZE_AUTO_DIR
from core.database import get_connection
from extractors import api_youtube, api_bluesky, api_hacker_news, parser_zeeschuimer, api_mastodon, api_rss
from transforms.deduplicator import process_record
from transforms.exporter import export_gold

def ingest_automated():
    print("Running Automated API Ingestion...")
    api_youtube.run()
    api_bluesky.run()
    api_hacker_news.run()
    api_mastodon.run()
    api_rss.run()

def ingest_drop_folder():
    print("Running Drop Folder Ingestion...")
    parser_zeeschuimer.run()

def transform_data():
    print("Running Transform (Silver Cleaning and Gold Export)...")
    conn = get_connection()
    
    processed_count = 0
    try:
        for json_file in BRONZE_AUTO_DIR.glob("*.json"):
            with open(json_file, 'r', encoding='utf-8') as f:
                record = json.load(f)
                if process_record(record, conn):
                    processed_count += 1
    finally:
        conn.close()
        
    print(f"Processed {processed_count} records into Silver layer.")
    export_gold()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Pax Silica Data Pipeline")
    subparsers = parser.add_subparsers(dest="command")

    ingest_parser = subparsers.add_parser("ingest")
    ingest_parser.add_argument("--track", choices=["automated", "drop_folder"], required=True)

    transform_parser = subparsers.add_parser("transform")

    args = parser.parse_args()

    if args.command == "ingest":
        if args.track == "automated":
            ingest_automated()
        elif args.track == "drop_folder":
            ingest_drop_folder()
    elif args.command == "transform":
        transform_data()
    else:
        parser.print_help()
