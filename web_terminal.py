#!/usr/bin/env python3
"""
Web Terminal Backend for YouTube Automation
FastAPI application with WebSocket support for interactive terminal
"""

import asyncio
import json
import datetime
import os
import sys
from pathlib import Path
from typing import Optional, Dict, Any

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import uvicorn

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from youtube_metadata import (
    list_available_accounts, authenticate_account, get_account_info,
    get_authenticated_service, get_my_unscheduled_private_video_ids,
    get_video_transcript, is_transcript_duplicate, generate_metadata_with_gemini,
    update_and_schedule_video, save_video_data, view_processed_data_summary,
    cleanup_old_data, get_account_id_from_service, QuotaExceededError
)

# Optional import for promotion features
try:
    from promotion_logic import PromotionEngine
    PROMOTION_AVAILABLE = True
except ImportError:
    PROMOTION_AVAILABLE = False
    print("Warning: promotion_logic not available (missing dependencies)")

app = FastAPI(title="YouTube Automation Terminal")

# Mount static files
web_terminal_dir = Path(__file__).parent / "web_terminal"
app.mount("/static", StaticFiles(directory=str(web_terminal_dir)), name="static")


class TerminalSession:
    """Manages a terminal session state"""
    def __init__(self, websocket: WebSocket):
        self.websocket = websocket
        self.selected_account: Optional[str] = None
        self.youtube_service = None
        self.channel_id: Optional[str] = None
        self.processing = False
        
    async def send(self, message_type: str, **kwargs):
        """Send message to client"""
        await self.websocket.send_json({
            "type": message_type,
            **kwargs
        })
    
    async def output(self, message: str, className: str = "text-white"):
        """Send output message"""
        await self.send("output", message=message, className=className)
    
    async def error(self, message: str):
        """Send error message"""
        await self.output(f"❌ {message}", "text-error")
    
    async def success(self, message: str):
        """Send success message"""
        await self.output(f"✓ {message}", "text-success")
    
    async def info(self, message: str):
        """Send info message"""
        await self.output(f"ℹ {message}", "text-info")
    
    async def warning(self, message: str):
        """Send warning message"""
        await self.output(f"⚠ {message}", "text-warning")


@app.get("/")
async def get_index():
    """Serve the terminal HTML page"""
    return FileResponse(str(web_terminal_dir / "index.html"))


# Global state for GUI (in production, use proper session management)
LAST_ACCOUNT_FILE = Path(__file__).parent / ".last_account.json"

def load_last_account():
    """Load last selected account from file"""
    try:
        if LAST_ACCOUNT_FILE.exists():
            with open(LAST_ACCOUNT_FILE, 'r') as f:
                data = json.load(f)
                return data.get("account_name"), data.get("channel_id")
    except:
        pass
    return None, None

def save_last_account(account_name, channel_id):
    """Save selected account for next session"""
    try:
        with open(LAST_ACCOUNT_FILE, 'w') as f:
            json.dump({"account_name": account_name, "channel_id": channel_id}, f)
    except:
        pass

# Load last account on startup
_last_account, _last_channel = load_last_account()

_gui_state = {
    "selected_account": _last_account,
    "youtube_service": None,
    "channel_id": _last_channel
}


@app.get("/api/accounts")
async def get_accounts():
    """Get list of all accounts"""
    try:
        accounts = list_available_accounts()
        accounts_list = []
        
        for account in accounts:
            try:
                from youtube_metadata import get_account_token_file, TOKEN_PICKLE_FILE
                from google.auth.transport.requests import Request
                import pickle
                
                if account == "default":
                    token_file = TOKEN_PICKLE_FILE
                else:
                    token_file = get_account_token_file(account)
                
                with open(token_file, "rb") as f:
                    creds = pickle.load(f)
                    
                    # Refresh expired credentials
                    if creds and creds.expired and creds.refresh_token:
                        try:
                            creds.refresh(Request())
                            # Save refreshed token
                            with open(token_file, "wb") as tf:
                                pickle.dump(creds, tf)
                        except Exception as refresh_error:
                            print(f"Could not refresh token for {account}: {refresh_error}")
                    
                    if creds:
                        try:
                            channel_id, channel_title = get_account_info(creds)
                        except:
                            channel_id = account
                            channel_title = account.capitalize()
                        
                        accounts_list.append({
                            "name": account,
                            "channel_id": channel_id,
                            "channel_title": channel_title,
                            "selected": account == _gui_state["selected_account"]
                        })
            except Exception as e:
                print(f"Error loading account {account}: {e}")
                # Still add the account even if we can't get full info
                accounts_list.append({
                    "name": account,
                    "channel_id": account,
                    "channel_title": account.capitalize(),
                    "selected": account == _gui_state["selected_account"]
                })
        
        return {"success": True, "accounts": accounts_list}
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.post("/api/add-account")
async def add_account(data: dict):
    """Add a new account"""
    try:
        account_name = data.get("account_name", "").strip()
        
        if not account_name:
            return {"success": False, "error": "Account name required"}
        
        import re
        if not re.match(r'^[a-zA-Z0-9_-]+$', account_name):
            return {"success": False, "error": "Invalid account name"}
        
        if account_name in list_available_accounts():
            return {"success": False, "error": f"Account '{account_name}' already exists"}
        
        # Run authentication
        loop = asyncio.get_event_loop()
        creds = await loop.run_in_executor(None, authenticate_account, account_name)
        
        if creds:
            channel_id, channel_title = get_account_info(creds)
            return {
                "success": True,
                "account": {
                    "name": account_name,
                    "channel_id": channel_id,
                    "channel_title": channel_title
                }
            }
        else:
            return {"success": False, "error": "Authentication failed"}
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.post("/api/select-account")
async def select_account(data: dict):
    """Select an account"""
    try:
        account_name = data.get("account", "").strip()
        
        if account_name not in list_available_accounts():
            return {"success": False, "error": "Account not found"}
        
        loop = asyncio.get_event_loop()
        creds = await loop.run_in_executor(None, authenticate_account, account_name)
        
        if creds:
            from googleapiclient.discovery import build
            service = build("youtube", "v3", credentials=creds)
            channel_id = get_account_id_from_service(service)
            
            _gui_state["selected_account"] = account_name
            _gui_state["youtube_service"] = service
            _gui_state["channel_id"] = channel_id
            
            # Save for next session
            save_last_account(account_name, channel_id)
            
            return {"success": True, "account": account_name}
        else:
            return {"success": False, "error": "Failed to authenticate"}
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.post("/api/run-automation")
async def run_automation_api(data: dict):
    """Run automation with settings"""
    try:
        account_name = data.get("account")
        
        # Use saved account if none specified
        if not account_name:
            account_name = _gui_state.get("selected_account")
        
        if not account_name:
            return {"success": False, "error": "No account specified. Please select an account first."}
        
        # Reuse existing service if available for same account
        if (_gui_state.get("youtube_service") and 
            _gui_state.get("selected_account") == account_name):
            service = _gui_state["youtube_service"]
            channel_id = _gui_state["channel_id"]
            creds = None  # Already have service
        else:
            # Authenticate and set up service
            loop = asyncio.get_event_loop()
            creds = await loop.run_in_executor(None, authenticate_account, account_name)
            
            if not creds:
                return {"success": False, "error": "Failed to authenticate account"}
            
            from googleapiclient.discovery import build
            service = build("youtube", "v3", credentials=creds)
            channel_id = get_account_id_from_service(service)
        
        # Update global state
        _gui_state["selected_account"] = account_name
        _gui_state["youtube_service"] = service
        _gui_state["channel_id"] = channel_id
        
        # Save for next session
        save_last_account(account_name, channel_id)
        
        # Extract settings
        start_date_str = data.get("start_date")
        videos_per_day = data.get("videos_per_day", 1)
        time_slots = data.get("time_slots", ["09:00"])
        
        # Start automation in background
        asyncio.create_task(run_automation_background(
            service, channel_id, start_date_str, videos_per_day, time_slots
        ))
        
        return {"success": True, "message": "Automation started"}
    except Exception as e:
        import traceback
        traceback.print_exc()
        return {"success": False, "error": str(e)}


