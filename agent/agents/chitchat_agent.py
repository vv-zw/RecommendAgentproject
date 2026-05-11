# agent/agents/chitchat_agent.py
"""
ChitchatAgent：闲聊 Agent。
处理与影视推荐无关的日常对话，自然回应并在适当时机引导推荐需求。
"""
import logging

logger = logging.getLogger(__name__)

CHITCHAT_SYSTEM_PROMPT = """你是一个友好的影视推荐助手，用简短自然的中文回复用户的闲聊（不超过 150 字）。
如果用户聊到影视相关话题，自然地引导他们提出具体推荐需求。
不要调用任何工具，不要主动推荐具体影视。"""

# LLM 失败时的固定友好提示语
FALLBACK_RESPONSE = "您好！我是影视推荐助手，可以为您推荐电影或剧集。请告诉我您的喜好！"


class ChitchatAgent:
    """闲聊 Agent，处理与影视推荐无关的日常对话。"""

    def chat(self, message: str, history: list = None) -> str:
        """
        处理闲聊消息，返回自然回复。

        Args:
            message: 用户输入的闲聊消息
            history: 对话历史列表（可选）

        Returns:
            闲聊回复字符串，不超过 150 字
        """
        try:
            from ai_config.llm_client import chat_completion

            messages = [{"role": "system", "content": CHITCHAT_SYSTEM_PROMPT}]

            # 注入最近对话历史
            if history:
                for msg in history[-4:]:
                    if isinstance(msg, dict) and msg.get("role") in ("user", "assistant"):
                        messages.append({"role": msg["role"], "content": msg["content"]})

            messages.append({"role": "user", "content": message})

            response = chat_completion(
                messages=messages,
                temperature=0.8,
                max_tokens=256,
            )

            reply = response.choices[0].message.content.strip()

            # 截断超长回复
            if len(reply) > 150:
                reply = reply[:147] + "..."

            return reply

        except Exception as e:
            logger.error(f"ChitchatAgent LLM 调用失败，返回固定提示：{e}")
            return FALLBACK_RESPONSE
