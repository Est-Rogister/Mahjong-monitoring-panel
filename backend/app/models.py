from sqlalchemy import Column, Integer, String, DateTime, Text
from sqlalchemy.sql import func
from app.database import Base


class MonitoredAccount(Base):
    __tablename__ = "monitored_accounts"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    player_id = Column(String, unique=True, index=True, nullable=False)
    nickname = Column(String, nullable=True)
    last_online = Column(DateTime, nullable=True)
    max_rank = Column(String, nullable=True)
    current_rank = Column(String, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class ScrapeLog(Base):
    __tablename__ = "scrape_logs"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    player_id = Column(String, nullable=False, index=True)
    status = Column(String, nullable=True)  # success / failed
    response_data = Column(Text, nullable=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
