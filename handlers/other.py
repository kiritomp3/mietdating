from aiogram import Router, types
from keyboards import main_menu

router = Router()

@router.message(lambda msg: msg.text == "Мероприятия")
async def events_handler(message: types.Message):
    await message.answer("📅 Раздел 'Мероприятия' в разработке. Скоро здесь появятся интересные события!", reply_markup=main_menu)

@router.message(lambda msg: msg.text == "Услуги")
async def services_handler(message: types.Message):
    await message.answer("🛠 Раздел 'Услуги' в разработке. Следите за обновлениями!", reply_markup=main_menu)

@router.message(lambda msg: msg.text == "Информация")
async def info_handler(message: types.Message):
    await message.answer(
        "ℹ Это бот для знакомств! Вы можете:\n"
        "- Искать анкеты и ставить лайки\n"
        "- Редактировать свою анкету\n"
        "- Получать уведомления о взаимных симпатиях\n"
        "Для начала используйте команду /start или выберите 'Поиск' в меню.",
        reply_markup=main_menu
    )