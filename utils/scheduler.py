import logging
import sqlite3
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from db import DATABASE_PATH

# Настройка логов
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Создаем планировщик
scheduler = AsyncIOScheduler()

# Функция очистки таблицы viewed_profiles
def clear_viewed_profiles():
    """Удаляет записи из таблицы просмотренных профилей"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    cursor.execute("DELETE FROM viewed_profiles")
    conn.commit()
    
    deleted_rows = cursor.rowcount
    conn.close()
    
    logger.info(f"🗑 Очищено записей в viewed_profiles: {deleted_rows}")

# Добавляем задачу в планировщик
scheduler.add_job(clear_viewed_profiles, "interval", minutes=1) 