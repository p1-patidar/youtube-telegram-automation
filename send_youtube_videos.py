import os
import json
import argparse
from datetime import datetime
import pytz
import requests
import subprocess
import shutil
import re
import base64
import tempfile
from dotenv import load_dotenv

load_dotenv()

# Defaults
DEFAULT_TIMEZONE = os.environ.get("TIMEZONE", "Asia/Kolkata")
CONFIG_PATH_ENV = os.environ.get("ACCOUNTS_CONFIG_PATH")

YOUTUBE_API_URL = "https://www.googleapis.com/youtube/v3/search"
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"


def load_config(path=None):
    """Load accounts configuration. If no config file is present, fall back to
    single-account behavior using environment variables (backwards-compatible).
    """
    # Look for a config file in working dir if not provided
    if path is None:
        path = CONFIG_PATH_ENV or os.path.join(os.getcwd(), "accounts_config.json")

    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    # Fallback to environment variables (legacy single-account mode)
    env = {
        "global": {
            "youtube_api_key": os.environ.get("YOUTUBE_API_KEY"),
            "telegram_bot_token": os.environ.get("TELEGRAM_BOT_TOKEN"),
        },
        "accounts": []
    }

    channel_id = os.environ.get("CHANNEL_ID")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    if channel_id and chat_id:
        env["accounts"].append({
            "channel_id": channel_id,
            "telegram_targets": [{"chat_id": chat_id}]
        })

    return env


def get_time_window(tz_name):
    tz = pytz.timezone(tz_name)
    now = datetime.now(tz)
    start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0)
    end_of_day = now.replace(hour=23, minute=59, second=59, microsecond=0)
    return start_of_day.isoformat(), end_of_day.isoformat()


def load_processed_set(channel_id):
    os.makedirs("processed_videos_data", exist_ok=True)
    safe_name = channel_id.replace("/", "_")
    path = os.path.join("processed_videos_data", f"account_{safe_name}_processed_videos.json")
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
                return set(data.get("videos", [])), path
        except Exception:
            return set(), path
    return set(), path


def save_processed_set(path, video_set):
    with open(path, "w", encoding="utf-8") as f:
        json.dump({"videos": list(video_set)}, f, indent=2)


def fetch_videos_for_channel(youtube_api_key, channel_id, start_iso, end_iso, max_results=50):
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
    resp = requests.get(YOUTUBE_API_URL, params=params)
    resp.raise_for_status()
    data = resp.json()
    videos = []
    for item in data.get("items", []):
        vid = item.get("id", {}).get("videoId")
        if vid:
            videos.append({"video_id": vid, "link": f"https://www.youtube.com/watch?v={vid}", "title": item.get("snippet", {}).get("title")})
    return videos


def fetch_transcript_ytdlp(video_url, prefer_langs=("en",)):
    """Try to extract transcript/subtitles using yt-dlp metadata.
    Falls back to the video description if subtitles are not available.
    Returns plain text transcript or None.
    """
    # Ensure yt-dlp is available
    if not shutil.which("yt-dlp"):
        print("yt-dlp not found on PATH; cannot fetch subtitles automatically.")
        return None

    try:
        cmd = ["yt-dlp", "--skip-download", "--dump-json", video_url]
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        if proc.returncode != 0 or not proc.stdout:
            print(f"yt-dlp failed for {video_url}: {proc.stderr.strip()}")
            return None
        data = json.loads(proc.stdout)

        # Check automatic_captions or subtitles
        for field in ("automatic_captions", "subtitles"):
            caps = data.get(field) or {}
            for lang in prefer_langs:
                if caps.get(lang):
                    # caps[lang] is typically a list of dicts with 'url' keys
                    entry = caps[lang][0]
                    sub_url = entry.get("url")
                    if sub_url:
                        r = requests.get(sub_url, timeout=30)
                        if r.ok:
                            text = _strip_vtt(r.text)
                            if text.strip():
                                return text

        # Fallback to description field
        desc = data.get("description")
        if desc and len(desc) > 20:
            return desc
        return None
    except Exception as e:
        print(f"Error fetching transcript via yt-dlp for {video_url}: {e}")
        return None


def _strip_vtt(vtt_text):
    # Remove WEBVTT header and timestamps
    lines = vtt_text.splitlines()
    out = []
    timestamp_re = re.compile(r"^\d{2}:\d{2}:\d{2}\.\d{3} -->")
    for line in lines:
        if line.strip().upper().startswith("WEBVTT"):
            continue
        if line.strip() == "":
            continue
        # skip cue timestamps
        if re.search(r"-->", line):
            continue
        # skip numeric cue ids
        if line.strip().isdigit():
            continue
        out.append(line.strip())
    return " ".join(out)


