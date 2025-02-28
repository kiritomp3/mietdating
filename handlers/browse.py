import logging
import sqlite3
import asyncio
from aiogram import Router, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from db import DATABASE_PATH, get_random_profile, like_profile, add_viewed_profile
from keyboards import main_menu
from datetime import datetime
from handlers.profile import calculate_age
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

print("📌 browse.py загружен!")
router = Router()

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Определяем состояния FSM
class BrowseState(StatesGroup):
    browsing = State()
    waiting_for_spam_text = State()

# Клавиатура для просмотра анкет
browse_menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="❤️"), KeyboardButton(text="👎")],
        [KeyboardButton(text="😴")],
        # KeyboardButton(text="🚀 Спам"),
    ],
    resize_keyboard=True
)

# Начало просмотра анкет
@router.message(lambda msg: msg.text == "Поиск")
async def browse_profiles(message: types.Message, state: FSMContext):
    """Начало просмотра анкет"""
    user_id = message.from_user.id
    logger.info(f"Пользователь {user_id} начал просмотр анкет.")

    conn = sqlite3.connect(DATABASE_PATH)
    # Устанавливаем row_factory для получения результата в виде словаря
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Проверяем, не женат ли пользователь
    cursor.execute("SELECT is_active FROM users WHERE user_tg_id = ?", (user_id,))
    user_status = cursor.fetchone()
    if user_status and user_status["is_active"] == 0:
        await message.answer("Поиск анкет для вас недоступен, так как вы указали, что женаты/замужем.", reply_markup=main_menu)
        conn.close()
        return

    # Получаем пользователей, которые лайкнули текущего пользователя
    cursor.execute("""
        SELECT who_chose FROM likes WHERE who_was_chosen = ?
        ORDER BY RANDOM()
        LIMIT 1
    """, (user_id,))
    liked_user = cursor.fetchone()

    if liked_user:
        liked_user_id = liked_user["who_chose"]
        # Получаем анкету лайкнувшего с новыми полями lp и module
        cursor.execute("""
            SELECT u.user_tg_id, u.first_name, u.date_of_birth, u.city, u.biography, p.photo, u.lp, u.module
            FROM users u
            LEFT JOIN photos p ON u.user_tg_id = p.user_tg_id
            WHERE u.user_tg_id = ?
        """, (liked_user_id,))
        user = cursor.fetchone()
        if user:
            profile_dict = {
                "id": user["user_tg_id"],
                "first_name": user["first_name"],
                "date_of_birth": user["date_of_birth"],
                "city": user["city"],
                "biography": user["biography"],
                "photo": user["photo"],
                "lp": user["lp"],
                "module": user["module"],
            }
            await state.update_data(current_profile=profile_dict)

            age = calculate_age(user["date_of_birth"]) if user["date_of_birth"] else "Не указан"
            profile_text = (
                f"💌 Вы понравились:\n\n"
                f"{user['first_name']}, {age}, {user['city']} — {user['biography']}\n"
                f"ЛП: {user['lp'] if user['lp'] is not None else 'Не указан'}, "
                f"Модуль: {user['module'] if user['module'] else 'Не указан'}"
            )

            if user["photo"]:
                await message.answer_photo(photo=user["photo"], caption=profile_text, reply_markup=browse_menu)
            else:
                await message.answer(profile_text, reply_markup=browse_menu)

            conn.close()
            return

    # Если лайкнувшие отсутствуют, показываем случайные анкеты
    user = get_random_profile(user_id)  # Функция возвращает dict с ключами
    if user:
        await state.update_data(current_profile=user)
        age = calculate_age(user["date_of_birth"]) if user["date_of_birth"] else "Не указан"
        profile_text = (
            f"{user['first_name']}, {age}, {user['city'] if user['city'] else 'Не указан'} — "
            f"{user['biography'] if user['biography'] else 'Описание отсутствует'}\n"
            f"ЛП: {user.get('lp', 'Не указан')}, Модуль: {user.get('module', 'Не указан')}"
        )

        if user["photo"]:
            await message.answer_photo(photo=user["photo"], caption=profile_text, reply_markup=browse_menu)
        else:
            await message.answer(profile_text, reply_markup=browse_menu)

        await state.set_state(BrowseState.browsing)
    else:
        await message.answer("Доступные анкеты закончились.", reply_markup=main_menu)

    conn.close()

