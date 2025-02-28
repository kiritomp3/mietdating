import asyncio
import logging
from aiogram import Bot, Dispatcher
from config import BOT_TOKEN  
from handlers import profile, start, browse
import utils

# Настраиваем логирование
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

dp.include_router(start.router)
dp.include_router(profile.router)
dp.include_router(browse.router)

async def main():
    logging.info("Бот запущен! 🚀")
    
    # Запускаем планировщик в отдельной задаче
    utils.scheduler.start()
    asyncio.create_task(run_scheduler())

    # Запускаем бота
    await dp.start_polling(bot)

# Функция-обертка для планировщика (чтобы он работал в фоне)
async def run_scheduler():
    while True:
        await asyncio.sleep(1)

if __name__ == "__main__":
    asyncio.run(main())