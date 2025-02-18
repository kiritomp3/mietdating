import asyncio
import logging
from aiogram import Bot, Dispatcher
from config import BOT_TOKEN  
from handlers import start, profile, browse

# Настраиваем логирование
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

dp.include_router(start.router)
dp.include_router(profile.router)
dp.include_router(browse.router)

async def main():
    logger.info("Бот запущен и готов к работе!")

    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())