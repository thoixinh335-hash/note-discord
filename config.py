import os
from dotenv import load_dotenv

load_dotenv()

# Discord
DISCORD_USER_TOKEN = os.getenv("DISCORD_USER_TOKEN")

# Settings
POLL_INTERVAL = int(os.getenv("POLL_INTERVAL", "2"))
STATUS_FORMAT = os.getenv("STATUS_FORMAT", "🎵 {artist} - {title}")
