from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import settings
from app.database import init_db
from app.routers import accounts

app = FastAPI(
    title="雀魂监控面板 API",
    description="雀魂玩家数据监控面板后端服务",
    version="1.0.0"
)

# 配置 CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(accounts.router)


@app.on_event("startup")
async def startup_event():
    """应用启动时初始化数据库"""
    await init_db()
    print("数据库初始化完成")


@app.get("/")
async def root():
    return {"message": "雀魂监控面板 API 服务运行中"}


@app.get("/health")
async def health_check():
    return {"status": "healthy"}


if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
