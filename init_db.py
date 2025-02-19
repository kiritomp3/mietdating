from db import Base, engine
import models  # Импортируем новую таблицу

Base.metadata.create_all(engine)  # Создаём только недостающие таблицы