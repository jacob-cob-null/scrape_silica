"""
llm_batches.py

Mapping-safe LLM pre-annotation for eval/laya_sample.csv.

Why this exists: a single prompt containing all 400 rows produced labels attached
to the wrong text. The model echoed ids 1..400 by output position and lost the
correspondence partway through - the header rows were correct, later ones carried
reasoning that described a different row. 32 of the 42 rows that literally say
"Pax Silica" came back as `none`.

This splits the sample into small batches, each with its own prompt, and refuses
to merge a batch unless the returned row_ids match that batch exactly. A batch the
model scrambled is reported and skipped rather than silently absorbed.

Subcommands:
    make    write eval/llm_batches/batch_NN.prompt.txt + manifest.json
    merge   validate every returned batch_NN.json, then fill laya_sample.csv
    status  show which batches are done, missing or failing validation

Workflow:
    $env:PYTHONPATH="."; python scripts\\llm_batches.py make --size 15
    ... paste each prompt file into the LLM, save the reply as batch_NN.json ...
    $env:PYTHONPATH="."; python scripts\\llm_batches.py status
    $env:PYTHONPATH="."; python scripts\\llm_batches.py merge
"""

import argparse
import json
import random
import re
import sys
from pathlib import Path

import pandas as pd

from scripts.merge_llm_labels import (
    DEFAULT_SAMPLE,
    DEFAULT_SCORED,
    apply_labels,
    backfill_gold,
    load_annotations,
    load_scheme,
    sanity_check,
)

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

REPO = Path(__file__).resolve().parent.parent
BATCH_DIR = REPO / "eval" / "llm_batches"
MANIFEST = BATCH_DIR / "manifest.json"
CRITERIA_FILE = REPO / "eval" / "criteria.json"

# Text shown to the annotator is truncated to keep each prompt small.
TEXT_LIMIT = 600

PREAMBLE = """You are an annotator for a research dataset on Philippine online discourse about the
"Pax Silica" initiative: a U.S.-led economic and security project in the Philippines covering
semiconductor and AI infrastructure, data centres, critical minerals and the Luzon Economic
Corridor, including its sites (New Clark City, Clark, Tarlac) and its local impacts.

Label EACH text on RELEVANCE using exactly one of:

  none   - no link to the Pax Silica project and no link to its specific sites or impacts.
           Includes generic Philippine news, semiconductor or rare-earth news about other
           countries, and talk of Clark or Tarlac with no project connection.
  weak   - a passing or indirect connection: a project-associated site, agency or theme is
           mentioned but the project itself is not discussed.
  direct - discusses the project, its sites, agencies, industry or local impacts, but is not
           centred on it.
  core   - centred on Pax Silica or its direct consequences: support, opposition, displacement,
           land, water, jobs, corruption or naming.

RULES (apply strictly):
1. Language is irrelevant. Filipino, Tagalog, Taglish, Cebuano and English get the same
   standard. Never lower the label because the text is short or in Filipino.
2. Criticism and opposition count fully. "No to Pax Silica" is core, not none.
3. A place name alone is not relevance. "Bridge collapsed in Tarlac" is none.
4. A theme alone is not relevance. Rare earths in Malaysia, EU critical minerals, a US mining
   programme: none. Pax Silica is the anchor.
5. Short and vague is none, but if the referent is clearly the project, do not punish brevity.
6. Judge each text alone. Never infer from context or from other rows in the batch.
7. If torn between two labels, choose the lower one and set "needs_review": true.

ARTIFACT RULE: if a text is not user-generated discourse (scraper boilerplate such as
"Forum user discussion regarding X.", a bare URL, a seed fixture, or empty/emoji-only noise),
set "artifact": true and still give relevance "none".

Calibration examples (label, then text):
  core   - "Nararapat sa atin bansa ang pax silica makakatulong sa mga pilipinong manggagawa"
  core   - "Big NO to PAX SILICA"
  core   - "Kawawang pilipinas may tubig sa pax silica pero walang tubig sa mahihirap"
  core   - "Aetas and Farmers in Tarlac Defend Ancestral Lands, Warn Pax Silica AI Hub Threatens
            Farmlands and Water"
  direct - "Eight more countries, including South Korea, will participate in the Luzon Economic
            Corridor (LEC)"
  weak   - "Clark Global City is great .. More space, more convenience to stroll around the City"
  none   - "ICYMI: Tulay sa Tarlac, bumagsak" (a bridge collapsed in Tarlac)
  none   - "American Resources forms Indo-Pacific unit to lead Malaysia rare earth expansion"

CRITICAL - ID FIDELITY:
The "row_id" values in the input are authoritative identifiers, NOT sequence numbers.
Copy each row_id verbatim into your answer. Never renumber. Never invent an id. Your reply
must contain each input row_id exactly once and no other ids. If the input ids are
"7, 91, 132", your output ids are exactly 7, 91 and 132 - not 1, 2, 3.

Reply with JSON ONLY - an array with one object per input row, in the SAME ORDER as the input,
no prose, no code fences:
[
  {"row_id": <int>, "relevance": "none|weak|direct|core", "artifact": false,
   "confidence": <0.0-1.0>, "needs_review": false, "why": "<max 15 words>"}
]

Input rows:
"""


