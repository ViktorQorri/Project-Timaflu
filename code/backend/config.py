import os
import secrets
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent / ".env")


class Config:
    """Settings read from environment variables. See .env.example for the names."""

    DB_HOST = os.getenv("DB_HOST") or "localhost"
    DB_PORT = int(os.getenv("DB_PORT") or "3306")
    DB_NAME = os.getenv("DB_NAME") or "timaflu"
    DB_USER = os.getenv("DB_USER") or "timaflu_app"
    DB_PASSWORD = os.getenv("DB_PASSWORD", "")
    # Without a fixed key, flash messages only survive until the next restart.
    SECRET_KEY = os.getenv("SECRET_KEY") or secrets.token_hex(32)
