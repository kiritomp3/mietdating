from db import Base, engine
import models

# Удаляем все таблицы
Base.metadata.drop_all(engine)
# Создаем заново
Base.metadata.create_all(engine)