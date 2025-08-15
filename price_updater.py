import asyncio
import requests
import random
from sqlalchemy.orm import Session
from backend.database.db_connector import get_db
from backend.database.models import Price

# 🔗 API URL для всех бирж
EXCHANGE_APIS = {
    "Binance": "https://api.binance.com/api/v3/ticker/price",
    "Bybit": "https://api.bybit.com/v5/market/tickers?category=spot",
    "Bitget": "https://api.bitget.com/api/v2/spot/market/tickers",
    "Gateio": "https://api.gateio.ws/api/v4/spot/tickers",
    "HTX": "https://api.huobi.pro/market/tickers",
    "KuCoin": "https://api.kucoin.com/api/v1/market/allTickers",
    "MEXC": "https://api.mexc.com/api/v3/ticker/price",
    "OKX": "https://www.okx.com/api/v5/market/tickers?instType=SPOT",
    "Poloniex": "https://api.poloniex.com/markets/price"
}

async def fetch_prices(exchange_name, api_url):
    """🔄 Запрашивает цены с биржи через REST API и обновляет базу данных"""
    db = next(get_db())
    
    # ⏱️ Добавим рандомную задержку перед каждым запросом (для обхода rate limit)
    await asyncio.sleep(random.uniform(3.0, 5.0))

    try:
        response = requests.get(api_url, timeout=10)
        response.raise_for_status()
        data = response.json()

        if isinstance(data, list):  
            prices = data
        elif isinstance(data, dict) and "data" in data:
            prices = data["data"]  
        elif isinstance(data, dict) and "result" in data and "list" in data["result"]:
            prices = data["result"]["list"]  
        else:
            print(f"⚠ Неизвестный формат данных {exchange_name}: {data}")
            return

        print(f"✅ Обновляю {exchange_name} ({len(prices)} пар)")

        for ticker in prices:
            try:
                if exchange_name == "Binance":
                    symbol, price = ticker["symbol"], float(ticker["price"])
                elif exchange_name == "Bybit":
                    symbol, price = ticker["symbol"], float(ticker["lastPrice"])
                elif exchange_name == "Bitget":
                    symbol, price = ticker["symbol"], float(ticker["lastPr"])
                elif exchange_name == "Gateio":
                    symbol, price = ticker["currency_pair"].replace("_", "").upper(), float(ticker["last"])
                elif exchange_name == "HTX":
                    symbol, price = ticker["symbol"].upper(), float(ticker["close"])
                elif exchange_name == "KuCoin":
                    symbol, price = ticker["symbol"].replace("-", "").upper(), float(ticker["last"])
                elif exchange_name == "MEXC":
                    symbol, price = ticker["symbol"].upper(), float(ticker["price"])
                elif exchange_name == "OKX":
                    symbol, price = ticker["instId"].replace("-", "").upper(), float(ticker["last"])
                elif exchange_name == "Poloniex":
                    symbol, price = ticker.get("symbol", "").replace("_", "").upper(), float(ticker.get("price", 0))
                else:
                    continue  

                # Запись в БД
                existing_price = db.query(Price).filter(Price.exchange == exchange_name, Price.asset == symbol).first()
                if existing_price:
                    existing_price.price = price
                else:
                    db.add(Price(exchange=exchange_name, asset=symbol, price=price))

            except (KeyError, ValueError, TypeError) as e:
                print(f"❌ Ошибка обработки {exchange_name} (пара {ticker}): {e}")

        db.commit()
        print(f"✅ Цены {exchange_name} обновлены в БД")

    except requests.exceptions.RequestException as e:
        print(f"❌ Ошибка {exchange_name}: {e}")

async def update_prices():
    """🔄 Фоновая задача для обновления цен каждые 10 секунд"""
    while True:
        for exchange, api_url in EXCHANGE_APIS.items():
            await fetch_prices(exchange, api_url)
        await asyncio.sleep(60)

if __name__ == "__main__":
    asyncio.run(update_prices())
