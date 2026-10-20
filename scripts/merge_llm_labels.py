"""
merge_llm_labels.py

Merges LLM annotator output (JSON) into eval/laya_sample.csv.

Writes the LLM's teacher labels into `label_relevance` and records provenance and
reasoning in `label_notes`, so machine labels stay distinguishable from human ones.
Also backfills Laya's `decision_rating`/`confidence` from the scored file when the
sample's gold fields are still blank, so one file holds the whole record.

IMPORTANT: the LLM's `confidence` field is the ANNOTATOR's certainty, NOT Laya's.
It is written into `label_notes` only. The gold `confidence` column keeps Laya's
value so the record stays gold-shaped.

Artifact rows are left with a blank `label_relevance` (score_eval.py ignores blanks),
so they never enter the metrics.

Accepts: a JSON array, JSONL, ```-fenced JSON, a JSON object wrapping a list under
results/rows/data/annotations/items, or a dict keyed by row_id.

Usage:
    $env:PYTHONPATH="."; python scripts\\merge_llm_labels.py
    $env:PYTHONPATH="."; python scripts\\merge_llm_labels.py --dry-run
    $env:PYTHONPATH="."; python scripts\\merge_llm_labels.py --input eval\\llm_batches\\annotations.json --overwrite
"""

import argparse
import json
import re
import shutil
import sys
from pathlib import Path

import pandas as pd

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

REPO = Path(__file__).resolve().parent.parent
DEFAULT_INPUT = REPO / "eval" / "llm_batches" / "annotations.json"
DEFAULT_SAMPLE = REPO / "eval" / "laya_sample.csv"
DEFAULT_SCORED = REPO / "eval" / "laya_sample_scored.csv"
CRITERIA_FILE = REPO / "eval" / "criteria.json"

# Accepted aliases for the LLM's output fields.
ID_KEYS = ("row_id", "id", "index")
LABEL_KEYS = ("relevance", "label", "relevance_label", "label_relevance")
WHY_KEYS = ("why", "reason", "explanation", "rationale")
CONF_KEYS = ("confidence", "conf", "llm_confidence")
REVIEW_KEYS = ("needs_review", "review", "flag_for_review")
ARTIFACT_KEYS = ("artifact", "is_artifact")


def load_scheme() -> tuple[set[str], float]:
    data = json.loads(CRITERIA_FILE.read_text(encoding="utf-8"))
    labels = set(data["questions"]["relevance"]["criteria"].keys())
    return labels, float(data.get("threshold", 50))


def pick(record: dict, keys: tuple[str, ...]):
    for key in keys:
        if key in record and record[key] is not None:
            return record[key]
    return None


def load_annotations(path: Path) -> list[dict]:
    if not path.exists():
        raise SystemExit(f"Annotator file not found: {path}")

    raw = path.read_text(encoding="utf-8-sig").strip()
    if not raw:
        raise SystemExit(
            f"{path} is empty (0 bytes). The annotator output was not saved - "
            "nothing to merge."
        )

    # Tolerate a ```json fence around the payload.
    if raw.startswith("```"):
        raw = re.sub(r"^```[a-zA-Z]*\s*", "", raw)
        raw = re.sub(r"\s*```$", "", raw)

    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        # Fall back to JSONL.
        rows = []
        for line_no, line in enumerate(raw.splitlines(), 1):
            line = line.strip().rstrip(",")
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise SystemExit(f"Cannot parse {path} as JSON or JSONL (line {line_no}): {exc}")
        data = rows

    if isinstance(data, dict):
        for key in ("results", "rows", "data", "annotations", "items"):
            if isinstance(data.get(key), list):
                data = data[key]
                break
        else:
            # Possibly keyed by row_id.
            keyed = []
            for key, value in data.items():
                if isinstance(value, dict):
                    value.setdefault("row_id", int(key) if str(key).isdigit() else key)
                    keyed.append(value)
            data = keyed

    if not isinstance(data, list):
        raise SystemExit(f"Unsupported JSON shape in {path}: {type(data).__name__}")

    records = []
    for i, item in enumerate(data):
        if not isinstance(item, dict):
            continue
        row_id = pick(item, ID_KEYS)
        if row_id is None:
            raise SystemExit(f"Record {i} has no row id field (looked for {ID_KEYS})")
        try:
            row_id = int(row_id)
        except (TypeError, ValueError):
            raise SystemExit(f"Record {i} has a non-integer row id: {row_id!r}")
        records.append({
            "row_id": row_id,
            "relevance": pick(item, LABEL_KEYS),
            "why": pick(item, WHY_KEYS),
            "llm_confidence": pick(item, CONF_KEYS),
            "needs_review": bool(pick(item, REVIEW_KEYS)),
            "artifact": bool(pick(item, ARTIFACT_KEYS)),
        })
    return records


def strip_generated_note(note: str) -> str:
    """Drop a previously generated artifact/LLM provenance block."""
    return re.split(r"(?:^|;\s*)(?:artifact|llm=)", note or "", maxsplit=1)[0].strip()


