# crawler/schema_validator.py
"""
SchemaValidator：爬取任务启动前检查并补全 content_items 表字段。
若字段缺失则自动执行 ALTER TABLE ADD COLUMN IF NOT EXISTS。
"""

import logging
import sys
import os

# 确保项目根目录在 sys.path 中
_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

import psycopg
from movie_recommendation.config import Config

logger = logging.getLogger("crawler.schema")


class SchemaValidationError(Exception):
    """ALTER TABLE 执行失败时抛出，调用方应终止爬取任务。"""
    pass


# 目标字段及其 PostgreSQL 类型
TARGET_COLUMNS: dict[str, str] = {
    "director":      "VARCHAR(255)",
    "actors":        "TEXT",
    "year":          "INTEGER",
    "region":        "VARCHAR(100)",
    "language":      "VARCHAR(100)",
    "duration":      "VARCHAR(100)",
    "episodes":      "VARCHAR(100)",
    "plot":          "TEXT",
    "raw_source":    "JSONB",
    "original_title": "VARCHAR(255)",
    "popularity":    "NUMERIC(10,4) DEFAULT 0",
    "status":        "VARCHAR(100)",
}


def _get_conn():
    url = Config.get_database_url()
    conn = psycopg.connect(url)
    conn.autocommit = True
    return conn


def validate_and_patch() -> None:
    """
    检查 app.content_items 表是否包含所有目标字段。
    缺失字段自动执行 ALTER TABLE ADD COLUMN IF NOT EXISTS。
    失败时抛出 SchemaValidationError。
    """
    schema = Config.PGSCHEMA
    table = "content_items"

    logger.info(f"开始验证表结构：{schema}.{table}")

    try:
        conn = _get_conn()
    except Exception as e:
        raise SchemaValidationError(f"无法连接数据库：{e}") from e

    try:
        with conn.cursor() as cur:
            # 查询现有字段
            cur.execute(
                """
                SELECT column_name
                FROM information_schema.columns
                WHERE table_schema = %s AND table_name = %s
                """,
                (schema, table),
            )
            existing_cols = {row[0] for row in cur.fetchall()}
            logger.debug(f"现有字段：{sorted(existing_cols)}")

            # 检查并补全缺失字段
            patched = []
            for col, col_type in TARGET_COLUMNS.items():
                if col not in existing_cols:
                    sql = (
                        f"ALTER TABLE {schema}.{table} "
                        f"ADD COLUMN IF NOT EXISTS {col} {col_type}"
                    )
                    logger.info(f"补充缺失字段：{col} {col_type}")
                    try:
                        cur.execute(sql)
                        patched.append(col)
                    except Exception as e:
                        raise SchemaValidationError(
                            f"ALTER TABLE 失败（字段 {col}）：{e}"
                        ) from e

            # 检查 raw_source 类型
            cur.execute(
                """
                SELECT data_type
                FROM information_schema.columns
                WHERE table_schema = %s AND table_name = %s
                  AND column_name = 'raw_source'
                """,
                (schema, table),
            )
            row = cur.fetchone()
            if row and row[0].lower() not in ("jsonb", "json"):
                logger.warning(
                    f"raw_source 字段类型为 {row[0]}，期望 JSONB，"
                    f"不强制修改，继续执行"
                )

        if patched:
            logger.info(f"表结构补全完成，新增字段：{patched}")
        else:
            logger.info("表结构验证通过，所有目标字段均已存在")

    except SchemaValidationError:
        raise
    except Exception as e:
        raise SchemaValidationError(f"表结构验证过程中发生异常：{e}") from e
    finally:
        conn.close()
