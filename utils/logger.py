"""
日志记录模块 - 统一管理日志输出
"""
import logging
import logging.handlers
import os
import sys
from datetime import datetime


def setup_logger(
    name="douban_crawler",
    log_level=logging.INFO,
    log_dir=None,
    log_file="crawler.log",
    console_output=True,
):
    """配置并返回logger实例"""
    logger = logging.getLogger(name)
    logger.setLevel(log_level)
    logger.handlers.clear()

    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    if log_dir and log_file:
        os.makedirs(log_dir, exist_ok=True)
        file_path = os.path.join(log_dir, log_file)
        file_handler = logging.handlers.RotatingFileHandler(
            file_path,
            maxBytes=10 * 1024 * 1024,
            backupCount=5,
            encoding="utf-8",
        )
        file_handler.setLevel(log_level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    if console_output:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(log_level)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

    return logger


def get_logger(name="douban_crawler"):
    """获取已有logger，不存在则创建默认"""
    logger = logging.getLogger(name)
    if not logger.handlers:
        from config import LOG_LEVEL, LOGS_DIR

        logger = setup_logger(name, LOG_LEVEL, LOGS_DIR, "crawler.log")
    return logger
