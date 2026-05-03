# agent/agent_core/response_generator.py


class ResponseGenerator:
    def generate_response(
        self,
        user_id: str,
        intent: str,
        tool_results,
        preference_context: dict | None = None
    ):
        """
        根据意图、工具结果和用户偏好上下文生成自然语言回复。

        Args:
            user_id: 用户 ID
            intent: NLU 解析出的意图
            tool_results: ToolOrchestrator 返回的结果
            preference_context: 用户偏好上下文 {'genres', 'directors', 'actors'}
        """
        nl_response = "抱歉，我暂时无法处理您的请求。"
        structured_results = []

        # 构建偏好描述文本（用于个性化回复）
        pref_desc = self._build_preference_description(preference_context)

        if intent in ("recommend_movie", "recommend_series", "search_movie"):
            if tool_results and isinstance(tool_results, list) and len(tool_results) > 0:
                structured_results = tool_results
                count = len(structured_results)
                content_type_label = "电影" if intent != "recommend_series" else "剧集"

                if pref_desc:
                    nl_response = (
                        f"根据您对{pref_desc}的偏好，为您推荐以下{count}部{content_type_label}，"
                        f"希望符合您的口味："
                    )
                else:
                    nl_response = f"为您推荐以下{count}部{content_type_label}，希望您喜欢："
            else:
                nl_response = "抱歉，暂时没有找到符合条件的推荐内容，请尝试换个描述方式。"

        elif intent == "add_to_watchlist":
            if isinstance(tool_results, dict) and tool_results.get("status") == "success":
                nl_response = "已成功添加到您的待看清单！"
            else:
                reason = tool_results.get("reason", "未知原因") if isinstance(tool_results, dict) else "未知原因"
                nl_response = f"添加到待看清单失败：{reason}，请指定具体的影视内容。"

        else:
            # 默认推荐
            if tool_results and isinstance(tool_results, list):
                structured_results = tool_results
                if pref_desc:
                    nl_response = f"根据您的偏好（{pref_desc}），为您推荐以下内容："
                else:
                    nl_response = "为您推荐以下热门影视内容："
            else:
                nl_response = "您好！我是您的影视推荐助手，可以为您推荐电影或剧集。请告诉我您的喜好！"

        return nl_response, structured_results

    def _build_preference_description(self, preference_context: dict | None) -> str:
        """根据偏好上下文构建简短的偏好描述文本。"""
        if not preference_context:
            return ""

        parts = []
        genres = preference_context.get('genres') or []
        directors = preference_context.get('directors') or []
        actors = preference_context.get('actors') or []

        if genres:
            parts.append('、'.join(genres[:2]) + "类型")
        if directors:
            parts.append(directors[0] + "导演的作品")
        if actors:
            parts.append(actors[0] + "主演的影视")

        return '，'.join(parts) if parts else ""
