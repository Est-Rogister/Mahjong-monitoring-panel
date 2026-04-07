from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    # 数据库配置
    DATABASE_URL: str = "sqlite:///./mjsoul_monitor.db"
    
    # 代理配置（可选）
    PROXY_POOL: List[str] = []
    
    # 请求配置
    REQUEST_TIMEOUT: int = 30
    RETRY_TIMES: int = 3
    
    # 缓存配置（秒）
    CACHE_TTL: int = 300
    
    # CORS配置 - 允许所有本地开发端口
    ALLOWED_ORIGINS: List[str] = [
        "http://localhost:5173", "http://127.0.0.1:5173",
        "http://localhost:5174", "http://127.0.0.1:5174",
        "http://localhost:5175", "http://127.0.0.1:5175",
        "http://localhost:3000", "http://127.0.0.1:3000",
    ]
    
    class Config:
        env_file = ".env"


settings = Settings()
