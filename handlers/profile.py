import logging
from aiogram import Router, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from db import SessionLocal
from models import User
from keyboards import main_menu
from aiogram.types import ReplyKeyboardRemove

router = Router()

# Настройка логирования
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Состояния для изменения анкеты
class EditProfile(StatesGroup):
    choose_field = State()
    new_value = State()

# 📜 Кнопка "Моя анкета"
@router.message(lambda msg: msg.text == "📜 Моя анкета")
async def my_profile(message: types.Message):
    user_id = message.from_user.id
    logger.info(f"Пользователь {user_id} запросил свою анкету.")

    with SessionLocal() as db:
        user = db.query(User).filter(User.id == user_id).first()

        if user:
            profile_text = (f"📜 Твоя анкета:\n\n"
                            f"👤 Имя: {user.name}\n"
                            f"🎂 Дата рождения: {user.birthdate}\n"
                            f"🏙 Город: {user.city}\n"
                            f"📝 Описание: {user.description if user.description else '—'}")
            
            if user.photo_id:
                await message.answer_photo(photo=user.photo_id, caption=profile_text, reply_markup=main_menu)
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

    with SessionLocal() as db:
        user = db.query(User).filter(User.id == user_id).first()
        
        if user:
            user.is_active = False
            db.commit()
            logger.info(f"Анкета пользователя {user_id} успешно отключена.")
            await message.answer("🔕 Твоя анкета отключена. Теперь тебя не смогут найти в поиске.", reply_markup=ReplyKeyboardRemove())
        else:
            logger.warning(f"Пользователь {user_id} пытался отключить анкету, но она не найдена.")
            await message.answer("Анкета не найдена. Используй /start для создания анкеты.")

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
        "👤 Имя": "name",
        "🎂 Дата рождения": "birthdate",
        "🏙 Город": "city",
        "🖼 Фото": "photo_id",
        "📝 Описание": "description"
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

    with SessionLocal() as db:
        user = db.query(User).filter(User.id == user_id).first()

        if not user:
            logger.warning(f"Пользователь {user_id} пытался изменить анкету, но она не найдена.")
            await message.answer("Анкета не найдена. Используй /start для её создания.")
            await state.clear()
            return

        if field == "birthdate":
            try:
                from datetime import datetime
                new_value = datetime.strptime(new_value, "%Y-%m-%d").date()
            except ValueError:
                logger.error(f"Пользователь {user_id} ввел некорректную дату: {new_value}")
                await message.answer("Некорректный формат даты! Введи в формате ГГГГ-ММ-ДД (например, 2000-05-15).")
                return

        if field == "photo_id":
            if not message.photo:
                logger.warning(f"Пользователь {user_id} не отправил фото при изменении фото.")
                await message.answer("Пожалуйста, отправь фото.")
                return
            new_value = message.photo[-1].file_id

        setattr(user, field, new_value)
        db.commit()
        logger.info(f"Пользователь {user_id} успешно изменил {field} на {new_value}")

    await message.answer("✅ Анкета успешно обновлена!", reply_markup=main_menu)
    await state.clear()