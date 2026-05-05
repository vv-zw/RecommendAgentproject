# crawler/data_writer.py
"""
DataWriter：将 FetchResult 列表 upsert 到 app.content_items 表。
使用 PostgreSQL JSONB || 运算符合并 raw_source，保留已有键只更新 reviews。
"""

import json
import logging
import os
import sys
from dataclasses import asdict
from typing import List, Tuple

import psycopg
from psycopg.types.json import Jsonb

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from movie_recommendation.config import Config
from crawler.detail_fetcher import FetchResult, ReviewItem

logger = logging.getLogger("crawler.writer")


def _get_conn():
    url = Config.get_database_url()
    conn = psycopg.connect(url)
    conn.autocommit = True
    return conn


def _reviews_to_jsonb(reviews: List[ReviewItem]) -> Jsonb:
    """将 ReviewItem 列表转换为 JSONB 格式的 raw_source 字典。"""
    reviews_list = []
    for r in reviews:
        reviews_list.append({
            "author":  r.author,
            "content": r.content,
            "rating":  r.rating,
            "date":    r.date,
        })
    return Jsonb({"reviews": reviews_list})


UPSERT_SQL = """
INSERT INTO {schema}.content_items (
    source_item_id, content_type, title,
    director, actors, year, region, language,
    duration, episodes, plot, raw_source, updated_at
) VALUES (
    %(source_item_id)s, %(content_type)s, %(title)s,
    %(director)s, %(actors)s, %(year)s, %(region)s, %(language)s,
    %(duration)s, %(episodes)s, %(plot)s, %(raw_source)s, CURRENT_TIMESTAMP
)
ON CONFLICT (source_item_id, content_type)
DO UPDATE SET
    director   = EXCLUDED.director,
    actors     = EXCLUDED.actors,
    year       = EXCLUDED.year,
    region     = EXCLUDED.region,
    language   = EXCLUDED.language,
    duration   = EXCLUDED.duration,
    episodes   = EXCLUDED.episodes,
    plot       = EXCLUDED.plot,
    raw_source = COALESCE({schema}.content_items.raw_source, '{{}}'::jsonb)
                 || EXCLUDED.raw_source,
    updated_at = CURRENT_TIMESTAMP
"""


class DataWriter:
    """将爬取结果批量 upsert 到 PostgreSQL。"""

    def __init__(self):
        self.schema = Config.PGSCHEMA

    def write_batch(self, results: List[FetchResult]) -> Tuple[int, int]:
        """
        批量写入，单条失败不回滚整批。
        返回 (成功数, 失败数)。
        """
        success_count = 0
        fail_count = 0

        for result in results:
            if not result.success:
                # 爬取阶段已失败，跳过写入
                fail_count += 1
                continue
            ok = self.write_one(result)
            if ok:
                success_count += 1
            else:
                fail_count += 1

        return success_count, fail_count

    def write_one(self, result: FetchResult) -> bool:
        """
        写入单条 FetchResult。
        返回 True 表示成功，False 表示失败。
        """
        # title 不能为 None（数据库 NOT NULL 约束）
        # 若爬取未能解析到 title，使用 result.source_item_id 作为兜底
        title = result.title or f"[未知标题-{result.source_item_id}]"

        sql = UPSERT_SQL.format(schema=self.schema)
        params = {
            "source_item_id": result.source_item_id,
            "content_type":   result.content_type,
            "title":          title,
            "director":       result.director,
            "actors":         result.actors,
            "year":           result.year,
            "region":         result.region,
            "language":       result.language,
            "duration":       result.duration,
            "episodes":       result.episodes,
            "plot":           result.plot,
            "raw_source":     _reviews_to_jsonb(result.reviews),
        }

        try:
            conn = _get_conn()
            try:
                with conn.cursor() as cur:
                    cur.execute(sql, params)
                logger.debug(
                    f"[写入成功] {result.source_item_id} 《{result.title}》"
                )
                return True
            finally:
                conn.close()
        except Exception as e:
            logger.error(
                f"[写入失败] {result.source_item_id} 《{result.title}》：{e}"
            )
            return False
