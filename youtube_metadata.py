import os
import pickle
import datetime
import json
import requests  # For making HTTP requests to Gemini API
import sys  # For sys.exc_info() if needed for deeper debugging
import pytz  # Consider adding to top-level imports
import tzlocal  # <--- Add this import
import hashlib  # For generating content hashes for duplicate detection
import re  # For account name validation

# 2025-12-30
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from dotenv import load_dotenv

load_dotenv()
from googleapiclient.http import MediaFileUpload  # Not used for this script but often for uploads

# --- Configuration ---
CLIENT_SECRETS_FILE = f"client_secret.json"  # Your OAuth 2.0 client secrets file
API_NAME = "youtube"
API_VERSION = "v3"
SCOPES = [
    "https://www.googleapis.com/auth/youtube.readonly",
    "https://www.googleapis.com/auth/youtube",
    "https://www.googleapis.com/auth/youtube.force-ssl"
]
TOKEN_PICKLE_FILE = "token.pickle"  # Default token file
ACCOUNTS_DIR = "youtube_accounts"  # Directory to store multiple account tokens

# Gemini API Configuration
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

GEMINI_API_URL_BASE = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"

# Data Storage Configuration
DATA_STORAGE_DIR = "processed_videos_data"
ACCOUNT_DATA_FILE_TEMPLATE = "account_{}_processed_videos.json"
PROMOTION_CONFIG_FILE = "accounts_config.json"

def load_promotion_config():
    """Load the promotion configuration file."""
    if os.path.exists(PROMOTION_CONFIG_FILE):
        try:
            with open(PROMOTION_CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading promotion config: {e}")
    return {"global": {}, "accounts": []}

def save_promotion_config(config):
    """Save the promotion configuration file."""
    try:
        with open(PROMOTION_CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2)
        return True
    except Exception as e:
        print(f"Error saving promotion config: {e}")
        return False

def get_account_promotion_config(account_name, global_config=None):
    """Get promotion config for a specific account."""
    config = load_promotion_config()
    accounts = config.get("accounts", [])
    
    # Find account config
    account_conf = next((a for a in accounts if a.get("account_name") == account_name), {})
    
    # Merge with global config if provided (or from file)
    if not global_config:
        global_config = config.get("global", {})
        
    # Return merged config (account overrides global)
    merged = global_config.copy()
    merged.update(account_conf)
    return merged


# --- Data Persistence Functions ---
def ensure_data_directory():
    """Ensure the data storage directory exists."""
    if not os.path.exists(DATA_STORAGE_DIR):
        os.makedirs(DATA_STORAGE_DIR)


def get_account_data_file_path(account_id):
    """Get the file path for storing account-specific data."""
    ensure_data_directory()
    filename = ACCOUNT_DATA_FILE_TEMPLATE.format(account_id)
    return os.path.join(DATA_STORAGE_DIR, filename)


def load_processed_videos_data(account_id):
    """Load processed videos data for a specific account."""
    file_path = get_account_data_file_path(account_id)
    try:
        if os.path.exists(file_path):
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception as e:
        print(f"Error loading processed videos data for account {account_id}: {e}")
    return {"videos": {}, "transcript_hashes": {}, "last_updated": None}


def save_processed_videos_data(account_id, data):
    """Save processed videos data for a specific account."""
    file_path = get_account_data_file_path(account_id)
    try:
        data["last_updated"] = datetime.datetime.now().isoformat()
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"Saved processed videos data for account {account_id}")
    except Exception as e:
        print(f"Error saving processed videos data for account {account_id}: {e}")


def generate_transcript_hash(transcript_text):
    """Generate a hash for transcript content to detect duplicates."""
    if not transcript_text:
        return None
    # Normalize the text by removing extra whitespace and converting to lowercase
    normalized_text = ' '.join(transcript_text.lower().split())
    return hashlib.md5(normalized_text.encode('utf-8')).hexdigest()


def is_transcript_duplicate(account_id, transcript_text, similarity_threshold=0.95):
    """Check if transcript is a duplicate of previously processed content."""
    if not transcript_text or transcript_text.strip() == "":
        return False
    
    data = load_processed_videos_data(account_id)
    transcript_hash = generate_transcript_hash(transcript_text)
    
    if transcript_hash in data.get("transcript_hashes", {}):
        duplicate_video_id = data["transcript_hashes"][transcript_hash]
        print(f"Found exact duplicate transcript matching video {duplicate_video_id}")
        return True
    
    # Check for similar content using a simple similarity measure
    normalized_new = ' '.join(transcript_text.lower().split())
    for existing_hash, video_id in data.get("transcript_hashes", {}).items():
        if video_id in data.get("videos", {}):
            existing_transcript = data["videos"][video_id].get("transcript", "")
            if existing_transcript:
                normalized_existing = ' '.join(existing_transcript.lower().split())
                # Simple similarity check based on word overlap
                if len(normalized_new) > 0 and len(normalized_existing) > 0:
                    words_new = set(normalized_new.split())
                    words_existing = set(normalized_existing.split())
                    common_words = words_new.intersection(words_existing)
                    similarity = len(common_words) / max(len(words_new), len(words_existing))
                    if similarity >= similarity_threshold:
                        print(f"Found similar transcript (similarity: {similarity:.2f}) matching video {video_id}")
                        return True
    
    return False


def save_video_data(account_id, video_id, transcript, metadata, scheduled_time=None):
    """Save video data including transcript and metadata."""
    data = load_processed_videos_data(account_id)
    
    transcript_hash = generate_transcript_hash(transcript)
    
    video_entry = {
        "video_id": video_id,
        "transcript": transcript,
        "transcript_hash": transcript_hash,
        "metadata": metadata,
        "processed_timestamp": datetime.datetime.now().isoformat(),
        "scheduled_time": scheduled_time.isoformat() if scheduled_time else None,
        "status": "scheduled" if scheduled_time else "processed"
    }
    
    # Store video data
    data["videos"][video_id] = video_entry
    
    # Store transcript hash for duplicate detection
    if transcript_hash:
        data["transcript_hashes"][transcript_hash] = video_id
    
    save_processed_videos_data(account_id, data)
    print(f"Saved data for video {video_id}")


def get_account_id_from_service(youtube_service):
    """Get the account/channel ID from the YouTube service."""
    try:
        request = youtube_service.channels().list(part="id", mine=True)
        response = request.execute()
        if response.get("items"):
            channel_id = response["items"][0]["id"]
            print(f"Detected account/channel ID: {channel_id}")
            return channel_id
    except Exception as e:
        print(f"Error getting account ID: {e}")
    # Fallback to a generic identifier
    return "default_account"


