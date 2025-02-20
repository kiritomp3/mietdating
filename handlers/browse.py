import logging
import sqlite3
from aiogram import Router, types
from aiogram.types import CallbackQuery
from db import DATABASE_PATH, get_random_profile, like_profile, add_viewed_profile
from keyboards import get_browse_keyboard, main_menu
from datetime import datetime, timedelta
from handlers.profile import calculate_age
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

print("📌 browse.py загружен!")
router = Router()

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# 🔍 Кнопка "Смотреть анкеты"
@router.message(lambda msg: msg.text == "Смотреть анкеты")
async def browse_profiles(message: types.Message):
    user_id = message.from_user.id
    logger.info(f"Пользователь {user_id} начал просмотр анкет.")

    user = get_random_profile(user_id)

    if user:
        age = calculate_age(user["date_of_birth"]) if user["date_of_birth"] else "Не указан"
        profile_text = (
            f"{user['first_name']}, {age}, {user['city']} — {user['biography']}"
        )
        keyboard = get_browse_keyboard(user["id"])

        if user["photo"]:
            await message.answer_photo(photo=user["photo"], caption=profile_text, reply_markup=keyboard)
        else:
            await message.answer(profile_text, reply_markup=keyboard)
    else:
        await message.answer("Доступные анкеты закончились.", reply_markup=main_menu)

# ❤️ Обработчик "Лайк"
@router.callback_query(lambda c: c.data.startswith("like:"))
async def like_profile_callback(callback: CallbackQuery):
    user_id = callback.from_user.id
    target_user_id = int(callback.data.split(":")[1])  # Получаем ID анкеты

    is_mutual = like_profile(user_id, target_user_id)

    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    cursor.execute("SELECT username FROM users WHERE user_tg_id = ?", (target_user_id,))
    target_username = cursor.fetchone()[0]

    cursor.execute("SELECT username FROM users WHERE user_tg_id = ?", (user_id,))
    user_username = cursor.fetchone()[0]


    if is_mutual:

        cursor.execute("DELETE FROM likes WHERE who_chose = ? AND who_was_chosen = ?", (user_id, target_user_id))
        cursor.execute("DELETE FROM likes WHERE who_chose = ? AND who_was_chosen = ?", (target_user_id, user_id))
        conn.commit()


        # ✅ Отправляем уведомления о взаимном лайке
        await callback.bot.send_message(user_id, f"🎉 У вас новый мэтч!\n @{target_username}")
        await callback.bot.send_message(target_user_id, f"🎉 У вас новый мэтч!\n @{user_username}")
    else:
        # ✅ Отправляем лайкнутому пользователю анкету того, кто его лайкнул
        liker = get_random_profile(target_user_id)  # Получаем анкету лайкнувшего

        if liker:
            age = calculate_age(liker["date_of_birth"]) if liker["date_of_birth"] else "Не указан"
            profile_text = (f"💌 Вы понравились:\n\n"
                            f"{liker['first_name']}, {age}, {liker['city']}  — {liker['biography']}")

            keyboard = get_browse_keyboard(liker["id"])

            if liker["photo"]:
                await callback.bot.send_photo(chat_id=target_user_id, photo=liker["photo"], caption=profile_text, reply_markup=keyboard)
            else:
                await callback.bot.send_message(chat_id=target_user_id, text=profile_text, reply_markup=keyboard)
    conn.close()
    
    await callback.answer("❤️ Лайк отправлен!")
    await send_new_profile(callback)

# 💔 Обработчик "Дизлайк"
@router.callback_query(lambda c: c.data.startswith("dislike:"))
async def dislike_profile(callback: CallbackQuery):
    user_id = callback.from_user.id
    target_id = int(callback.data.split(":")[1])  # Получаем ID анкеты

    logger.info(f"Пользователь {user_id} поставил дизлайк анкете {target_id}.")
    await callback.answer("💔")

    await send_new_profile(callback)

class SpamState(StatesGroup):
    waiting_for_text = State()

# 📩 Обработчик спам кнопки
@router.callback_query(lambda c: c.data.startswith("spam:"))
async def spam_profile(callback: CallbackQuery, state: FSMContext):
    """Обработчик нажатия кнопки 'spam'"""
    user_id = callback.from_user.id
    target_user_id = int(callback.data.split(":")[1])  # ID анкеты

    # Сохраняем ID получателя в FSM-состоянии
    await state.update_data(target_user_id=target_user_id)

    await callback.message.answer("📩 Введите текст, который хотите отправить пользователю:")
    await state.set_state(SpamState.waiting_for_text)

    await callback.answer()  # Закрываем callback-запрос

@router.message(SpamState.waiting_for_text)
async def send_spam_message(message: types.Message, state: FSMContext):
    """Получение текста от пользователя и отправка 'spam' сообщения"""
    user_id = message.from_user.id
    user_text = message.text  # Получаем текст от пользователя

    data = await state.get_data()
    target_user_id = data.get("target_user_id")  # Получаем ID получателя

    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()

    # ✅ Исправленный запрос (добавлен LEFT JOIN для фото)
    cursor.execute("""
        SELECT u.first_name, u.date_of_birth, u.city, u.biography, p.photo 
        FROM users u
        LEFT JOIN photos p ON u.user_tg_id = p.user_tg_id
        WHERE u.user_tg_id = ?
    """, (user_id,))
    sender = cursor.fetchone()
    conn.close()

    if not sender:
        await message.answer("⚠ Ошибка: пользователь не найден.")
        await state.clear()
        return

    age = calculate_age(sender[1]) if sender[1] else "Не указан"
    profile_text = (f"🌞 Вы понравились:\n\n"
                    f"{sender[0]}, {age}, {sender[2] if sender[2] else 'Не указан'}\n"
                    f"{sender[3] if sender[3] else 'Описание отсутствует'}\n\n"
                    f"💬 Сообщение: {user_text}")

    keyboard = get_browse_keyboard(user_id)  # Кнопки "Лайк" и "Дизлайк"

    # Отправляем анкету + сообщение
    if sender[4]:  # Фото
        await message.bot.send_photo(chat_id=target_user_id, photo=sender[4], caption=profile_text, reply_markup=keyboard)
    else:
        await message.bot.send_message(chat_id=target_user_id, text=profile_text, reply_markup=keyboard)

    await message.answer("✅ Сообщение отправлено!")
    await send_new_profile(message)
    await state.clear()

# Функция для отправки новой анкеты
async def send_new_profile(callback):
    user_id = callback.from_user.id  # ✅ Работает и для Message, и для CallbackQuery
    user = get_random_profile(user_id)

    if user:
        age = calculate_age(user["date_of_birth"]) if user["date_of_birth"] else "Не указан"
        profile_text = (
            f"{user['first_name']}, {age}, {user['city']} — {user['biography']}"
        )
        keyboard = get_browse_keyboard(user["id"])  # Передаем ID анкеты в кнопку

        # ✅ Проверяем, является ли callback объектом Message или CallbackQuery
        if isinstance(callback, CallbackQuery):
            target = callback.message
        else:  # Значит, это объект Message
            target = callback

        if user["photo"]:
            await target.answer_photo(photo=user["photo"], caption=profile_text, reply_markup=keyboard)
        else:
            await target.answer(profile_text, reply_markup=keyboard)
    else:
        if isinstance(callback, CallbackQuery):
            await callback.message.answer("Доступные анкеты закончились.", reply_markup=main_menu)
        else:
            await callback.answer("Доступные анкеты закончились.", reply_markup=main_menu)