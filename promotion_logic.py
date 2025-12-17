import os
import json
import datetime
import pytz
import requests
from googleapiclient.discovery import build
import google.generativeai as genai
from instagrapi import Client as InstaClient
import tempfile
import base64
from dotenv import load_dotenv

load_dotenv()

# Constants
YOUTUBE_API_URL = "https://www.googleapis.com/youtube/v3/search"
GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"

class PromotionEngine:
    def __init__(self, gemini_api_key=None):
        self.gemini_api_key = gemini_api_key or os.environ.get("GEMINI_API_KEY")
        self.processed_dir = "processed_videos_data"
        os.makedirs(self.processed_dir, exist_ok=True)

    def get_time_window(self, tz_name):
        try:
            tz = pytz.timezone(tz_name)
        except Exception:
            tz = pytz.utc
        now = datetime.datetime.now(tz)
        start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0)
        end_of_day = now.replace(hour=23, minute=59, second=59, microsecond=0)
        return start_of_day.isoformat(), end_of_day.isoformat()

    def load_processed_set(self, channel_id):
        safe_name = channel_id.replace("/", "_")
        path = os.path.join(self.processed_dir, f"account_{safe_name}_promoted_videos.json")
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    return set(data.get("videos", [])), path
            except Exception:
                return set(), path
        return set(), path

    def save_processed_set(self, path, video_set):
        with open(path, "w", encoding="utf-8") as f:
            json.dump({"videos": list(video_set)}, f, indent=2)

    def fetch_videos_for_channel(self, youtube_api_key, channel_id, start_iso, end_iso, max_results=50):
        params = {
            "part": "snippet",
            "channelId": channel_id,
            "maxResults": max_results,
            "order": "date",
            "publishedAfter": start_iso,
            "publishedBefore": end_iso,
            "type": "video",
            "key": youtube_api_key,
        }
        try:
            resp = requests.get(YOUTUBE_API_URL, params=params)
            resp.raise_for_status()
            data = resp.json()
            videos = []
            for item in data.get("items", []):
                vid = item.get("id", {}).get("videoId")
                if vid:
                    videos.append({
                        "video_id": vid,
                        "link": f"https://www.youtube.com/watch?v={vid}",
                        "title": item.get("snippet", {}).get("title")
                    })
            return videos
        except Exception as e:
            print(f"Error fetching videos: {e}")
            return []

    def fetch_transcript_ytdlp(self, video_url, prefer_langs=("en",)):
        if not shutil.which("yt-dlp"):
            return None

        try:
            cmd = ["yt-dlp", "--skip-download", "--dump-json", video_url]
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            if proc.returncode != 0 or not proc.stdout:
                return None
            data = json.loads(proc.stdout)

            for field in ("automatic_captions", "subtitles"):
                caps = data.get(field) or {}
                for lang in prefer_langs:
                    if caps.get(lang):
                        entry = caps[lang][0]
                        sub_url = entry.get("url")
                        if sub_url:
                            r = requests.get(sub_url, timeout=30)
                            if r.ok:
                                text = self._strip_vtt(r.text)
                                if text.strip():
                                    return text
            
            desc = data.get("description")
            if desc and len(desc) > 20:
                return desc
            return None
        except Exception as e:
            print(f"Error fetching transcript: {e}")
            return None

    def _strip_vtt(self, vtt_text):
        lines = vtt_text.splitlines()
        out = []
        for line in lines:
            if line.strip().upper().startswith("WEBVTT"): continue
            if line.strip() == "": continue
            if "-->" in line: continue
            if line.strip().isdigit(): continue
            out.append(line.strip())
        return " ".join(out)

    def generate_tweet(self, transcript_text, max_words=30):
        if not self.gemini_api_key or not transcript_text:
            return None
        
        prompt = f"Write a viral, clickbait-style tweet (max {max_words} words) to promote a YouTube video based on this transcript. Use a hook to make people click. Do NOT include any links (I will add one). Output ONLY the tweet text.\n\nTranscript:\n{transcript_text[:25000]}"
        return self._call_gemini(prompt)

    def generate_image_prompt(self, transcript_text):
        if not self.gemini_api_key or not transcript_text:
            return None
        
        prompt = f"Create a HIGHLY CLICKBAIT, viral-style image generation prompt based on this video transcript. The image should be shocking, intriguing, or visually stunning to stop the scroll on Instagram. Describe the subject, action, lighting, and style in detail. Output ONLY the prompt text.\n\nTranscript:\n{transcript_text[:20000]}"
        return self._call_gemini(prompt)

    def generate_instagram_caption(self, transcript_text):
        if not self.gemini_api_key or not transcript_text:
            return None
        
        prompt = f"Write an engaging, viral Instagram caption for a video based on this transcript. Use a hook in the first line. Include emojis and 5-10 relevant hashtags at the end. Output ONLY the caption text.\n\nTranscript:\n{transcript_text[:20000]}"
        return self._call_gemini(prompt)

    def _call_gemini(self, prompt):
        url = f"{GEMINI_API_URL}?key={self.gemini_api_key}"
        payload = {"contents": [{"parts": [{"text": prompt}]}], "generationConfig": {"responseMimeType": "text/plain"}}
        headers = {"Content-Type": "application/json"}
        try:
            resp = requests.post(url, headers=headers, json=payload, timeout=60)
            resp.raise_for_status()
            data = resp.json()
            cand = data.get("candidates")
            if cand:
                content = cand[0].get("content")
                if isinstance(content, dict):
                    parts = content.get("parts") or []
                    if parts:
                        return parts[0].get("text", "").strip()
                else:
                    # Fallback for older/alternate shapes
                    return (cand[0].get("text") or cand[0].get("output") or "").strip()
            return None
        except Exception as e:
            print(f"Gemini error: {e}")
            return None

    def send_telegram_message(self, bot_token, chat_id, text, dry_run=False):
        if dry_run:
            return {"ok": True, "dry_run": True}
        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        payload = {"chat_id": chat_id, "text": text, "parse_mode": "HTML"}
        try:
            resp = requests.post(url, data=payload, timeout=15)
            return resp.json()
        except Exception as e:
            return {"error": str(e)}

    def post_tweet(self, target_conf, tweet_text, dry_run=False):
        # Simplified dispatcher
        if dry_run:
            return {"ok": True, "dry_run": True}
        
        # 1. Bearer Token
        token = target_conf.get("x_bearer_token")
        if token:
            url = "https://api.twitter.com/2/tweets"
            headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
            try:
                r = requests.post(url, headers=headers, json={"text": tweet_text}, timeout=15)
                return r.json()
            except Exception as e:
                return {"error": str(e)}
        
        # 2. Webhook
        webhook = target_conf.get("webhook")
        if webhook:
            try:
                r = requests.post(webhook, json={"text": tweet_text}, timeout=15)
                return r.json()
            except Exception as e:
                return {"error": str(e)}
                
        return {"error": "No valid Twitter configuration"}

    def generate_image(self, webhook_url, prompt, dry_run=False):
        if dry_run:
            return None
        try:
            r = requests.post(webhook_url, json={"prompt": prompt}, timeout=60)
            r.raise_for_status()
            j = r.json()
            if j.get("image_url"):
                return j.get("image_url")
            if j.get("base64"):
                b = base64.b64decode(j.get("base64"))
                fd, path = tempfile.mkstemp(suffix=".png")
                with os.fdopen(fd, "wb") as f:
                    f.write(b)
                return path
            return None
        except Exception as e:
            print(f"Image gen error: {e}")
            return None

    def post_instagram(self, ig_conf, image_url, caption, is_story=False, dry_run=False):
        if dry_run:
            return {"ok": True, "dry_run": True}
        
        ig_user_id = ig_conf.get("ig_user_id")
        access_token = ig_conf.get("access_token")
        if not ig_user_id or not access_token:
            return {"error": "Missing IG credentials"}

        try:
            # 1. Create Container
            create_url = f"https://graph.facebook.com/v17.0/{ig_user_id}/media"
            payload = {"image_url": image_url, "caption": caption, "access_token": access_token}
            if is_story:
                payload["is_story"] = True
            
            r1 = requests.post(create_url, data=payload, timeout=30)
            r1.raise_for_status()
            creation_id = r1.json().get("id")

            # 2. Publish
            publish_url = f"https://graph.facebook.com/v17.0/{ig_user_id}/media_publish"
            r2 = requests.post(publish_url, data={"creation_id": creation_id, "access_token": access_token}, timeout=30)
            return r2.json()
        except Exception as e:
            return {"error": str(e)}

    def generate_image_gemini(self, prompt):
        """Generate image using Gemini (Imagen) API."""
        if not self.gemini_api_key:
            return None
        
        # Try Imagen 3 endpoint
        url = f"https://generativelanguage.googleapis.com/v1beta/models/imagen-3.0-generate-001:predict?key={self.gemini_api_key}"
        payload = {
            "instances": [{"prompt": prompt}],
            "parameters": {
                "sampleCount": 1,
                "aspectRatio": "1:1"
            }
        }
        headers = {"Content-Type": "application/json"}
        
        try:
            resp = requests.post(url, headers=headers, json=payload, timeout=60)
            resp.raise_for_status()
            data = resp.json()
            
            # Parse response (structure may vary, assuming standard Vertex-like or AI Studio)
            predictions = data.get("predictions")
            if predictions:
                b64_data = predictions[0].get("bytesBase64Encoded")
                if b64_data:
                    b = base64.b64decode(b64_data)
                    fd, path = tempfile.mkstemp(suffix=".png")
                    with os.fdopen(fd, "wb") as f:
                        f.write(b)
                    return path
            return None
        except Exception as e:
            print(f"Gemini Image Gen error: {e}")
            return None

    def post_instagram_instagrapi(self, username, password, image_path, caption, dry_run=False):
        """Post to Instagram using Instagrapi (Unofficial API)."""
        if dry_run:
            return "Dry Run: Posted to Instagram (Instagrapi)"
        
        try:
            cl = InstaClient()
            cl.login(username, password)
            media = cl.photo_upload(image_path, caption)
            return f"Posted ID: {media.pk}"
        except Exception as e:
            return f"Error (Instagrapi): {e}"

    def process_account(self, account_config, dry_run=False, log_callback=print):
        """
        Main driver function for a single account.
        account_config: dict containing keys like 'channel_id', 'youtube_api_key', 'telegram_targets', etc.
        """
        channel_id = account_config.get("channel_id")
        if not channel_id:
            log_callback("Skipping account: No channel_id")
            return

        api_key = account_config.get("youtube_api_key")
        if not api_key:
            log_callback(f"Skipping {channel_id}: No YouTube API key")
            return

        tz_name = account_config.get("timezone", "UTC")
        start_iso, end_iso = self.get_time_window(tz_name)
        
        log_callback(f"Checking videos for {channel_id} ({start_iso} to {end_iso})...")
        videos = self.fetch_videos_for_channel(api_key, channel_id, start_iso, end_iso)
        
        existing_set, path = self.load_processed_set(channel_id)
        new_videos = [v for v in videos if v["video_id"] not in existing_set]

        if not new_videos:
            log_callback("No new videos found.")
            return

        for v in new_videos:
            log_callback(f"Processing new video: {v['title']}")
            
            # 1. Telegram
            tg_targets = account_config.get("telegram_targets", [])
            msg_text = f"New video posted: {v['link']}\n{v.get('title','')}"
            for tg in tg_targets:
                res = self.send_telegram_message(tg.get("bot_token"), tg.get("chat_id"), msg_text, dry_run)
                log_callback(f"Telegram sent: {res}")

            # 2. Content Generation (if needed)
            tw_targets = account_config.get("twitter_targets", [])
            ig_targets = account_config.get("instagram_targets", [])
            
            if tw_targets or ig_targets:
                transcript = self.fetch_transcript_ytdlp(v['link'])
                if transcript:
                    # Twitter
                    if tw_targets:
                        tweet_body = self.generate_tweet(transcript)
                        if tweet_body:
                            final_tweet = f"{tweet_body}\n\n{v['link']}"
                            for tw in tw_targets:
                                res = self.post_tweet(tw, final_tweet, dry_run)
                                log_callback(f"Twitter posted: {res}")
                    
                    # Instagram
                    if ig_targets:
                        img_prompt = self.generate_image_prompt(transcript)
                        ig_caption = self.generate_instagram_caption(transcript) or v.get('title','')
                        
                        if img_prompt:
                            img_url = None
                            # Check source
                            source = account_config.get("image_source", "webhook")
                            
                            if source == "gemini":
                                log_callback("Generating image with Gemini...")
                                img_url = self.generate_image_gemini(img_prompt)
                            else:
                                # Webhook fallback
                                img_webhook = account_config.get("image_generation_webhook")
                                if img_webhook:
                                    log_callback("Generating image via Webhook...")
                                    img_url = self.generate_image(img_webhook, img_prompt, dry_run)
                            
                            if img_url:
                                for ig in ig_targets:
                                    method = account_config.get("ig_method", "official")
                                    if method == "instagrapi":
                                        # Use Instagrapi
                                        username = account_config.get("ig_username")
                                        password = account_config.get("ig_password")
                                        if username and password:
                                            # Instagrapi needs a local file path. 
                                            # If img_url is a local path (from Gemini), use it.
                                            # If it's a URL (from Webhook), download it first.
                                            local_path = img_url
                                            if img_url.startswith("http"):
                                                try:
                                                    import urllib.request
                                                    fd, local_path = tempfile.mkstemp(suffix=".jpg")
                                                    urllib.request.urlretrieve(img_url, local_path)
                                                except Exception as e:
                                                    log_callback(f"Failed to download image for Instagrapi: {e}")
                                                    local_path = None
                                            
                                            if local_path:
                                                res = self.post_instagram_instagrapi(username, password, local_path, ig_caption, dry_run)
                                                log_callback(f"Instagram (Instagrapi) posted: {res}")
                                        else:
                                            log_callback("Missing Instagrapi credentials.")
                                    else:
                                        # Use Official API
                                        res = self.post_instagram(ig, img_url, ig_caption, dry_run=dry_run)
                                        log_callback(f"Instagram posted: {res}")
                            else:
                                log_callback("Image generation failed.")
                else:
                    log_callback("No transcript available for content generation.")

            existing_set.add(v["video_id"])
        
        self.save_processed_set(path, existing_set)
