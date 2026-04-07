<template>
  <div class="player-detail">
    <div class="header">
      <el-button @click="goBack" link>
        <el-icon><ArrowLeft /></el-icon>返回列表
      </el-button>
      <h2>玩家详情</h2>
      <div class="placeholder"></div>
    </div>

    <div v-if="loading" class="loading">
      <el-skeleton :rows="10" animated />
    </div>

    <div v-else-if="playerData" class="content">
      <!-- 基本信息卡片 -->
      <el-card class="info-card">
        <div class="player-header">
          <div class="player-info">
            <h3>{{ playerData.nickname }}</h3>
            <p class="player-id">ID: {{ playerData.player_id }}</p>
          </div>
          <div class="player-ranks">
            <div class="rank-display">
              <span class="label">当前段位:</span>
              <RankBadge :rank="(playerData.current_rank || account?.current_rank || null) as string | null" />
            </div>
            <div class="rank-display">
              <span class="label">最高段位:</span>
              <RankBadge :rank="(playerData.max_rank || account?.max_rank || null) as string | null" />
            </div>
          </div>
        </div>
      </el-card>

      <!-- 段位分数 -->
      <el-row :gutter="20" class="stats-row">
        <el-col :span="12">
          <el-card class="score-card">
            <div class="score-item">
              <span class="label">当前分数:</span>
              <span class="value">{{ playerData.current_score }} / 2800</span>
              <el-progress :percentage="Math.min(100, (playerData.current_score || 0) / 28)" :stroke-width="10" />
            </div>
            <div class="score-item">
              <span class="label">最高分数:</span>
              <span class="value highest">{{ playerData.max_score }}</span>
            </div>
          </el-card>
        </el-col>
        <el-col :span="12">
          <el-card class="rank-rate-card">
            <div class="rank-rate-title">顺位分布</div>
            <div ref="rankChartRef" class="rank-chart"></div>
            <div class="rank-legend">
              <div class="legend-item">
                <span class="dot" style="background: #e6a23c;"></span>
                <span>1位 {{ rankRatesDisplay[0] }}%</span>
              </div>
              <div class="legend-item">
                <span class="dot" style="background: #67c23a;"></span>
                <span>2位 {{ rankRatesDisplay[1] }}%</span>
              </div>
              <div class="legend-item">
                <span class="dot" style="background: #409eff;"></span>
                <span>3位 {{ rankRatesDisplay[2] }}%</span>
              </div>
              <div class="legend-item">
                <span class="dot" style="background: #909399;"></span>
                <span>4位 {{ rankRatesDisplay[3] }}%</span>
              </div>
            </div>
          </el-card>
        </el-col>
      </el-row>

      <!-- 基础统计 -->
      <el-row :gutter="20" class="stats-row">
        <el-col :span="8">
          <el-card class="stat-card">
            <div class="stat-value">{{ playerData.stats.total_games }}</div>
            <div class="stat-label">总对局数</div>
          </el-card>
        </el-col>
        <el-col :span="8">
          <el-card class="stat-card">
            <div class="stat-value">{{ playerData.stats.avg_rank.toFixed(2) }}</div>
            <div class="stat-label">平均顺位</div>
          </el-card>
        </el-col>
        <el-col :span="8">
          <el-card class="stat-card">
            <div class="stat-value">{{ playerData.stats.negative_rate }}%</div>
            <div class="stat-label">被飞率</div>
          </el-card>
        </el-col>
      </el-row>

      <!-- 详细统计 -->
      <el-card class="extended-stats-card">
        <template #header>
          <div class="card-header">
            <span>详细统计</span>
          </div>
        </template>
        <el-row :gutter="20">
          <el-col :span="6" v-for="(value, key) in extendedStatsDisplay as Record<string, number>" :key="key">
            <div class="extended-stat-item">
              <div class="stat-name">{{ key }}</div>
              <div class="stat-value-small">{{ formatStatValue(key, value as number) }}</div>
            </div>
          </el-col>
        </el-row>
      </el-card>

      <!-- 最近对局 -->
      <el-card class="matches-card">
        <template #header>
          <div class="card-header">
            <span>最近对局</span>
          </div>
        </template>
        <el-table :data="playerData.recent_matches" style="width: 100%" v-if="playerData.recent_matches.length > 0" class="matches-table">
          <el-table-column prop="date" label="时间" min-width="140" align="center" />
          <el-table-column prop="room" label="房间" min-width="100" align="center" />
          <el-table-column label="顺位" min-width="70" align="center">
            <template #default="scope">
              <span :class="`rank-text-${scope.row.rank}`">
                {{ scope.row.rank }}位
              </span>
            </template>
          </el-table-column>
          <el-table-column label="PT变化" min-width="90" align="center">
            <template #default="scope">
              <span :class="scope.row.point_change >= 0 ? 'positive' : 'negative'">
                {{ scope.row.point_change >= 0 ? '+' : '' }}{{ scope.row.point_change }}
              </span>
            </template>
          </el-table-column>
        </el-table>
        <el-empty v-else description="暂无对局记录" />
      </el-card>
    </div>

    <el-empty v-else description="加载失败，请返回重试" />
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed, watch, nextTick } from 'vue';
import { useRouter, useRoute } from 'vue-router';
import { ElMessage } from 'element-plus';
import { ArrowLeft } from '@element-plus/icons-vue';
import * as echarts from 'echarts';
import { accountApi } from '../api';
import type { PlayerDetails, Account } from '../types';
import RankBadge from '../components/RankBadge.vue';

