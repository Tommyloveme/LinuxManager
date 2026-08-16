<template>
  <div class="card">
    <div class="row">
      <input v-model="q" placeholder="过滤单元名" @keydown.enter="load" />
      <button @click="load">刷新</button>
    </div>
    <p v-if="!items.length" class="muted">当前主机没有 systemctl，或无权列出服务。SUSE 上以具备权限的身份运行 Cedar 即可管理单元。</p>
    <table v-else>
      <thead><tr><th>单元</th><th>load</th><th>active</th><th>sub</th><th>说明</th><th></th></tr></thead>
      <tbody>
        <tr v-for="u in items" :key="u.name">
          <td class="mono">{{ u.name }}</td>
          <td>{{ u.load }}</td>
          <td>{{ u.active }}</td>
          <td>{{ u.sub }}</td>
          <td>{{ u.description }}</td>
          <td class="acts">
            <button @click="act(u.name, 'start')">启动</button>
            <button @click="act(u.name, 'stop')">停止</button>
            <button @click="act(u.name, 'restart')">重启</button>
            <button @click="act(u.name, 'status')">状态</button>
          </td>
        </tr>
      </tbody>
    </table>
    <pre v-if="output" class="out">{{ output }}</pre>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from "vue";
import { api } from "@/api/client";

const items = ref<any[]>([]);
const q = ref("");
const output = ref("");

async function load() {
  items.value = (await api.get(`/services?q=${encodeURIComponent(q.value)}`)).items;
}

async function act(unit: string, action: string) {
  const data = await api.post(`/services/${encodeURIComponent(unit)}/action`, { action });
  output.value = data.output;
  await load();
}

onMounted(load);
</script>

<style scoped>
.card { background: var(--card); border: 1px solid var(--line); border-radius: var(--radius); padding: 16px; }
.row { display: flex; gap: 8px; margin-bottom: 12px; }
input { flex: 1; border: 1px solid var(--line); border-radius: 8px; padding: 8px; }
button { border: 1px solid var(--line); border-radius: 8px; padding: 6px 10px; background: #fff; }
table { width: 100%; border-collapse: collapse; }
th, td { text-align: left; padding: 8px; border-bottom: 1px solid var(--line); font-size: 13px; }
.mono { font-family: var(--mono); font-size: 12px; }
.muted { color: var(--muted); }
.out { background: #171411; color: #e8dcc8; padding: 12px; max-height: 280px; overflow: auto; }
</style>