def view_processed_data_summary(account_id):
    """Display a summary of processed video data for an account."""
    data = load_processed_videos_data(account_id)
    videos = data.get("videos", {})
    
    if not videos:
        print(f"No processed videos found for account {account_id}")
        return
    
    print(f"\n--- Processed Videos Summary for Account {account_id} ---")
    print(f"Total processed videos: {len(videos)}")
    
    # Count by status
    scheduled_count = sum(1 for v in videos.values() if v.get("status") == "scheduled")
    duplicate_count = sum(1 for v in videos.values() if "Duplicate" in v.get("metadata", {}).get("title", ""))
    error_count = sum(1 for v in videos.values() if "Error" in v.get("metadata", {}).get("title", ""))
    
    print(f"  Successfully scheduled: {scheduled_count}")
    print(f"  Duplicates detected: {duplicate_count}")
    print(f"  Processing errors: {error_count}")
    print(f"  Last updated: {data.get('last_updated', 'Unknown')}")
    
    # Show recent videos
    recent_videos = list(videos.items())[-5:]  # Last 5 videos
    print(f"\nRecent videos:")
    for video_id, video_data in recent_videos:
        title = video_data.get("metadata", {}).get("title", "No title")[:50]
        status = video_data.get("status", "unknown")
        timestamp = video_data.get("processed_timestamp", "Unknown")[:19]  # Remove microseconds
        print(f"  {video_id}: {title}... (Status: {status}, Processed: {timestamp})")


def cleanup_old_data(account_id, days_to_keep=30):
    """Clean up old processed video data (optional maintenance function)."""
    data = load_processed_videos_data(account_id)
    videos = data.get("videos", {})
    
    if not videos:
        return
    
    cutoff_date = datetime.datetime.now() - datetime.timedelta(days=days_to_keep)
    videos_to_remove = []
    
    for video_id, video_data in videos.items():
        processed_time_str = video_data.get("processed_timestamp")
        if processed_time_str:
            try:
                processed_time = datetime.datetime.fromisoformat(processed_time_str.replace('Z', '+00:00'))
                if processed_time < cutoff_date:
                    videos_to_remove.append(video_id)
            except Exception:
                continue
    
    if videos_to_remove:
        print(f"Removing {len(videos_to_remove)} old video records (older than {days_to_keep} days)")
        for video_id in videos_to_remove:
            # Remove from transcript hashes too
            video_hash = videos[video_id].get("transcript_hash")
            if video_hash and video_hash in data.get("transcript_hashes", {}):
                del data["transcript_hashes"][video_hash]
            del videos[video_id]
        
        save_processed_videos_data(account_id, data)
        print(f"Cleanup complete. Removed {len(videos_to_remove)} old records.")
    else:
        print("No old records to clean up.")


def add_account_standalone():
    """Standalone function to add a new account."""
    print("\n🔐 Add New YouTube Account")
    print("=" * 30)
    
    available_accounts = list_available_accounts()
    
    if available_accounts:
        print("Existing accounts:")
        for account in available_accounts:
            if account == "default":
                token_file = TOKEN_PICKLE_FILE
            else:
                token_file = get_account_token_file(account)
            
            try:
                with open(token_file, "rb") as f:
                    creds = pickle.load(f)
                    if creds and creds.valid:
                        channel_id, channel_title = get_account_info(creds)
                        if channel_title:
                            print(f"  - {account}: {channel_title} ({channel_id})")
                        else:
                            print(f"  - {account}: (Unable to get channel info)")
            except Exception:
                print(f"  - {account}: (Error reading credentials)")
        print()
    
    while True:
        account_name = input("Enter a name for the new account (e.g., 'personal', 'business'): ").strip()
        if not account_name:
            print("❌ Account name cannot be empty.")
            continue
        if account_name in available_accounts:
            print(f"❌ Account '{account_name}' already exists. Please choose a different name.")
            continue
        if not re.match(r'^[a-zA-Z0-9_-]+$', account_name):
            print("❌ Account name can only contain letters, numbers, hyphens, and underscores.")
            continue
        break
    
    print(f"\n🚀 Setting up new account: {account_name}")
    print("📱 This will open a browser window for Google OAuth authentication...")
    print("   Please complete the authentication in your browser.")
    
    try:
        creds = authenticate_account(account_name)
        if creds:
            # Verify the account was set up correctly
            channel_id, channel_title = get_account_info(creds)
            if channel_title:
                print(f"\n✅ Successfully added account!")
                print(f"   Account Name: {account_name}")
                print(f"   Channel: {channel_title}")
                print(f"   Channel ID: {channel_id}")
                print(f"   Token saved to: {get_account_token_file(account_name)}")
                print(f"\n🎉 You can now select this account when running the automation!")
                return True
            else:
                print(f"⚠️  Account added but unable to verify channel information.")
                print(f"   Token saved to: {get_account_token_file(account_name)}")
                return True
        else:
            print("❌ Failed to authenticate new account.")
            return False
    except Exception as e:
        print(f"❌ Error adding account: {e}")
        return False


