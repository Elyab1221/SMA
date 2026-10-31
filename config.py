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
    # Fallback key generated for local session signing
    SECRET_KEY = secrets.token_hex(32)

# Database configuration: support DATABASE_URL, POSTGRES_URL, or local SQLite fallback
DATABASE_URL = os.environ.get("DATABASE_URL") or os.environ.get("POSTGRES_URL")
DATABASE = os.environ.get("DATABASE", "sma.db")

# Message limits
DAILY_LIMIT = 5

# Security settings
MAX_FAILS = 5          # Number of incorrect attempts before lockout
LOCK_SECONDS = 600     # Lockout duration in seconds (10 minutes)
SESSION_LIFETIME = timedelta(hours=8)

# Transport security
IS_PRODUCTION = os.environ.get("RENDER") is not None or os.environ.get("FLASK_ENV") == "production"
HTTPS = os.environ.get("HTTPS") == "1" or IS_PRODUCTION
DEBUG = os.environ.get("FLASK_DEBUG", "0") == "1"

# Port (defaults to 5050 to avoid collision with PostgreSQL on local port 5000)
PORT = int(os.environ.get("PORT", 5050))
