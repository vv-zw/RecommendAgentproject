# rag/embedding.py
"""
Embedding 模块：调用外部 Embedding API 将文本转换为向量。
替换原有的自制 TF-IDF 实现。
"""
import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)

# 向量维度（与所选模型一致）
# DeepSeek text-embedding-v2: 1024 维
# OpenAI text-embedding-3-small: 1536 维
# OpenAI text-embedding-3-large: 3072 维
EMBEDDING_DIM = int(os.environ.get("EMBEDDING_DIM", "1536"))


def get_text_embedding(text: str) -> Optional[list]:
    """
    将文本转换为向量。

    Args:
        text: 待向量化的文本

    Returns:
        float 列表（向量），失败时返回 None
    """
    if not text or not text.strip():
        return None

    try:
        from ai_config.llm_client import get_embedding
        return get_embedding(text.strip())
    except Exception as e:
        logger.error(f"Embedding API 调用失败：{e}")
        return None


def build_content_text(title: str, plot: str = "", genres: str = "") -> str:
    """
    将影视的多个字段拼接为用于向量化的文本。
    格式：标题。类型。剧情简介。
    """
    parts = []
    if title:
        parts.append(title.strip())
    if genres:
        # genres 格式为 "科幻/动作/冒险"，转为自然语言
        genre_list = [g.strip() for g in genres.split("/") if g.strip()]
        if genre_list:
            parts.append("类型：" + "、".join(genre_list))
    if plot:
        # 简介截断，避免 token 过多
        parts.append(plot.strip()[:300])
    return "。".join(parts)