def send_telegram_message(bot_token, chat_id, text, dry_run=False):
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {"chat_id": chat_id, "text": text, "parse_mode": "HTML"}
    if dry_run:
        print(f"DRY RUN -> Would send to chat {chat_id} via bot {bot_token}: {text}")
        return None
    resp = requests.post(url, data=payload)
    try:
        return resp.json()
    except Exception:
        return {"ok": resp.ok, "status_code": resp.status_code, "text": resp.text}


def generate_tweet_with_gemini(transcript_text, max_words=40):
    if not GEMINI_API_KEY:
        print("GEMINI_API_KEY not set; cannot generate tweet.")
        return None
    if not transcript_text:
        return None

    prompt = f"Write a concise English tweet (no more than {max_words} words) about this YouTube video based on the following transcript. Keep the tone engaging and use one relevant hashtag. Output only the tweet text.\n\nTranscript:\n{transcript_text[:25000]}"
    url = f"{GEMINI_API_URL}?key={GEMINI_API_KEY}"
    payload = {"contents": [{"parts": [{"text": prompt}]}], "generationConfig": {"responseMimeType": "text/plain"}}
    headers = {"Content-Type": "application/json"}
    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=60)
        resp.raise_for_status()
        data = resp.json()
        cand = data.get("candidates")
        if cand and len(cand) > 0:
            # Candidate parsing: try to extract text safely
            first = cand[0]
            content = first.get("content")
            if isinstance(content, dict):
                parts = content.get("parts") or []
                if parts:
                    text = parts[0].get("text")
                else:
                    text = None
            else:
                # Older/alternate response shapes
                text = first.get("text") or first.get("output")

            if isinstance(text, str):
                words = text.split()
                if len(words) > max_words:
                    text = " ".join(words[:max_words])
                return text.strip()
        return None
    except Exception as e:
        print(f"Gemini generation error: {e}")
        return None


def generate_image_prompt_gemini(transcript_text):
    """Use Gemini to create a short image-generation prompt based on the transcript.
    Returns a prompt string or None.
    """
    if not GEMINI_API_KEY:
        print("GEMINI_API_KEY not set; cannot generate image prompt.")
        return None
    if not transcript_text:
        return None
    prompt = f"Create a concise, descriptive image-generation prompt for a social media post (Instagram feed image and story) based on this transcript. Keep it vivid, mention visual elements, composition, color palette, and one short caption suggestion. Output only the prompt text.\n\nTranscript:\n{transcript_text[:20000]}"
    url = f"{GEMINI_API_URL}?key={GEMINI_API_KEY}"
    payload = {"contents": [{"parts": [{"text": prompt}]}], "generationConfig": {"responseMimeType": "text/plain"}}
    headers = {"Content-Type": "application/json"}
    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=60)
        resp.raise_for_status()
        data = resp.json()
        cand = data.get("candidates")
        if cand and len(cand) > 0:
            first = cand[0]
            content = first.get("content")
            if isinstance(content, dict):
                parts = content.get("parts") or []
                if parts:
                    text = parts[0].get("text")
                else:
                    text = None
            else:
                text = first.get("text") or first.get("output")
            if isinstance(text, str):
                return text.strip()
        return None
    except Exception as e:
        print(f"Gemini image-prompt error: {e}")
        return None


def generate_image_via_webhook(image_prompt, webhook_url, dry_run=False):
    """Send the image prompt to an image-generation webhook which should return a JSON
    with an accessible `image_url` field. The webhook could be an integration with Stable, DALL·E, etc.
    Returns image_url or None.
    """
    if dry_run:
        print(f"DRY RUN -> would POST image prompt to {webhook_url}: {image_prompt[:200]}...")
        return None
    try:
        r = requests.post(webhook_url, json={"prompt": image_prompt}, timeout=60)
        r.raise_for_status()
        j = r.json()
        # Expect webhook to return {"image_url": "https://..."} or {"base64": "..."}
        if j.get("image_url"):
            return j.get("image_url")
        if j.get("base64"):
            # Save to a temp file and return file path
            b = base64.b64decode(j.get("base64"))
            fd, path = tempfile.mkstemp(suffix=".png")
            with os.fdopen(fd, "wb") as f:
                f.write(b)
            return path
        return None
    except Exception as e:
        print(f"Image webhook error: {e}")
        return None


