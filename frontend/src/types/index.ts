// 账号相关类型
export interface Account {
  id: number;
  player_id: string;
  nickname: string | null;
  last_online: string | null;
  max_rank: string | null;
  current_rank: string | null;
  created_at: string;
  updated_at: string;
}

export interface AccountCreate {
  player_id: string;
}

// 玩家统计
export interface PlayerStats {
  total_games: number;
  avg_rank: number;
  rank_rates: number[];
  negative_rate: number;
}

// 扩展统计
export interface ExtendedStats {
  和牌率: number;
  自摸率: number;
  放铳率: number;
  副露率: number;
  立直率: number;
  平均打点: number;
  平均铳点: number;
  最大连庄: number;
  和了巡数: number;
  流局率: number;
  一发率: number;
  里宝率: number;
  先制率: number;
  W立直: number;
  役满: number;
}

// 对局记录
export interface MatchRecord {
  date: string;
  room: string;
  rank: number;
  point_change: number;
}

// 玩家详情
export interface PlayerDetails {
  player_id: string;
  nickname: string;
  current_rank?: string | null;
  max_rank?: string | null;
  current_score?: number;
  max_score?: number;
  last_online?: string | null;
  stats: PlayerStats;
  extended_stats: ExtendedStats;
  rank_history: any[];
  recent_matches: MatchRecord[];
}

// 玩家搜索结果
export interface PlayerSearchResult {
  player_id: string;
  nickname: string;
  rank: string;
  score: number;
  latest_timestamp: number;
}

// API 响应
export interface ApiResponse<T = any> {
  success: boolean;
  message?: string;
  data?: T;
}
