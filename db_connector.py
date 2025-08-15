from sqlalchemy import create_engine # type: ignore 
from sqlalchemy.orm import sessionmaker # type: ignore 
import yaml # type: ignore 
import os

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
CONFIG_PATH = os.path.join(BASE_DIR, "config.yaml")

with open(CONFIG_PATH, "r") as file:
    config = yaml.safe_load(file)

# Формируем строку подключения
DATABASE_URL = f"mysql+pymysql://{config['db']['user']}:{config['db']['password']}@{config['db']['host']}/{config['db']['name']}"

# Создаем подключение
engine = create_engine(
    DATABASE_URL,
    echo=False,        #     Выводы SQL в LOG
    pool_size=20,      # ✅ Увеличиваем количество соединений в пуле
    max_overflow=30,   # ✅ Увеличиваем максимальное количество соединений
    pool_timeout=60    # ✅ Ждем 60 секунд перед ошибкой
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Функция для работы с БД
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
