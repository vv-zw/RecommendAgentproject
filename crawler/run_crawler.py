#!/usr/bin/env python
# crawler/run_crawler.py
"""
豆瓣爬虫入口脚本。

用法：
  python crawler/run_crawler.py                          # 启动定时调度
  python crawler/run_crawler.py --run-now                # 立即爬取全部
  python crawler/run_crawler.py --run-now --type movie --limit 10
  python crawler/run_crawler.py --retry-failed           # 重跑上次失败条目
"""

import argparse
import json
import logging
import os
import sys
import time
from pathlib import Path
from typing import List, Optional, Tuple

# ── 路径设置 ──────────────────────────────────────────────────────
_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from crawler.crawl_logger import CrawlLogger, FAILED_ITEMS_FILE, setup_logger
from crawler.data_writer import DataWriter
from crawler.detail_fetcher import DetailFetcher
from crawler.schema_validator import SchemaValidationError, validate_and_patch
from crawler.scheduler import Scheduler
from crawler.utils import random_delay
from movie_recommendation.config import Config

import psycopg

# 初始化根日志
setup_logger("crawler")
logger = logging.getLogger("crawler.main")
crawl_logger = CrawlLogger()


# ── 数据库查询 ────────────────────────────────────────────────────

def _get_conn():
    url = Config.get_database_url()
    conn = psycopg.connect(url, row_factory=psycopg.rows.dict_row)
    conn.autocommit = True
    return conn


def fetch_source_ids(
    content_type: str,
    limit: Optional[int] = None,
) -> List[Tuple[str, str, str]]:
    """
    从数据库读取待爬取的 (source_item_id, content_type, title) 列表。
    只返回 source_item_id 为纯数字的条目（豆瓣真实 ID），跳过 UUID 等无效 ID。
    content_type: 'movie' | 'series' | 'all'
    """
    schema = Config.PGSCHEMA
    conn = _get_conn()
    try:
        with conn.cursor() as cur:
            if content_type == "all":
                where = "source_item_id ~ '^[0-9]+$'"
                params: list = []
            else:
                where = "content_type = %s AND source_item_id ~ '^[0-9]+$'"
                params = [content_type]

            sql = (
                f"SELECT source_item_id, content_type, title "
                f"FROM {schema}.content_items "
                f"WHERE {where} "
                f"ORDER BY id"
            )
            if limit:
                sql += f" LIMIT {int(limit)}"

            cur.execute(sql, params)
            rows = [(r["source_item_id"], r["content_type"], r["title"] or "") for r in cur.fetchall()]
            logger.info(f"共找到 {len(rows)} 条有效豆瓣 ID 待爬取")
            return rows
    finally:
        conn.close()


# ── 失败条目持久化 ────────────────────────────────────────────────

