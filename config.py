import os

BOT_TOKEN = "7000170472:AAFbSx3qSEpdSlAxbhqaQxfi_-GB-9O0RY4"

# Данные для подключения к PostgreSQL
DB_USER = "postgres"
DB_HOST = "localhost"
DB_PORT = "5432"
DB_NAME = "dating_bot"

# Создание строки подключения
DATABASE_URL = f"postgresql://{DB_USER}@{DB_HOST}:{DB_PORT}/{DB_NAME}"