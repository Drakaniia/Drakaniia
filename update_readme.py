#!/usr/bin/env python3
"""
GitHub Profile README Auto-Updater
Updates the quote with a styled card design
Maintains GitHub activity streak through automated commits
"""

import os
import re
from datetime import datetime
import pytz
import random

# Configuration
README_PATH = "README.md"
TIMEZONE = pytz.timezone("Asia/Manila")  # UTC+8 (Philippines)

# Curated quote collection
QUOTES = [
    {"text": "The only way to do great work is to love what you do.", "author": "Steve Jobs"},
    {"text": "Innovation distinguishes between a leader and a follower.", "author": "Steve Jobs"},
    {"text": "Code is like humor. When you have to explain it, it's bad.", "author": "Cory House"},
    {"text": "First, solve the problem. Then, write the code.", "author": "John Johnson"},
    {"text": "Programming isn't about what you know; it's about what you can figure out.", "author": "Chris Pine"},
    {"text": "The best error message is the one that never shows up.", "author": "Thomas Fuchs"},
    {"text": "Simplicity is the soul of efficiency.", "author": "Austin Freeman"},
    {"text": "Make it work, make it right, make it fast.", "author": "Kent Beck"},
    {"text": "Any fool can write code that a computer can understand. Good programmers write code that humans can understand.", "author": "Martin Fowler"},
    {"text": "Experience is the name everyone gives to their mistakes.", "author": "Oscar Wilde"},
    {"text": "The only true wisdom is in knowing you know nothing.", "author": "Socrates"},
    {"text": "Wishing to be friends is quick work, but friendship is a slow ripening fruit.", "author": "Aristotle"},
    {"text": "Success is not final, failure is not fatal: it is the courage to continue that counts.", "author": "Winston Churchill"},
    {"text": "The future belongs to those who believe in the beauty of their dreams.", "author": "Eleanor Roosevelt"},
    {"text": "It does not matter how slowly you go as long as you do not stop.", "author": "Confucius"},
]


def get_current_timestamp():
    """Get formatted timestamp in specified timezone"""
    now = datetime.now(TIMEZONE)
    return now.strftime("%Y-%m-%d %H:%M:%S")


def get_random_quote():
    """Get a random quote from the collection"""
    return random.choice(QUOTES)


def update_readme():
    """Update the Quote of the Day section in README.md with styled card"""
    
    if not os.path.exists(README_PATH):
        print(f"❌ Error: {README_PATH} not found!")
        return False
    
    # Read current README
    with open(README_PATH, "r", encoding="utf-8") as f:
        content = f.read()
    
    # Get random quote and timestamp
    quote_data = get_random_quote()
    timestamp = get_current_timestamp()
    
    # Format new quote section with styled card
    new_quote_section = f'''<div align="center">

## 💬 Quote of the Day

<div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); border-radius: 15px; padding: 30px; margin: 20px 0; box-shadow: 0 10px 30px rgba(0,0,0,0.3); position: relative;">
  <div style="background: rgba(255,255,255,0.1); backdrop-filter: blur(10px); border-radius: 12px; padding: 25px; border: 1px solid rgba(255,255,255,0.2);">
    <div style="text-align: center; margin-bottom: 15px;">
      <span style="font-size: 48px; color: #FFD700; opacity: 0.8; font-family: Georgia, serif;">"</span>
    </div>
    <p style="font-size: 18px; color: #FFFFFF; text-align: center; line-height: 1.6; margin: 0 0 20px 0; font-style: italic; font-weight: 400;">
      {quote_data['text']}
    </p>
    <div style="text-align: right; margin-top: 15px;">
      <span style="font-size: 16px; color: #FFD700; font-weight: 600;">— {quote_data['author']}</span>
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
    print("\n📝 Updating README.md with styled quote card...")
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