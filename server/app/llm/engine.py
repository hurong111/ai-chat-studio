"""LLM 引擎抽象。所有引擎都实现 stream() 生成器，上层统一走 SSE。"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import AsyncGenerator


class BaseEngine(ABC):
    """所有引擎的统一接口。"""

    name: str = "base"

    @abstractmethod
    async def stream(
        self,
        messages: list[dict],  # [{role, content}]
        *,
        model_id: str | None = None,
        system_prompt: str | None = None,
    ) -> AsyncGenerator[str, None]:
        """流式产出回复片段（不含特殊 token）。"""
        ...

    async def close(self) -> None:
        """释放资源（本地模型卸载、HTTP 会话关闭）。"""
        return None


# ---------- 简单工具函数 ----------
def build_messages_with_system(
    history: list[dict],
    system_prompt: str | None = None,
) -> list[dict]:
    """把 system prompt 插到消息最前面（若已有 system 则不重复加）。"""
    msgs = list(history)
    if system_prompt and not any(m.get("role") == "system" for m in msgs):
        msgs.insert(0, {"role": "system", "content": system_prompt})
    return msgs