def batch_name(index: int) -> str:
    return f"batch_{index:02d}"


def load_manifest() -> dict:
    if not MANIFEST.exists():
        raise SystemExit("No manifest. Run: python scripts\\llm_batches.py make")
    return json.loads(MANIFEST.read_text(encoding="utf-8"))


def cmd_make(args: argparse.Namespace) -> None:
    df = pd.read_csv(args.sample, dtype=str, keep_default_na=False)
    valid_labels, _ = load_scheme()
    df["row_id"] = df["row_id"].astype(int)
    text_by_id = dict(zip(df["row_id"], df["content"].str.slice(0, TEXT_LIMIT)))

    BATCH_DIR.mkdir(parents=True, exist_ok=True)

    # Re-running make must not throw away work: preserve every batch whose
    # reply already validates, and only re-batch the rows not yet answered.
    # A reply that fails validation is discarded and its rows re-batched.
    preserved: dict[str, list[int]] = {}
    if MANIFEST.exists():
        old = json.loads(MANIFEST.read_text(encoding="utf-8"))
        for name, ids in old.get("batches", {}).items():
            records, problems = read_batch(name, ids)
            if records and not problems:
                preserved[name] = ids
            elif (BATCH_DIR / f"{name}.json").exists():
                (BATCH_DIR / f"{name}.json").unlink()
                (BATCH_DIR / f"{name}.prompt.txt").unlink(missing_ok=True)
                print(f"  discarded {name}: reply failed validation, rows re-batched")

    done = {i for ids in preserved.values() for i in ids}
    todo = df[~df["row_id"].isin(done)]
    if not args.all:
        todo = todo[~todo["label_relevance"].isin(valid_labels)]
    ids = todo["row_id"].tolist()

    start = 1
    if preserved:
        start = max(int(re.search(r"(\d+)", n).group(1)) for n in preserved) + 1

    # Shuffle then chunk, so no batch is a single platform/topic run that could
    # drag the labels. Row order inside a batch is restored to ascending row_id.
    rng = random.Random(args.seed)
    rng.shuffle(ids)
    chunks = [ids[i:i + args.size] for i in range(0, len(ids), args.size)]

    manifest = {"batch_size": args.size, "seed": args.seed, "batches": dict(preserved)}
    for n, ids_in_batch in enumerate(chunks, start):
        name = batch_name(n)
        ids_sorted = sorted(ids_in_batch)
        manifest["batches"][name] = ids_sorted
        payload = [{"row_id": i, "text": text_by_id[i]} for i in ids_sorted]
        prompt = PREAMBLE + json.dumps(payload, ensure_ascii=False, indent=1)
        (BATCH_DIR / f"{name}.prompt.txt").write_text(prompt, encoding="utf-8")

    MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=1), encoding="utf-8")

    # Remove files for batches no longer in the manifest - stale prompts/replies
    # from an earlier layout would collide with re-used batch numbers.
    keep = set(manifest["batches"])
    for p in list(BATCH_DIR.glob("batch_*")):
        if p.name.split(".")[0] not in keep:
            p.unlink()
            print(f"  removed stale {p.name}")

    if preserved:
        print(f"Preserved {len(preserved)} completed batch(es) "
              f"({len(done)} rows already answered)")
    print(f"Wrote {len(chunks)} new prompt(s) to {BATCH_DIR}")
    print(f"  {len(ids)} rows to label, batch size {args.size}, seed {args.seed}")
    print("\nNext:")
    print("  1. Paste each batch_NN.prompt.txt into the LLM (one call per batch).")
    print(f"  2. Save each reply as {BATCH_DIR.name}\\batch_NN.json")
    print("  3. python scripts\\llm_batches.py status")
    print("  4. python scripts\\llm_batches.py merge")


