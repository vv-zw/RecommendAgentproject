# crawler/crawl_logger.py
"""日志配置：控制台 + RotatingFileHandler（10MB，保留5份）"""

import logging
import os
import time
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import List, Optional


LOG_DIR = Path(__file__).resolve().parents[1] / "logs"
LOG_FILE = LOG_DIR / "crawler.log"
FAILED_ITEMS_FILE = LOG_DIR / "failed_items.json"


def setup_logger(name: str = "crawler") -> logging.Logger:
    """
    配置并返回爬虫专用 Logger。
    - 控制台：INFO 级别
    - 文件：RotatingFileHandler，maxBytes=10MB，backupCount=5
    - 日志级别通过环境变量 LOG_LEVEL 配置（默认 INFO）
    """
    LOG_DIR.mkdir(parents=True, exist_ok=True)

    level_name = os.getenv("LOG_LEVEL", "INFO").upper()
    level = getattr(logging, level_name, logging.INFO)

    logger = logging.getLogger(name)
    logger.setLevel(level)

    if logger.handlers:
        return logger  # 避免重复添加 handler

    fmt = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # 控制台 handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)
    console_handler.setFormatter(fmt)
    logger.addHandler(console_handler)

    # 文件 handler（轮转）
    file_handler = RotatingFileHandler(
        LOG_FILE,
        maxBytes=10 * 1024 * 1024,  # 10 MB
        backupCount=5,
        encoding="utf-8",
    )
    file_handler.setLevel(level)
    file_handler.setFormatter(fmt)
    logger.addHandler(file_handler)

    return logger


class CrawlLogger:
    """结构化爬取任务日志，封装任务开始/结束/单条成功/失败的日志方法。"""

    def __init__(self):
        self.logger = setup_logger("crawler.task")
        self._task_start_time: Optional[float] = None

    def task_start(self, content_type: str, total: int) -> None:
        self._task_start_time = time.time()
        self.logger.info(
            f"═══ 爬取任务开始 ═══ 类型={content_type} 待爬取={total} 条"
        )

    def item_success(self, source_item_id: str, title: str, elapsed: float) -> None:
        self.logger.info(
            f"[成功] {source_item_id} 《{title}》 耗时={elapsed:.2f}s"
        )

    def item_failure(
        self, source_item_id: str, reason: str, retries: int
    ) -> None:
        self.logger.error(
            f"[失败] {source_item_id} 原因={reason} 重试次数={retries}"
        )

    def task_end(
        self,
        success: int,
        failed: int,
        elapsed: float,
        failed_ids: List[str],
    ) -> None:
        self.logger.info(
            f"═══ 爬取任务完成 ═══ 成功={success} 失败={failed} "
            f"总耗时={elapsed:.1f}s"
        )
        if failed_ids:
            self.logger.warning(
                f"失败条目列表（共 {len(failed_ids)} 个）：{', '.join(failed_ids)}"
            )

    def schema_check(self, message: str, level: str = "info") -> None:
        getattr(self.logger, level)(f"[表结构] {message}")
