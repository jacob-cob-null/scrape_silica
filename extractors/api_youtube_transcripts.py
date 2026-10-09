import json
import time
from pathlib import Path
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api.formatters import TextFormatter
from core.config import BRONZE_AUTO_DIR

def run():
    print("Running YouTube Transcript Extractor...")
    
    # 1. Find all YouTube video files we've scraped
    vid_files = list(BRONZE_AUTO_DIR.glob("youtube_vid_*.json"))
    if not vid_files:
        print("No YouTube video files found. Skipping.")
        return
        
    vid_ids = []
    for f in vid_files:
        try:
            with open(f, 'r', encoding='utf-8') as fh:
                data = json.load(fh)
                if "source_id" in data and data["source_id"].startswith("yt_vid_"):
                    vid_id = data["source_id"].split("yt_vid_")[1]
                    vid_ids.append(vid_id)
        except Exception:
            pass
            
    # Remove duplicates
    vid_ids = list(set(vid_ids))
    print(f"Found {len(vid_ids)} unique YouTube videos to check for transcripts.")
    
    # 2. Extract transcripts
    formatter = TextFormatter()
    success_count = 0
    
    for i, vid_id in enumerate(vid_ids, 1):
        # Skip if we already have the transcript
        out_file = BRONZE_AUTO_DIR / f"youtube_transcript_{vid_id}.json"
        if out_file.exists():
            continue
            
        try:
            print(f"[{i}/{len(vid_ids)}] Fetching transcript for video {vid_id}...")
            # Try to fetch transcript (auto-generated or manual)
            try:
                transcript_list = YouTubeTranscriptApi().list(vid_id)
                # Just get the first available english one or any transcript
                try:
                    transcript = transcript_list.find_transcript(['en', 'en-US', 'en-GB'])
                except Exception:
                    transcript = list(transcript_list)[0]
                    
                transcript_data = transcript.fetch()
            except Exception as e:
                print(f"  -> No transcript available (or error): {e}")
                continue
                
            text_content = formatter.format_transcript(transcript_data)
            
            if not text_content.strip():
                continue
                
            record = {
                "platform": "youtube_transcript",
                "tier": "strict",
                "source_id": f"yt_transcript_{vid_id}",
                "raw_content": text_content[:50000],  # Cap at 50k chars
                "timestamp_utc": int(time.time()),
                "url": f"https://www.youtube.com/watch?v={vid_id}"
            }
            
            with open(out_file, 'w', encoding='utf-8') as fh:
                json.dump(record, fh)
                
            success_count += 1
            time.sleep(1)  # Be nice to the API
            
        except Exception as e:
            # Often videos just don't have transcripts, which is normal
            print(f"  -> No transcript available (or error): {e}")
            
    print(f"Finished YouTube Transcripts. Saved {success_count} new transcripts.")

if __name__ == "__main__":
    run()
