# agent/agents/explanation_agent.py
"""
ExplanationAgent：解释 Agent。
包装现有 ExplanationGenerator，结合 StructuredContext 的 mood 和 context 字段
生成更贴合用户需求的个性化推荐理由。
"""
import json
import logging
from typing import Optional

from agent.agents.structured_context import StructuredContext

logger = logging.getLogger(__name__)

EXPLANATION_SYSTEM_PROMPT = """请为以下影视推荐生成个性化推荐理由（每条 1-2 句，20-50 字）。

用户当前需求背景：{context}
用户情绪状态：{mood}

要求：
- 若 mood 非空，推荐理由中体现情绪契合度，如"适合今晚放松心情"
- 若 context 非空，结合场景信息，如"适合和家人一起观看"
- 优先突出与用户需求最相关的影视特征（类型、导演、评分、剧情主题等）
- 语言自然亲切，不要像广告词

返回 JSON 数组：[{{"id": 1, "explanation": "..."}}, ...]
不要有任何其他文字"""


class ExplanationAgent:
    """解释 Agent，为推荐结果生成上下文感知的个性化推荐理由。"""

    def __init__(self):
        from explain.explanation_generator import explanation_generator
        self._generator = explanation_generator

    def explain(
        self,
        results: list[dict],
        ctx: StructuredContext,
    ) -> list[dict]:
        """
        为每条推荐结果添加 explanation 字段。

        Args:
            results: 推荐结果列表（content_items 格式）
            ctx: StructuredContext，包含 mood 和 context 信息

        Returns:
            每条记录追加了 explanation 字段的列表
        """
        if not results:
            return results

        # 先用模板填充默认值，确保每条都有 explanation
        output = [dict(item) for item in results]
        for item in output:
            item["explanation"] = self._generator._template_explanation(item, None)

        # 尝试用 LLM 生成更好的理由（最多处理前 8 条）
        items_to_explain = output[:8]
        try:
            llm_explanations = self._llm_generate(items_to_explain, ctx)
            if llm_explanations:
                exp_map = {
                    e["id"]: e["explanation"]
                    for e in llm_explanations
                    if "id" in e and "explanation" in e
                }
                for item in output:
                    if item.get("id") in exp_map:
                        item["explanation"] = exp_map[item["id"]]
        except Exception as e:
            logger.warning(f"ExplanationAgent LLM 调用失败，使用模板降级：{e}")

        return output

    def _llm_generate(
        self,
        items: list[dict],
        ctx: StructuredContext,
    ) -> list[dict]:
        """调用 LLM 批量生成上下文感知的推荐理由。"""
        from ai_config.llm_client import chat_completion

        # 构建影视摘要（只传关键字段）
        items_summary = []
        for item in items:
            items_summary.append({
                "id": item.get("id"),
                "title": item.get("title", ""),
                "genres": item.get("genres", []),
                "vote_average": item.get("vote_average"),
                "director": item.get("director", ""),
                "overview": (item.get("overview") or "")[:80],
            })

        mood = ctx.mood if ctx.mood else "无特殊情绪偏好"
        context = ctx.context if ctx.context else "无特殊场景"

        system_prompt = EXPLANATION_SYSTEM_PROMPT.format(
            mood=mood,
            context=context,
        )

        user_content = f"影视列表：{json.dumps(items_summary, ensure_ascii=False)}"

        response = chat_completion(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content},
            ],
            temperature=0.5,
            max_tokens=512,
        )

        raw = response.choices[0].message.content.strip()

        # 清理 markdown 代码块
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
            raw = raw.strip()

        return json.loads(raw)
