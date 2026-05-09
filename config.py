import os
from dotenv import load_dotenv

load_dotenv()


class Config:

    # Секрет для JWT
    SECRET_KEY = os.environ.get("HM_SECRET_KEY", "hm-dev-secret-key-32-bytes-min!!")

    # База данных
    DATABASE_URL = os.environ.get("HM_DATABASE_URL", "sqlite:///./home_money.db")

    # Telegram Bot
    BOT_TOKEN = os.environ.get("HM_BOT_TOKEN", "")

    # SOCKS прокси (оставьте пустым, если не нужен)
    BOT_PROXY_URL = os.environ.get("HM_BOT_PROXY_URL", "")

    # Кто может писать боту (через запятую Telegram ID, пусто = все)
    BOT_ALLOWED_USERS = os.environ.get("HM_BOT_ALLOWED_USERS", "")

    # Flask
    DEBUG = os.environ.get("HM_DEBUG", "true").lower() in ("true", "1", "yes")
