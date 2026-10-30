"""模型注册中心：扫描本地 models/ 目录 + 远端 providers，返回统一的模型列表。

以后想加本地模型，只要在 models/<model_id>/model.json 里放一份配置就行，
GET /api/models 会自动扫到，前端下拉框会自动出现，不用改任何代码。
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from app.core.config import settings
from app.models.schemas import ModelOut


def _weights_exists(model_dir: Path, conf: dict) -> bool:
    """检查权重文件是否存在（支持绝对路径或相对模型目录的路径）。"""
    for key in ("weights", "lora_weights"):
        p = conf.get(key)
        if not p:
            continue
        pp = Path(p)
        if (pp if pp.is_absolute() else model_dir / pp).exists():
            return True
    return False


def _scan_local_models() -> list[ModelOut]:
    base = Path(settings.local_model_dir)
    if not base.exists():
        return []
    out: list[ModelOut] = []
    for conf_path in sorted(base.glob("*/model.json")):
        try:
            conf = json.loads(conf_path.read_text(encoding="utf-8"))
        except Exception:
            continue
        mid = conf.get("id") or conf_path.parent.name
        out.append(
            ModelOut(
                id=mid,
                name=conf.get("name", mid),
                provider="local",
                kind=conf.get("kind", "full_sft"),
                description=conf.get("description"),
                is_available=_weights_exists(conf_path.parent, conf),
            )
        )
    return out


def _scan_remote_models() -> list[ModelOut]:
    out: list[ModelOut] = []
    for prov in settings.remote_provider_list:
        if prov == "deepseek":
            if settings.remote_deepseek_key:
                out.append(ModelOut(
                    id=f"remote/deepseek/{settings.remote_deepseek_model}",
                    name=f"远端·DeepSeek ({settings.remote_deepseek_model})",
                    provider="deepseek", kind="remote",
                    description="OpenAI 兼容 API，需要 API Key", is_available=True,
                ))
            else:
                out.append(ModelOut(
                    id=f"remote/deepseek/{settings.remote_deepseek_model}",
                    name=f"远端·DeepSeek ({settings.remote_deepseek_model}) [未配置]",
                    provider="deepseek", kind="remote",
                    description="未填 REMOTE_DEEPSEEK_KEY，改 .env 后生效", is_available=False,
                ))
        elif prov == "qwen":
            if settings.remote_qwen_key:
                out.append(ModelOut(
                    id=f"remote/qwen/{settings.remote_qwen_model}",
                    name=f"远端·通义千问 ({settings.remote_qwen_model})",
                    provider="qwen", kind="remote", is_available=True,
                ))
            else:
                out.append(ModelOut(
                    id=f"remote/qwen/{settings.remote_qwen_model}",
                    name=f"远端·通义千问 ({settings.remote_qwen_model}) [未配置]",
                    provider="qwen", kind="remote", is_available=False,
                ))
        elif prov == "ollama":
            out.append(ModelOut(
                id=f"remote/ollama/{settings.remote_ollama_model}",
                name=f"本地 Ollama ({settings.remote_ollama_model})",
                provider="ollama", kind="remote",
                description=f"默认端点 {settings.remote_ollama_base_url}，启动 Ollama 后自动可用",
                is_available=True,
            ))
    return out


def _builtin_mock_models() -> list[ModelOut]:
    """当 ENGINE_BACKEND=mock 时，至少给前端两个可选模型，演示模型切换。"""
    return [
        ModelOut(
            id="mock/general", name="Mock·通用助手（离线演示）",
            provider="mock", kind="full_sft",
            description="不依赖任何模型文件，按关键词匹配回复，用于前后端联调。",
            is_available=True,
        ),
        ModelOut(
            id="mock/wukong", name="Mock·悟空人格（离线演示）",
            provider="mock", kind="lora",
            description="LoRA 挂载到通用底座的人格化角色（Mock 实现，等真实 LoRA 就位后替换）。",
            is_available=True,
        ),
    ]


def list_all_models() -> list[ModelOut]:
    """供 GET /api/models 直接调用。"""
    local = _scan_local_models()
    remote = _scan_remote_models()
    out = local + remote
    # 只有在本机和远端都不可用时，才退回离线 Mock，避免演示时下拉框里混入假模型
    if not any(m.is_available for m in out):
        out.extend(_builtin_mock_models())
    return out


DEFAULT_SYSTEM_PROMPT = "你是一个有帮助、准确、友好的中文 AI 助手。回答要简洁明了，不确定的内容请直说不确定。"


def get_model_system_prompt(model_id: str | None) -> str | None:
    """按模型返回 system prompt。

    本地模型默认不加 system（与训练数据保持一致，尤其 LoRA 人格不能被通用提示词覆盖）；
    model.json 里写了 system_prompt 才使用。远端模型使用通用系统提示。
    """
    if not model_id or model_id.startswith(("remote/", "mock/")):
        return DEFAULT_SYSTEM_PROMPT
    mid = model_id.removeprefix("local/").split("/")[0]
    conf_path = Path(settings.local_model_dir) / mid / "model.json"
    try:
        conf = json.loads(conf_path.read_text(encoding="utf-8"))
    except Exception:
        return None
    sp = conf.get("system_prompt")
    return sp or None
