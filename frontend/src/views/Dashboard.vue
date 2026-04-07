<template>
  <div class="dashboard">
    <div class="header">
      <h1>雀魂监控面板</h1>
      <el-button type="primary" @click="showAddDialog = true">
        <el-icon><Plus /></el-icon>添加账号
      </el-button>
    </div>

    <div class="accounts-grid" v-if="accounts.length > 0">
      <el-card
        v-for="account in accounts"
        :key="account.id"
        class="account-card"
        shadow="hover"
      >
        <div class="card-header">
          <div class="nickname">{{ account.nickname || '加载中...' }}</div>
          <div class="player-id">ID: {{ account.player_id }}</div>
        </div>

        <div class="card-body">
          <div class="rank-info">
            <div class="rank-item">
              <span class="label">当前段位:</span>
              <RankBadge :rank="account.current_rank" />
            </div>
            <div class="rank-item">
              <span class="label">最高段位:</span>
              <RankBadge :rank="account.max_rank" />
            </div>
          </div>

          <div class="last-online" v-if="account.last_online">
            <span class="label">上次上线:</span>
            <span class="time">{{ formatTime(account.last_online) }}</span>
          </div>
          <div class="last-online" v-else>
            <span class="label">上次上线:</span>
            <span class="time">未获取</span>
          </div>
        </div>

        <div class="card-footer">
          <el-button 
            type="primary" 
            size="small" 
            @click="goToDetail(account.id)"
          >
            详情
          </el-button>
          <el-button
            type="warning"
            size="small"
            :loading="refreshing === account.id"
            @click="refreshAccount(account.id)"
          >
            刷新
          </el-button>
          <el-button
            type="danger"
            size="small"
            @click="deleteAccount(account.id)"
          >
            删除
          </el-button>
        </div>
      </el-card>
    </div>

    <el-empty v-else description="暂无监控账号，请点击右上角添加" />

    <!-- 添加账号对话框 -->
    <el-dialog
      v-model="showAddDialog"
      title="添加监控账号"
      width="500px"
    >
      <el-form :model="newAccount" label-width="100px">
        <el-form-item label="搜索昵称">
          <el-select
            v-model="selectedPlayer"
            filterable
            remote
            reserve-keyword
            placeholder="输入玩家昵称搜索"
            :remote-method="searchPlayers"
            :loading="searching"
            style="width: 100%"
            @change="onPlayerSelect"
          >
            <el-option
              v-for="player in searchResults"
              :key="player.player_id"
              :label="`${player.nickname} (ID: ${player.player_id})`"
              :value="player"
            >
              <div class="search-result-item">
                <span class="nickname">{{ player.nickname }}</span>
                <span class="player-id">ID: {{ player.player_id }}</span>
                <RankBadge :rank="player.rank" />
                <span class="score">{{ player.score }}pt</span>
              </div>
            </el-option>
          </el-select>
        </el-form-item>
        
        <el-divider>或直接输入ID</el-divider>
        
        <el-form-item label="玩家ID">
          <el-input
            v-model="newAccount.player_id"
            placeholder="请输入玩家ID，如: 13044970"
            @input="selectedPlayer = null"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showAddDialog = false">取消</el-button>
        <el-button type="primary" @click="addAccount" :loading="adding">
          确定
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue';
import { useRouter } from 'vue-router';
import { ElMessage, ElMessageBox } from 'element-plus';
import { Plus } from '@element-plus/icons-vue';
import { accountApi } from '../api';
import type { Account, AccountCreate, PlayerSearchResult } from '../types';
import RankBadge from '../components/RankBadge.vue';

const router = useRouter();
const accounts = ref<Account[]>([]);
const showAddDialog = ref(false);
const adding = ref(false);
const refreshing = ref<number | null>(null);

// 搜索相关
const searchResults = ref<PlayerSearchResult[]>([]);
const searching = ref(false);
const selectedPlayer = ref<PlayerSearchResult | null>(null);

const newAccount = ref<AccountCreate>({
  player_id: '',
});

// 获取账号列表
const fetchAccounts = async () => {
  try {
    const response = await accountApi.getAccounts();
    accounts.value = response.data;
  } catch (error) {
    ElMessage.error('获取账号列表失败');
    console.error(error);
  }
};

