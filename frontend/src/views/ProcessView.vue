<template>
  <div class="wrap">
    <div class="stats" v-if="summary">
      <article class="card"><h3>CPU</h3><Meter :value="summary.cpu_percent" /></article>
      <article class="card"><h3>内存</h3><Meter :value="summary.memory.percent" /></article>
      <article class="card"><h3>进程数</h3><b>{{ summary.process_count }}</b></article>
    </div>
    <div class="card">
      <div class="row">
        <input v-model="q" placeholder="过滤名称 / 命令 / 用户" @keydown.enter="load" />
        <button @click="load">刷新</button>
      </div>
      <table>
        <thead>
          <tr><th>PID</th><th>用户</th><th>CPU</th><th>RSS</th><th>状态</th><th>进程</th><th></th></tr>
        </thead>
        <tbody>
          <tr v-for="p in items" :key="p.pid">
            <td class="mono">{{ p.pid }}</td>
            <td>{{ p.user }}</td>
            <td>{{ p.cpu.toFixed(1) }}</td>
            <td class="mono">{{ (p.rss / 1024 / 1024).toFixed(0) }}M</td>
            <td>{{ p.status }}</td>
            <td>
              <strong>{{ p.name }}</strong>
              <div class="cmd">{{ p.cmdline }}</div>
            </td>
            <td><button class="danger" @click="kill(p.pid)">结束</button></td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from "vue";
import { api } from "@/api/client";
import Meter from "@/components/Meter.vue";

const items = ref<any[]>([]);
const summary = ref<any>(null);
const q = ref("");

async function load() {
  const data = await api.get(`/process?q=${encodeURIComponent(q.value)}`);
  items.value = data.items;
  summary.value = data.summary;
}

async function kill(pid: number) {
  if (!confirm(`向 ${pid} 发送 SIGTERM？`)) return;
  await api.post("/process/kill", { pid, signal: "TERM" });
  await load();
}

onMounted(load);
</script>

<style scoped>
.wrap { display: flex; flex-direction: column; gap: 16px; }
.stats { display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; }
.card { background: var(--card); border: 1px solid var(--line); border-radius: var(--radius); padding: 16px; }
.row { display: flex; gap: 8px; margin-bottom: 12px; }
input, button { border: 1px solid var(--line); border-radius: 8px; padding: 8px 12px; background: #fff; }
input { flex: 1; }
table { width: 100%; border-collapse: collapse; }
th, td { text-align: left; padding: 8px; border-bottom: 1px solid var(--line); vertical-align: top; font-size: 13px; }
.mono { font-family: var(--mono); }
.cmd { color: var(--muted); font-size: 12px; max-width: 520px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.danger { color: var(--danger); }
</style>
