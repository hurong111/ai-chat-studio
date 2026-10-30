"""GET /api/models —— 给前端下拉框用。"""
from __future__ import annotations

from fastapi import APIRouter, Depends

from app.core.deps import get_current_user
from app.llm.registry import list_all_models
from app.models.orm import User
from app.models.schemas import ModelOut

router = APIRouter(prefix="/api", tags=["models"])


@router.get("/models", response_model=list[ModelOut])
def get_models(_: User = Depends(get_current_user)):
    return list_all_models()
