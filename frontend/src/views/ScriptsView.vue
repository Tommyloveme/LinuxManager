<template>
  <div class="layout">
    <aside class="list card">
      <div class="row">
        <h3>脚本</h3>
        <button @click="create">新建</button>
      </div>
      <input v-model="q" placeholder="搜索" />
      <button
        v-for="s in filtered"
        :key="s.id"
        class="item"
        :class="{ on: current?.id === s.id }"
        @click="open(s)"
      >
        <strong>{{ s.name }}</strong>
        <span>{{ s.tags || s.interpreter }}</span>
      </button>
    </aside>
    <section class="card editor" v-if="current">
      <div class="row">
        <input v-model="current.name" class="title" />
        <button class="primary" @click="save">保存</button>
        <button @click="run">运行</button>
        <button @click="remove">删除</button>
      </div>
      <div class="meta">
        <input v-model="current.interpreter" />
        <input v-model="current.tags" placeholder="标签" />
        <input v-model.number="current.timeout_sec" type="number" />
      </div>
      <textarea v-model="current.description" rows="2" placeholder="说明" />
      <textarea v-model="current.content" class="code" spellcheck="false" />
      <div class="row">
        <button class="primary" :disabled="!selected.length" @click="batch">批量执行勾选</button>
        <span class="muted">勾选左侧多个脚本后点这里。当前勾选 {{ selected.length }} 个。</span>
      </div>
      <pre v-if="output" class="out">{{ output }}</pre>
    </section>
    <aside class="card checks">
      <h3>批量勾选</h3>
      <label v-for="s in items" :key="s.id">
        <input type="checkbox" :value="s.id" v-model="selected" />
        {{ s.name }}
      </label>
    </aside>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { api } from "@/api/client";

const items = ref<any[]>([]);
const current = ref<any>(null);
const q = ref("");
const selected = ref<number[]>([]);
const output = ref("");

const filtered = computed(() => items.value.filter((s) => s.name.includes(q.value) || s.tags.includes(q.value)));

async function load() {
  items.value = (await api.get("/scripts")).items;
  if (!current.value && items.value[0]) current.value = { ...items.value[0] };
}

function open(s: any) {
  current.value = { ...s };
  output.value = "";
}

function create() {
  current.value = {
    id: null,
    name: "未命名脚本",
    description: "",
    interpreter: "/bin/bash",
    content: "#!/bin/bash\nset -euo pipefail\n\n",
    tags: "",
    timeout_sec: 120,
  };
}

async function save() {
  if (current.value.id) {
    current.value = await api.patch(`/scripts/${current.value.id}`, current.value);
  } else {
    current.value = await api.post("/scripts", current.value);
  }
  await load();
}

async function run() {
  if (!current.value.id) await save();
  const result = await api.post(`/scripts/${current.value.id}/run`);
  output.value = `exit ${result.exit_code}\n${result.stdout}\n${result.stderr}`;
}

async function batch() {
  const result = await api.post("/scripts/batch", { script_ids: selected.value, stop_on_error: true });
  output.value = result.items.map((r: any) => `# ${r.script_name} exit ${r.exit_code}\n${r.stdout}${r.stderr}`).join("\n\n");
}

async function remove() {
  if (!current.value?.id) return;
  await api.del(`/scripts/${current.value.id}`);
  current.value = null;
  await load();
}

onMounted(load);
</script>

<style scoped>
.layout { display: grid; grid-template-columns: 240px 1fr 200px; gap: 16px; align-items: start; }
.card { background: var(--card); border: 1px solid var(--line); border-radius: var(--radius); padding: 16px; }
.row { display: flex; gap: 8px; align-items: center; margin-bottom: 10px; }
h3 { margin: 0; flex: 1; }
input, textarea, button { border: 1px solid var(--line); border-radius: 8px; padding: 8px; background: #fff; }
.primary { background: var(--accent); color: #fff; border-color: var(--accent); }
.item {
  display: flex; flex-direction: column; align-items: flex-start; width: 100%;
  margin-top: 6px; background: transparent;
}
.item.on { background: #f3ead4; }
.item span { color: var(--muted); font-size: 12px; }
.title { flex: 1; font-family: var(--serif); font-size: 18px; }
.meta { display: grid; grid-template-columns: 1fr 1fr 90px; gap: 8px; margin-bottom: 8px; }
.code { width: 100%; min-height: 320px; font-family: var(--mono); font-size: 13px; line-height: 1.5; }
.out { background: #171411; color: #e8dcc8; padding: 14px; border-radius: 10px; overflow: auto; max-height: 280px; }
.checks label { display: flex; gap: 8px; margin: 8px 0; font-size: 13px; }
.muted { color: var(--muted); font-size: 12px; }
@media (max-width: 1100px) { .layout { grid-template-columns: 1fr; } }
</style>
