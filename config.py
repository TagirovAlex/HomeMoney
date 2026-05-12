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

    # SOCKS прокси (отдельные поля)
    BOT_PROXY_HOST = os.environ.get("HM_BOT_PROXY_HOST", "")
    BOT_PROXY_PORT = os.environ.get("HM_BOT_PROXY_PORT", "")
    BOT_PROXY_USERNAME = os.environ.get("HM_BOT_PROXY_USERNAME", "")
    BOT_PROXY_PASSWORD = os.environ.get("HM_BOT_PROXY_PASSWORD", "")

    @staticmethod
    def get_proxy_url() -> str:
        host = Config.BOT_PROXY_HOST
        if not host:
            return ""
        auth = ""
        if Config.BOT_PROXY_USERNAME and Config.BOT_PROXY_PASSWORD:
            auth = f"{Config.BOT_PROXY_USERNAME}:{Config.BOT_PROXY_PASSWORD}@"
        port = f":{Config.BOT_PROXY_PORT}" if Config.BOT_PROXY_PORT else ""
        return f"socks5://{auth}{host}{port}"



    # Кто может писать боту (через запятую Telegram ID, пусто = все)
    BOT_ALLOWED_USERS = os.environ.get("HM_BOT_ALLOWED_USERS", "")

    # Flask
    DEBUG = os.environ.get("HM_DEBUG", "true").lower() in ("true", "1", "yes")
