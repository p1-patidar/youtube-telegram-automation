# 🎯 Quick Reference Card

## Launch the GUI
```bash
python run_gui.py
```

---

## Main Menu Options

| Option | What It Does | Time |
|--------|-------------|------|
| **Run Automation** | Schedule unscheduled videos | 5-30 min |
| **Add Account** | Connect YouTube account | 2-5 min |
| **Manage Accounts** | View/edit accounts & data | 1-10 min |
| **Exit** | Close the application | Instant |

---

## Run Automation - 3 Steps

### Step 1: Review Videos
- Shows all unscheduled draft videos
- Lists video IDs
- Confirms you're ready to proceed

### Step 2: Configure
- **Date**: When to start (DD-MM-YYYY)
- **Videos/Day**: How many daily (1-10)
- **Times**: Exact schedule (HH:MM format)

### Step 3: Process
- Click "Start Processing"
- Watch real-time progress
- See success count when done

---

## Time Format Examples

| Input | Valid | Notes |
|-------|-------|-------|
| 09:00 | ✅ | Morning slot |
| 15:00 | ✅ | Afternoon slot |
| 9:00 | ❌ | Use 09:00 format |
| 25:00 | ❌ | Invalid hour |
| 23:59 | ✅ | Almost midnight |

---

## Date Format Examples

| Input | Valid | Notes |
|-------|-------|-------|
| 15-11-2025 | ✅ | DD-MM-YYYY format |
| 11-15-2025 | ❌ | Wrong format |
| 2025-11-15 | ❌ | Wrong format |
| Today's date | ✅ | Auto-filled |

---

## Troubleshooting Quick Fixes

### "No videos found"
- [ ] Check you have draft videos
- [ ] Verify account is connected
- [ ] Refresh the page

### "Can't add account"
- [ ] Verify client_secret.json exists
- [ ] Check internet connection
- [ ] Try refreshing credentials

### "Metadata error"
- [ ] Verify GEMINI_API_KEY in .env
- [ ] Check internet connection
- [ ] Check API quota not exceeded

### "GUI won't start"
- [ ] Ensure all packages installed
- [ ] Run: `pip install -r requirements.txt`
- [ ] Check Python version (3.7+)

---

## File Locations

| What | Where |
|------|-------|
| Launcher | `run_gui.py` |
| GUI Code | `youtube_gui.py` |
| Backend | `youtube_metadata.py` |
| Account Tokens | `youtube_accounts/` folder |
| Video Data | `processed_videos_data/` folder |
| API Keys | `.env` file |
| OAuth Credentials | `client_secret.json` |

---

## Installation Checklist

- [ ] Python 3.7+ installed
- [ ] `pip install -r requirements.txt`
- [ ] `client_secret.json` in same folder
- [ ] `.env` file with GEMINI_API_KEY
- [ ] Run `python run_gui.py`

---

## Common Workflows

### Workflow 1: Add First Account
```
Menu → Add New Account → Enter name → 
  Browser opens → Click "Allow" → Done!
```

### Workflow 2: Schedule Videos
```
Menu → Run Automation → Step 1: Review → 
  Step 2: Set date/time/count → 
  Step 3: Watch it work!
```

### Workflow 3: Check Status
```
Menu → Manage Accounts → Data Management → 
  Select account → View Summary
```

---

## Environment Variables (.env)

```
# Required for metadata generation
GEMINI_API_KEY=your_api_key_here
```

---

## YouTube API Limits

| Operation | Cost | Limit |
|-----------|------|-------|
| Fetch videos | 1 unit | 10,000/day |
| Get captions | 200 units | 10,000/day |
| Update video | 50 units | 10,000/day |

💡 Tip: Schedule 2-3 videos per day to stay within limits

---

## Processing Times

| Task | Time |
|------|------|
| Fetch videos | 2-5s |
| Generate metadata | 3-8s per video |
| Schedule video | 1-2s |
| Full processing | 30s - 5 min (depends on count) |

---

## Status Icons

| Icon | Meaning |
|------|---------|
| ✓ | Success |
| ✗ | Failed |
| ⏰ | Time/Schedule |
| 📝 | Transcript |
| 🤖 | AI/Gemini |
| 📌 | Title/Metadata |
| 📤 | Upload/Schedule |

---

## Important Notes

⚠️ **DO NOT:**
- Share client_secret.json
- Share .env file
- Close GUI during "Step 3"
- Use times in the past
- Use > 10 videos per day

✅ **DO:**
- Keep backups of data
- Test with 1 video first
- Monitor API usage
- Refresh credentials periodically

---

## Documentation Files

| Document | Read Time | Content |
|----------|-----------|---------|
| GUI_QUICKSTART.md | 5 min | Get started |
| GUI_VISUAL_GUIDE.md | 10 min | See the interface |
| GUI_README.md | 20 min | Complete reference |
| PLATFORM_SETUP.md | 15 min | Advanced setup |
| FEATURE_CHECKLIST.md | 10 min | All features |
| README_INDEX.md | 5 min | Documentation map |

---

## Support Resources

1. **Quick Start**: GUI_QUICKSTART.md
2. **Visual Guide**: GUI_VISUAL_GUIDE.md (with diagrams)
3. **Full Docs**: GUI_README.md
4. **Platform Help**: PLATFORM_SETUP.md
5. **Features**: FEATURE_CHECKLIST.md
6. **Navigation**: README_INDEX.md

---

## Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| Tab | Next field |
| Shift+Tab | Previous field |
| Enter | Submit form |
| Esc | Cancel dialog |
| Ctrl+C (Terminal) | Stop process |

---

## Default Values

| Setting | Default |
|---------|---------|
| Videos per day | 1 |
| First slot time | 09:00 |
| Date format | DD-MM-YYYY |
| Time format | HH:MM (24-hour) |
| Data retention | 30 days |
| Duplicate threshold | 95% match |

---

## API Keys Required

| Service | Key | Where to Get |
|---------|-----|--------------|
| YouTube | OAuth file | Google Cloud Console |
| Gemini | GEMINI_API_KEY | Google AI Studio |

---

## System Requirements

- **OS**: macOS, Windows, or Linux
- **Python**: 3.7+
- **RAM**: 512 MB minimum
- **Disk**: 100 MB free space
- **Network**: Internet connection

---

## Contact & Help

1. Read relevant documentation
2. Check troubleshooting section
3. Verify all requirements are met
4. Review error messages carefully

---

## Version Info

- **GUI Version**: 1.0
- **Release**: November 2025
- **Python**: 3.7+
- **Status**: Production Ready ✅

---

## Quick Links

🚀 **Start**: `python run_gui.py`  
📖 **Docs**: See README_INDEX.md  
❓ **Help**: See GUI_README.md  
⚙️ **Setup**: See PLATFORM_SETUP.md  

---

**Print this card for quick reference! 📋**
