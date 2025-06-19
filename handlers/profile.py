import logging
import sqlite3
from aiogram import Router, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from db import DATABASE_PATH, save_user_photo, get_photo
from keyboards import main_menu
from aiogram.types import ReplyKeyboardRemove
from datetime import datetime
from utils.face_detection import has_face_in_photo

router = Router()

# Настройка логирования
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Состояния для изменения анкеты
class EditProfile(StatesGroup):
    choose_field = State()
    new_value = State()

# Вычисляем возраст
def calculate_age(birthdate):
    if isinstance(birthdate, str):
        birthdate = datetime.strptime(birthdate, "%Y-%m-%d").date()

    today = datetime.utcnow().date()
    return today.year - birthdate.year - ((today.month, today.day) < (birthdate.month, birthdate.day))

# 📜 Кнопка "Моя анкета"
@router.message(lambda msg: msg.text == "Моя анкета")
async def my_profile(message: types.Message):
    user_id = message.from_user.id
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT first_name, date_of_birth, city, biography, lp, module
        FROM users WHERE user_tg_id = ?
    """, (user_id,))
    user = cursor.fetchone()
    conn.close()

    if user:
        age = calculate_age(user[1]) if user[1] else "Не указан"
        profile_text = (
            f"{user[0]}, {age}, {user[2] if user[2] else 'Не указан'} — {user[3] if user[3] else 'Описание отсутствует'}\n"
            f"ЛП: {user[4] if user[4] is not None else 'Не указан'}, Модуль: {user[5] if user[5] else 'Не указан'}"
        )
        photo = get_photo(user_id)
        profile_menu = types.ReplyKeyboardMarkup(
            keyboard=[
                [types.KeyboardButton(text="✏ Изменить анкету"), types.KeyboardButton(text="🚫 Выключить анкету")],
                [types.KeyboardButton(text="Главное меню")]
            ],
            resize_keyboard=True
        )
        if photo:
            await message.answer_photo(photo=photo, caption=profile_text, reply_markup=profile_menu)
        else:
            await message.answer(profile_text, reply_markup=profile_menu)
    else:
        await message.answer("Анкета не найдена. Используй /start для создания анкеты.")

# 🚫 Кнопка "Выключить анкету"
@router.message(lambda msg: msg.text == "🚫 Выключить анкету")
async def disable_profile(message: types.Message):
    user_id = message.from_user.id
    logger.info(f"Пользователь {user_id} выключает свою анкету.")

    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET is_active = 0 WHERE user_tg_id = ?", (user_id,))
    conn.commit()
    conn.close()

    await message.answer("🔕 Твоя анкета отключена. Теперь тебя не смогут найти в поиске.", reply_markup=ReplyKeyboardRemove())

# ✏ Кнопка "Изменить анкету"
@router.message(lambda msg: msg.text == "✏ Изменить анкету")
async def edit_profile_start(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    logger.info(f"Пользователь {user_id} начал редактирование анкеты.")

    keyboard = types.ReplyKeyboardMarkup(
        keyboard=[
            [types.KeyboardButton(text="Имя"), types.KeyboardButton(text="Дата рождения")],
            [types.KeyboardButton(text="Город"), types.KeyboardButton(text="Фото")],
            [types.KeyboardButton(text="Описание"), types.KeyboardButton(text="ЛП"), types.KeyboardButton(text="Модуль")],
            [types.KeyboardButton(text="❌Отмена")]
        ],
        resize_keyboard=True
    )
    await message.answer("Что ты хочешь изменить?", reply_markup=keyboard)
    await state.set_state(EditProfile.choose_field)

# Выбор параметра для изменения
field_mapping = {
    "Имя": "first_name",
    "Дата рождения": "date_of_birth",
    "Город": "city",
    "Фото": "photos",
    "Описание": "biography",
    "ЛП": "lp",
    "Модуль": "module"
}

@router.message(EditProfile.choose_field)
async def process_edit_choice(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    logger.info(f"Пользователь {user_id} выбрал изменение параметра: {message.text}")

    if message.text == "❌Отмена":
        logger.info(f"Пользователь {user_id} отменил изменение анкеты.")
        await message.answer("Изменение анкеты отменено.", reply_markup=main_menu)
        await state.clear()
        return

    if message.text not in field_mapping:
        logger.warning(f"Пользователь {user_id} ввел некорректное значение: {message.text}")
        await message.answer("Выбери один из предложенных вариантов.")
        return

    await state.update_data(field=field_mapping[message.text])
    
    if message.text == "Дата рождения":
        await message.answer("Введи новую дату рождения (в формате ГГГГ-ММ-ДД):")
    elif message.text == "Фото":
        await message.answer("Отправь новое фото.")
    else:
        await message.answer(f"Введи новое значение для {message.text}:")
    
    await state.set_state(EditProfile.new_value)

# Обработка нового значения
@router.message(EditProfile.new_value)
async def process_new_value(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    user_data = await state.get_data()
    field = user_data["field"]

    if field == "photos":
        if not message.photo:
            await message.answer("Пожалуйста, отправьте фото.")
            return
        new_value = message.photo[-1].file_id

        # Проверяем, есть ли уже фото у пользователя
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM photos WHERE user_tg_id = ?", (user_id,))
        existing_photo = cursor.fetchone()

        if existing_photo:
            cursor.execute("UPDATE photos SET photo = ? WHERE user_tg_id = ?", (new_value, user_id))
            logger.info(f"Фото пользователя {user_id} обновлено!")
        else:
            cursor.execute("INSERT INTO photos (photo, user_tg_id) VALUES (?, ?)", (new_value, user_id))
            logger.info(f"Фото пользователя {user_id} добавлено!")
        conn.commit()
        conn.close()
        await message.answer("✅ Фото успешно обновлено!", reply_markup=main_menu)
        await state.clear()
        return

    # Для остальных полей ожидаем текст
    if not message.text:
        await message.answer("Пожалуйста, введите корректное текстовое значение.")
        return
    new_value = message.text.strip()

    if field == "date_of_birth":
        try:
            new_value = datetime.strptime(new_value, "%Y-%m-%d").date()
        except ValueError:
            logger.error(f"Пользователь {user_id} ввел некорректную дату: {new_value}")
            await message.answer("Некорректный формат даты! Введите в формате ГГГГ-ММ-ДД (например, 2000-05-15).")
            return

    elif field == "lp":
        try:
            lp_value = int(new_value)
            if lp_value < 1:
                raise ValueError
            new_value = lp_value
        except ValueError:
            await message.answer("Пожалуйста, введите корректное число от 1.")
            return

    elif field == "module":
        if new_value not in ["1", "2", "3", "Лес"]:
            await message.answer("Пожалуйста, выберите один из вариантов: 1, 2, 3 или 'Лес'.")
            return

    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    cursor.execute(f"UPDATE users SET {field} = ? WHERE user_tg_id = ?", (new_value, user_id))
    conn.commit()
    conn.close()

    logger.info(f"Пользователь {user_id} успешно изменил {field} на {new_value}")
    await message.answer("✅ Анкета успешно обновлена!", reply_markup=main_menu)
    await state.clear()