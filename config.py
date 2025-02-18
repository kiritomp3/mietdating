import os

# Токен бота (его лучше хранить в .env)
BOT_TOKEN = ""

# Данные для подключения к PostgreSQL
DB_USER = "postgres"
DB_HOST = "localhost"
DB_PORT = "5432"
DB_NAME = "dating_bot"

# Создание строки подключения
DATABASE_URL = f"postgresql://{DB_USER}@{DB_HOST}:{DB_PORT}/{DB_NAME}"