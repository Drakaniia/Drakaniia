#!/usr/bin/env python3
"""
GitHub Profile README Auto-Updater
Fetches quotes from API and displays them in README
Maintains GitHub activity streak through automated commits
"""

import os
import re
from datetime import datetime
import pytz
import urllib.request
import json

# Configuration
README_PATH = "README.md"
TIMEZONE = pytz.timezone("Asia/Manila")  # UTC+8 (Philippines)


def get_current_timestamp():
    """Get formatted timestamp in specified timezone"""
    now = datetime.now(TIMEZONE)
    return now.strftime("%Y-%m-%d %H:%M:%S")


def fetch_quote_from_api():
    """Fetch a random quote from the API"""
    try:
        api_url = "https://api.quotable.io/random"
        
        with urllib.request.urlopen(api_url, timeout=10) as response:
            data = json.loads(response.read().decode())
            return {
                "text": data["content"],
                "author": data["author"]
            }
    except Exception as e:
        print(f"⚠️  API fetch failed: {e}")
        # Fallback quote if API fails
        return {
            "text": "The only way to do great work is to love what you do.",
            "author": "Steve Jobs"
        }


def update_readme():
    """Update the Quote of the Day section in README.md"""
    
    if not os.path.exists(README_PATH):
        print(f"❌ Error: {README_PATH} not found!")
        return False
    
    # Read current README
    with open(README_PATH, "r", encoding="utf-8") as f:
        content = f.read()
    
    # Fetch quote from API and get timestamp
    quote_data = fetch_quote_from_api()
    timestamp = get_current_timestamp()
    
    # Format new quote section - matching the simple format in your README
    new_quote_section = f'''<div align="center">

## 💬 Quote of the Day

> "{quote_data['text']}"
> 
> **— {quote_data['author']}**

_🤖 Auto-updated: {timestamp} (UTC+8)_

</div>'''
    
    # Define regex pattern to match the quote section
    # This pattern matches from the "## 💬 Quote of the Day" until the closing </div>
    pattern = r'(<div align="center">\s*## 💬 Quote of the Day.*?_🤖 Auto-updated:.*?\(UTC\+8\)_\s*</div>)'
    
    # Replace the quote section
    match = re.search(pattern, content, re.DOTALL)
    if match:
        updated_content = re.sub(pattern, new_quote_section, content, flags=re.DOTALL)
        
        # Only write if content actually changed
        if updated_content != content:
            with open(README_PATH, "w", encoding="utf-8") as f:
                f.write(updated_content)
            
            print("✅ README.md updated successfully!")
            print(f"💬 Quote: {quote_data['text']}")
            print(f"✍️  Author: {quote_data['author']}")
            print(f"🕐 Timestamp: {timestamp}")
            return True
        else:
            print("ℹ️  No changes - same quote fetched")
            return False
    else:
        print("❌ Error: Could not find Quote of the Day section in README.md")
        print(f"Pattern: {pattern}")
        print("Content preview:")
        print(content[:500])
        return False


def main():
    """Main execution function"""
    print("=" * 60)
    print("🚀 GitHub Profile Auto-Updater")
    print("=" * 60)
    
    # Update README
    print("\n📝 Fetching quote from API...")
    success = update_readme()
    
    if success:
        print("\n" + "=" * 60)
        print("✨ Update completed successfully!")
        print("=" * 60)
        return 0
    else:
        print("\n⚠️  No update needed or failed")
        return 0  # Return 0 even if no update to avoid workflow failure


if __name__ == "__main__":
    exit(main())