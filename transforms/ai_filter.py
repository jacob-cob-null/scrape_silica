import json
import time
from pathlib import Path
from core.database import get_connection

REPO = Path(__file__).resolve().parent.parent
CRITERIA_FILE = REPO / "eval" / "criteria.json"


def load_relevance_question() -> dict:
    if not CRITERIA_FILE.exists():
        raise FileNotFoundError(f"Missing criteria file: {CRITERIA_FILE}")
    with open(CRITERIA_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data["questions"]["relevance"]


def load_router():
    try:
        from laya import Router
    except ImportError as exc:
        raise SystemExit(
            "The 'laya' package is not installed. Run: "
            "pip install -r requirements-laya.txt."
        ) from exc
    return Router()


def score_text(text: str, router=None, question=None) -> tuple[int, int]:
    """Score a single text string with Laya, returning (decision_rating, confidence)."""
    if router is None:
        router = load_router()
    if question is None:
        question = load_relevance_question()

    try:
        answer = router.predict(text, {"relevance": question})["answers"]["relevance"]
        if question.get("type") == "noul":
            decision = int(round(100 * float(answer.get("noul", 0.0))))
        else:
            probs = answer.get("probabilities") or {}
            decision = int(round(100 * (probs.get("direct", 0.0) + probs.get("core", 0.0))))
        confidence = int(round(100 * float(answer.get("confidence", 0.0))))
        return min(max(decision, 0), 100), min(max(confidence, 0), 100)
    except Exception:
        return 0, 0


def run(limit=None, batch_size=32):
    print("Running AI Semantic Scorer via native LAYA (noul)...")
    question = load_relevance_question()
    router = load_router()
    conn = get_connection()

    try:
        # Get unprocessed records
        query = "SELECT content_hash, cleaned_content FROM silver_records WHERE decision_rating IS NULL"
        if limit:
            query += f" LIMIT {limit}"

        unprocessed = conn.execute(query).fetchall()

        if not unprocessed:
            print("No new records to filter.")
            return

        total = len(unprocessed)
        print(f"Found {total:,} records to classify. Scoring on GPU via LAYA (batch_size={batch_size})...")

        processed_count = 0
        start_time = time.time()
        is_noul = question.get("type") == "noul"

        for start in range(0, total, batch_size):
            chunk = unprocessed[start:start + batch_size]
            hashes = [row[0] for row in chunk]
            texts = [row[1] or "" for row in chunk]

            requests = [{"state": t, "questions": {"relevance": question}} for t in texts]
            updates = []

            try:
                results = router.predict_batch(requests, batch_size=len(chunk))
                for h, res in zip(hashes, results):
                    ans = res["answers"]["relevance"]
                    if is_noul:
                        closeness = float(ans.get("noul", 0.0))
                    else:
                        probs = ans.get("probabilities") or {}
                        closeness = probs.get("direct", 0.0) + probs.get("core", 0.0)
                    rating = int(round(100 * closeness))
                    conf = int(round(100 * float(ans.get("confidence", 0.0))))
                    updates.append((rating, conf, h))
            except Exception as exc:
                print(f"  Batch [{start}:{start+len(chunk)}] failed ({exc}); falling back to sequential...")
                for h, t in zip(hashes, texts):
                    d, c = score_text(t, router=router, question=question)
                    updates.append((d, c, h))

            conn.executemany(
                "UPDATE silver_records SET decision_rating = ?, confidence = ? WHERE content_hash = ?",
                updates
            )
            processed_count += len(chunk)

            if processed_count % (batch_size * 4) == 0 or processed_count == total:
                elapsed = time.time() - start_time
                speed = processed_count / elapsed if elapsed > 0 else 0.0
                print(f"  Scored {processed_count:,}/{total:,} | Speed: {speed:.1f} rec/s")

        elapsed = time.time() - start_time
        print(f"AI Scoring complete: {processed_count:,} records in {elapsed:.1f}s.")
    finally:
        conn.close()