def build_note(existing: str, rec: dict) -> str:
    bits = []
    if rec["artifact"]:
        bits.append("artifact")
    bits.append(f"llm={rec['relevance']}")
    if rec["why"]:
        bits.append(f"why: {rec['why']}")
    if rec["llm_confidence"] is not None:
        try:
            bits.append(f"llm_conf={float(rec['llm_confidence']):g}")
        except (TypeError, ValueError):
            bits.append(f"llm_conf={rec['llm_confidence']}")
    if rec["needs_review"]:
        bits.append("needs_review")
    note = "; ".join(bits)
    existing = (existing or "").strip()
    return f"{existing}; {note}" if existing else note


def backfill_gold(df: pd.DataFrame, scored_path: Path, valid_labels: set[str]) -> int:
    """Fill blank decision_rating/confidence from the scored file, joined on row_id."""
    if not scored_path.exists():
        print(f"  note: {scored_path.name} not found; gold rating fields left as-is")
        return 0

    scored = pd.read_csv(scored_path, dtype=str, keep_default_na=False)
    if "row_id" not in scored.columns or "decision_rating" not in scored.columns:
        print(f"  note: {scored_path.name} lacks row_id/decision_rating; skipped")
        return 0

    lookup = {
        str(r["row_id"]): (r.get("decision_rating", ""), r.get("confidence", ""))
        for _, r in scored.iterrows()
    }

    filled = 0
    for idx, row in df.iterrows():
        if str(row.get("decision_rating", "")).strip():
            continue
        gold = lookup.get(str(row["row_id"]))
        if not gold or not str(gold[0]).strip():
            continue
        df.at[idx, "decision_rating"] = gold[0]
        df.at[idx, "confidence"] = gold[1]
        filled += 1
    return filled


def sanity_check(df: pd.DataFrame, valid_labels: set[str]) -> None:
    """Anchor test: texts that literally say 'Pax Silica' must be labelled positive.

    This is the cheapest way to catch an annotator whose row_id mapping broke,
    which produces coherent reasoning attached to the wrong text.
    """
    pax = re.compile(r"pax\s*[- ]?silica", re.I)
    positive = {"direct", "core"}
    long_enough = df["content"].str.len() >= 25

    anchor = df[long_enough & df["content"].str.contains(pax, na=False)]
    if anchor.empty:
        return

    caught = anchor["label_relevance"].isin(positive).sum()
    recall = caught / len(anchor)

    llm_pos = df[df["label_relevance"].isin(positive)]
    unanchored = (llm_pos[~llm_pos["content"].str.contains(pax, na=False)]
                  if not llm_pos.empty else llm_pos)

    print("\n--- annotator sanity check (anchor: text mentions 'Pax Silica') ---")
    print(f"  rows mentioning Pax Silica : {len(anchor)}")
    print(f"  of those labelled positive : {caught}  (recall {recall:.0%})")
    print(f"  positives with no mention  : {len(unanchored)}")

    if recall < 0.7:
        print("\n  *** LIKELY MISALIGNED OUTPUT ***")
        print("  An annotator that read these rows could not miss most explicit")
        print("  'Pax Silica' mentions. The reasoning below is attached to the wrong")
        print("  text - re-run the annotation, one row (or a small batch) per call.")
        for _, r in anchor[~anchor["label_relevance"].isin(positive)].head(8).iterrows():
            snippet = re.sub(r"\s+", " ", r["content"])[:58]
            print(f"    row {r['row_id']:>3}  labelled {r['label_relevance']:<6} "
                  f"| {snippet}")
        for _, r in unanchored.head(8).iterrows():
            snippet = re.sub(r"\s+", " ", r["content"])[:58]
            print(f"    row {r['row_id']:>3}  labelled {r['label_relevance']:<6} "
                  f"| {snippet}  (no 'Pax Silica' in text)")


