import logging
from aiogram import Router, types
from aiogram.types import CallbackQuery
from sqlalchemy.sql import func
from sqlalchemy.orm import Session
from db import SessionLocal
from models import User, Like, ViewedProfile
from keyboards import get_browse_keyboard, main_menu
from datetime import datetime, timedelta
from sqlalchemy import and_
from handlers.profile import calculate_age

print("📌 browse.py загружен!")
router = Router()

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Функция для поиска случайной анкеты
def get_random_profile(exclude_user_id: int):
    with SessionLocal() as db:
        five_minutes_ago = datetime.utcnow() - timedelta(minutes=5)

        recently_viewed = db.query(ViewedProfile.target_id).filter(
            and_(
                ViewedProfile.user_id == exclude_user_id,
                ViewedProfile.viewed_at >= five_minutes_ago
            )
        ).subquery()

        user = db.query(User).filter(
            and_(
                User.id != exclude_user_id,
                User.is_active == True,
                ~User.id.in_(recently_viewed)
            )
        ).order_by(func.random()).first()

        if user:
            # Сохраняем просмотр
            viewed = ViewedProfile(user_id=exclude_user_id, target_id=user.id)
            db.add(viewed)
            db.commit()

            # Возвращаем данные как словарь
            return {
                "id": user.id,
                "name": user.name,
                "birthdate": user.birthdate,
                "city": user.city,
                "description": user.description,
                "photo_id": user.photo_id
            }

    return None  # Если нет доступных анкет

# 🔍 Кнопка "Смотреть анкеты"
@router.message(lambda msg: msg.text == "Смотреть анкеты")
async def browse_profiles(message: types.Message):
    user_id = message.from_user.id
    logger.info(f"Пользователь {user_id} начал просмотр анкет.")
    
    user = get_random_profile(exclude_user_id=user_id)
    
    if user:
        age = calculate_age(user["birthdate"])
        profile_text = (
            f"{user['name']}, "
            f"{age}, "
            f"{user['city']} — "
            f"{user['description'] if user['description'] else ''}"
        )
        keyboard = get_browse_keyboard(user["id"])

        if user["photo_id"]:
            await message.answer_photo(photo=user["photo_id"], caption=profile_text, reply_markup=keyboard)
        else:
            await message.answer(profile_text, reply_markup=keyboard)
    else:
        await message.answer("Доступные анкеты закончились.", reply_markup=main_menu)

# ❤️ Обработчик "Лайк"
@router.callback_query(lambda c: c.data.startswith("like:"))
async def like_profile(callback: CallbackQuery):
    user_id = callback.from_user.id
    target_user_id = int(callback.data.split(":")[1])  # Получаем ID анкеты из callback_data

    with SessionLocal() as db:
        # Добавляем лайк в БД
        like = Like(user_id=user_id, liked_user_id=target_user_id)
        db.add(like)
        db.commit()

        # Проверяем взаимный лайк
        mutual_like = db.query(Like).filter_by(user_id=target_user_id, liked_user_id=user_id).first()
        if mutual_like:
            # Удаляем лайки из БД
            db.delete(like)
            db.delete(mutual_like)
            db.commit()

            # Получаем информацию о пользователях
            target_user = db.query(User).filter_by(id=target_user_id).first()
            user = db.query(User).filter_by(id=user_id).first()

            # Отправляем сообщение о совпадении
            username_text = f"🎉 У вас новый мэтч!\n @{target_user.username}"
            await callback.bot.send_message(user_id, username_text)

            await callback.bot.send_message(target_user_id, f"🎉 У вас новый мэтч!\n@{user.username}")
        else:
            # Отправляем лайкнутому пользователю анкету того, кто его лайкнул с кнопками "Лайк" и "Дизлайк"
            liker = db.query(User).filter_by(id=user_id).first()
            if liker:  # Проверяем, что liker найден
                age = calculate_age(liker.birthdate)
                profile_text = (f"💌 Вы понравились!\n\n"
                                f"{liker.name}, "
                                f"{age}, "
                                f"{liker.city}  — "
                                f"{liker.description if liker.description else ''}")

                keyboard = get_browse_keyboard(liker.id)

                if liker.photo_id:
                    await callback.bot.send_photo(chat_id=target_user_id, photo=liker.photo_id, caption=profile_text, reply_markup=keyboard)
                else:
                    await callback.bot.send_message(chat_id=target_user_id, text=profile_text, reply_markup=keyboard)

            # Отправляем новую анкету только если лайк НЕ был взаимным
            await send_new_profile(callback)

    await callback.answer("❤️ Лайк отправлен!")

# 💔 Обработчик "Дизлайк"
@router.callback_query(lambda c: c.data.startswith("dislike:"))
async def dislike_profile(callback: CallbackQuery):
    user_id = callback.from_user.id
    target_id = int(callback.data.split(":")[1])  # Получаем ID анкеты

    logger.info(f"Пользователь {user_id} поставил дизлайк анкете {target_id}.")
    await callback.answer("💔")
    
    await send_new_profile(callback)

# Функция для отправки новой анкеты
async def send_new_profile(callback: CallbackQuery):
    user_id = callback.from_user.id
    user = get_random_profile(exclude_user_id=user_id)
    if user:
        age = calculate_age(user["birthdate"])
        profile_text = (
            f"{user['name']}, "
            f"{age}, "
            f"{user['city']}  — "
            f"{user['description'] if user['description'] else ''}"
        )
        keyboard = get_browse_keyboard(user["id"])  # Передаем ID анкеты в кнопку

        if user["photo_id"]:
            await callback.message.answer_photo(photo=user["photo_id"], caption=profile_text, reply_markup=keyboard)
        else:
            await callback.message.answer(profile_text, reply_markup=keyboard)
    else:
        await callback.message.answer("Доступные анкеты закончились.", reply_markup=main_menu)