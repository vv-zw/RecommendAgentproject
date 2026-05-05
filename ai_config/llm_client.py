# ai_config/llm_client.py
"""
统一 LLM 客户端封装。
DeepSeek 完全兼容 OpenAI SDK，通过 base_url 切换 Provider。
"""
import os
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# 全局单例，避免重复初始化
_client = None


def get_llm_client():
    """
    获取 LLM 客户端单例（OpenAI SDK，兼容 DeepSeek）。
    首次调用时初始化，后续复用同一实例。
    """
    global _client
    if _client is not None:
        return _client

    try:
        from openai import OpenAI
    except ImportError:
        raise ImportError(
            "openai 包未安装，请运行: pip install openai"
        )

    api_key = os.environ.get("DEEPSEEK_API_KEY", "")
    provider = os.environ.get("LLM_PROVIDER", "deepseek").lower()

    if not api_key:
        logger.warning(
            "DEEPSEEK_API_KEY 未配置，LLM 功能将不可用。"
            "请在 .env 文件中设置 DEEPSEEK_API_KEY=sk-xxx"
        )

    if provider == "deepseek":
        base_url = "https://api.deepseek.com"
    elif provider == "openai":
        base_url = "https://api.openai.com/v1"
    else:
        # 支持自定义兼容端点
        base_url = os.environ.get("LLM_BASE_URL", "https://api.deepseek.com")
        logger.info(f"使用自定义 LLM 端点：{base_url}")

    _client = OpenAI(api_key=api_key or "placeholder", base_url=base_url)
    logger.info(f"LLM 客户端初始化完成，Provider={provider}")
    return _client


def chat_completion(
    messages: list,
    tools: Optional[list] = None,
    temperature: float = 0.7,
    max_tokens: int = 2048,
    stream: bool = False,
):
    """
    统一 LLM 对话调用入口。

    Args:
        messages: OpenAI 格式的消息列表 [{"role": "...", "content": "..."}]
        tools: Function Calling 工具 schema 列表，None 表示不启用工具调用
        temperature: 生成温度，NLU 场景建议 0.1，对话场景建议 0.7
        max_tokens: 最大生成 token 数
        stream: 是否启用流式输出

    Returns:
        OpenAI ChatCompletion 响应对象（stream=True 时返回生成器）

    Raises:
        Exception: API 调用失败时抛出，调用方负责捕获和降级处理
    """
    client = get_llm_client()
    model = os.environ.get("LLM_MODEL", "deepseek-chat")

    kwargs = dict(
        model=model,
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
        stream=stream,
    )

    if tools:
        kwargs["tools"] = tools
        kwargs["tool_choice"] = "auto"

    return client.chat.completions.create(**kwargs)


def get_embedding(text: str) -> list:
    """
    调用 Embedding API 将文本转换为向量。

    Args:
        text: 待向量化的文本

    Returns:
        float 列表，向量维度取决于所选模型

    Raises:
        Exception: API 调用失败时抛出，调用方负责降级处理
    """
    client = get_llm_client()
    model = os.environ.get("EMBEDDING_MODEL", "text-embedding-v2")

    resp = client.embeddings.create(input=text, model=model)
    return resp.data[0].embedding


def reset_client() -> None:
    """重置客户端单例（主要用于测试或切换配置）。"""
    global _client
    _client = None