def manage_accounts():
    """Account management utility function."""
    while True:
        print("\n--- Account Management ---")
        available_accounts = list_available_accounts()
        
        if not available_accounts:
            print("No accounts found.")
            add_new = input("Would you like to add a new account? (yes/no): ").lower()
            if add_new == 'yes':
                # Add new account directly
                while True:
                    account_name = input("Enter a name for the new account (e.g., 'personal', 'business'): ").strip()
                    if not account_name:
                        print("Account name cannot be empty.")
                        continue
                    if not re.match(r'^[a-zA-Z0-9_-]+$', account_name):
                        print("Account name can only contain letters, numbers, hyphens, and underscores.")
                        continue
                    break
                
                print(f"Setting up new account: {account_name}")
                print("This will open a browser window for Google OAuth authentication...")
                
                try:
                    creds = authenticate_account(account_name)
                    if creds:
                        channel_id, channel_title = get_account_info(creds)
                        if channel_title:
                            print(f"✅ Successfully added account: {account_name}")
                            print(f"   Channel: {channel_title}")
                            print(f"   ID: {channel_id}")
                            print(f"   Token saved to: {get_account_token_file(account_name)}")
                            continue  # Continue the loop to show the menu again
                        else:
                            print(f"⚠️  Account added but unable to verify channel information.")
                    else:
                        print("❌ Failed to authenticate new account.")
                except Exception as e:
                    print(f"Error adding account: {e}")
            else:
                return
        
        print("Available accounts:")
        for i, account in enumerate(available_accounts, 1):
            # Get account info for display
            if account == "default":
                token_file = TOKEN_PICKLE_FILE
            else:
                token_file = get_account_token_file(account)
            
            try:
                with open(token_file, "rb") as f:
                    creds = pickle.load(f)
                    if creds and creds.valid:
                        channel_id, channel_title = get_account_info(creds)
                        if channel_title:
                            print(f"  {i}. {account} - {channel_title} ({channel_id})")
                        else:
                            print(f"  {i}. {account} - (Unable to get channel info)")
                    else:
                        print(f"  {i}. {account} - (Credentials need refresh)")
            except Exception as e:
                print(f"  {i}. {account} - (Error reading credentials)")
        
        print("\nOptions:")
        print("  a. Add new account")
        print("  v. View account data summary")
        print("  d. Delete account")
        print("  r. Refresh account credentials")
        print("  c. Cleanup old data")
        print("  b. Back to main menu")
        
        choice = input("\nEnter choice: ").lower().strip()
        
        if choice == 'b':
            break
        elif choice == 'a':
            # Add new account
            print("\n--- Add New Account ---")
            available_accounts = list_available_accounts()
            
            while True:
                account_name = input("Enter a name for the new account (e.g., 'personal', 'business'): ").strip()
                if not account_name:
                    print("Account name cannot be empty.")
                    continue
                if account_name in available_accounts:
                    print(f"Account '{account_name}' already exists. Please choose a different name.")
                    continue
                if not re.match(r'^[a-zA-Z0-9_-]+$', account_name):
                    print("Account name can only contain letters, numbers, hyphens, and underscores.")
                    continue
                break
            
            print(f"Setting up new account: {account_name}")
            print("This will open a browser window for Google OAuth authentication...")
            
            try:
                creds = authenticate_account(account_name)
                if creds:
                    # Verify the account was set up correctly
                    channel_id, channel_title = get_account_info(creds)
                    if channel_title:
                        print(f"✅ Successfully added account: {account_name}")
                        print(f"   Channel: {channel_title}")
                        print(f"   ID: {channel_id}")
                        print(f"   Token saved to: {get_account_token_file(account_name)}")
                    else:
                        print(f"⚠️  Account added but unable to verify channel information.")
                else:
                    print("❌ Failed to authenticate new account.")
            except Exception as e:
                print(f"Error adding account: {e}")
                
        elif choice == 'v':
            account_choice = input("Enter account name to view: ").strip()
            if account_choice in available_accounts:
                # Get the channel ID for this account
                try:
                    if account_choice == "default":
                        token_file = TOKEN_PICKLE_FILE
                    else:
                        token_file = get_account_token_file(account_choice)
                    
                    with open(token_file, "rb") as f:
                        creds = pickle.load(f)
                        channel_id, _ = get_account_info(creds)
                        if channel_id:
                            view_processed_data_summary(channel_id)
                        else:
                            print("Could not retrieve channel ID for this account.")
                except Exception as e:
                    print(f"Error viewing account data: {e}")
            else:
                print("Account not found.")
        
        elif choice == 'd':
            account_choice = input("Enter account name to delete: ").strip()
            if account_choice in available_accounts:
                confirm = input(f"Are you sure you want to delete account '{account_choice}'? (yes/no): ").lower()
                if confirm == 'yes':
                    try:
                        if account_choice == "default":
                            if os.path.exists(TOKEN_PICKLE_FILE):
                                os.remove(TOKEN_PICKLE_FILE)
                                print(f"Deleted default account token file.")
                        else:
                            token_file = get_account_token_file(account_choice)
                            if os.path.exists(token_file):
                                os.remove(token_file)
                                print(f"Deleted account '{account_choice}' token file.")
                        
                        # Note: We don't delete the processed video data in case user wants to keep it
                        print("Note: Processed video data is preserved. Use cleanup option if you want to remove it.")
                    except Exception as e:
                        print(f"Error deleting account: {e}")
                else:
                    print("Deletion cancelled.")
            else:
                print("Account not found.")
        
        elif choice == 'r':
            account_choice = input("Enter account name to refresh: ").strip()
            if account_choice in available_accounts:
                print(f"Refreshing credentials for account: {account_choice}")
                try:
                    creds = authenticate_account(account_choice)
                    if creds:
                        channel_id, channel_title = get_account_info(creds)
                        if channel_title:
                            print(f"✅ Successfully refreshed: {account_choice} - {channel_title}")
                        else:
                            print("✅ Credentials refreshed but unable to verify channel info.")
                    else:
                        print("❌ Failed to refresh credentials.")
                except Exception as e:
                    print(f"Error refreshing account: {e}")
            else:
                print("Account not found.")
        
        elif choice == 'c':
            account_choice = input("Enter account name to cleanup: ").strip()
            if account_choice in available_accounts:
                try:
                    # Get channel ID for the account
                    if account_choice == "default":
                        token_file = TOKEN_PICKLE_FILE
                    else:
                        token_file = get_account_token_file(account_choice)
                    
                    with open(token_file, "rb") as f:
                        creds = pickle.load(f)
                        channel_id, _ = get_account_info(creds)
                        if channel_id:
                            days = input("Enter days to keep (default 30): ").strip()
                            days_to_keep = int(days) if days.isdigit() else 30
                            cleanup_old_data(channel_id, days_to_keep)
                        else:
                            print("Could not retrieve channel ID for cleanup.")
                except Exception as e:
                    print(f"Error during cleanup: {e}")
            else:
                print("Account not found.")
        else:
            print("Invalid choice.")


class QuotaExceededError(Exception):
    """Custom exception for YouTube API quota exhaustion."""
    pass


def is_youtube_quota_error(error):
    """Checks if an HttpError is due to YouTube API quota exhaustion."""
    if isinstance(error, HttpError) and error.resp.status == 403:
        try:
            error_details = json.loads(error.content.decode())
            if "error" in error_details and "errors" in error_details["error"]:
                for err_item in error_details["error"]["errors"]:
                    if err_item.get("reason") == "quotaExceeded":
                        return True
            # Fallback check if structured reason is not found but message indicates quota issue
            if "quotaexceeded" in str(error.content).lower() or "quota" in str(error.content).lower():
                return True
        except (json.JSONDecodeError, UnicodeDecodeError, AttributeError):
            # If content isn't JSON or cannot be decoded, check raw content string
            if "quotaexceeded" in str(error.content).lower() or "quota" in str(error.content).lower():
                return True
    return False


# --- YouTube API Authentication ---
def ensure_accounts_directory():
    """Ensure the accounts directory exists."""
    if not os.path.exists(ACCOUNTS_DIR):
        os.makedirs(ACCOUNTS_DIR)
        print(f"Created accounts directory: {ACCOUNTS_DIR}")


def get_account_token_file(account_name):
    """Get the token file path for a specific account."""
    ensure_accounts_directory()
    return os.path.join(ACCOUNTS_DIR, f"token_{account_name}.pickle")


def list_available_accounts():
    """List all available authenticated accounts."""
    ensure_accounts_directory()
    accounts = []
    
    # Check for token files in accounts directory
    if os.path.exists(ACCOUNTS_DIR):
        for file in os.listdir(ACCOUNTS_DIR):
            if file.startswith("token_") and file.endswith(".pickle"):
                account_name = file[6:-7]  # Remove "token_" prefix and ".pickle" suffix
                accounts.append(account_name)
    
    # Check for default token file
    if os.path.exists(TOKEN_PICKLE_FILE):
        accounts.append("default")
    
    return sorted(accounts)


def get_account_info(creds):
    """Get account information from credentials."""
    try:
        service = build(API_NAME, API_VERSION, credentials=creds)
        request = service.channels().list(part="snippet", mine=True)
        response = request.execute()
        
        if response.get("items"):
            channel = response["items"][0]
            channel_id = channel["id"]
            channel_title = channel["snippet"]["title"]
            return channel_id, channel_title
        return None, None
    except Exception as e:
        print(f"Error getting account info: {e}")
        return None, None


