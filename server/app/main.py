"""FastAPI 入口：挂路由、开 CORS、启动时建表、托管前端静态页。"""
from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.core.config import settings
from app.core.db import Base, engine
from app.llm.factory import close_all_engines
from app.api import auth, conversations, chat, models_list

# 前端打包产物（npm run build 生成的 web/dist）
WEB_DIST = Path(__file__).resolve().parents[2] / "web" / "dist"


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动时自动建表（开发期够用；生产用 Alembic）
    Base.metadata.create_all(bind=engine)
    # 后台预热本地模型：用户第一次发消息时无需等待 30s+ 的权重加载
    import asyncio

    from app.llm.factory import get_engine

    if (Path(settings.local_model_dir) / "full_sft_768" / "model.json").exists():
        async def _warmup():
            try:
                eng = get_engine("local")
                for mid in ("local/full_sft_768", "local/wukong_lora_768"):
                    try:
                        await asyncio.to_thread(eng._load, mid)
                    except Exception as e:
                        print(f"[warmup] {mid} 跳过: {e}")
            except Exception as e:
                print(f"[warmup] 本地引擎不可用: {e}")

        asyncio.create_task(_warmup())
    yield
    await close_all_engines()


app = FastAPI(
    title="AI 聊天对话系统",
    version="0.1.0",
    description="毕业设计 / 课程作业 Demo。账号体系 + 多模型切换 + SSE 流式回复。\n"
                "当前 ENGINE_BACKEND=mock，无模型文件也可完整跑通前端。",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list if settings.cors_origins_list else ["*"],
    # 放行 Cloudflare Pages 与临时隧道域名（前端独立托管时跨域调 API）
    allow_origin_regex=r"https://.*\.(pages\.dev|trycloudflare\.com)",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(conversations.router)
app.include_router(chat.router)
app.include_router(models_list.router)


@app.get("/", tags=["meta"], include_in_schema=False)
def root():
    # 有前端打包产物时直接返回页面，否则返回服务信息
    index = WEB_DIST / "index.html"
    if index.exists():
        return FileResponse(index)
    return {
        "name": "AI 聊天对话系统",
        "docs": "/docs",
        "engine_backend": settings.engine_backend,
        "local_model_dir": settings.local_model_dir,
    }


@app.get("/healthz", tags=["meta"])
def healthz():
    return {"ok": True}


# 托管前端静态资源（assets 等），SPA 路由回退到 index.html
if WEB_DIST.exists():
    app.mount("/assets", StaticFiles(directory=WEB_DIST / "assets"), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    def spa_fallback(full_path: str):
        # API 路径不进这里（上面路由已先匹配），其余一律回退到前端入口
        target = WEB_DIST / full_path
        if full_path and target.is_file():
            return FileResponse(target)
        return FileResponse(WEB_DIST / "index.html")
