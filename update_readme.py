#!/usr/bin/env python3
"""
GitHub Profile README Auto-Updater
Fetches a random quote and updates the README.md file
Maintains GitHub activity streak through automated commits
"""

import os
import re
import requests
from datetime import datetime
import pytz

# Configuration
README_PATH = "README.md"
TIMEZONE = pytz.timezone("Asia/Manila")  # UTC+8 (Philippines)
QUOTE_APIS = [
    "https://api.quotable.io/random",
    "https://zenquotes.io/api/random",
]

# Fallback quotes if APIs fail
FALLBACK_QUOTES = [
    {"text": "The only way to do great work is to love what you do.", "author": "Steve Jobs"},
    {"text": "Code is like humor. When you have to explain it, it's bad.", "author": "Cory House"},
    {"text": "First, solve the problem. Then, write the code.", "author": "John Johnson"},
    {"text": "Experience is the name everyone gives to their mistakes.", "author": "Oscar Wilde"},
    {"text": "In order to be irreplaceable, one must always be different.", "author": "Coco Chanel"},
    {"text": "Java is to JavaScript what car is to Carpet.", "author": "Chris Heilmann"},
    {"text": "Knowledge is power.", "author": "Francis Bacon"},
    {"text": "Sometimes it pays to stay in bed on Monday, rather than spending the rest of the week debugging Monday's code.", "author": "Dan Salomon"},
    {"text": "Perfection is achieved not when there is nothing more to add, but rather when there is nothing more to take away.", "author": "Antoine de Saint-Exupery"},
    {"text": "Code never lies, comments sometimes do.", "author": "Ron Jeffries"},
]


def fetch_quote():
    """Fetch a random quote from APIs or fallback list"""
    # Try APIs first
    for api_url in QUOTE_APIS:
        try:
            response = requests.get(api_url, timeout=5)
            if response.status_code == 200:
                data = response.json()
                
                # Handle different API response formats
                if api_url.startswith("https://api.quotable.io"):
                    return {
                        "text": data.get("content", ""),
                        "author": data.get("author", "Unknown")
                    }
                elif api_url.startswith("https://zenquotes.io"):
                    if isinstance(data, list) and len(data) > 0:
                        return {
                            "text": data[0].get("q", ""),
                            "author": data[0].get("a", "Unknown")
                        }
        except Exception as e:
            print(f"⚠️  API {api_url} failed: {str(e)}")
            continue
    
    # Fallback to local quotes
    import random
    quote = random.choice(FALLBACK_QUOTES)
    print("ℹ️  Using fallback quote")
    return quote


def get_current_timestamp():
    """Get formatted timestamp in specified timezone"""
    now = datetime.now(TIMEZONE)
    return now.strftime("%Y-%m-%d %H:%M:%S")


def update_readme(quote):
    """Update the Quote of the Day section in README.md"""
    
    if not os.path.exists(README_PATH):
        print(f"❌ Error: {README_PATH} not found!")
        return False
    
    # Read current README
    with open(README_PATH, "r", encoding="utf-8") as f:
        content = f.read()
    
    # Format new quote section
    timestamp = get_current_timestamp()
    new_quote_section = f'''<div align="center">

## 💬 Quote of the Day

> "{quote['text']}"
> 
> **— {quote['author']}**

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
        print(f"📝 Quote: \"{quote['text']}\"")
        print(f"👤 Author: {quote['author']}")
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
    
    # Fetch quote
    print("\n📡 Fetching new quote...")
    quote = fetch_quote()
    
    if not quote or not quote.get("text"):
        print("❌ Failed to fetch quote")
        return 1
    
    # Update README
    print("\n📝 Updating README.md...")
    success = update_readme(quote)
    
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