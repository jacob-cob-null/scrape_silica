import httpx
import time
from core.database import get_connection

def score_text(text: str, model="laya") -> tuple[int, int]:
    prompt = f"""You are an intelligence analyst evaluating a dataset. 
Read the following text. How relevant is it to geopolitics, semiconductors, economic zones, infrastructure development, US/China relations, or local community displacement in the Philippines? 

Respond strictly with valid JSON containing two keys:
- "decision_rating": an integer from 0 to 100 (0 = completely irrelevant, 100 = highly relevant).
- "confidence": an integer from 0 to 100 indicating your confidence in this rating.

Text: "{text[:1500]}"
"""

    try:
        response = httpx.post("http://localhost:11434/api/generate", json={
            "model": model,
            "prompt": prompt,
            "stream": False,
            "format": "json",
            "options": {
                "temperature": 0.0 
            }
        }, timeout=15.0)
        
        if response.status_code == 200:
            import json
            result_str = response.json().get('response', '{}').strip()
            data = json.loads(result_str)
            decision = int(data.get("decision_rating", 100))
            confidence = int(data.get("confidence", 100))
            return min(max(decision, 0), 100), min(max(confidence, 0), 100)
    except Exception:
        pass 
    return 100, 100 # Default if error

def run(limit=None):
    print("Running AI Semantic Scorer via Local Ollama...")
    conn = get_connection()
    
    # Get unprocessed records
    query = "SELECT content_hash, cleaned_content FROM silver_records WHERE decision_rating IS NULL"
    if limit:
        query += f" LIMIT {limit}"
        
    unprocessed = conn.execute(query).fetchall()
    
    if not unprocessed:
        print("No new records to filter.")
        return
        
    print(f"Found {len(unprocessed)} records to classify. Pushing to RTX 3060...")
    
    processed_count = 0
    start_time = time.time()
    
    for row in unprocessed:
        content_hash, text = row
        
        decision, confidence = score_text(text, model="laya") 
        
        conn.execute("UPDATE silver_records SET decision_rating = ?, confidence = ? WHERE content_hash = ?", (decision, confidence, content_hash))
        processed_count += 1
            
        if processed_count % 100 == 0:
            elapsed = time.time() - start_time
            print(f"Scored {processed_count}/{len(unprocessed)} | Speed: {processed_count/elapsed:.2f} records/sec")
            
    print(f"AI Scoring complete for {processed_count} records.")
