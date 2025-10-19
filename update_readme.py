#!/usr/bin/env python3
"""
GitHub Profile README Auto-Updater
Updates the quote image URL with a cache-busting timestamp
Maintains GitHub activity streak through automated commits
"""

import os
import re
from datetime import datetime
import pytz

# Configuration
README_PATH = "README.md"
TIMEZONE = pytz.timezone("Asia/Manila")  # UTC+8 (Philippines)
QUOTE_API_BASE = "https://quotes-github-readme.vercel.app/api?type=horizontal&theme=tokyonight"


def get_current_timestamp():
    """Get formatted timestamp in specified timezone"""
    now = datetime.now(TIMEZONE)
    return now.strftime("%Y-%m-%d %H:%M:%S")


def get_quote_url_with_cache_buster():
    """Generate quote URL with timestamp to force refresh"""
    timestamp = int(datetime.now(TIMEZONE).timestamp())
    return f"{QUOTE_API_BASE}&t={timestamp}"


def update_readme():
    """Update the Quote of the Day section in README.md with refreshed image URL"""
    
    if not os.path.exists(README_PATH):
        print(f"❌ Error: {README_PATH} not found!")
        return False
    
    # Read current README
    with open(README_PATH, "r", encoding="utf-8") as f:
        content = f.read()
    
    # Generate new quote URL with cache buster
    quote_url = get_quote_url_with_cache_buster()
    timestamp = get_current_timestamp()
    
    # Format new quote section
    new_quote_section = f'''<div align="center">

## 💬 Quote of the Day

![Quote]({quote_url})

_🤖 Auto-updated: {timestamp} (UTC+8)_

</div>'''
    
    # Define regex pattern to match the quote section
    # This pattern captures everything between the quote section markers
    pattern = r'(<div align="center">\s*\n\s*## 💬 Quote of the Day.*?</div>)'
    
    # Replace the quote section
    if re.search(pattern, content, re.DOTALL):
        updated_content = re.sub(pattern, new_quote_section, content, flags=re.DOTALL)
        
        # Write updated content back
        with open(README_PATH, "w", encoding="utf-8") as f:
            f.write(updated_content)
        
        print("✅ README.md updated successfully!")
        print(f"🔗 Quote URL: {quote_url}")
        print(f"🕐 Timestamp: {timestamp}")
        return True
    else:
        print("❌ Error: Could not find Quote of the Day section in README.md")
        return False


def main():
    """Main execution function"""
    print("=" * 60)
    print("🚀 GitHub Profile Auto-Updater")
    print("=" * 60)
    
    # Update README with refreshed quote URL
    print("\n📝 Updating README.md with fresh quote...")
    success = update_readme()
    
    if success:
        print("\n" + "=" * 60)
        print("✨ Update completed successfully!")
        print("=" * 60)
        return 0
    else:
        print("\n❌ Update failed!")
        return 1


if __name__ == "__main__":
    exit(main())