def post_instagram_media(ig_conf, image_url, caption, is_story=False, dry_run=False):
    """Post an image to Instagram using the Facebook Graph API for Instagram Business accounts.
    ig_conf should contain 'ig_user_id' and 'access_token'.
    Returns the API response or None.

    Note: This implementation expects the Graph API media endpoints to be available for the account.
    Typical flow:
      1) POST https://graph.facebook.com/{ig_user_id}/media with image_url and caption -> returns creation_id
      2) POST https://graph.facebook.com/{ig_user_id}/media_publish with creation_id to publish
    For Stories some accounts may support creating a story container (same endpoint) and publishing it.
    """
    ig_user_id = ig_conf.get("ig_user_id")
    access_token = ig_conf.get("access_token")
    if not ig_user_id or not access_token:
        print("Missing Instagram ig_user_id or access_token; skipping Instagram post.")
        return None
    if dry_run:
        print(f"DRY RUN -> Would create Instagram {'story' if is_story else 'post'} for {ig_user_id} with image {image_url} and caption: {caption}")
        return None

    try:
        # 1) Create media container
        create_url = f"https://graph.facebook.com/v17.0/{ig_user_id}/media"
        payload = {"image_url": image_url, "caption": caption, "access_token": access_token}
        # Indicate story if requested (some APIs accept 'is_story' or 'media_type' flags)
        if is_story:
            payload["is_story"] = True
        r1 = requests.post(create_url, data=payload, timeout=30)
        r1.raise_for_status()
        j1 = r1.json()
        creation_id = j1.get("id") or j1.get("creation_id")
        if not creation_id:
            print(f"Failed to create Instagram media container: {j1}")
            return j1

        # 2) Publish
        publish_url = f"https://graph.facebook.com/v17.0/{ig_user_id}/media_publish"
        r2 = requests.post(publish_url, data={"creation_id": creation_id, "access_token": access_token}, timeout=30)
        r2.raise_for_status()
        return r2.json()
    except Exception as e:
        print(f"Instagram posting error: {e}")
        return None


def create_youtube_community_payload(transcript_text, video_link):
    """Generate a short YouTube community post text based on transcript and link the video."""
    # Keep it concise and engaging
    max_chars = 500
    summary = (transcript_text or "").strip().replace("\n", " ")[:1000]
    # Try to pick the first 200 chars as hook
    hook = summary[:200]
    post_text = f"{hook}...\nWatch: {video_link}"
    if len(post_text) > max_chars:
        post_text = post_text[:max_chars]
    return post_text


def post_youtube_community_via_webhook(webhook_url, post_text, dry_run=False):
    if dry_run:
        print(f"DRY RUN -> would POST community post to webhook {webhook_url} payload: {{'text': post_text}}")
        return None
    try:
        r = requests.post(webhook_url, json={"text": post_text}, timeout=15)
        try:
            return r.json()
        except Exception:
            return {"status_code": r.status_code, "text": r.text}
    except Exception as e:
        return {"error": str(e)}


def post_tweet_via_webhook(webhook_url, tweet_text, dry_run=False):
    if dry_run:
        print(f"DRY RUN -> would POST to webhook {webhook_url} payload: {{'text': tweet_text}}")
        return None
    try:
        r = requests.post(webhook_url, json={"text": tweet_text}, timeout=15)
        try:
            return r.json()
        except Exception:
            return {"status_code": r.status_code, "text": r.text}
    except Exception as e:
        return {"error": str(e)}


def post_tweet_oauth1(oauth_conf, tweet_text, dry_run=False):
    """Post a tweet using OAuth1 credentials (api_key, api_secret, access_token, access_token_secret).
    oauth_conf: dict with keys api_key, api_secret, access_token, access_token_secret
    """
    try:
        from requests_oauthlib import OAuth1
    except Exception:
        print("requests_oauthlib required for OAuth1 posting. Please install requests-oauthlib.")
        return None

    if dry_run:
        print(f"DRY RUN -> would post tweet: {tweet_text}")
        return None

    auth = OAuth1(oauth_conf.get("api_key"), oauth_conf.get("api_secret"), oauth_conf.get("access_token"), oauth_conf.get("access_token_secret"))
    url = "https://api.twitter.com/1.1/statuses/update.json"
    try:
        res = requests.post(url, auth=auth, data={"status": tweet_text}, timeout=15)
        try:
            return res.json()
        except Exception:
            return {"status_code": res.status_code, "text": res.text}
    except Exception as e:
        return {"error": str(e)}


