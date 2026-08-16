<template>
  <div class="layout">
    <aside class="card">
      <div class="row">
        <h3>批处理</h3>
        <button @click="create">新建</button>
      </div>
      <button v-for="p in items" :key="p.id" class="item" :class="{ on: current?.id === p.id }" @click="open(p)">
        <strong>{{ p.name }}</strong>
        <span>{{ p.steps.length }} 步 · {{ p.tags }}</span>
      </button>
    </aside>
    <section class="card" v-if="current">
      <div class="row">
        <input v-model="current.name" class="title" />
        <label class="chk"><input type="checkbox" v-model="current.stop_on_error" /> 出错即停</label>
        <button class="primary" @click="save">保存</button>
        <button @click="run" :disabled="running">{{ running ? "执行中…" : "运行" }}</button>
        <button @click="remove">删除</button>
      </div>
      <textarea v-model="current.description" rows="2" placeholder="说明：这组操作解决什么问题" />
      <div v-for="(step, i) in current.steps" :key="i" class="step">
        <header>
          <b>{{ i + 1 }}</b>
          <input v-model="step.name" />
          <select v-model="step.kind">
            <option>command</option>
            <option>script</option>
            <option>archive</option>
            <option>sync</option>
            <option>process</option>
            <option>service</option>
            <option>wait</option>
          </select>
          <select v-model="step.on_error">
            <option value="stop">失败则停止</option>
            <option value="continue">失败继续</option>
          </select>
          <button @click="current.steps.splice(i, 1)">移除</button>
        </header>
        <textarea v-model="step.payloadText" class="code" spellcheck="false" />
      </div>
      <button @click="addStep">增加步骤</button>
      <pre v-if="log" class="out">{{ log }}</pre>
    </section>
    <aside class="card">
      <h3>最近运行</h3>
      <div v-for="r in runs" :key="r.id" class="run">
        <strong>{{ r.playbook_name }}</strong>
        <span :class="r.status">{{ r.status }}</span>
        <pre>{{ r.log.slice(-400) }}</pre>
      </div>
    </aside>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from "vue";
import { api } from "@/api/client";

const items = ref<any[]>([]);
const current = ref<any>(null);
const runs = ref<any[]>([]);
const log = ref("");
const running = ref(false);

function encode(p: any) {
  return {
    ...p,
    steps: p.steps.map((s: any) => ({
      ...s,
      payloadText: JSON.stringify(s.payload || {}, null, 2),
    })),
  };
}

function decode(p: any) {
  return {
    name: p.name,
    description: p.description,
    tags: p.tags,
    stop_on_error: p.stop_on_error,
    steps: p.steps.map((s: any, i: number) => ({
      name: s.name,
      kind: s.kind,
      on_error: s.on_error,
      ord: i,
      payload: JSON.parse(s.payloadText || "{}"),
    })),
  };
}

async function load() {
  items.value = (await api.get("/playbooks")).items;
  runs.value = (await api.get("/playbooks/runs")).items;
}

function open(p: any) {
  current.value = encode(JSON.parse(JSON.stringify(p)));
  log.value = "";
}

function create() {
  current.value = encode({
    id: null,
    name: "新批处理",
    description: "",
    tags: "",
    stop_on_error: true,
    steps: [{ name: "执行命令", kind: "command", on_error: "stop", payload: { command: "uname -a" } }],
  });
}

function addStep() {
  current.value.steps.push({
    name: "新步骤",
    kind: "command",
    on_error: "stop",
    payloadText: JSON.stringify({ command: "true" }, null, 2),
  });
}

async function save() {
  const body = decode(current.value);
  if (current.value.id) current.value = encode(await api.patch(`/playbooks/${current.value.id}`, body));
  else current.value = encode(await api.post("/playbooks", body));
  await load();
}

async function run() {
  if (!current.value.id) await save();
  running.value = true;
  try {
    const result = await api.post(`/playbooks/${current.value.id}/run`);
    log.value = result.log;
    await load();
  } finally {
    running.value = false;
  }
}

async function remove() {
  if (!current.value?.id) return;
  await api.del(`/playbooks/${current.value.id}`);
  current.value = null;
  await load();
}

onMounted(load);
</script>

<style scoped>
.layout { display: grid; grid-template-columns: 220px 1fr 260px; gap: 16px; }
.card { background: var(--card); border: 1px solid var(--line); border-radius: var(--radius); padding: 16px; }
.row { display: flex; gap: 8px; align-items: center; margin-bottom: 10px; }
input, textarea, select, button { border: 1px solid var(--line); border-radius: 8px; padding: 8px; background: #fff; }
.primary { background: var(--accent); color: #fff; border-color: var(--accent); }
.title { flex: 1; font-family: var(--serif); font-size: 18px; }
.item { display: flex; flex-direction: column; width: 100%; margin-top: 8px; align-items: flex-start; background: transparent; }
.item.on { background: #f3ead4; }
.item span, .chk { color: var(--muted); font-size: 12px; }
.step { border: 1px dashed var(--line); border-radius: 10px; padding: 10px; margin: 10px 0; }
.step header { display: grid; grid-template-columns: 24px 1fr 110px 120px 64px; gap: 6px; margin-bottom: 8px; align-items: center; }
.code { width: 100%; min-height: 90px; font-family: var(--mono); font-size: 12px; }
.out, .run pre { background: #171411; color: #e8dcc8; padding: 12px; border-radius: 8px; overflow: auto; }
.run { margin-bottom: 14px; }
.run span { font-size: 12px; }
.ok { color: var(--ok); }
.failed { color: var(--danger); }
@media (max-width: 1100px) { .layout { grid-template-columns: 1fr; } }
</style>
