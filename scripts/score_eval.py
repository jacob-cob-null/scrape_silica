"""
score_eval.py

Scores eval/laya_sample.csv with Laya and fills the two GOLD fields:

    decision_rating   0-100 = round(100 * P(anchor closeness))
    confidence        0-100 = 100 * Laya's confidence signal

Then, if the ground-truth column label_relevance is filled, reports precision /
recall / F1, ECE, and a threshold sweep so the operating point is chosen from
data rather than hardcoded.

Verified answer shapes (laya 0.4.11):
    noul:
        answers.relevance = {
            "type": "noul",
            "noul": 0.8629,       # P(true) -> closeness to anchor
            "confidence": 0.8629,
        }
    choice:
        answers.relevance = {
            "type": "choice",
            "choice": "core",
            "probabilities": {"none": .., "weak": .., "direct": .., "core": ..},
            "confidence": 0.1778,
        }

Usage:
    $env:USE_TF="0"; $env:PYTHONPATH="."; python scripts\score_eval.py
    $env:USE_TF="0"; $env:PYTHONPATH="."; python scripts\score_eval.py --limit 20
    $env:USE_TF="0"; $env:PYTHONPATH="."; python scripts\score_eval.py --metrics-only
"""

import argparse
import json
import sys
from pathlib import Path

import pandas as pd

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

REPO = Path(__file__).resolve().parent.parent
IN_FILE = REPO / "eval" / "laya_sample.csv"
OUT_FILE = REPO / "eval" / "laya_sample_scored.csv"
CRITERIA_FILE = REPO / "eval" / "criteria.json"

RELEVANCE_VALUES = {"none", "weak", "direct", "core"}
DEFAULT_POSITIVES = {"direct", "core"}
DEFAULT_THRESHOLD = 50


def load_scheme() -> tuple[dict, set[str], float]:
    if not CRITERIA_FILE.exists():
        raise SystemExit(f"Missing {CRITERIA_FILE}")
    data = json.loads(CRITERIA_FILE.read_text(encoding="utf-8"))
    question = data["questions"]["relevance"]
    positives = set(data.get("positive_labels", DEFAULT_POSITIVES))
    threshold = float(data.get("threshold", DEFAULT_THRESHOLD))
    return question, positives, threshold


def load_router():
    try:
        from laya import Router
    except ImportError as exc:  # pragma: no cover
        raise SystemExit(
            "The 'laya' package is not installed. Run: "
            "pip install -r requirements-laya.txt."
        ) from exc
    return Router(preload=True)


def score(df: pd.DataFrame, question: dict, positives: set[str], batch_size: int = 32) -> pd.DataFrame:
    router = load_router()
    ratings, confidences = [], []
    is_noul = question.get("type") == "noul"
    texts = df["content"].fillna("").tolist()
    total = len(texts)

    for start in range(0, total, batch_size):
        chunk = texts[start:start + batch_size]
        requests = [{"state": t, "questions": {"relevance": question}} for t in chunk]
        try:
            results = router.predict_batch(requests, batch_size=batch_size)
            for res in results:
                ans = res["answers"]["relevance"]
                if is_noul:
                    closeness = float(ans.get("noul", 0.0))
                    ratings.append(int(round(100 * closeness)))
                else:
                    probs = ans.get("probabilities") or {}
                    positive_mass = sum(probs.get(k, 0.0) for k in positives)
                    ratings.append(int(round(100 * positive_mass)))
                confidences.append(int(round(100 * float(ans.get("confidence", 0.0)))))
        except Exception as exc:
            print(f"  Batch [{start}:{start+len(chunk)}] failed: {exc}; fallback to sequential")
            for t in chunk:
                try:
                    ans = router.predict(t, {"relevance": question})["answers"]["relevance"]
                    if is_noul:
                        ratings.append(int(round(100 * float(ans.get("noul", 0.0)))))
                    else:
                        probs = ans.get("probabilities") or {}
                        positive_mass = sum(probs.get(k, 0.0) for k in positives)
                        ratings.append(int(round(100 * positive_mass)))
                    confidences.append(int(round(100 * float(ans.get("confidence", 0.0)))))
                except Exception as inner_exc:
                    print(f"    Item scoring failed: {inner_exc}")
                    ratings.append("")
                    confidences.append("")

        print(f"  scored {min(start + len(chunk), total)}/{total}")

    df = df.copy()
    df["decision_rating"] = ratings
    df["confidence"] = confidences
    return df


def filter_labeled(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.Series]:
    labeled = df[df["label_relevance"].isin(RELEVANCE_VALUES)].copy()
    ratings = pd.to_numeric(labeled["decision_rating"], errors="coerce")
    labeled = labeled[ratings.notna()].copy()
    return labeled, pd.to_numeric(labeled["decision_rating"], errors="coerce")


