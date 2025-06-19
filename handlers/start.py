import logging
import sqlite3
from db import DATABASE_PATH, check_if_user_registered
from aiogram import Router, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from db import register_user, save_user_photo, get_photo
from keyboards import main_menu
from utils.face_detection import has_face_in_photo
from handlers.browse import browse_profiles  # Импортируем функцию для поиска анкет
from handlers.profile import calculate_age

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
    marital_status = State()  # Семейное положение
    lp = State()              # Новый вопрос: Ваш ЛП?
    module = State()          # Новый вопрос: Ваш модуль?

@router.message(Command("start"))
async def start_cmd(message: types.Message, state: FSMContext):
    """Обработчик команды /start (начало регистрации)"""
    logger.info(f"Получена команда /start от {message.from_user.id} ({message.from_user.username})")
    
    user_id = message.from_user.id
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    cursor.execute("SELECT is_active FROM users WHERE user_tg_id = ?", (user_id,))
    user = cursor.fetchone()
    
    if user:
        is_active = user[0]
        if is_active == 0:
            cursor.execute("UPDATE users SET is_active = 1 WHERE user_tg_id = ?", (user_id,))
            conn.commit()
            logger.info(f"Анкета пользователя {user_id} включена при повторном /start.")
            await message.answer("✅ Твоя анкета снова активна и доступна для поиска!", reply_markup=main_menu)
        else:
            logger.info(f"Пользователь {user_id} уже зарегистрирован и активен.")
            await message.answer("Вы уже зарегистрированы! Используйте меню для взаимодействия.", reply_markup=main_menu)
    else:
        logger.info(f"Пользователь {user_id} не найден в базе. Начинаем регистрацию.")
        keyboard = types.ReplyKeyboardMarkup(
            keyboard=[
                [types.KeyboardButton(text="Мужчина"), types.KeyboardButton(text="Женщина")]
            ],
            resize_keyboard=True
        )
        await message.answer("Выбери свой пол:", reply_markup=keyboard)
        await state.set_state(Register.sex)
    
    conn.close()

@router.message(Register.sex)
async def process_sex(message: types.Message, state: FSMContext):
    """Сохраняем пол пользователя"""
    if message.text not in ["Мужчина", "Женщина"]:
        await message.answer("Выбери пол, нажав на кнопку.")
        return

    logger.info(f"Пользователь {message.from_user.id} выбрал пол: {message.text}")
    await state.update_data(sex=message.text)

    keyboard = types.ReplyKeyboardMarkup(
        keyboard=[
            [types.KeyboardButton(text="Мужчину"), types.KeyboardButton(text="Женщину")]
        ],
        resize_keyboard=True
    )
    await message.answer("Кого ты хочешь найти?", reply_markup=keyboard)
    await state.set_state(Register.looking_for)

@router.message(Register.looking_for)
async def process_looking_for(message: types.Message, state: FSMContext):
    """Сохраняем, кого ищет пользователь"""
    if message.text not in ["Мужчину", "Женщину"]:
        await message.answer("Выбери вариант, нажав на кнопку.")
        return

    logger.info(f"Пользователь {message.from_user.id} ищет: {message.text}")
    await state.update_data(looking_for=message.text)

    keyboard = types.ReplyKeyboardMarkup(
        keyboard=[
            [types.KeyboardButton(text="Секс"), types.KeyboardButton(text="Дружеские"), types.KeyboardButton(text="Серьезные")]
        ],
        resize_keyboard=True
    )
    await message.answer("Выбери, какие отношения ты ищешь:", reply_markup=keyboard)
    await state.set_state(Register.relationship_type)