def authenticate_account(account_name=None):
    """Authenticate a specific account or create a new one."""
    if account_name and account_name != "default":
        token_file = get_account_token_file(account_name)
    else:
        token_file = TOKEN_PICKLE_FILE
    
    creds = None
    if os.path.exists(token_file):
        with open(token_file, "rb") as token:
            creds = pickle.load(token)
    
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
                print(f"Refreshed credentials for account: {account_name or 'default'}")
            except Exception as e:
                print(f"Failed token refresh for {account_name or 'default'}: {e}. Re-authenticating...")
                creds = None
        
        if not creds:
            print(f"Starting OAuth flow for account: {account_name or 'default'}")
            flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRETS_FILE, SCOPES)
            creds = flow.run_local_server(port=0)
        
        # Save credentials
        with open(token_file, "wb") as token:
            pickle.dump(creds, token)
            print(f"Credentials saved to: {token_file}")
    
    return creds


def select_or_add_account():
    """Allow user to select an existing account or add a new one."""
    available_accounts = list_available_accounts()
    
    print("\n--- YouTube Account Selection ---")
    
    if available_accounts:
        print("Available accounts:")
        for i, account in enumerate(available_accounts, 1):
            # Get account info for display
            if account == "default":
                token_file = TOKEN_PICKLE_FILE
            else:
                token_file = get_account_token_file(account)
            
            try:
                with open(token_file, "rb") as f:
                    creds = pickle.load(f)
                    if creds and creds.valid:
                        channel_id, channel_title = get_account_info(creds)
                        if channel_title:
                            print(f"  {i}. {account} - {channel_title} ({channel_id})")
                        else:
                            print(f"  {i}. {account} - (Unable to get channel info)")
                    else:
                        print(f"  {i}. {account} - (Credentials need refresh)")
            except Exception as e:
                print(f"  {i}. {account} - (Error reading credentials)")
        
        print(f"  {len(available_accounts) + 1}. Add new account")
        print("  0. Exit")
        
        while True:
            try:
                choice = input(f"\nSelect account (1-{len(available_accounts) + 1}, or 0 to exit): ").strip()
                choice_num = int(choice)
                
                if choice_num == 0:
                    print("Exiting...")
                    return None, None
                elif 1 <= choice_num <= len(available_accounts):
                    selected_account = available_accounts[choice_num - 1]
                    print(f"Selected account: {selected_account}")
                    creds = authenticate_account(selected_account)
                    return selected_account, creds
                elif choice_num == len(available_accounts) + 1:
                    # Add new account
                    break
                else:
                    print("Invalid choice. Please try again.")
            except ValueError:
                print("Please enter a valid number.")
    else:
        print("No existing accounts found.")
        add_new = input("Would you like to add a new account? (yes/no): ").lower()
        if add_new != 'yes':
            print("Exiting...")
            return None, None
    
    # Add new account
    while True:
        account_name = input("\nEnter a name for the new account (e.g., 'personal', 'business'): ").strip()
        if not account_name:
            print("Account name cannot be empty.")
            continue
        if account_name in available_accounts:
            print(f"Account '{account_name}' already exists. Please choose a different name.")
            continue
        if not re.match(r'^[a-zA-Z0-9_-]+$', account_name):
            print("Account name can only contain letters, numbers, hyphens, and underscores.")
            continue
        break
    
    print(f"Setting up new account: {account_name}")
    creds = authenticate_account(account_name)
    
    if creds:
        # Verify the account was set up correctly
        channel_id, channel_title = get_account_info(creds)
        if channel_title:
            print(f"✅ Successfully added account: {account_name} - {channel_title} ({channel_id})")
        else:
            print(f"⚠️  Account added but unable to verify channel information.")
        return account_name, creds
    else:
        print("Failed to authenticate new account.")
        return None, None


def get_authenticated_service():
    """Get authenticated service with account selection."""
    account_name, creds = select_or_add_account()
    
    if not creds:
        print("Authentication failed or cancelled.")
        return None, None
    
    try:
        service = build(API_NAME, API_VERSION, credentials=creds)
        return service, account_name
    except Exception as e:
        print(f"Error building YouTube service: {e}")
        return None, None


# --- Fetching Unscheduled Private Video IDs ---
def get_my_unscheduled_private_video_ids(youtube_service):
    """
    Fetches video IDs that are private AND not scheduled for publication.
    Excludes videos that already have a publishAt date set.
    """
    print("Fetching your unscheduled private video IDs...")
    unscheduled_private_video_ids, next_page_token, max_results = [], None, 50
    try:
        while True:
            search_req = youtube_service.search().list(part="id", forMine=True, type="video", maxResults=max_results,
                                                       pageToken=next_page_token)
            search_res = search_req.execute()
            ids_on_page = [item["id"]["videoId"] for item in search_res.get("items", []) if
                           item.get("id", {}).get("kind") == "youtube#video"]
            if ids_on_page:
                # Get both status and snippet to check privacy and scheduling
                videos_list_req = youtube_service.videos().list(part="status,snippet", id=",".join(ids_on_page))
                videos_list_res = videos_list_req.execute()
                for item in videos_list_res.get("items", []):
                    status = item.get("status", {})
                    snippet = item.get("snippet", {})

                    # Check if video is private and NOT scheduled
                    is_private = status.get("privacyStatus") == "private"
                    publish_at = status.get("publishAt")  # This will be None/null if not scheduled

                    if is_private and not publish_at:
                        unscheduled_private_video_ids.append(item["id"])
                        print(
                            f"  Found unscheduled private video: {item['id']} - '{snippet.get('title', 'No Title')[:50]}...'")
                    elif is_private and publish_at:
                        print(f"  Skipping already scheduled video: {item['id']} - scheduled for {publish_at}")

            next_page_token = search_res.get("nextPageToken")
            if not next_page_token: break

        print(
            f"Found {len(unscheduled_private_video_ids)} unscheduled private videos." if unscheduled_private_video_ids else "No unscheduled private videos found.")
        return unscheduled_private_video_ids
    except Exception as e:
        print(f"Error fetching unscheduled private videos: {e}");
        return []


