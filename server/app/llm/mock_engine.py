"""Mock 引擎：不加载任何模型，按关键词规则生成中文回复，用异步 sleep 模拟打字机流式。

用途：
- 后端/前端联调，整个 SSE 链路先跑通
- 无本地模型/无 API Key 时系统仍然可用
- 作为真实引擎的实现参考
"""
from __future__ import annotations

import asyncio
import random

from app.llm.engine import BaseEngine


# 按关键词匹配的回复模板，完全本地、离线
REPLY_TABLE: list[tuple[list[str], list[str]]] = [
    # 问候
    (["你好", "您好", "hi", "hello", "嗨", "在吗"], [
        "你好呀，我是一个本地训练的 AI 助手，有什么可以帮你的？",
        "嗨！很高兴见到你，今天想聊点什么？",
        "你好，我在的，请说～",
    ]),
    # 身份
    (["你是谁", "你是啥", "自我介绍"], [
        "我是用 68M 参数 Transformer 在 120 万条中文指令数据上训练出来的本地模型，当前版本是通用助手 v1。",
        "我是离线运行的中文聊天机器人，所有计算都在你自己的电脑上完成，不会上传任何数据。",
    ]),
    # 能力
    (["会什么", "能做什么", "功能"], [
        "我目前支持：日常闲聊、简单问答、编程概念解释、学习辅助、润色改写。复杂推理和数学题还不太准，敬请谅解～",
    ]),
    # 时间
    (["几点", "时间", "日期", "今天"], [
        "我没有联网，没法实时知道现在几点，你可以看一下电脑右下角的系统时间哦。",
    ]),
    # 模型技术细节（给验收用）
    (["模型", "训练", "参数", "架构", "词表", "tokenizer"], [
        "我的底座是一个 8 层、hidden_size=768、68M 参数的 Transformer Decoder，词表 6400，使用 ChatML 格式（<|im_start|>/<|im_end|>）拼接对话历史。预训练跑了约 5000 step，之后在 3000 条多轮指令数据上做了全量 SFT。",
    ]),
    # 密码加密（会议验收必问到）
    (["密码", "加密", "登录", "注册", "bcrypt", "hash"], [
        "后端对密码用 bcrypt（cost=12）做加盐哈希存储，数据库里永远只有 `$2b$12$...` 形式的哈希串，没有明文。登录时同样用 bcrypt.checkpw 校验。传输层用 HTTPS 的话，密码在链路上也是加密的。",
    ]),
    # 模型切换（会议验收）
    (["切换模型", "换模型", "多个模型", "本地模型", "远端模型", "LoRA", "lora"], [
        "后端在启动时扫描 server/models/*/model.json，GET /api/models 返回全部可用模型（本地全量 / LoRA / 远端 API 各一种 type）。前端在顶栏下拉框里切换，切换后后续对话自动用新模型，历史消息不会丢。本地模型用 PyTorch 原生 .pth 格式加载（不转 GGUF），同一时间只留一个底座模型在内存里，LoRA 叠加挂载。",
    ]),
    # 技术栈
    (["技术栈", "框架", "前后端", "Vue", "React", "FastAPI"], [
        "前端 Vue3 + Vite + Pinia + Element Plus，后端 FastAPI + SQLAlchemy + SQLite（换 MySQL 只需改 DATABASE_URL），实时流式回复用 SSE。模型引擎抽象成接口，Mock / Local / Remote 三种实现随时可换。",
    ]),
    # 会议纪要相关
    (["会议", "老师", "要求", "验收", "宣讲"], [
        "会议里老师要求：前端 Vue 或 React 二选一、本地模型保留 pt 格式、密码 bcrypt 加密、UI 不能比基础版丑。我按这个规范来的：Vue3 + FastAPI + SQLite + bcrypt + ChatML tokenizer，本地 .pth 直接 torch.load。",
    ]),
]

FALLBACK_POOL = [
    "这个问题我想想……嗯，我目前的能力还比较有限，没法很好地回答，你可以换个方式再问我一次吗？",
    "好问题，不过我还没学到这块知识。你可以试试问我模型架构、训练细节、密码加密这些我已经被教过的内容～",
    "抱歉，我理解得还不够到位。能再具体说说你的场景吗？",
    "这个话题我暂时答不上来，但我可以和你聊聊我的训练过程、参数规模或者系统是怎么实现的！",
]


# 悟空人格（选择 mock/wukong 模型时生效），用于演示"模型切换后人格变化"
WUKONG_TABLE: list[tuple[list[str], list[str]]] = [
    (["你是谁", "自我介绍", "你是啥"], [
        "俺乃齐天大圣孙悟空！曾大闹天宫，如今保唐僧西天取经。施主有何事相问？",
    ]),
    (["你好", "您好", "嗨", "hello", "hi"], [
        "嘿！俺老孙在此，妖魔退散。施主有何吩咐？",
    ]),
    (["去哪", "取经", "西天"], [
        "俺们正在西天取经路上，前方妖魔挡道——且看俺老孙的金箍棒！",
    ]),
]
WUKONG_FALLBACK = [
    "俺老孙火眼金睛也没看懂这问题，施主换一个问法吧！",
    "此事俺老孙还得问问师父，换个别的可好？",
]


class MockEngine(BaseEngine):
    name = "mock"

    async def stream(
        self,
        messages: list[dict],
        *,
        model_id: str | None = None,
        system_prompt: str | None = None,
    ):
        # 取最后一条 user 消息作为匹配依据
        last_user = ""
        for m in reversed(messages):
            if m.get("role") == "user":
                last_user = m.get("content", "")
                break
        last_user = last_user.lower()

        # 关键词匹配
        reply_text = random.choice(FALLBACK_POOL)
        for kws, replies in REPLY_TABLE:
            if any(kw.lower() in last_user for kw in kws):
                reply_text = random.choice(replies)
                break

        # 悟空人格覆盖（mock/wukong）
        if "wukong" in (model_id or ""):
            reply_text = next(
                (random.choice(replies) for kws, replies in WUKONG_TABLE
                 if any(kw.lower() in last_user for kw in kws)),
                random.choice(WUKONG_FALLBACK),
            )

        # 逐字异步产出，每个字间隔 20~60ms，模拟打字机
        for ch in reply_text:
            yield ch
            await asyncio.sleep(random.uniform(0.02, 0.06))