def post_tweet_x_api(bearer_token, tweet_text, dry_run=False):
    """Post a tweet via X (Twitter) API v2 using a user OAuth2 bearer token with `tweet.write` scope.
    The token provided must be a user access token (not an app-only token)."""
    if dry_run:
        print(f"DRY RUN -> would POST to X API /2/tweets: {tweet_text}")
        return None
    if not bearer_token:
        return {"error": "Missing X API bearer token"}
    url = "https://api.twitter.com/2/tweets"
    headers = {"Authorization": f"Bearer {bearer_token}", "Content-Type": "application/json"}
    payload = {"text": tweet_text}
    try:
        r = requests.post(url, headers=headers, json=payload, timeout=15)
        try:
            return r.json()
        except Exception:
            return {"status_code": r.status_code, "text": r.text}
    except Exception as e:
        return {"error": str(e)}


def post_tweet_dispatch(target_conf, tweet_text, global_conf=None, dry_run=False):
    """
    Unified dispatcher for posting to X/Twitter.
    Preference order:
      1) per-target `x_bearer_token`
      2) per-target `oauth2.access_token` (user OAuth2 token)
      3) global `x_bearer_token`
      4) per-target `webhook`
      5) per-target `oauth` (OAuth1 config)
    Returns the response from the underlying posting function.
    """
    global_conf = global_conf or {}

    # 1) Per-target X bearer token
    token = target_conf.get("x_bearer_token")
    if token:
        return post_tweet_x_api(token, tweet_text, dry_run=dry_run)

    # 2) Per-target OAuth2 user token (access_token)
    oauth2 = target_conf.get("oauth2") or {}
    token2 = oauth2.get("access_token")
    if token2:
        return post_tweet_x_api(token2, tweet_text, dry_run=dry_run)

    # 3) Global X bearer token
    gtoken = global_conf.get("x_bearer_token")
    if gtoken:
        return post_tweet_x_api(gtoken, tweet_text, dry_run=dry_run)

    # 4) Webhook fallback
    webhook = target_conf.get("webhook")
    if webhook:
        return post_tweet_via_webhook(webhook, tweet_text, dry_run=dry_run)

    # 5) OAuth1 fallback
    oauth1_conf = target_conf.get("oauth")
    if oauth1_conf:
        return post_tweet_oauth1(oauth1_conf, tweet_text, dry_run=dry_run)

    return {"error": "No valid twitter/X target configuration found"}