def compute_metrics(df: pd.DataFrame, positives: set[str], threshold: float) -> None:
    labeled, ratings = filter_labeled(df)
    if labeled.empty:
        print("\nNo filled label_relevance values yet - skipping metrics.")
        return

    labeled["truth"] = labeled["label_relevance"].isin(positives).astype(int)

    print(f"\nLabeled rows: {len(labeled)} | positive: {int(labeled['truth'].sum())} "
          f"(+{', '.join(sorted(positives))})")

    print("\nThreshold sweep (decision_rating is 0-100):")
    rows = []
    for t in [40, 50, 60, 70, 75, 80]:
        preds = (ratings >= t).astype(int)
        tp = int(((preds == 1) & (labeled["truth"] == 1)).sum())
        fp = int(((preds == 1) & (labeled["truth"] == 0)).sum())
        fn = int(((preds == 0) & (labeled["truth"] == 1)).sum())
        precision = tp / (tp + fp) if (tp + fp) else 0.0
        recall = tp / (tp + fn) if (tp + fn) else 0.0
        rows.append({
            "threshold": t,
            "kept": int(preds.sum()),
            "precision": round(precision, 3),
            "recall": round(recall, 3),
            "f1": round(2 * precision * recall / (precision + recall), 3)
            if (precision + recall) else 0.0,
        })
    print(pd.DataFrame(rows).to_string(index=False))

    preds = (ratings >= threshold).astype(int)
    tp = int(((preds == 1) & (labeled["truth"] == 1)).sum())
    fp = int(((preds == 1) & (labeled["truth"] == 0)).sum())
    fn = int(((preds == 0) & (labeled["truth"] == 1)).sum())
    tn = int(((preds == 0) & (labeled["truth"] == 0)).sum())
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0

    print(f"\nAt the configured threshold ({threshold:.0f}): TP={tp} FP={fp} FN={fn} TN={tn}")
    print(f"Precision {precision:.3f} | Recall {recall:.3f} | "
          f"F1 {2 * precision * recall / (precision + recall):.3f}"
          if (precision + recall) else "Precision 0 | Recall 0 | F1 0")

    # ECE over 10 bins, treating decision_rating/100 as the predicted probability.
    prob = ratings / 100.0
    bins = pd.cut(prob, bins=[i / 10 for i in range(11)], include_lowest=True)
    ece = 0.0
    for _, idx in labeled.groupby(bins, observed=True).groups.items():
        subset = labeled.loc[idx]
        bucket_prob = (pd.to_numeric(subset["decision_rating"]) / 100.0).mean()
        accuracy = subset["truth"].mean()
        ece += abs(bucket_prob - accuracy) * len(subset) / len(labeled)
    print(f"ECE (10 bins): {ece:.3f}")


def summarize(df: pd.DataFrame, threshold: float) -> None:
    ratings = pd.to_numeric(df["decision_rating"], errors="coerce")
    print("\ndecision_rating distribution:")
    bins = pd.cut(ratings, [0, 20, 40, 60, 80, 100], include_lowest=True)
    print(df.groupby(bins, observed=False).size().to_string())
    n = int(ratings.notna().sum())
    print(f"\nrated: {n}/{len(df)} rows | >= {threshold:.0f}: "
          f"{int((ratings >= threshold).sum())} "
          f"({(ratings >= threshold).mean() * 100:.1f}%)")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--metrics-only", action="store_true")
    parser.add_argument("--threshold", type=float, default=None)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--input", type=Path, default=None,
                        help="score/metrics source (default: eval/laya_sample.csv; "
                             "with --metrics-only, falls back to the scored file)")
    args = parser.parse_args()

    question, positives, configured_threshold = load_scheme()
    threshold = args.threshold if args.threshold is not None else configured_threshold

    if args.input is not None:
        source = args.input
    elif args.metrics_only and OUT_FILE.exists():
        source = OUT_FILE
    else:
        source = IN_FILE
    if not source.exists():
        raise SystemExit(f"Sample file not found: {source}")

    df = pd.read_csv(source, dtype=str, keep_default_na=False)

    if not args.metrics_only:
        subset = df if args.limit is None else df.head(args.limit)
        subset = score(subset, question, positives)
        subset.to_csv(OUT_FILE, index=False, encoding="utf-8-sig", quoting=1)
        print(f"\nWrote scored sample to {OUT_FILE} ({len(subset)} rows)")
        summarize(subset, threshold)
        df = subset

    compute_metrics(df, positives, threshold)


if __name__ == "__main__":
    main()
