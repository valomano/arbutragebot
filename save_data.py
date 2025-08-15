from sqlalchemy.orm import Session  # type: ignore
from models import Price, ArbitrageSignal, Liquidity, Log

def save_price(db: Session, exchange: str, asset: str, price: float):
    new_price = Price(exchange=exchange, asset=asset, price=price)
    db.add(new_price)
    db.commit()

def save_arbitrage_signal(db: Session, asset: str, exchange_buy: str, exchange_sell: str, buy_price: float, sell_price: float, spread: float):
    signal = ArbitrageSignal(asset=asset, exchange_buy=exchange_buy, exchange_sell=exchange_sell, buy_price=buy_price, sell_price=sell_price, spread=spread)
    db.add(signal)
    db.commit()

def save_liquidity(db: Session, exchange: str, asset: str, bid_volume: float, ask_volume: float):
    liquidity = Liquidity(exchange=exchange, asset=asset, bid_volume=bid_volume, ask_volume=ask_volume)
    db.add(liquidity)
    db.commit()

def save_log(db: Session, level: str, message: str):
    log_entry = Log(level=level, message=message)
    db.add(log_entry)
    db.commit()
