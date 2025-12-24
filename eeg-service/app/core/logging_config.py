# app/core/logging_config.py
from logging.handlers import RotatingFileHandler
from pathlib import Path
import logging, sys
from pythonjsonlogger import jsonlogger

def setup_json_logger(service_name: str = "eeg-service"):
    Path("logs").mkdir(exist_ok=True)

    logger = logging.getLogger()                # root
    logger.setLevel(logging.INFO)

    json_format = (
        "%(asctime)s %(levelname)s %(name)s %(message)s "
        "%(filename)s %(lineno)d %(funcName)s"
    )
    formatter = jsonlogger.JsonFormatter(json_format)

    console = logging.StreamHandler(sys.stdout)
    console.setFormatter(formatter)

    fileh = RotatingFileHandler(
        f"logs/{service_name}.json.log", maxBytes=10_000_000, backupCount=5, encoding="utf-8"
    )
    fileh.setFormatter(formatter)

    if logger.hasHandlers():
        logger.handlers.clear()
    logger.addHandler(console)
    logger.addHandler(fileh)

    # quiet noisy libs
    logging.getLogger("uvicorn").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.INFO)

    logger.info("JSON structured logging initialized")
    return logger