def get_video_transcript(youtube_service, video_id):
    print(f"Fetching transcript for video ID: {video_id}...")
    try:
        try:
            captions = youtube_service.captions().list(part="snippet", videoId=video_id).execute()
        except HttpError as e_list:
            if is_youtube_quota_error(e_list):
                print(f"Quota exceeded during captions.list for {video_id}.")
                raise QuotaExceededError(f"Quota exceeded at captions.list for {video_id}") from e_list
            # Re-raise other HttpErrors or handle as per original logic for non-quota caption list errors
            print(f"HttpError listing captions for {video_id}: {e_list}");
            return None

        if not captions.get("items"): print(f"No caption tracks for {video_id}."); return None
        cap_id = next(
            (i["id"] for l_pref in ["en", "en-US"] for i in captions["items"] if i["snippet"]["language"] == l_pref),
            None)
        if not cap_id and captions["items"]: cap_id = captions["items"][0]["id"]; print(
            f"Using lang: {captions['items'][0]['snippet']['language']}")

        if cap_id:
            # Attempt SRT
            try:
                srt_raw_content = youtube_service.captions().download(id=cap_id, tfmt="srt").execute()
                parsed_srt = parse_srt_to_text(srt_raw_content)
                # Check if parsing was successful (not just non-empty, but didn't return the error string)
                if "Error decoding SRT" not in parsed_srt and parsed_srt.strip():
                    return parsed_srt
                else:
                    print(f"SRT parsing failed or empty for {video_id}. Trying VTT...")
            except HttpError as e_srt:
                if is_youtube_quota_error(e_srt):
                    print(f"Quota exceeded during SRT download for {video_id}.")
                    raise QuotaExceededError(f"Quota exceeded at SRT download for {video_id}") from e_srt
                print(
                    f"SRT download failed (non-quota HttpError: {e_srt.resp.status if hasattr(e_srt, 'resp') else 'N/A'}). Trying VTT...")
            except Exception as e_parse_srt:  # Catch other errors during SRT processing
                print(f"Error processing SRT for {video_id}: {e_parse_srt}. Trying VTT...")

            # Attempt VTT if SRT was not successful
            print(f"Attempting VTT download for {video_id}...")  # Explicitly state VTT attempt
            try:
                vtt_raw_content = youtube_service.captions().download(id=cap_id, tfmt="vtt").execute()
                return parse_vtt_to_text(vtt_raw_content)
            except HttpError as e_vtt:
                if is_youtube_quota_error(e_vtt):
                    print(f"Quota exceeded during VTT download for {video_id}.")
                    raise QuotaExceededError(f"Quota exceeded at VTT download for {video_id}") from e_vtt
                print(
                    f"VTT download failed for {video_id} (non-quota HttpError: {e_vtt.resp.status if hasattr(e_vtt, 'resp') else 'N/A'}). No transcript.");
                return None
            except Exception as e_parse_vtt:
                print(f"Error processing VTT for {video_id}: {e_parse_vtt}. No transcript.");
                return None
        else:
            print(f"No suitable caption ID found for {video_id}.");
            return None
    except QuotaExceededError:  # Ensure it propagates
        raise
    except Exception as e_general:  # Catch any other unexpected errors
        print(f"An unexpected error occurred in get_video_transcript for {video_id}: {e_general}");
        return None


def parse_srt_to_text(content):
    if not isinstance(content, str):
        try:
            content = content.decode('utf-8')
        except UnicodeDecodeError:  # More specific exception
            try:
                content = content.decode('latin-1');
                print("Decoded SRT with latin-1")
            except Exception as e_decode:
                print(f"Could not decode SRT: {e_decode}");
                return "Error decoding SRT"  # More specific error message
        except Exception as e_gen_decode:
            print(f"Error decoding SRT content: {e_gen_decode}");
            return "Error decoding SRT"
    return " ".join(
        [l.strip() for l in content.splitlines() if l.strip() and not l.strip().isdigit() and "-->" not in l])


def parse_vtt_to_text(content):
    if not isinstance(content, str):
        try:
            content = content.decode('utf-8')
        except UnicodeDecodeError:  # More specific exception
            try:
                content = content.decode('latin-1');
                print("Decoded VTT with latin-1")
            except Exception as e_decode:
                print(f"Could not decode VTT: {e_decode}");
                return "Error decoding VTT"  # More specific error message
        except Exception as e_gen_decode:
            print(f"Error decoding VTT content: {e_gen_decode}");
            return "Error decoding VTT"
    lines, text_lines, in_cue = content.splitlines(), [], False
    if not lines or "WEBVTT" not in lines[0]: print(
        "Warning: Not VTT format. Attempting generic text extraction."); return " ".join([l.strip() for l in lines if
                                                                                          l.strip() and "-->" not in l and not l.strip().isdigit() and not any(
                                                                                              h in l for h in
                                                                                              ["Kind:", "Language:",
                                                                                               "Style:",
                                                                                               "NOTE"])])  # Corrected "Lang:" to "Language:"
    for line in lines:
        line = line.strip()
        if not line: in_cue = False; continue
        if any(h in line for h in ["WEBVTT", "NOTE", "STYLE"]): continue
        if "-->" in line: in_cue = True; continue
        if in_cue and line: text_lines.append(line)
    return " ".join(text_lines)


# --- Metadata Generation (Gemini API) ---

# Track blocked providers to skip on subsequent calls
_blocked_providers = {
    "gemini_primary": False,
    "gemini_backup": False,
    "openai": False,
    "last_working": None  # Remember last working provider
}

