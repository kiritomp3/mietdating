import pytest
from aiogram.types import Message, CallbackQuery
from aiogram import Dispatcher
from handlers.profile import my_profile
from handlers.browse import like_profile
from unittest.mock import AsyncMock
from models import User, Like, ViewedProfile
from datetime import date

@pytest.mark.asyncio
async def test_my_profile_handler(db_session):
    """Тест обработчика команды 'Моя анкета'"""
    # Создаем фиктивного пользователя в базе
    user = User(id=12345, username="testuser", name="Alice", birthdate=date(1990, 5, 10), city="NY", is_active=True)
    db_session.add(user)
    db_session.commit()

    # Создаем моковое сообщение
    message = AsyncMock(spec=Message)
    message.text = "Моя анкета"
    message.from_user.id = 12345

    await my_profile(message)

    message.answer.assert_called_once()  # Проверяем, что сообщение отправлено

@pytest.mark.asyncio
async def test_like_handler(db_session):
    """Тест обработчика лайков"""
    user1 = User(id=1, username="user1", name="Alice", birthdate=date(1990, 5, 10), city="NY", is_active=True)
    user2 = User(id=2, username="user2", name="Bob", birthdate=date(1992, 8, 15), city="LA", is_active=True)
    db_session.add_all([user1, user2])
    db_session.commit()

    callback = AsyncMock(spec=CallbackQuery)
    callback.data = "like:2"
    callback.from_user.id = 1
    callback.bot.send_message = AsyncMock()

    await like_profile(callback)

    callback.bot.send_message.assert_called()  # Проверяем, что бот отправил сообщение