<template>
  <div class="layout">
    <section class="card">
      <div class="row">
        <input v-model="path" class="path" @keydown.enter="ls" />
        <button @click="up">上级</button>
        <button @click="ls">打开</button>
        <button @click="mkdir">新建目录</button>
        <label class="upload">上传<input type="file" @change="upload" /></label>
      </div>
      <table>
        <thead><tr><th></th><th>名称</th><th>大小</th><th>修改时间</th></tr></thead>
        <tbody>
          <tr v-for="e in listing.entries || []" :key="e.path">
            <td><input type="checkbox" :value="e.path" v-model="picked" /></td>
            <td>
              <button class="link" @click="e.is_dir ? (path = e.path, ls()) : preview(e.path)">
                {{ e.is_dir ? "▸" : "·" }} {{ e.name }}
              </button>
            </td>
            <td class="mono">{{ e.is_dir ? "" : e.size }}</td>
            <td class="mono">{{ e.mtime?.slice(0, 19) }}</td>
          </tr>
        </tbody>
      </table>
      <pre v-if="text" class="out">{{ text }}</pre>
    </section>
    <aside class="card">
      <h3>正则打包</h3>
      <p class="muted">对勾选路径（或手动填写）按正则收集文件，打成 tar.gz / zip。</p>
      <textarea v-model="sourcesText" rows="4" />
      <input v-model="include" placeholder="包含正则，如 .*\\.log$" />
      <input v-model="exclude" placeholder="排除正则，如 .*\\.gz$" />
      <input v-model="outputName" placeholder="产物名" />
      <select v-model="fmt">
        <option value="tar.gz">tar.gz</option>
        <option value="zip">zip</option>
      </select>
      <button class="primary" @click="archive">开始打包</button>
      <p v-if="archiveResult" class="ok">
        {{ archiveResult.file_count }} 个文件，
        <a :href="`/api/v1/files/download?path=${encodeURIComponent(archiveResult.archive_path)}&token=${token}`" target="_blank">下载</a>
      </p>
      <h3>目录同步</h3>
      <textarea v-model="syncText" rows="5" placeholder='[{"src":"/var/log","dst":"/tmp/log-copy"}]' />
      <label class="chk"><input type="checkbox" v-model="deleteExtra" /> 删除目标多余文件</label>
      <button @click="sync">同步</button>
      <pre v-if="syncResult">{{ JSON.stringify(syncResult, null, 2) }}</pre>
    </aside>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref, watch } from "vue";
import { api, getToken } from "@/api/client";
import { useSession } from "@/stores/session";

const session = useSession();
const token = getToken();
const path = ref(session.cwd || "/");
const listing = ref<any>({ entries: [] });
const picked = ref<string[]>([]);
const sourcesText = ref("");
const include = ref(".*");
const exclude = ref("");
const outputName = ref("bundle");
const fmt = ref("tar.gz");
const archiveResult = ref<any>(null);
const syncText = ref("[]");
const deleteExtra = ref(false);
const syncResult = ref<any>(null);
const text = ref("");

watch(picked, (val) => {
  sourcesText.value = val.join("\n");
});

async function ls() {
  listing.value = await api.get(`/files/ls?path=${encodeURIComponent(path.value)}`);
  path.value = listing.value.path;
}

function up() {
  if (listing.value.parent) {
    path.value = listing.value.parent;
    ls();
  }
}

async function preview(p: string) {
  const data = await api.get(`/files/read?path=${encodeURIComponent(p)}`);
  text.value = data.content;
}

async function mkdir() {
  const name = prompt("目录名");
  if (!name) return;
  await api.post("/files/mkdir", { path: `${listing.value.path}/${name}` });
  await ls();
}

async function upload(ev: Event) {
  const file = (ev.target as HTMLInputElement).files?.[0];
  if (!file) return;
  const body = new FormData();
  body.append("file", file);
  await fetch(`/api/v1/files/upload?path=${encodeURIComponent(listing.value.path)}`, {
    method: "POST",
    headers: { Authorization: `Bearer ${getToken()}` },
    body,
  });
  await ls();
}

async function archive() {
  const sources = sourcesText.value.split(/\n+/).map((s) => s.trim()).filter(Boolean);
  archiveResult.value = await api.post("/files/archive", {
    sources,
    include: include.value || null,
    exclude: exclude.value || null,
    format: fmt.value,
    output_name: outputName.value,
  });
}

async function sync() {
  syncResult.value = await api.post("/files/sync", {
    mappings: JSON.parse(syncText.value),
    include: include.value || null,
    exclude: exclude.value || null,
    delete_extra: deleteExtra.value,
  });
}

onMounted(ls);
</script>

<style scoped>
.layout { display: grid; grid-template-columns: 1.4fr 0.7fr; gap: 16px; }
.card { background: var(--card); border: 1px solid var(--line); border-radius: var(--radius); padding: 16px; }
.row { display: flex; gap: 8px; margin-bottom: 12px; }
.path { flex: 1; font-family: var(--mono); }
input, textarea, select, button { border: 1px solid var(--line); border-radius: 8px; padding: 8px; background: #fff; margin-bottom: 8px; width: 100%; }
.row input, .row button, .upload { width: auto; margin: 0; }
.primary { background: var(--accent); color: #fff; border-color: var(--accent); }
table { width: 100%; border-collapse: collapse; }
th, td { text-align: left; padding: 8px; border-bottom: 1px solid var(--line); font-size: 13px; }
.link { border: 0; background: none; padding: 0; text-align: left; }
.mono { font-family: var(--mono); font-size: 12px; }
.muted { color: var(--muted); font-size: 13px; }
.ok { color: var(--ok); }
.out { background: #171411; color: #e8dcc8; padding: 12px; max-height: 240px; overflow: auto; }
.upload { font-size: 13px; display: flex; align-items: center; gap: 6px; }
@media (max-width: 1000px) { .layout { grid-template-columns: 1fr; } }
</style>
