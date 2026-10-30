"""SSE 流式聊天：前端 POST /api/chat/stream 接收打字机回复。

完整流程：
1. 找到/创建 conversation，保存 user 消息到数据库
2. 读取历史 messages（去掉最后一条 user，再加上本次 user）传给引擎
3. 边从引擎拿 token 边 yield SSE 帧，同时把 assistant 回复累积写回数据库
4. 最后 yield [DONE]
"""
from __future__ import annotations

import json
from datetime import datetime
from typing import AsyncGenerator

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sse_starlette.sse import EventSourceResponse

from app.core.db import get_db
from app.core.deps import get_current_user
from app.models.orm import User, Conversation, Message
from app.models.schemas import ChatStreamIn
from app.llm.factory import get_engine_for_model
from app.llm.registry import get_model_system_prompt

router = APIRouter(prefix="/api/chat", tags=["chat"])


def _get_or_create_conv(
    conv_id: int | None,
    user: User,
    model_id: str | None,
    db: Session,
) -> Conversation:
    if conv_id is not None:
        conv = db.get(Conversation, conv_id)
        if not conv or conv.user_id != user.id:
            raise HTTPException(404, "conversation not found")
        # 允许中途切模型
        if model_id and conv.model_id != model_id:
            conv.model_id = model_id
            db.commit()
        conv.updated_at = datetime.utcnow()
        return conv

    conv = Conversation(
        user_id=user.id,
        title="新对话",
        model_id=model_id,
    )
    db.add(conv)
    db.commit()
    db.refresh(conv)
    return conv


def _build_history_messages(conv: Conversation, db: Session) -> list[dict]:
    msgs = (
        db.query(Message)
        .filter(Message.conversation_id == conv.id)
        .order_by(Message.created_at.asc())
        .all()
    )
    return [{"role": m.role, "content": m.content} for m in msgs]


@router.post("/stream")
async def chat_stream(
    body: ChatStreamIn,
    current: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # 1. 找到/创建 conversation
    conv = _get_or_create_conv(body.conversation_id, current, body.model_id, db)

    # 2. 保存 user 消息
    user_msg = Message(
        conversation_id=conv.id,
        role="user",
        content=body.message,
        model_id=body.model_id or conv.model_id,
    )
    db.add(user_msg)
    db.commit()
    db.refresh(user_msg)

    # 3. 取历史 + 本次 user
    history = _build_history_messages(conv, db)

    # 4. 调用引擎流式生成
    engine = get_engine_for_model(body.model_id or conv.model_id)  # 按 model_id 路由引擎

    async def gen() -> AsyncGenerator[str, None]:
        full_reply: list[str] = []
        try:
            async for piece in engine.stream(
                history,
                model_id=body.model_id or conv.model_id,
                system_prompt=get_model_system_prompt(body.model_id or conv.model_id),
            ):
                full_reply.append(piece)
                yield json.dumps({"delta": piece, "conv_id": conv.id}, ensure_ascii=False)
        except Exception as exc:
            # 引擎异常也把已生成内容存下来，再 yield 错误帧
            err_msg = f"\n\n[引擎错误：{exc!s}]"
            full_reply.append(err_msg)
            yield json.dumps({"delta": err_msg, "error": str(exc)}, ensure_ascii=False)
        finally:
            # 5. 落库 assistant 消息
            reply_text = "".join(full_reply).strip()
            if reply_text:
                assistant_msg = Message(
                    conversation_id=conv.id,
                    role="assistant",
                    content=reply_text,
                    model_id=body.model_id or conv.model_id,
                )
                db.add(assistant_msg)
                # 自动用首句作为对话标题（如果还是默认的"新对话"）
                if conv.title == "新对话":
                    first = body.message.strip().replace("\n", " ")[:20]
                    conv.title = first or "新对话"
                conv.updated_at = datetime.utcnow()
                db.commit()
                yield json.dumps({
                    "done": True,
                    "conv_id": conv.id,
                    "assistant_msg_id": assistant_msg.id,
                    "title": conv.title,
                }, ensure_ascii=False)

    return EventSourceResponse(gen(), media_type="text/event-stream")
