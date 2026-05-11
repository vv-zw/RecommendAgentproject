# agent/agents/router_agent.py
"""
RouterAgent：意图路由 Agent。
单次 LLM 调用将用户输入分类为四种意图类型之一。
"""
import logging
import re

logger = logging.getLogger(__name__)

# 合法意图类型
VALID_INTENT_TYPES = {"explicit_query", "vague_recommendation", "mixed", "chitchat"}

ROUTER_SYSTEM_PROMPT = """你是影视推荐系统的意图路由模块。分析用户输入，返回以下四种意图类型之一（严格返回单个词，不含其他文字）：

- explicit_query：用户有明确的查询条件，如指定评分要求（高分、最近热门）、指定类型（喜剧、科幻）、指定片名、询问某片详情
- vague_recommendation：用户没有明确条件，泛泛地想要推荐，如"给我推荐点什么"、"今晚看什么好"
- mixed：用户有部分条件但不够具体，如"推荐一部好看的电影"、"有什么好看的剧"
- chitchat：与影视推荐无关的日常对话

判断规则：
1. 含有"高分"、"最近"、"热门"、"评分"等客观筛选词 → explicit_query
2. 含有具体类型词（喜剧、科幻、悬疑等）且无其他模糊修饰 → explicit_query
3. 含有具体片名或询问某片内容 → explicit_query
4. 完全没有条件的推荐请求 → vague_recommendation
5. 有条件但条件模糊（"好看的"、"不错的"）→ mixed"""


class RouterAgent:
    """意图路由 Agent，将用户输入分类为四种意图类型之一。"""

    def route(self, user_message: str, history: list = None) -> str:
        """
        分析用户输入，返回意图类型。

        Args:
            user_message: 用户输入的自然语言消息
            history: 对话历史列表（可选，辅助判断上下文）

        Returns:
            意图类型字符串：
            - explicit_query：明确查询
            - vague_recommendation：模糊推荐
            - mixed：混合
            - chitchat：闲聊
        """
        try:
            from ai_config.llm_client import chat_completion

            messages = [{"role": "system", "content": ROUTER_SYSTEM_PROMPT}]

            # 注入最近对话历史帮助理解上下文
            if history:
                for msg in history[-4:]:
                    if isinstance(msg, dict) and msg.get("role") in ("user", "assistant"):
                        messages.append({"role": msg["role"], "content": msg["content"]})

            messages.append({"role": "user", "content": user_message})

            response = chat_completion(
                messages=messages,
                temperature=0.2,
                max_tokens=50,
            )

            raw = response.choices[0].message.content.strip()
            intent_type = self._parse_intent(raw)

            if intent_type in VALID_INTENT_TYPES:
                logger.info(f"RouterAgent 意图分类：{intent_type}")
                return intent_type

            logger.warning(f"RouterAgent 返回无效意图类型：{raw}，降级为 vague_recommendation")
            return "vague_recommendation"

        except Exception as e:
            logger.error(f"RouterAgent LLM 调用失败，降级为 vague_recommendation：{e}")
            return "vague_recommendation"

    def _parse_intent(self, raw: str) -> str:
        """从 LLM 返回内容中提取有效的意图类型。"""
        # 去除可能的 markdown 代码块包裹
        cleaned = raw.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.split("\n", 1)[-1].rsplit("```", 1)[0].strip()

        # 尝试直接匹配
        if cleaned in VALID_INTENT_TYPES:
            return cleaned

        # 尝试从文本中提取意图类型词
        for intent_type in VALID_INTENT_TYPES:
            if intent_type in cleaned.lower():
                return intent_type

        return cleaned.lower()
