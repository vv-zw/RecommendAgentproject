# explain/explanation_generator.py
"""
ExplanationGenerator：为推荐结果生成个性化推荐理由。
使用 LLM 生成，失败时降级为模板字符串。
"""
import json
import logging
from typing import Optional

logger = logging.getLogger(__name__)

EXPLANATION_SYSTEM_PROMPT = """你是一个影视推荐助手，请为以下推荐结果生成简短的个性化推荐理由。

要求：
- 每条理由 1-2 句话，20-40 字
- 结合用户偏好说明为什么推荐这部（如有偏好信息）
- 突出影视的核心亮点（类型特色、导演、评分、剧情特点等）
- 语言自然亲切，不要像广告词
- 严格返回 JSON 数组，格式：[{"id": 1, "explanation": "..."}, ...]
- 不要有任何其他文字"""


class ExplanationGenerator:
    """LLM 驱动的推荐理由生成器。"""

    def generate_explanations(
        self,
        recommendations: list[dict],
        preference_context: Optional[dict] = None,
    ) -> list[dict]:
        """
        为推荐结果列表中的每条记录添加 explanation 字段。

        Args:
            recommendations: 推荐结果列表（content_items 格式）
            preference_context: 用户偏好上下文

        Returns:
            每条记录追加了 explanation 字段的列表
        """
        if not recommendations:
            return recommendations

        # 先用模板填充默认值，确保每条都有 explanation
        results = [dict(item) for item in recommendations]
        for item in results:
            item["explanation"] = self._template_explanation(item, preference_context)

        # 尝试用 LLM 生成更好的理由（最多处理前 8 条，节省 token）
        items_to_explain = results[:8]
        try:
            llm_explanations = self._llm_generate(items_to_explain, preference_context)
            if llm_explanations:
                # 按 id 更新 explanation
                exp_map = {e["id"]: e["explanation"] for e in llm_explanations if "id" in e and "explanation" in e}
                for item in results:
                    if item.get("id") in exp_map:
                        item["explanation"] = exp_map[item["id"]]
        except Exception as e:
            logger.warning(f"LLM 推荐理由生成失败，使用模板降级：{e}")

        return results

    def _llm_generate(
        self,
        items: list[dict],
        preference_context: Optional[dict],
    ) -> list[dict]:
        """调用 LLM 批量生成推荐理由。"""
        from ai_config.llm_client import chat_completion

        # 构建偏好摘要
        pref_summary = self._build_preference_summary(preference_context)

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

        user_content = f"影视列表：{json.dumps(items_summary, ensure_ascii=False)}"
        if pref_summary:
            user_content = f"用户偏好：{pref_summary}\n\n{user_content}"

        response = chat_completion(
            messages=[
                {"role": "system", "content": EXPLANATION_SYSTEM_PROMPT},
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

    def _template_explanation(self, item: dict, preference_context: Optional[dict]) -> str:
        """模板降级：根据影视信息生成简单推荐理由。"""
        title = item.get("title", "")
        genres = item.get("genres") or []
        vote = item.get("vote_average", 0)
        director = item.get("director", "")

        # 检查是否匹配用户偏好
        if preference_context:
            pref_genres = set(g.lower() for g in (preference_context.get("genres") or []))
            item_genres = set(g.lower() for g in genres)
            if item_genres & pref_genres:
                matched = list(item_genres & pref_genres)[0]
                return f"符合您对{matched}类型的偏好，豆瓣评分 {vote:.1f}"

        # 通用模板
        genre_str = "、".join(genres[:2]) if genres else "影视"
        if vote >= 8.0:
            return f"豆瓣高分{genre_str}，评分 {vote:.1f}，口碑极佳"
        elif vote >= 7.0:
            return f"口碑不错的{genre_str}，评分 {vote:.1f}，值得一看"
        elif director:
            return f"{director}执导的{genre_str}作品"
        else:
            return f"为您推荐的{genre_str}内容"

    def _build_preference_summary(self, preference_context: Optional[dict]) -> str:
        """将偏好上下文转换为简短描述。"""
        if not preference_context:
            return ""
        parts = []
        genres = preference_context.get("genres") or []
        directors = preference_context.get("directors") or []
        actors = preference_context.get("actors") or []
        if genres:
            parts.append("、".join(genres[:2]) + "类型")
        if directors:
            parts.append(directors[0] + "导演")
        if actors:
            parts.append(actors[0] + "主演")
        return "，".join(parts)


# 模块级单例
explanation_generator = ExplanationGenerator()
