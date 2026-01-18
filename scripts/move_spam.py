#!/usr/bin/env python3
"""
Direct spam mover script - bypasses LLM for immediate spam cleanup.
Usage:
    python3 move_spam.py [options]

Options:
    --max NUM       Maximum number of emails to scan (default: 100)
    --dry-run       Preview what would be moved without actually moving
    --account ID    Email account ID (default: first account)

Examples:
    # Move spam from last 100 emails
    python3 move_spam.py

    # Scan last 300 emails (for bulk cleanup)
    python3 move_spam.py --max 300

    # Preview what would be moved
    python3 move_spam.py --max 150 --dry-run
"""
import sys
import os
import asyncio
import argparse

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from server.assistant_functions import move_spam_to_folder, _load_email_accounts, logger


async def main():
    parser = argparse.ArgumentParser(
        description='Move spam emails to Spam folder',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    parser.add_argument(
        '--max',
        type=int,
        default=100,
        metavar='NUM',
        help='Maximum number of emails to scan (default: 100)'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Preview what would be moved without actually moving'
    )
    parser.add_argument(
        '--account',
        type=str,
        default=None,
        metavar='ID',
        help='Email account ID (default: first account)'
    )
    
    args = parser.parse_args()
    
    # Load accounts
    accounts = _load_email_accounts()
    if not accounts:
        print("ERROR: No email accounts configured.")
        print("Please configure an email account first through the web UI or API.")
        return 1
    
    # Get account ID
    account_id = args.account if args.account else list(accounts.keys())[0]
    if account_id not in accounts:
        print(f"ERROR: Account '{account_id}' not found.")
        print(f"Available accounts: {', '.join(accounts.keys())}")
        return 1
    
    print("=" * 60)
    print("SPAM MOVER - Direct Email Cleanup")
    print("=" * 60)
    print(f"Account: {account_id}")
    print(f"Scanning: Last {args.max} emails")
    print(f"Mode: {'DRY RUN (preview only)' if args.dry_run else 'LIVE (will move emails)'}")
    print("=" * 60)
    print()
    
    # Run spam mover
    result = await move_spam_to_folder(
        account_id=account_id,
        max_messages=args.max,
        dry_run=args.dry_run
    )
    
    if "error" in result:
        print(f"ERROR: {result['error']}")
        return 1
    
    # Display results
    message = result.get("message", "Completed")
    spam_count = result.get("spam_count", 0)
    moved_count = result.get("moved_count", 0)
    target_folder = result.get("target_folder", "Spam")
    
    print(f"✓ {message}")
    print()
    
    if spam_count > 0:
        print(f"Spam emails found: {spam_count}")
        if not args.dry_run:
            print(f"Successfully moved: {moved_count}")
        print()
        
        spam_messages = result.get("spam_messages", [])
        if spam_messages:
            print("Sample of spam emails:")
            print("-" * 60)
            for i, spam in enumerate(spam_messages[:10], 1):
                print(f"{i}. From: {spam.get('from', 'Unknown')}")
                print(f"   Subject: {spam.get('subject', 'No subject')}")
                print()
    else:
        print("No spam emails found in the scanned messages.")
    
    print("=" * 60)
    if args.dry_run:
        print("This was a DRY RUN. No emails were moved.")
        print(f"To actually move spam, run without --dry-run:")
        print(f"    python3 move_spam.py --max {args.max}")
    else:
        print(f"Spam emails have been moved to the '{target_folder}' folder.")
        print("Check your email client to verify.")
    print("=" * 60)
    
    return 0


if __name__ == '__main__':
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n\nInterrupted by user.")
        sys.exit(130)
    except Exception as e:
        print(f"\nFATAL ERROR: {e}")
        logger.exception("Fatal error in move_spam.py")
        sys.exit(1)
