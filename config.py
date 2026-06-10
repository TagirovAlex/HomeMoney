import os
from dotenv import load_dotenv

load_dotenv()


class Config:

    # Секрет для JWT — ОБЯЗАТЕЛЕН в production
    _SECRET_KEY = os.environ.get("HM_SECRET_KEY")
    if not _SECRET_KEY:
        import logging
        _debug = os.environ.get("HM_DEBUG", "false").lower() in ("true", "1", "yes")
        if not _debug:
            raise RuntimeError("HM_SECRET_KEY не задан! Установите его в .env для production.")
        logging.warning("HM_SECRET_KEY не задан. Используется DEVELOPMENT-ключ! Установите HM_SECRET_KEY в .env")
        _SECRET_KEY = "hm-dev-secret-key-32-bytes-min!!"
    SECRET_KEY = _SECRET_KEY

    # Refresh token (30 дней по умолчанию)
    REFRESH_TOKEN_EXPIRE_DAYS = int(os.environ.get("HM_REFRESH_TOKEN_EXPIRE_DAYS", "30"))

    # База данных
    DATABASE_URL = os.environ.get("HM_DATABASE_URL", "sqlite:///./instance/home_money.db")

    # Директория для бэкапов (должна быть вне webroot)
    BACKUP_DIR = os.environ.get("HM_BACKUP_DIR", "backups")

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

    @staticmethod
    def get_proxy_params() -> dict | None:
        host = Config.BOT_PROXY_HOST
        if not host:
            return None
        return {
            "host": host,
            "port": int(Config.BOT_PROXY_PORT) if Config.BOT_PROXY_PORT else 1080,
            "username": Config.BOT_PROXY_USERNAME or None,
            "password": Config.BOT_PROXY_PASSWORD or None,
        }

    # Кто может писать боту (через запятую Telegram ID, пусто = все)
    BOT_ALLOWED_USERS = os.environ.get("HM_BOT_ALLOWED_USERS", "")

    # Dashboard
    DASHBOARD_TX_LIMIT = int(os.environ.get("HM_DASHBOARD_TX_LIMIT", "5"))

    # Flask
    DEBUG = os.environ.get("HM_DEBUG", "false").lower() in ("true", "1", "yes")
