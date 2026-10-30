"""按需构造 LLM 引擎实例：按 model_id 路由 + 单例缓存。

路由规则（与前端下拉框的模型 id 对应）：
  mock/xxx   -> MockEngine（离线演示）
  remote/xxx -> RemoteEngine（OpenAI 兼容第三方 API）
  其他        -> LocalEngine（本地 .pth，id 即 models/ 下的目录名）
"""
from __future__ import annotations

from app.core.config import settings
from app.llm.engine import BaseEngine
from app.llm.mock_engine import MockEngine


_engine_cache: dict[str, BaseEngine] = {}


def get_engine(kind: str | None = None) -> BaseEngine:
    """kind: mock | local | remote；留空则读 settings.engine_backend。"""
    key = kind or settings.engine_backend
    if key in _engine_cache:
        return _engine_cache[key]

    if key == "mock":
        eng: BaseEngine = MockEngine()
    elif key == "local":
        from app.llm.local_engine import LocalEngine  # 延迟导入，避免拖慢 mock 启动
        eng = LocalEngine()
    elif key == "remote":
        from app.llm.remote_engine import RemoteEngine
        eng = RemoteEngine()
    else:
        raise ValueError(f"unknown engine backend: {key}")

    _engine_cache[key] = eng
    return eng


def get_engine_for_model(model_id: str | None) -> BaseEngine:
    """聊天接口按前端选择的 model_id 路由到对应引擎。"""
    if not model_id:
        return get_engine()
    if model_id.startswith("remote/"):
        return get_engine("remote")
    if model_id.startswith("mock/"):
        return get_engine("mock")
    return get_engine("local")


async def close_all_engines() -> None:
    for eng in _engine_cache.values():
        await eng.close()
    _engine_cache.clear()
