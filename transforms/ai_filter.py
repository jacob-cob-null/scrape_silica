import httpx
import time
from core.database import get_connection

def score_text(text: str, model="laya") -> int:
    prompt = f"""You are an intelligence analyst evaluating a dataset. 
Read the following text. How relevant is it to geopolitics, semiconductors, economic zones, infrastructure development, US/China relations, or local community displacement in the Philippines? 

Score its relevance from 0 to 100, where 0 is completely irrelevant and 100 is highly relevant.
Answer strictly with only the integer number and nothing else.

Text: "{text[:1500]}"
Score:"""

    try:
        response = httpx.post("http://localhost:11434/api/generate", json={
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "num_predict": 4, # Only need a few tokens for a number like "100"
                "temperature": 0.0 
            }
        }, timeout=15.0)
        
        if response.status_code == 200:
            result_str = response.json().get('response', '').strip()
            # Extract just the digits in case it outputs something like "85%" or "Score: 85"
            digits = ''.join(filter(str.isdigit, result_str))
            if digits:
                score = int(digits)
                return min(max(score, 0), 100) # Clamp between 0 and 100
    except Exception as e:
        pass 
    return 100 # Default to 100 (keep) if error

def run():
    print("Running AI Semantic Scorer via Local Ollama...")
    conn = get_connection()
    
    # We add a relevance_score integer column. We use TRY/EXCEPT so it doesn't crash if it already exists.
    try:
        conn.execute("ALTER TABLE silver_records ADD COLUMN relevance_score INTEGER")
    except Exception:
        pass
        
    # Get unprocessed records
    unprocessed = conn.execute("SELECT content_hash, cleaned_content FROM silver_records WHERE relevance_score IS NULL").fetchall()
    
    if not unprocessed:
        print("No new records to filter.")
        return
        
    print(f"Found {len(unprocessed)} records to classify. Pushing to RTX 3060...")
    
    processed_count = 0
    start_time = time.time()
    
    for row in unprocessed:
        content_hash, text = row
        
        score = score_text(text, model="laya") 
        
        conn.execute("UPDATE silver_records SET relevance_score = ? WHERE content_hash = ?", (score, content_hash))
        processed_count += 1
            
        if processed_count % 100 == 0:
            elapsed = time.time() - start_time
            print(f"Scored {processed_count}/{len(unprocessed)} | Speed: {processed_count/elapsed:.2f} records/sec")
            
    print(f"AI Scoring complete for {processed_count} records.")
