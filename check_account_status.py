#!/usr/bin/env python3
"""
Test the GUI account selection with invalid tokens.
This verifies that the GUI will trigger OAuth flow for invalid accounts.
"""

import os
import sys
import pickle
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from youtube_metadata import (
    list_available_accounts,
    get_account_token_file,
    TOKEN_PICKLE_FILE,
)


def check_account_status():
    """Check the status of all accounts without triggering errors."""
    available_accounts = list_available_accounts()

    print("\n" + "=" * 60)
    print("🔍 Account Token Status Check")
    print("=" * 60 + "\n")

    if not available_accounts:
        print("❌ No accounts found")
        return

    print(f"Found {len(available_accounts)} account(s):\n")

    for account in available_accounts:
        try:
            if account == "default":
                token_file = TOKEN_PICKLE_FILE
            else:
                token_file = get_account_token_file(account)

            if not os.path.exists(token_file):
                print(f"  ⚠️  {account:20} → Token file missing")
                continue

            with open(token_file, "rb") as f:
                creds = pickle.load(f)

                if creds is None:
                    print(f"  ⚠️  {account:20} → Credentials corrupted")
                elif creds.valid:
                    print(f"  ✅ {account:20} → Valid (ready to use)")
                elif creds.expired:
                    has_refresh = hasattr(creds, "refresh_token") and creds.refresh_token
                    if has_refresh:
                        print(
                            f"  🔄 {account:20} → Expired (can auto-refresh)"
                        )
                    else:
                        print(
                            f"  ⚠️  {account:20} → Expired (needs re-authentication)"
                        )
                else:
                    print(f"  ⚠️  {account:20} → Invalid")

        except Exception as e:
            print(f"  ❌ {account:20} → Error: {str(e)[:40]}")

    print("\n" + "=" * 60)
    print("✨ When you select an account in the GUI:")
    print("   • Valid accounts: Work immediately")
    print("   • Invalid accounts: Browser opens for re-authentication")
    print("   • After auth: Fresh token saved, continues normally")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    check_account_status()
