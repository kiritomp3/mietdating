import logging
from aiogram import Router, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy.orm import Session
from db import SessionLocal
from models import User
from keyboards import main_menu  # ✅ Импортируем главное меню

router = Router()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class Register(StatesGroup):
    name = State()
    birthdate = State()
    city = State()
    photo = State()
    description = State()

@router.message(Command("start"))
async def start_cmd(message: types.Message, state: FSMContext):
    logger.info(f"Получена команда /start от {message.from_user.id} ({message.from_user.username})")

    user_id = message.from_user.id

    with SessionLocal() as db:
        user = db.query(User).filter(User.id == user_id).first()

        if user:
            if not user.is_active:
                user.is_active = True
                db.commit()
                logger.info(f"Анкета пользователя {user_id} автоматически включена при /start.")
                await message.answer("✅ Твоя анкета снова активна и доступна для поиска!")

            logger.info(f"Пользователь {user_id} уже зарегистрирован.")
            await message.answer("Вы уже зарегистрированы! Используйте меню для взаимодействия.", reply_markup=main_menu)
        else:
            logger.info(f"Пользователь {user_id} не найден в базе. Начинаем регистрацию.")
            await message.answer("Привет! Давай создадим твою анкету. Как тебя зовут?")
            await state.set_state(Register.name)

@router.message(Register.name)
async def process_name(message: types.Message, state: FSMContext):
    logger.info(f"Пользователь {message.from_user.id} ввел имя: {message.text}")
    await state.update_data(name=message.text)
    await message.answer("Отлично! Теперь введи свою дату рождения (в формате ГГГГ-ММ-ДД):")
    await state.set_state(Register.birthdate)

@router.message(Register.birthdate)
async def process_birthdate(message: types.Message, state: FSMContext):
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
    logger.info(f"Пользователь {message.from_user.id} ввел город: {message.text}")
    await state.update_data(city=message.text)
    await message.answer("Теперь отправь свою фотографию.")
    await state.set_state(Register.photo)

@router.message(Register.photo)
async def process_photo(message: types.Message, state: FSMContext):
    if not message.photo:
        logger.warning(f"Пользователь {message.from_user.id} отправил не фото!")
        await message.answer("Пожалуйста, отправь именно фотографию.")
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
    user_data = await state.get_data()
    description = message.text if message.text != "Без описания" else None

    logger.info(f"Пользователь {message.from_user.id} завершает регистрацию.")
    logger.info(f"Анкета: {user_data}, Описание: {description}")

    with SessionLocal() as db:
        new_user = User(
            id=message.from_user.id,
            username=message.from_user.username,
            name=user_data["name"],
            birthdate=user_data["birthdate"],
            city=user_data["city"],
            photo_id=user_data["photo_id"],
            description=description,
            is_active=True  # ✅ Анкета автоматически включается при регистрации
        )
        db.add(new_user)
        db.commit()
        db.refresh(new_user)

    await message.answer(
        "Анкета успешно создана! Теперь ты можешь смотреть анкеты других пользователей.",
        reply_markup=main_menu  # ⬅️ Добавляем клавиатуру
    )
    await state.clear()
    logger.info(f"Пользователь {message.from_user.id} успешно зарегистрирован!")