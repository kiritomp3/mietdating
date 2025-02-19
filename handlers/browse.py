import logging
from aiogram import Router, types
from aiogram.types import CallbackQuery
from sqlalchemy.sql import func
from sqlalchemy.orm import Session
from db import SessionLocal
from models import User, Like
from keyboards import get_browse_keyboard, main_menu

print("📌 browse.py загружен!")
router = Router()

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Функция для поиска случайной анкеты
def get_random_profile(exclude_user_id: int):
    with SessionLocal() as db:
        user = db.query(User).filter(
            User.id != exclude_user_id,
            User.is_active == True
        ).order_by(func.random()).first()
        return user

# Функция сохранения лайка в БД
def save_like(user_id: int, liked_user_id: int):
    with SessionLocal() as db:
        # Проверяем, есть ли взаимный лайк
        existing_like = db.query(Like).filter(
            Like.user_id == liked_user_id,
            Like.liked_user_id == user_id
        ).first()

        if existing_like:
            existing_like.is_mutual = True
            db.commit()
            return True  # Взаимный лайк
        else:
            new_like = Like(user_id=user_id, liked_user_id=liked_user_id, is_mutual=False)
            db.add(new_like)
            db.commit()
            return False  # Обычный лайк

# 🔍 Кнопка "Смотреть анкеты"
@router.message(lambda msg: msg.text == "👀 Смотреть анкеты")
async def browse_profiles(message: types.Message):
    user_id = message.from_user.id
    logger.info(f"Пользователь {user_id} начал просмотр анкет.")
    
    user = get_random_profile(exclude_user_id=user_id)
    if user:
        profile_text = (
            f"📜 Анкета:\n\n"
            f"👤 Имя: {user.name}\n"
            f"🎂 Дата рождения: {user.birthdate}\n"
            f"🏙 Город: {user.city}\n"
            f"📝 Описание: {user.description if user.description else '—'}"
        )
        keyboard = get_browse_keyboard(user.id)  # Теперь передаем ID анкеты в кнопку!

        if user.photo_id:
            await message.answer_photo(photo=user.photo_id, caption=profile_text, reply_markup=keyboard)
        else:
            await message.answer(profile_text, reply_markup=keyboard)
    else:
        await message.answer("Нет доступных анкет.", reply_markup=main_menu)

# ❤️ Обработчик "Лайк"
@router.callback_query(lambda c: c.data.startswith("like:"))
async def like_profile(callback: CallbackQuery):
    user_id = callback.from_user.id
    target_user_id = int(callback.data.split(":")[1])  # Получаем ID анкеты из callback_data

    with SessionLocal() as db:
        # Проверяем, лайкал ли этот пользователь уже
        existing_like = db.query(Like).filter_by(user_id=user_id, liked_user_id=target_user_id).first()
        if existing_like:
            await callback.answer("Вы уже лайкали эту анкету!")
            return
        
        # Добавляем лайк в БД
        like = Like(user_id=user_id, liked_user_id=target_user_id)
        db.add(like)
        db.commit()

        # Проверяем взаимный лайк
        mutual_like = db.query(Like).filter_by(user_id=target_user_id, liked_user_id=user_id).first()
        if mutual_like:
            like.is_mutual = True
            mutual_like.is_mutual = True
            db.commit()

            # Взаимный лайк — отправляем username только лайкнутого пользователя
            target_user = db.query(User).filter_by(id=target_user_id).first()

            username_text = f"👤 Свяжитесь с пользователем: @{target_user.username}"
            await callback.bot.send_message(user_id, username_text)
        else:
            # Отправляем лайкнутому пользователю анкету того, кто его лайкнул с кнопками "Лайк" и "Дизлайк"
            liker = db.query(User).filter_by(id=user_id).first()
            profile_text = (f"💌 Вы понравились!\n\n"
                            f"👤 Имя: {liker.name}\n"
                            f"🎂 Дата рождения: {liker.birthdate}\n"
                            f"🏙 Город: {liker.city}\n"
                            f"📝 Описание: {liker.description if liker.description else '—'}")

            keyboard = get_browse_keyboard(liker.id)  # Кнопки "Лайк" и "Дизлайк"

            if liker.photo_id:
                await callback.bot.send_photo(chat_id=target_user_id, photo=liker.photo_id, caption=profile_text, reply_markup=keyboard)
            else:
                await callback.bot.send_message(chat_id=target_user_id, text=profile_text, reply_markup=keyboard)

    await callback.answer("❤️ Лайк отправлен!")

    # Показываем следующую анкету
    await send_new_profile(callback)

# 💔 Обработчик "Дизлайк"
@router.callback_query(lambda c: c.data.startswith("dislike:"))
async def dislike_profile(callback: CallbackQuery):
    user_id = callback.from_user.id
    target_id = int(callback.data.split(":")[1])  # Получаем ID анкеты

    logger.info(f"Пользователь {user_id} поставил дизлайк анкете {target_id}.")
    await callback.answer("💔 Дизлайк отправлен!")
    
    await send_new_profile(callback)

# Функция для отправки новой анкеты
async def send_new_profile(callback: CallbackQuery):
    user_id = callback.from_user.id
    user = get_random_profile(exclude_user_id=user_id)

    if user:
        profile_text = (
            f"📜 Анкета:\n\n"
            f"👤 Имя: {user.name}\n"
            f"🎂 Дата рождения: {user.birthdate}\n"
            f"🏙 Город: {user.city}\n"
            f"📝 Описание: {user.description if user.description else '—'}"
        )
        keyboard = get_browse_keyboard(user.id)  # Передаем ID анкеты в кнопку

        if user.photo_id:
            await callback.message.answer_photo(photo=user.photo_id, caption=profile_text, reply_markup=keyboard)
        else:
            await callback.message.answer(profile_text, reply_markup=keyboard)
    else:
        await callback.message.answer("Нет больше анкет.", reply_markup=main_menu)