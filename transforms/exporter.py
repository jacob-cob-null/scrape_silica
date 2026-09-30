import duckdb
from core.config import GOLD_DIR
from core.database import get_connection
import pyarrow as pa
import pyarrow.parquet as pq
import csv

def export_gold():
    print("Exporting Gold Layer data...")
    conn = get_connection()
    
    try:
        # Only export records that passed the AI filter threshold (elastic scoring)
        # You can change '60' to '80' if you need strict accuracy, or '40' for more volume.
        query = "SELECT platform, cleaned_content AS content FROM silver_records WHERE relevance_score >= 60 OR relevance_score IS NULL"
        df = conn.execute(query).df()
        
        if df.empty:
            print("No data found in Silver layer to export.")
            return

        parquet_path = GOLD_DIR / "pax_silica_corpus.parquet"
        csv_path = GOLD_DIR / "pax_silica_corpus.csv"
        
        # Outputs:
        # 1. Parquet (using Snappy)
        df.to_parquet(parquet_path, compression='snappy')
        # 2. CSV (UTF-8 encoding, quoted fields)
        df.to_csv(csv_path, encoding='utf-8', index=False, quoting=csv.QUOTE_ALL)
        
        print(f"Exported {len(df)} records to {parquet_path} and {csv_path}")
    finally:
        conn.close()
