#!/usr/bin/env python3
"""
Token Refresh Utility
Automatically refreshes expired OAuth tokens for all YouTube accounts
"""

import os
import pickle
from google.auth.transport.requests import Request
from youtube_metadata import list_available_accounts, get_account_token_file, TOKEN_PICKLE_FILE

def refresh_all_tokens():
    """Refresh all expired tokens."""
    print("🔄 YouTube Token Refresh Utility")
    print("=" * 50)
    
    available_accounts = list_available_accounts()
    
    if not available_accounts:
        print("No accounts found.")
        return
    
    print(f"Found {len(available_accounts)} account(s)\n")
    
    refreshed = 0
    already_valid = 0
    failed = 0
    
    for account in available_accounts:
        if account == "default":
            token_file = TOKEN_PICKLE_FILE
        else:
            token_file = get_account_token_file(account)
        
        try:
            with open(token_file, "rb") as f:
                creds = pickle.load(f)
            
            print(f"Checking: {account}")
            
            if not creds:
                print(f"  ✗ No credentials found")
                failed += 1
                continue
            
            if creds.valid:
                print(f"  ✓ Token is valid")
                already_valid += 1
            elif creds.expired and creds.refresh_token:
                print(f"  🔄 Token expired, refreshing...")
                try:
                    creds.refresh(Request())
                    # Save refreshed credentials
                    with open(token_file, "wb") as f:
                        pickle.dump(creds, f)
                    print(f"  ✓ Token refreshed successfully")
                    refreshed += 1
                except Exception as e:
                    print(f"  ✗ Failed to refresh: {e}")
                    failed += 1
            else:
                print(f"  ⚠ Token invalid but no refresh token available")
                failed += 1
        
        except Exception as e:
            print(f"  ✗ Error: {e}")
            failed += 1
        
        print()
    
    # Summary
    print("=" * 50)
    print(f"Summary:")
    print(f"  ✓ Already valid: {already_valid}")
    print(f"  ✓ Refreshed: {refreshed}")
    print(f"  ✗ Failed: {failed}")
    print()
    
    if failed == 0 and refreshed > 0:
        print("✅ All tokens refreshed successfully!")
    elif failed == 0:
        print("✅ All tokens are valid!")
    else:
        print(f"⚠️  {failed} token(s) need re-authentication")
        print("   Use 'Manage Accounts' > 'Refresh Credentials' in the GUI")

if __name__ == "__main__":
    refresh_all_tokens()
