import asyncio
import json
from sqlalchemy.orm import Session
from backend.database.db_connector import get_db
from backend.database.models import Price
from backend.utils.logger import logging
import logging
import websockets
import requests
import gzip
import aiohttp



# WebSocket URL и каналы для бирж
WS_ENDPOINTS = {
    "Binance": "wss://stream.binance.com:9443/ws/!ticker@arr",
    "Bybit": "wss://stream.bybit.com/v5/public/spot",
    "OKX": "wss://ws.okx.com:8443/ws/v5/public",
    "KuCoin": "wss://ws-api-spot.kucoin.com/?token=",
    "Gateio": "wss://api.gateio.ws/ws/v4/",
    "HTX": "wss://api.huobi.pro/ws",
    "MEXC": "wss://wbs.mexc.com/ws",
    "Bitget": "wss://ws.bitget.com/spot/v1/stream",
    "Poloniex": "wss://ws.poloniex.com/ws/public"
}

def get_bybit_symbols():
    url = "https://api.bybit.com/v5/market/instruments-info?category=spot"
    response = requests.get(url).json()
    symbols = [item["symbol"] for item in response.get("result", {}).get("list", [])]
    return symbols

async def get_and_save_initial_bybit_prices():
    url = "https://api.bybit.com/v5/market/tickers?category=spot"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            data = await response.json()
            prices = data.get('result', {}).get('list', [])
            for item in prices:
                symbol = item['symbol']
                price = float(item['lastPrice'])
                await save_price('Bybit', symbol, price)


def get_okx_symbols():
    url = "https://www.okx.com/api/v5/public/instruments?instType=SPOT"
    response = requests.get(url).json()
    symbols = [item["instId"] for item in response.get("data", [])]
    return symbols

def get_gateio_symbols():
    url = "https://api.gateio.ws/api/v4/spot/currency_pairs"
    response = requests.get(url).json()
    return [item["id"] for item in response if item.get("trade_status") == "tradable"]

async def save_price(exchange, symbol, price):
    db: Session = next(get_db())
    existing_price = db.query(Price).filter(Price.exchange == exchange, Price.asset == symbol).first()
    if existing_price:
        existing_price.price = price
    else:
        db.add(Price(exchange=exchange, asset=symbol, price=price))
    db.commit()

# Обработчики сообщений
#BINANCE
async def handle_binance(ws):
    async for message in ws:
        data = json.loads(message)
        for item in data:
            symbol = item['s']
            price = float(item['c'])
            await save_price('Binance', symbol, price)

#BYBIT
async def handle_bybit(ws):
    symbols = get_bybit_symbols()
    batch_size = 20
    symbol_batches = [symbols[i:i + batch_size] for i in range(0, len(symbols), batch_size)]

    # Подписываемся на все символы партиями
    for batch in symbol_batches:
        subscribe_message = {
            "op": "subscribe",
            "args": [f"tickers.{symbol}" for symbol in batch]
        }
        await ws.send(json.dumps(subscribe_message))
        await asyncio.sleep(0.2)

    async for message in ws:
        data = json.loads(message)
        if "topic" in data and data["topic"].startswith("tickers.") and "data" in data:
            ticker_data = data["data"]
            symbol = ticker_data.get("symbol")
            price = ticker_data.get("lastPrice")

            if symbol and price:
                await save_price('Bybit', symbol, float(price))

#OKX
async def handle_okx(ws):
    symbols = get_okx_symbols()
    batch_size = 20
    symbol_batches = [symbols[i:i + batch_size] for i in range(0, len(symbols), batch_size)]

    for batch in symbol_batches:
        subscribe_message = {
            "op": "subscribe",
            "args": [{"channel": "tickers", "instId": symbol} for symbol in batch]
        }
        await ws.send(json.dumps(subscribe_message))
        await asyncio.sleep(0.2)

    async for message in ws:
        data = json.loads(message)


        if data.get("arg", {}).get("channel") == "tickers" and "data" in data:
            for ticker in data["data"]:
                symbol = ticker['instId'].replace("-", "")
                price = ticker.get('last')
                if symbol and price:
                    await save_price('OKX', symbol, float(price))

#KUCOIN
async def handle_kucoin(_):
    while True:
        try:
            token_response = requests.post("https://api.kucoin.com/api/v1/bullet-public").json()
            ws_endpoint = token_response["data"]["instanceServers"][0]["endpoint"]
            token = token_response["data"]["token"]
            ws_url = f"{ws_endpoint}?token={token}"

            async with websockets.connect(ws_url) as websocket:
                subscribe_message = {
                    "id": "kucoin_prices",
                    "type": "subscribe",
                    "topic": "/market/ticker:all",
                    "response": True
                }
                await websocket.send(json.dumps(subscribe_message))
                logging.info("✅ KuCoin подписка отправлена!")

                async for message in websocket:
                    data = json.loads(message)

                    if data.get("type") == "ping":
                        pong_response = {"id": data["id"], "type": "pong"}
                        await websocket.send(json.dumps(pong_response))
                        logging.info("✅ KuCoin отправлен pong")
                        continue

                    if data.get("type") == "message" and "data" in data:
                        ticker = data["data"]
                        symbol = data.get("subject").replace("-", "")
                        price = ticker.get('price')
                        if symbol and price:
                            try:
                                await save_price('KuCoin', symbol, float(price))
                                logging.info(f"✅ KuCoin цена обновлена: {symbol} - {price}")
                            except Exception as save_exc:
                                return
        except Exception as e:
            await asyncio.sleep(5)

