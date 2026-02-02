#!/bin/bash
# AI Team Message Guard - FORCE HTML removal
# Usage: ./message_guard.sh "Your message here"

MESSAGE="$1"
TARGET="${2:-1268858185}"

# Remove ALL HTML tags
MESSAGE=$(echo "$MESSAGE" | sed 's/<[^>]*>//g')

# Replace HTML entities
MESSAGE=$(echo "$MESSAGE" | sed 's/&nbsp;/ /g; s/&lt;/</g; s/&gt;/>/g; s/&amp;/&/g; s/&quot;/"/g')

# Send via openclaw
openclaw message send --channel telegram --target "$TARGET" --message "$MESSAGE"