const router = useRouter();
const route = useRoute();

const playerId = ref<number>(parseInt(route.params.id as string));
const playerData = ref<PlayerDetails | null>(null);
const account = ref<Account | null>(null);
const loading = ref(true);
const rankChartRef = ref<HTMLElement | null>(null);
let rankChart: echarts.ECharts | null = null;

// 扩展统计显示
const extendedStatsDisplay = computed(() => {
  if (!playerData.value?.extended_stats) return {};
  const stats = playerData.value.extended_stats;
  return {
    '和牌率': stats.和牌率 || 0,
    '自摸率': stats.自摸率 || 0,
    '放铳率': stats.放铳率 || 0,
    '副露率': stats.副露率 || 0,
    '立直率': stats.立直率 || 0,
    '平均打点': stats.平均打点 || 0,
    '平均铳点': stats.平均铳点 || 0,
    '最大连庄': stats.最大连庄 || 0,
    '和了巡数': stats.和了巡数 || 0,
    '流局率': stats.流局率 || 0,
    '一发率': stats.一发率 || 0,
    '里宝率': stats.里宝率 || 0,
    '先制率': stats.先制率 || 0,
    'W立直': stats.W立直 || 0,
    '役满': stats.役满 || 0,
  };
});

// 格式化统计值
const formatStatValue = (key: string, value: number | undefined) => {
  const v = value ?? 0;
  if (key === '平均打点' || key === '平均铳点') {
    return v.toLocaleString();
  }
  if (key === '和了巡数') {
    return v.toFixed(1);
  }
  if (key === '最大连庄' || key === 'W立直' || key === '役满') {
    return v;
  }
  return v + '%';
};

// 计算四位率并显示所有顺位率
const rankRatesDisplay = computed(() => {
  if (!playerData.value?.stats?.rank_rates) return [0, 0, 0, 0];
  const rates = playerData.value.stats.rank_rates;
  // 计算四位率: 100 - 1位 - 2位 - 3位
  const fourthRate = Math.max(0, 100 - (rates[0] || 0) - (rates[1] || 0) - (rates[2] || 0));
  return [...rates.slice(0, 3), fourthRate];
});

// 初始化饼图
const initRankChart = () => {
  if (!rankChartRef.value || !playerData.value) return;
  
  if (rankChart) {
    rankChart.dispose();
  }
  
  rankChart = echarts.init(rankChartRef.value);
  
  const data = [
    { value: rankRatesDisplay.value[0], name: '1位', itemStyle: { color: '#e6a23c' } },
    { value: rankRatesDisplay.value[1], name: '2位', itemStyle: { color: '#67c23a' } },
    { value: rankRatesDisplay.value[2], name: '3位', itemStyle: { color: '#409eff' } },
    { value: rankRatesDisplay.value[3], name: '4位', itemStyle: { color: '#909399' } },
  ];
  
  const option = {
    tooltip: {
      trigger: 'item',
      formatter: '{b}: {c}%'
    },
    series: [
      {
        type: 'pie',
        radius: ['40%', '70%'],
        avoidLabelOverlap: false,
        itemStyle: {
          borderRadius: 4,
          borderColor: '#fff',
          borderWidth: 2
        },
        label: {
          show: false
        },
        emphasis: {
          label: {
            show: true,
            fontSize: 14,
            fontWeight: 'bold'
          }
        },
        labelLine: {
          show: false
        },
        data: data
      }
    ]
  };
  
  rankChart.setOption(option);
};

// 返回列表
const goBack = () => {
  router.push('/');
};

// 获取玩家详情
const fetchPlayerDetails = async () => {
  loading.value = true;
  try {
    const response = await accountApi.getAccountDetails(playerId.value);
    playerData.value = response.data;
  } catch (error: any) {
    const msg = error.response?.data?.detail || '获取详情失败';
    ElMessage.error(msg);
  } finally {
    loading.value = false;
  }
};

