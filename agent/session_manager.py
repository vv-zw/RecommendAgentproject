# agent/session_manager.py
"""
SessionManager：管理多轮对话的 session 历史。
使用内存字典存储，支持滑动窗口和过期清理。
"""
import uuid
import logging
from datetime import datetime, timedelta
from typing import Optional

logger = logging.getLogger(__name__)

# Session 过期时间（分钟）
SESSION_TTL_MINUTES = 30

# 全局 session 存储（进程内单例）
_sessions: dict[str, dict] = {}


class SessionManager:
    """
    管理对话 session 的生命周期。

    存储结构：
    {
        "session_uuid": {
            "history": [{"role": "user"/"assistant", "content": "..."}],
            "last_active": datetime,
            "created_at": datetime
        }
    }
    """

    def get_or_create(self, session_id: Optional[str] = None) -> tuple[str, list]:
        """
        获取已有 session 或创建新 session。

        Args:
            session_id: 客户端传入的 session ID，None 时自动创建

        Returns:
            (session_id, history) 元组
            - session_id: 本次使用的 session ID（新建或已有）
            - history: 该 session 的完整历史消息列表
        """
        self.cleanup_expired()

        if session_id and session_id in _sessions:
            session = _sessions[session_id]
            session["last_active"] = datetime.now()
            logger.debug(f"复用 session: {session_id}，历史消息数: {len(session['history'])}")
            return session_id, session["history"]

        # session_id 不存在（首次创建或已过期），生成新 ID
        new_id = str(uuid.uuid4())
        _sessions[new_id] = {
            "history": [],
            "last_active": datetime.now(),
            "created_at": datetime.now(),
        }
        logger.debug(f"创建新 session: {new_id}")
        return new_id, []

    def append(self, session_id: str, role: str, content: str) -> None:
        """
        向 session 追加一条消息。

        Args:
            session_id: session ID
            role: 消息角色，"user" 或 "assistant"
            content: 消息内容
        """
        if session_id not in _sessions:
            logger.warning(f"session {session_id} 不存在，自动创建")
            self.get_or_create(session_id)

        _sessions[session_id]["history"].append({"role": role, "content": content})
        _sessions[session_id]["last_active"] = datetime.now()

    def get_windowed_history(self, session_id: str, window: int = 10) -> list:
        """
        返回最近 window 轮（最多 window*2 条消息）的历史。
        System Prompt 不计入窗口，由调用方单独处理。

        Args:
            session_id: session ID
            window: 保留的对话轮数，默认 10 轮

        Returns:
            消息列表，格式为 [{"role": "...", "content": "..."}]
        """
        if session_id not in _sessions:
            return []

        history = _sessions[session_id]["history"]
        max_messages = window * 2  # 每轮 = user + assistant 各一条

        if len(history) <= max_messages:
            return list(history)

        # 截取最近的消息，确保从 user 消息开始（保持对话完整性）
        recent = history[-max_messages:]
        # 如果第一条是 assistant，去掉它（保持 user 开头）
        if recent and recent[0]["role"] == "assistant":
            recent = recent[1:]

        return list(recent)

    def cleanup_expired(self) -> None:
        """清理超过 SESSION_TTL_MINUTES 分钟未活动的 session。"""
        now = datetime.now()
        expired = [
            sid for sid, data in _sessions.items()
            if now - data["last_active"] > timedelta(minutes=SESSION_TTL_MINUTES)
        ]
        for sid in expired:
            del _sessions[sid]
            logger.debug(f"清理过期 session: {sid}")

        if expired:
            logger.info(f"清理了 {len(expired)} 个过期 session")

    def get_session_count(self) -> int:
        """返回当前活跃 session 数量（用于监控）。"""
        return len(_sessions)

    def clear_session(self, session_id: str) -> None:
        """手动清除指定 session（用于用户主动清空对话）。"""
        if session_id in _sessions:
            del _sessions[session_id]
            logger.debug(f"手动清除 session: {session_id}")


# 模块级单例，供各模块直接导入使用
session_manager = SessionManager()
