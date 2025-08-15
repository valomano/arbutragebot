import requests
import logging
from backend.database.models import OrderBook
from backend.database.db_connector import get_db
from backend.core.liquidity_checker import get_all_pairs, LIQUIDITY_APIS, format_symbol
from datetime import datetime

# Логгируем по отдельному файлу
logging.basicConfig(
    filename="logs/orderbook.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    encoding="utf-8"
)


async def fetch_liquidity(session, exchange: str, asset: str, retries=3):
    """🔄 Асинхронно получает ликвидность для указанной пары на бирже."""
    if exchange not in LIQUIDITY_APIS:
        print(f"❌ Биржа {exchange} не поддерживает API ликвидности.")
        return None

def fetch_orderbook(exchange: str, asset: str, depth: int = 50):
    symbol = format_symbol(exchange, asset)
    url_template = LIQUIDITY_APIS.get(exchange)
    if not url_template:
        logging.warning(f"🔶 Нет API для {exchange}")
        return None
    
    url = url_template.format(symbol)

    try:
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        data = response.json()

        if exchange == "Binance":
            bids = [(float(p), float(q)) for p, q in data["bids"]]
            asks = [(float(p), float(q)) for p, q in data["asks"]]
        elif exchange == "Bybit":
            bids = [(float(i["price"]), float(i["size"])) for i in data["result"]["b"]]
            asks = [(float(i["price"]), float(i["size"])) for i in data["result"]["a"]]
        elif exchange == "KuCoin":
            bids = [(float(p), float(q)) for p, q in data["data"]["bids"]]
            asks = [(float(p), float(q)) for p, q in data["data"]["asks"]]
        elif exchange == "OKX":
            bids = [(float(p[0]), float(p[1])) for p in data["data"][0]["bids"]]
            asks = [(float(p[0]), float(p[1])) for p in data["data"][0]["asks"]]
        elif exchange == "MEXC":
            bids = [(float(p), float(q)) for p, q in data["bids"]]
            asks = [(float(p), float(q)) for p, q in data["asks"]]
        elif exchange == "Gateio":
            bids = [(float(p[0]), float(p[1])) for p in data["bids"]]
            asks = [(float(p[0]), float(p[1])) for p in data["asks"]]
        elif exchange == "Bitget":
            bids = [(float(p[0]), float(p[1])) for p in data["data"]["bids"]]
            asks = [(float(p[0]), float(p[1])) for p in data["data"]["asks"]]
        elif exchange == "HTX":
            bids = [(float(p[0]), float(p[1])) for p in data["tick"]["bids"]]
            asks = [(float(p[0]), float(p[1])) for p in data["tick"]["asks"]]
        elif exchange == "Poloniex":
            bids = [(float(p[0]), float(p[1])) for p in data["bids"]]
            asks = [(float(p[0]), float(p[1])) for p in data["asks"]]
        else:
            logging.warning(f"🔶 Не обработано API от {exchange}")
            return None

        return bids[:depth], asks[:depth]

    except Exception as e:
        logging.error(f"❌ Ошибка получения orderbook {exchange}:{asset} -> {e}")
        return None

def update_orderbooks():
    db = next(get_db())
    pairs = get_all_pairs()
    updated = 0

    for exchange, asset in pairs:
        result = fetch_orderbook(exchange, asset, depth=50)
        if not result:
            continue

        bids, asks = result
        orderbook = OrderBook(
            exchange=exchange,
            asset=asset,
            bids=bids,
            asks=asks,
            timestamp=datetime.utcnow()
        )

        db.merge(orderbook)
        updated += 1

    db.commit()
    db.close()
    logging.info(f"✅ Обновлены {updated} orderbooks")
