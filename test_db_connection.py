from sqlalchemy.orm import sessionmaker # type: ignore
from sqlalchemy import inspect # type: ignore
import sys
import os

# Получаем путь к корню проекта (c:\xampp\htdocs\)
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

# Добавляем backend/database в путь поиска модулей
sys.path.append(os.path.join(BASE_DIR, "backend", "database"))

from db_connector import engine, get_db
from models import Base, Price


# Создаем таблицы, если их нет
Base.metadata.create_all(bind=engine)

# Проверяем подключение к базе
def test_connection():
    try:
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        print(f"✅ Успешное подключение! Найдены таблицы: {tables}")
    except Exception as e:
        print(f"❌ Ошибка подключения: {e}")

# Тестовая запись и чтение данных
def test_insert_and_read():
    db = next(get_db())
    
    # Добавляем тестовую цену
    new_price = Price(exchange="TestExchange", asset="BTC/USDT", price=50000.0)
    db.add(new_price)
    db.commit()
    print("✅ Тестовая запись добавлена!")
    
    # Читаем данные
    result = db.query(Price).all()
    print(f"📊 Найдено записей: {len(result)}")
    for r in result:
        print(f"{r.exchange} - {r.asset}: {r.price} USDT")

if __name__ == "__main__":
    test_connection()
    test_insert_and_read()