def read_batch(name: str, expected: list[int]) -> tuple[list[dict], list[str]]:
    """Parse one batch reply and check its ids against the manifest."""
    path = BATCH_DIR / f"{name}.json"
    problems = []
    if not path.exists():
        return [], [f"{name}: reply not found ({path.name})"]

    try:
        records = load_annotations(path)
    except SystemExit as exc:
        return [], [f"{name}: unreadable - {exc}"]

    got = [r["row_id"] for r in records]
    if len(set(got)) != len(got):
        dupes = sorted({i for i in got if got.count(i) > 1})
        problems.append(f"{name}: duplicate ids {dupes[:10]}")
    missing = sorted(set(expected) - set(got))
    extra = sorted(set(got) - set(expected))
    if missing:
        problems.append(f"{name}: missing ids {missing[:10]} ({len(missing)} of {len(expected)})")
    if extra:
        problems.append(f"{name}: unexpected ids {extra[:10]} ({len(extra)})")
    if len(records) != len(expected):
        problems.append(f"{name}: {len(records)} records for {len(expected)} rows")
    return records, problems


def cmd_status(args: argparse.Namespace) -> None:
    manifest = load_manifest()
    ok = missing = bad = 0
    for name, expected in manifest["batches"].items():
        path = BATCH_DIR / f"{name}.json"
        if not path.exists():
            missing += 1
            print(f"  [ ] {name}  {len(expected)} rows  (no reply)")
            continue
        records, problems = read_batch(name, expected)
        if problems:
            bad += 1
            print(f"  [!] {name}  {'; '.join(p.split(': ', 1)[1] for p in problems)}")
        else:
            ok += 1
            print(f"  [x] {name}  {len(records)} rows  ok")
    print(f"\n{ok} ok, {bad} failing, {missing} not returned "
          f"(of {len(manifest['batches'])} batches)")


def cmd_merge(args: argparse.Namespace) -> None:
    manifest = load_manifest()
    valid_labels, threshold = load_scheme()

    all_records: list[dict] = []
    problems: list[str] = []
    for name, expected in manifest["batches"].items():
        if not (BATCH_DIR / f"{name}.json").exists():
            problems.append(f"{name}: reply missing - run status for details")
            continue
        records, batch_problems = read_batch(name, expected)
        problems.extend(batch_problems)
        all_records.extend(records)

    if problems:
        print("Refusing to merge - these batches did not validate:")
        for p in problems:
            print(f"  {p}")
        print("\nFix or re-run the listed batches, then merge again. Run status for detail.")
        raise SystemExit(1)

    # Persist the combined output for audit.
    combined = BATCH_DIR / "annotations.json"
    combined.write_text(json.dumps(all_records, ensure_ascii=False, indent=1), encoding="utf-8")

    df = pd.read_csv(args.sample, dtype=str, keep_default_na=False)
    df["row_id"] = df["row_id"].astype(str)
    backfill_gold(df, args.scored, valid_labels)

    stats = apply_labels(df, all_records, valid_labels, args.overwrite)
    print(f"\nMerged {stats['merged']} labels | "
          f"{stats['blanked_artifact']} artifact rows blanked | "
          f"{stats['skipped']} skipped")

    filled = df[df["label_relevance"].isin(valid_labels)]
    print("\nlabel_relevance distribution:")
    print(filled["label_relevance"].value_counts().reindex(
        ["none", "weak", "direct", "core"]).fillna(0).astype(int).to_string())

    sanity_check(df, valid_labels)

    out = args.out or args.sample
    df.to_csv(out, index=False, encoding="utf-8-sig", quoting=1)
    print(f"\nWrote {len(df)} rows to {out}")


def main() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)

    p_make = sub.add_parser("make", help="write per-batch prompt files")
    p_make.add_argument("--sample", type=Path, default=DEFAULT_SAMPLE)
    p_make.add_argument("--size", type=int, default=15, help="rows per batch (default 15)")
    p_make.add_argument("--seed", type=int, default=42)
    p_make.add_argument("--all", action="store_true", help="re-batch even labelled rows")
    p_make.set_defaults(func=cmd_make)

    p_status = sub.add_parser("status", help="check returned batches")
    p_status.set_defaults(func=cmd_status)

    p_merge = sub.add_parser("merge", help="validate and merge returned batches")
    p_merge.add_argument("--sample", type=Path, default=DEFAULT_SAMPLE)
    p_merge.add_argument("--scored", type=Path, default=DEFAULT_SCORED)
    p_merge.add_argument("--out", type=Path, default=None, help="defaults to --sample")
    p_merge.add_argument("--overwrite", action="store_true")
    p_merge.set_defaults(func=cmd_merge)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