# Обработчик "Лайк"
@router.message(lambda msg: msg.text == "❤️")
async def like_profile_action(message: types.Message, state: FSMContext):
    """Обрабатывает лайк пользователя и проверяет мэтч"""
    data = await state.get_data()

    if "current_profile" not in data:
        await message.answer("🔄 Загрузка новой анкеты...")
        await send_new_profile(message, state)
        return

    user_id = message.from_user.id
    target_user_id = data["current_profile"]["id"]

    logger.info(f"🔍 Пользователь {user_id} лайкает анкету {target_user_id}")

    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("INSERT INTO likes (who_chose, who_was_chosen) VALUES (?, ?)", (user_id, target_user_id))
    conn.commit()

    cursor.execute("SELECT id FROM likes WHERE who_chose = ? AND who_was_chosen = ?", (target_user_id, user_id))
    mutual_like = cursor.fetchone()
    if mutual_like:
        logger.info(f"✅ Мэтч! {user_id} и {target_user_id} взаимно лайкнули друг друга.")
        cursor.execute("DELETE FROM likes WHERE (who_chose = ? AND who_was_chosen = ?) OR (who_chose = ? AND who_was_chosen = ?)",
                       (user_id, target_user_id, target_user_id, user_id))
        cursor.execute("UPDATE users SET likes_received = likes_received - 1 WHERE user_tg_id = ? AND likes_received > 0", (user_id,))
        cursor.execute("UPDATE users SET likes_received = likes_received - 1 WHERE user_tg_id = ? AND likes_received > 0", (target_user_id,))
        conn.commit()

        cursor.execute("SELECT username FROM users WHERE user_tg_id = ?", (target_user_id,))
        target_username = cursor.fetchone()["username"]

        cursor.execute("SELECT username FROM users WHERE user_tg_id = ?", (user_id,))
        user_username = cursor.fetchone()["username"]

        cursor.execute("SELECT likes_received FROM users WHERE user_tg_id = ?", (target_user_id,))
        target_likes_count = cursor.fetchone()["likes_received"]

        cursor.execute("SELECT likes_received FROM users WHERE user_tg_id = ?", (user_id,))
        user_likes_count = cursor.fetchone()["likes_received"]

        conn.close()

        await message.bot.send_message(user_id, f"🎉 У вас новый мэтч!\n @{target_username}\n💌 Осталось симпатий: {user_likes_count}")
        await message.bot.send_message(target_user_id, f"🎉 У вас новый мэтч!\n @{user_username}\n💌 Осталось симпатий: {target_likes_count}")
    else:
        logger.info(f"🚀 Нет взаимного лайка. {user_id} просто лайкнул {target_user_id}")
        cursor.execute("UPDATE users SET likes_received = likes_received + 1 WHERE user_tg_id = ?", (target_user_id,))
        conn.commit()
        cursor.execute("SELECT likes_received FROM users WHERE user_tg_id = ?", (target_user_id,))
        likes_count = cursor.fetchone()["likes_received"]
        conn.close()
        await message.bot.send_message(target_user_id, f"💌 Вы понравились ({likes_count} пользователям).")

    await message.answer("❤️ Лайк отправлен!")
    await send_new_profile(message, state)

# Обработчик "Дизлайк"
@router.message(lambda msg: msg.text == "👎")
async def dislike_profile_action(message: types.Message, state: FSMContext):
    logger.info(f"Пользователь {message.from_user.id} поставил дизлайк.")
    await send_new_profile(message, state)

