import duckdb
from .config import SILVER_DIR

DB_PATH = SILVER_DIR / "pax_silica_staging.duckdb"

def get_connection():
    conn = duckdb.connect(str(DB_PATH))
    # Create the staging table if it doesn't exist
    conn.execute("""
        CREATE TABLE IF NOT EXISTS silver_records (
            content_hash VARCHAR PRIMARY KEY,
            platform VARCHAR,
            cleaned_content VARCHAR
        )
    """)
    return conn