async def run_automation_background(service, channel_id, start_date_str, videos_per_day, time_slots):
    """Run automation in background with progress updates"""
    try:
        import datetime
        import pytz
        import tzlocal
        
        # Parse start date
        start_date = datetime.datetime.strptime(start_date_str, "%Y-%m-%d").date()
        
        # Get timezone
        local_tz_name = tzlocal.get_localzone_name()
        system_tz = pytz.timezone(local_tz_name) if local_tz_name else pytz.utc
        
        # Fetch videos
        loop = asyncio.get_event_loop()
        videos = await loop.run_in_executor(None, get_my_unscheduled_private_video_ids, service)
        
        if not videos:
            print("No unscheduled private videos found")
            return
        
        print(f"Found {len(videos)} video(s) to process")
        
        current_date = start_date
        slot_index = 0
        scheduled_count = 0
        
        for idx, video_id in enumerate(videos):
            print(f"[{idx+1}/{len(videos)}] Processing {video_id}...")
            
            # Calculate publish time
            time_str = time_slots[slot_index % len(time_slots)]
            hour, minute = map(int, time_str.split(':'))
            
            publish_dt_naive = datetime.datetime.combine(current_date, datetime.time(hour, minute))
            publish_dt = system_tz.localize(publish_dt_naive)
            
            # Ensure it's in the future
            min_valid_dt = datetime.datetime.now(system_tz) + datetime.timedelta(minutes=30)
            while publish_dt < min_valid_dt:
                slot_index += 1
                if slot_index % len(time_slots) == 0:
                    current_date += datetime.timedelta(days=1)
                time_str = time_slots[slot_index % len(time_slots)]
                hour, minute = map(int, time_str.split(':'))
                publish_dt_naive = datetime.datetime.combine(current_date, datetime.time(hour, minute))
                publish_dt = system_tz.localize(publish_dt_naive)
            
            print(f"  Scheduled for: {publish_dt.strftime('%Y-%m-%d %H:%M')}")
            
            # Get transcript
            transcript = await loop.run_in_executor(None, get_video_transcript, service, video_id)
            if not transcript:
                print(f"  No transcript found. Skipping.")
                continue
            
            # Check duplicates
            is_dup = await loop.run_in_executor(None, is_transcript_duplicate, channel_id, transcript)
            if is_dup:
                print(f"  Duplicate content detected. Skipping.")
                continue
            
            # Generate metadata
            print(f"  Generating metadata...")
            metadata = await loop.run_in_executor(None, generate_metadata_with_gemini, transcript)
            
            if not metadata or "Placeholder" in metadata.get("title", "") or "Fallback" in metadata.get("title", ""):
                print(f"  Metadata generation failed. Skipping.")
                continue
            
            print(f"  Title: {metadata['title'][:60]}...")
            
            # Schedule video
            success = await loop.run_in_executor(
                None, 
                update_and_schedule_video, 
                service, 
                video_id, 
                metadata, 
                publish_dt
            )
            
            if success:
                scheduled_count += 1
                print(f"  Video scheduled!")
                await loop.run_in_executor(None, save_video_data, channel_id, video_id, transcript, metadata, publish_dt)
            else:
                print(f"  Failed to schedule video")
                await loop.run_in_executor(None, save_video_data, channel_id, video_id, transcript, metadata, None)
            
            # Move to next slot
            slot_index += 1
            if slot_index % len(time_slots) == 0 and slot_index >= videos_per_day * len(time_slots):
                current_date += datetime.timedelta(days=1)
        
        print(f"Automation complete! Scheduled {scheduled_count}/{len(videos)} videos")
        
    except Exception as e:
        print(f"Automation failed: {e}")
        import traceback
        traceback.print_exc()


