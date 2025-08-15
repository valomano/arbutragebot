from sqlalchemy.orm import Session
from backend.database.models import Price, ArbitrageSignal, OrderBook
from backend.core.liquidity_checker import check_liquidity, analyze_order_impact
from backend.core.risk_managment import check_risk
from backend.utils.logger import log_arbitrage
from sqlalchemy import and_
from datetime import datetime
import logging



MIN_SPREAD = 3.0  # Минимальный спред, при котором сигнал остаётся в БД

# Настроим логирование
logging.basicConfig(filename="logs/arbitrage.log", level=logging.INFO, format="%(asctime)s - %(message)s")


def estimate_price_impact(db: Session, exchange: str, asset: str, order_type: str, amount_usdt: float) -> float:
    """
    📉 Оценивает влияние ордера на цену (price impact).
    order_type: "buy" или "sell"
    amount_usdt: сумма в USDT
    """

    book = db.query(OrderBook).filter_by(exchange=exchange, asset=asset).first()
    if not book:
        return 100.0  # Если нет данных — считаем большой риск

    try:
        import ast
        side = ast.literal_eval(book.asks if order_type == "buy" else book.bids)
        if not side:
            return 100.0

        total_cost = 0.0
        acquired = 0.0

        for price_str, qty_str in side:
            price = float(price_str)
            qty = float(qty_str)
            max_buy = qty * price if order_type == "buy" else qty

            if order_type == "buy":
                if total_cost + max_buy < amount_usdt:
                    total_cost += max_buy
                    acquired += qty
                else:
                    needed = amount_usdt - total_cost
                    acquired += needed / price
                    break
            else:  # sell
                if acquired + qty < amount_usdt:
                    acquired += qty
                    total_cost += qty * price
                else:
                    total_cost += (amount_usdt - acquired) * price
                    break

        if acquired == 0:
            return 100.0

        market_price = float(side[0][0])
        average_price = total_cost / acquired
        impact = (average_price - market_price) / market_price * 100 if order_type == "buy" else \
                 (market_price - average_price) / market_price * 100
        return round(impact, 3)

    except Exception as e:
        logging.warning(f"⚠️ Ошибка расчета price impact для {exchange} {asset}: {e}")
        return 100.0



def find_arbitrage_opportunities(db: Session):
    analyze_order_impact(db)
  #  update_orderbooks(db)
    """🔍 Анализирует цены и ищет арбитражные возможности."""
    try:
        prices = db.query(Price).all()

        price_map = {}
        for price in prices:
            if price.asset not in price_map:
                price_map[price.asset] = []
            price_map[price.asset].append((price.exchange, price.price))

        logging.info(f"🔍 Анализируем {len(price_map)} активов...")

        signals = []
        skipped_liquidity = 0
        skipped_risk = 0
        skipped_spread = 0
        updated_signals = 0
        deleted_signals = 0
        skipped_order = 0
        
        # ✅ Межбиржевой арбитраж
        for asset, price_list in price_map.items():
            price_list.sort(key=lambda x: x[1])
            if len(price_list) > 1:
                low_exchange, low_price = price_list[0]
                high_exchange, high_price = price_list[-1]
                if low_price == 0:
                    continue
                spread = (high_price - low_price) / low_price * 100

               # logging.info(f"📊 {asset}: Мин цена {low_price} ({low_exchange}), Макс цена {high_price} ({high_exchange}) -> Спред: {spread:.2f}%")

                if spread >= 3:
                   # logging.info(f"🔎 Проверяем ликвидность {asset} -> {low_exchange}, {high_exchange}")
                    if check_liquidity(asset, low_exchange, db) and check_liquidity(asset, high_exchange, db):
                       # logging.info(f"⚡ Проверяем риски {asset} -> {low_exchange}, {high_exchange}")
                        if check_risk(asset, low_exchange, high_exchange, low_price, high_price):
                            impact_buy = estimate_price_impact(db, low_exchange, asset, "buy", amount_usdt=100)
                            impact_sell = estimate_price_impact(db, high_exchange, asset, "sell", amount_usdt=100)
                            if impact_buy < 1.5 and impact_sell < 1.5:
                                signal = ArbitrageSignal(
                                    asset=asset,
                                    buy_exchange=low_exchange,
                                    sell_exchange=high_exchange,
                                    buy_price=low_price,
                                    sell_price=high_price,
                                    spread=spread,
                                    type="межбиржевой",
                                    timestamp=datetime.utcnow()
                                )
                                signals.append(signal)
                            else:                            
                                skipped_order += 1
                                #logging.info(f"❌ Слишком большой price impact: BUY {impact_buy:.2f}% / SELL {impact_sell:.2f}%")
                        else:
                            skipped_risk += 1
                          #  logging.info(f"❌ Отказ из-за риска: {asset}")
                    else:
                        skipped_liquidity += 1
                       # logging.info(f"❌ Отказ из-за ликвидности: {asset}")
                else:
                    skipped_spread += 1
                   # logging.info(f"⛔ Спред ниже 1%: {asset} -> {spread:.2f}%")

       

      
    
        for signal in signals:
            log_message = (
                f"Арбитраж: {signal.asset} | Купить на {signal.buy_exchange} за {signal.buy_price} | "
                f"Продать на {signal.sell_exchange} за {signal.sell_price} | Профит: {signal.spread:.2f}% "
                f"| Тип: {signal.type}"
            )
           # logging.info(f"✅ {log_message}")

            existing = db.query(ArbitrageSignal).filter(
                ArbitrageSignal.asset == signal.asset,
                ArbitrageSignal.buy_exchange == signal.buy_exchange,
                ArbitrageSignal.sell_exchange == signal.sell_exchange
            ).first()

            if signal.spread >= MIN_SPREAD:
                if existing:
                    existing.buy_price = signal.buy_price
                    existing.sell_price = signal.sell_price
                    existing.spread = signal.spread
                    existing.timestamp = signal.timestamp
                    updated_signals += 1
                   # logging.info(f"🔁 Обновлён сигнал: {signal.asset} | Спред: {signal.spread:.2f}%")
                else:
                    db.add(signal)
                   # logging.info(f"➕ Добавлен сигнал: {signal.asset} | Спред: {signal.spread:.2f}%")
            else:
                if existing:
                    db.delete(existing)
                    deleted_signals += 1
                   # logging.info(f"❌ Удалён сигнал: {signal.asset} | Спред упал ниже {MIN_SPREAD}% ({signal.spread:.2f}%)")

        db.commit()

        logging.info(f"✅ Обработка завершена: {len(signals)} сигналов")
        logging.info(f"📉 Пропущено по спреду: {skipped_spread}")
        logging.info(f"💧 Пропущено по ликвидности: {skipped_liquidity}")
        logging.info(f"⚠ Пропущено влияние на цену: {skipped_order}")
        logging.info(f"⚠ Пропущено по рискам: {skipped_risk}")
        logging.info(f"🔁 Обновлены сигналы: {updated_signals}")
        logging.info(f"❌ Удалены сигналы: {deleted_signals}")
        logging.info(f"----------------------------------------------------")
        db.close()
        return signals

    except Exception as e:
        logging.error(f"❌ Ошибка в find_arbitrage_opportunities: {e}")
        db.rollback()
        db.close()
        return []

