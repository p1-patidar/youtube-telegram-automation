# YouTube Shorts Automation Suite - GUI Documentation

## Overview

The GUI version provides a user-friendly interface for the YouTube Shorts automation tool, replacing the terminal-based interaction. It features intuitive dialogs, real-time progress tracking, and comprehensive account management.

## Features

### Main Menu
- **Run Automation** - Schedule unscheduled private videos with AI-generated metadata
- **Add New Account** - Connect a new YouTube account via OAuth
- **Manage Accounts** - View, refresh, and delete accounts; manage processed video data
- **Exit** - Close the application

### Run Automation Workflow

The automation process is split into 3 steps for clarity:

#### Step 1: Review Videos
- Automatically fetches all unscheduled private (draft) videos from your channel
- Displays a list of videos ready for processing
- Shows the total count of videos to be scheduled

#### Step 2: Schedule Settings
Configure how and when videos will be scheduled:
- **Start Date**: Pick the date to begin scheduling (DD-MM-YYYY format)
- **Videos Per Day**: Set how many videos to schedule daily (1-10)
- **Time Slots**: Specify exact times for each video slot
  - Times must be in HH:MM format (24-hour)
  - Times must be in ascending order

#### Step 3: Processing
Real-time monitoring of the automation process:
- **Progress Bar**: Visual representation of completion
- **Live Output**: See detailed logs as each video is processed
- **Status Updates**: Track scheduling, transcript fetching, and metadata generation

### Account Management

#### View Accounts Tab
- Lists all connected accounts with their YouTube channel names
- Shows account status (valid credentials, needs refresh, errors)
- Displays account IDs for reference

#### Account Operations Tab
- **Refresh Credentials**: Update OAuth tokens without re-authenticating
- **Delete Account**: Permanently remove an account (tokens only, data preserved)

#### Data Management Tab
- **View Summary**: See statistics on processed videos per account
  - Total videos processed
  - Successfully scheduled count
  - Detected duplicates
  - Processing errors
  - Recent video history
- **Cleanup Old Data**: Remove processed video records older than a specified number of days

## Installation

### Prerequisites
- Python 3.7+
- macOS, Windows, or Linux
- Google OAuth 2.0 credentials (`client_secret.json`)
- Gemini API key (for metadata generation)

### Setup Steps

1. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure Environment**
   - Create a `.env` file in the same directory as the scripts
   - Add your Gemini API key:
     ```
     GEMINI_API_KEY=your_api_key_here
     ```

3. **Setup Google OAuth**
   - Go to [Google Cloud Console](https://console.cloud.google.com)
   - Create a new project
   - Enable YouTube Data API v3
   - Create OAuth 2.0 credentials (Desktop app type)
   - Download and save as `client_secret.json`

## Running the GUI

### Option 1: Using the Launcher Script
```bash
python run_gui.py
```

### Option 2: Direct Execution
```bash
python youtube_gui.py
```

### Option 3: Terminal Command
```bash
python3 -m youtube_gui
```

## Usage Workflow

### First Time Setup
1. Launch the GUI
2. Click "Add New Account"
3. Enter a descriptive account name (e.g., "personal", "business")
4. Browser will open for Google OAuth authentication
5. Allow the app access to your YouTube account
6. Account is now ready to use

### Scheduling Videos
1. Click "Run Automation"
2. **Step 1**: Review fetched unscheduled videos
3. **Step 2**: Set scheduling parameters:
   - Choose start date
   - Select videos per day
   - Configure time slots
4. **Step 3**: Click "Start Processing"
5. Monitor progress in real-time
6. Processing completes automatically

### Managing Accounts
1. Click "Manage Accounts"
2. Choose from three tabs:
   - **View Accounts**: See all connected accounts
   - **Account Operations**: Refresh or delete accounts
   - **Data Management**: View statistics and cleanup old data

## Features & Capabilities

### Duplicate Detection
- Automatically detects duplicate transcripts
- Compares content similarity (95% threshold)
- Prevents scheduling of duplicate content

### Metadata Generation
- Uses Google's Gemini AI for title, description, and tags
- Generates viral-optimized metadata
- Supports multiple languages (configurable)

### Timezone Handling
- Automatically detects system timezone
- Ensures proper scheduling in your local time
- 30-minute minimum buffer for scheduled videos

### Error Handling
- Gracefully handles API quota limits
- Skips videos with transcript issues
- Preserves processed video data for recovery
- Detailed error messages in output log

### Multi-Account Support
- Manage multiple YouTube accounts simultaneously
- Separate processed video tracking per account
- Individual account credentials and data isolation

## Troubleshooting

### Issue: "tkcalendar" import error
**Solution**: Install the missing package
```bash
pip install tkcalendar
```

### Issue: "No unscheduled private videos found"
**Solution**: 
- Ensure you have draft videos (private, not scheduled)
- Videos must exist in your YouTube Studio
- Check account has proper authentication

### Issue: Metadata generation fails
**Solution**:
- Verify `GEMINI_API_KEY` is set in `.env`
- Check API quota limits
- Ensure internet connection

### Issue: OAuth authentication fails
**Solution**:
- Verify `client_secret.json` exists and is valid
- Check OAuth app is enabled in Google Cloud Console
- Try refreshing credentials from "Account Operations"

### Issue: Videos not scheduling at chosen time
**Solution**:
- Ensure times are 30+ minutes in the future
- Check system timezone is correct
- Verify date format (DD-MM-YYYY)

## File Structure

```
├── youtube_metadata.py         # Core automation logic
├── youtube_gui.py              # GUI implementation
├── run_gui.py                  # Launcher script
├── requirements.txt            # Python dependencies
├── client_secret.json          # Google OAuth credentials
├── .env                        # Environment variables
├── processed_videos_data/      # Stored video metadata
├── youtube_accounts/           # Account tokens
└── token.pickle                # Default account token
```

## Advanced Options

### Customizing Metadata Generation

Edit the prompt in `youtube_metadata.py` function `generate_metadata_with_gemini()` to customize:
- Title format and length
- Description style
- Hashtag strategy
- Target tags

### Adjusting Duplicate Detection

Modify `is_transcript_duplicate()` function parameters:
- `similarity_threshold`: Default 0.95 (95% match)
- Adjust lower for stricter duplicate detection
- Adjust higher for more lenient matching

### Data Cleanup

Use "Cleanup Old Data" to manage storage:
- Remove processed video records
- Keep data for specified number of days
- Preserves recent video history

## API Limits & Quotas

YouTube API quota allocation:
- **Standard**: 10,000 units per day
- Common operations:
  - Fetch captions: 200 units
  - Update video: 50 units
  - List videos: 1 unit

Gemini API:
- **Free tier**: 60 requests per minute
- Monitor usage in Google AI Studio

## Security Notes

- OAuth tokens stored locally in `youtube_accounts/` directory
- Tokens use `.pickle` format with Python serialization
- Credentials are read-only unless refreshed
- Never commit `client_secret.json` or `.env` to version control
- Use `.gitignore` for sensitive files

## Support & Feedback

For issues or feature requests:
1. Check the troubleshooting section
2. Review error messages in the output log
3. Verify all prerequisites are installed
4. Check documentation files

## Version Info

- Current Version: 1.0
- Last Updated: November 2025
- Compatibility: Python 3.7+

---

**Note**: This GUI is built on tkinter, which is included with Python on all platforms. For the best experience on macOS, you may want to install Python via Homebrew or conda rather than the official installer.