def generate_metadata_with_gemini(transcript_text):
    global _blocked_providers
    
    # If we have a known working provider, try it first
    if _blocked_providers.get("last_working") == "ollama":
        print("  🏠 Using cached Ollama (previous providers were rate-limited)...")
        result = _try_ollama(transcript_text)
        if result:
            return result
    
    print("Attempting metadata generation...")
    
    # Get both primary and backup API keys
    primary_key = GEMINI_API_KEY
    backup_key = os.getenv("GEMINI_API_KEY_BACKUP")
    api_keys = []
    if primary_key and not _blocked_providers.get("gemini_primary"):
        api_keys.append(("gemini_primary", primary_key))
    if backup_key and not _blocked_providers.get("gemini_backup"):
        api_keys.append(("gemini_backup", backup_key))
    
    if not api_keys and not os.getenv("OPENAI_API_KEY"): 
        print("ERROR: All API keys missing or blocked.")
        return _try_ollama(transcript_text) or {"title": "Placeholder - API Key Missing", "description": "...", "hashtags": [], "tags": []}
    
    if not transcript_text or transcript_text.strip() == "" or "Error decoding" in transcript_text: 
        print(f"Transcript issue: '{transcript_text[:50]}...'")
        return {"title": "Title (Transcript Issue)", "description": "...", "hashtags": [], "tags": []}

    prompt = f"""Analyze this YouTube Short transcript and generate viral-optimized metadata in hindi:

    CONTENT ANALYSIS FIRST:
    - What's the main hook/value proposition?
    - Content type: Educational, Entertainment, Comedy, Lifestyle, etc.
    - Target audience demographics
    - Key moments/highlights

    TITLE GENERATION (max 70 chars, choose BEST option):
    Use viral formulas like:
    - Curiosity gaps: "This changed everything about..."
    - Numbers: "3 secrets that..."
    - Questions: "Why do people..."
    - Shock value: "Nobody talks about..."
    - Before/After: "From X to Y in..."
    - Controversy: "The truth about..."
    - Urgency: "Stop doing this..."

    DESCRIPTION (max 250 chars):
    - Hook in first line
    - Clear value/entertainment promise
    - 2-3 relevant trending keywords naturally integrated
    - Call-to-action (follow, like, share)
    - End with #shorts

    HASHTAGS (5-7 total):
    - Always start with #shorts
    - 2-3 trending hashtags (broad reach)
    - 2-3 niche-specific hashtags (targeted)
    - 1 branded/unique hashtag if applicable

    TAGS (15 total):
    - Mix of broad trending keywords
    - Specific niche terms
    - Competitor analysis terms
    - Long-tail keywords
    - Content-type descriptors

    CURRENT TRENDS TO CONSIDER:
    - What's trending in this niche?
    - Seasonal relevance
    - Pop culture references
    - Current events connections

    Transcript: --- {transcript_text[:25000]} ---

    Return ONLY valid JSON with viral-optimized metadata: {{"title": "T", "description": "D", "hashtags": ["#H"], "tags": ["T"]}}"""


    payload = {"contents": [{"parts": [{"text": prompt}]}], "generationConfig": {"responseMimeType": "application/json",
                                                                                 "responseSchema": {"type": "OBJECT",
                                                                                                    "properties": {
                                                                                                        "title": {
                                                                                                            "type": "STRING"},
                                                                                                        "description": {
                                                                                                            "type": "STRING"},
                                                                                                        "hashtags": {
                                                                                                            "type": "ARRAY",
                                                                                                            "items": {
                                                                                                                "type": "STRING"}},
                                                                                                        "tags": {
                                                                                                            "type": "ARRAY",
                                                                                                            "items": {
                                                                                                                "type": "STRING"}}},
                                                                                                    "required": [
                                                                                                        "title",
                                                                                                        "description",
                                                                                                        "hashtags",
                                                                                                        "tags"]}}}
    headers = {'Content-Type': 'application/json'}
    
    # Try each API key with retries
    for provider_name, api_key in api_keys:
        key_label = "primary" if "primary" in provider_name else "backup"
        url = f"{GEMINI_API_URL_BASE}?key={api_key}"
        
        max_retries = 2
        for attempt in range(max_retries):
            try:
                resp = requests.post(url, headers=headers, json=payload, timeout=90)
                resp.raise_for_status()
                data = resp.json()
                if data.get("candidates") and data["candidates"][0].get("content", {}).get("parts", [{}])[0].get("text"):
                    meta = json.loads(data["candidates"][0]["content"]["parts"][0]["text"])
                    if not all(k in meta for k in ["title", "description", "hashtags", "tags"]) or not isinstance(
                            meta.get("hashtags"), list) or not isinstance(meta.get("tags"), list) or not meta.get(
                        "title") or not meta.get("description"): raise ValueError("Incomplete Gemini data")
                    print(f"Metadata generated (using Gemini {key_label}).")
                    _blocked_providers["last_working"] = provider_name
                    return meta
                else:
                    raise ValueError(f"Unexpected Gemini response: {data.get('promptFeedback', data)}")
            except requests.exceptions.HTTPError as e:
                if e.response.status_code == 429:
                    if attempt < max_retries - 1:
                        wait_time = (attempt + 1) * 10
                        print(f"  ⏳ Rate limited ({key_label}). Waiting {wait_time}s...")
                        import time
                        time.sleep(wait_time)
                        continue
                    else:
                        print(f"  ⚠️ {key_label.title()} key rate-limited. Marking as blocked...")
                        _blocked_providers[provider_name] = True
                        break  # Try next API key
                else:
                    print(f"Gemini error: {e}")
                    break  # Try OpenAI fallback
            except Exception as e:
                print(f"Gemini error: {e}")
                break  # Try OpenAI fallback
    
    # Try OpenAI as fallback
    openai_key = os.getenv("OPENAI_API_KEY")
    if openai_key and not _blocked_providers.get("openai"):
        print("  🔄 Trying OpenAI as fallback...")
        try:
            import openai
            client = openai.OpenAI(api_key=openai_key)
            
            openai_prompt = f"""Analyze this YouTube Short transcript and generate viral-optimized metadata in Hindi.

Transcript: {transcript_text[:8000]}

Return ONLY valid JSON with:
{{"title": "catchy title max 70 chars", "description": "engaging description max 250 chars", "hashtags": ["#shorts", "#tag1", "#tag2"], "tags": ["tag1", "tag2", ...]}}"""

            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": openai_prompt}],
                response_format={"type": "json_object"}
            )
            
            meta = json.loads(response.choices[0].message.content)
            if all(k in meta for k in ["title", "description", "hashtags", "tags"]):
                print("Metadata generated (using OpenAI).")
                _blocked_providers["last_working"] = "openai"
                return meta
        except Exception as e:
            error_str = str(e)
            if "429" in error_str or "rate" in error_str.lower():
                _blocked_providers["openai"] = True
            print(f"  OpenAI error: {e}")
    
    # Try local Ollama as final fallback
    result = _try_ollama(transcript_text)
    if result:
        _blocked_providers["last_working"] = "ollama"
        return result
    
    print("  ❌ All providers exhausted (including local)")
    return {"title": "Fallback - All APIs Failed", "description": "...", "hashtags": [], "tags": []}


def _try_ollama(transcript_text):
    """Try local Ollama as fallback"""
    print("  🏠 Trying local Ollama (llama3.2:1b)...")
    try:
        ollama_url = "http://localhost:11434/api/generate"
        ollama_prompt = f"""Generate YouTube metadata in Hindi for this transcript.

Transcript: {transcript_text[:4000]}

Return ONLY valid JSON with these exact keys:
{{"title": "catchy title max 70 chars", "description": "engaging description max 250 chars", "hashtags": ["#shorts", "#tag1"], "tags": ["tag1", "tag2"]}}"""

        ollama_payload = {
            "model": "llama3.2:1b",
            "prompt": ollama_prompt,
            "stream": False,
            "format": "json"
        }
        
        resp = requests.post(ollama_url, json=ollama_payload, timeout=120)
        if resp.status_code == 200:
            result = resp.json()
            meta = json.loads(result.get("response", "{}"))
            if all(k in meta for k in ["title", "description", "hashtags", "tags"]):
                print("Metadata generated (using local Ollama).")
                return meta
    except Exception as e:
        print(f"  Ollama error: {e}")
    return None


