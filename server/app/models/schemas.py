"""Pydantic Schema —— 入参/出参。"""
from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, EmailStr, Field


# ---------- Auth ----------
class RegisterIn(BaseModel):
    username: str = Field(min_length=3, max_length=32, pattern=r"^[A-Za-z0-9_]+$")
    password: str = Field(min_length=6, max_length=64)
    nickname: Optional[str] = None
    email: Optional[EmailStr] = None


class LoginIn(BaseModel):
    username: str
    password: str


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserOut(BaseModel):
    id: int
    username: str
    nickname: Optional[str] = None
    email: Optional[str] = None
    avatar: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class UpdateProfileIn(BaseModel):
    nickname: Optional[str] = Field(default=None, max_length=64)
    email: Optional[EmailStr] = None
    avatar: Optional[str] = Field(default=None, max_length=512)


class ChangePasswordIn(BaseModel):
    old_password: str
    new_password: str = Field(min_length=6, max_length=64)


# ---------- Conversation ----------
class ConversationOut(BaseModel):
    id: int
    title: str
    model_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class CreateConversationIn(BaseModel):
    title: Optional[str] = "新对话"
    model_id: Optional[str] = None


class PatchConversationIn(BaseModel):
    title: Optional[str] = None
    model_id: Optional[str] = None


# ---------- Message ----------
class MessageOut(BaseModel):
    id: int
    role: Literal["system", "user", "assistant"]
    content: str
    model_id: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


# ---------- Chat ----------
class ChatStreamIn(BaseModel):
    conversation_id: Optional[int] = None  # 为空则创建新对话
    model_id: Optional[str] = None
    message: str = Field(min_length=1, max_length=10000)


# ---------- Model List ----------
class ModelOut(BaseModel):
    id: str
    name: str
    provider: str  # mock | local | remote | ollama
    kind: Literal["full_sft", "lora", "pretrain", "remote"]
    description: Optional[str] = None
    is_available: bool = True
