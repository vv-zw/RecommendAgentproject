# app_logger/logger.py
import logging
import os
import sys
from logging.handlers import RotatingFileHandler

# 保证logs目录存在
if not os.path.exists('logs'):
    os.makedirs('logs')

def setup_logger(log_path="logs/app.log", level="INFO"):
    """
    Sets up a standardized logger for the application.
    :param log_path: The path to the log file.
    :param level: The logging level.
    :return: A configured logger instance.
    """
    # Use a unique name for the logger to avoid conflicts
    logger = logging.getLogger("AIRecommendationApp")
    logger.setLevel(getattr(logging, level.upper(), logging.INFO))

    # 如果已经有handlers，则不再添加，避免重复日志
    if logger.hasHandlers():
        return logger

    # Formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # Console Handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # File Handler (with rotation)
    file_handler = RotatingFileHandler(
        log_path, maxBytes=10*1024*1024, backupCount=5, encoding='utf-8'
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    return logger

# 创建一个默认的logger实例供其他模块直接导入使用
logger = setup_logger()