def update_and_schedule_video(youtube_service, video_id, metadata, publish_at_datetime):
    print(f"\nUpdating/scheduling {video_id}: Title: {metadata['title']}")
    # ... (datetime and description logic remains the same) ...
    if publish_at_datetime.tzinfo is None:  # Ensure publish_at_datetime is timezone-aware
        # Assuming publish_at_datetime should be in local time, convert to UTC for API
        local_tz = datetime.datetime.now(datetime.timezone.utc).astimezone().tzinfo  # Get local timezone
        aware_local_dt = pytz.timezone(str(local_tz)).localize(publish_at_datetime)
        utc_dt = aware_local_dt.astimezone(datetime.timezone.utc)
    else:  # Already timezone-aware
        utc_dt = publish_at_datetime.astimezone(datetime.timezone.utc)
    iso_ts = utc_dt.isoformat().replace('+00:00', 'Z')  # Ensure 'Z' for UTC
    print(f"  Local Schedule: {publish_at_datetime:%Y-%m-%d %H:%M:%S %Z%z}, UTC ISO: {iso_ts}")

    full_desc = metadata['description']
    existing_hashtags = {tag.lower() for tag in full_desc.split() if tag.startswith('#')}
    if "#shorts" not in existing_hashtags:  # Check against normalized set
        full_desc += " #shorts"
    for tag_item in metadata.get('hashtags', []):
        clean_hashtag = tag_item if tag_item.startswith('#') else '#' + tag_item
        if clean_hashtag.lower() not in existing_hashtags:
            full_desc += f" {clean_hashtag}"
            existing_hashtags.add(clean_hashtag.lower())  # Add to set to avoid duplicates

    snippet = {"title": metadata["title"][:100], "description": full_desc[:5000],
               "tags": [t for t in metadata.get("tags", []) if t][:25],  # Ensure tags are strings and limit count
               "categoryId": "24", "defaultLanguage": "en"}  # Assuming category 'Entertainment', adjust if needed
    body = {"id": video_id, "snippet": snippet, "status": {"privacyStatus": "private", "publishAt": iso_ts,
                                                           "selfDeclaredMadeForKids": False}}
    try:
        res = youtube_service.videos().update(part="snippet,status", body=body).execute()
        print(
            f"  Success! Status: {res.get('status', {}).get('privacyStatus')}, Scheduled: {res.get('status', {}).get('publishAt')}")
        return True
    except HttpError as e_http:
        if is_youtube_quota_error(e_http):
            print(f"  Quota exceeded during videos.update for {video_id}.")
            raise QuotaExceededError(f"Quota exceeded at videos.update for {video_id}") from e_http
        error_content = e_http.content.decode() if hasattr(e_http,
                                                           'content') and e_http.content else "No error content."
        print(
            f"  HTTP Error updating {video_id} (status: {e_http.resp.status if hasattr(e_http, 'resp') else 'N/A'}): {e_http} - Details: {error_content}")
        return False
    except QuotaExceededError:  # Ensure it propagates if raised from is_youtube_quota_error
        raise
    except Exception as e_gen:
        print(f"  Error updating {video_id}: {e_gen}");
        return False