@router.message(Register.relationship_type)
async def process_relationship_type(message: types.Message, state: FSMContext):
    """Сохраняем форму отношений и переходим к следующему шагу"""
    if message.text not in ["Секс", "Дружеские", "Серьезные"]:
        await message.answer("Выбери вариант, нажав на кнопку.")
        return

    logger.info(f"Пользователь {message.from_user.id} ищет отношения типа: {message.text}")
    await state.update_data(relationship_type=message.text)

    # ✅ Убираем клавиатуру после выбора
    await message.answer("Отлично! Как тебя зовут?", reply_markup=types.ReplyKeyboardRemove())

    # ✅ Переход к следующему шагу регистрации
    await state.set_state(Register.name)

@router.message(Register.name)
async def process_name(message: types.Message, state: FSMContext):
    """Сохраняем имя пользователя и переходим к следующему шагу"""
    user_name = message.text.strip()

    if not user_name:
        await message.answer("Пожалуйста, введи корректное имя.")
        return

    logger.info(f"Пользователь {message.from_user.id} ввел имя: {user_name}")
    await state.update_data(name=user_name)

    # ✅ Запрашиваем дату рождения
    await message.answer("Отлично! Теперь введи свою дату рождения (в формате ДД.ММ.ГГГГ):")

    await state.set_state(Register.birthdate)

@router.message(Register.city)
async def process_city(message: types.Message, state: FSMContext):
    """Сохраняем город пользователя"""
    user_city = message.text.strip()

    if not user_city:
        await message.answer("Пожалуйста, введи корректное название города.")
        return

    logger.info(f"Пользователь {message.from_user.id} ввел город: {user_city}")
    await state.update_data(city=user_city)

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
   # has_face = await has_face_in_photo(message.photo[-1])
    #if not has_face:
     #   logger.warning(f"Пользователь {message.from_user.id} отправил фото без лица!")
      #  await message.answer("На фотографии не обнаружено лицо. Пожалуйста, отправь фото, где четко видно твое лицо.")
       # return
    photo_id = message.photo[-1].file_id
    logger.info(f"Пользователь {message.from_user.id} загрузил фото: {photo_id}")

    await state.update_data(photo_id=photo_id)
    keyboard = types.ReplyKeyboardMarkup(
        keyboard=[[types.KeyboardButton(text="Без описания")]],
        resize_keyboard=True,
    )
    await message.answer("Напиши описание анкеты или нажми кнопку 'Без описания'.", reply_markup=keyboard)
    await state.set_state(Register.description)

@router.message(Register.birthdate)
async def process_birthdate(message: types.Message, state: FSMContext):
    """Сохраняем дату рождения пользователя"""
    try:
        from datetime import datetime
        birthdate = datetime.strptime(message.text.strip(), "%d.%m.%Y").date()
        logger.info(f"Пользователь {message.from_user.id} ввел дату рождения: {birthdate}")

        await state.update_data(birthdate=str(birthdate))

        # ✅ Переход к следующему шагу
        await message.answer("Отлично! В каком городе ты живешь?")
        await state.set_state(Register.city)

    except ValueError:
        logger.warning(f"Пользователь {message.from_user.id} ввел неверную дату: {message.text}")
        await message.answer("Некорректный формат даты! Введи в формате ДД.ММ.ГГГГ (например, 15.05.2000).")


@router.message(Register.description)
async def process_description(message: types.Message, state: FSMContext):
    """Сохраняем описание и переходим к вопросу о семейном положении"""
    user_data = await state.get_data()
    description = message.text if message.text != "Без описания" else None

    await state.update_data(description=description)

    # Переходим к вопросу о семейном положении
    keyboard = types.ReplyKeyboardMarkup(
        keyboard=[
            [types.KeyboardButton(text="Да"), types.KeyboardButton(text="Нет")]
        ],
        resize_keyboard=True
    )
    await message.answer("Вы женаты/замужем?", reply_markup=keyboard)
    await state.set_state(Register.marital_status)

@router.message(Register.marital_status)
async def process_marital_status(message: types.Message, state: FSMContext):
    if message.text not in ["Да", "Нет"]:
        await message.answer("Пожалуйста, выберите 'Да' или 'Нет'.")
        return

    await state.update_data(marital_status=message.text)
    await message.answer("Ваш ЛП? (Введите число от 1):", reply_markup=types.ReplyKeyboardRemove())
    await state.set_state(Register.lp)
