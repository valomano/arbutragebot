import asyncio
from sqlalchemy.orm import Session
from backend.database.db_connector import get_db
from backend.core.arbitrage import find_arbitrage_opportunities
from backend.core.liquidity_checker import update_all_liquidity
from backend.core.liquidity_checker import check_liquidity
from backend.database.models import Liquidity
from backend.database.models import Price

from frontend import app



db = next(get_db())

# Получаем все пары из базы
pairs = [(p.exchange, p.asset) for p in db.query(Price).all()]

# Запускаем асинхронное обновление ликвидности
liquidity_data = asyncio.run(update_all_liquidity(pairs))

# ✅ Записываем в базу
for exchange, asset, bid_vol, ask_vol in liquidity_data:
    existing_liquidity = db.query(Liquidity).filter(Liquidity.exchange == exchange, Liquidity.asset == asset).first()
    if existing_liquidity:
        existing_liquidity.bid_volume = bid_vol
        existing_liquidity.ask_volume = ask_vol
    else:
        db.add(Liquidity(exchange=exchange, asset=asset, bid_volume=bid_vol, ask_volume=ask_vol))

db.commit()
print(f"✅ Обновление ликвидности завершено!")

async def run_arbitrage():
    """🔄 Фоновая задача для запуска арбитражного анализа каждые 10 секунд"""
    while True:
        db: Session = next(get_db())
        find_arbitrage_opportunities(db)
        db.close()
        await asyncio.sleep(10)


if __name__ == "__main__":
    asyncio.run(run_arbitrage())
