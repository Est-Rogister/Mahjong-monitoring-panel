import asyncio
import random
import json
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from datetime import datetime
from typing import Optional, Dict, Any, List
import aiohttp
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from config import settings
from app.models import ScrapeLog, MonitoredAccount


class AmaeKoromoScraper:
    """雀魂数据抓取器"""
    
    # 段位映射表
    RANK_MAP = {
        0: "初心1", 1: "初心2", 2: "初心3",
        3: "雀士1", 4: "雀士2", 5: "雀士3",
        6: "雀杰1", 7: "雀杰2", 8: "雀杰3",
        9: "雀豪1", 10: "雀豪2", 11: "雀豪3",
        12: "雀圣1", 13: "雀圣2", 14: "雀圣3",
        15: "魂天"
    }
    
    # 房间类型映射
    ROOM_MAP = {
        0: "铜之间东", 1: "铜之间南",
        2: "银之间东", 3: "银之间南",
        4: "金之间东", 5: "金之间南",
        6: "玉之间东", 7: "玉之间南",
        8: "王座东", 9: "王座南"
    }
    
    def __init__(self):
        self.proxy_pool = settings.PROXY_POOL
        self.timeout = aiohttp.ClientTimeout(total=settings.REQUEST_TIMEOUT)
        self.user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
        ]
    
    def _get_headers(self) -> Dict[str, str]:
        """获取随机请求头"""
        return {
            "User-Agent": random.choice(self.user_agents),
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Referer": "https://amae-koromo.sapk.ch/",
        }
    
    def _get_proxy(self) -> Optional[str]:
        """获取随机代理"""
        if self.proxy_pool:
            return random.choice(self.proxy_pool)
        return None
    
    def _parse_rank(self, rank_value: int) -> str:
        """解析段位数值为文本"""
        return self.RANK_MAP.get(rank_value, f"未知({rank_value})")
    
    def _parse_room(self, room_value: int) -> str:
        """解析房间类型"""
        return self.ROOM_MAP.get(room_value, f"未知({room_value})")
    
    async def _fetch_with_retry(self, url: str, params: Optional[Dict] = None) -> Dict[str, Any]:
        """带重试机制的请求"""
        last_error = None
        
        for attempt in range(settings.RETRY_TIMES):
            try:
                if attempt > 0:
                    await asyncio.sleep(2 ** attempt)
                
                proxy = self._get_proxy()
                headers = self._get_headers()
                
                async with aiohttp.ClientSession(timeout=self.timeout) as session:
                    async with session.get(
                        url, 
                        headers=headers, 
                        params=params,
                        proxy=proxy,
                        ssl=False
                    ) as response:
                        response.raise_for_status()
                        return await response.json()
                        
            except Exception as e:
                last_error = str(e)
                continue
        
        raise Exception(f"Failed after {settings.RETRY_TIMES} attempts: {last_error}")
    
    async def fetch_player_data(
        self, 
        player_id: str, 
        mode: str = "12",
        db: Optional[AsyncSession] = None
    ) -> Dict[str, Any]:
        """
        抓取玩家数据（使用新的数据源API）
        
        Args:
            player_id: 玩家ID
            mode: 游戏模式 (12=四麻玉之间, 11=三麻玉之间等)
            db: 数据库会话（用于记录日志）
        
        Returns:
            解析后的玩家数据
        """
        # 使用新的数据源API
        # mode: 12=四麻玉之间, 11=三麻玉之间, 24=三麻金之间等
        mode_int = int(mode) if mode.isdigit() else 12
        
        # 构建API URL (使用四麻API pl4)
        base_url = f"https://5-data.amae-koromo.com/api/v2/pl4"
        start_time = 1262304000000  # 2010-01-01
        end_time = int(datetime.now().timestamp() * 1000)
        
        # 获取基础统计
        stats_url = f"{base_url}/player_stats/{player_id}/{start_time}/{end_time}"
        # 获取扩展统计
        extended_url = f"{base_url}/player_extended_stats/{player_id}/{start_time}/{end_time}"
        
        try:
            # 并行获取三个接口的数据
            params = {"mode": mode_int, "tag": 493203}
            
            stats_data = await self._fetch_with_retry(stats_url, params)
            extended_data = await self._fetch_with_retry(extended_url, params)
            
            # 获取最近对局记录
            records_url = f"{base_url}/player_records/{player_id}/{end_time}/{start_time}"
            records_params = {
                "limit": 20,
                "mode": mode_int,
                "descending": "true",
                "tag": total_games if 'total_games' in locals() else 100
            }
            records_data = await self._fetch_with_retry(records_url, records_params)
            
            # 合并并解析数据
            parsed_data = self._parse_new_player_data(player_id, stats_data, extended_data, records_data)
            
            # 记录成功日志
            if db:
                await self._log_scrape(
                    db, player_id, "success", 
                    json.dumps({"stats": stats_data, "extended": extended_data}, ensure_ascii=False)[:1000]
                )
            
            return parsed_data
            
        except Exception as e:
            if db:
                await self._log_scrape(db, player_id, "failed", error_message=str(e))
            raise Exception(f"Failed to fetch player data: {str(e)}")
    
    def _parse_new_player_data(self, player_id: str, stats_data: Dict, extended_data: Dict, records_data: List = None) -> Dict[str, Any]:
        """解析新的API数据为结构化数据"""
        
        # 基础信息
        nickname = stats_data.get("nickname", "未知")
        
        # 段位信息
        level = stats_data.get("level", {})
        max_level = stats_data.get("max_level", {})
        current_rank = self._parse_level_to_rank(level.get("id", 0))
        max_rank = self._parse_level_to_rank(max_level.get("id", 0))
        
        # 统计信息
        total_games = stats_data.get("count", 0)
        avg_rank = stats_data.get("avg_rank", 0)
        rank_rates = stats_data.get("rank_rates", [0, 0, 0])
        
        # 扩展统计
        extended_stats = {
            "和牌率": round(extended_data.get("和牌率", 0) * 100, 2),
            "自摸率": round(extended_data.get("自摸率", 0) * 100, 2),
            "放铳率": round(extended_data.get("放铳率", 0) * 100, 2),
            "副露率": round(extended_data.get("副露率", 0) * 100, 2),
            "立直率": round(extended_data.get("立直率", 0) * 100, 2),
            "平均打点": extended_data.get("平均打点", 0),
            "平均铳点": extended_data.get("平均铳点", 0),
            "最大连庄": extended_data.get("最大连庄", 0),
            "和了巡数": round(extended_data.get("和了巡数", 0), 2),
            "流局率": round(extended_data.get("流局率", 0) * 100, 2),
            "一发率": round(extended_data.get("一发率", 0) * 100, 2),
            "里宝率": round(extended_data.get("里宝率", 0) * 100, 2),
            "先制率": round(extended_data.get("先制率", 0) * 100, 2),
            "W立直": extended_data.get("W立直", 0),
            "役满": extended_data.get("役满", 0),
        }
        
        # 解析最近对局
        recent_matches = self._parse_new_records(player_id, records_data or [])
        
        return {
            "player_id": player_id,
            "nickname": nickname,
            "current_rank": current_rank,
            "max_rank": max_rank,
            "current_score": level.get("score", 0),
            "max_score": max_level.get("score", 0),
            "last_online": self._parse_last_online(stats_data.get("latest_timestamp")),
            "stats": {
                "total_games": total_games,
                "avg_rank": round(avg_rank, 2),
                "rank_rates": [round(r * 100, 2) for r in rank_rates],
                "negative_rate": round(stats_data.get("negative_rate", 0) * 100, 2),
            },
            "extended_stats": extended_stats,
            "rank_history": [],
            "recent_matches": recent_matches
        }
    
    def _parse_new_records(self, player_id: str, records: List[Dict]) -> List[Dict]:
        """解析新的对局记录格式"""
        matches = []
        player_id_int = int(player_id)
        
        for record in records:
            players = record.get("players", [])
            
            # 查找当前玩家在这场对局中的信息
            player_rank = 0
            point_change = 0
            
            for i, player in enumerate(players):
                if player.get("accountId") == player_id_int:
                    player_rank = i + 1
                    point_change = player.get("gradingScore", 0)
                    break
            
            # 解析时间戳
            start_time = record.get("startTime", 0)
            date_str = datetime.fromtimestamp(start_time).strftime("%Y-%m-%d %H:%M") if start_time else "未知"
            
            # 解析房间类型
            mode_id = record.get("modeId", 0)
            room_name = self._parse_mode_id(mode_id)
            
            matches.append({
                "date": date_str,
                "room": room_name,
                "rank": player_rank,
                "point_change": point_change
            })
        
        return matches
    
    def _parse_mode_id(self, mode_id: int) -> str:
        """解析 modeId 为房间名称"""
        # modeId 映射
        mode_map = {
            12: "四麻玉之间",
            11: "三麻玉之间",
            24: "三麻金之间",
            9: "四麻金之间",
            16: "四麻王座",
            15: "三麻王座",
        }
        return mode_map.get(mode_id, f"房间({mode_id})")
    
    def _parse_player_data(self, player_id: str, raw_data: Dict) -> Dict[str, Any]:
        """解析原始数据为结构化数据（旧API，保留兼容）"""
        
        # 基础信息
        nickname = raw_data.get("nickname", "未知")
        
        # 段位信息
        max_rank_value = raw_data.get("max_rank", 0)
        current_rank_value = raw_data.get("rank", 0)
        
        # 统计信息
        stats = raw_data.get("stat", {})
        total_games = stats.get("count", 0)
        
        # 计算和了率
        win_count = stats.get("win", 0)
        win_rate = win_count / total_games if total_games > 0 else 0
        
        # 计算平均顺位
        rank_counts = stats.get("rank_counts", [0, 0, 0, 0])
        total_ranks = sum(rank_counts)
        avg_rank = sum((i + 1) * count for i, count in enumerate(rank_counts)) / total_ranks if total_ranks > 0 else 0
        
        # 最近10场战绩
        recent_10 = self._get_recent_10_matches(raw_data.get("records", []))
        
        # 最近对局列表
        recent_matches = self._parse_recent_matches(raw_data.get("records", [])[:20])
        
        # 段位历史（简化版）
        rank_history = raw_data.get("rank_history", [])
        
        return {
            "player_id": player_id,
            "nickname": nickname,
            "max_rank": self._parse_rank(max_rank_value),
            "current_rank": self._parse_rank(current_rank_value),
            "last_online": self._parse_last_online(raw_data.get("latest_timestamp")),
            "stats": {
                "total_games": total_games,
                "win_rate": round(win_rate * 100, 2),
                "avg_rank": round(avg_rank, 2),
                "recent_10": recent_10
            },
            "rank_history": rank_history,
            "recent_matches": recent_matches
        }
    
    def _get_recent_10_matches(self, records: List[Dict]) -> List[int]:
        """获取最近10场战绩（顺位）"""
        recent = []
        for record in records[:10]:
            # 查找玩家在这场对局中的顺位
            for i, pid in enumerate(record.get("players", [])):
                if str(pid) == record.get("target_player"):
                    recent.append(i + 1)
                    break
        return recent
    
    def _parse_recent_matches(self, records: List[Dict]) -> List[Dict]:
        """解析最近对局列表"""
        matches = []
        for record in records:
            # 查找玩家在这场对局中的信息
            player_rank = 0
            point_change = 0
            
            for i, pid in enumerate(record.get("players", [])):
                if str(pid) == record.get("target_player"):
                    player_rank = i + 1
                    scores = record.get("scores", [])
                    if i < len(scores):
                        point_change = scores[i]
                    break
            
            # 解析时间戳
            timestamp = record.get("start_time", 0)
            date_str = datetime.fromtimestamp(timestamp / 1000).strftime("%Y-%m-%d %H:%M") if timestamp else "未知"
            
            # 解析房间类型
            room_type = record.get("room_type", 0)
            
            matches.append({
                "date": date_str,
                "room": self._parse_room(room_type),
                "rank": player_rank,
                "point_change": point_change
            })
        
        return matches
    
    def _parse_last_online(self, timestamp: Optional[int]) -> Optional[datetime]:
        """解析最后上线时间"""
        if timestamp:
            return datetime.fromtimestamp(timestamp / 1000)
        return None
    
    async def _log_scrape(
        self, 
        db: AsyncSession, 
        player_id: str, 
        status: str, 
        response_data: Optional[str] = None,
        error_message: Optional[str] = None
    ):
        """记录抓取日志"""
        log = ScrapeLog(
            player_id=player_id,
            status=status,
            response_data=response_data,
            error_message=error_message
        )
        db.add(log)
        await db.commit()
    
    def _parse_level_to_rank(self, level_id: int) -> str:
        """解析 level.id 为段位文本
        
        level.id 格式: 
        - 1xxxx = 四麻段位 (10101=初心1, 10201=雀士1, 10301=雀杰1, 10401=雀豪1, 10501=雀圣1, 10601=魂天)
        - 2xxxx = 三麻段位
        """
        # 提取后四位判断段位
        base = level_id % 10000
        rank_num = base // 100  # 01=初心, 02=雀士, 03=雀杰, 04=雀豪, 05=雀圣, 06=魂天
        level_num = base % 100  # 01, 02, 03
        
        rank_map = {
            1: "初心",
            2: "雀士", 
            3: "雀杰",
            4: "雀豪",
            5: "雀圣",
            6: "魂天"
        }
        
        rank_name = rank_map.get(rank_num, f"未知({rank_num})")
        return f"{rank_name}{level_num}"
    
    async def search_players(self, nickname: str, limit: int = 20) -> List[Dict[str, Any]]:
        """
        根据昵称或ID搜索玩家
        
        Args:
            nickname: 玩家昵称（支持模糊搜索）或玩家ID（纯数字）
            limit: 返回结果数量限制
        
        Returns:
            玩家列表，包含 player_id 和 nickname
        """
        # 如果输入是纯数字，当作玩家ID直接查询
        if nickname.isdigit():
            try:
                base_url = "https://5-data.amae-koromo.com/api/v2/pl4"
                start_time = 1262304000000
                end_time = int(datetime.now().timestamp() * 1000)
                stats_url = f"{base_url}/player_stats/{nickname}/{start_time}/{end_time}"
                
                params = {"mode": 12, "tag": 493203}
                stats_data = await self._fetch_with_retry(stats_url, params)
                
                level = stats_data.get("level", {})
                return [{
                    "player_id": nickname,
                    "nickname": stats_data.get("nickname", "未知"),
                    "rank": self._parse_level_to_rank(level.get("id", 0)),
                    "score": level.get("score", 0),
                    "latest_timestamp": stats_data.get("latest_timestamp")
                }]
            except Exception:
                return []
        
        # 使用正确的搜索 API
        url = f"https://5-data.amae-koromo.com/api/v2/pl4/search_player/{nickname}"
        
        last_error = None
        
        for attempt in range(settings.RETRY_TIMES):
            try:
                if attempt > 0:
                    await asyncio.sleep(2 ** attempt)
                
                proxy = self._get_proxy()
                headers = self._get_headers()
                
                async with aiohttp.ClientSession(timeout=self.timeout) as session:
                    async with session.get(
                        url, 
                        headers=headers,
                        params={"limit": limit, "tag": "all"},
                        proxy=proxy,
                        ssl=False
                    ) as response:
                        response.raise_for_status()
                        raw_data = await response.json()
                        
                        # 解析搜索结果
                        results = []
                        for item in raw_data:
                            level = item.get("level", {})
                            level_id = level.get("id", 0)
                            
                            results.append({
                                "player_id": str(item.get("id")),
                                "nickname": item.get("nickname", "未知"),
                                "rank": self._parse_level_to_rank(level_id),
                                "score": level.get("score", 0),
                                "latest_timestamp": item.get("latest_timestamp")
                            })
                        
                        return results
                        
            except Exception as e:
                last_error = str(e)
                continue
        
        raise Exception(f"Failed to search players after {settings.RETRY_TIMES} attempts: {last_error}")


# 全局抓取器实例
scraper = AmaeKoromoScraper()
