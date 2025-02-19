import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy.orm import Session
from db import SessionLocal
from models import ViewedProfile


# Настройка логов
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Создаем планировщик
scheduler = AsyncIOScheduler()


# Функция очистки таблицы viewed_profiles
def clear_viewed_profiles():
    with SessionLocal() as db:
        deleted_rows = db.query(ViewedProfile).delete()
        db.commit()
        logger.info(f"🗑 Очищено записей в viewed_profiles: {deleted_rows}")

        

# Добавляем задачу в планировщик
scheduler.add_job(clear_viewed_profiles, "interval", minutes=1)