@app.get("/api/stats")
async def get_stats(channel_id: str = ""):
    """Get statistics for an account"""
    try:
        if not channel_id:
            return {"success": False, "error": "Channel ID required"}
        
        # Load processed videos data
        from youtube_metadata import load_processed_videos_data
        data = load_processed_videos_data(channel_id)
        videos = data.get("videos", {})
        
        total_videos = len(videos)
        scheduled = sum(1 for v in videos.values() if v.get("status") == "scheduled")
        duplicates = sum(1 for v in videos.values() if "Duplicate" in v.get("metadata", {}).get("title", ""))
        
        return {
            "success": True,
            "stats": {
                "total_videos": total_videos,
                "scheduled": scheduled,
                "duplicates": duplicates
            }
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.get("/api/recent-videos")
async def get_recent_videos(channel_id: str = None, limit: int = 20):
    """Get recent videos from a YouTube channel for promotion selection"""
    try:
        if not channel_id:
            return {"success": False, "error": "Channel ID required"}
        
        from googleapiclient.discovery import build
        from dotenv import load_dotenv
        from datetime import datetime
        import pytz
        
        load_dotenv()
        
        api_key = os.getenv("YOUTUBE_API_KEY")
        if not api_key:
            return {"success": False, "error": "YouTube API key not configured"}
        
        youtube = build('youtube', 'v3', developerKey=api_key)
        india_tz = pytz.timezone('Asia/Kolkata')
        
        # Get recent videos from channel
        request = youtube.search().list(
            part="snippet",
            channelId=channel_id,
            order="date",
            maxResults=limit,
            type="video"
        )
        response = request.execute()
        
        videos = []
        for item in response.get('items', []):
            video_id = item['id']['videoId']
            snippet = item['snippet']
            
            # Format date
            published_at = snippet['publishedAt']
            video_date = datetime.fromisoformat(published_at.replace('Z', '+00:00'))
            video_date = video_date.astimezone(india_tz)
            
            videos.append({
                "id": video_id,
                "title": snippet['title'],
                "thumbnail": snippet['thumbnails']['default']['url'],
                "published": video_date.strftime("%d %b %Y, %I:%M %p"),
                "url": f"https://youtu.be/{video_id}"
            })
        
        return {"success": True, "videos": videos}
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return {"success": False, "error": str(e)}


@app.get("/api/last-video-date")
async def get_last_video_date(channel_id: str = None):
    """Get the date of the last scheduled or published video"""
    try:
        from datetime import datetime, timedelta
        import pytz
        
        india_tz = pytz.timezone('Asia/Kolkata')
        
        if not channel_id:
            # Return tomorrow by default if no channel
            tomorrow = datetime.now(india_tz) + timedelta(days=1)
            return {"success": True, "next_date": tomorrow.strftime("%Y-%m-%d")}
        
        # Try to get videos from YouTube API
        try:
            from googleapiclient.discovery import build
            from dotenv import load_dotenv
            load_dotenv()
            
            api_key = os.getenv("YOUTUBE_API_KEY")
            if not api_key:
                raise Exception("No API key")
            
            youtube = build('youtube', 'v3', developerKey=api_key)
            
            # Get latest videos from channel
            request = youtube.search().list(
                part="snippet",
                channelId=channel_id,
                order="date",
                maxResults=10,
                type="video"
            )
            response = request.execute()
            
            latest_date = None
            
            for item in response.get('items', []):
                published_at = item['snippet']['publishedAt']
                # Parse ISO format date
                video_date = datetime.fromisoformat(published_at.replace('Z', '+00:00'))
                video_date = video_date.astimezone(india_tz)
                
                if latest_date is None or video_date > latest_date:
                    latest_date = video_date
            
            if latest_date:
                # Next day after last video
                next_date = latest_date + timedelta(days=1)
                # Make sure it's at least tomorrow
                tomorrow = datetime.now(india_tz) + timedelta(days=1)
                if next_date < tomorrow:
                    next_date = tomorrow
                
                return {"success": True, "next_date": next_date.strftime("%Y-%m-%d"), "last_video": latest_date.strftime("%Y-%m-%d")}
            
        except Exception as e:
            print(f"Error fetching videos: {e}")
        
        # Fallback to tomorrow
        tomorrow = datetime.now(india_tz) + timedelta(days=1)
        return {"success": True, "next_date": tomorrow.strftime("%Y-%m-%d")}
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return {"success": False, "error": str(e)}


@app.post("/api/run-promotion")
async def run_promotion_api(data: dict):
    """Run promotion across platforms"""
    try:
        if not PROMOTION_AVAILABLE:
            return {"success": False, "error": "Promotion feature not available. Install dependencies: pip install google-generativeai instagrapi"}
        
        channel_id = data.get("channel_id")
        video_ids = data.get("video_ids", [])
        platforms = data.get("platforms", {})
        
        if not channel_id:
            return {"success": False, "error": "Channel ID required"}
        
        if not video_ids:
            return {"success": False, "error": "No videos selected"}
        
        if not platforms:
            return {"success": False, "error": "No platforms selected"}
        
        # Start promotion in background
        asyncio.create_task(run_promotion_background(channel_id, video_ids, platforms))
        
        return {"success": True, "message": f"Promotion started for {len(video_ids)} video(s)"}
    except Exception as e:
        import traceback
        traceback.print_exc()
        return {"success": False, "error": str(e)}


async def run_promotion_background(channel_id, video_ids, platforms):
    """Run promotion in background"""
    global promotion_log, promotion_status
    
    # Reset and initialize
    promotion_log = []
    promotion_status = {"running": True, "complete": False}
    
    try:
        from dotenv import load_dotenv
        load_dotenv()
        
        promotion_log.append(f"🚀 Starting promotion for {len(video_ids)} video(s)")
        promotion_log.append(f"📡 Platforms: {', '.join(platforms.keys())}")
        promotion_log.append("")
        
        # Skip old promotion engine, use direct API calls
        
        # Build account config for process_account method
        account_config = {
            "channel_id": channel_id,
            "youtube_api_key": os.getenv("YOUTUBE_API_KEY", ""),
            "telegram_targets": [],
            "twitter_targets": [],
            "instagram_targets": [],
            "video_ids": video_ids  # Pass specific video IDs instead of count
        }
        
        # Set up platform configurations
        if 'telegram' in platforms:
            telegram_config = platforms['telegram']
            account_config["telegram_targets"].append({
                "bot_token": telegram_config.get('bot_token'),
                "chat_id": telegram_config.get('channel_id')
            })
        
        if 'twitter' in platforms:
            # Load Twitter credentials from .env
            account_config["twitter_targets"].append({
                "api_key": os.getenv("X_API_KEY", ""),
                "api_secret": os.getenv("X_API_KEY_SECRET", ""),
                "access_token": os.getenv("X_ACCESS_TOKEN", ""),
                "access_secret": os.getenv("X_ACCESS_TOKEN_SECRET", ""),
                "bearer_token": os.getenv("X_BEARER_TOKEN", "")
            })
        
        if 'instagram' in platforms:
            # Load Instagram credentials from .env
            account_config["instagram_targets"].append({
                "username": os.getenv("INSTA_USERNAME", ""),
                "password": os.getenv("INSTA_PASSWORD", "")
            })
        
        # Get video details from YouTube for logging
        from googleapiclient.discovery import build
        api_key = os.getenv("YOUTUBE_API_KEY")
        youtube = build('youtube', 'v3', developerKey=api_key)
        
        # Process each video
        total_videos = len(video_ids)
        for idx, video_id in enumerate(video_ids, 1):
            try:
                # Get video title
                video_response = youtube.videos().list(part="snippet", id=video_id).execute()
                video_title = "Unknown"
                if video_response.get('items'):
                    video_title = video_response['items'][0]['snippet']['title']
                
                video_url = f"https://youtu.be/{video_id}"
                promotion_log.append(f"📹 [{idx}/{total_videos}] Processing: {video_title[:50]}...")
                
                # Promote to each platform
                for platform_name, platform_config in platforms.items():
                    try:
                        if platform_name == 'telegram':
                            bot_token = account_config["telegram_targets"][0]["bot_token"]
                            chat_id = account_config["telegram_targets"][0]["chat_id"]
                            message = f"🎬 New Video!\n\n{video_title}\n\n{video_url}"
                            
                            import requests
                            tg_url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
                            response = requests.post(tg_url, json={"chat_id": chat_id, "text": message})
                            
                            if response.status_code == 200:
                                promotion_log.append(f"   ✅ Telegram: Sent successfully")
                            else:
                                promotion_log.append(f"   ❌ Telegram: Failed - {response.text[:100]}")
                        
                        elif platform_name == 'twitter':
                            twitter_creds = account_config["twitter_targets"][0]
                            import tweepy
                            
                            # Get video transcript
                            promotion_log.append(f"   📝 Fetching video transcript...")
                            transcript_text = ""
                            try:
                                from youtube_transcript_api import YouTubeTranscriptApi
                                transcript_list = YouTubeTranscriptApi.get_transcript(video_id)
                                transcript_text = " ".join([t['text'] for t in transcript_list[:50]])  # First 50 segments
                            except Exception as te:
                                promotion_log.append(f"   ⚠️ No transcript available, using title")
                                transcript_text = video_title
                            
                            # Generate tweet using Gemini AI
                            promotion_log.append(f"   🤖 Generating tweet with Gemini AI...")
                            tweet_text = None
                            gemini_key = os.getenv("GEMINI_API_KEY")
                            
                            if gemini_key and transcript_text:
                                import google.generativeai as genai
                                genai.configure(api_key=gemini_key)
                                model = genai.GenerativeModel('gemini-2.0-flash-exp')
                                
                                max_retries = 3
                                char_limit = 250  # Leave room for URL
                                
                                for attempt in range(max_retries):
                                    try:
                                        prompt = f"""Create an engaging tweet for this YouTube video. 
Video Title: {video_title}
Video Transcript: {transcript_text[:2000]}

Requirements:
- Maximum {char_limit} characters (STRICT LIMIT)
- Include relevant emojis
- Make it catchy and encourage clicks
- Do NOT include any URL or link
- Do NOT use hashtags
- Just the tweet text, nothing else

Tweet:"""
                                        
                                        response = model.generate_content(prompt)
                                        generated_tweet = response.text.strip().strip('"').strip("'")
                                        
                                        if len(generated_tweet) <= char_limit:
                                            tweet_text = generated_tweet
                                            break
                                        else:
                                            char_limit = char_limit - 30  # Reduce limit for next attempt
                                            promotion_log.append(f"   ⚠️ Tweet too long ({len(generated_tweet)} chars), retrying...")
                                    except Exception as gemini_error:
                                        error_str = str(gemini_error)
                                        if "429" in error_str or "Too Many Requests" in error_str:
                                            wait_time = (attempt + 1) * 10  # 10s, 20s, 30s
                                            promotion_log.append(f"   ⏳ Rate limited, waiting {wait_time}s...")
                                            import time
                                            time.sleep(wait_time)
                                        else:
                                            promotion_log.append(f"   ⚠️ Gemini error: {error_str[:80]}")
                                            break
                            
                            # Fallback if Gemini fails
                            if not tweet_text:
                                tweet_text = f"🎬 {video_title[:200]}"
                            
                            # Append video URL
                            full_tweet = f"{tweet_text}\n\n{video_url}"
                            
                            # Post to Twitter using v2 API
                            client = tweepy.Client(
                                consumer_key=twitter_creds["api_key"],
                                consumer_secret=twitter_creds["api_secret"],
                                access_token=twitter_creds["access_token"],
                                access_token_secret=twitter_creds["access_secret"]
                            )
                            
                            result = client.create_tweet(text=full_tweet)
                            promotion_log.append(f"   ✅ Twitter/X: Posted! \"{tweet_text[:50]}...\"")
                        
                        elif platform_name == 'instagram':
                            # Instagram posting is complex, just log for now
                            promotion_log.append(f"   ⚠️ Instagram: Manual posting required (API limitations)")
                            
                    except Exception as platform_error:
                        promotion_log.append(f"   ❌ {platform_name.title()}: {str(platform_error)[:100]}")
                
            except Exception as video_error:
                promotion_log.append(f"❌ Error processing video {video_id}: {str(video_error)[:100]}")
        
        promotion_log.append(f"")
        promotion_log.append(f"✨ Promotion complete! Processed {total_videos} video(s)")
        promotion_status["running"] = False
        promotion_status["complete"] = True
        
    except Exception as e:
        promotion_log.append(f"❌ Promotion failed: {str(e)}")
        promotion_status["running"] = False
        promotion_status["complete"] = True
        import traceback
        traceback.print_exc()


# Store promotion progress
promotion_log = []
promotion_status = {"running": False, "complete": False}


@app.get("/api/promotion-status")
async def get_promotion_status():
    """Get current promotion status and logs"""
    return {
        "running": promotion_status["running"],
        "complete": promotion_status["complete"],
        "logs": promotion_log
    }


@app.post("/api/promotion-reset")
async def reset_promotion_status():
    """Reset promotion status for new run"""
    global promotion_log, promotion_status
    promotion_log = []
    promotion_status = {"running": False, "complete": False}
    return {"success": True}


@app.get("/api/promotion-config")
async def get_promotion_config():
    """Get promotion configuration from environment variables"""
    try:
        from dotenv import load_dotenv
        load_dotenv()
        
        # Check Twitter credentials from .env (API v1.1)
        twitter_api_key = os.getenv("X_API_KEY", "")
        twitter_api_secret = os.getenv("X_API_KEY_SECRET", "")
        twitter_access_token = os.getenv("X_ACCESS_TOKEN", "")
        twitter_access_secret = os.getenv("X_ACCESS_TOKEN_SECRET", "")
        twitter_bearer = os.getenv("X_BEARER_TOKEN", "")
        
        # Twitter is connected if we have the API credentials
        twitter_connected = bool(twitter_api_key and twitter_api_secret and twitter_access_token and twitter_access_secret)
        
        # Check Instagram credentials from .env
        insta_username = os.getenv("INSTA_USERNAME", "")
        insta_password = os.getenv("INSTA_PASSWORD", "")
        instagram_connected = bool(insta_username and insta_password)
        
        config = {
            "telegram": {
                "bot_token": os.getenv("TELEGRAM_BOT_TOKEN", ""),
                "channel_id": os.getenv("TELEGRAM_CHAT_ID", "")
            },
            "twitter": {
                "api_key": twitter_api_key,
                "api_secret": twitter_api_secret,
                "access_token": twitter_access_token,
                "access_secret": twitter_access_secret,
                "bearer_token": twitter_bearer,
                "connected": twitter_connected,
                "username": "@connected" if twitter_connected else None
            },
            "instagram": {
                "username": insta_username,
                "connected": instagram_connected
            },
            "gemini_api_key": os.getenv("GEMINI_API_KEY", "")
        }
        
        return {"success": True, "config": config}
    except Exception as e:
        return {"success": False, "error": str(e)}


# Twitter OAuth 2.0 with PKCE
import secrets
import hashlib
import base64

# Store PKCE values temporarily
_oauth_state = {}

@app.get("/api/twitter/auth")
async def twitter_auth_start():
    """Start Twitter OAuth 2.0 PKCE flow"""
    try:
        from dotenv import load_dotenv
        load_dotenv()
        
        client_id = os.getenv("X_CLIENT_ID")
        if not client_id:
            return {"success": False, "error": "X_CLIENT_ID not configured in .env"}
        
        # Generate PKCE code verifier and challenge
        code_verifier = secrets.token_urlsafe(32)
        code_challenge = base64.urlsafe_b64encode(
            hashlib.sha256(code_verifier.encode()).digest()
        ).decode().rstrip('=')
        
        state = secrets.token_urlsafe(16)
        
        # Store for callback
        _oauth_state['twitter'] = {
            'code_verifier': code_verifier,
            'state': state
        }
        
        # Twitter OAuth 2.0 authorization URL
        redirect_uri = "http://localhost:8000/api/twitter/callback"
        scopes = "tweet.read tweet.write users.read offline.access"
        
        auth_url = (
            f"https://twitter.com/i/oauth2/authorize"
            f"?response_type=code"
            f"&client_id={client_id}"
            f"&redirect_uri={redirect_uri}"
            f"&scope={scopes.replace(' ', '%20')}"
            f"&state={state}"
            f"&code_challenge={code_challenge}"
            f"&code_challenge_method=S256"
        )
        
        return {"success": True, "auth_url": auth_url}
    except Exception as e:
        import traceback
        traceback.print_exc()
        return {"success": False, "error": str(e)}


@app.get("/api/twitter/callback")
async def twitter_callback(code: str = None, state: str = None, error: str = None):
    """Handle Twitter OAuth callback"""
    from fastapi.responses import HTMLResponse
    
    if error:
        return HTMLResponse(f"""
            <html><body style="font-family: sans-serif; text-align: center; padding: 50px;">
                <h2>❌ Twitter Authorization Failed</h2>
                <p>{error}</p>
                <p>You can close this window.</p>
                <script>setTimeout(() => window.close(), 3000);</script>
            </body></html>
        """)
    
    try:
        from dotenv import load_dotenv
        import requests
        import json
        load_dotenv()
        
        stored = _oauth_state.get('twitter', {})
        if state != stored.get('state'):
            return HTMLResponse("<h2>State mismatch error</h2>")
        
        client_id = os.getenv("X_CLIENT_ID")
        client_secret = os.getenv("X_CLIENT_SECRET")
        redirect_uri = "http://localhost:8000/api/twitter/callback"
        
        # Exchange code for tokens
        token_url = "https://api.twitter.com/2/oauth2/token"
        data = {
            "code": code,
            "grant_type": "authorization_code",
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "code_verifier": stored.get('code_verifier')
        }
        
        # Use Basic Auth with client credentials
        auth = (client_id, client_secret)
        
        response = requests.post(token_url, data=data, auth=auth)
        tokens = response.json()
        
        if 'access_token' not in tokens:
            return HTMLResponse(f"<h2>Token exchange failed</h2><pre>{tokens}</pre>")
        
        # Get user info
        user_response = requests.get(
            "https://api.twitter.com/2/users/me",
            headers={"Authorization": f"Bearer {tokens['access_token']}"}
        )
        user_data = user_response.json()
        username = user_data.get('data', {}).get('username', 'unknown')
        
        # Save tokens
        tokens['username'] = f"@{username}"
        with open("twitter_tokens.json", 'w') as f:
            json.dump(tokens, f, indent=2)
        
        return HTMLResponse(f"""
            <html><body style="font-family: sans-serif; text-align: center; padding: 50px; background: #0a0e27; color: white;">
                <h2 style="color: #10b981;">✓ Twitter Connected!</h2>
                <p>Connected as <strong>@{username}</strong></p>
                <p>You can close this window and return to the app.</p>
                <script>
                    if (window.opener) {{
                        window.opener.postMessage({{ type: 'twitter_connected', username: '@{username}' }}, '*');
                    }}
                    setTimeout(() => window.close(), 2000);
                </script>
            </body></html>
        """)
    except Exception as e:
        import traceback
        traceback.print_exc()
        return HTMLResponse(f"<h2>Error</h2><pre>{str(e)}</pre>")


@app.post("/api/twitter/disconnect")
async def twitter_disconnect():
    """Disconnect Twitter account"""
    try:
        if os.path.exists("twitter_tokens.json"):
            os.remove("twitter_tokens.json")
        return {"success": True}
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.get("/api/instagram/auth")
async def instagram_auth_start():
    """Start Instagram login flow (using instagrapi)"""
    # For Instagram, we'll use a simple username/password modal since Meta's API requires business accounts
    return {"success": True, "message": "Instagram uses username/password auth. Please enter credentials.", "use_modal": True}


@app.post("/api/instagram/login")
async def instagram_login(data: dict):
    """Login to Instagram using instagrapi"""
    try:
        from instagrapi import Client
        import json
        
        username = data.get('username')
        password = data.get('password')
        
        if not username or not password:
            return {"success": False, "error": "Username and password required"}
        
        cl = Client()
        
        # Try to login
        try:
            cl.login(username, password)
        except Exception as login_error:
            return {"success": False, "error": f"Login failed: {str(login_error)}"}
        
        # Save session
        session_data = {
            "username": f"@{username}",
            "session": cl.get_settings()
        }
        
        with open("instagram_session.json", 'w') as f:
            json.dump(session_data, f, indent=2)
        
        return {"success": True, "username": f"@{username}"}
    except ImportError:
        return {"success": False, "error": "instagrapi not installed. Run: pip install instagrapi"}
    except Exception as e:
        import traceback
        traceback.print_exc()
        return {"success": False, "error": str(e)}


@app.post("/api/instagram/disconnect")
async def instagram_disconnect():
    """Disconnect Instagram account"""
    try:
        if os.path.exists("instagram_session.json"):
            os.remove("instagram_session.json")
        return {"success": True}
    except Exception as e:
        return {"success": False, "error": str(e)}




@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for terminal communication"""
    await websocket.accept()
    session = TerminalSession(websocket)
    
    try:
        while True:
            # Receive command from client
            data = await websocket.receive_json()
            
            if data.get("type") == "command":
                command = data.get("command", "").strip()
                await handle_command(session, command)
                
    except WebSocketDisconnect:
        print("Client disconnected")
    except Exception as e:
        print(f"WebSocket error: {e}")
        try:
            await session.error(f"Server error: {e}")
        except:
            pass


async def handle_command(session: TerminalSession, command: str):
    """Route and execute commands"""
    if not command:
        return
    
    parts = command.split()
    cmd = parts[0].lower()
    args = parts[1:] if len(parts) > 1 else []
    
    # Command routing
    commands = {
        "help": cmd_help,
        "list-accounts": cmd_list_accounts,
        "add-account": cmd_add_account,
        "select-account": cmd_select_account,
        "run": cmd_run_automation,
        "promote": cmd_promote,
        "stats": cmd_stats,
        "clear": cmd_clear,
        "exit": cmd_exit,
        "accounts": cmd_list_accounts,  # alias
        "status": cmd_status,
    }
    
    if cmd in commands:
        try:
            await commands[cmd](session, args)
        except Exception as e:
            await session.error(f"Command failed: {e}")
    else:
        await session.error(f"Unknown command: {cmd}")
        await session.info("Type 'help' to see available commands")


async def cmd_help(session: TerminalSession, args: list):
    """Show help information"""
    await session.output("─" * 70, "separator")
    await session.output("Available Commands:", "text-info")
    await session.output("")
    
    commands_help = [
        ("help", "Show this help message"),
        ("list-accounts", "List all authenticated YouTube accounts"),
        ("add-account <name>", "Add a new YouTube account"),
        ("select-account <name>", "Select an account for operations"),
        ("status", "Show current session status"),
        ("run", "Run automation (schedule videos)"),
        ("promote", "Run promotion engine"),
        ("stats [account]", "View processed data summary"),
        ("clear", "Clear terminal screen"),
        ("exit", "Close terminal connection"),
    ]
    
    for cmd, desc in commands_help:
        await session.output(f"  {cmd:<25} {desc}", "text-white")
    
    await session.output("")
    await session.output("─" * 70, "separator")


async def cmd_list_accounts(session: TerminalSession, args: list):
    """List available accounts"""
    accounts = list_available_accounts()
    
    if not accounts:
        await session.warning("No accounts found")
        await session.info("Use 'add-account <name>' to add a new account")
        return
    
    await session.output("─" * 70, "separator")
    await session.output(f"Found {len(accounts)} account(s):", "text-info")
    await session.output("")
    
    for account in accounts:
        try:
            from youtube_metadata import get_account_token_file, TOKEN_PICKLE_FILE
            import pickle
            
            if account == "default":
                token_file = TOKEN_PICKLE_FILE
            else:
                token_file = get_account_token_file(account)
            
            with open(token_file, "rb") as f:
                creds = pickle.load(f)
                if creds and creds.valid:
                    channel_id, channel_title = get_account_info(creds)
                    if channel_title:
                        marker = "→" if account == session.selected_account else " "
                        await session.output(f"  {marker} {account}", "text-success")
                        await session.output(f"      Channel: {channel_title}", "text-muted")
                        await session.output(f"      ID: {channel_id}", "text-muted")
                    else:
                        await session.output(f"  ○ {account} (Unable to get info)", "text-warning")
                else:
                    await session.output(f"  ○ {account} (Credentials need refresh)", "text-warning")
        except Exception as e:
            await session.output(f"  ✗ {account} (Error: {e})", "text-error")
    
    await session.output("")
    await session.output("─" * 70, "separator")


async def cmd_add_account(session: TerminalSession, args: list):
    """Add a new account"""
    if not args:
        await session.error("Account name required")
        await session.info("Usage: add-account <name>")
        return
    
    account_name = args[0]
    
    # Validate account name
    import re
    if not re.match(r'^[a-zA-Z0-9_-]+$', account_name):
        await session.error("Invalid account name. Use only letters, numbers, hyphens, and underscores")
        return
    
    if account_name in list_available_accounts():
        await session.error(f"Account '{account_name}' already exists")
        return
    
    await session.info(f"Adding account: {account_name}")
    await session.warning("This will open a browser window for OAuth authentication")
    await session.output("Please complete the authentication in your browser...")
    
    try:
        # Run authentication in a separate thread to avoid blocking
        loop = asyncio.get_event_loop()
        creds = await loop.run_in_executor(None, authenticate_account, account_name)
        
        if creds:
            channel_id, channel_title = get_account_info(creds)
            if channel_title:
                await session.success(f"Account added successfully!")
                await session.output(f"  Account: {account_name}", "text-white")
                await session.output(f"  Channel: {channel_title}", "text-white")
                await session.output(f"  ID: {channel_id}", "text-white")
            else:
                await session.warning("Account added but unable to verify channel info")
        else:
            await session.error("Authentication failed")
    except Exception as e:
        await session.error(f"Failed to add account: {e}")


async def cmd_select_account(session: TerminalSession, args: list):
    """Select an account for operations"""
    if not args:
        await session.error("Account name required")
        await session.info("Usage: select-account <name>")
        return
    
    account_name = args[0]
    accounts = list_available_accounts()
    
    if account_name not in accounts:
        await session.error(f"Account '{account_name}' not found")
        await session.info("Use 'list-accounts' to see available accounts")
        return
    
    try:
        loop = asyncio.get_event_loop()
        creds = await loop.run_in_executor(None, authenticate_account, account_name)
        
        if creds:
            from googleapiclient.discovery import build
            service = build("youtube", "v3", credentials=creds)
            channel_id = get_account_id_from_service(service)
            channel_id_info, channel_title = get_account_info(creds)
            
            session.selected_account = account_name
            session.youtube_service = service
            session.channel_id = channel_id
            
            await session.success(f"Selected account: {account_name}")
            if channel_title:
                await session.output(f"  Channel: {channel_title}", "text-white")
        else:
            await session.error("Failed to authenticate account")
    except Exception as e:
        await session.error(f"Failed to select account: {e}")


async def cmd_status(session: TerminalSession, args: list):
    """Show session status"""
    await session.output("─" * 70, "separator")
    await session.output("Session Status:", "text-info")
    await session.output("")
    
    if session.selected_account:
        await session.output(f"  Selected Account: {session.selected_account}", "text-success")
        await session.output(f"  Channel ID: {session.channel_id}", "text-muted")
        await session.output(f"  Processing: {'Yes' if session.processing else 'No'}", "text-muted")
    else:
        await session.warning("No account selected")
        await session.info("Use 'select-account <name>' to select an account")
    
    await session.output("")
    await session.output("─" * 70, "separator")


async def cmd_run_automation(session: TerminalSession, args: list):
    """Run automation to schedule videos"""
    if not session.selected_account or not session.youtube_service:
        await session.error("No account selected")
        await session.info("Use 'select-account <name>' first")
        return
    
    if session.processing:
        await session.warning("Automation already running")
        return
    
    session.processing = True
    
    try:
        await session.info("Starting automation...")
        await session.output("─" * 70, "separator")
        
        # Fetch videos
        await session.output("Fetching unscheduled private videos...", "text-info")
        loop = asyncio.get_event_loop()
        videos = await loop.run_in_executor(None, get_my_unscheduled_private_video_ids, session.youtube_service)
        
        if not videos:
            await session.warning("No unscheduled private videos found")
            session.processing = False
            return
        
        await session.success(f"Found {len(videos)} video(s) to process")
        await session.output("")
        
        # Simple scheduling (1 video per day starting tomorrow at 9 AM)
        import pytz
        import tzlocal
        
        local_tz_name = tzlocal.get_localzone_name()
        system_tz = pytz.timezone(local_tz_name) if local_tz_name else pytz.utc
        
        current_date = datetime.date.today() + datetime.timedelta(days=1)
        scheduled_count = 0
        
        for idx, video_id in enumerate(videos):
            await session.output(f"[{idx+1}/{len(videos)}] Processing {video_id}...", "text-info")
            
            # Send progress
            await session.send("progress", current=idx+1, total=len(videos), message="Processing videos...")
            
            # Calculate publish time
            publish_dt_naive = datetime.datetime.combine(current_date, datetime.time(9, 0))
            publish_dt = system_tz.localize(publish_dt_naive)
            
            # Ensure it's in the future
            min_valid_dt = datetime.datetime.now(system_tz) + datetime.timedelta(minutes=30)
            if publish_dt < min_valid_dt:
                current_date += datetime.timedelta(days=1)
                publish_dt_naive = datetime.datetime.combine(current_date, datetime.time(9, 0))
                publish_dt = system_tz.localize(publish_dt_naive)
            
            await session.output(f"  ⏰ Scheduled for: {publish_dt.strftime('%Y-%m-%d %H:%M')}", "text-muted")
            
            # Get transcript
            transcript = await loop.run_in_executor(None, get_video_transcript, session.youtube_service, video_id)
            if not transcript:
                await session.warning(f"  No transcript found. Skipping.")
                continue
            
            # Check duplicates
            is_dup = await loop.run_in_executor(None, is_transcript_duplicate, session.channel_id, transcript)
            if is_dup:
                await session.warning(f"  Duplicate content detected. Skipping.")
                continue
            
            # Generate metadata
            await session.output(f"  🤖 Generating metadata...", "text-muted")
            metadata = await loop.run_in_executor(None, generate_metadata_with_gemini, transcript)
            
            if not metadata or "Placeholder" in metadata.get("title", "") or "Fallback" in metadata.get("title", ""):
                await session.warning(f"  Metadata generation failed. Skipping.")
                continue
            
            await session.output(f"  📌 Title: {metadata['title'][:60]}...", "text-muted")
            
            # Schedule video
            success = await loop.run_in_executor(
                None, 
                update_and_schedule_video, 
                session.youtube_service, 
                video_id, 
                metadata, 
                publish_dt
            )
            
            if success:
                scheduled_count += 1
                await session.success(f"  Video scheduled!")
                await loop.run_in_executor(None, save_video_data, session.channel_id, video_id, transcript, metadata, publish_dt)
            else:
                await session.error(f"  Failed to schedule video")
                await loop.run_in_executor(None, save_video_data, session.channel_id, video_id, transcript, metadata, None)
            
            await session.output("")
            
            # Move to next day
            current_date += datetime.timedelta(days=1)
        
        await session.output("─" * 70, "separator")
        await session.success(f"Automation complete! Scheduled {scheduled_count}/{len(videos)} videos")
        
    except QuotaExceededError as e:
        await session.error(f"YouTube API quota exceeded: {e}")
    except Exception as e:
        await session.error(f"Automation failed: {e}")
        import traceback
        traceback.print_exc()
    finally:
        session.processing = False


async def cmd_promote(session: TerminalSession, args: list):
    """Run promotion engine"""
    if not PROMOTION_AVAILABLE:
        await session.error("Promotion feature not available")
        await session.info("Missing required dependencies: pip install google-generativeai instagrapi")
        return
    
    if not session.selected_account:
        await session.error("No account selected")
        await session.info("Use 'select-account <name>' first")
        return
    
    await session.info("Promotion feature requires additional configuration")
    await session.warning("This feature is under development")


async def cmd_stats(session: TerminalSession, args: list):
    """View processed data summary"""
    if not session.channel_id:
        await session.error("No account selected")
        await session.info("Use 'select-account <name>' first")
        return
    
    await session.output("─" * 70, "separator")
    
    # Capture stdout to get summary
    from io import StringIO
    import sys
    
    old_stdout = sys.stdout
    sys.stdout = StringIO()
    
    try:
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, view_processed_data_summary, session.channel_id)
        output = sys.stdout.getvalue()
        
        for line in output.split('\n'):
            if line.strip():
                await session.output(line, "text-white")
    finally:
        sys.stdout = old_stdout
    
    await session.output("─" * 70, "separator")


async def cmd_clear(session: TerminalSession, args: list):
    """Clear terminal"""
    await session.send("clear")


async def cmd_exit(session: TerminalSession, args: list):
    """Exit terminal"""
    await session.info("Closing connection...")
    await session.websocket.close()


if __name__ == "__main__":
    print("Starting YouTube Automation Web Terminal...")
    print("Server will be available at: http://localhost:8000")
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
