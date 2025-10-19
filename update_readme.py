#!/usr/bin/env python3
"""
GitHub Profile README Auto-Updater
Fetches quotes from API and displays them in a styled card
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
QUOTE_API_URL = "https://quotes-github-readme.vercel.app/api?type=horizontal&theme=tokyonight"


def get_current_timestamp():
    """Get formatted timestamp in specified timezone"""
    now = datetime.now(TIMEZONE)
    return now.strftime("%Y-%m-%d %H:%M:%S")


def fetch_quote_from_api():
    """Fetch a random quote from the API"""
    try:
        # The API returns an SVG, so we'll use a different quotes API that returns JSON
        # Using quotable.io API for reliable JSON responses
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
    """Update the Quote of the Day section in README.md with styled card"""
    
    if not os.path.exists(README_PATH):
        print(f"❌ Error: {README_PATH} not found!")
        return False
    
    # Read current README
    with open(README_PATH, "r", encoding="utf-8") as f:
        content = f.read()
    
    # Fetch quote from API and get timestamp
    quote_data = fetch_quote_from_api()
    timestamp = get_current_timestamp()
    
    # Escape any potential HTML characters in the quote
    quote_text = quote_data['text'].replace('"', '&quot;').replace('<', '&lt;').replace('>', '&gt;')
    quote_author = quote_data['author'].replace('"', '&quot;').replace('<', '&lt;').replace('>', '&gt;')
    
    # Format new quote section with styled card
    new_quote_section = f'''<div align="center">

## 💬 Quote of the Day

<div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); border-radius: 15px; padding: 30px; margin: 20px 0; box-shadow: 0 10px 30px rgba(0,0,0,0.3); position: relative;">
  <div style="background: rgba(255,255,255,0.1); backdrop-filter: blur(10px); border-radius: 12px; padding: 25px; border: 1px solid rgba(255,255,255,0.2);">
    <div style="text-align: center; margin-bottom: 15px;">
      <span style="font-size: 48px; color: #FFD700; opacity: 0.8; font-family: Georgia, serif;">"</span>
    </div>
    <p style="font-size: 18px; color: #FFFFFF; text-align: center; line-height: 1.6; margin: 0 0 20px 0; font-style: italic; font-weight: 400;">
      {quote_text}
    </p>
    <div style="text-align: right; margin-top: 15px;">
      <span style="font-size: 16px; color: #FFD700; font-weight: 600;">— {quote_author}</span>
    </div>
  </div>
</div>

_🤖 Auto-updated: {timestamp} (UTC+8)_

</div>'''
    
    # Define regex pattern to match the quote section
    pattern = r'(<div align="center">\s*\n\s*## 💬 Quote of the Day.*?</div>)'
    
    # Replace the quote section
    if re.search(pattern, content, re.DOTALL):
        updated_content = re.sub(pattern, new_quote_section, content, flags=re.DOTALL)
        
        # Write updated content back
        with open(README_PATH, "w", encoding="utf-8") as f:
            f.write(updated_content)
        
        print("✅ README.md updated successfully!")
        print(f"💬 Quote: {quote_data['text']}")
        print(f"✍️  Author: {quote_data['author']}")
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
    
    # Update README with styled quote card
    print("\n📝 Fetching quote from API...")
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