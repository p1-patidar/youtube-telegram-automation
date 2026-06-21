# YouTube Shorts Automation Suite

A multi-account automation suite that sends new YouTube Shorts from your channel(s) to Telegram, generates AI-written metadata, and cross-posts to Twitter/X and Instagram — controlled through a desktop GUI or terminal/web UI.

## What It Does

- **Multi-account support:** manage multiple YouTube channels, each with its own Telegram/Twitter/Instagram targets
- **AI metadata generation:** uses Gemini AI to generate titles/descriptions/tags for videos
- **Cross-posting:** sends new Shorts to Telegram chats, with optional Twitter (via webhook/IFTTT or X API) and Instagram (via access token) distribution
- **Token management:** refreshes and verifies OAuth tokens/account status (`refresh_tokens.py`, `check_account_status.py`)
- **Multiple interfaces:** Tkinter desktop GUI (`automation_gui.py` / `run_gui.py`), a browser-based terminal (`run_web_terminal.py`, `web_terminal/`), and standalone scripts (`send_youtube_videos.py`, `youtube_metadata.py`)
- **Utilities:** timestamp removal from descriptions, Instagram transcription helper

## Tech Stack

- **Language:** Python 3
- **APIs:** YouTube Data API v3 (OAuth via `google-auth`/`InstalledAppFlow`), Gemini API, Telegram Bot API, Twitter/X API, Instagram Graph API
- **GUI:** Tkinter (desktop), simple JS/HTML web terminal
- **Config:** `.env` for secrets, `accounts_config.json` for per-account/channel routing (uses placeholder values, not committed with real credentials)

## How to Run

```bash
# Install dependencies
pip install -r requirements.txt

# Configure environment variables
cp .env.example .env
# Fill in GEMINI_API_KEY (required), YOUTUBE_API_KEY, TELEGRAM_BOT_TOKEN, etc.

# Set up Google OAuth
# 1. Create a project at https://console.cloud.google.com
# 2. Enable YouTube Data API v3
# 3. Create OAuth 2.0 Desktop credentials, download as client_secret.json

# Launch the desktop GUI
python run_gui.py

# Or launch the web terminal
python run_web_terminal.py
```

See `docs/GUI_QUICKSTART.md` and `docs/START_HERE.md` in this repo for the full first-time setup walkthrough, and `docs/MULTI_ACCOUNT_GUIDE.md` for adding additional channels.

## Project Structure

```
automation_gui.py        # Tkinter desktop GUI
run_gui.py                # GUI entry point
run_web_terminal.py       # Web-based terminal entry point
web_terminal/             # Browser terminal frontend (HTML/JS/CSS)
send_youtube_videos.py    # Core: detect new videos, send to Telegram/socials
youtube_metadata.py       # YouTube OAuth + metadata generation
promotion_logic.py        # Cross-posting / promotion rules
refresh_tokens.py          # OAuth token refresh
check_account_status.py   # Account/connection health checks
accounts_config.json      # Per-account routing config (placeholders only)
docs/                      # Setup guides for GUI, multi-account, platform setup
```

## Notes

`accounts_config.json` in this repo contains placeholder values only (e.g. `<YOUR_YOUTUBE_API_KEY>`); real credentials are meant to be supplied via `.env` / local config and are not committed.
