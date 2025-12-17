# YouTube Multi-Account Management Guide

## Overview
The YouTube automation script now supports managing multiple YouTube accounts without having to delete authentication files. Each account gets its own token file and processed video database.

## Features

### 🔐 **Account Management**
- **Multiple Accounts**: Store credentials for multiple YouTube channels
- **Account Selection**: Choose which account to work with each time
- **Account Isolation**: Each account has its own processed video database
- **Easy Switching**: No need to delete or backup token files

### 📁 **File Structure**
```
youtube_accounts/
├── token_personal.pickle      # Personal account credentials
├── token_business.pickle      # Business account credentials
└── token_channel2.pickle      # Another account credentials

processed_videos_data/
├── account_UCxxx_processed_videos.json    # Personal account data
├── account_UCyyy_processed_videos.json    # Business account data
└── account_UCzzz_processed_videos.json    # Another account data
```

## How to Use

### 🚀 **Running the Script**
```bash
cd "/Users/pp/Desktop/YOUTUBE TELEGRAM"
"/Users/pp/Desktop/YOUTUBE TELEGRAM/.venv/bin/python" youtube_metadata.py
```

### 📋 **Main Menu Options**

1. **Run automation (schedule videos)**
   - Select an account or add a new one
   - Process and schedule videos for that account
   - All data is saved per account

2. **Manage accounts**
   - View existing accounts
   - Add new accounts
   - Delete accounts
   - Refresh credentials
   - View processed data summaries
   - Cleanup old data

3. **Exit**

### ➕ **Adding a New Account**

1. Choose "Run automation" or "Manage accounts"
2. Select "Add new account" 
3. Enter a descriptive name (e.g., "personal", "business", "gaming")
4. Complete OAuth flow in browser
5. Account is saved and ready to use

### 🔄 **Switching Between Accounts**

Each time you run the automation:
1. Script shows all available accounts with channel names
2. Select the account you want to work with
3. Script loads that account's data and processes videos
4. All scheduling and data is specific to that account

### 🗂️ **Account Data Management**

Each account maintains:
- **Processed Videos**: Complete history of all processed videos
- **Duplicate Detection**: Account-specific duplicate checking
- **Scheduling Data**: When videos were scheduled
- **Metadata History**: Generated titles, descriptions, hashtags

### 🧹 **Maintenance Options**

- **View Data Summary**: See processing statistics for any account
- **Refresh Credentials**: Update expired authentication tokens
- **Cleanup Old Data**: Remove old processed video records
- **Delete Account**: Remove account credentials (data preserved)

## Benefits

✅ **No More Manual Token Management**: Keep multiple accounts without file juggling
✅ **Complete Isolation**: Each account's data is separate and secure
✅ **Easy Account Switching**: Select different accounts for different purposes
✅ **Persistent Data**: All processing history is maintained per account
✅ **Duplicate Prevention**: Works independently for each account
✅ **Flexible Workflow**: Process videos for multiple channels efficiently

## Example Workflow

```
1. Run script
2. Main Menu appears
3. Choose "1. Run automation"
4. Select account:
   - "1. personal - My Personal Channel (UCabc123)"
   - "2. business - My Business Channel (UCdef456)"
   - "3. Add new account"
5. Choose account 1 (personal)
6. Script processes personal channel videos
7. Data saved to personal account database
8. Next time, can easily switch to business account
```

## Troubleshooting

- **"No accounts found"**: Add a new account through the menu
- **"Credentials need refresh"**: Use account management to refresh
- **"Unable to get channel info"**: Check internet connection and try refresh
- **"Account already exists"**: Choose a different name or manage existing account

This multi-account system makes it easy to manage YouTube automation across multiple channels professionally and efficiently! 🎯