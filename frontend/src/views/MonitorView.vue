<template>
  <div class="wrap">
    <div class="tabs">
      <button :class="{ on: tab === 'process' }" @click="tab = 'process'">进程</button>
      <button :class="{ on: tab === 'services' }" @click="tab = 'services'">服务 (systemd)</button>
      <div class="spacer"></div>
      <label class="chk">
        <input type="checkbox" v-model="autoRefresh" @change="toggleAuto" /> 实时刷新
      </label>
      <select v-model.number="interval" @change="toggleAuto" class="interval">
        <option :value="2">2s</option>
        <option :value="3">3s</option>
        <option :value="5">5s</option>
        <option :value="10">10s</option>
      </select>
      <button @click="refresh">刷新</button>
    </div>

    <!-- 进程 -->
    <template v-if="tab === 'process'">
      <div class="stats" v-if="summary">
        <article class="card stat"><h4>CPU</h4><Meter :value="summary.cpu_percent" /><span class="mono">{{ summary.cpu_count }} 核 · 负载 {{ summary.loadavg.join(" / ") }}</span></article>
        <article class="card stat"><h4>内存</h4><Meter :value="summary.memory.percent" /><span class="mono">{{ mib(summary.memory.used) }} / {{ mib(summary.memory.total) }}</span></article>
        <article class="card stat"><h4>磁盘</h4><Meter :value="summary.disk.percent" /><span class="mono">剩余 {{ gib(summary.disk.free) }}</span></article>
        <article class="card stat"><h4>进程</h4><b class="big">{{ summary.process_count }}</b></article>
      </div>
      <div class="card">
        <div class="row">
          <input v-model="pq" placeholder="过滤名称 / 命令 / 用户" @keydown.enter="loadProcess" />
          <button @click="loadProcess">查询</button>
          <span v-if="autoRefresh" class="live">● 实时</span>
        </div>
        <table>
          <thead>
            <tr><th @click="sortBy('cpu')" class="sortable">CPU%</th><th @click="sortBy('rss')" class="sortable">内存</th><th>PID</th><th>用户</th><th>状态</th><th>进程</th><th></th></tr>
          </thead>
          <tbody>
            <tr v-for="p in procItems" :key="p.pid">
              <td class="mono">{{ p.cpu.toFixed(1) }}</td>
              <td class="mono">{{ (p.rss / 1024 / 1024).toFixed(0) }}M</td>
              <td class="mono">{{ p.pid }}</td>
              <td>{{ p.user }}</td>
              <td>{{ p.status }}</td>
              <td><strong>{{ p.name }}</strong><div class="cmd">{{ p.cmdline }}</div></td>
              <td>
                <button class="mini" @click="kill(p.pid, 'TERM')">结束</button>
                <button class="mini danger" @click="kill(p.pid, 'KILL')">强杀</button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </template>

    <!-- 服务 -->
    <template v-else>
      <div class="card">
        <div class="row">
          <input v-model="sq" placeholder="过滤单元名或说明" @keydown.enter="loadServices" />
          <button @click="loadServices">查询</button>
          <span v-if="autoRefresh" class="live">● 实时</span>
        </div>
        <p v-if="!svcItems.length" class="muted">当前主机没有 systemctl，或无权列出服务。以具备权限的身份运行即可管理单元。</p>
        <table v-else>
          <thead><tr><th>单元</th><th>状态</th><th>子状态</th><th>说明</th><th class="acts-h">操作</th></tr></thead>
          <tbody>
            <tr v-for="u in svcItems" :key="u.name">
              <td class="mono">{{ u.name }}</td>
              <td><span class="dot" :class="u.active === 'active' ? 'on' : 'off'"></span>{{ u.active }}</td>
              <td>{{ u.sub }}</td>
              <td class="desc">{{ u.description }}</td>
              <td class="acts">
                <button class="mini" @click="act(u.name, 'start')">启动</button>
                <button class="mini" @click="act(u.name, 'stop')">停止</button>
                <button class="mini" @click="act(u.name, 'restart')">重启</button>
                <button class="mini" @click="act(u.name, 'status')">状态</button>
              </td>
            </tr>
          </tbody>
        </table>
        <pre v-if="svcOutput" class="out">{{ svcOutput }}</pre>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref } from "vue";
import { api } from "@/api/client";
import Meter from "@/components/Meter.vue";

