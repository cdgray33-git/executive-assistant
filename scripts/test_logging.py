#!/usr/bin/env python3
"""
Test script to verify logging is working correctly.
This should be run after installation to confirm setup.
"""
import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

def test_logging():
    """Test that logging is properly configured."""
    print("=" * 60)
    print("LOGGING CONFIGURATION TEST")
    print("=" * 60)
    print()
    
    # Check log directory
    log_dir = os.path.expanduser("~/ExecutiveAssistant/logs")
    log_file = os.path.join(log_dir, "assistant.log")
    
    print(f"Expected log directory: {log_dir}")
    print(f"Expected log file: {log_file}")
    print()
    
    # Check if directory exists
    if os.path.exists(log_dir):
        print(f"✓ Log directory exists")
    else:
        print(f"✗ Log directory does NOT exist - creating it...")
        try:
            os.makedirs(log_dir, exist_ok=True)
            print(f"✓ Log directory created successfully")
        except Exception as e:
            print(f"✗ Failed to create log directory: {e}")
            return False
    
    # Check if writable
    if os.access(log_dir, os.W_OK):
        print(f"✓ Log directory is writable")
    else:
        print(f"✗ Log directory is NOT writable")
        return False
    
    print()
    
    # Try to import and use the module
    try:
        print("Testing module import...")
        from server.assistant_functions import logger, LOG_FILE
        print(f"✓ Module imported successfully")
        print(f"✓ Logger name: {logger.name}")
        print(f"✓ Logger handlers: {len(logger.handlers)}")
        print(f"✓ Configured log file: {LOG_FILE}")
        print()
        
        # Test writing to log
        print("Testing log write...")
        logger.info("Test log entry from logging test script")
        print(f"✓ Log write successful")
        
        # Check if file was created
        if os.path.exists(LOG_FILE):
            print(f"✓ Log file exists: {LOG_FILE}")
            # Show last few lines
            try:
                with open(LOG_FILE, 'r') as f:
                    lines = f.readlines()
                    print()
                    print("Last 5 log entries:")
                    print("-" * 60)
                    for line in lines[-5:]:
                        print(line.rstrip())
                    print("-" * 60)
            except Exception as e:
                print(f"Warning: Could not read log file: {e}")
        else:
            print(f"✗ Log file was not created: {LOG_FILE}")
            return False
        
    except Exception as e:
        print(f"✗ Error testing module: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    print()
    print("=" * 60)
    print("✓ ALL TESTS PASSED")
    print("=" * 60)
    print()
    print("Logging is working correctly!")
    print(f"View logs with: tail -f {log_file}")
    print()
    
    return True


if __name__ == '__main__':
    try:
        success = test_logging()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\nFATAL ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
