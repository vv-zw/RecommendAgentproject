# rag/rag_engine.py
"""
RagEngine：基于 pgvector 的语义向量检索引擎。
替换原有的本地 TF-IDF 实现。
"""
import logging
import time
from typing import Optional

import psycopg
import psycopg.rows
from movie_recommendation.config import Config
from rag.embedding import get_text_embedding, build_content_text

logger = logging.getLogger(__name__)

SCHEMA = Config.PGSCHEMA


def _get_conn():
    url = Config.get_database_url()
    return psycopg.connect(url, row_factory=psycopg.rows.dict_row)


def _row_to_result(row: dict) -> dict:
    """将 content_items 行转换为标准结果格式。"""
    genres_raw = row.get("genres") or ""
    genres_list = [g.strip() for g in genres_raw.split("/") if g.strip()] if genres_raw else []
    return {
        "id": row.get("id"),
        "title": row.get("title", ""),
        "overview": row.get("plot", "") or "",
        "poster_path": row.get("cover_url", "") or "",
        "vote_average": float(row.get("rating", 0) or 0),
        "media_type": row.get("content_type", "movie"),
        "genres": genres_list,
        "popularity": float(row.get("popularity", 0) or 0),
        "director": row.get("director", "") or "",
        "actors": row.get("actors", "") or "",
        "year": row.get("year"),
        "similarity": float(row.get("similarity", 0) or 0),
    }


class RagEngine:
    """基于 pgvector 的语义向量检索引擎。"""

    def semantic_search(self, query: str, top_k: int = 10) -> list[dict]:
        """
        将查询文本向量化后在 pgvector 中执行余弦近邻检索。

        Args:
            query: 用户查询文本（支持情感/氛围描述）
            top_k: 返回结果数量

        Returns:
            按相似度降序排列的 content_items 列表，含 similarity 字段
        """
        # 1. 向量化查询
        query_vec = get_text_embedding(query)
        if query_vec is None:
            logger.warning(f"查询向量化失败，降级为关键词搜索：{query}")
            return self._fallback_keyword_search(query, top_k)

        # 2. pgvector 近邻检索
        try:
            with _get_conn() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        f"""
                        SELECT *, 1 - (embedding <=> %s::vector) AS similarity
                        FROM {SCHEMA}.content_items
                        WHERE embedding IS NOT NULL
                        ORDER BY embedding <=> %s::vector
                        LIMIT %s
                        """,
                        (query_vec, query_vec, top_k),
                    )
                    rows = cur.fetchall()
            return [_row_to_result(r) for r in rows]
        except Exception as e:
            logger.error(f"pgvector 检索失败，降级为关键词搜索：{e}")
            return self._fallback_keyword_search(query, top_k)

    def index_content(self, content_id: int) -> bool:
        """
        为单条影视记录生成并存储 embedding。

        Args:
            content_id: content_items 表的 id

        Returns:
            是否成功
        """
        try:
            with _get_conn() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        f"SELECT id, title, plot, genres FROM {SCHEMA}.content_items WHERE id = %s",
                        (content_id,),
                    )
                    row = cur.fetchone()

            if not row:
                logger.warning(f"未找到 content_id={content_id}")
                return False

            text = build_content_text(
                title=row.get("title", ""),
                plot=row.get("plot", "") or "",
                genres=row.get("genres", "") or "",
            )
            vec = get_text_embedding(text)
            if vec is None:
                return False

            with _get_conn() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        f"UPDATE {SCHEMA}.content_items SET embedding = %s::vector WHERE id = %s",
                        (vec, content_id),
                    )
                conn.commit()

            logger.debug(f"content_id={content_id} embedding 已更新")
            return True

        except Exception as e:
            logger.error(f"index_content 失败 content_id={content_id}：{e}")
            return False

    def batch_index(self, batch_size: int = 50) -> dict:
        """
        批量为所有未索引（embedding IS NULL）的记录生成 embedding。

        Args:
            batch_size: 每批处理数量（控制 API 调用频率）

        Returns:
            统计信息 {'total': N, 'success': N, 'failed': N, 'elapsed': N}
        """
        start = time.time()
        success = 0
        failed = 0

        try:
            with _get_conn() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        f"SELECT id, title, plot, genres FROM {SCHEMA}.content_items "
                        f"WHERE embedding IS NULL ORDER BY id"
                    )
                    rows = cur.fetchall()
        except Exception as e:
            logger.error(f"batch_index 查询失败：{e}")
            return {"total": 0, "success": 0, "failed": 0, "elapsed": 0}

        total = len(rows)
        logger.info(f"开始批量向量化，共 {total} 条记录")

        for i, row in enumerate(rows):
            content_id = row["id"]
            text = build_content_text(
                title=row.get("title", ""),
                plot=row.get("plot", "") or "",
                genres=row.get("genres", "") or "",
            )

            vec = get_text_embedding(text)
            if vec is None:
                failed += 1
                logger.warning(f"[{i+1}/{total}] content_id={content_id} 向量化失败，跳过")
                continue

            try:
                with _get_conn() as conn:
                    with conn.cursor() as cur:
                        cur.execute(
                            f"UPDATE {SCHEMA}.content_items SET embedding = %s::vector WHERE id = %s",
                            (vec, content_id),
                        )
                    conn.commit()
                success += 1
                if (i + 1) % 50 == 0:
                    logger.info(f"进度：{i+1}/{total}，成功 {success}，失败 {failed}")
            except Exception as e:
                failed += 1
                logger.error(f"[{i+1}/{total}] content_id={content_id} 写入失败：{e}")

            # 每批次后短暂休眠，避免 API 限流
            if (i + 1) % batch_size == 0:
                time.sleep(0.5)

        elapsed = time.time() - start
        result = {"total": total, "success": success, "failed": failed, "elapsed": round(elapsed, 1)}
        logger.info(f"批量向量化完成：{result}")
        return result

    def _fallback_keyword_search(self, query: str, limit: int = 10) -> list[dict]:
        """Embedding API 失败时的降级：PostgreSQL 关键词搜索。"""
        try:
            with _get_conn() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        f"""SELECT * FROM {SCHEMA}.content_items
                            WHERE title ILIKE %s OR plot ILIKE %s OR genres ILIKE %s
                            ORDER BY popularity DESC NULLS LAST LIMIT %s""",
                        (f"%{query}%", f"%{query}%", f"%{query}%", limit),
                    )
                    rows = cur.fetchall()
            return [_row_to_result(r) for r in rows]
        except Exception as e:
            logger.error(f"降级关键词搜索也失败：{e}")
            return []


# 模块级单例
rag_engine = RagEngine()
