import logging
from loguru import logger
import sys

def setup_logger():
    logger.remove()
    logger.add(
        sys.stdout,
        format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan> - <level>{message}</level>",
        level="INFO"
    )
    logger.add(
        "logs/bot.log",
        rotation="1 day",
        retention="30 days",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name} - {message}",
        level="DEBUG"
    )
    logging.basicConfig(handlers=[], level=logging.INFO)
    logger.info("Logger initialized")