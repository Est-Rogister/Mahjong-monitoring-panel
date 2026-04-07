<template>
  <span class="rank-badge" :class="rankClass">
    {{ displayRank }}
  </span>
</template>

<script setup lang="ts">
import { computed } from 'vue';

const props = defineProps<{
  rank: string | null;
}>();

const displayRank = computed(() => {
  return props.rank || '未知';
});

const rankClass = computed(() => {
  if (!props.rank) return 'rank-unknown';
  
  const rank = props.rank;
  if (rank.includes('魂天')) return 'rank-celestial';
  if (rank.includes('圣')) return 'rank-saint';
  if (rank.includes('豪')) return 'rank-master';
  if (rank.includes('杰')) return 'rank-expert';
  if (rank.includes('士')) return 'rank-advanced';
  if (rank.includes('心')) return 'rank-beginner';
  
  return 'rank-unknown';
});
</script>

<style scoped>
.rank-badge {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 12px;
  font-weight: 600;
}

.rank-celestial {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
}

.rank-saint {
  background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
  color: white;
}

.rank-master {
  background: linear-gradient(135deg, #fa709a 0%, #fee140 100%);
  color: white;
}

.rank-expert {
  background: linear-gradient(135deg, #30cfd0 0%, #330867 100%);
  color: white;
}

.rank-advanced {
  background: linear-gradient(135deg, #a8edea 0%, #fed6e3 100%);
  color: #333;
}

.rank-beginner {
  background: linear-gradient(135deg, #d299c2 0%, #fef9d7 100%);
  color: #333;
}

.rank-unknown {
  background-color: #e4e7ed;
  color: #909399;
}
</style>
