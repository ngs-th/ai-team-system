#!/usr/bin/env python3
"""
Agent Message Filter - FORCE HTML stripping
Agents MUST use this to send messages to Telegram
"""

import re
import subprocess
import sys

TELEGRAM_CHANNEL = "1268858185"

def force_strip_html(text: str) -> str:
    """Force remove ALL HTML tags and entities - NO EXCEPTIONS"""
    if not text:
        return ''
    
    # Remove ALL HTML tags (aggressive)
    text = re.sub(r'<[^>]+>', '', text)
    
    # Replace HTML entities
    replacements = {
        '&nbsp;': ' ',
        '&lt;': '<',
        '&gt;': '>',
        '&amp;': '&',
        '&quot;': '"',
        '&#39;': "'",
        '&hellip;': '...',
        '&mdash;': '—',
        '&ndash;': '-',
    }
    
    for entity, char in replacements.items():
        text = text.replace(entity, char)
    
    # Clean up extra whitespace
    text = ' '.join(text.split())
    
    return text.strip()

def send_message(text: str, channel: str = "telegram", target: str = TELEGRAM_CHANNEL) -> bool:
    """
    Send message to Telegram with FORCE HTML stripping
    Agents MUST use this function instead of sending directly
    """
    # FORCE strip HTML
    clean_text = force_strip_html(text)
    
    try:
        result = subprocess.run(
            ["openclaw", "message", "send", 
             "--channel", channel,
             "--target", target, 
             "--message", clean_text],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode != 0:
            print(f"[Send Error] {result.stderr}", file=sys.stderr)
            return False
            
        return True
        
    except Exception as e:
        print(f"[Send Error] {e}", file=sys.stderr)
        return False

def main():
    """CLI usage: python3 message_filter.py "Your message with <b>HTML</b>" """
    import argparse
    parser = argparse.ArgumentParser(description='Send message with HTML filtering')
    parser.add_argument('message', help='Message to send')
    parser.add_argument('--target', default=TELEGRAM_CHANNEL, help='Target channel')
    args = parser.parse_args()
    
    # Show before/after
    print(f"Original: {args.message}")
    clean = force_strip_html(args.message)
    print(f"Cleaned:  {clean}")
    
    if send_message(args.message, target=args.target):
        print("✅ Sent successfully")
    else:
        print("❌ Failed to send")
        sys.exit(1)

if __name__ == '__main__':
    main()
