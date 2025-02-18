import logging
from aiogram import Router, types
from aiogram.types import CallbackQuery
from sqlalchemy.sql import func
from db import SessionLocal
from models import User
from keyboards import get_browse_keyboard, main_menu

print("📌 browse.py загружен!")


router = Router()

# Настройка логирования
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Функция для поиска случайной анкеты
def get_random_profile(exclude_user_id: int):
    with SessionLocal() as db:
        print(f"🔍 Запрос анкеты, исключая user_id: {exclude_user_id}")  # 🚀 Отладка

        user = db.query(User).filter(
            User.id != exclude_user_id,
            User.is_active == True
        ).order_by(func.random()).first()

        if user:
            print(f"✅ Найдена анкета: {user.id}")  # 🚀 Отладка
        else:
            print("❌ Анкет не найдено!")  # 🚀 Отладка

        return user

# 🔍 Кнопка "Смотреть анкеты"
@router.message(lambda msg: msg.text == "👀 Смотреть анкеты")
async def browse_profiles(message: types.Message):
    print(f"🟢 Хэндлер просмотра анкет вызван пользователем {message.from_user.id}")
    user_id = message.from_user.id
    logger.info(f"Пользователь {user_id} начал просмотр анкет.")

    print(f"🔍 Ищу анкету для user_id: {user_id}")  # 🚀 Отладка

    user = get_random_profile(exclude_user_id=user_id)

    if user:
        print(f"✅ Найдена анкета: {user.id}")  # 🚀 Отладка
        profile_text = (f"📜 Анкета:\n\n"
                        f"👤 Имя: {user.name}\n"
                        f"🎂 Дата рождения: {user.birthdate}\n"
                        f"🏙 Город: {user.city}\n"
                        f"📝 Описание: {user.description if user.description else '—'}")
        
        if user.photo_id:
            await message.answer_photo(photo=user.photo_id, caption=profile_text, reply_markup=get_browse_keyboard())
        else:
            await message.answer(profile_text, reply_markup=get_browse_keyboard())
    else:
        print("❌ Нет доступных анкет!")  # 🚀 Отладка
        await message.answer("Нет доступных анкет.", reply_markup=main_menu)

# ❤️ Обработчик "Лайк"
@router.callback_query(lambda c: c.data == "like")
async def like_profile(callback: CallbackQuery):
    user_id = callback.from_user.id
    logger.info(f"Пользователь {user_id} поставил лайк.")

    await callback.answer("❤️ Лайк отправлен!")
    user = get_random_profile(exclude_user_id=user_id)

    if user:
        profile_text = (f"📜 Анкета:\n\n"
                        f"👤 Имя: {user.name}\n"
                        f"🎂 Дата рождения: {user.birthdate}\n"
                        f"🏙 Город: {user.city}\n"
                        f"📝 Описание: {user.description if user.description else '—'}")

        if user.photo_id:
            await callback.message.answer_photo(photo=user.photo_id, caption=profile_text, reply_markup=get_browse_keyboard())
        else:
            await callback.message.answer(profile_text, reply_markup=get_browse_keyboard())
    else:
        await callback.message.answer("Нет больше анкет.", reply_markup=main_menu)

# 💔 Обработчик "Дизлайк"
@router.callback_query(lambda c: c.data == "dislike")
async def dislike_profile(callback: CallbackQuery):
    user_id = callback.from_user.id
    logger.info(f"Пользователь {user_id} поставил дизлайк.")

    await callback.answer("💔 Дизлайк отправлен!")
    user = get_random_profile(exclude_user_id=user_id)

    if user:
        profile_text = (f"📜 Анкета:\n\n"
                        f"👤 Имя: {user.name}\n"
                        f"🎂 Дата рождения: {user.birthdate}\n"
                        f"🏙 Город: {user.city}\n"
                        f"📝 Описание: {user.description if user.description else '—'}")

        if user.photo_id:
            await callback.message.answer_photo(photo=user.photo_id, caption=profile_text, reply_markup=get_browse_keyboard())
        else:
            await callback.message.answer(profile_text, reply_markup=get_browse_keyboard())
    else:
        await callback.message.answer("Нет больше анкет.", reply_markup=main_menu)