def save_failed_items(failed: list) -> None:
    """将失败条目写入 logs/failed_items.json。"""
    FAILED_ITEMS_FILE.parent.mkdir(parents=True, exist_ok=True)
    data = {
        "last_run": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "failed_items": failed,
    }
    with open(FAILED_ITEMS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    logger.info(f"失败条目已保存到 {FAILED_ITEMS_FILE}")


def load_failed_items() -> List[Tuple[str, str, str]]:
    """从 logs/failed_items.json 读取上次失败的条目。"""
    if not FAILED_ITEMS_FILE.exists():
        logger.warning(f"未找到失败记录文件：{FAILED_ITEMS_FILE}")
        return []
    with open(FAILED_ITEMS_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    items = data.get("failed_items", [])
    return [
        (item["source_item_id"], item["content_type"], item.get("title", ""))
        for item in items
    ]


# ── 核心爬取任务 ──────────────────────────────────────────────────

def run_crawl_task(
    content_type: str = "all",
    limit: Optional[int] = None,
    items: Optional[List[Tuple[str, str, str]]] = None,
) -> None:
    """
    执行一次完整的爬取任务。

    Args:
        content_type: 'movie' | 'series' | 'all'
        limit: 最大爬取条目数（None 表示不限制）
        items: 指定条目列表（用于 --retry-failed），None 时从数据库读取
    """
    # 1. 验证表结构
    try:
        validate_and_patch()
    except SchemaValidationError as e:
        logger.error(f"表结构验证失败，终止爬取：{e}")
        return

    # 2. 获取待爬取条目
    if items is None:
        items = fetch_source_ids(content_type, limit)

    if not items:
        logger.info("没有找到待爬取的条目，任务结束")
        return

    total = len(items)
    crawl_logger.task_start(content_type, total)

    fetcher = DetailFetcher()
    writer = DataWriter()

    success_count = 0
    fail_count = 0
    failed_records = []

    # 3. 逐条爬取
    for idx, (source_id, ctype, title) in enumerate(items, 1):
        logger.info(f"[{idx}/{total}] 爬取：{source_id} 《{title}》")
        t_start = time.time()

        try:
            result = fetcher.fetch(source_id, ctype)
            elapsed = time.time() - t_start

            if result.success:
                ok = writer.write_one(result)
                if ok:
                    success_count += 1
                    crawl_logger.item_success(source_id, result.title or title, elapsed)
                else:
                    fail_count += 1
                    crawl_logger.item_failure(source_id, "数据库写入失败", result.retries)
                    failed_records.append({
                        "source_item_id": source_id,
                        "content_type": ctype,
                        "title": title,
                        "reason": "数据库写入失败",
                        "retries": result.retries,
                        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
                    })
            else:
                fail_count += 1
                crawl_logger.item_failure(source_id, result.error or "未知错误", result.retries)
                failed_records.append({
                    "source_item_id": source_id,
                    "content_type": ctype,
                    "title": title,
                    "reason": result.error or "未知错误",
                    "retries": result.retries,
                    "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
                })

        except Exception as e:
            elapsed = time.time() - t_start
            fail_count += 1
            logger.error(f"[{source_id}] 未预期异常：{e}")
            crawl_logger.item_failure(source_id, str(e), 0)
            failed_records.append({
                "source_item_id": source_id,
                "content_type": ctype,
                "title": title,
                "reason": str(e),
                "retries": 0,
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
            })

        # 条目间随机延迟
        if idx < total:
            random_delay()

    # 4. 任务汇总
    total_elapsed = time.time() - (crawl_logger._task_start_time or time.time())
    failed_ids = [r["source_item_id"] for r in failed_records]
    crawl_logger.task_end(success_count, fail_count, total_elapsed, failed_ids)

    # 5. 持久化失败条目
    if failed_records:
        save_failed_items(failed_records)


# ── CLI ───────────────────────────────────────────────────────────

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="豆瓣影视数据爬虫",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例：
  python crawler/run_crawler.py                          # 启动定时调度（每天凌晨2点）
  python crawler/run_crawler.py --run-now                # 立即爬取全部
  python crawler/run_crawler.py --run-now --type movie --limit 10
  python crawler/run_crawler.py --retry-failed           # 重跑上次失败条目
        """,
    )
    parser.add_argument(
        "--run-now",
        action="store_true",
        help="立即触发一次爬取，不等待定时调度",
    )
    parser.add_argument(
        "--type",
        choices=["movie", "series", "all"],
        default="all",
        help="指定爬取内容类型（默认 all）",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        metavar="N",
        help="限制本次爬取的最大条目数（用于测试）",
    )
    parser.add_argument(
        "--retry-failed",
        action="store_true",
        help="仅重新爬取上次任务中失败的条目",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    if args.retry_failed:
        # 重跑失败条目
        logger.info("模式：重跑上次失败条目")
        failed_items = load_failed_items()
        if not failed_items:
            logger.info("没有失败条目需要重跑")
            return
        logger.info(f"共 {len(failed_items)} 个失败条目待重跑")
        run_crawl_task(items=failed_items)

    elif args.run_now:
        # 立即执行
        logger.info(f"模式：立即爬取 type={args.type} limit={args.limit}")
        run_crawl_task(content_type=args.type, limit=args.limit)

    else:
        # 启动定时调度
        logger.info("模式：定时调度")
        scheduler = Scheduler(
            job_func=lambda: run_crawl_task(content_type="all")
        )
        scheduler.start()


if __name__ == "__main__":
    main()
