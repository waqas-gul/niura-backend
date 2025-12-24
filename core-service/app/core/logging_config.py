from logging.handlers import RotatingFileHandler
from pathlib import Path
import sys
from pythonjsonlogger import jsonlogger
import logging


def setup_json_logger():
    
    
    #create logs directory if notexists
    Path("logs").mkdir(exist_ok=True)
    
    #Base logger
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    
    #JSON formattor for structured Logs
    json_format = (
        "%(asctime)s %(levelname)s %(name)s %(filename)s %(lineno)d %(funcName)s %(message)s"
    )
    
    json_formatter = jsonlogger.JsonFormatter(json_format)
    
    #console handler (stdout)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(json_formatter)
    
    #Rotating file handler
    file_handler = RotatingFileHandler(
        "logs/core-service.json.log", maxBytes=10_000_000, backupCount=5, encoding ="utf-8"
    )
    
    file_handler.setFormatter(json_formatter)
    
    if logger.hasHandlers():
        logger.handlers.clear()
        
    logger.addHandler(console_handler)
    # logger.addHandler(file_handler)
    
    #Reduce noisy libraries
    logging.getLogger("uvicorn").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    
    logger.info("JSON structured logging initialized")
    return logger
    
    
    log_format = "%(asctime)"