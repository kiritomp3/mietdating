from sqlalchemy import Column, Integer, String, Boolean, Date, ForeignKey, DateTime, func, Index
from sqlalchemy.orm import relationship
from db import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)  # Уникальный ID пользователя (Telegram ID)
    username = Column(String, unique=True, index=True)  # Telegram username
    name = Column(String, nullable=True)  # Имя (соответствует first_name)
    last_name = Column(String, nullable=True)  # Фамилия
    birthdate = Column(Date, nullable=True)  # Дата рождения (соответствует date_of_birth)
    gender = Column(String, nullable=True)  # Пол
    city = Column(String, nullable=True)  # Город
    description = Column(String, nullable=True)  # Описание (соответствует biography)
    is_active = Column(Boolean, default=True)  # Анкета включена/выключена
    last_sent_profile = Column(Integer, nullable=True)  # ID последнего отправленного профиля
    likes_received = Column(Integer, default=0)  # Количество полученных лайков
    sex = Column(String, nullable=True)  # Пол (дубликат gender?)
    looking_for = Column(String, nullable=True)  # Кого ищет пользователь
    relationship_type = Column(String, nullable=True)  # Тип отношений
    marital_status = Column(String, default="Нет")  # Семейное положение
    lp = Column(Integer, nullable=True)  # ЛП
    module = Column(String, nullable=True)  # Модуль

    # Связь с таблицей photos
    photos = relationship("Photo", back_populates="user", cascade="all, delete-orphan")
    # Связь с таблицами likes и viewed_profiles
    likes_given = relationship("Like", foreign_keys="[Like.user_id]", back_populates="user")
    likes_received_rel = relationship("Like", foreign_keys="[Like.liked_user_id]", back_populates="liked_user")
    viewed_profiles = relationship("ViewedProfile", foreign_keys="[ViewedProfile.user_id]", back_populates="user")
    targeted_profiles = relationship("ViewedProfile", foreign_keys="[ViewedProfile.target_id]", back_populates="target")

class Photo(Base):
    __tablename__ = "photos"

    id = Column(Integer, primary_key=True, autoincrement=True)  # Уникальный ID записи
    photo = Column(String, nullable=False)  # Telegram file_id (хранится как строка)
    user_tg_id = Column(Integer, ForeignKey("users.id"), nullable=False)  # Внешний ключ на users

    # Связь с таблицей users
    user = relationship("User", back_populates="photos")

class Like(Base):
    __tablename__ = "likes"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)  # Уникальный ID лайка
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)  # Кто поставил лайк
    liked_user_id = Column(Integer, ForeignKey("users.id"), nullable=False)  # Кого лайкнули
    is_mutual = Column(Boolean, default=False)  # Взаимный ли лайк

    # Связь с таблицей users
    user = relationship("User", foreign_keys=[user_id], back_populates="likes_given")
    liked_user = relationship("User", foreign_keys=[liked_user_id], back_populates="likes_received_rel")

    # Индексы для оптимизации поиска лайков
    __table_args__ = (
        Index('idx_user_id', user_id),
        Index('idx_liked_user_id', liked_user_id),
    )

class ViewedProfile(Base):
    __tablename__ = "viewed_profiles"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)  # Уникальный ID записи
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)  # Кто смотрел
    target_id = Column(Integer, ForeignKey("users.id"), nullable=False)  # Чей профиль смотрели
    viewed_at = Column(DateTime(timezone=True), default=func.now(), nullable=False)  # Время просмотра

    # Связь с таблицей users
    user = relationship("User", foreign_keys=[user_id], back_populates="viewed_profiles")
    target = relationship("User", foreign_keys=[target_id], back_populates="targeted_profiles")

    # Индекс для оптимизации поиска по времени просмотра
    __table_args__ = (
        Index('idx_user_viewed_at', user_id, viewed_at),
    )