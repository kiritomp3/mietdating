import logging
import sqlite3
from db import DATABASE_PATH
from aiogram import Router, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from db import check_if_user_registered, register_user, save_user_photo, get_photo
from keyboards import main_menu
from utils.face_detection import has_face_in_photo


router = Router()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class Register(StatesGroup):
    sex = State()
    looking_for = State()
    relationship_type = State()
    name = State()
    birthdate = State()
    city = State()
    photo = State()
    description = State()

@router.message(Command("start"))
async def start_cmd(message: types.Message, state: FSMContext):
    """Обработчик команды /start (проверяет регистрацию пользователя и включает анкету)"""
    logger.info(f"Получена команда /start от {message.from_user.id} ({message.from_user.username})")

    user_id = message.from_user.id

    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()

    # ✅ Проверяем, зарегистрирован ли пользователь
    cursor.execute("SELECT is_active FROM users WHERE user_tg_id = ?", (user_id,))
    user = cursor.fetchone()

    if user:
        is_active = user[0]
        if is_active == 0:
            # ✅ Включаем анкету, если она была отключена
            cursor.execute("UPDATE users SET is_active = 1 WHERE user_tg_id = ?", (user_id,))
            conn.commit()
            logger.info(f"Анкета пользователя {user_id} включена при повторном /start.")
            await message.answer("✅ Твоя анкета снова активна и доступна для поиска!", reply_markup=main_menu)
        else:
            logger.info(f"Пользователь {user_id} уже зарегистрирован и активен.")
            await message.answer("Вы уже зарегистрированы! Используйте меню для взаимодействия.", reply_markup=main_menu)
    else:
        # ✅ Если пользователя нет в БД, запускаем регистрацию
        logger.info(f"Пользователь {user_id} не найден в базе. Начинаем регистрацию.")
        await message.answer("Привет! Давай создадим твою анкету. Как тебя зовут?")
        await state.set_state(Register.name)

    conn.close()

@router.message(Register.name)
async def process_name(message: types.Message, state: FSMContext):
    """Сохраняем имя пользователя"""
    logger.info(f"Пользователь {message.from_user.id} ввел имя: {message.text}")
    await state.update_data(name=message.text)
    await message.answer("Отлично! Теперь введи свою дату рождения (в формате ГГГГ-ММ-ДД):")
    await state.set_state(Register.birthdate)

@router.message(Register.birthdate)
async def process_birthdate(message: types.Message, state: FSMContext):
    """Сохраняем дату рождения пользователя"""
    try:
        from datetime import datetime
        birthdate = datetime.strptime(message.text, "%Y-%m-%d").date()
        logger.info(f"Пользователь {message.from_user.id} ввел дату рождения: {birthdate}")

        await state.update_data(birthdate=birthdate)
        await message.answer("Отлично! В каком городе ты живешь?")
        await state.set_state(Register.city)
    except ValueError:
        logger.warning(f"Пользователь {message.from_user.id} ввел неверную дату: {message.text}")
        await message.answer("Некорректный формат даты! Введи в формате ГГГГ-ММ-ДД (например, 2000-05-15).")

@router.message(Register.city)
async def process_city(message: types.Message, state: FSMContext):
    """Сохраняем город пользователя"""
    logger.info(f"Пользователь {message.from_user.id} ввел город: {message.text}")
    await state.update_data(city=message.text)
    await message.answer("Теперь отправь свою фотографию.")
    await state.set_state(Register.photo)

@router.message(Register.photo)
async def process_photo(message: types.Message, state: FSMContext):
    """Сохраняем фото пользователя"""
    if not message.photo:
        logger.warning(f"Пользователь {message.from_user.id} отправил не фото!")
        await message.answer("Пожалуйста, отправь именно фотографию.")
        return
    # Проверяем наличие лица на фото
    has_face = await has_face_in_photo(message.photo[-1])
    if not has_face:
        logger.warning(f"Пользователь {message.from_user.id} отправил фото без лица!")
        await message.answer("На фотографии не обнаружено лицо. Пожалуйста, отправь фото, где четко видно твое лицо.")
        return
    photo_id = message.photo[-1].file_id
    logger.info(f"Пользователь {message.from_user.id} загрузил фото: {photo_id}")

    await state.update_data(photo_id=photo_id)
    keyboard = types.ReplyKeyboardMarkup(
        keyboard=[[types.KeyboardButton(text="Без описания")]],
        resize_keyboard=True,
    )
    await message.answer("Напиши описание анкеты или нажми кнопку 'Без описания'.", reply_markup=keyboard)
    await state.set_state(Register.description)

@router.message(Register.description)
async def process_description(message: types.Message, state: FSMContext):
    """Завершаем регистрацию и сохраняем данные"""
    user_data = await state.get_data()
    description = message.text if message.text != "Без описания" else None

    date_of_birth = str(user_data.get("birthdate", "0000-00-00"))  # ✅ Теперь не вызовет KeyError

    logger.info(f"Пользователь {message.from_user.id} завершает регистрацию.")
    logger.info(f"Анкета: {user_data}, Описание: {description}")

    # Регистрируем пользователя в SQLite
    register_user(
        user_tg_id=message.from_user.id,
        username=message.from_user.username,
        first_name=user_data["name"],
        date_of_birth=date_of_birth,
        city=user_data["city"],
        biography=description
    )

    # Сохраняем фото пользователя
    save_user_photo(message.from_user.id, user_data["photo_id"])

    await message.answer(
        "✅ Анкета успешно создана! Теперь ты можешь смотреть анкеты других пользователей.",
        reply_markup=main_menu
    )
    await state.clear()
    logger.info(f"Пользователь {message.from_user.id} успешно зарегистрирован!")