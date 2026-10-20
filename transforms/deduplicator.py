import hashlib
import duckdb
from .cleaner import clean_text

def clean_and_hash_record(record: dict) -> tuple[str, str, str] | None:
    """
    Cleans raw content and generates a deterministic content hash.
    Returns (content_hash, platform, cleaned_content) or None if filtered out.
    """
    raw_content = record.get('raw_content', '')
    platform = record.get('platform', 'unknown')
    
    cleaned_content = clean_text(raw_content)
    if not cleaned_content:
        return None
        
    content_without_whitespace = "".join(cleaned_content.split())
    hash_input = platform.lower() + content_without_whitespace.lower()
    content_hash = hashlib.sha256(hash_input.encode('utf-8')).hexdigest()
    return (content_hash, platform, cleaned_content)

def insert_records_batch(batch: list[tuple[str, str, str]], conn: duckdb.DuckDBPyConnection) -> int:
    """
    Batch inserts records into silver_records using DuckDB executemany.
    Deduplication is handled automatically via ON CONFLICT DO NOTHING.
    """
    if not batch:
        return 0
    try:
        conn.executemany("""
            INSERT INTO silver_records (content_hash, platform, cleaned_content)
            VALUES (?, ?, ?)
            ON CONFLICT (content_hash) DO NOTHING
        """, batch)
        return len(batch)
    except Exception as e:
        print(f"Error inserting batch: {e}")
        return 0

