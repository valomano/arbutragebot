from sqlalchemy import Column, Integer, String, Float, DateTime, Text # type: ignore
from sqlalchemy.ext.declarative import declarative_base # type: ignore
from datetime import datetime


Base = declarative_base()

class Price(Base):
    __tablename__ = "prices"
    id = Column(Integer, primary_key=True, autoincrement=True)
    exchange = Column(String(50), nullable=False)
    asset = Column(String(20), nullable=False)
    price = Column(Float, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)

class ArbitrageSignal(Base):
    __tablename__ = "arbitrage_signals"

    id = Column(Integer, primary_key=True, autoincrement=True)
    asset = Column(String, nullable=False)
    buy_exchange = Column(String, nullable=False)  # ✅ Должно быть buy_exchange
    sell_exchange = Column(String, nullable=False)  # ✅ Должно быть sell_exchange
    buy_price = Column(Float, nullable=False)
    sell_price = Column(Float, nullable=False)
    spread = Column(Float, nullable=False)
    type = Column(String, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)


class Liquidity(Base):
    __tablename__ = "liquidity"
    id = Column(Integer, primary_key=True, autoincrement=True)
    exchange = Column(String(50), nullable=False)
    asset = Column(String(20), nullable=False)
    bid_volume = Column(Float, nullable=False)
    ask_volume = Column(Float, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)

class Log(Base):
    __tablename__ = "logs"
    id = Column(Integer, primary_key=True, autoincrement=True)
    level = Column(String(20), nullable=False)  # ERROR, INFO, WARNING
    message = Column(String(255), nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)

class OrderBook(Base):
    __tablename__ = "order_books"

    id = Column(Integer, primary_key=True, index=True)
    exchange = Column(String(50), nullable=False)
    asset = Column(String(50), nullable=False)
    bids = Column(Text, nullable=False)  # JSON-строка с bid-ордерами
    asks = Column(Text, nullable=False)  # JSON-строка с ask-ордерами
    timestamp = Column(DateTime, default=datetime.utcnow)