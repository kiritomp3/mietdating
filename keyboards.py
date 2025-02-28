from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

# Главное меню
main_menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="Поиск"), KeyboardButton(text="Моя анкета")],
        [KeyboardButton(text="Мероприятия"), KeyboardButton(text="Услуги")],
        [KeyboardButton(text="Информация")]
    ],
    resize_keyboard=True,
)

# Клавиатура для просмотра анкет

def get_browse_keyboard(user_id: int):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❤️", callback_data=f"like:{user_id}")],
        [InlineKeyboardButton(text="👎", callback_data=f"dislike:{user_id}")],
    ])