const tab = ref<"process" | "services">("process");
const autoRefresh = ref(false);
const interval = ref(3);
let timer: number | null = null;

const procItems = ref<any[]>([]);
const summary = ref<any>(null);
const pq = ref("");
const sortKey = ref<"cpu" | "rss">("cpu");

const svcItems = ref<any[]>([]);
const sq = ref("");
const svcOutput = ref("");

const mib = (n: number) => `${(n / 1024 ** 2).toFixed(0)} MiB`;
const gib = (n: number) => `${(n / 1024 ** 3).toFixed(1)} GiB`;

function sortBy(key: "cpu" | "rss") {
  sortKey.value = key;
  procItems.value = [...procItems.value].sort((a, b) => b[key] - a[key]);
}

async function loadProcess() {
  const data = await api.get(`/process?q=${encodeURIComponent(pq.value)}`);
  procItems.value = [...data.items].sort((a, b) => b[sortKey.value] - a[sortKey.value]);
  summary.value = data.summary;
}

async function loadServices() {
  svcItems.value = (await api.get(`/services?q=${encodeURIComponent(sq.value)}`)).items;
}

async function kill(pid: number, signal: string) {
  if (!confirm(`向进程 ${pid} 发送 SIG${signal}？`)) return;
  await api.post("/process/kill", { pid, signal });
  await loadProcess();
}

async function act(unit: string, action: string) {
  const data = await api.post(`/services/${encodeURIComponent(unit)}/action`, { action });
  svcOutput.value = `# ${unit} ${action}\n${data.output}`;
  await loadServices();
}

function refresh() {
  tab.value === "process" ? loadProcess() : loadServices();
}

function toggleAuto() {
  if (timer) { clearInterval(timer); timer = null; }
  if (autoRefresh.value) {
    timer = window.setInterval(refresh, interval.value * 1000);
  }
}

onMounted(() => {
  loadProcess();
  loadServices();
});
onBeforeUnmount(() => { if (timer) clearInterval(timer); });
</script>

<style scoped>
.wrap { display: flex; flex-direction: column; gap: 16px; }
.card { background: var(--card); border: 1px solid var(--line); border-radius: var(--radius); padding: 16px; }
.tabs { display: flex; gap: 8px; align-items: center; }
.tabs > button { border: 1px solid var(--line); border-radius: 8px; padding: 8px 16px; background: var(--card); }
.tabs > button.on { background: var(--sidebar); color: #fff; border-color: var(--sidebar); }
.spacer { flex: 1; }
.chk { display: flex; gap: 6px; align-items: center; color: var(--muted); font-size: 13px; }
.interval { border: 1px solid var(--line); border-radius: 8px; padding: 7px; background: #fff; }
.stats { display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; }
.stat h4 { margin: 0 0 8px; font-size: 13px; color: var(--muted); }
.stat .mono { font-size: 11px; color: var(--muted); }
.big { font-size: 30px; font-family: var(--serif); }
.row { display: flex; gap: 8px; margin-bottom: 12px; align-items: center; }
.row input { flex: 1; }
input, button, select { border: 1px solid var(--line); border-radius: 8px; padding: 8px 12px; background: #fff; }
.live { color: var(--ok); font-size: 12px; }
table { width: 100%; border-collapse: collapse; }
th, td { text-align: left; padding: 8px; border-bottom: 1px solid var(--line); vertical-align: top; font-size: 13px; }
.sortable { cursor: pointer; user-select: none; }
.sortable:hover { color: var(--accent); }
.mono { font-family: var(--mono); font-size: 12px; }
.cmd { color: var(--muted); font-size: 12px; max-width: 460px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.mini { padding: 4px 10px; font-size: 12px; margin-right: 4px; }
.danger { color: var(--danger); }
.desc { color: var(--muted); max-width: 320px; }
.acts-h { width: 220px; }
.acts { white-space: nowrap; }
.dot { display: inline-block; width: 8px; height: 8px; border-radius: 50%; margin-right: 6px; }
.dot.on { background: var(--ok); }
.dot.off { background: #bbb; }
.out { background: #171411; color: #e8dcc8; padding: 12px; max-height: 260px; overflow: auto; margin-top: 12px; white-space: pre-wrap; }
.muted { color: var(--muted); }
@media (max-width: 900px) { .stats { grid-template-columns: repeat(2, 1fr); } }
</style>
