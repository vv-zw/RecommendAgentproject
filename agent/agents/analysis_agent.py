# agent/agents/analysis_agent.py
"""
AnalysisAgent：需求分析 Agent。
深度理解用户需求，必要时追问，输出 StructuredContext。
"""
import json
import logging

from agent.agents.structured_context import StructuredContext

logger = logging.getLogger(__name__)

ANALYSIS_SYSTEM_PROMPT = """你是影视推荐系统的需求分析模块。分析用户的推荐需求，评估清晰度，必要时生成追问。

严格返回 JSON，格式如下：
{{
  "intent": "recommend_movie",
  "confidence": "high",
  "mood": "轻松解压",
  "genres": ["喜剧", "动画"],
  "keywords": [],
  "directors": [],
  "actors": [],
  "content_type": "movie",
  "context": "用户压力大，需要治愈系内容",
  "clarify_question": ""
}}

confidence 评估规则：
- high：用户明确说明了类型、情绪或具体需求，可以直接推荐
- medium：有部分信息但不够完整
- low：几乎没有有效信息，如仅说"推荐电影"

clarify_question 规则：
- confidence=low 时，生成 1-2 个追问问题，合并为一句话，如"您想看什么类型的？最近心情怎么样？"
- confidence=medium 时，可选择追问最关键的缺失信息
- confidence=high 时，clarify_question 必须为空字符串
{force_no_clarify}

注意：
- genres 使用中文类型名：科幻、动作、喜剧、爱情、悬疑、恐怖、动画、纪录片、剧情、犯罪、惊悚
- mood 描述情绪需求：轻松、感动、刺激、治愈、烧脑、温暖
- context 用一句话描述用户的场景和需求背景
- content_type 取值：movie（电影）、series（剧集）、""（不限）"""


class AnalysisAgent:
    """需求分析 Agent，评估需求清晰度并必要时追问。"""

    def analyze(
        self,
        user_message: str,
        history: list = None,
        clarify_round: int = 0,
    ) -> StructuredContext:
        """
        分析用户需求，返回 StructuredContext。

        Args:
            user_message: 用户输入的自然语言消息
            history: 对话历史列表（可选）
            clarify_round: 当前追问轮次，达到 3 时强制输出

        Returns:
            StructuredContext 对象。
            若 ctx.clarify_question 非空，表示需要向用户追问。
        """
        try:
            from ai_config.llm_client import chat_completion

            # 构造强制不追问指令
            if clarify_round >= 3:
                force_clause = "- 已追问 2 轮以上，clarify_question 必须为空字符串（强制输出结果，不再追问）"
            else:
                force_clause = ""

            system_prompt = ANALYSIS_SYSTEM_PROMPT.format(force_no_clarify=force_clause)

            messages = [{"role": "system", "content": system_prompt}]

            # 注入对话历史
            if history:
                for msg in history[-6:]:
                    if isinstance(msg, dict) and msg.get("role") in ("user", "assistant"):
                        messages.append({"role": msg["role"], "content": msg["content"]})

            messages.append({"role": "user", "content": user_message})

            response = chat_completion(
                messages=messages,
                temperature=0.3,
                max_tokens=512,
            )

            raw = response.choices[0].message.content.strip()
            ctx = self._parse_response(raw, clarify_round)
            logger.info(f"AnalysisAgent 分析完成：confidence={ctx.confidence}, "
                        f"clarify_question={'有' if ctx.clarify_question else '无'}")
            return ctx

        except Exception as e:
            logger.error(f"AnalysisAgent LLM 调用失败，降级处理：{e}")
            return self._fallback_context(user_message, clarify_round)

    def _parse_response(self, raw: str, clarify_round: int) -> StructuredContext:
        """解析 LLM 返回的 JSON 为 StructuredContext。"""
        # 清理 markdown 代码块
        cleaned = raw.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.split("```")[1]
            if cleaned.startswith("json"):
                cleaned = cleaned[4:]
            cleaned = cleaned.strip()

        try:
            data = json.loads(cleaned)
        except json.JSONDecodeError:
            logger.warning(f"AnalysisAgent JSON 解析失败，原始返回：{raw[:200]}")
            return self._fallback_context(raw, clarify_round)

        # 提取字段，使用 get 提供默认值
        return StructuredContext(
            intent=data.get("intent", "recommend_movie"),
            confidence=self._validate_confidence(data.get("confidence", "low")),
            mood=data.get("mood", "") or "",
            genres=data.get("genres") or [],
            keywords=data.get("keywords") or [],
            directors=data.get("directors") or [],
            actors=data.get("actors") or [],
            content_type=data.get("content_type", "") or "",
            context=data.get("context", "") or "",
            skip_preference_injection=False,
            clarify_question=data.get("clarify_question", "") or "",
            clarify_round=clarify_round,
        )

    def _validate_confidence(self, confidence: str) -> str:
        """校验 confidence 值的合法性。"""
        if confidence in ("high", "medium", "low"):
            return confidence
        return "low"

    def _fallback_context(self, user_message: str, clarify_round: int) -> StructuredContext:
        """LLM 调用失败时的降级：用原始输入构造最小化 StructuredContext。"""
        return StructuredContext(
            intent="recommend_movie",
            confidence="low",
            mood="",
            genres=[],
            keywords=[],
            directors=[],
            actors=[],
            content_type="",
            context=user_message[:200] if user_message else "",
            skip_preference_injection=False,
            clarify_question="",  # 降级时不追问，直接进入推荐
            clarify_round=clarify_round,
        )
