from sqlalchemy import Column, Integer, String, Boolean, Date, ForeignKey, DateTime, func
from sqlalchemy.orm import relationship

from sqlalchemy.orm import declarative_base
Base = declarative_base()

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)  # Уникальный ID пользователя
    username = Column(String, unique=True, index=True)  # Telegram username
    name = Column(String, nullable=False)  # Имя
    birthdate = Column(Date, nullable=False)  # Дата рождения
    city = Column(String, nullable=False)  # Город
    description = Column(String, nullable=True)  # Описание анкеты
    photo_id = Column(String, nullable=True)  # ID фото из Telegram
    is_active = Column(Boolean, default=True)  # Анкета включена/выключена


class ViewedProfile(Base):
    __tablename__ = "viewed_profiles"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)  # Кто смотрит анкету
    target_id = Column(Integer, ForeignKey("users.id"), nullable=False)  # Какая анкета просмотрена
    viewed_at = Column(DateTime, default=func.now())  # Когда просмотрена

    user = relationship("User", foreign_keys=[user_id])
    target = relationship("User", foreign_keys=[target_id])