# agent/agent_core/response_generator.py
"""
ResponseGenerator：使用 LLM 生成自然语言回复。
替换原有的模板字符串拼接逻辑。
"""
import json
import logging
import os
from typing import Generator, Optional, Union

import requests as req

logger = logging.getLogger(__name__)

RESPONSE_SYSTEM_PROMPT = """你是一个专业的影视推荐助手，用自然流畅的中文向用户介绍推荐内容。

根据工具返回的推荐结果，生成一段自然的推荐介绍：
- 语言自然亲切，不要像在读列表或背稿子
- 结合用户偏好说明推荐理由（如有偏好信息）
- 每部作品用 1-2 句话介绍核心亮点（类型、导演、评分、剧情特色等）
- 如果推荐结果为空，友好地引导用户换一种描述方式
- 回复长度控制在 300 字以内
- 不要重复列出影视的所有字段，挑最有吸引力的点说"""


class ResponseGenerator:
    """LLM 驱动的自然语言回复生成器。"""

    def generate(
        self,
        messages: list,
        tool_results: list,
        preference_context: Optional[dict] = None,
        stream: bool = False,
    ) -> Union[str, Generator]:
        """
        调用 LLM 生成自然语言回复。

        Args:
            messages: 包含对话历史和工具调用结果的消息列表
            tool_results: 工具返回的推荐结果列表
            preference_context: 用户偏好上下文
            stream: True 时返回 token 生成器（用于 SSE）

        Returns:
            stream=False: 完整回复字符串
            stream=True: token 生成器
        """
        # 构建偏好摘要
        pref_summary = self._build_preference_summary(preference_context)

        # 构建推荐结果摘要（只传关键字段，节省 token）
        results_summary = self._build_results_summary(tool_results)

        # 构建发给 LLM 的消息
        gen_messages = [{"role": "system", "content": RESPONSE_SYSTEM_PROMPT}]

        # 加入最近的对话上下文（最多 4 条，帮助理解上下文）
        for msg in messages[-4:]:
            if isinstance(msg, dict) and msg.get("role") in ("user", "assistant"):
                gen_messages.append({"role": msg["role"], "content": msg["content"]})

        # 加入推荐结果作为上下文
        context_content = f"推荐结果：{results_summary}"
        if pref_summary:
            context_content = f"用户偏好：{pref_summary}\n\n{context_content}"

        gen_messages.append({"role": "user", "content": context_content})

        if stream:
            # 流式模式：用 requests 直接调用，绕过 httpx 在 Windows 下的流式问题
            return self._stream_with_requests(gen_messages)
        else:
            # 普通模式：用 openai SDK
            try:
                from ai_config.llm_client import chat_completion
                response = chat_completion(
                    messages=gen_messages,
                    temperature=0.7,
                    max_tokens=512,
                    stream=False,
                )
                return response.choices[0].message.content.strip()
            except Exception as e:
                logger.error(f"ResponseGenerator LLM 调用失败，降级处理：{e}")
                return self._fallback_response(tool_results, preference_context)

    def _stream_with_requests(self, messages: list) -> Generator:
        """
        用 requests 库直接调用 DeepSeek 流式 API。
        绕过 httpx 在某些 Windows 网络环境下的流式连接问题。
        """
        api_key = os.environ.get("DEEPSEEK_API_KEY", "")
        provider = os.environ.get("LLM_PROVIDER", "deepseek")
        model = os.environ.get("LLM_MODEL", "deepseek-chat")

        # 提前检查 API Key 是否有效，避免在 generator 中才暴露异常
        if not api_key or api_key == "your_api_key_here":
            raise Exception("DEEPSEEK_API_KEY 未配置或无效")

        if provider == "deepseek":
            url = "https://api.deepseek.com/chat/completions"
        else:
            url = "https://api.openai.com/v1/chat/completions"

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": model,
            "messages": messages,
            "temperature": 0.7,
            "max_tokens": 512,
            "stream": True,
        }

        try:
            with req.post(url, headers=headers, json=payload, stream=True, timeout=60) as resp:
                resp.raise_for_status()
                for line in resp.iter_lines():
                    if not line:
                        continue
                    line_str = line.decode("utf-8") if isinstance(line, bytes) else line
                    if line_str.startswith("data:"):
                        data = line_str[5:].strip()
                        if data == "[DONE]":
                            break
                        try:
                            chunk = json.loads(data)
                            content = chunk.get("choices", [{}])[0].get("delta", {}).get("content", "")
                            if content:
                                yield content
                        except json.JSONDecodeError:
                            continue
        except Exception as e:
            logger.error(f"requests 流式调用失败：{e}")
            # 重新抛出异常，让上层捕获并降级
            raise

    def _build_results_summary(self, tool_results: list) -> str:
        """将推荐结果列表转换为简洁的 JSON 摘要（只保留关键字段）。"""
        if not tool_results:
            return "[]（未找到相关内容）"

        summary = []
        for item in tool_results[:8]:  # 最多传 8 条给 LLM
            summary.append({
                "id": item.get("id"),
                "title": item.get("title", ""),
                "year": item.get("year"),
                "genres": item.get("genres", []),
                "vote_average": item.get("vote_average"),
                "director": item.get("director", ""),
                "overview": (item.get("overview") or "")[:100],
            })
        return json.dumps(summary, ensure_ascii=False)

    def _build_preference_summary(self, preference_context: Optional[dict]) -> str:
        """将偏好上下文转换为简短的文字描述。"""
        if not preference_context:
            return ""

        parts = []
        genres = preference_context.get("genres") or []
        directors = preference_context.get("directors") or []
        actors = preference_context.get("actors") or []

        if genres:
            parts.append("、".join(genres[:3]) + "类型")
        if directors:
            parts.append(directors[0] + "导演的作品")
        if actors:
            parts.append(actors[0] + "主演的影视")

        return "，".join(parts) if parts else ""

    def _fallback_response(
        self,
        tool_results: list,
        preference_context: Optional[dict] = None,
    ) -> str:
        """LLM 调用失败时的降级模板回复。"""
        pref_desc = self._build_preference_summary(preference_context)

        if not tool_results:
            return "抱歉，暂时没有找到符合条件的推荐内容，请尝试换个描述方式。"

        count = len(tool_results)
        if pref_desc:
            return f"根据您对{pref_desc}的偏好，为您推荐以下 {count} 部影视，希望符合您的口味："
        return f"为您推荐以下 {count} 部影视，希望您喜欢："
