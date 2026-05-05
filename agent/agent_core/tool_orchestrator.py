# agent/agent_core/tool_orchestrator.py
"""
ToolOrchestrator：LLM 驱动的 Function Calling 工具编排器。
LLM 自主决定调用哪些工具及传入什么参数，替换原有的 if-elif 分支逻辑。
"""
import json
import logging
from typing import Optional

import psycopg
import psycopg.rows
from movie_recommendation.config import Config

logger = logging.getLogger(__name__)

SCHEMA = Config.PGSCHEMA

# ── 工具 Schema 定义 ──────────────────────────────────────────────
TOOLS_SCHEMA = [
    {
        "type": "function",
        "function": {
            "name": "search_content",
            "description": "按关键词搜索影视内容，支持按类型、内容类型过滤。适合用户知道具体名字或关键词时使用。",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "搜索关键词，如影视名称、导演名、演员名、主题词"
                    },
                    "content_type": {
                        "type": "string",
                        "enum": ["movie", "series"],
                        "description": "内容类型，movie 为电影，series 为剧集/综艺"
                    },
                    "genres": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "类型过滤列表，如 ['科幻', '动作']"
                    },
                    "limit": {
                        "type": "integer",
                        "default": 10,
                        "description": "返回结果数量，默认 10"
                    }
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "semantic_search",
            "description": "语义向量检索，适合情感/氛围/主题描述，如'温暖治愈'、'烧脑悬疑'、'父女情'等模糊查询。",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "语义查询描述，支持情感、氛围、主题等自然语言描述"
                    },
                    "top_k": {
                        "type": "integer",
                        "default": 10,
                        "description": "返回结果数量"
                    }
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_similar_content",
            "description": "根据指定影视名称，检索风格/主题相似的其他作品。适合'类似XXX的电影'这类请求。",
            "parameters": {
                "type": "object",
                "properties": {
                    "content_title": {
                        "type": "string",
                        "description": "参考影视的名称，如'流浪地球'"
                    },
                    "limit": {
                        "type": "integer",
                        "default": 10,
                        "description": "返回结果数量"
                    }
                },
                "required": ["content_title"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_user_preference",
            "description": "获取当前用户的偏好历史，包括喜欢的类型、导演、演员。用于个性化推荐。",
            "parameters": {
                "type": "object",
                "properties": {
                    "user_id": {
                        "type": "string",
                        "description": "用户 ID"
                    }
                },
                "required": ["user_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_content_detail",
            "description": "查询指定影视的详细信息，包括剧情简介、导演、演员、评分等。",
            "parameters": {
                "type": "object",
                "properties": {
                    "content_id": {
                        "type": "integer",
                        "description": "影视内容的数据库 ID"
                    }
                },
                "required": ["content_id"]
            }
        }
    }
]

# Function Calling 最大循环次数，防止无限循环
MAX_TOOL_ITERATIONS = 5


def _get_conn():
    url = Config.get_database_url()
    return psycopg.connect(url, row_factory=psycopg.rows.dict_row)


def _row_to_result(row: dict) -> dict:
    """将 content_items 数据库行转换为标准结果格式。"""
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
        "region": row.get("region", "") or "",
        "language": row.get("language", "") or "",
        "duration": row.get("duration", "") or "",
        "episodes": row.get("episodes", "") or "",
    }


