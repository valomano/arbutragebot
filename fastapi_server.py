from fastapi import FastAPI, Depends, BackgroundTasks
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from backend.database.db_connector import get_db
from backend.database.models import Price, ArbitrageSignal
import os

# 📂 Определяем пути
BASE_DIR = os.path.abspath(os.path.dirname(__file__))  # backend/
ROOT_DIR = os.path.abspath(os.path.join(BASE_DIR, ".."))  # htdocs/

print(f"🚀 FastAPI сервер загружается из {ROOT_DIR}")

# 📂 Инициализация FastAPI
app = FastAPI()

# 📂 Подключаем статические файлы (CSS, JS)
app.mount("/static", StaticFiles(directory=os.path.join(ROOT_DIR, "frontend/static")), name="static")

# 📂 Подключаем HTML-шаблоны
TEMPLATES_DIR = os.path.join(ROOT_DIR, "frontend/templates")

# 📊 Главная страница (Dashboard)
@app.get("/")
async def root():
    return FileResponse(os.path.join(TEMPLATES_DIR, "dashboard.html"))

@app.get("/dashboard")
async def get_dashboard():
    return FileResponse(os.path.join(TEMPLATES_DIR, "dashboard.html"))

# 📊 Получение всех цен
@app.get("/prices")
def get_prices(db: Session = Depends(get_db)):
    prices = db.query(Price).all()
    return {"data": prices}

# 📈 Получение цены для конкретного актива
@app.get("/price/{symbol}")
def get_price(symbol: str, db: Session = Depends(get_db)):
    price = db.query(Price).filter(Price.asset == symbol).first()
    if price:
        return {"symbol": symbol, "price": price.price, "exchange": price.exchange}
    return {"error": "Asset not found"}

# 📊 Получение арбитражных сигналов
@app.get("/arbitrage")
def get_arbitrage_signals(db: Session = Depends(get_db)):
    signals = db.query(ArbitrageSignal).all()
    return {"data": signals}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="localhost", port=8080, log_level="debug")