@router.message(Register.lp)
async def process_lp(message: types.Message, state: FSMContext):
    try:
        lp_value = int(message.text.strip())
        if lp_value < 1 or lp_value:
            raise ValueError
    except ValueError:
        await message.answer("Пожалуйста, введите корректное число от 1 до 130.")
        return

    await state.update_data(lp=lp_value)
    keyboard = types.ReplyKeyboardMarkup(
        keyboard=[
            [types.KeyboardButton(text="1"), types.KeyboardButton(text="2"),
             types.KeyboardButton(text="3"), types.KeyboardButton(text="Лес")]
        ],
        resize_keyboard=True
    )
    await message.answer("Ваш модуль? (Выберите 1, 2, 3 или 'Лес')", reply_markup=keyboard)
    await state.set_state(Register.module)


    user_data = await state.get_data()
    is_married = message.text == "Да"

    logger.info(f"Пользователь {message.from_user.id} указал семейное положение: {message.text}")


@router.message(Register.module)
async def process_module(message: types.Message, state: FSMContext):
    valid_options = ["1", "2", "3", "Лес"]
    if message.text not in valid_options:
        await message.answer("Пожалуйста, выберите один из вариантов: 1, 2, 3 или 'Лес'.")
        return

    await state.update_data(module=message.text)
    user_data = await state.get_data()
    
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO users (
            user_tg_id, username, first_name, date_of_birth, city, biography, gender,
            looking_for, relationship_type, is_active, marital_status, lp, module
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        message.from_user.id,
        message.from_user.username,
        user_data["name"],
        user_data.get("birthdate", "0000-00-00"),
        user_data["city"],
        user_data["description"],
        user_data["sex"],
        user_data["looking_for"],
        user_data["relationship_type"],
        0 if user_data.get("marital_status") == "Да" else 1,  # Если женат/замужем, анкета не активна
        user_data["marital_status"],
        user_data["lp"],
        user_data["module"]
    ))
    conn.commit()
    conn.close()

    save_user_photo(message.from_user.id, user_data["photo_id"])

    confirmation_text = (
        "✅ Анкета успешно создана! Теперь ты можешь смотреть анкеты других пользователей."
        if user_data["marital_status"] != "Да"
        else "✅ Анкета успешно создана, но так как вы женаты/замужем, поиск анкет для вас недоступен."
    )
    await message.answer(confirmation_text, reply_markup=main_menu)
    await state.clear()
    logger.info(f"Пользователь {message.from_user.id} успешно зарегистрирован!")

@router.message(lambda msg: msg.text == "Поиск")
async def search_profiles(message: types.Message, state: FSMContext):
    """Обработчик нажатия на кнопку 'Поиск'"""
    user_id = message.from_user.id
    if not check_if_user_registered(user_id):
        await message.answer("Для поиска анкет необходимо зарегистрироваться. Пожалуйста, начните регистрацию с команды /start.")
    else:
        await browse_profiles(message, state)  # Вызываем функцию поиска анкет

@router.message(lambda msg: msg.text == "Моя анкета")
async def my_profile(message: types.Message):
    """Обработчик нажатия на кнопку 'Моя анкета'"""
    user_id = message.from_user.id
    if not check_if_user_registered(user_id):
        await message.answer("Вы не зарегистрированы. Начинаем регистрацию.")
        await start_cmd(message)  # Начинаем регистрацию
    else:
        # Получаем данные пользователя из базы данных
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT first_name, date_of_birth, city, biography, lp, module FROM users WHERE user_tg_id = ?", (user_id,))
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

@router.message(lambda msg: msg.text == "Главное меню")
async def main_menu_handler(message: types.Message):
    """Возвращает пользователя в главное меню"""
    await message.answer("Вы вернулись в главное меню.", reply_markup=main_menu)