def process_account(account, global_conf, start_iso, end_iso, dry_run=False):
    channel_id = account.get("channel_id")
    if not channel_id:
        print("Skipping account with no channel_id")
        return

    youtube_api_key = account.get("youtube_api_key") or global_conf.get("youtube_api_key")
    if not youtube_api_key:
        print(f"No YouTube API key for channel {channel_id}; skipping")
        return

    videos = fetch_videos_for_channel(youtube_api_key, channel_id, start_iso, end_iso)
    existing_set, path = load_processed_set(channel_id)

    new_videos = [v for v in videos if v["video_id"] not in existing_set]

    # If there are telegram targets configured, send to each
    telegram_targets = account.get("telegram_targets", [])
    # Support single legacy value
    if not telegram_targets and account.get("telegram_chat_id"):
        telegram_targets = [{"chat_id": account.get("telegram_chat_id")}]

    if not telegram_targets:
        print(f"No telegram targets for channel {channel_id}; skipping send step")

    if new_videos:
        for v in new_videos:
            text = f"New video posted: {v['link']}\n{v.get('title','')}"
            for t in telegram_targets:
                bot = t.get("bot_token") or global_conf.get("telegram_bot_token")
                chat = t.get("chat_id")
                if not bot or not chat:
                    print(f"Missing telegram bot or chat for target {t}; skipping")
                    continue
                res = send_telegram_message(bot, chat, text, dry_run=dry_run)
                print(f"Sent to {chat}: {res}")
            # --- Transcription + Tweet generation/posting ---
            try:
                transcript = fetch_transcript_ytdlp(v['link'])
                if transcript:
                    tweet_text = None
                    # Allow account-level override of tweet length
                    tweet_word_limit = account.get("tweet_word_limit") or global_conf.get("tweet_word_limit") or 40
                    try:
                        tweet_word_limit = int(tweet_word_limit)
                    except Exception:
                        tweet_word_limit = 40

                    tweet_text = generate_tweet_with_gemini(transcript, max_words=tweet_word_limit)
                    if tweet_text:
                        twitter_targets = account.get("twitter_targets", [])
                        # Support legacy single twitter_webhook in account
                        if not twitter_targets and account.get("twitter_webhook"):
                            twitter_targets = [{"webhook": account.get("twitter_webhook")}]

                        if not twitter_targets:
                            # Try global twitter webhook
                            if global_conf.get("twitter_webhook"):
                                twitter_targets = [{"webhook": global_conf.get("twitter_webhook") }]

                        for tt in twitter_targets:
                            resp = post_tweet_dispatch(tt, tweet_text, global_conf=global_conf, dry_run=dry_run)
                            print(f"Twitter/X post response for target {tt}: {resp}")
                    # --- Image generation and Instagram posting ---
                    try:
                        # Generate image prompt
                        img_prompt = generate_image_prompt_gemini(transcript)
                        img_url = None
                        # Determine image generation webhook (per-account -> global)
                        img_wh = account.get("image_generation_webhook") or global_conf.get("image_generation_webhook")
                        if img_prompt and img_wh:
                            img_url = generate_image_via_webhook(img_prompt, img_wh, dry_run=dry_run)
                        # If an image URL was produced, post to Instagram targets
                        instagram_targets = account.get("instagram_targets", [])
                        if instagram_targets:
                            for it in instagram_targets:
                                if not img_url:
                                    print(f"No image URL available for Instagram target {it}; skipping")
                                    continue
                                resp = post_instagram_media(it, img_url, caption=(v.get('title') or ''), is_story=False, dry_run=dry_run)
                                print(f"Instagram post response: {resp}")
                                # Optionally post as story too
                                if it.get("post_story", False):
                                    resp2 = post_instagram_media(it, img_url, caption=(v.get('title') or ''), is_story=True, dry_run=dry_run)
                                    print(f"Instagram story response: {resp2}")
                        else:
                            print("No instagram_targets configured for this account.")

                        # --- YouTube community post ---
                        community_conf = account.get("youtube_community") or global_conf.get("youtube_community")
                        if community_conf:
                            post_text = create_youtube_community_payload(transcript, v.get('link'))
                            # support webhook posting for community posts
                            if community_conf.get("webhook"):
                                res = post_youtube_community_via_webhook(community_conf.get("webhook"), post_text, dry_run=dry_run)
                                print(f"YouTube community webhook response: {res}")
                            else:
                                # fallback: save to file for manual posting
                                out_dir = "youtube_community_out"
                                os.makedirs(out_dir, exist_ok=True)
                                fname = os.path.join(out_dir, f"community_{v['video_id']}.txt")
                                with open(fname, "w", encoding="utf-8") as f:
                                    f.write(post_text)
                                print(f"Saved community post draft to {fname}")
                    except Exception as e:
                        print(f"Error during image/instagram/community flow for {v['link']}: {e}")
                else:
                    print(f"No transcript found for {v['link']}; skipping tweet generation")
            except Exception as e:
                print(f"Error during transcription/tweet flow for {v['link']}: {e}")
            # mark video as processed after attempting sends to avoid duplicates
            existing_set.add(v["video_id"])
    else:
        # If configured, optionally notify of no new videos
        for t in telegram_targets:
            send_if_none = t.get("send_no_video_messages", account.get("send_no_video_messages", False))
            if send_if_none:
                bot = t.get("bot_token") or global_conf.get("telegram_bot_token")
                chat = t.get("chat_id")
                if bot and chat:
                    res = send_telegram_message(bot, chat, "No new videos today.", dry_run=dry_run)
                    print(f"No-videos message to {chat}: {res}")

    # Persist processed set
    save_processed_set(path, existing_set)


def main():
    parser = argparse.ArgumentParser(description="Send new YouTube videos to Telegram (multi-account)")
    parser.add_argument("--config", "-c", help="Path to accounts_config.json")
    parser.add_argument("--timezone", "-t", help="Timezone name (e.g., Asia/Kolkata)")
    parser.add_argument("--dry-run", action="store_true", help="Don't send messages; just print actions")
    args = parser.parse_args()

    cfg = load_config(args.config)
    tz = args.timezone or cfg.get("global", {}).get("timezone") or DEFAULT_TIMEZONE
    start_iso, end_iso = get_time_window(tz)

    global_conf = cfg.get("global", {})

    accounts = cfg.get("accounts", [])
    if not accounts:
        print("No accounts configured. Exiting.")
        return

    for account in accounts:
        try:
            process_account(account, global_conf, start_iso, end_iso, dry_run=args.dry_run)
        except Exception as e:
            print(f"Error processing account {account.get('channel_id')}: {e}")


if __name__ == "__main__":
    main()
