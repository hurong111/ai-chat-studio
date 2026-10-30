"""远端引擎：调用任意 OpenAI 兼容 API，流式返回。

支持的 provider（在 server/.env 里配置）：
  deepseek  https://api.deepseek.com/v1
  qwen      通义 / 魔塔 API-Inference（https://api-inference.modelscope.cn/v1）
  ollama    本地 Ollama / LM Studio（http://localhost:11434/v1）

model_id 约定（与 registry.py 保持一致）：
  remote/<provider>/<model_name>   例：remote/qwen/Qwen/Qwen2.5-72B-Instruct
"""
from __future__ import annotations

from openai import AsyncOpenAI

from app.core.config import settings
from app.llm.engine import BaseEngine

PROVIDERS = {
    "deepseek": lambda: (settings.remote_deepseek_base_url, settings.remote_deepseek_key,
                         settings.remote_deepseek_model),
    "qwen": lambda: (settings.remote_qwen_base_url, settings.remote_qwen_key,
                     settings.remote_qwen_model),
    "ollama": lambda: (settings.remote_ollama_base_url, "ollama",  # Ollama 不校验 key
                       settings.remote_ollama_model),
}


class RemoteEngine(BaseEngine):
    name = "remote"

    @staticmethod
    def _conf_for(model_id: str) -> tuple[str, str, str]:
        parts = model_id.split("/")
        prov = parts[1] if len(parts) > 1 else ""
        if prov not in PROVIDERS:
            raise RuntimeError(f"未知远端 provider: {prov}")
        base, key, default_model = PROVIDERS[prov]()
        if not key:
            raise RuntimeError(f"{prov} 未配置 API Key，请在 server/.env 填写后重启后端")
        model_name = "/".join(parts[2:]) if len(parts) > 2 and parts[2] else default_model
        return base, key, model_name

    async def stream(self, messages, *, model_id=None, system_prompt=None):
        base, key, model_name = self._conf_for(model_id or "")
        client = AsyncOpenAI(base_url=base, api_key=key, timeout=120)

        msgs = ([{"role": "system", "content": system_prompt}] if system_prompt else []) + list(messages)

        resp = await client.chat.completions.create(
            model=model_name, messages=msgs, stream=True, temperature=0.7,
        )
        async for chunk in resp:
            if chunk.choices and chunk.choices[0].delta and chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content
