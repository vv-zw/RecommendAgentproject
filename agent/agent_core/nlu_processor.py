# agent/agent_core/nlu_processor.py
"""
NLUProcessor：使用 LLM 理解中文用户输入，提取意图和实体。
替换原有的英文关键词匹配逻辑。
"""
import json
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# NLU System Prompt：要求 LLM 严格返回 JSON，不含任何其他文字
NLU_SYSTEM_PROMPT = """你是一个影视推荐系统的意图理解模块。请分析用户输入，提取意图和实体，以 JSON 格式返回。

支持的意图类型：
- recommend_movie: 用户想要推荐电影
- recommend_series: 用户想要推荐剧集/电视剧/综艺
- search_content: 用户在搜索特定影视内容（知道具体名字）
- add_to_watchlist: 用户想把某部影视加入待看清单
- get_detail: 用户想了解某部影视的详细信息
- chitchat: 闲聊，与影视推荐无关

返回格式（严格 JSON，不要有任何其他文字，不要有 markdown 代码块）：
{
  "intent": "recommend_movie",
  "entities": {
    "genres": ["科幻"],
    "directors": [],
    "actors": [],
    "keywords": ["太空探索"],
    "mood": "刺激紧张",
    "content_title": ""
  }
}

注意：
1. genres 使用中文类型名，如科幻、动作、喜剧、爱情、悬疑、恐怖、动画、纪录片、剧情、犯罪、惊悚
2. mood 描述用户的情绪需求，如轻松、感动、刺激、治愈、烧脑、温暖，没有则留空字符串
3. content_title 仅在用户提到具体影视名称时填写，否则留空字符串
4. keywords 提取用户描述中的关键主题词，如"父女情"、"复仇"、"末日"等
5. 若用户说"换几部"、"再推荐几个"等，意图与上一轮相同，请根据上下文判断"""

# 默认降级返回值
_DEFAULT_RESULT = {
    "intent": "unknown",
    "entities": {
        "genres": [],
        "directors": [],
        "actors": [],
        "keywords": [],
        "mood": "",
        "content_title": "",
    },
}


class NLUProcessor:
    """LLM 驱动的中文意图理解处理器。"""

    def process(
        self,
        text: str,
        history: Optional[list] = None,
    ) -> tuple[str, dict]:
        """
        将用户输入解析为结构化意图和实体。

        Args:
            text: 用户输入的自然语言文本（支持中文）
            history: 可选的对话历史，用于上下文理解（多轮对话场景）

        Returns:
            (intent, entities) 元组
            - intent: str，如 recommend_movie / recommend_series / search_content 等
            - entities: dict，包含 genres/directors/actors/keywords/mood/content_title
        """
        try:
            from ai_config.llm_client import chat_completion
        except ImportError as e:
            logger.error(f"LLM 客户端导入失败：{e}")
            return _DEFAULT_RESULT["intent"], _DEFAULT_RESULT["entities"].copy()

        # 构建消息列表：system prompt + 可选历史 + 当前用户输入
        messages = [{"role": "system", "content": NLU_SYSTEM_PROMPT}]

        # 注入最近 3 轮历史（避免 token 过多），帮助理解"换几部"等上下文依赖表达
        if history:
            for msg in history[-6:]:  # 最多 3 轮 = 6 条消息
                if msg.get("role") in ("user", "assistant"):
                    messages.append({"role": msg["role"], "content": msg["content"]})

        messages.append({"role": "user", "content": text})

        try:
            response = chat_completion(
                messages=messages,
                temperature=0.1,   # 低温度确保 JSON 输出稳定
                max_tokens=256,    # NLU 输出很短，不需要太多 token
            )
            raw = response.choices[0].message.content.strip()

            # 清理可能的 markdown 代码块包裹
            if raw.startswith("```"):
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]
                raw = raw.strip()

            parsed = json.loads(raw)
            intent = parsed.get("intent", "unknown")
            entities = parsed.get("entities", {})

            # 字段校验：缺失字段补充默认值
            entities.setdefault("genres", [])
            entities.setdefault("directors", [])
            entities.setdefault("actors", [])
            entities.setdefault("keywords", [])
            entities.setdefault("mood", "")
            entities.setdefault("content_title", "")

            # 确保列表类型字段不是 None
            for list_field in ("genres", "directors", "actors", "keywords"):
                if not isinstance(entities[list_field], list):
                    entities[list_field] = []

            logger.debug(f"NLU 解析结果：intent={intent}, entities={entities}")
            return intent, entities

        except json.JSONDecodeError as e:
            logger.warning(f"NLU LLM 返回 JSON 格式不合法，降级处理：{e}，原始内容：{raw!r}")
            return "unknown", _DEFAULT_RESULT["entities"].copy()

        except Exception as e:
            logger.error(f"NLU LLM 调用失败，降级处理：{e}")
            return "unknown", _DEFAULT_RESULT["entities"].copy()
