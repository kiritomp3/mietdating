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
    logger.info(f"Пользователь {user_id} запросил свою анкету.")

    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT first_name, date_of_birth, city, biography FROM users WHERE user_tg_id = ?", (user_id,))
    user = cursor.fetchone()
    conn.close()

    if user:
        age = calculate_age(user[1]) if user[1] else "Не указан"
        profile_text = (
            f"{user[0]}, {age}, {user[2] if user[2] else 'Не указан'} — {user[3] if user[3] else 'Описание отсутствует'}"
        )
        photo = get_photo(user_id)
        if photo:
            await message.answer_photo(photo=photo, caption=profile_text, reply_markup=main_menu)
        else:
            await message.answer(profile_text, reply_markup=main_menu)
    else:
        logger.warning(f"Пользователь {user_id} пытался получить анкету, но она не найдена.")
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
            [types.KeyboardButton(text="👤 Имя"), types.KeyboardButton(text="🎂 Дата рождения")],
            [types.KeyboardButton(text="🏙 Город"), types.KeyboardButton(text="🖼 Фото")],
            [types.KeyboardButton(text="📝 Описание")]
        ],
        resize_keyboard=True
    )
    await message.answer("Что ты хочешь изменить?", reply_markup=keyboard)
    await state.set_state(EditProfile.choose_field)

# Выбор параметра для изменения
@router.message(EditProfile.choose_field)
async def process_edit_choice(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    logger.info(f"Пользователь {user_id} выбрал изменение параметра: {message.text}")

    field_mapping = {
        "👤 Имя": "first_name",
        "🎂 Дата рождения": "date_of_birth",
        "🏙 Город": "city",
        "🖼 Фото": "photo",
        "📝 Описание": "biography"
    }

    if message.text == "❌ Отмена":
        logger.info(f"Пользователь {user_id} отменил изменение анкеты.")
        await message.answer("Изменение анкеты отменено.", reply_markup=main_menu)
        await state.clear()
        return

    if message.text not in field_mapping:
        logger.warning(f"Пользователь {user_id} ввел некорректное значение: {message.text}")
        await message.answer("Выбери один из предложенных вариантов.")
        return

    await state.update_data(field=field_mapping[message.text])
    
    if message.text == "🎂 Дата рождения":
        await message.answer("Введи новую дату рождения (в формате ГГГГ-ММ-ДД):")
    elif message.text == "🖼 Фото":
        await message.answer("Отправь новое фото.")
    else:
        await message.answer(f"Введи новое значение для {message.text}:")
    
    await state.set_state(EditProfile.new_value)

# Обработка нового значения
@router.message(EditProfile.new_value)
async def process_new_value(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    new_value = message.text
    logger.info(f"Пользователь {user_id} вводит новое значение: {new_value}")

    user_data = await state.get_data()
    field = user_data["field"]

    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()

    if field == "date_of_birth":
        try:
            new_value = datetime.strptime(new_value, "%Y-%m-%d").date()
        except ValueError:
            logger.error(f"Пользователь {user_id} ввел некорректную дату: {new_value}")
            await message.answer("Некорректный формат даты! Введи в формате ГГГГ-ММ-ДД (например, 2000-05-15).")
            return

    if field == "photo":
        if not message.photo:
            logger.warning(f"Пользователь {user_id} не отправил фото при изменении фото.")
            await message.answer("Пожалуйста, отправь фото.")
            return
        new_value = message.photo[-1].file_id
        save_user_photo(user_id, new_value)
        await message.answer("✅ Фото успешно обновлено!", reply_markup=main_menu)
    else:
        cursor.execute(f"UPDATE users SET {field} = ? WHERE user_tg_id = ?", (new_value, user_id))
        conn.commit()
        conn.close()

        logger.info(f"Пользователь {user_id} успешно изменил {field} на {new_value}")
        await message.answer("✅ Анкета успешно обновлена!", reply_markup=main_menu)

    await state.clear()