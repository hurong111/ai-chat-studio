"""本地引擎：加载自己训练的 .pth 权重（全量SFT / LoRA），CPU/GPU 自适应。

模型注册方式：在 server/models/<model_id>/model.json 里放一份配置即可，
后端启动后 GET /api/models 自动扫到，前端下拉框自动出现。

model.json 字段说明：
  id / name / description        展示用
  kind                           full_sft | lora
  weights                        底座权重路径（绝对路径或相对模型目录）
  lora_weights / lora_rank       LoRA 权重路径与秩（kind=lora 时）
  base_model_id                  LoRA 底座对应的模型目录名（kind=lora 时）
  tokenizer                      tokenizer 目录（pretrain_project/modelT）
  project_root                   pretrain_project 根目录（用于 import model.model_my）
  hidden_size / num_hidden_layers / vocab_size
  eos_token_id                   建议 6（<|im_end|>）
  max_new_tokens / temperature / top_p / repetition_penalty
"""
from __future__ import annotations

import asyncio
import json
import os
import sys
from pathlib import Path
from threading import Thread

from app.core.config import settings
from app.llm.engine import BaseEngine


class LocalEngine(BaseEngine):
    name = "local"
    _cache: dict[str, dict] = {}

    # ---------- 加载 ----------
    def _model_dir(self, model_id: str) -> Path:
        mid = model_id.removeprefix("local/").split("/")[0]
        return Path(settings.local_model_dir) / mid

    @staticmethod
    def _resolve(model_dir: Path, p: str) -> Path:
        pp = Path(p)
        return pp if pp.is_absolute() else model_dir / pp

    def _load(self, model_id: str) -> dict:
        if model_id in self._cache:
            return self._cache[model_id]

        import torch  # 延迟导入：mock 模式启动不受影响

        d = self._model_dir(model_id)
        conf = json.loads((d / "model.json").read_text(encoding="utf-8"))

        # 让后端进程能 import 训练工程里的 model.model_my
        project_root = str(Path(conf["project_root"]).resolve())
        if project_root not in sys.path:
            sys.path.insert(0, project_root)
        from model.model_my import TransformerConfig, GPTForCausalLM

        from transformers import AutoTokenizer
        tok = AutoTokenizer.from_pretrained(conf["tokenizer"])

        cfg = TransformerConfig(
            hidden_size=conf.get("hidden_size", 768),
            num_hidden_layers=conf.get("num_hidden_layers", 8),
            vocab_size=conf.get("vocab_size", 6400),
        )
        model = GPTForCausalLM(cfg)

        kind = conf.get("kind", "full_sft")
        sd_path = self._resolve(d, conf["lora_weights"] if kind == "lora" else conf["weights"])
        sd = torch.load(sd_path, map_location="cpu")

        if kind == "lora":
            from model.model_lora import apply_lora, load_lora

            rank = conf.get("lora_rank", 8)
            base_id = conf.get("base_model_id")
            if base_id:
                # 推荐用法：底座（全量SFT）+ LoRA 增量。
                # 即使 LoRA 文件里携带了底座权重，也只取其中的 lora.* 键，
                # 保证人格是「在全量SFT 底座上叠加」而不是另一份预训练底座。
                base_dir = Path(settings.local_model_dir) / base_id
                base_conf = json.loads((base_dir / "model.json").read_text(encoding="utf-8"))
                base_sd = torch.load(self._resolve(base_dir, base_conf["weights"]), map_location="cpu")
                model.load_state_dict(base_sd, strict=True)
                apply_lora(model, rank=rank)
                load_lora(model, str(sd_path))
            elif "model.embed_tokens.weight" in sd:
                # 未指定底座，但文件里自带完整权重：挂载 LoRA 结构后整体严格加载
                apply_lora(model, rank=rank)
                model.load_state_dict(sd, strict=True)
            else:
                raise RuntimeError("LoRA 模型缺少 base_model_id，且权重文件不含底座权重")
        else:
            model.load_state_dict(sd, strict=True)

        model.eval()
        device = "cuda" if torch.cuda.is_available() else "cpu"
        if device == "cpu":
            # CPU 推理吃满全部核心，68M 小模型可提速 2~3 倍
            torch.set_num_threads(max(1, os.cpu_count() or 4))
        model.to(device)
        entry = {"model": model, "tok": tok, "conf": conf, "device": device}
        self._cache[model_id] = entry
        print(f"[LocalEngine] 已加载 {model_id} ({kind}) -> {device}")
        return entry

    # ---------- 生成 ----------
    async def stream(self, messages, *, model_id=None, system_prompt=None):
        if not model_id:
            raise RuntimeError("本地引擎必须指定 model_id")
        entry = await asyncio.to_thread(self._load, model_id)
        model, tok, conf, device = entry["model"], entry["tok"], entry["conf"], entry["device"]

        # 与训练时完全一致的 ChatML 拼接
        prompt = ""
        if system_prompt:
            prompt += f"<|im_start|>system\n{system_prompt}<|im_end|>\n"
        for m in messages[-8:]:  # 最多带最近 8 条，防止 CPU 上太慢
            if m.get("role") not in ("system", "user", "assistant"):
                continue
            prompt += f"<|im_start|>{m['role']}\n{m.get('content', '')}<|im_end|>\n"
        prompt += "<|im_start|>assistant\n"

        def _start():
            """在子线程里启动 generate，用 TextIteratorStreamer 边生成边吐字。"""
            import torch
            from transformers import TextIteratorStreamer
            ids = tok(prompt, return_tensors="pt", add_special_tokens=False).input_ids.to(device)
            streamer = TextIteratorStreamer(tok, skip_prompt=True, skip_special_tokens=True)
            kw = dict(
                input_ids=ids,
                streamer=streamer,
                max_new_tokens=conf.get("max_new_tokens", 128),
                do_sample=True,
                temperature=conf.get("temperature", 0.6),
                top_p=conf.get("top_p", 0.9),
                top_k=conf.get("top_k", 30),
                repetition_penalty=conf.get("repetition_penalty", 1.25),
                eos_token_id=conf.get("eos_token_id", 6),  # <|im_end|>
                pad_token_id=0,
            )

            def _run():
                import torch as _t
                with _t.inference_mode():
                    model.generate(**kw)

            th = Thread(target=_run, daemon=True)
            th.start()
            return streamer, th

        streamer, _th = await asyncio.to_thread(_start)

        # 把子线程产出的文本块桥接到异步队列，前端 SSE 立刻收到第一个字
        loop = asyncio.get_running_loop()
        q: asyncio.Queue = asyncio.Queue()

        def _pump():
            try:
                for piece in streamer:
                    loop.call_soon_threadsafe(q.put_nowait, piece)
            finally:
                loop.call_soon_threadsafe(q.put_nowait, None)

        # 注意：不能 await，否则等整段生成完才开始往下发，等于没流式
        asyncio.ensure_future(asyncio.to_thread(_pump))

        while True:
            piece = await q.get()
            if piece is None:
                break
            # 防御：个别 tokenizer 会把 <|im_end|> 文本吐出来，截掉
            piece = piece.replace("<|im_end|>", "")
            if not piece:
                continue
            yield piece
