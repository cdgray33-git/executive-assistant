#!/usr/bin/env python3
"""
Bulk Yahoo Spam Cleanup using Local Ollama AI
Processes oldest emails, categorizes with AI, deletes spam
"""
import sys
import os
import argparse
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'server'))

from connectors.yahoo_connector import YahooConnector
from spam_detector import SpamDetector
import json

def main():
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Yahoo Spam Cleanup with AI')
    parser.add_argument('--model', type=str, default='llama3.2:latest',
                       help='Ollama model to use (e.g., qwen2.5:7b-instruct)')
    parser.add_argument('--batch-size', type=int, default=100,
                       help='Number of emails to process')
    parser.add_argument('--email', type=str, help='Yahoo email address')
    parser.add_argument('--password', type=str, help='Yahoo app password')
    args = parser.parse_args()
    
    print("?? Yahoo Spam Cleanup - AI Powered")
    print("=" * 60)
    
    # Get credentials
    email = args.email or input("Yahoo email address: ")
    app_password = args.password or input("Yahoo app password: ")
    
    print(f"\n?? Connecting to {email}...")
    
    # Connect to Yahoo
    yahoo = YahooConnector(email, app_password)
    success, msg = yahoo.connect()
    
    if not success:
        print(f"? Failed: {msg}")
        sys.exit(1)
    
    print("? Connected!")
    
    # Get mailbox stats
    stats = yahoo.get_mailbox_stats()
    print(f"\n?? Mailbox Stats:")
    print(f"   Total emails: {stats.get('total_messages', 'unknown')}")
    print(f"   Unread: {stats.get('unread_count', 'unknown')}")
    
    # Ask how many to process (unless specified via CLI)
    if args.batch_size == 100:  # default value
        batch_input = input("\nHow many emails to process? [default: 100]: ").strip()
        batch_size = int(batch_input) if batch_input else 100
    else:
        batch_size = args.batch_size
    
    print(f"\n?? Fetching {batch_size} oldest emails...")
    emails = yahoo.preview_emails(count=batch_size, oldest_first=True)
    print(f"? Retrieved {len(emails)} emails")
    
    if not emails:
        print("No emails found!")
        yahoo.disconnect()
        return
    
    # Initialize AI detector with specified model
    print(f"\n?? Loading AI spam detector (Ollama model: {args.model})...")
    detector = SpamDetector(model_name=args.model)
    
    # Categorize with AI
    print("?? Analyzing emails with AI (this may take a few minutes)...")
    categorized = detector.batch_categorize(emails)
    
    # Separate by category
    spam = [e for e in categorized if e.get('category') == 'spam']
    keep = [e for e in categorized if e.get('category') == 'keep']
    unsure = [e for e in categorized if e.get('category') == 'unsure']
    
    print(f"\n?? AI Results:")
    print(f"   ?? Spam: {len(spam)}")
    print(f"   ?? Keep: {len(keep)}")
    print(f"   ?? Unsure: {len(unsure)}")
    
    # Show spam preview
    if spam:
        print(f"\n?? Spam emails detected (showing first 10):")
        for i, email in enumerate(spam[:10]):
            print(f"\n  {i+1}. From: {email.get('from', '')[:50]}")
            print(f"     Subject: {email.get('subject', '')[:60]}")
            print(f"     Reason: {email.get('reasoning', '')[:80]}")
        
        if len(spam) > 10:
            print(f"\n  ... and {len(spam) - 10} more spam emails")
        
        # Confirm deletion
        print(f"\n??  Ready to delete {len(spam)} spam emails")
        print("   This will move them to Trash (NOT permanent)")
        response = input("\n   Continue? [y/N]: ")
        
        if response.lower() == 'y':
            # RECONNECT before deletion (AI processing may have caused timeout)
            print("\n?? Reconnecting to Yahoo...")
            yahoo.disconnect()
            success, msg = yahoo.connect()
            if not success:
                print(f"? Reconnection failed: {msg}")
                print("   Please try running the script again to delete the identified spam")
                sys.exit(1)
            print("? Reconnected!")
            
            print("\n???  Deleting spam...")
            spam_ids = [e['id'] for e in spam]
            result = yahoo.delete_emails(spam_ids, permanent=False)
            
            if result.get('success'):
                print(f"? Deleted {result['deleted_count']} emails")
                if result.get('failed_count', 0) > 0:
                    print(f"??  {result['failed_count']} failed")
            else:
                print(f"? Error: {result.get('error')}")
        else:
            print("? Deletion cancelled")
    else:
        print("\n? No spam detected in this batch!")
    
    # Disconnect
    yahoo.disconnect()
    print("\n? Done!\n")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n??  Interrupted by user")
        sys.exit(0)
    except Exception as e:
        print(f"\n? Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
