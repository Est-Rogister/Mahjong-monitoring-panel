import axios from 'axios';
import type { Account, AccountCreate, PlayerDetails, ApiResponse, PlayerSearchResult } from '../types';

const api = axios.create({
  baseURL: 'http://localhost:8000/api',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// 账号相关 API
export const accountApi = {
  // 获取所有账号
  getAccounts: () => api.get<Account[]>('/accounts'),
  
  // 添加账号
  createAccount: (data: AccountCreate) => api.post<Account>('/accounts', data),
  
  // 删除账号
  deleteAccount: (id: number) => api.delete<ApiResponse>(`/accounts/${id}`),
  
  // 刷新账号数据
  refreshAccount: (id: number) => api.post<Account>(`/accounts/${id}/refresh`),
  
  // 获取账号详情
  getAccountDetails: (id: number) => api.get<PlayerDetails>(`/accounts/${id}/details`),
  
  // 搜索玩家
  searchPlayers: (nickname: string, limit: number = 10) => 
    api.get<{ success: boolean; data: PlayerSearchResult[] }>('/accounts/search/players', {
      params: { nickname, limit }
    }),
};

export default api;
