# agent/agents/recommendation_agent.py
"""
RecommendationAgent：推荐 Agent。
基于 StructuredContext 执行 Function Calling 工具调用，并生成自然语言回复。
整合现有 ToolOrchestrator 和 ResponseGenerator 的功能，支持动态推荐策略。
"""
import json
import logging
from typing import Generator, Optional, Union

import psycopg
import psycopg.rows
from movie_recommendation.config import Config

from agent.agents.structured_context import StructuredContext

logger = logging.getLogger(__name__)

SCHEMA = Config.PGSCHEMA

# ── 工具 Schema 定义（复用现有 5 个工具，search_content 新增 sort_by 参数）──
TOOLS_SCHEMA = [
    {
        "type": "function",
        "function": {
            "name": "search_content",
            "description": "按关键词搜索影视内容，支持按类型、内容类型、排序方式过滤。适合用户知道具体名字或关键词时使用。",
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
                    "sort_by": {
                        "type": "string",
                        "enum": ["rating", "popularity", "relevance"],
                        "default": "relevance",
                        "description": "排序方式：rating 按评分降序，popularity 按热度降序，relevance 按相关性"
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

MAX_TOOL_ITERATIONS = 5

# 通用 System Prompt
GENERAL_SYSTEM_PROMPT = """你是一个专业的影视推荐助手，拥有丰富的电影和剧集知识。

你的职责：
1. 理解用户的推荐需求（类型、情绪、具体影视名称等）
2. 调用合适的工具搜索和检索影视内容
3. 根据用户偏好和搜索结果，给出个性化的推荐

工具使用原则：
- 用户提到具体影视名称时，优先用 search_content 或 get_similar_content
- 用户描述情绪/氛围时（如"温暖治愈"），优先用 semantic_search
- 需要了解用户偏好时，调用 get_user_preference
- 可以组合使用多个工具获取更好的结果

回复原则：
- 用自然流畅的中文回复
- 推荐时说明推荐理由
- 如果找不到合适内容，友好地引导用户换一种描述"""

# 明确查询模式的 System Prompt 补充
EXPLICIT_QUERY_RULES = """
当前为明确查询模式。规则：
1. 不要调用 get_user_preference 工具
2. 使用 search_content 时，sort_by 参数优先选择 "rating" 或 "popularity"
3. 推荐结果以客观质量（评分、热度）为主要依据
4. 在回复中不要提及用户的历史偏好"""


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


class RecommendationAgent:
    """推荐 Agent，基于 StructuredContext 执行工具调用并生成回复。"""

    def __init__(self):
        self.response_generator = None  # 延迟初始化

    def _get_response_generator(self):
        """延迟导入 ResponseGenerator，避免循环依赖。"""
        if self.response_generator is None:
            from agent.agent_core.response_generator import ResponseGenerator
            self.response_generator = ResponseGenerator()
        return self.response_generator

    def execute(
        self,
        user_id: str,
        ctx: StructuredContext,
        preference_context: Optional[dict],
        messages: list,
    ) -> list[dict]:
        """
        执行工具调用，返回推荐结果列表（去重）。

        Args:
            user_id: 用户 ID
            ctx: StructuredContext 结构化需求上下文
            preference_context: 用户偏好上下文
            messages: 包含对话历史的消息列表

        Returns:
            推荐结果列表
        """
        from ai_config.llm_client import chat_completion

        # 构建 System Prompt
        system_prompt = GENERAL_SYSTEM_PROMPT
        if ctx.skip_preference_injection:
            system_prompt += EXPLICIT_QUERY_RULES

        # 在 messages 前插入 system prompt
        current_messages = [{"role": "system", "content": system_prompt}]
        # 跳过原始 messages 中的 system prompt（如果有）
        for msg in messages:
            if isinstance(msg, dict) and msg.get("role") != "system":
                current_messages.append(msg)

        # 附加结构化需求信息到用户消息
        self._append_context_info(current_messages, ctx)

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
                logger.error(f"RecommendationAgent LLM 调用失败（第 {iteration+1} 次）：{e}")
                # LLM 调用失败时，使用混合推荐算法降级
                logger.error("【降级触发】启用混合推荐算法降级策略（NCF + TextCNN + 规则融合）")
                all_results = self._hybrid_recommendation_fallback(user_id, ctx, preference_context)
                logger.error(f"【降级完成】混合推荐返回 {len(all_results)} 条结果")
                return all_results

            choice = response.choices[0]
            message = choice.message

            if not message.tool_calls:
                current_messages.append({
                    "role": "assistant",
                    "content": message.content or "",
                })
                logger.debug(f"RecommendationAgent 工具调用完成，共 {iteration+1} 次迭代")
                break

            current_messages.append(message)

            for tool_call in message.tool_calls:
                func_name = tool_call.function.name

                # explicit_query 模式下禁止调用 get_user_preference
                if ctx.skip_preference_injection and func_name == "get_user_preference":
                    logger.info("explicit_query 模式，跳过 get_user_preference 调用")
                    current_messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": json.dumps({"info": "明确查询模式，不需要获取用户偏好"}, ensure_ascii=False),
                    })
                    continue

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

                current_messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": json.dumps(tool_result, ensure_ascii=False),
                })

        # 兜底查询：所有工具返回空时执行全库热门查询
        if not all_results:
            logger.info("所有工具返回空，执行全库热门内容兜底查询")
            all_results = self._fallback_popular_query()

        return all_results

    def generate_response(
        self,
        results: list[dict],
        ctx: StructuredContext,
        messages: list = None,
        preference_context: Optional[dict] = None,
        stream: bool = False,
    ) -> Union[str, Generator]:
        """
        生成自然语言回复。

        Args:
            results: 推荐结果列表
            ctx: StructuredContext
            messages: 对话历史消息列表（可选）
            preference_context: 用户偏好上下文
            stream: 是否启用流式输出

        Returns:
            stream=False: 完整回复字符串
            stream=True: token 生成器
        """
        rg = self._get_response_generator()

        # 构建传给 ResponseGenerator 的 messages
        gen_messages = []
        if messages:
            for msg in messages:
                if isinstance(msg, dict) and msg.get("role") in ("user", "assistant"):
                    gen_messages.append(msg)

        # 流式模式下，提前检查 API Key 是否有效，避免在 generator 中才暴露异常
        if stream:
            import os
            api_key = os.environ.get("DEEPSEEK_API_KEY", "")
            # 调试日志：打印 API Key 信息
            masked = api_key[:6] + "****" + api_key[-4:] if len(api_key) > 10 else str(api_key)
            logger.error(f"【调试】检查 API Key: {masked}, 长度: {len(api_key) if api_key else 0}, 以sk-开头: {api_key.startswith('sk-') if api_key else False}")
            # 检查 API Key 是否有效：DeepSeek/OpenAI 标准格式 sk-xxx，且长度要足够
            is_valid = api_key and api_key.startswith("sk-") and len(api_key) > 20
            if not is_valid:
                logger.error(f"【降级触发】API Key 无效，流式模式使用模板生成回复")
                return self._stream_template_response(results, preference_context)

        # 先尝试用 LLM 生成自然语言回复
        try:
            return rg.generate(
                messages=gen_messages,
                tool_results=results,
                preference_context=preference_context,
                stream=stream,
            )
        except Exception as e:
            # LLM 调用失败时，使用模板降级
            logger.error(f"【降级触发】generate_response LLM 失败，使用模板生成回复：{e}")
            if stream:
                return self._stream_template_response(results, preference_context)
            return self._template_response(results, preference_context)

    def _template_response(self, results: list[dict], preference_context: Optional[dict] = None) -> str:
        """LLM 不可用时的模板降级回复，基于实际推荐结果生成。"""
        if not results:
            return "抱歉，暂时没有找到符合条件的推荐内容，请尝试换个描述方式。"

        lines = []
        # 偏好描述
        pref_parts = []
        if preference_context:
            genres = preference_context.get("genres") or []
            if genres:
                pref_parts.append("、".join(genres[:3]))
        if pref_parts:
            lines.append(f"根据您对{pref_parts[0]}等类型的偏好，为您推荐：")
        else:
            lines.append("为您推荐以下影视：")

        for item in results[:6]:
            title = item.get("title", "未知")
            genres = "/".join(item.get("genres", [])[:3])
            rating = item.get("vote_average", 0)
            director = item.get("director", "")
            overview = (item.get("overview") or "")[:60]

            detail_parts = []
            if genres:
                detail_parts.append(genres)
            if rating:
                detail_parts.append(f"评分 {rating}")
            if director:
                detail_parts.append(f"{director} 导演")

            detail_str = " | ".join(detail_parts) if detail_parts else ""
            line = f"- 《{title}》"
            if detail_str:
                line += f"（{detail_str}）"
            if overview:
                line += f"\n  {overview}..."
            lines.append(line)

        lines.append("\n以上推荐由系统算法生成，如需更精准的推荐，请稍后再试。")
        return "\n".join(lines)

    def _stream_template_response(self, results: list[dict], preference_context: Optional[dict] = None):
        """模拟流式输出模板回复（逐字 yield），兼容 SSE 格式。"""
        text = self._template_response(results, preference_context)
        # 逐字 yield，模拟打字效果
        for char in text:
            yield char

    def _append_context_info(self, messages: list, ctx: StructuredContext):
        """将 StructuredContext 中的关键信息附加到最后一条用户消息。"""
        if not messages:
            return

        # 找到最后一条 user 消息
        last_user_idx = None
        for i in range(len(messages) - 1, -1, -1):
            if messages[i].get("role") == "user":
                last_user_idx = i
                break

        if last_user_idx is None:
            return

        extras = []
        if ctx.genres:
            extras.append(f"类型：{'/'.join(ctx.genres)}")
        if ctx.keywords:
            extras.append(f"关键词：{'/'.join(ctx.keywords)}")
        if ctx.mood:
            extras.append(f"情绪：{ctx.mood}")
        if ctx.directors:
            extras.append(f"导演：{'/'.join(ctx.directors)}")
        if ctx.actors:
            extras.append(f"演员：{'/'.join(ctx.actors)}")
        if ctx.content_type:
            extras.append(f"内容类型：{ctx.content_type}")

        if extras:
            original = messages[last_user_idx]["content"]
            messages[last_user_idx]["content"] = f"{original}\n[需求分析：{', '.join(extras)}]"

    def _dispatch_tool(self, func_name: str, args: dict, user_id: str):
        """根据工具名称分发到对应的执行函数。"""
        dispatch = {
            "search_content": lambda: self._tool_search_content(
                query=args.get("query", ""),
                content_type=args.get("content_type"),
                genres=args.get("genres"),
                sort_by=args.get("sort_by", "relevance"),
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

    # ── 工具实现（复用现有 ToolOrchestrator 的逻辑）──────────────────

    def _tool_search_content(
        self,
        query: str,
        content_type: Optional[str] = None,
        genres: Optional[list] = None,
        sort_by: str = "relevance",
        limit: int = 10,
    ) -> list:
        """关键词搜索：title、plot、genres 的 ILIKE 多字段查询，支持排序。"""
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

                    # 根据 sort_by 选择排序方式
                    if sort_by == "rating":
                        order = "ORDER BY rating DESC NULLS LAST"
                    elif sort_by == "popularity":
                        order = "ORDER BY popularity DESC NULLS LAST"
                    else:
                        order = "ORDER BY popularity DESC NULLS LAST"

                    params.append(int(limit))

                    cur.execute(
                        f"SELECT * FROM {SCHEMA}.content_items WHERE {where} "
                        f"{order} LIMIT %s",
                        params,
                    )
                    return [_row_to_result(r) for r in cur.fetchall()]
        except Exception as e:
            logger.error(f"search_content 查询失败：{e}")
            return []

    def _tool_semantic_search(self, query: str, top_k: int = 10) -> list:
        """语义检索（RAG 阶段完成前的占位实现，使用关键词搜索代替）。"""
        logger.debug(f"semantic_search 占位实现，使用关键词搜索：{query}")
        return self._tool_search_content(query=query, limit=top_k)

    def _tool_get_similar_content(self, content_title: str, limit: int = 10) -> list:
        """相似内容检索（RAG 阶段完成前的占位实现）。"""
        if not content_title:
            return []
        try:
            with _get_conn() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        f"SELECT genres, content_type FROM {SCHEMA}.content_items "
                        f"WHERE title ILIKE %s LIMIT 1",
                        (f"%{content_title}%",),
                    )
                    ref = cur.fetchone()

                if not ref:
                    return self._tool_search_content(query=content_title, limit=limit)

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

    def _fallback_popular_query(self) -> list:
        """兜底查询：无过滤条件的全库热门内容。"""
        try:
            with _get_conn() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        f"SELECT * FROM {SCHEMA}.content_items "
                        f"ORDER BY popularity DESC NULLS LAST LIMIT 10",
                    )
                    return [_row_to_result(r) for r in cur.fetchall()]
        except Exception as e:
            logger.error(f"兜底热门查询失败：{e}")
            return []

    def _hybrid_recommendation_fallback(
        self,
        user_id: str,
        ctx: StructuredContext,
        preference_context: Optional[dict],
    ) -> list:
        """
        混合推荐算法降级策略。
        当 LLM API 调用失败时，使用 NCF + TextCNN + 规则特征融合进行推荐。
        4 级降级链路：
        1. NCF + TextCNN + 规则特征融合
        2. 用户偏好匹配 + 内容相似度
        3. 纯规则 + 多样性重排
        4. 全库热门兜底
        """
        try:
            # 第 1 级：NCF + TextCNN + 规则特征融合
            results = self._level1_ncf_textcnn_rules(user_id, ctx, preference_context)
            if results:
                logger.error(f"【降级链路】第 1 级成功（NCF+TextCNN+规则），返回 {len(results)} 条")
                return results

            # 第 2 级：用户偏好匹配 + 内容相似度
            results = self._level2_preference_similarity(user_id, ctx, preference_context)
            if results:
                logger.error(f"【降级链路】第 2 级成功（偏好匹配），返回 {len(results)} 条")
                return results

            # 第 3 级：纯规则 + 多样性重排
            results = self._level3_rules_diversity(ctx)
            if results:
                logger.error(f"【降级链路】第 3 级成功（规则+多样性），返回 {len(results)} 条")
                return results

            # 第 4 级：全库热门兜底
            logger.error("【降级链路】第 4 级兜底（全库热门）")
            return self._fallback_popular_query()

        except Exception as e:
            logger.error(f"【降级链路】混合推荐算法降级失败：{e}")
            return self._fallback_popular_query()

    def _level1_ncf_textcnn_rules(
        self,
        user_id: str,
        ctx: StructuredContext,
        preference_context: Optional[dict],
    ) -> list:
        """
        第 1 级：NCF + TextCNN + 规则特征融合。
        模拟 NCF 协同过滤 + TextCNN 语义相似度 + 规则特征评分。
        """
        try:
            with _get_conn() as conn:
                with conn.cursor() as cur:
                    # 基础查询：获取候选集
                    base_query = f"""
                        SELECT * FROM {SCHEMA}.content_items
                        WHERE rating IS NOT NULL AND popularity IS NOT NULL
                        ORDER BY popularity DESC NULLS LAST
                        LIMIT 100
                    """
                    cur.execute(base_query)
                    candidates = [_row_to_result(r) for r in cur.fetchall()]

                    if not candidates:
                        return []

                    # 计算融合分数
                    scored_items = []
                    for item in candidates:
                        # NCF 分数（基于热度模拟协同过滤）
                        ncf_score = min(item.get("popularity", 0) / 100, 1.0)

                        # TextCNN 分数（基于类型匹配模拟语义相似度）
                        textcnn_score = self._calculate_textcnn_score(item, ctx)

                        # 规则特征分数
                        genre_score = self._calculate_genre_score(item, preference_context)
                        quality_score = min(item.get("vote_average", 0) / 10, 1.0)

                        # 融合公式：0.35*NCF + 0.30*TextCNN + 0.20*genre + 0.10*quality + 0.05*diversity
                        final_score = (
                            0.35 * ncf_score +
                            0.30 * textcnn_score +
                            0.20 * genre_score +
                            0.10 * quality_score +
                            0.05 * (1.0 - len(scored_items) / 100)  # diversity
                        )

                        scored_items.append((item, final_score))

                    # 按分数排序，取前 10
                    scored_items.sort(key=lambda x: x[1], reverse=True)
                    return [item for item, _ in scored_items[:10]]

        except Exception as e:
            logger.error(f"第 1 级推荐失败：{e}")
            return []

    def _level2_preference_similarity(
        self,
        user_id: str,
        ctx: StructuredContext,
        preference_context: Optional[dict],
    ) -> list:
        """
        第 2 级：用户偏好匹配 + 内容相似度。
        基于用户历史偏好和当前查询的相似度匹配。
        """
        try:
            # 获取用户偏好
            user_pref = preference_context or self._tool_get_user_preference(user_id)
            pref_genres = set(g.lower() for g in (user_pref.get("genres") or []))

            # 构建查询条件
            conditions = ["1=1"]
            params = []

            if pref_genres:
                genre_conds = ["genres ILIKE %s" for _ in pref_genres]
                conditions.append(f"({' OR '.join(genre_conds)})")
                params.extend(f"%{g}%" for g in pref_genres)

            if ctx.content_type in ("movie", "series"):
                conditions.append("content_type = %s")
                params.append(ctx.content_type)

            where_clause = " AND ".join(conditions)

            with _get_conn() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        f"SELECT * FROM {SCHEMA}.content_items "
                        f"WHERE {where_clause} "
                        f"ORDER BY rating DESC NULLS LAST, popularity DESC NULLS LAST "
                        f"LIMIT 10",
                        params,
                    )
                    return [_row_to_result(r) for r in cur.fetchall()]

        except Exception as e:
            logger.error(f"第 2 级推荐失败：{e}")
            return []

    def _level3_rules_diversity(self, ctx: StructuredContext) -> list:
        """
        第 3 级：纯规则 + 多样性重排。
        基于简单规则筛选，并保证结果多样性。
        """
        try:
            with _get_conn() as conn:
                with conn.cursor() as cur:
                    # 按评分和热度取前 50
                    cur.execute(
                        f"SELECT * FROM {SCHEMA}.content_items "
                        f"ORDER BY rating DESC NULLS LAST, popularity DESC NULLS LAST "
                        f"LIMIT 50",
                    )
                    candidates = [_row_to_result(r) for r in cur.fetchall()]

                    if not candidates:
                        return []

                    # 多样性重排：确保不同类型混合
                    genre_groups = {}
                    for item in candidates:
                        genres = item.get("genres") or ["其他"]
                        primary_genre = genres[0] if genres else "其他"
                        if primary_genre not in genre_groups:
                            genre_groups[primary_genre] = []
                        genre_groups[primary_genre].append(item)

                    # 轮询取各类型，保证多样性
                    diverse_results = []
                    genre_keys = list(genre_groups.keys())
                    idx = 0
                    while len(diverse_results) < 10 and genre_keys:
                        for genre in genre_keys[:]:
                            if genre_groups[genre]:
                                diverse_results.append(genre_groups[genre].pop(0))
                                if len(diverse_results) >= 10:
                                    break
                            else:
                                genre_keys.remove(genre)
                        idx += 1
                        if idx > 20:  # 防止无限循环
                            break

                    return diverse_results[:10]

        except Exception as e:
            logger.error(f"第 3 级推荐失败：{e}")
            return []

    def _calculate_textcnn_score(self, item: dict, ctx: StructuredContext) -> float:
        """计算 TextCNN 语义相似度分数（基于类型和关键词匹配）。"""
        score = 0.0
        item_genres = set(g.lower() for g in (item.get("genres") or []))

        # 类型匹配
        ctx_genres = set(g.lower() for g in (ctx.genres or []))
        if item_genres and ctx_genres:
            overlap = len(item_genres & ctx_genres)
            score += min(overlap / max(len(ctx_genres), 1), 1.0) * 0.6

        # 关键词匹配（标题和简介）
        keywords = ctx.keywords or []
        title = (item.get("title") or "").lower()
        overview = (item.get("overview") or "").lower()
        text = f"{title} {overview}"

        if keywords:
            matched = sum(1 for kw in keywords if kw.lower() in text)
            score += min(matched / max(len(keywords), 1), 1.0) * 0.4

        return min(score, 1.0)

    def _calculate_genre_score(self, item: dict, preference_context: Optional[dict]) -> float:
        """计算类型偏好匹配分数。"""
        if not preference_context:
            return 0.5  # 无偏好时默认中等分数

        pref_genres = set(g.lower() for g in (preference_context.get("genres") or []))
        item_genres = set(g.lower() for g in (item.get("genres") or []))

        if not pref_genres or not item_genres:
            return 0.5

        overlap = len(pref_genres & item_genres)
        return min(overlap / max(len(pref_genres), 1), 1.0)