// 获取账号基本信息
const fetchAccountInfo = async () => {
  try {
    const response = await accountApi.getAccounts();
    account.value = response.data.find(a => a.id === playerId.value) || null;
  } catch (error) {
    console.error('获取账号信息失败', error);
  }
};

onMounted(() => {
  fetchAccountInfo();
  fetchPlayerDetails();
});

// 监听数据变化，初始化图表
watch(() => playerData.value, (newData) => {
  if (newData && !loading.value) {
    nextTick(() => {
      initRankChart();
    });
  }
}, { deep: true });

// 窗口大小变化时重新渲染图表
window.addEventListener('resize', () => {
  rankChart?.resize();
});
</script>

<style scoped>
.player-detail {
  padding: 20px;
  max-width: 1200px;
  margin: 0 auto;
}

.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
}

.header h2 {
  margin: 0;
  font-size: 20px;
  color: #303133;
}

.placeholder {
  width: 80px;
}

.loading {
  padding: 40px;
}

.content {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.info-card {
  margin-bottom: 8px;
}

.player-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.player-info h3 {
  margin: 0 0 8px 0;
  font-size: 24px;
  color: #303133;
}

.player-id {
  margin: 0;
  color: #909399;
  font-size: 14px;
}

.player-ranks {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.rank-display {
  display: flex;
  align-items: center;
  gap: 8px;
}

.rank-display .label {
  font-size: 14px;
  color: #606266;
}

.stats-row {
  margin-bottom: 8px;
}

.stat-card {
  text-align: center;
  padding: 20px;
}

.stat-value {
  font-size: 32px;
  font-weight: 600;
  color: #409eff;
  margin-bottom: 8px;
}

.stat-label {
  font-size: 14px;
  color: #606266;
}

.recent-card,
.matches-card {
  margin-bottom: 8px;
}

.matches-table :deep(.el-table__header) th {
  text-align: center !important;
}

.matches-table :deep(.el-table__cell) {
  text-align: center !important;
}

.card-header {
  font-weight: 600;
  color: #303133;
}

.recent-matches {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  padding: 10px 0;
}

.match-rank {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 36px;
  height: 36px;
  border-radius: 50%;
  font-weight: 600;
  font-size: 16px;
}

.rank-1 {
  background: linear-gradient(135deg, #ffd700, #ffed4a);
  color: #8b6914;
}

.rank-2 {
  background: linear-gradient(135deg, #c0c0c0, #e8e8e8);
  color: #666;
}

.rank-3 {
  background: linear-gradient(135deg, #cd7f32, #daa520);
  color: white;
}

.rank-4 {
  background-color: #f4f4f5;
  color: #909399;
}

.no-data {
  color: #909399;
  font-size: 14px;
}

.rank-text-1 {
  color: #e6a23c;
  font-weight: 600;
}

.rank-text-2 {
  color: #67c23a;
  font-weight: 600;
}

.rank-text-3 {
  color: #409eff;
  font-weight: 600;
}

.rank-text-4 {
  color: #909399;
}

.positive {
  color: #67c23a;
  font-weight: 600;
}

.negative {
  color: #f56c6c;
  font-weight: 600;
}

/* 分数卡片 */
.score-card {
  padding: 16px;
}

.score-item {
  margin-bottom: 16px;
}

.score-item:last-child {
  margin-bottom: 0;
}

.score-item .label {
  font-size: 14px;
  color: #606266;
  margin-right: 8px;
}

.score-item .value {
  font-size: 18px;
  font-weight: 600;
  color: #409eff;
}

.score-item .value.highest {
  color: #e6a23c;
}

/* 顺位分布 */
.rank-rate-card {
  padding: 16px;
}

.rank-rate-title {
  font-size: 14px;
  color: #606266;
  margin-bottom: 12px;
}

.rank-chart {
  height: 200px;
  margin-bottom: 16px;
}

.rank-legend {
  display: flex;
  justify-content: center;
  gap: 16px;
  flex-wrap: wrap;
}

.legend-item {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  color: #606266;
}

.legend-item .dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
}

/* 详细统计 */
.extended-stats-card {
  margin-bottom: 8px;
}

.extended-stat-item {
  text-align: center;
  padding: 16px 8px;
  border-radius: 8px;
  background-color: #f5f7fa;
  margin-bottom: 16px;
}

.stat-name {
  font-size: 13px;
  color: #606266;
  margin-bottom: 8px;
}

.stat-value-small {
  font-size: 18px;
  font-weight: 600;
  color: #409eff;
}
</style>
