<template>
  <div class="meter">
    <div class="bar"><i :style="{ width: Math.min(100, value) + '%' }" /></div>
    <b>{{ value.toFixed(1) }}%</b>
  </div>
</template>

<script setup lang="ts">
defineProps<{ value: number }>();
</script>

<style scoped>
.meter { display: flex; align-items: center; gap: 12px; }
.bar {
  flex: 1;
  height: 8px;
  background: #eadfca;
  border-radius: 99px;
  overflow: hidden;
}
i {
  display: block;
  height: 100%;
  background: var(--accent);
  border-radius: 99px;
}
b { font-variant-numeric: tabular-nums; width: 56px; text-align: right; }
</style>
