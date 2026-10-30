"""SQLAlchemy 引擎 + Session 工厂 + Base。"""
from __future__ import annotations

import os
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.core.config import settings

# SQLite 特判：相对路径基于 server/ 目录
url = settings.database_url
if url.startswith("sqlite:///./"):
    db_path = Path(__file__).resolve().parents[2] / url.replace("sqlite:///./", "")
    db_path.parent.mkdir(parents=True, exist_ok=True)
    url = f"sqlite:///{db_path.resolve()}"

connect_args = {"check_same_thread": False} if url.startswith("sqlite") else {}

engine = create_engine(url, connect_args=connect_args, pool_pre_ping=True, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


class Base(DeclarativeBase):
    pass


def get_db():
    """FastAPI 依赖注入：请求级 Session，用完自动 close。"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
