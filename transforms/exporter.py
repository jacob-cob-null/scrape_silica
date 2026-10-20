import csv

from core.config import GOLD_DIR
from core.database import get_connection
from core.schema import GOLD_COLUMNS


def export_gold():
    """Export the gold layer: platform, decision_rating, confidence, content.

    Exactly the four fields in core.schema.GOLD_COLUMNS. Rows that the AI filter
    has not rated yet are still exported, with blank rating fields.
    """
    print("Exporting Gold Layer data...")
    conn = get_connection()

    try:
        query = """
            SELECT
                platform,
                CAST(decision_rating AS INTEGER) AS decision_rating,
                CAST(confidence AS INTEGER) AS confidence,
                cleaned_content AS content
            FROM silver_records
            ORDER BY platform, cleaned_content
        """
        df = conn.execute(query).df()

        if df.empty:
            print("No data found in Silver layer to export.")
            return

        # Enforce the shared schema, in order.
        df = df[GOLD_COLUMNS]

        # Nullable integers so unrated rows write as empty, not "50.0".
        for col in ("decision_rating", "confidence"):
            df[col] = df[col].astype("Int64")

        rated = int(df["decision_rating"].notna().sum())
        print(f"  {rated:,}/{len(df):,} rows have an AI rating; "
              f"{len(df) - rated:,} are blank.")

        parquet_path = GOLD_DIR / "pax_silica_corpus.parquet"
        csv_path = GOLD_DIR / "pax_silica_corpus.csv"

        # Snappy Parquet + UTF-8 CSV with quoted fields.
        df.to_parquet(parquet_path, compression="snappy")
        df.to_csv(csv_path, encoding="utf-8", index=False, quoting=csv.QUOTE_ALL)

        print(f"Exported {len(df)} rows x {len(GOLD_COLUMNS)} columns "
              f"to {parquet_path.name} and {csv_path.name}")
    finally:
        conn.close()
