import logging
import os

# 📂 Директория для логов
LOG_DIR = "logs"
LOG_FILE = os.path.join(LOG_DIR, "arbitrage.log")

# 🛠️ Создаем папку logs, если её нет
if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR)

# 🔧 Настраиваем логирование
logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    encoding="utf-8",
)



def log_arbitrage(message):
    """📜 Логирует арбитражные сигналы и анализ."""
    logging.info(message)

def log_error(message):
    """⚠️ Логирует ошибки."""
    error_log = os.path.join(LOG_DIR, "errors.log")
    logging.basicConfig(
        filename=error_log,
        level=logging.ERROR,
        format="%(asctime)s - ERROR - %(message)s",
        encoding="utf-8",
    )
    logging.error(message)

