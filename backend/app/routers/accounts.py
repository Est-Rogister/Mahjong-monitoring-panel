from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete

from app.database import get_db
from app.models import MonitoredAccount
from app.schemas import (
    AccountCreate, 
    AccountResponse, 
    PlayerDetails,
    ApiResponse
)
from app.services.scraper import scraper

router = APIRouter(prefix="/api/accounts", tags=["accounts"])


@router.get("", response_model=List[AccountResponse])
async def get_accounts(db: AsyncSession = Depends(get_db)):
    """获取所有监控账号列表"""
    result = await db.execute(select(MonitoredAccount))
    accounts = result.scalars().all()
    return accounts


@router.post("", response_model=AccountResponse)
async def create_account(
    account: AccountCreate, 
    db: AsyncSession = Depends(get_db)
):
    """添加新的监控账号"""
    # 检查是否已存在
    result = await db.execute(
        select(MonitoredAccount).where(MonitoredAccount.player_id == account.player_id)
    )
    existing = result.scalar_one_or_none()
    
    if existing:
        raise HTTPException(status_code=400, detail="该玩家ID已存在")
    
    # 创建新账号记录
    db_account = MonitoredAccount(player_id=account.player_id)
    db.add(db_account)
    await db.commit()
    await db.refresh(db_account)
    
    return db_account


@router.delete("/{account_id}", response_model=ApiResponse)
async def delete_account(account_id: int, db: AsyncSession = Depends(get_db)):
    """删除监控账号"""
    result = await db.execute(
        select(MonitoredAccount).where(MonitoredAccount.id == account_id)
    )
    account = result.scalar_one_or_none()
    
    if not account:
        raise HTTPException(status_code=404, detail="账号不存在")
    
    await db.execute(
        delete(MonitoredAccount).where(MonitoredAccount.id == account_id)
    )
    await db.commit()
    
    return ApiResponse(success=True, message="删除成功")


@router.post("/{account_id}/refresh", response_model=AccountResponse)
async def refresh_account(
    account_id: int, 
    db: AsyncSession = Depends(get_db)
):
    """手动刷新账号数据"""
    result = await db.execute(
        select(MonitoredAccount).where(MonitoredAccount.id == account_id)
    )
    account = result.scalar_one_or_none()
    
    if not account:
        raise HTTPException(status_code=404, detail="账号不存在")
    
    try:
        # 抓取最新数据
        player_data = await scraper.fetch_player_data(account.player_id, db=db)
        
        # 更新账号信息
        account.nickname = player_data.get("nickname")
        account.last_online = player_data.get("last_online")
        account.max_rank = player_data.get("max_rank")
        account.current_rank = player_data.get("current_rank")
        
        await db.commit()
        await db.refresh(account)
        
        return account
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"数据刷新失败: {str(e)}")


@router.get("/{account_id}/details", response_model=PlayerDetails)
async def get_account_details(
    account_id: int, 
    db: AsyncSession = Depends(get_db)
):
    """获取玩家详细数据"""
    result = await db.execute(
        select(MonitoredAccount).where(MonitoredAccount.id == account_id)
    )
    account = result.scalar_one_or_none()
    
    if not account:
        raise HTTPException(status_code=404, detail="账号不存在")
    
    try:
        # 抓取详细数据
        player_data = await scraper.fetch_player_data(account.player_id, db=db)
        return PlayerDetails(**player_data)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取详情失败: {str(e)}")


@router.get("/search/players")
async def search_players(
    nickname: str = Query(..., description="玩家昵称，支持模糊搜索"),
    limit: int = Query(10, ge=1, le=50, description="返回结果数量限制")
):
    """
    根据昵称搜索玩家
    
    返回匹配的玩家列表，包含 player_id 和 nickname
    """
    import traceback
    try:
        results = await scraper.search_players(nickname, limit=limit)
        return {"success": True, "data": results}
    except Exception as e:
        error_detail = f"搜索失败: {str(e)}\n{traceback.format_exc()}"
        print(error_detail)  # 打印到后端日志
        raise HTTPException(status_code=500, detail=f"搜索失败: {str(e)}")
