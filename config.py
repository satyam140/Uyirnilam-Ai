import os

from dotenv import load_dotenv

load_dotenv()


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-only-change-me")
    DEMO_MODE = os.getenv("DEMO_MODE", "true").lower() == "true"
    DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///uyirnilam.db")
    PORT = int(os.getenv("PORT", "5000"))
    DEBUG = os.getenv("FLASK_ENV", "development") == "development"
    MAX_CONTENT_LENGTH = 8 * 1024 * 1024
    CLAUDE_API_KEY = os.getenv("CLAUDE_API_KEY", "")
    CLAUDE_MODEL = os.getenv("CLAUDE_MODEL", "claude-sonnet-4-20250514")
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
    GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
