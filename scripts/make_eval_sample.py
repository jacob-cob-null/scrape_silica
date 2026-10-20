"""
make_eval_sample.py

Builds a stratified random evaluation sample from the Silver layer for validating
the Laya decision model.

The record mirrors the GOLD schema (platform, decision_rating, confidence, content)
and adds only what labeling needs: a row id, the join key, the ground-truth label and
a notes field. Nothing else is carried.

Columns:
    row_id            stable 1..N reference for discussing rows
    content_hash      primary key in silver_records (join key)
    platform          gold field
    content           gold field (cleaned text, truncated for readability)
    decision_rating   gold field, filled by scripts/score_eval.py (0-100)
    confidence        gold field, filled by scripts/score_eval.py (0-100)
    label_relevance   GROUND TRUTH for decision_rating: none|weak|direct|core
    label_notes       free text for review scratch (artifacts, ambiguity)

Usage:
    $env:PYTHONPATH="."; python scripts\make_eval_sample.py
    $env:PYTHONPATH="."; python scripts\make_eval_sample.py --size 400 --seed 7
"""

import argparse
import shutil
import sys
import zlib
from pathlib import Path

import duckdb
import pandas as pd

from core.database import DB_PATH
from core.schema import GOLD_COLUMNS

# Console on Windows defaults to cp1252 and crashes on emoji in scraped text.
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

REPO = Path(__file__).resolve().parent.parent
DEFAULT_OUT = REPO / "eval" / "laya_sample.csv"

# Gold field for the text is `content`. Truncated for readability while labeling.
TEXT_LIMIT = 1500

# Known synthetic content to exclude from the sample.
EXCLUDE_PATTERNS = ["Mock %", "%Golden Node%"]

GROUND_TRUTH_COLUMNS = ["label_relevance", "label_notes"]

# Gold fields the scorer fills in, derived from the shared schema so the eval
# record and the gold export cannot drift apart.
RATING_COLUMNS = [c for c in GOLD_COLUMNS if c not in ("platform", "content")]

RELEVANCE_VALUES = {"none", "weak", "direct", "core"}

# Patterns that indicate non-discourse (reported, not stored as a column).
ARTIFACT_HINTS = ["Forum user discussion regarding"]


def allocate(counts: dict[str, int], size: int, floor: int) -> dict[str, int]:
    """Largest-remainder allocation with a per-platform floor, capped at availability."""
    if size >= sum(counts.values()):
        return dict(counts)

    base = {p: min(floor, c) for p, c in counts.items()}
    remaining = size - sum(base.values())

    if remaining < 0:  # floor budget exceeds the requested size
        base = {p: 0 for p in counts}
        remaining = size

    active = {p: c - base[p] for p, c in counts.items() if c - base[p] > 0}
    remaining = min(remaining, sum(active.values()))

    total_active = sum(active.values())
    quotas = {p: remaining * v / total_active for p, v in active.items()}
    alloc = {p: int(q) for p, q in quotas.items()}
    leftover = remaining - sum(alloc.values())
    for p in sorted(quotas, key=lambda k: quotas[k] - int(quotas[k]), reverse=True)[:leftover]:
        alloc[p] += 1

    out = {p: base.get(p, 0) + alloc.get(p, 0) for p in counts}

    shortfall = size - sum(out.values())
    while shortfall > 0:
        candidates = [p for p in counts if counts[p] - out[p] > 0]
        if not candidates:
            break
        p = max(candidates, key=lambda k: counts[k] - out[k])
        out[p] += 1
        shortfall -= 1
    return out


def load_eligible(conn: duckdb.DuckDBPyConnection) -> pd.DataFrame:
    exclusions = " ".join(
        f"AND cleaned_content NOT ILIKE '{pattern}'" for pattern in EXCLUDE_PATTERNS
    )
    return conn.execute(
        f"""
        SELECT platform, content_hash
        FROM silver_records
        WHERE 1 = 1 {exclusions}
        """
    ).df()