# Обработчик "Спам"
@router.message(lambda msg: msg.text == "🚀 Спам")
async def spam_profile_action(message: types.Message, state: FSMContext):
    """Обрабатывает спам пользователя и проверяет мэтч"""
    data = await state.get_data()
    
    if "current_profile" not in data:
        await message.answer("🔄 Загрузка новой анкеты...")
        await send_new_profile(message, state)
        return

    user_id = message.from_user.id
    target_user_id = data["current_profile"]["id"]

    logger.info(f"🔍 Пользователь {user_id} использует 'Спам' для анкеты {target_user_id}")

    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("INSERT INTO likes (who_chose, who_was_chosen) VALUES (?, ?)", (user_id, target_user_id))
    conn.commit()

    cursor.execute("SELECT id FROM likes WHERE who_chose = ? AND who_was_chosen = ?", (target_user_id, user_id))
    mutual_like = cursor.fetchone()

    if mutual_like:
        logger.info(f"✅ Мэтч! {user_id} и {target_user_id} взаимно лайкнули друг друга.")
        cursor.execute("DELETE FROM likes WHERE (who_chose = ? AND who_was_chosen = ?) OR (who_chose = ? AND who_was_chosen = ?)",
                       (user_id, target_user_id, target_user_id, user_id))
        cursor.execute("UPDATE users SET likes_received = likes_received - 1 WHERE user_tg_id = ? AND likes_received > 0", (user_id,))
        cursor.execute("UPDATE users SET likes_received = likes_received - 1 WHERE user_tg_id = ? AND likes_received > 0", (target_user_id,))
        conn.commit()

        cursor.execute("SELECT username FROM users WHERE user_tg_id = ?", (target_user_id,))
        target_username = cursor.fetchone()["username"]

        cursor.execute("SELECT username FROM users WHERE user_tg_id = ?", (user_id,))
        user_username = cursor.fetchone()["username"]

        cursor.execute("SELECT likes_received FROM users WHERE user_tg_id = ?", (target_user_id,))
        target_likes_count = cursor.fetchone()["likes_received"]

        cursor.execute("SELECT likes_received FROM users WHERE user_tg_id = ?", (user_id,))
        user_likes_count = cursor.fetchone()["likes_received"]

        conn.close()

        await message.bot.send_message(user_id, f"🎉 У вас новый мэтч!\n @{target_username}\n💌 Осталось симпатий: {user_likes_count}")
        await message.bot.send_message(target_user_id, f"🎉 У вас новый мэтч!\n @{user_username}\n💌 Осталось симпатий: {target_likes_count}")
        await message.answer("❤️ Мэтч! Переходим к следующей анкете...")
        await send_new_profile(message, state)
    else:
        logger.info(f"🚀 Нет взаимного лайка. {user_id} использует 'Спам' для {target_user_id}")
        cursor.execute("UPDATE users SET likes_received = likes_received + 1 WHERE user_tg_id = ?", (target_user_id,))
        conn.commit()
        cursor.execute("SELECT likes_received FROM users WHERE user_tg_id = ?", (target_user_id,))
        likes_count = cursor.fetchone()["likes_received"]
        conn.close()
        await message.bot.send_message(target_user_id, f"💌 Вы понравились ({likes_count} пользователям).")
        await state.update_data(target_user_id=target_user_id)
        await message.answer("📩 Введите текст, который хотите отправить пользователю:")
        await state.set_state(BrowseState.waiting_for_spam_text)

@router.message(BrowseState.waiting_for_spam_text)
async def send_spam_message(message: types.Message, state: FSMContext):
    """Получение текста от пользователя и отправка 'spam' сообщения"""
    user_id = message.from_user.id
    user_text = message.text
    data = await state.get_data()
    target_user_id = data.get("target_user_id")

    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("""
        SELECT u.user_tg_id, u.first_name, u.date_of_birth, u.city, u.biography, p.photo, u.lp, u.module
        FROM users u
        LEFT JOIN photos p ON u.user_tg_id = p.user_tg_id
        WHERE u.user_tg_id = ?
    """, (user_id,))
    sender = cursor.fetchone()

    if not sender:
        conn.close()
        await message.answer("⚠ Ошибка: пользователь не найден.")
        await state.clear()
        return

    age = calculate_age(sender["date_of_birth"]) if sender["date_of_birth"] else "Не указан"
    profile_text = (
        f"🌞 Вы понравились:\n\n"
        f"{sender['first_name']}, {age}, {sender['city'] if sender['city'] else 'Не указан'} — "
        f"{sender['biography'] if sender['biography'] else 'Описание отсутствует'}\n"
        f"ЛП: {sender['lp'] if sender['lp'] is not None else 'Не указан'}, "
        f"Модуль: {sender['module'] if sender['module'] else 'Не указан'}"
    )

    keyboard = browse_menu

    if sender["photo"]:
        await message.bot.send_photo(chat_id=target_user_id, photo=sender["photo"], caption=profile_text, reply_markup=keyboard)
    else:
        await message.bot.send_message(chat_id=target_user_id, text=profile_text, reply_markup=keyboard)

    await message.answer("✅ Сообщение отправлено!")
    cursor.execute("UPDATE users SET last_sent_profile = ? WHERE user_tg_id = ?", (user_id, target_user_id))
    conn.commit()
    conn.close()

    await send_new_profile(message, state)
    await state.clear()

# Выход в главное меню ("Спать")
@router.message(lambda msg: msg.text == "😴")
async def exit_browse_mode(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer("Ты вернулся в главное меню.", reply_markup=main_menu)

# Функция для отправки новой анкеты
async def send_new_profile(message, state: FSMContext):
    user_id = message.from_user.id
    user = get_random_profile(user_id)  # Ожидается dict с ключами
    if user:
        await state.update_data(current_profile=user)
        age = calculate_age(user["date_of_birth"]) if user["date_of_birth"] else "Не указан"
        profile_text = (
            f"{user['first_name']}, {age}, {user['city']} — {user['biography']}\n"
            f"ЛП: {user.get('lp', 'Не указан')}, Модуль: {user.get('module', 'Не указан')}"
        )
        if user["photo"]:
            await message.answer_photo(photo=user["photo"], caption=profile_text, reply_markup=browse_menu)
        else:
            await message.answer(profile_text, reply_markup=browse_menu)
    else:
        await message.answer("Доступные анкеты закончились.", reply_markup=main_menu)