class ToolOrchestrator:
    """LLM 驱动的工具编排器，通过 Function Calling 循环执行工具调用。"""

    def execute(
        self,
        user_id: str,
        messages: list,
        preference_context: Optional[dict] = None,
    ) -> tuple[list, list]:
        """
        执行 Function Calling 循环，直到 LLM 不再请求工具调用。

        Args:
            user_id: 用户 ID
            messages: 包含对话历史的消息列表（含 system prompt）
            preference_context: 用户偏好上下文

        Returns:
            (updated_messages, structured_results)
            - updated_messages: 追加了工具调用结果的消息列表
            - structured_results: 所有工具调用返回的推荐结果列表（去重）
        """
        from ai_config.llm_client import chat_completion

        current_messages = list(messages)
        all_results: list = []
        seen_ids: set = set()

        for iteration in range(MAX_TOOL_ITERATIONS):
            try:
                response = chat_completion(
                    messages=current_messages,
                    tools=TOOLS_SCHEMA,
                    temperature=0.3,
                    max_tokens=1024,
                )
            except Exception as e:
                logger.error(f"Function Calling LLM 调用失败（第 {iteration+1} 次）：{e}")
                break

            choice = response.choices[0]
            message = choice.message

            # 没有工具调用，退出循环
            if not message.tool_calls:
                # 把最终的 assistant 消息追加到消息列表
                current_messages.append({
                    "role": "assistant",
                    "content": message.content or "",
                })
                logger.debug(f"Function Calling 完成，共 {iteration+1} 次迭代")
                break

            # 把 assistant 的工具调用消息追加到列表
            current_messages.append(message)

            # 执行每个工具调用
            for tool_call in message.tool_calls:
                func_name = tool_call.function.name
                try:
                    args = json.loads(tool_call.function.arguments)
                except json.JSONDecodeError:
                    args = {}
                    logger.warning(f"工具 {func_name} 参数解析失败：{tool_call.function.arguments}")

                logger.debug(f"执行工具：{func_name}，参数：{args}")
                tool_result = self._dispatch_tool(func_name, args, user_id)

                # 收集推荐结果（去重）
                if isinstance(tool_result, list):
                    for item in tool_result:
                        item_id = item.get("id")
                        if item_id and item_id not in seen_ids:
                            seen_ids.add(item_id)
                            all_results.append(item)

                # 把工具结果追加到消息列表
                current_messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": json.dumps(tool_result, ensure_ascii=False),
                })

        return current_messages, all_results

    def _dispatch_tool(self, func_name: str, args: dict, user_id: str):
        """根据工具名称分发到对应的执行函数。"""
        dispatch = {
            "search_content": lambda: self._tool_search_content(
                query=args.get("query", ""),
                content_type=args.get("content_type"),
                genres=args.get("genres"),
                limit=args.get("limit", 10),
            ),
            "semantic_search": lambda: self._tool_semantic_search(
                query=args.get("query", ""),
                top_k=args.get("top_k", 10),
            ),
            "get_similar_content": lambda: self._tool_get_similar_content(
                content_title=args.get("content_title", ""),
                limit=args.get("limit", 10),
            ),
            "get_user_preference": lambda: self._tool_get_user_preference(
                user_id=args.get("user_id", user_id),
            ),
            "get_content_detail": lambda: self._tool_get_content_detail(
                content_id=args.get("content_id"),
            ),
        }

        handler = dispatch.get(func_name)
        if not handler:
            logger.warning(f"未知工具：{func_name}")
            return {"error": f"未知工具：{func_name}"}

        try:
            return handler()
        except Exception as e:
            logger.error(f"工具 {func_name} 执行失败：{e}")
            return {"error": str(e)}

    # ── 工具实现 ──────────────────────────────────────────────────

    def _tool_search_content(
        self,
        query: str,
        content_type: Optional[str] = None,
        genres: Optional[list] = None,
        limit: int = 10,
    ) -> list:
        """关键词搜索：title、plot、genres 的 ILIKE 多字段查询。"""
        if not query:
            return []
        try:
            with _get_conn() as conn:
                with conn.cursor() as cur:
                    conditions = [
                        "(title ILIKE %s OR plot ILIKE %s OR genres ILIKE %s)"
                    ]
                    params: list = [f"%{query}%", f"%{query}%", f"%{query}%"]

                    if content_type in ("movie", "series"):
                        conditions.append("content_type = %s")
                        params.append(content_type)

                    if genres:
                        genre_conds = ["genres ILIKE %s" for _ in genres]
                        conditions.append(f"({' OR '.join(genre_conds)})")
                        params.extend(f"%{g}%" for g in genres)

                    where = " AND ".join(conditions)
                    params.append(int(limit))

                    cur.execute(
                        f"SELECT * FROM {SCHEMA}.content_items WHERE {where} "
                        f"ORDER BY popularity DESC NULLS LAST LIMIT %s",
                        params,
                    )
                    return [_row_to_result(r) for r in cur.fetchall()]
        except Exception as e:
            logger.error(f"search_content 查询失败：{e}")
            return []

    def _tool_semantic_search(self, query: str, top_k: int = 10) -> list:
        """
        语义检索（RAG 阶段完成前的占位实现）。
        当前用关键词搜索代替，RAG 完成后切换为 pgvector 近邻检索。
        """
        logger.debug(f"semantic_search 占位实现，使用关键词搜索：{query}")
        return self._tool_search_content(query=query, limit=top_k)

    def _tool_get_similar_content(self, content_title: str, limit: int = 10) -> list:
        """
        相似内容检索（RAG 阶段完成前的占位实现）。
        先找到参考影视，再按其类型搜索相似内容。
        """
        if not content_title:
            return []
        try:
            with _get_conn() as conn:
                with conn.cursor() as cur:
                    # 先找参考影视
                    cur.execute(
                        f"SELECT genres, content_type FROM {SCHEMA}.content_items "
                        f"WHERE title ILIKE %s LIMIT 1",
                        (f"%{content_title}%",),
                    )
                    ref = cur.fetchone()

                if not ref:
                    # 找不到参考影视，退化为关键词搜索
                    return self._tool_search_content(query=content_title, limit=limit)

                # 按参考影视的类型搜索相似内容
                genres_raw = ref.get("genres") or ""
                genres = [g.strip() for g in genres_raw.split("/") if g.strip()]
                content_type = ref.get("content_type")

                with _get_conn() as conn:
                    with conn.cursor() as cur:
                        if genres:
                            genre_conds = ["genres ILIKE %s" for _ in genres[:3]]
                            params: list = [f"%{g}%" for g in genres[:3]]
                            if content_type:
                                params.append(content_type)
                                type_cond = " AND content_type = %s"
                            else:
                                type_cond = ""
                            # 排除参考影视本身
                            params.append(f"%{content_title}%")
                            params.append(int(limit))
                            cur.execute(
                                f"SELECT * FROM {SCHEMA}.content_items "
                                f"WHERE ({' OR '.join(genre_conds)}){type_cond} "
                                f"AND title NOT ILIKE %s "
                                f"ORDER BY rating DESC, popularity DESC NULLS LAST LIMIT %s",
                                params,
                            )
                        else:
                            cur.execute(
                                f"SELECT * FROM {SCHEMA}.content_items "
                                f"ORDER BY popularity DESC NULLS LAST LIMIT %s",
                                (int(limit),),
                            )
                        return [_row_to_result(r) for r in cur.fetchall()]
        except Exception as e:
            logger.error(f"get_similar_content 查询失败：{e}")
            return []

    def _tool_get_user_preference(self, user_id: str) -> dict:
        """从 user_preferences 表查询用户偏好。"""
        if not user_id:
            return {"genres": [], "directors": [], "actors": []}
        try:
            with _get_conn() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        f"SELECT genres, director, actors FROM {SCHEMA}.user_preferences "
                        f"WHERE user_id = %s",
                        (user_id,),
                    )
                    rows = cur.fetchall()

            genres, directors, actors = set(), set(), set()
            for row in rows:
                if row.get("genres"):
                    for g in row["genres"].split("/"):
                        if g.strip():
                            genres.add(g.strip())
                if row.get("director") and row["director"].strip():
                    directors.add(row["director"].strip())
                if row.get("actors"):
                    for a in row["actors"].split("/"):
                        if a.strip():
                            actors.add(a.strip())

            return {
                "genres": list(genres),
                "directors": list(directors),
                "actors": list(actors),
            }
        except Exception as e:
            logger.error(f"get_user_preference 查询失败：{e}")
            return {"genres": [], "directors": [], "actors": []}

    def _tool_get_content_detail(self, content_id: Optional[int]) -> dict:
        """查询单条影视详情。"""
        if not content_id:
            return {"error": "content_id 不能为空"}
        try:
            with _get_conn() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        f"SELECT * FROM {SCHEMA}.content_items WHERE id = %s",
                        (int(content_id),),
                    )
                    row = cur.fetchone()
            if not row:
                return {"error": f"未找到 ID={content_id} 的影视"}
            return _row_to_result(row)
        except Exception as e:
            logger.error(f"get_content_detail 查询失败：{e}")
            return {"error": str(e)}
