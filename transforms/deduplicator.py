import hashlib
import duckdb
from .cleaner import clean_text
from core.database import get_connection

def process_record(record: dict, conn: duckdb.DuckDBPyConnection):
    """
    Processes a single record from the Bronze layer.
    Applies the cleaner and deduplicator, then upserts to DuckDB.
    """
    raw_content = record.get('raw_content', '')
    platform = record.get('platform', 'unknown')
    
    cleaned_content = clean_text(raw_content)
    if not cleaned_content:
        return False
        
    # Deduplication
    content_without_whitespace = "".join(cleaned_content.split())
    hash_input = platform.lower() + content_without_whitespace.lower()
    content_hash = hashlib.sha256(hash_input.encode('utf-8')).hexdigest()
    
    # Upsert into Silver DuckDB
    # DuckDB's ON CONFLICT DO NOTHING requires a UNIQUE or PRIMARY KEY, which we set.
    try:
        conn.execute("""
            INSERT INTO silver_records (content_hash, platform, cleaned_content)
            VALUES (?, ?, ?)
            ON CONFLICT (content_hash) DO NOTHING
        """, (content_hash, platform, cleaned_content))
        return True
    except Exception as e:
        print(f"Error inserting record: {e}")
        return False
