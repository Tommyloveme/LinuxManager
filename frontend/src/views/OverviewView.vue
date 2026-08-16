<template>
  <div v-if="data" class="wrap">
    <div class="hero card">
      <div>
        <p class="kicker">{{ data.os }}</p>
        <h2>{{ data.host }}</h2>
        <p class="muted">{{ data.arch }} · Cedar {{ data.app.version }}</p>
      </div>
      <div class="chips">
        <span>{{ data.resources.process_count }} 个进程</span>
        <span>{{ data.resources.cpu_count }} 核</span>
        <span v-for="n in data.networks.slice(0, 2)" :key="n.iface">{{ n.ipv4[0] }}</span>
      </div>
    </div>
    <div class="grid">
      <article class="card">
        <h3>CPU</h3>
        <Meter :value="data.resources.cpu_percent" />
        <p class="muted">负载 {{ data.resources.loadavg.join(" / ") }}</p>
      </article>
      <article class="card">
        <h3>内存</h3>
        <Meter :value="data.resources.memory.percent" />
        <p class="muted">{{ fmt(data.resources.memory.used) }} / {{ fmt(data.resources.memory.total) }}</p>
      </article>
      <article class="card">
        <h3>磁盘</h3>
        <Meter :value="data.resources.disk.percent" />
        <p class="muted">剩余 {{ fmt(data.resources.disk.free) }}</p>
      </article>
    </div>
    <div class="card">
      <h3>能力</h3>
      <div class="mods">
        <div v-for="m in data.app.modules" :key="m.key">
          <strong>{{ m.title }}</strong>
          <span>{{ m.description }}</span>
        </div>
      </div>
    </div>
  </div>
  <p v-else-if="error" class="err">{{ error }}</p>
</template>

<script setup lang="ts">
import { onMounted, ref } from "vue";
import { api } from "@/api/client";
import Meter from "@/components/Meter.vue";

const data = ref<any>(null);
const error = ref("");

function fmt(n: number) {
  if (n > 1024 ** 3) return `${(n / 1024 ** 3).toFixed(1)} GiB`;
  if (n > 1024 ** 2) return `${(n / 1024 ** 2).toFixed(0)} MiB`;
  return `${n} B`;
}

onMounted(async () => {
  try {
    data.value = await api.get("/system/overview");
  } catch (err) {
    error.value = err instanceof Error ? err.message : "加载失败";
  }
});
</script>

<style scoped>
.wrap { display: flex; flex-direction: column; gap: 18px; }
.card {
  background: var(--card);
  border: 1px solid var(--line);
  border-radius: var(--radius);
  padding: 20px 22px;
}
.hero { display: flex; justify-content: space-between; align-items: end; gap: 16px; }
.kicker { color: var(--muted); letter-spacing: 0.08em; text-transform: uppercase; font-size: 11px; margin: 0 0 6px; }
h2 { font-family: var(--serif); font-size: 32px; margin: 0; font-weight: 500; }
h3 { margin: 0 0 12px; font-size: 15px; }
.muted { color: var(--muted); }
.chips { display: flex; gap: 8px; flex-wrap: wrap; }
.chips span {
  border: 1px solid var(--line);
  border-radius: 999px;
  padding: 4px 10px;
  font-size: 12px;
}
.grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px; }
.mods { display: grid; grid-template-columns: repeat(2, 1fr); gap: 14px 24px; }
.mods div { display: flex; flex-direction: column; gap: 4px; }
.mods span { color: var(--muted); font-size: 13px; }
.err { color: var(--danger); }
@media (max-width: 900px) {
  .grid, .mods, .hero { display: block; }
}
</style>