// 添加账号
const addAccount = async () => {
  if (!newAccount.value.player_id.trim()) {
    ElMessage.warning('请输入玩家ID');
    return;
  }

  adding.value = true;
  try {
    await accountApi.createAccount({
      player_id: newAccount.value.player_id.trim(),
    });
    ElMessage.success('添加成功');
    showAddDialog.value = false;
    newAccount.value.player_id = '';
    await fetchAccounts();
  } catch (error: any) {
    const msg = error.response?.data?.detail || '添加失败';
    ElMessage.error(msg);
  } finally {
    adding.value = false;
  }
};

// 删除账号
const deleteAccount = async (id: number) => {
  try {
    await ElMessageBox.confirm('确定要删除这个监控账号吗？', '提示', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning',
    });

    await accountApi.deleteAccount(id);
    ElMessage.success('删除成功');
    await fetchAccounts();
  } catch (error: any) {
    if (error !== 'cancel') {
      const msg = error.response?.data?.detail || '删除失败';
      ElMessage.error(msg);
    }
  }
};

// 刷新账号数据
const refreshAccount = async (id: number) => {
  refreshing.value = id;
  try {
    await accountApi.refreshAccount(id);
    ElMessage.success('刷新成功');
    await fetchAccounts();
  } catch (error: any) {
    const msg = error.response?.data?.detail || '刷新失败';
    ElMessage.error(msg);
  } finally {
    refreshing.value = null;
  }
};

// 跳转到详情页
const goToDetail = (id: number) => {
  router.push(`/player/${id}`);
};

// 搜索玩家
const searchPlayers = async (query: string) => {
  if (!query || query.length < 2) {
    searchResults.value = [];
    return;
  }
  
  searching.value = true;
  try {
    const response = await accountApi.searchPlayers(query, 10);
    searchResults.value = response.data.data;
  } catch (error) {
    console.error('搜索失败', error);
    searchResults.value = [];
  } finally {
    searching.value = false;
  }
};

// 选择玩家
const onPlayerSelect = (player: PlayerSearchResult) => {
  if (player) {
    newAccount.value.player_id = player.player_id;
  }
};

// 格式化时间
const formatTime = (timeStr: string) => {
  const date = new Date(timeStr);
  const now = new Date();
  const diff = now.getTime() - date.getTime();
  
  const minutes = Math.floor(diff / 60000);
  const hours = Math.floor(diff / 3600000);
  const days = Math.floor(diff / 86400000);
  
  if (minutes < 1) return '刚刚';
  if (minutes < 60) return `${minutes}分钟前`;
  if (hours < 24) return `${hours}小时前`;
  if (days < 30) return `${days}天前`;
  
  return date.toLocaleDateString();
};

onMounted(() => {
  fetchAccounts();
});
</script>

<style scoped>
.dashboard {
  padding: 20px;
  max-width: 1400px;
  margin: 0 auto;
}

.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
}

.header h1 {
  margin: 0;
  font-size: 24px;
  color: #303133;
}

.accounts-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 20px;
}

.account-card {
  transition: transform 0.2s;
}

.account-card:hover {
  transform: translateY(-4px);
}

.card-header {
  margin-bottom: 16px;
  padding-bottom: 12px;
  border-bottom: 1px solid #ebeef5;
}

.nickname {
  font-size: 18px;
  font-weight: 600;
  color: #303133;
  margin-bottom: 4px;
}

.player-id {
  font-size: 12px;
  color: #909399;
}

.card-body {
  margin-bottom: 16px;
}

.rank-info {
  margin-bottom: 12px;
}

.rank-item {
  display: flex;
  align-items: center;
  margin-bottom: 8px;
}

.label {
  font-size: 14px;
  color: #606266;
  margin-right: 8px;
  min-width: 70px;
}

.last-online {
  display: flex;
  align-items: center;
  font-size: 13px;
}

.last-online .time {
  color: #409eff;
}

.card-footer {
  display: flex;
  gap: 8px;
  justify-content: flex-end;
}

/* 搜索结果样式 */
.search-result-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 4px 0;
}

.search-result-item .nickname {
  font-weight: 600;
  color: #303133;
  font-size: 14px;
  min-width: 120px;
}

.search-result-item .player-id {
  color: #909399;
  font-size: 12px;
  min-width: 100px;
}

.search-result-item .score {
  color: #67c23a;
  font-size: 12px;
  font-weight: 500;
}
</style>
