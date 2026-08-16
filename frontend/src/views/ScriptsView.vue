<template>
  <div class="layout">
    <aside class="list card">
      <div class="row">
        <h3>脚本库</h3>
        <button @click="create">新建</button>
      </div>
      <input v-model="q" placeholder="搜索名称或标签" class="search" />

      <div class="list-head">
        <label class="chk">
          <input type="checkbox" :checked="allChecked" @change="toggleAll" /> 全选
        </label>
        <span class="muted">已选 {{ selected.length }}</span>
      </div>

      <div class="items">
        <div
          v-for="s in filtered"
          :key="s.id"
          class="item"
          :class="{ on: current && current.id === s.id }"
        >
          <input type="checkbox" :value="s.id" v-model="selected" @click.stop />
          <button class="item-main" @click="open(s)">
            <strong>{{ s.name }}</strong>
            <span>{{ s.tags || s.interpreter }}</span>
          </button>
        </div>
        <p v-if="!filtered.length" class="muted empty">没有匹配的脚本</p>
      </div>

      <div class="batch">
        <label class="chk"><input type="checkbox" v-model="stopOnError" /> 失败即停止</label>
        <button class="primary" :disabled="!selected.length || running" @click="batch">
          {{ running ? "执行中…" : `批量执行选中 (${selected.length})` }}
        </button>
      </div>
    </aside>

    <section class="card editor" v-if="current">
      <div class="row">
        <input v-model="current.name" class="title" />
        <button class="primary" @click="save">保存</button>
        <button @click="run" :disabled="running">运行</button>
        <button class="danger" @click="remove">删除</button>
      </div>
      <div class="meta">
        <input v-model="current.interpreter" placeholder="解释器" />
        <input v-model="current.tags" placeholder="标签，逗号分隔" />
        <input v-model.number="current.timeout_sec" type="number" placeholder="超时(秒)" />
      </div>
      <textarea v-model="current.description" rows="2" placeholder="说明" />
      <textarea v-model="current.content" class="code" spellcheck="false" />
      <pre v-if="output" class="out">{{ output }}</pre>
    </section>
    <section class="card placeholder" v-else>
      <p class="muted">从左侧选择脚本进行编辑，或点击「新建」。批量执行会按列表顺序运行所有勾选的脚本。</p>
    </section>
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
const running = ref(false);
const stopOnError = ref(true);

const filtered = computed(() =>
  items.value.filter((s) => s.name.includes(q.value) || (s.tags || "").includes(q.value))
);
const allChecked = computed(
  () => filtered.value.length > 0 && filtered.value.every((s) => selected.value.includes(s.id))
);

function toggleAll() {
  if (allChecked.value) {
    const ids = filtered.value.map((s) => s.id);
    selected.value = selected.value.filter((id) => !ids.includes(id));
  } else {
    const ids = new Set(selected.value);
    filtered.value.forEach((s) => ids.add(s.id));
    selected.value = [...ids];
  }
}

async function load() {
  items.value = (await api.get("/scripts")).items;
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
  output.value = "";
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
  running.value = true;
  output.value = "";
  try {
    if (!current.value.id) await save();
    const result = await api.post(`/scripts/${current.value.id}/run`);
    output.value = `# ${current.value.name} · exit ${result.exit_code}\n${result.stdout}${result.stderr}`;
  } catch (err) {
    output.value = err instanceof Error ? err.message : "运行失败";
  } finally {
    running.value = false;
  }
}

async function batch() {
  running.value = true;
  output.value = "";
  try {
    const result = await api.post("/scripts/batch", {
      script_ids: selected.value,
      stop_on_error: stopOnError.value,
    });
    output.value = result.items
      .map((r: any) => `# ${r.script_name} · exit ${r.exit_code}\n${r.stdout}${r.stderr}`)
      .join("\n\n");
  } catch (err) {
    output.value = err instanceof Error ? err.message : "批量执行失败";
  } finally {
    running.value = false;
  }
}

async function remove() {
  if (!current.value?.id) {
    current.value = null;
    return;
  }
  if (!confirm(`删除脚本「${current.value.name}」？`)) return;
  await api.del(`/scripts/${current.value.id}`);
  selected.value = selected.value.filter((id) => id !== current.value.id);
  current.value = null;
  await load();
}

onMounted(load);
</script>

<style scoped>
.layout { display: grid; grid-template-columns: 320px 1fr; gap: 16px; align-items: start; }
.card { background: var(--card); border: 1px solid var(--line); border-radius: var(--radius); padding: 16px; }
.row { display: flex; gap: 8px; align-items: center; margin-bottom: 10px; }
h3 { margin: 0; flex: 1; font-size: 15px; }
input, textarea, button, select { border: 1px solid var(--line); border-radius: 8px; padding: 8px; background: #fff; }
.search { width: 100%; margin-bottom: 10px; }
.primary { background: var(--accent); color: #fff; border-color: var(--accent); }
.danger { color: var(--danger); }
button:disabled { opacity: 0.5; }
.list { display: flex; flex-direction: column; max-height: 78vh; }
.list-head { display: flex; justify-content: space-between; align-items: center; padding: 6px 2px; font-size: 12px; }
.items { flex: 1; overflow: auto; display: flex; flex-direction: column; gap: 4px; }
.item { display: flex; align-items: center; gap: 8px; padding: 4px 6px; border-radius: 8px; }
.item.on { background: #f3ead4; }
.item-main {
  display: flex; flex-direction: column; align-items: flex-start; flex: 1;
  border: 0; background: transparent; padding: 4px;
}
.item-main span { color: var(--muted); font-size: 12px; }
.empty { text-align: center; padding: 20px 0; }
.batch { display: flex; flex-direction: column; gap: 8px; padding-top: 12px; border-top: 1px solid var(--line); margin-top: 10px; }
.chk { display: flex; gap: 6px; align-items: center; color: var(--muted); font-size: 13px; }
.title { flex: 1; font-family: var(--serif); font-size: 18px; }
.meta { display: grid; grid-template-columns: 1fr 1fr 110px; gap: 8px; margin-bottom: 8px; }
.editor textarea { width: 100%; margin-bottom: 8px; }
.code { min-height: 340px; font-family: var(--mono); font-size: 13px; line-height: 1.5; }
.out { background: #171411; color: #e8dcc8; padding: 14px; border-radius: 10px; overflow: auto; max-height: 300px; white-space: pre-wrap; }
.muted { color: var(--muted); font-size: 13px; }
.placeholder { display: grid; place-items: center; min-height: 320px; }
@media (max-width: 1100px) { .layout { grid-template-columns: 1fr; } }
</style>
