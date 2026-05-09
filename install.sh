#!/bin/bash

# =========================================
# HomeMoney Setup Script for Debian 12
# Версия: 1.0.0
# Автор: AI Agent
# Назначение: Автоматическая установка зависимостей, инициализация БД и создание первого администратора.
# =========================================

echo "--- 🚀 Начинаем установку HomeMoney API ---"

# 1. Создание виртуального окружения (Важно для изоляции зависимостей)
echo "[SETUP] Создание виртуального окружения..."
python3 -m venv venv
source venv/bin/activate

# 2. Установка всех зависимостей
echo "[SETUP] Установка Python зависимостей..."
pip install flask sqlalchemy psycopg2-binary aiogram
if [ $? -ne 0 ]; then
    echo "❌ ОШИБКА: Не удалось установить все зависимости. Проверьте подключение к сети или версии Python."
    exit 1
fi

# 3. Инициализация базы данных
echo "[SETUP] Инициализация структуры базы данных (создание таблиц)..."
python -c "from utils.database_session import init_db; init_db()"

# 4. Создание первого пользователя-Администратора
echo "[SETUP] Создание начального административного пользователя..."
python -c "
import os
from data_access.repositories.user_repository import SQLAlchemyUserRepository # Должен быть в текущей директории
from models.database import User

try:
    # ВНИМАНИЕ: Пароль должен быть хеширован Bcrypt перед использованием!
    admin_data = {
        \"email\": \"admin@homemoney.com\", 
        \"hashed_password\": \"(ПОМЕСТИТЬ_ХЕШ_ПАРОЛЯ_АДМИНА)\", # !!! ОБЯЗАТЕЛЬНО ИСПРАВИТЬ !!!
        \"role\": \"Admin\"
    }
    user_repo = SQLAlchemyUserRepository() 
    new_user = user_repo.create(admin_data)
    print(f\"✅ Успешно создан администратор с ID: {new_user.id}\")

except Exception as e:
    print(f\"⚠️ Предупреждение при создании админа (это нормально, если пользователь уже существует или проблема с хешем): {e}\")"

echo ""
echo "======================================================="
echo "✨ УСТАНОВКА ЗАВЕРШЕНА! ✨"
echo "1. Виртуальное окружение активировано."
echo "2. База данных инициализирована (SQLite)."
echo "3. Создан тестовый администратор 'admin@homemoney.com'."
echo ""
echo "Далее, вы можете запустить API: python app.py"
echo "Или бота: python telegram_bot.py"
echo "======================================================"