"""Conversations CRUD + 消息历史。"""
from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import get_current_user
from app.models.orm import User, Conversation, Message
from app.models.schemas import (
    ConversationOut, CreateConversationIn, PatchConversationIn, MessageOut,
)

router = APIRouter(prefix="/api", tags=["conversations"])


def _get_conv_or_404(conv_id: int, user: User, db: Session) -> Conversation:
    conv = db.get(Conversation, conv_id)
    if not conv or conv.user_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "conversation not found")
    return conv


@router.get("/conversations", response_model=list[ConversationOut])
def list_conversations(current: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return (
        db.query(Conversation)
        .filter(Conversation.user_id == current.id)
        .order_by(Conversation.updated_at.desc())
        .all()
    )


@router.post("/conversations", response_model=ConversationOut, status_code=status.HTTP_201_CREATED)
def create_conversation(
    body: CreateConversationIn,
    current: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    conv = Conversation(
        user_id=current.id,
        title=body.title or "新对话",
        model_id=body.model_id,
    )
    db.add(conv)
    db.commit()
    db.refresh(conv)
    return conv


@router.get("/conversations/{conv_id}", response_model=ConversationOut)
def get_conversation(
    conv_id: int,
    current: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return _get_conv_or_404(conv_id, current, db)


@router.patch("/conversations/{conv_id}", response_model=ConversationOut)
def patch_conversation(
    conv_id: int,
    body: PatchConversationIn,
    current: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    conv = _get_conv_or_404(conv_id, current, db)
    payload = body.model_dump(exclude_unset=True)
    for k, v in payload.items():
        setattr(conv, k, v)
    db.commit()
    db.refresh(conv)
    return conv


@router.delete("/conversations/{conv_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_conversation(
    conv_id: int,
    current: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    conv = _get_conv_or_404(conv_id, current, db)
    db.delete(conv)
    db.commit()
    return None


@router.get("/conversations/{conv_id}/messages", response_model=list[MessageOut])
def list_messages(
    conv_id: int,
    current: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _get_conv_or_404(conv_id, current, db)
    return (
        db.query(Message)
        .filter(Message.conversation_id == conv_id)
        .order_by(Message.created_at.asc())
        .all()
    )
