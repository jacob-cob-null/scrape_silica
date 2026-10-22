"""
scripts/surgical_update.py

Performs a targeted, surgical update of the Silver DuckDB database and Gold export:
1. Audits silver_records against the updated 7-stage filter cascade.
2. Purges records that fail the quality gates (foreign language homonyms, ticker pumps).
3. Updates news records whose trailing domain suffixes were stripped, resetting
   decision_rating = NULL so they are re-scored.
4. Re-scores only modified unrated records via GPU batch inference (LAYA noul).
5. Refreshes the Gold Parquet and CSV analytical exports.
"""

from pathlib import Path
import time
import duckdb

from core.database import get_connection
from transforms.cleaner import clean_text
from transforms import ai_filter, exporter


def run_surgical_update():
    t_start = time.time()
    print("=" * 65)
    print("SURGICAL UPDATE: REFRESHING SILVER & GOLD RELEVANCE")
    print("=" * 65)

    conn = get_connection()

    try:
        print("\n[1/4] Auditing silver_records with updated cleaner...")
        t0 = time.time()
        rows = conn.execute(
            "SELECT content_hash, cleaned_content, decision_rating FROM silver_records"
        ).fetchall()
        total = len(rows)
        print(f"  Auditing {total:,} records across quality gates...")

        to_delete = []
        to_update = []

        for ch, content, rating in rows:
            cleaned = clean_text(content)
            if cleaned is None:
                to_delete.append(ch)
            elif cleaned != content:
                to_update.append((cleaned, ch))

        print(f"  Audit complete in {time.time() - t0:.1f}s.")
        print(f"  -> Records to purge (noise/foreign/ticker): {len(to_delete):,}")
        print(f"  -> Records to re-score (domain stripped):   {len(to_update):,}")

        if to_delete:
            print("\n[2/4] Purging invalid records from Silver database...")
            conn.executemany(
                "DELETE FROM silver_records WHERE content_hash = ?",
                [(h,) for h in to_delete],
            )
            print(f"  Successfully deleted {len(to_delete):,} rows.")

        if to_update:
            print("\n[3/4] Resetting modified records for re-scoring...")
            conn.executemany(
                "UPDATE silver_records SET cleaned_content = ?, decision_rating = NULL, confidence = NULL WHERE content_hash = ?",
                to_update,
            )
            print(f"  Successfully updated and reset {len(to_update):,} rows.")

    finally:
        conn.close()

    if to_update:
        print("\n[4/4] Re-scoring modified records on GPU via LAYA batching...")
        ai_filter.run(batch_size=32)
    else:
        print("\nNo records require GPU re-scoring.")

    print("\nRefreshing Gold analytical exports...")
    exporter.export_gold()

    elapsed = time.time() - t_start
    print(f"\nSurgical update completed in {elapsed:.1f}s!")


if __name__ == "__main__":
    run_surgical_update()
