import asyncio
import json
import websockets
from sqlalchemy.orm import Session
from backend.database.models import Liquidity, Price
from backend.database.db_connector import get_db
from datetime import datetime

# Функция для получения всех пар из базы данных
def get_all_pairs():
    db = next(get_db())
    pairs = db.query(Price.exchange, Price.asset).all()
    db.close()
    return pairs

def format_symbol(exchange: str, asset: str) -> str:
    if "USDT" not in asset:
        return asset
    base_asset = asset.replace("USDT", "")
    if exchange in ["KuCoin", "OKX"]:
        return f"{base_asset}-USDT"
    elif exchange in ["Gateio", "Poloniex"]:
        return f"{base_asset}_USDT"
    else:
        return asset

async def fetch_binance_liquidity(asset: str):
    symbol = asset.lower()
    url = f"wss://stream.binance.com:9443/ws/{symbol}@depth5@100ms"
    try:
        async with websockets.connect(url) as ws:
            response = await ws.recv()
            data = json.loads(response)
            bids = data.get("bids", [])
            asks = data.get("asks", [])
            bid_volume = sum(float(b[1]) for b in bids[:5])
            ask_volume = sum(float(a[1]) for a in asks[:5])
            return "Binance", asset.upper(), bid_volume, ask_volume, bids, asks
    except Exception as e:
        print(f"❌ Ошибка Binance ({asset}): {e}")
        return None

# Здесь можно реализовать аналогичные функции для других бирж

async def update_all_liquidity(pairs):
    results = []
    for exchange, asset in pairs:
        if exchange == "Binance":
            print(f"🌐 Проверка пары {asset} на Binance")
            result = await fetch_binance_liquidity(asset)
            if result:
                print(f"✅ Получено: {result[0]} {result[1]}")
                results.append(result)
            else:
                print(f"❌ Нет данных по {asset}")
    return results


def check_liquidity(asset, exchange, db: Session):
    liquidity_data = db.query(Liquidity).filter(
        Liquidity.asset == asset, Liquidity.exchange == exchange
    ).first()
    if liquidity_data is None:
        return False
    return liquidity_data.bid_volume > 0 and liquidity_data.ask_volume > 0

async def main():
    pairs = get_all_pairs()
    results = await update_all_liquidity(pairs)
    db = next(get_db())
    valid_assets = set()
    for exchange, asset, bid_volume, ask_volume, bids, asks in results:
        existing_liquidity = db.query(Liquidity).filter(Liquidity.exchange == exchange, Liquidity.asset == asset).first()
        if existing_liquidity:
            existing_liquidity.bid_volume = bid_volume
            existing_liquidity.ask_volume = ask_volume
            existing_liquidity.timestamp = datetime.utcnow()
        else:
            db.add(Liquidity(
                exchange=exchange,
                asset=asset,
                bid_volume=bid_volume,
                ask_volume=ask_volume,
                timestamp=datetime.utcnow()
            ))
    # 🧹 Удаляем невалидные пары для этой биржи (только Binance, пока)
    binance_assets_in_db = db.query(Price).filter(Price.exchange == "Binance").all()
    for pair in binance_assets_in_db:
        if (pair.exchange, pair.asset) not in valid_assets:
            print(f"🗑 Удаляю невалидную пару: {pair.exchange} - {pair.asset}")
            db.delete(pair)
            # 🎯 Здесь можно анализировать bids/asks и оценивать влияние на рынок
            price_impact = analyze_order_impact(bids, asks, bid_volume, ask_volume)
            print(f"💡 Влияние на цену ({exchange} - {asset}): {price_impact:.4f}%")

    db.commit()
    db.close()
    print("✅ Ликвидность и влияние на рынок обновлены!")

def analyze_order_impact(bids, asks, bid_volume, ask_volume):
    if not bids or not asks:
        return 0
    best_bid_price = float(bids[0][0])
    best_ask_price = float(asks[0][0])
    avg_bid_price = sum(float(b[0]) for b in bids[:5]) / len(bids[:5])
    avg_ask_price = sum(float(a[0]) for a in asks[:5]) / len(asks[:5])
    impact = abs(avg_ask_price - avg_bid_price) / ((best_bid_price + best_ask_price) / 2) * 100
    return impact

if __name__ == "__main__":
    asyncio.run(main())
