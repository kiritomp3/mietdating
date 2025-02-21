import os

BOT_TOKEN = "7544081250:AAHhkAQ4ZbiR-FLUw7mcacCqSaBbJA4SEWw"

# Данные для подключения к PostgreSQL
DB_USER = "postgres"
DB_HOST = "localhost"
DB_PORT = "5432"
DB_NAME = "dating_bot"

# Создание строки подключения
DATABASE_URL = f"postgresql://{DB_USER}@{DB_HOST}:{DB_PORT}/{DB_NAME}"