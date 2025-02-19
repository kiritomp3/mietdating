import sys
import os
import pytest
import asyncio
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from db import Base  # ✅ Используем Base из db.py
from models import User, Like, ViewedProfile

# ✅ Добавляем корневую директорию проекта в sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# ✅ Используем SQLite in-memory для чистых тестов
TEST_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture(scope="function")
def db_session():
    """Фикстура для тестовой базы данных"""
    print("\n📌 Создаем тестовую БД...")
    Base.metadata.create_all(bind=engine)  # ✅ Создаем таблицы перед тестом
    session = TestingSessionLocal()
    yield session
    print("\n🗑 Очищаем тестовую БД...")
    session.close()
    Base.metadata.drop_all(bind=engine)  # ✅ Удаляем таблицы после теста

@pytest.fixture(scope="session")
def event_loop():
    """Создание event loop для асинхронных тестов"""
    loop = asyncio.get_event_loop()
    yield loop
    loop.close()