<template>
  <div class="card">
    <table>
      <thead><tr><th>ID</th><th>类型</th><th>标题</th><th>状态</th><th>产物</th><th>时间</th></tr></thead>
      <tbody>
        <tr v-for="j in items" :key="j.id">
          <td>{{ j.id }}</td>
          <td>{{ j.kind }}</td>
          <td>{{ j.title }}</td>
          <td :class="j.status">{{ j.status }}</td>
          <td class="mono">
            <a v-if="j.artifact_path" :href="`/api/v1/files/download?path=${encodeURIComponent(j.artifact_path)}&token=${token}`">下载</a>
          </td>
          <td class="mono">{{ j.created_at?.slice(0, 19) }}</td>
        </tr>
      </tbody>
    </table>
    <p v-if="!items.length" class="muted">还没有后台作业。打包文件后会在这里留下记录。</p>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from "vue";
import { api, getToken } from "@/api/client";

const items = ref<any[]>([]);
const token = getToken();
onMounted(async () => {
  items.value = (await api.get("/jobs")).items;
});
</script>

<style scoped>
.card { background: var(--card); border: 1px solid var(--line); border-radius: var(--radius); padding: 16px; }
table { width: 100%; border-collapse: collapse; }
th, td { text-align: left; padding: 8px; border-bottom: 1px solid var(--line); }
.mono { font-family: var(--mono); font-size: 12px; }
.ok { color: var(--ok); }
.failed { color: var(--danger); }
.muted { color: var(--muted); }
</style>
