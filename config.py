import os
import secrets
from datetime import timedelta
from dotenv import load_dotenv

# Ensure .env is loaded from the directory containing config.py
env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
load_dotenv(env_path)

# App secret key for session signing
SECRET_KEY = os.environ.get("SECRET_KEY")
if not SECRET_KEY:
    SECRET_KEY = secrets.token_hex(32)

# Database path
DATABASE = os.environ.get("DATABASE", "sma.db")

# Message limits
DAILY_LIMIT = 5

# Security settings
MAX_FAILS = 5          # Number of incorrect attempts before lockout
LOCK_SECONDS = 600     # Lockout duration in seconds (10 minutes)
SESSION_LIFETIME = timedelta(hours=8)

# Transport security
HTTPS = os.environ.get("HTTPS") == "1"
DEBUG = os.environ.get("FLASK_DEBUG", "0") == "1"
