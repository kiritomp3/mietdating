import os
import sqlite3
import logging
from typing import Optional, List

DATABASE_PATH = os.path.join("data", "dating_bot.db")
logger = logging.getLogger("bot")


def create_database() -> None:
    """Создает базу данных и необходимые таблицы"""
    create_dir()

    conn = sqlite3.connect(DATABASE_PATH, uri=True)
    cursor = conn.cursor()

    create_users_table(cursor)
    create_photos_table(cursor)
    create_likes_table(cursor)
    create_viewed_profiles_table(cursor)

    conn.commit()
    conn.close()
    logger.info("✅ База данных успешно создана")


def create_dir() -> None:
    """Создает папку для хранения БД, если она отсутствует"""
    dir_name = os.path.dirname(DATABASE_PATH)
    if not os.path.exists(dir_name):
        os.makedirs(dir_name, exist_ok=True)


def create_users_table(cursor) -> None:
    """Создает таблицу пользователей"""
    cursor.execute("""CREATE TABLE IF NOT EXISTS users(
        user_tg_id INTEGER PRIMARY KEY,
        username TEXT,
        first_name TEXT DEFAULT NULL,
        last_name TEXT DEFAULT NULL,
        date_of_birth TIMESTAMP DEFAULT NULL,
        gender TEXT DEFAULT NULL,
        city TEXT DEFAULT NULL,
        biography TEXT DEFAULT NULL,
        is_active INTEGER DEFAULT 1
    )""")


def create_photos_table(cursor) -> None:
    """Создает таблицу фотографий пользователей"""
    cursor.execute("""CREATE TABLE IF NOT EXISTS photos(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        photo BLOB,
        user_tg_id INTEGER,
        FOREIGN KEY (user_tg_id) REFERENCES users (user_tg_id) ON DELETE CASCADE
    )""")


def create_likes_table(cursor) -> None:
    """Создает таблицу лайков"""
    cursor.execute("""CREATE TABLE IF NOT EXISTS likes(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        who_chose INTEGER,
        who_was_chosen INTEGER,
        is_mutual INTEGER DEFAULT 0,
        FOREIGN KEY (who_chose) REFERENCES users (user_tg_id) ON DELETE CASCADE,
        FOREIGN KEY (who_was_chosen) REFERENCES users (user_tg_id) ON DELETE CASCADE
    )""")


def create_viewed_profiles_table(cursor) -> None:
    """Создает таблицу просмотренных профилей"""
    cursor.execute("""CREATE TABLE IF NOT EXISTS viewed_profiles(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        target_id INTEGER,
        viewed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users (user_tg_id) ON DELETE CASCADE,
        FOREIGN KEY (target_id) REFERENCES users (user_tg_id) ON DELETE CASCADE
    )""")


# Создаем БД при первом запуске
create_database()

def get_photo(user_tg_id: int) -> Optional[str]:
    """Получает фото пользователя из базы данных"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT photo FROM photos WHERE user_tg_id = ?", (user_tg_id,))
    photo = cursor.fetchone()
    conn.close()

    if photo:
        return photo[0]  # Возвращаем ID фото из Telegram (file_id)
    return None

def check_if_user_registered(user_tg_id: int) -> bool:
    """Проверяет, зарегистрирован ли пользователь"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT user_tg_id FROM users WHERE user_tg_id = ?", (user_tg_id,))
    user = cursor.fetchone()
    conn.close()
    return user is not None


def register_user(user_tg_id: int, username: str, first_name: Optional[str] = None, date_of_birth: Optional[str] = None, city: Optional[str] = None, biography: Optional[str] = None) -> None:
    """Регистрирует нового пользователя"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO users (user_tg_id, username, first_name, date_of_birth, city, biography) VALUES (?, ?, ?, ?, ?, ?)", 
                   (user_tg_id, username, first_name, date_of_birth, city, biography))
    conn.commit()
    conn.close()


def get_random_profile(exclude_user_id: int) -> Optional[dict]:
    """Выбирает случайный профиль, которого пользователь еще не смотрел"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()

    # ✅ Проверяем, какие анкеты уже просмотрены
    cursor.execute("""
        SELECT u.user_tg_id, u.username, u.first_name, u.date_of_birth, u.city, u.biography, p.photo
        FROM users u
        LEFT JOIN photos p ON u.user_tg_id = p.user_tg_id
        WHERE u.user_tg_id != ?
        AND u.is_active = 1
        AND u.user_tg_id NOT IN (
            SELECT target_id FROM viewed_profiles WHERE user_id = ?
        )
        ORDER BY RANDOM()
        LIMIT 1
    """, (exclude_user_id, exclude_user_id))

    profile = cursor.fetchone()

    if profile:
        # ✅ Добавляем анкету в `viewed_profiles`
        cursor.execute("INSERT INTO viewed_profiles (user_id, target_id) VALUES (?, ?)", (exclude_user_id, profile[0]))
        conn.commit()

        conn.close()
        return {
            "id": profile[0],
            "username": profile[1],
            "first_name": profile[2],
            "date_of_birth": profile[3],
            "city": profile[4] if profile[4] else "Не указан",
            "biography": profile[5] if profile[5] else "Описание отсутствует",
            "photo": profile[6]
        }

    conn.close()
    return None


def save_user_photo(user_tg_id: int, photo: bytes) -> None:
    """Сохраняет фото пользователя"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO photos (photo, user_tg_id) VALUES (?, ?)", (photo, user_tg_id))
    conn.commit()
    conn.close()


def like_profile(user_id: int, liked_user_id: int) -> bool:
    """Ставит лайк пользователю и проверяет взаимность"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()

    # Добавляем лайк
    cursor.execute("INSERT INTO likes (who_chose, who_was_chosen) VALUES (?, ?)", (user_id, liked_user_id))
    conn.commit()

    # Проверяем, есть ли взаимный лайк
    cursor.execute("SELECT id FROM likes WHERE who_chose = ? AND who_was_chosen = ?", (liked_user_id, user_id))
    mutual_like = cursor.fetchone()

    if mutual_like:
        # Обновляем статус взаимного лайка
        cursor.execute("UPDATE likes SET is_mutual = 1 WHERE who_chose = ? AND who_was_chosen = ?", (user_id, liked_user_id))
        cursor.execute("UPDATE likes SET is_mutual = 1 WHERE who_chose = ? AND who_was_chosen = ?", (liked_user_id, user_id))
        conn.commit()
        conn.close()
        return True  # Взаимный лайк

    conn.close()
    return False  # Лайк без взаимности


def add_viewed_profile(user_id: int, target_id: int) -> None:
    """Добавляет просмотренный профиль в список"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO viewed_profiles (user_id, target_id) VALUES (?, ?)", (user_id, target_id))
    conn.commit()
    conn.close()