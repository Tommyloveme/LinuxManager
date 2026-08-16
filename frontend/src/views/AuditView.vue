<template>
  <div class="card">
    <table>
      <thead>
        <tr><th>时间</th><th>操作者</th><th>Linux 用户</th><th>动作</th><th>对象</th><th>结果</th></tr>
      </thead>
      <tbody>
        <tr v-for="row in items" :key="row.id">
          <td class="mono">{{ row.created_at?.slice(0, 19) }}</td>
          <td>{{ row.actor }}</td>
          <td>{{ row.linux_user }}</td>
          <td>{{ row.action }}</td>
          <td>{{ row.target }}</td>
          <td :class="{ ok: row.ok, failed: !row.ok }">{{ row.ok ? "成功" : "失败" }}</td>
        </tr>
      </tbody>
    </table>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from "vue";
import { api } from "@/api/client";

const items = ref<any[]>([]);
onMounted(async () => {
  items.value = (await api.get("/audit")).items;
});
</script>

<style scoped>
.card { background: var(--card); border: 1px solid var(--line); border-radius: var(--radius); padding: 16px; }
table { width: 100%; border-collapse: collapse; }
th, td { text-align: left; padding: 8px; border-bottom: 1px solid var(--line); font-size: 13px; }
.mono { font-family: var(--mono); font-size: 12px; }
.ok { color: var(--ok); }
.failed { color: var(--danger); }
</style>
