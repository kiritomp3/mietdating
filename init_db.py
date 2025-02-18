from db import Base, engine
from models import ViewedProfile  # Импортируем новую таблицу

Base.metadata.create_all(engine)  # Создаём только недостающие таблицы