def main():
    result = get_authenticated_service()
    if not result or result[0] is None:
        print("Authentication failed. Exiting.")
        return
    
    youtube, selected_account_name = result

    print(f"\n--- YouTube Shorts Automation (Advanced Scheduling) ---")
    print(f"Working with account: {selected_account_name}")
    print("Fetches ONLY unscheduled private (draft) videos, generates metadata, and schedules them.")
    print("Videos that are already scheduled will be excluded.")
    print("Duplicate content detection is enabled to skip similar transcripts.")
    print("Ensure GEMINI_API_KEY is set.\n")

    # Get account ID for data storage (use the actual channel ID from API)
    account_id = get_account_id_from_service(youtube)
    print(f"Channel ID: {account_id}")

    # Load existing processed videos data
    processed_data = load_processed_videos_data(account_id)
    print(f"Loaded data for {len(processed_data.get('videos', {}))} previously processed videos")
    
    # Offer to view processed data summary
    if processed_data.get("videos"):
        view_data = input("Would you like to view processed data summary? (yes/no): ").lower()
        if view_data == 'yes':
            view_processed_data_summary(account_id)
            print()  # Add spacing

    # Determine system local timezone once using tzlocal and pytz
    SYSTEM_LOCAL_TIMEZONE = None
    try:
        local_tz_name_str = tzlocal.get_localzone_name()
        if local_tz_name_str:
            SYSTEM_LOCAL_TIMEZONE = pytz.timezone(local_tz_name_str)
            print(f"Successfully determined system local timezone as: {SYSTEM_LOCAL_TIMEZONE}")
        else:
            raise ValueError("tzlocal.get_localzone_name() returned an empty or None value.")
    except pytz.exceptions.UnknownTimeZoneError:
        print(f"Warning: tzlocal returned timezone name '{local_tz_name_str}', which pytz does not recognize.")
        print(
            "Please ensure your system timezone is configured with a standard IANA name or install `tzdata` package if on Windows.")
    except Exception as e_tz:  # Catch other potential errors from tzlocal or pytz
        print(f"Error determining local timezone: {e_tz}.")

    if not SYSTEM_LOCAL_TIMEZONE:
        print(
            "Falling back to UTC for scheduling as local timezone could not be reliably determined. This may not be your local time.")
        SYSTEM_LOCAL_TIMEZONE = pytz.utc

    # Use the new function that excludes already scheduled videos
    video_ids = get_my_unscheduled_private_video_ids(youtube)
    if not video_ids: print("No unscheduled private videos found. Exiting."); return

    print(
        f"\nFound {len(video_ids)} unscheduled private videos: {', '.join(video_ids[:3])}{'...' if len(video_ids) > 3 else ''}")
    if input("Proceed with ALL these unscheduled private videos? (yes/no): ").lower() != 'yes': print(
        "Cancelled. Exiting."); return

    while True:
        date_str = input("Start date (DD-MM-YYYY): ")
        try:
            start_date = datetime.datetime.strptime(date_str, "%d-%m-%Y").date()
            break
        except ValueError:
            print("Invalid date format.")
    if start_date < datetime.date.today(): print(
        f"Warning: Start date {start_date} is past. Scheduling from first available slot.")

    while True:
        vids_per_day_str = input("Videos per day (e.g., 1, 2): ")
        try:
            vids_per_day = int(vids_per_day_str)
            assert vids_per_day > 0
            break
        except:
            print("Must be positive integer.")

    daily_times = []
    prompt_suggestion = 9
    for i in range(vids_per_day):
        while True:
            time_str = input(f"  Time for video {i + 1}/day (HH:MM, e.g., {prompt_suggestion:02d}:00): ")
            try:
                vid_time = datetime.datetime.strptime(time_str, "%H:%M").time()
                if i > 0 and vid_time <= daily_times[-1]:
                    print(f"Must be after {daily_times[-1]:%H:%M}.")
                else:
                    daily_times.append(vid_time)
                    prompt_suggestion = (vid_time.hour + 2) % 24
                    break
            except ValueError:
                print("Invalid time format.")

    current_date, current_time_idx = start_date, 0
    eligible_to_process = video_ids  # These are already filtered to be unscheduled

    print(f"\nTotal unscheduled private videos to attempt scheduling: {len(eligible_to_process)}")
    if input("Proceed with these unscheduled private videos? (yes/no): ").lower() != 'yes': print(
        "Cancelled. Exiting."); return

    quota_error_hit = False
    processed_video_count = 0
    scheduled_count = 0

    try:
        for vid_idx, vid_id_to_sched in enumerate(eligible_to_process):
            processed_video_count = vid_idx + 1
            print(f"\nProcessing video {vid_idx + 1}/{len(eligible_to_process)}: {vid_id_to_sched}")

            publish_dt = None
            slot_loop_count = 0
            iter_current_date = current_date
            iter_current_time_idx = current_time_idx

            while publish_dt is None and slot_loop_count < (len(daily_times) * 365 * 2):
                slot_loop_count += 1
                candidate_dt_naive = datetime.datetime.combine(iter_current_date, daily_times[iter_current_time_idx])

                # Use the SYSTEM_LOCAL_TIMEZONE determined earlier
                candidate_dt = SYSTEM_LOCAL_TIMEZONE.localize(candidate_dt_naive)
                min_valid_dt = datetime.datetime.now(SYSTEM_LOCAL_TIMEZONE) + datetime.timedelta(minutes=30)

                if candidate_dt >= min_valid_dt:
                    publish_dt = candidate_dt
                else:
                    iter_current_time_idx += 1
                    if iter_current_time_idx >= len(daily_times):
                        iter_current_time_idx = 0
                        iter_current_date += datetime.timedelta(days=1)

            video_scheduled_this_iteration = False
            if not publish_dt:
                print(f"Could not find a valid future slot for {vid_id_to_sched}... Skipping this video.")
            else:
                print(f"  To be scheduled: {publish_dt.strftime('%Y-%m-%d %H:%M:%S %Z%z')} (local)")
                transcript = get_video_transcript(youtube, vid_id_to_sched)
                if not transcript:
                    print(f"Skipping {vid_id_to_sched} (no transcript or error fetching it).")
                else:
                    # Check for duplicate content
                    if is_transcript_duplicate(account_id, transcript):
                        print(f"Skipping {vid_id_to_sched} (duplicate content detected).")
                        # Save the transcript data even if skipped for future reference
                        save_video_data(account_id, vid_id_to_sched, transcript, 
                                      {"title": "Skipped - Duplicate Content", "description": "Duplicate content detected", "hashtags": [], "tags": []}, 
                                      None)
                    else:
                        metadata = generate_metadata_with_gemini(transcript)
                        if not metadata or "Placeholder" in metadata.get("title", "") or "Fallback" in metadata.get("title", ""):
                            print(f"Skipping {vid_id_to_sched} (metadata error/placeholder).")
                            # Save the transcript data even if metadata generation failed
                            save_video_data(account_id, vid_id_to_sched, transcript, 
                                          {"title": "Skipped - Metadata Error", "description": "Metadata generation failed", "hashtags": [], "tags": []}, 
                                          None)
                        else:
                            if update_and_schedule_video(youtube, vid_id_to_sched, metadata, publish_dt):
                                scheduled_count += 1
                                video_scheduled_this_iteration = True
                                # Save the successful processing data
                                save_video_data(account_id, vid_id_to_sched, transcript, metadata, publish_dt)
                            else:
                                # Save the data even if scheduling failed
                                save_video_data(account_id, vid_id_to_sched, transcript, metadata, None)

            current_time_idx += 1
            day_advanced_master_schedule = False
            if current_time_idx >= len(daily_times):
                current_time_idx = 0
                current_date += datetime.timedelta(days=1)
                day_advanced_master_schedule = True

            if day_advanced_master_schedule and vid_id_to_sched != eligible_to_process[-1]:
                print(
                    f"  --- Master schedule slot advanced to next day. Next video processing will start from {current_date:%Y-%m-%d} ---")
            print("-" * 40)

    except QuotaExceededError as e:
        print(f"\nSTOPPING PROCESSING: YouTube API Quota Exceeded.")
        print(f"Error detail: {e}")
        quota_error_hit = True
    except Exception as e_main:
        print(f"\nAN UNEXPECTED ERROR OCCURRED in the main processing loop: {e_main}")
        import traceback
        traceback.print_exc()
        quota_error_hit = True

    finally:
        print(f"\n--- Automation Complete ---")
        
        # Load updated processed data to show statistics
        updated_data = load_processed_videos_data(account_id)
        total_processed_videos = len(updated_data.get("videos", {}))
        duplicate_count = sum(1 for v in updated_data.get("videos", {}).values() 
                            if "Duplicate Content" in v.get("metadata", {}).get("title", ""))
        
        print(f"Data Storage Summary:")
        print(f"  Account ID: {account_id}")
        print(f"  Total videos in database: {total_processed_videos}")
        print(f"  Duplicates detected in this session: {duplicate_count}")
        print(f"  Data saved to: {get_account_data_file_path(account_id)}")
        
        if scheduled_count > 0:
            print(f"Successfully scheduled {scheduled_count} video(s).")
        else:
            print("No videos were scheduled successfully in this run.")

        if quota_error_hit:
            print(f"Processing was halted prematurely.")
            current_exception = sys.exc_info()[1]
            if isinstance(current_exception, QuotaExceededError):
                print("Reason: YouTube API Quota Limit Reached.")
            elif current_exception is not None:
                print(f"Reason: An unexpected error occurred ({type(current_exception).__name__}).")
            else:
                print("Reason: Unknown critical error.")

            print(
                f"{processed_video_count} video(s) out of {len(eligible_to_process)} eligible videos were attempted before stopping.")
            if processed_video_count > scheduled_count:
                print(
                    f"{processed_video_count - scheduled_count} of these attempted videos were not successfully scheduled (e.g. skipped, or the one that hit quota).")

            if len(eligible_to_process) - processed_video_count > 0:
                print(
                    f"{len(eligible_to_process) - processed_video_count} video(s) from the eligible list were not attempted at all.")

        elif processed_video_count < len(eligible_to_process) and not quota_error_hit:
            print(
                f"{len(eligible_to_process) - scheduled_count} video(s) were skipped due to non-critical reasons (e.g., no transcript, metadata error, slot not found).")
        elif not quota_error_hit and scheduled_count == len(eligible_to_process) and len(
                eligible_to_process) > 0:  # Added check for >0
            print("All eligible videos were processed successfully!")
        elif not quota_error_hit and not eligible_to_process:  # Case where no videos were eligible initially
            print("No videos were eligible for processing.")


if __name__ == "__main__":
    if not os.path.exists(CLIENT_SECRETS_FILE):
        print(f"ERROR: '{CLIENT_SECRETS_FILE}' not found.")
    else:
        # Main menu
        while True:
            print("\n" + "="*50)
            print("🎬 YouTube Shorts Automation Suite")
            print("="*50)
            print("1. Run automation (schedule videos)")
            print("2. Add new account")
            print("3. Manage accounts")
            print("4. Exit")
            
            choice = input("\nSelect option (1-4): ").strip()
            
            if choice == '1':
                main()
                break  # Exit after running automation
            elif choice == '2':
                if add_account_standalone():
                    print("\n✨ Account added successfully! You can now run automation with this account.")
                else:
                    print("\n❌ Failed to add account. Please try again.")
            elif choice == '3':
                manage_accounts()
            elif choice == '4':
                print("Goodbye! 👋")
                break
            else:
                print("Invalid choice. Please enter 1, 2, 3, or 4.")