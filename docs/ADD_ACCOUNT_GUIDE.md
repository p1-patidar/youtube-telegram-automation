# Quick Guide: Adding YouTube Accounts

## 🚀 How to Add New YouTube Accounts

You now have **multiple ways** to add new YouTube accounts to your automation system:

### Method 1: Direct from Main Menu (Recommended)
```bash
python youtube_metadata.py
```
1. Choose option **2. Add new account**
2. Enter a descriptive name (e.g., "personal", "business", "gaming")
3. Complete Google OAuth authentication in browser
4. Account is ready to use!

### Method 2: Through Account Management
```bash
python youtube_metadata.py
```
1. Choose option **3. Manage accounts**
2. Choose option **a. Add new account**
3. Enter account name and authenticate
4. Return to management menu for more operations

### Method 3: When No Accounts Exist
If you have no accounts, the system will automatically prompt you to add one.

## 📝 Account Naming Guidelines

✅ **Good names**: `personal`, `business`, `gaming`, `main_channel`, `backup_account`
❌ **Invalid**: Names with spaces, special characters (except - and _)

## 🔐 Authentication Process

1. **Browser Opens**: Google OAuth page will open automatically
2. **Sign In**: Use the Google account associated with your YouTube channel
3. **Grant Permissions**: Allow access to YouTube API
4. **Success**: Account credentials are saved securely

## 📁 What Gets Created

```
youtube_accounts/
└── token_youraccountname.pickle    # Secure credentials

processed_videos_data/
└── account_UCxxxxx_processed_videos.json    # Account's video data
```

## 🎯 Using Multiple Accounts

Once added, accounts appear in the selection menu when you run automation:
```
--- YouTube Account Selection ---
Available accounts:
  1. personal - My Personal Channel (UCabc123)
  2. business - My Business Channel (UCdef456)
  3. gaming - Gaming Channel (UCghi789)
  4. Add new account
  0. Exit
```

## 🔧 Troubleshooting

**"Failed to authenticate"**: 
- Check internet connection
- Try again with correct Google account
- Ensure YouTube channel exists for the Google account

**"Account already exists"**:
- Choose a different name
- Or manage existing account through option 3

**"Browser doesn't open"**:
- Copy the URL from terminal and paste in browser
- Complete authentication manually

## 🎉 Success!

After adding an account, you'll see:
```
✅ Successfully added account!
   Account Name: business
   Channel: My Business Channel
   Channel ID: UCdef456789
   Token saved to: youtube_accounts/token_business.pickle

🎉 You can now select this account when running the automation!
```

Your account is now ready for video automation! 🚀