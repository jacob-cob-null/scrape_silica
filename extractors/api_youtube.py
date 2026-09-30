import os
import json
import time
from googleapiclient.discovery import build
from core.config import BRONZE_AUTO_DIR, ALL_KEYWORDS, TIER_1_BRAND, TIER_2_ANCHORS

YOUTUBE_SAFE_KEYWORDS = list(TIER_1_BRAND) + list(TIER_2_ANCHORS)

def run():
    print("Running YouTube API Extractor...")
    api_key = os.getenv('YOUTUBE_API_KEY')

    if not api_key or not api_key.strip():
        print("YouTube API key missing in .env. Skipping real extraction.")
        return

    try:
        youtube = build('youtube', 'v3', developerKey=api_key)
        
        for keyword in YOUTUBE_SAFE_KEYWORDS:
            print(f"Searching YouTube for: {keyword}")
            # Search for videos
            search_response = youtube.search().list(
                q=keyword,
                part='id,snippet',
                maxResults=50,
                type='video'
            ).execute()
            
            for search_result in search_response.get('items', []):
                video_id = search_result['id']['videoId']
                video_title = search_result['snippet']['title']
                video_desc = search_result['snippet']['description']
                
                # Save video context
                video_record = {
                    "platform": "youtube_video",
                    "tier": "strict",
                    "source_id": f"yt_vid_{video_id}",
                    "raw_content": f"{video_title}\n{video_desc}",
                    "timestamp_utc": int(time.time())
                }
                
                v_filename = BRONZE_AUTO_DIR / f"youtube_vid_{video_id}.json"
                with open(v_filename, 'w', encoding='utf-8') as f:
                    json.dump(video_record, f)

                # Fetch top comments for this video
                try:
                    comments_response = youtube.commentThreads().list(
                        part='snippet',
                        videoId=video_id,
                        maxResults=100,
                        textFormat='plainText'
                    ).execute()
                    
                    for comment_thread in comments_response.get('items', []):
                        comment = comment_thread['snippet']['topLevelComment']['snippet']
                        comment_id = comment_thread['id']
                        
                        c_record = {
                            "platform": "youtube_comment",
                            "tier": "strict",
                            "source_id": f"yt_com_{comment_id}",
                            "raw_content": comment['textDisplay'],
                            "timestamp_utc": int(time.time())
                        }
                        
                        c_filename = BRONZE_AUTO_DIR / f"youtube_com_{comment_id}.json"
                        with open(c_filename, 'w', encoding='utf-8') as f:
                            json.dump(c_record, f)
                except Exception:
                    # Video might have comments disabled
                    pass
                
    except Exception as e:
        print(f"Error during YouTube extraction: {e}")
        
    print("YouTube extraction complete.")
