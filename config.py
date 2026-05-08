from datetime import datetime
import os

class Config:
    """Общие настройки конфигурации приложения."""
    SECRET_KEY = 'super_secret_key_dev_123' # В production использовать переменные окружения!
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL', 'sqlite:///home_money.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False

class DevelopmentConfig(Config):
    """Конфигурация для разработки."""
    DEBUG = True

class ProductionConfig(Config):
    """Конфигурация для продакшена."""
    DEBUG = False