#GATEIO
async def handle_gateio(ws):
    symbols = get_gateio_symbols()
    batch_size = 10
    symbol_batches = [symbols[i:i + batch_size] for i in range(0, len(symbols), batch_size)]

    for batch in symbol_batches:
        subscribe_message = {
            "time": int(asyncio.get_event_loop().time()),
            "channel": "spot.tickers",
            "event": "subscribe",
            "payload": batch
        }
        await ws.send(json.dumps(subscribe_message))
        logging.info(f"📡 Gate.io подписка на: {batch}")
        await asyncio.sleep(0.5)

    # 🧠 Запускаем задачу, которая будет сама пинговать
    async def send_ping():
        while True:
            try:
                await ws.ping()
                logging.debug("📤 Отправлен ping")
                await asyncio.sleep(20)  # Gate.io отключает через ~30 сек без пинга
            except Exception as e:
                logging.error(f"❌ Ping error Gate.io: {e}")
                break

    asyncio.create_task(send_ping())

    async for message in ws:
        try:
            data = json.loads(message)

            if data.get("event") == "ping":
                await ws.send(json.dumps({"event": "pong"}))
                logging.info("🔁 Gate.io отправлен pong (json)")
                continue

            if data.get("channel") == "spot.tickers" and data.get("event") == "update":
                for ticker in data.get("result", []):
                    symbol = ticker.get("currency_pair", "").replace("_", "").upper()
                    price = float(ticker.get("last", 0))
                    if symbol and price > 0:
                        await save_price('Gateio', symbol, price)
                        logging.info(f"✅ Gate.io цена обновлена: {symbol} - {price}")
        except Exception as e:
            logging.error(f"❌ Ошибка Gate.io: {e} | message: {message}")




#HUOBI(HTX)
async def handle_htx(ws):
    subscribe_message = {"sub": "market.tickers", "id": "htx_prices"}
    await ws.send(json.dumps(subscribe_message))

    async for message in ws:
        decompressed_data = gzip.decompress(message).decode('utf-8') if isinstance(message, bytes) else message
        data = json.loads(decompressed_data)

        if 'ping' in data:
            pong_response = json.dumps({"pong": data["ping"]})
            await ws.send(pong_response)
        elif 'ch' in data and 'tick' in data:
            tickers = data['tick']
            symbol = tickers['symbol'].upper()
            price = float(tickers['close'])
            await save_price('HTX', symbol, price)



#MEXC
async def handle_mexc(ws):
    subscribe_message = {
        "method": "SUBSCRIPTION",
        "params": ["spot@public.deals.v3.api@BTCUSDT"],
    }
    await ws.send(json.dumps(subscribe_message))

    async for message in ws:
        data = json.loads(message)
        if data.get("c") == "spot@public.deals.v3.api":
            for deal in data.get("d", {}).get("deals", []):
                symbol = deal.get("s", "").upper()
                price = float(deal.get("p", 0))
                if symbol and price:
                    await save_price('MEXC', symbol, price)

#BITGET
async def handle_bitget(ws):
    subscribe_message = {
        "op": "subscribe",
        "args": [{"instType": "SP", "channel": "ticker", "instId": "default"}]
    }
    await ws.send(json.dumps(subscribe_message))

    async for message in ws:
        data = json.loads(message)
        if data.get("action") == "update" and "data" in data:
            for ticker in data["data"]:
                symbol = ticker["instId"].replace("_", "").upper()
                price = float(ticker["lastPr"])
                await save_price('Bitget', symbol, price)

#POLONIEX
async def handle_poloniex(ws):
    subscribe_message = {
        "event": "subscribe",
        "channel": ["ticker"],
        "symbols": ["all"]
    }
    await ws.send(json.dumps(subscribe_message))

    async def send_ping(ws):
        while True:
            try:
                await ws.send(json.dumps({"event": "ping"}))
                await asyncio.sleep(15)  # отправляем ping чаще
            except websockets.exceptions.ConnectionClosed:
                break

    asyncio.create_task(send_ping(ws))

    async for message in ws:
        data = json.loads(message)
        if data.get("channel") == "ticker" and data.get("data"):
            for ticker in data["data"]:
                symbol = ticker["symbol"].replace("_", "").upper()
                price = float(ticker["close"])
                await save_price('Poloniex', symbol, price)




# Пример обработчиков, для остальных бирж сделай аналогично

async def connect_exchange(exchange, url, handler):
    while True:
        try:
            async with websockets.connect(url) as ws:
                await handler(ws)
        except Exception as e:
            logging.error(f"Ошибка WebSocket {exchange}: {e}")
            await asyncio.sleep(5)  # переподключение после ошибки


async def main():
    # Для Bybit сначала загружаем REST-данные
    # await get_and_save_initial_bybit_prices()

    exchanges = [
        # ('Binance', WS_ENDPOINTS['Binance'], handle_binance),
        # ('Bybit', WS_ENDPOINTS['Bybit'], handle_bybit),
        # ('OKX', WS_ENDPOINTS['OKX'], handle_okx),
        # ('KuCoin', WS_ENDPOINTS['KuCoin'], handle_kucoin),
         ('Gateio', WS_ENDPOINTS['Gateio'], handle_gateio),
        # ('HTX', WS_ENDPOINTS['HTX'], handle_htx),
        # ('MEXC', WS_ENDPOINTS['MEXC'], handle_mexc),
        # ('Bitget', WS_ENDPOINTS['Bitget'], handle_bitget),
        # ('Poloniex', WS_ENDPOINTS['Poloniex'], handle_poloniex),
    ]

    

    # Затем запускаем WS-подключения
    tasks = [
        asyncio.create_task(connect_exchange(name, url, handler))
        for name, url, handler in exchanges
    ]

    await asyncio.gather(*tasks, return_exceptions=True)

if __name__ == "__main__":
    asyncio.run(main())
