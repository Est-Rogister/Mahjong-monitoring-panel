from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List, Any


# ==================== Account Schemas ====================

class AccountBase(BaseModel):
    player_id: str


class AccountCreate(AccountBase):
    pass


class AccountUpdate(BaseModel):
    nickname: Optional[str] = None
    last_online: Optional[datetime] = None
    max_rank: Optional[str] = None
    current_rank: Optional[str] = None


class AccountResponse(AccountBase):
    id: int
    nickname: Optional[str]
    last_online: Optional[datetime]
    max_rank: Optional[str]
    current_rank: Optional[str]
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


# ==================== Player Details Schemas ====================

class PlayerStats(BaseModel):
    total_games: int
    avg_rank: float
    rank_rates: List[float]
    negative_rate: float


class ExtendedStats(BaseModel):
    和牌率: float
    自摸率: float
    放铳率: float
    副露率: float
    立直率: float
    平均打点: int
    平均铳点: int
    最大连庄: int
    和了巡数: float
    流局率: float
    一发率: float
    里宝率: float
    先制率: float
    W立直: int
    役满: int


class MatchRecord(BaseModel):
    date: str
    room: str
    rank: int
    point_change: int


class PlayerDetails(BaseModel):
    player_id: str
    nickname: str
    current_rank: Optional[str] = None
    max_rank: Optional[str] = None
    current_score: Optional[int] = None
    max_score: Optional[int] = None
    stats: PlayerStats
    extended_stats: ExtendedStats
    rank_history: List[Any]
    recent_matches: List[MatchRecord]


# ==================== API Response Schemas ====================

class ApiResponse(BaseModel):
    success: bool
    message: Optional[str] = None
    data: Optional[Any] = None
