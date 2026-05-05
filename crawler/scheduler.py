# crawler/scheduler.py
"""
Scheduler：使用 schedule 库按配置时间定时触发爬取任务。
通过 threading.Event 防止任务并发运行。
"""

import logging
import os
import threading
import time
from typing import Callable

import schedule

logger = logging.getLogger("crawler.scheduler")

# 默认每天凌晨 2 点运行
DEFAULT_RUN_TIME = "02:00"


class Scheduler:
    """定时调度器，每天在指定时间触发一次爬取任务。"""

    def __init__(self, job_func: Callable):
        """
        Args:
            job_func: 无参数的可调用对象，代表一次完整的爬取任务
        """
        self._job_func = job_func
        self._running = threading.Event()  # 任务运行中标志
        self._run_time = os.getenv("CRAWLER_RUN_TIME", DEFAULT_RUN_TIME)

    def _safe_job(self) -> None:
        """带任务锁的 job 包装，防止并发运行。"""
        if self._running.is_set():
            logger.warning(
                "上一次爬取任务仍在运行，跳过本次定时触发"
            )
            return

        self._running.set()
        try:
            logger.info(f"定时任务触发，开始执行爬取")
            self._job_func()
        except Exception as e:
            logger.error(f"爬取任务执行异常：{e}")
        finally:
            self._running.clear()

    def start(self) -> None:
        """
        阻塞运行定时调度器。
        按 CRAWLER_RUN_TIME 环境变量（默认 02:00）每天触发一次。
        """
        logger.info(
            f"定时调度器启动，每天 {self._run_time} 触发爬取任务"
        )
        schedule.every().day.at(self._run_time).do(self._safe_job)

        while True:
            schedule.run_pending()
            time.sleep(30)  # 每 30 秒检查一次