def apply_labels(df: pd.DataFrame, records: list[dict], valid_labels: set[str],
                 overwrite: bool = False) -> dict:
    """Write annotator records into df's label columns, keyed by row_id."""
    df["row_id"] = df["row_id"].astype(str)
    by_id: dict[str, dict] = {}
    for rec in records:
        by_id.setdefault(str(rec["row_id"]), rec)

    merged = blanked_artifact = skipped = 0
    for idx, row in df.iterrows():
        rec = by_id.get(row["row_id"])
        if rec is None:
            continue
        if rec["relevance"] not in valid_labels:
            skipped += 1
            continue
        if rec["artifact"]:
            df.at[idx, "label_relevance"] = ""
            blanked_artifact += 1
        else:
            if str(row.get("label_relevance", "")).strip() and not overwrite:
                skipped += 1
                continue
            df.at[idx, "label_relevance"] = rec["relevance"]
            merged += 1
        existing = strip_generated_note(row.get("label_notes", ""))
        df.at[idx, "label_notes"] = build_note(existing, rec)

    return {"merged": merged, "blanked_artifact": blanked_artifact,
            "skipped": skipped, "by_id": by_id}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--sample", type=Path, default=DEFAULT_SAMPLE)
    parser.add_argument("--scored", type=Path, default=DEFAULT_SCORED,
                        help="source of Laya's ratings when the sample is blank")
    parser.add_argument("--out", type=Path, default=None, help="defaults to --sample (in place)")
    parser.add_argument("--dry-run", action="store_true", help="report only, write nothing")
    parser.add_argument("--overwrite", action="store_true",
                        help="replace labels that are already filled")
    args = parser.parse_args()

    valid_labels, threshold = load_scheme()
    records = load_annotations(args.input)

    if not args.sample.exists():
        raise SystemExit(f"Sample not found: {args.sample}")
    df = pd.read_csv(args.sample, dtype=str, keep_default_na=False)
    if "row_id" not in df.columns:
        raise SystemExit(f"{args.sample} has no row_id column")
    df["row_id"] = df["row_id"].astype(str)

    backfilled = backfill_gold(df, args.scored, valid_labels)
    if backfilled:
        print(f"Backfilled {backfilled} gold rating(s) from {args.scored.name}")

    rec_by_id: dict[str, dict] = {}
    for rec in records:
        rec_by_id.setdefault(str(rec["row_id"]), rec)

    known = set(df["row_id"])
    unknown = sorted(set(rec_by_id) - known, key=lambda v: (not v.isdigit(), v))
    dupes = len(records) - len(rec_by_id)
    invalid = [r for r in records
               if r["relevance"] not in valid_labels and not r["artifact"]]

    stats = apply_labels(df, records, valid_labels, args.overwrite)
    merged = stats["merged"]
    blanked_artifact = stats["blanked_artifact"]
    skipped = stats["skipped"]

    print(f"Read {len(records)} annotations from {args.input.name}")
    if dupes:
        print(f"  note: {dupes} duplicate row_id(s); last occurrence kept")
    if unknown:
        print(f"  WARNING: {len(unknown)} row_id(s) not in the sample: {unknown[:20]}")
    if invalid:
        print(f"  WARNING: {len(invalid)} record(s) with an unrecognized label: "
              f"{[r['relevance'] for r in invalid][:10]}")
    no_annotation = sorted(known - set(rec_by_id),
                           key=lambda v: int(v) if v.isdigit() else 0)
    if no_annotation:
        print(f"  {len(no_annotation)} sample row(s) had no annotation: "
              f"{no_annotation[:20]}")

    print(f"\nMerged {merged} labels | {blanked_artifact} artifact rows blanked "
          f"| {skipped} skipped (already labelled or invalid)")

    filled = df[df["label_relevance"].isin(valid_labels)]
    print("\nlabel_relevance distribution:")
    print(filled["label_relevance"].value_counts().reindex(
        ["none", "weak", "direct", "core"]).fillna(0).astype(int).to_string())

    review = int(filled["label_notes"].str.contains("needs_review", na=False).sum())
    print(f"\nrows flagged needs_review: {review}")

    # Laya vs LLM, the human review queue.
    ratings = pd.to_numeric(df["decision_rating"], errors="coerce")
    llm_positive = df["label_relevance"].isin(["direct", "core"])
    laya_positive = ratings >= threshold
    comparable = df["label_relevance"].ne("") & ratings.notna()

    missed = comparable & llm_positive & ~laya_positive
    false_pos = comparable & ~llm_positive & laya_positive
    agree = int((comparable & (llm_positive == laya_positive)).sum())

    print(f"\nLaya vs LLM at decision_rating >= {threshold:.0f} "
          f"({len(filled)} labelled rows): {agree} agree, "
          f"{int(missed.sum())} missed by Laya, {int(false_pos.sum())} extra from Laya")

    def show(mask, title):
        subset = df[mask]
        if subset.empty:
            return
        print(f"\n{title} ({len(subset)}):")
        for _, r in subset.head(30).iterrows():
            snippet = re.sub(r"\s+", " ", r["content"])[:70]
            print(f"  row {r['row_id']:>3}  llm={r['label_relevance']:<6} "
                  f"laya={r['decision_rating']:>3}  {snippet}")

    show(missed, "Missed by Laya - LLM says relevant")
    show(false_pos, "Extra from Laya - LLM says not relevant")
    show(df["label_notes"].str.contains("needs_review", na=False), "Flagged needs_review")

    sanity_check(df, valid_labels)

    if args.dry_run:
        print("\nDry run - nothing written.")
        return

    out = args.out or args.sample
    if not args.overwrite and out == args.sample:
        existing_labels = pd.read_csv(args.sample, dtype=str, keep_default_na=False)
        if existing_labels["label_relevance"].isin(valid_labels).any():
            backup = args.sample.with_name(args.sample.stem + "_backup.csv")
            shutil.copy2(args.sample, backup)
            print(f"\nBacked up previous labels to {backup}")

    out.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out, index=False, encoding="utf-8-sig", quoting=1)
    print(f"Wrote {len(df)} rows to {out}")


if __name__ == "__main__":
    main()
