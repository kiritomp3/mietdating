import logging
import sqlite3
import asyncio
from aiogram import Router, types
from aiogram.types import CallbackQuery, ReplyKeyboardMarkup, KeyboardButton
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

# ✅ Определяем состояния FSM
class BrowseState(StatesGroup):
    browsing = State()
    waiting_for_spam_text = State()

# ✅ Клавиатура для просмотра анкет
browse_menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="❤️ Лайк"), KeyboardButton(text="👎 Дизлайк")],
        [KeyboardButton(text="😴 Спать")],
        #KeyboardButton(text="🚀 Спам"),
    ],
    resize_keyboard=True
)

# ✅ Начало просмотра анкет
@router.message(lambda msg: msg.text == "Смотреть анкеты")
async def browse_profiles(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    logger.info(f"Пользователь {user_id} начал просмотр анкет.")

    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()

    # ✅ Получаем пользователей, которые лайкнули текущего пользователя
    cursor.execute("""
        SELECT who_chose FROM likes WHERE who_was_chosen = ?
        ORDER BY RANDOM()
        LIMIT 1
    """, (user_id,))
    liked_user = cursor.fetchone()

    if liked_user:
        liked_user_id = liked_user[0]

        # ✅ Получаем анкету лайкнувшего
        cursor.execute("""
            SELECT u.user_tg_id, u.first_name, u.date_of_birth, u.city, u.biography, p.photo 
            FROM users u
            LEFT JOIN photos p ON u.user_tg_id = p.user_tg_id
            WHERE u.user_tg_id = ?
        """, (liked_user_id,))
        user = cursor.fetchone()

        if user:
            profile_dict = {
                "id": user[0],
                "first_name": user[1],
                "date_of_birth": user[2],
                "city": user[3],
                "biography": user[4],
                "photo": user[5],
            }
            await state.update_data(current_profile=profile_dict)

            age = calculate_age(user[2]) if user[2] else "Не указан"
            profile_text = f"💌 Вы понравились:\n\n{user[1]}, {age}, {user[3]} — {user[4]}"

            if user[5]:
                await message.answer_photo(photo=user[5], caption=profile_text, reply_markup=browse_menu)
            else:
                await message.answer(profile_text, reply_markup=browse_menu)

            conn.close()
            return

    # ✅ Если лайкнувшие закончились, показываем случайные анкеты
    user = get_random_profile(user_id)
    
    if user:
        await state.update_data(current_profile=user)
        age = calculate_age(user["date_of_birth"]) if user["date_of_birth"] else "Не указан"
        profile_text = f"{user['first_name']}, {age}, {user['city']} — {user['biography']}"

        if user["photo"]:
            await message.answer_photo(photo=user["photo"], caption=profile_text, reply_markup=browse_menu)
        else:
            await message.answer(profile_text, reply_markup=browse_menu)

        await state.set_state(BrowseState.browsing)  # ✅ Переходим в состояние просмотра анкет
    else:
        await message.answer("Доступные анкеты закончились.", reply_markup=main_menu)

    conn.close()

# ✅ Обработчик "Лайк"
@router.message(lambda msg: msg.text == "❤️ Лайк")
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
    cursor = conn.cursor()

    # ✅ Сначала записываем лайк в БД и коммитим его
    cursor.execute("INSERT INTO likes (who_chose, who_was_chosen) VALUES (?, ?)", (user_id, target_user_id))
    conn.commit()

    # ✅ Проверяем, записался ли лайк
    cursor.execute("SELECT who_chose, who_was_chosen FROM likes WHERE who_chose = ? AND who_was_chosen = ?", (user_id, target_user_id))
    new_like = cursor.fetchone()
    if new_like:
        logger.info(f"✅ Лайк успешно записан: {new_like}")
    else:
        logger.error(f"❌ Лайк НЕ записался! Ошибка в БД!")

    # ✅ Повторно проверяем мэтч ПОСЛЕ записи лайка
    cursor.execute("SELECT id FROM likes WHERE who_chose = ? AND who_was_chosen = ?", (target_user_id, user_id))
    mutual_like = cursor.fetchone()

    if mutual_like:
        logger.info(f"✅ Мэтч! {user_id} и {target_user_id} взаимно лайкнули друг друга.")

        # ✅ Удаляем лайки друг друга после успешного мэтча
        cursor.execute("DELETE FROM likes WHERE who_chose = ? AND who_was_chosen = ?", (user_id, target_user_id))
        cursor.execute("DELETE FROM likes WHERE who_chose = ? AND who_was_chosen = ?", (target_user_id, user_id))

        # ✅ Уменьшаем счетчик likes_received у обоих пользователей
        cursor.execute("UPDATE users SET likes_received = likes_received - 1 WHERE user_tg_id = ? AND likes_received > 0", (user_id,))
        cursor.execute("UPDATE users SET likes_received = likes_received - 1 WHERE user_tg_id = ? AND likes_received > 0", (target_user_id,))
        conn.commit()

        # ✅ Получаем usernames пользователей
        cursor.execute("SELECT username FROM users WHERE user_tg_id = ?", (target_user_id,))
        target_username = cursor.fetchone()[0]

        cursor.execute("SELECT username FROM users WHERE user_tg_id = ?", (user_id,))
        user_username = cursor.fetchone()[0]

        # ✅ Получаем обновленное количество лайков для уведомления
        cursor.execute("SELECT likes_received FROM users WHERE user_tg_id = ?", (target_user_id,))
        target_likes_count = cursor.fetchone()[0]
        cursor.execute("SELECT likes_received FROM users WHERE user_tg_id = ?", (user_id,))
        user_likes_count = cursor.fetchone()[0]

        conn.close()

        # ✅ Отправляем уведомления о мэтче с обновленным количеством лайков
        await message.bot.send_message(user_id, f"🎉 У вас новый мэтч!\n @{target_username}\n💌 Осталось симпатий: {user_likes_count}")
        await message.bot.send_message(target_user_id, f"🎉 У вас новый мэтч!\n @{user_username}\n💌 Осталось симпатий: {target_likes_count}")

    else:
        logger.info(f"🚀 Нет взаимного лайка. {user_id} просто лайкнул {target_user_id}")

        # ✅ Увеличиваем счетчик лайков у пользователя
        cursor.execute("UPDATE users SET likes_received = likes_received + 1 WHERE user_tg_id = ?", (target_user_id,))
        conn.commit()

        # ✅ Получаем количество лайков
        cursor.execute("SELECT likes_received FROM users WHERE user_tg_id = ?", (target_user_id,))
        likes_count = cursor.fetchone()[0]

        conn.close()

        # ✅ Отправляем сообщение о новом лайке
        await message.bot.send_message(target_user_id, f"💌 Вы понравились ({likes_count} пользователям).")

    await message.answer("❤️ Лайк отправлен!")
    await send_new_profile(message, state)

# ✅ Обработчик "Дизлайк"
@router.message(lambda msg: msg.text == "👎 Дизлайк")
async def dislike_profile_action(message: types.Message, state: FSMContext):
    logger.info(f"Пользователь {message.from_user.id} поставил дизлайк.")
    await send_new_profile(message, state)

# ✅ Обработчик "Спам"
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
    cursor = conn.cursor()

    # ✅ Сначала записываем лайк в БД и коммитим его
    cursor.execute("INSERT INTO likes (who_chose, who_was_chosen) VALUES (?, ?)", (user_id, target_user_id))
    conn.commit()

    # ✅ Проверяем, записался ли лайк
    cursor.execute("SELECT who_chose, who_was_chosen FROM likes WHERE who_chose = ? AND who_was_chosen = ?", (user_id, target_user_id))
    new_like = cursor.fetchone()
    if new_like:
        logger.info(f"✅ Лайк успешно записан: {new_like}")
    else:
        logger.error(f"❌ Лайк НЕ записался! Ошибка в БД!")

    # ✅ Повторно проверяем мэтч ПОСЛЕ записи лайка
    cursor.execute("SELECT id FROM likes WHERE who_chose = ? AND who_was_chosen = ?", (target_user_id, user_id))
    mutual_like = cursor.fetchone()

    if mutual_like:
        logger.info(f"✅ Мэтч! {user_id} и {target_user_id} взаимно лайкнули друг друга.")

        # ✅ Удаляем лайки друг друга после успешного мэтча
        cursor.execute("DELETE FROM likes WHERE who_chose = ? AND who_was_chosen = ?", (user_id, target_user_id))
        cursor.execute("DELETE FROM likes WHERE who_chose = ? AND who_was_chosen = ?", (target_user_id, user_id))

        # ✅ Уменьшаем счетчик likes_received у обоих пользователей
        cursor.execute("UPDATE users SET likes_received = likes_received - 1 WHERE user_tg_id = ? AND likes_received > 0", (user_id,))
        cursor.execute("UPDATE users SET likes_received = likes_received - 1 WHERE user_tg_id = ? AND likes_received > 0", (target_user_id,))
        conn.commit()

        # ✅ Получаем usernames пользователей
        cursor.execute("SELECT username FROM users WHERE user_tg_id = ?", (target_user_id,))
        target_username = cursor.fetchone()[0]
        cursor.execute("SELECT username FROM users WHERE user_tg_id = ?", (user_id,))
        user_username = cursor.fetchone()[0]

        # ✅ Получаем обновленное количество лайков для уведомления
        cursor.execute("SELECT likes_received FROM users WHERE user_tg_id = ?", (target_user_id,))
        target_likes_count = cursor.fetchone()[0]
        cursor.execute("SELECT likes_received FROM users WHERE user_tg_id = ?", (user_id,))
        user_likes_count = cursor.fetchone()[0]

        conn.close()

        # ✅ Отправляем уведомления о мэтче с обновленным количеством лайков
        await message.bot.send_message(user_id, f"🎉 У вас новый мэтч!\n @{target_username}\n💌 Осталось симпатий: {user_likes_count}")
        await message.bot.send_message(target_user_id, f"🎉 У вас новый мэтч!\n @{user_username}\n💌 Осталось симпатий: {target_likes_count}")

        # ✅ Переходим к следующей анкете после мэтча
        await message.answer("❤️ Мэтч! Переходим к следующей анкете...")
        await send_new_profile(message, state)

    else:
        logger.info(f"🚀 Нет взаимного лайка. {user_id} использует 'Спам' для {target_user_id}")

        # ✅ Увеличиваем счетчик лайков у пользователя
        cursor.execute("UPDATE users SET likes_received = likes_received + 1 WHERE user_tg_id = ?", (target_user_id,))
        conn.commit()

        # ✅ Получаем количество лайков
        cursor.execute("SELECT likes_received FROM users WHERE user_tg_id = ?", (target_user_id,))
        likes_count = cursor.fetchone()[0]

        conn.close()

        # ✅ Отправляем сообщение о новом лайке
        await message.bot.send_message(target_user_id, f"💌 Вы понравились ({likes_count} пользователям).")

        # ✅ Запрашиваем текст для спама
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
    cursor = conn.cursor()

    # ✅ Получаем анкету отправителя
    cursor.execute("""
        SELECT u.user_tg_id, u.first_name, u.date_of_birth, u.city, u.biography, p.photo 
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

    age = calculate_age(sender[2]) if sender[2] else "Не указан"
    profile_text = (f"🌞 Вы понравились:\n\n"
                    f"{sender[1]}, {age}, {sender[3] if sender[3] else 'Не указан'}\n"
                    f"{sender[4] if sender[4] else 'Описание отсутствует'}\n\n"
                    f"💬 Сообщение: {user_text}")

    keyboard = browse_menu

    # ✅ Отправляем анкету + сообщение
    if sender[5]:  # Фото
        await message.bot.send_photo(chat_id=target_user_id, photo=sender[5], caption=profile_text, reply_markup=keyboard)
    else:
        await message.bot.send_message(chat_id=target_user_id, text=profile_text, reply_markup=keyboard)

    await message.answer("✅ Сообщение отправлено!")

    # ✅ Сохраняем ID отправителя в last_sent_profile для получателя
    cursor.execute("UPDATE users SET last_sent_profile = ? WHERE user_tg_id = ?", (user_id, target_user_id))
    conn.commit()
    conn.close()

    await send_new_profile(message, state)
    await state.clear()

# ✅ Выход в главное меню ("Спать")
@router.message(lambda msg: msg.text == "😴 Спать")
async def exit_browse_mode(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer("Ты вернулся в главное меню.", reply_markup=main_menu)

# ✅ Функция для отправки новой анкеты
async def send_new_profile(message, state: FSMContext):
    user_id = message.from_user.id
    user = get_random_profile(user_id)

    if user:
        await state.update_data(current_profile=user)
        age = calculate_age(user["date_of_birth"]) if user["date_of_birth"] else "Не указан"
        profile_text = f"{user['first_name']}, {age}, {user['city']} — {user['biography']}"

        if user["photo"]:
            await message.answer_photo(photo=user["photo"], caption=profile_text, reply_markup=browse_menu)
        else:
            await message.answer(profile_text, reply_markup=browse_menu)
    else:
        await message.answer("Доступные анкеты закончились.", reply_markup=main_menu)
