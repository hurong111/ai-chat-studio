"""Auth 相关：注册、登录、当前用户、改信息、改密码。"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import get_current_user
from app.core.security import hash_password, verify_password, create_access_token
from app.models.orm import User
from app.models.schemas import (
    RegisterIn, LoginIn, TokenOut, UserOut, UpdateProfileIn, ChangePasswordIn,
)

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def register(body: RegisterIn, db: Session = Depends(get_db)):
    if db.query(User).filter(User.username == body.username).first():
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "username already taken")
    u = User(
        username=body.username,
        password_hash=hash_password(body.password),
        nickname=body.nickname or body.username,
        email=body.email,
    )
    db.add(u)
    db.commit()
    db.refresh(u)
    return u


@router.post("/login", response_model=TokenOut)
def login(body: LoginIn, db: Session = Depends(get_db)):
    u = db.query(User).filter(User.username == body.username).first()
    if not u or not verify_password(body.password, u.password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "username or password wrong")
    return TokenOut(access_token=create_access_token(u.id))


@router.get("/me", response_model=UserOut)
def me(current: User = Depends(get_current_user)):
    return current


@router.put("/me", response_model=UserOut)
def update_profile(
    body: UpdateProfileIn,
    current: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # 只更新非 None 字段
    payload = body.model_dump(exclude_unset=True)
    for k, v in payload.items():
        setattr(current, k, v)
    db.commit()
    db.refresh(current)
    return current


@router.put("/me/password", status_code=status.HTTP_204_NO_CONTENT)
def change_password(
    body: ChangePasswordIn,
    current: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not verify_password(body.old_password, current.password_hash):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "old password wrong")
    # 防止新旧密码一样
    if verify_password(body.new_password, current.password_hash):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "new password must differ from old")
    current.password_hash = hash_password(body.new_password)
    db.commit()
    return None
