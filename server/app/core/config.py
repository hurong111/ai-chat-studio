"""集中式配置，通过 pydantic-settings 从 .env 或环境变量加载。"""
from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    host: str = "0.0.0.0"
    port: int = 8000
    cors_origins: str = "http://localhost:5173"

    database_url: str = "sqlite:///./data/chat.db"

    jwt_secret: str = "change-me-to-a-long-random-string-please"
    jwt_expire_minutes: int = 1440
    bcrypt_rounds: int = 12

    engine_backend: str = "mock"  # mock | local | remote

    remote_providers: str = ""

    # DeepSeek
    remote_deepseek_key: str = ""
    remote_deepseek_base_url: str = "https://api.deepseek.com/v1"
    remote_deepseek_model: str = "deepseek-chat"

    # 通义
    remote_qwen_key: str = ""
    remote_qwen_base_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    remote_qwen_model: str = "qwen-plus"

    # Ollama / LM Studio
    remote_ollama_base_url: str = "http://localhost:11434/v1"
    remote_ollama_model: str = "qwen2.5:3b"

    # 本地模型目录
    local_model_dir: str = "./models"

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def remote_provider_list(self) -> list[str]:
        return [p.strip().lower() for p in self.remote_providers.split(",") if p.strip()]


settings = Settings()
