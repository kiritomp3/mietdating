#from sqlalchemy import Column, Integer, String, Boolean, Date, ForeignKey, DateTime, func, Index
#from sqlalchemy.orm import relationship
#from db import Base

#class User(Base):
#   __tablename__ = "users"
#
#    id = Column(Integer, primary_key=True, index=True)  # Уникальный ID пользователя
#    username = Column(String, unique=True, index=True)  # Telegram username
#    name = Column(String, nullable=False)  # Имя
#    birthdate = Column(Date, nullable=False)  # Дата рождения
#    city = Column(String, nullable=False)  # Город
#    description = Column(String, nullable=True)  # Описание анкеты
#    photo_id = Column(String, nullable=True)  # ID фото из Telegram
#    is_active = Column(Boolean, default=True)  # Анкета включена/выключена



#class ViewedProfile(Base):
 
#   __tablename__ = "viewed_profiles"
#
#    id = Column(Integer, primary_key=True, index=True)
#    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
#    target_id = Column(Integer, ForeignKey("users.id"), nullable=False)
#    viewed_at = Column(DateTime, default=func.now())

#    user = relationship("User", foreign_keys=[user_id])
#    target = relationship("User", foreign_keys=[target_id])

    # Добавляем индекс для оптимизации поиска по времени просмотра
#    __table_args__ = (
#        Index('idx_user_viewed_at', user_id, viewed_at),
#    )


#class Like(Base):
#    __tablename__ = "likes"
#
#    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
#    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
#    liked_user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
#    is_mutual = Column(Boolean, default=False)