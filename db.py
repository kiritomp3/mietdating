from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Данные для подключения
DB_USER = "postgres"
DB_PASSWORD = "kiritowaw"
DB_HOST = "localhost"
DB_PORT = "5432"
DB_NAME = "dating_bot"

# Используем обычный (синхронный) движок
DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# Создаём движок
engine = create_engine(DATABASE_URL, echo=True)

# Создаём сессию
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)