def sample_rows(eligible: pd.DataFrame, allocation: dict[str, int], seed: int) -> pd.DataFrame:
    picks = []
    for platform, n in allocation.items():
        if n <= 0:
            continue
        group = eligible[eligible["platform"] == platform]
        if group.empty:
            continue
        # crc32 gives a stable per-platform seed (Python's hash() is salted).
        group_seed = seed + zlib.crc32(platform.encode("utf-8")) % 100_000
        picks.append(group.sample(n=min(n, len(group)), random_state=group_seed))
    if not picks:
        return eligible.head(0)
    return pd.concat(picks, ignore_index=True)


def fetch_content(conn: duckdb.DuckDBPyConnection, hashes: list[str]) -> dict[str, str]:
    conn.execute("CREATE OR REPLACE TEMP TABLE picks(content_hash VARCHAR)")
    conn.executemany("INSERT INTO picks VALUES (?)", [(h,) for h in hashes])
    rows = conn.execute(
        """
        SELECT s.content_hash, s.cleaned_content
        FROM silver_records s JOIN picks USING (content_hash)
        """
    ).fetchall()
    return {h: text for h, text in rows}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--size", type=int, default=400, help="total rows (default 400)")
    parser.add_argument("--seed", type=int, default=42, help="random seed (default 42)")
    parser.add_argument("--floor", type=int, default=10, help="min rows per platform")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()

    if not DB_PATH.exists():
        raise SystemExit(f"Silver DB not found: {DB_PATH}")

    conn = duckdb.connect(str(DB_PATH), read_only=True)
    try:
        eligible = load_eligible(conn)
        counts = eligible["platform"].value_counts().to_dict()
        allocation = allocate(counts, args.size, args.floor)
        sampled = sample_rows(eligible, allocation, args.seed)
        content = fetch_content(conn, sampled["content_hash"].tolist())
    finally:
        conn.close()

    sampled = sampled.copy()
    sampled["cleaned_content"] = sampled["content_hash"].map(content)
    sampled = sampled[sampled["cleaned_content"].notna()].reset_index(drop=True)
    sampled["row_id"] = sampled.index + 1

    sampled["content"] = sampled["cleaned_content"].str.slice(0, TEXT_LIMIT)

    for col in GROUND_TRUTH_COLUMNS + RATING_COLUMNS:
        sampled[col] = ""

    sampled = sampled[
        ["row_id", "content_hash", "platform", "content"]
        + RATING_COLUMNS
        + GROUND_TRUTH_COLUMNS
    ]

    # Don't silently destroy labeling work if the existing sample has labels.
    if args.out.exists():
        existing = pd.read_csv(args.out, dtype=str, keep_default_na=False)
        labeled = 0
        if "label_relevance" in existing.columns:
            labeled = int(existing["label_relevance"].str.strip().isin(RELEVANCE_VALUES).sum())
        if labeled:
            backup = args.out.with_name(args.out.stem + "_backup.csv")
            shutil.copy2(args.out, backup)
            print(f"Existing sample had {labeled} filled labels -> backed up to {backup}")

    args.out.parent.mkdir(parents=True, exist_ok=True)
    sampled.to_csv(args.out, index=False, encoding="utf-8-sig", quoting=1)

    print(f"\nWrote {len(sampled)} rows to {args.out} (seed={args.seed}, floor={args.floor})")
    print(f"Columns: {', '.join(sampled.columns)}")
    comp = (
        pd.DataFrame({"sampled": sampled["platform"].value_counts(),
                      "available": pd.Series(counts)})
        .fillna(0)
        .astype(int)
        .sort_values("sampled", ascending=False)
    )
    comp["pct"] = (comp["sampled"] / comp["sampled"].sum() * 100).round(1)
    print()
    print(comp.to_string())

    # Artifacts are no longer a column, so report them once for awareness.
    artifacts = sampled["content"].str.startswith(tuple(ARTIFACT_HINTS))
    short = sampled["content"].str.len() < 15
    print(f"\nManual-review hints: {int(artifacts.sum())} scraper artifacts, "
          f"{int(short.sum())} very short (<15 chars). Note these in label_notes.")


if __name__ == "__main__":
    main()
