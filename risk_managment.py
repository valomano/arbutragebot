def check_risk(asset: str, buy_exchange: str, sell_exchange: str, buy_price: float, sell_price: float, max_fee=0.5):
    """⚠ Проверяет риски арбитражной сделки."""
    
    # 📉 Проверяем разницу цены (слишком резкий скачок?)
    price_diff = abs(sell_price - buy_price) / buy_price * 100
    if price_diff > 10:
        print(f"⚠ Слишком резкое изменение цены {asset}: {price_diff}%")
        return False
    
    # 💸 Проверяем комиссии (если комиссия выше 0.5%, сделка невыгодная)
    trading_fee = 0.1  # TODO: Запрашивать реальную комиссию с API
    withdrawal_fee = 0.2  # TODO: Запрашивать реальные данные

    total_fee = trading_fee + withdrawal_fee
    if total_fee > max_fee:
        print(f"❌ Слишком высокая комиссия для {asset}: {total_fee}%")
        return False

    # ⏳ Проверяем скорость вывода (если долго - пропускаем)
    withdrawal_time = 30  # TODO: Запрашивать реальные данные в минутах
    if withdrawal_time > 60:
        print(f"⚠ Долгое время вывода {asset} с {buy_exchange} -> {sell_exchange}: {withdrawal_time} минут")
        return False

    print(f"✅ Сделка безопасна: {asset} ({buy_exchange} -> {sell_exchange})")
    return True
