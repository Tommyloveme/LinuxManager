<template>
  <div class="layout">
    <section
      class="card browser"
      :class="{ dragging }"
      @dragover.prevent="dragging = true"
      @dragleave.prevent="dragging = false"
      @drop.prevent="onDrop"
    >
      <div class="row path-row">
        <button @click="up" title="上级目录">↑</button>
        <input v-model="path" class="path" @keydown.enter="ls" />
        <button @click="ls">打开</button>
        <button @click="mkdir">新建目录</button>
      </div>

      <div class="row filter-row">
        <input v-model="filter" class="filter" placeholder="按名称正则过滤，如 \.log$" />
        <label class="chk"><input type="checkbox" v-model="showHidden" /> 显示隐藏文件</label>
        <span class="muted count">{{ visibleEntries.length }} 项 · 选中 {{ picked.length }}</span>
      </div>

      <div v-if="filterError" class="err small">正则无效：{{ filterError }}</div>

      <table>
        <thead>
          <tr>
            <th><input type="checkbox" :checked="allChecked" @change="toggleAll" /></th>
            <th>名称</th><th>大小</th><th>修改时间</th><th>权限</th><th></th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="e in visibleEntries" :key="e.path" :class="{ hidden: e.name.startsWith('.') }">
            <td><input type="checkbox" :value="e.path" v-model="picked" /></td>
            <td>
              <button class="link" @click="e.is_dir ? enter(e) : preview(e)">
                <span class="ic">{{ e.is_dir ? "📁" : "📄" }}</span> {{ e.name }}
              </button>
            </td>
            <td class="mono">{{ e.is_dir ? "—" : human(e.size) }}</td>
            <td class="mono">{{ e.mtime?.slice(0, 19).replace("T", " ") }}</td>
            <td class="mono">{{ e.mode }}</td>
            <td class="acts">
              <button v-if="!e.is_dir" class="mini" @click="preview(e)">预览</button>
              <a class="mini" :href="dl(e.path)" target="_blank">下载</a>
              <button class="mini danger" @click="remove(e)">删除</button>
            </td>
          </tr>
          <tr v-if="!visibleEntries.length"><td colspan="6" class="muted empty">空目录或无匹配项</td></tr>
        </tbody>
      </table>
      <p class="drop-hint muted">提示：把本机文件拖到此处即可上传到当前目录。</p>
    </section>

    <aside class="card panel">
      <h3>下载到本地</h3>
      <p class="muted small">对勾选项（文件或目录，目录会递归）按下方正则收集，复制或打包到本机。</p>
      <label class="fld">收集范围
        <textarea v-model="sourcesText" rows="3" placeholder="每行一个路径；留空则用当前目录" />
      </label>
      <div class="two">
        <label class="fld">包含正则<input v-model="include" placeholder=".*\.log$" /></label>
        <label class="fld">排除正则<input v-model="exclude" placeholder=".*\.gz$" /></label>
      </div>
      <label class="fld">下载方式
        <select v-model="mode">
          <option value="copy">复制文件（默认）</option>
          <option value="archive">打包成压缩包</option>
        </select>
      </label>

      <template v-if="mode === 'copy'">
        <button class="primary" :disabled="copying" @click="copyToLocal">
          {{ copying ? `复制中 ${copyDone}/${copyTotal}…` : "选择本地文件夹并复制" }}
        </button>
        <p class="muted small">使用浏览器目录选择器写入本机文件夹；不支持时会退化为逐个下载。</p>
      </template>
      <template v-else>
        <div class="two">
          <label class="fld">产物名<input v-model="outputName" placeholder="bundle" /></label>
          <label class="fld">格式
            <select v-model="fmt"><option value="tar.gz">tar.gz</option><option value="zip">zip</option></select>
          </label>
        </div>
        <button class="primary" :disabled="archiving" @click="archive">{{ archiving ? "打包中…" : "打包并下载" }}</button>
        <p v-if="archiveResult" class="ok small">
          {{ archiveResult.file_count }} 个文件 ·
          <a :href="dl(archiveResult.archive_path)" target="_blank">下载压缩包</a>
        </p>
      </template>
      <p v-if="copyMsg" :class="['small', copyOk ? 'ok' : 'err']">{{ copyMsg }}</p>

      <h3 class="mt">上传到当前目录</h3>
      <label class="upload-btn">
        选择本机文件（可多选）
        <input type="file" multiple @change="onPick" />
      </label>
      <p v-if="uploadMsg" class="small ok">{{ uploadMsg }}</p>

      <h3 class="mt">预览设置</h3>
      <label class="fld">默认预览方式
        <select v-model="previewMode" @change="savePreviewMode">
          <option value="inline">内联预览（文本 / 图片）</option>
          <option value="download">下载并用本机默认程序打开</option>
        </select>
      </label>
    </aside>

    <!-- 预览浮层 -->
    <div v-if="previewing" class="overlay" @click.self="closePreview">
      <div class="preview-box card">
        <div class="preview-head">
          <strong class="mono">{{ previewing.name }}</strong>
          <div>
            <a class="mini" :href="dl(previewing.path)" target="_blank">下载</a>
            <button class="mini" @click="closePreview">退出预览</button>
          </div>
        </div>
        <img v-if="isImage(previewing.name)" :src="dl(previewing.path)" class="preview-img" />
        <pre v-else-if="previewText !== null" class="preview-text">{{ previewText }}</pre>
        <p v-else class="muted">无法内联预览该文件，请下载后用本机程序打开。</p>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";
import { api, getToken } from "@/api/client";
import { useSession } from "@/stores/session";

const session = useSession();
const path = ref(session.cwd || "/");
const listing = ref<any>({ entries: [] });
const picked = ref<string[]>([]);
const filter = ref("");
const filterError = ref("");
const showHidden = ref(false);

const sourcesText = ref("");
const include = ref("");
const exclude = ref("");
const mode = ref("copy");
const outputName = ref("bundle");
const fmt = ref("tar.gz");
const archiveResult = ref<any>(null);
const archiving = ref(false);

const copying = ref(false);
const copyDone = ref(0);
const copyTotal = ref(0);
const copyMsg = ref("");
const copyOk = ref(false);

const uploadMsg = ref("");

const previewing = ref<any>(null);
const previewText = ref<string | null>(null);
const previewMode = ref(localStorage.getItem("cedar.previewMode") || "inline");

const dragging = ref(false);

const visibleEntries = computed(() => {
  let entries = (listing.value.entries || []) as any[];
  if (!showHidden.value) entries = entries.filter((e) => !e.name.startsWith("."));
  if (filter.value) {
    try {
      const re = new RegExp(filter.value);
      filterError.value = "";
      entries = entries.filter((e) => re.test(e.name));
    } catch (err) {
      filterError.value = err instanceof Error ? err.message : "";
    }
  } else {
    filterError.value = "";
  }
  return entries;
});
const allChecked = computed(
  () => visibleEntries.value.length > 0 && visibleEntries.value.every((e) => picked.value.includes(e.path))
);

watch(picked, (val) => {
  if (val.length) sourcesText.value = val.join("\n");
});

function human(n: number) {
  if (n > 1024 ** 3) return `${(n / 1024 ** 3).toFixed(1)}G`;
  if (n > 1024 ** 2) return `${(n / 1024 ** 2).toFixed(1)}M`;
  if (n > 1024) return `${(n / 1024).toFixed(0)}K`;
  return `${n}B`;
}
function dl(p: string) {
  return `/api/v1/files/download?path=${encodeURIComponent(p)}&token=${getToken()}`;
}
function isImage(name: string) {
  return /\.(png|jpe?g|gif|webp|bmp|svg)$/i.test(name);
}

async function ls() {
  listing.value = await api.get(`/files/ls?path=${encodeURIComponent(path.value)}`);
  path.value = listing.value.path;
  picked.value = [];
}
function enter(e: any) {
  path.value = e.path;
  ls();
}
function up() {
  if (listing.value.parent) {
    path.value = listing.value.parent;
    ls();
  }
}
function toggleAll() {
  if (allChecked.value) {
    const paths = visibleEntries.value.map((e) => e.path);
    picked.value = picked.value.filter((p) => !paths.includes(p));
  } else {
    const set = new Set(picked.value);
    visibleEntries.value.forEach((e) => set.add(e.path));
    picked.value = [...set];
  }
}

async function preview(e: any) {
  if (previewMode.value === "download" || (!isImage(e.name) && isBinary(e.name))) {
    window.open(dl(e.path), "_blank");
    if (previewMode.value === "download") return;
  }
  previewing.value = e;
  previewText.value = null;
  if (isImage(e.name)) return;
  try {
    const data = await api.get(`/files/read?path=${encodeURIComponent(e.path)}`);
    previewText.value = data.content;
  } catch {
    previewText.value = null;
  }
}
function isBinary(name: string) {
  return /\.(zip|gz|tar|bin|exe|so|o|pdf|mp4|mp3|png|jpe?g|gif)$/i.test(name);
}
function closePreview() {
  previewing.value = null;
  previewText.value = null;
}
function savePreviewMode() {
  localStorage.setItem("cedar.previewMode", previewMode.value);
}

async function mkdir() {
  const name = prompt("目录名");
  if (!name) return;
  await api.post("/files/mkdir", { path: `${listing.value.path}/${name}` });
  await ls();
}
async function remove(e: any) {
  if (!confirm(`删除 ${e.name}？`)) return;
  await api.del(`/files?path=${encodeURIComponent(e.path)}`);
  await ls();
}

function sources(): string[] {
  const list = sourcesText.value.split(/\n+/).map((s) => s.trim()).filter(Boolean);
  return list.length ? list : [listing.value.path];
}

async function archive() {
  archiving.value = true;
  archiveResult.value = null;
  try {
    archiveResult.value = await api.post("/files/archive", {
      sources: sources(),
      include: include.value || null,
      exclude: exclude.value || null,
      format: fmt.value,
      output_name: outputName.value,
    });
  } catch (err) {
    copyOk.value = false;
    copyMsg.value = err instanceof Error ? err.message : "打包失败";
  } finally {
    archiving.value = false;
  }
}

async function copyToLocal() {
  copyMsg.value = "";
  let collected;
  try {
    collected = await api.post("/files/collect", {
      sources: sources(),
      include: include.value || null,
      exclude: exclude.value || null,
    });
  } catch (err) {
    copyOk.value = false;
    copyMsg.value = err instanceof Error ? err.message : "收集文件失败";
    return;
  }
  const files = collected.items as any[];
  if (!files.length) {
    copyOk.value = false;
    copyMsg.value = "没有匹配到文件";
    return;
  }

  const picker = (window as any).showDirectoryPicker;
  copying.value = true;
  copyDone.value = 0;
  copyTotal.value = files.length;
  try {
    if (picker) {
      const dir = await picker({ mode: "readwrite" });
      for (const f of files) {
        const blob = await (await fetch(dl(f.path))).blob();
        await writeInto(dir, f.rel, blob);
        copyDone.value++;
      }
      copyOk.value = true;
      copyMsg.value = `已复制 ${files.length} 个文件到本机文件夹`;
    } else {
      for (const f of files) {
        const a = document.createElement("a");
        a.href = dl(f.path);
        a.download = f.rel.split("/").pop() || "file";
        document.body.appendChild(a);
        a.click();
        a.remove();
        copyDone.value++;
        await new Promise((r) => setTimeout(r, 150));
      }
      copyOk.value = true;
      copyMsg.value = `浏览器不支持目录选择，已改为逐个下载 ${files.length} 个文件`;
    }
  } catch (err) {
    copyOk.value = false;
    copyMsg.value = err instanceof Error ? err.message : "复制被取消或失败";
  } finally {
    copying.value = false;
  }
}

async function writeInto(dirHandle: any, rel: string, blob: Blob) {
  const parts = rel.split("/").filter(Boolean);
  let dir = dirHandle;
  for (let i = 0; i < parts.length - 1; i++) {
    dir = await dir.getDirectoryHandle(parts[i], { create: true });
  }
  const fh = await dir.getFileHandle(parts[parts.length - 1], { create: true });
  const w = await fh.createWritable();
  await w.write(blob);
  await w.close();
}

async function onPick(ev: Event) {
  const files = (ev.target as HTMLInputElement).files;
  if (files) await uploadFiles(Array.from(files));
  (ev.target as HTMLInputElement).value = "";
}
async function onDrop(ev: DragEvent) {
  dragging.value = false;
  const files = ev.dataTransfer?.files;
  if (files && files.length) await uploadFiles(Array.from(files));
}
async function uploadFiles(files: File[]) {
  uploadMsg.value = "";
  let done = 0;
  for (const file of files) {
    const body = new FormData();
    body.append("file", file);
    await fetch(`/api/v1/files/upload?path=${encodeURIComponent(listing.value.path)}`, {
      method: "POST",
      headers: { Authorization: `Bearer ${getToken()}` },
      body,
    });
    done++;
  }
  uploadMsg.value = `已上传 ${done} 个文件到 ${listing.value.path}`;
  await ls();
}

onMounted(ls);
</script>

<style scoped>
.layout { display: grid; grid-template-columns: 1fr 320px; gap: 16px; align-items: start; }
.card { background: var(--card); border: 1px solid var(--line); border-radius: var(--radius); padding: 16px; }
.browser.dragging { outline: 2px dashed var(--accent); outline-offset: -6px; }
.row { display: flex; gap: 8px; align-items: center; margin-bottom: 10px; }
.path { flex: 1; font-family: var(--mono); }
.filter { flex: 1; font-family: var(--mono); }
input, textarea, select, button { border: 1px solid var(--line); border-radius: 8px; padding: 8px; background: #fff; }
.path-row button, .filter-row .chk { white-space: nowrap; }
.chk { display: flex; gap: 6px; align-items: center; color: var(--muted); font-size: 13px; }
.count { margin-left: auto; }
.primary { background: var(--accent); color: #fff; border-color: var(--accent); width: 100%; }
button:disabled { opacity: 0.5; }
table { width: 100%; border-collapse: collapse; }
th, td { text-align: left; padding: 7px 8px; border-bottom: 1px solid var(--line); font-size: 13px; }
tr.hidden { opacity: 0.6; }
.link { border: 0; background: none; padding: 0; text-align: left; cursor: pointer; }
.ic { margin-right: 4px; }
.mono { font-family: var(--mono); font-size: 12px; }
.acts { white-space: nowrap; }
.mini { padding: 3px 8px; font-size: 12px; margin-left: 4px; display: inline-block; }
.danger { color: var(--danger); }
.muted { color: var(--muted); }
.small { font-size: 12px; }
.empty { text-align: center; padding: 24px 0; }
.ok { color: var(--ok); }
.err { color: var(--danger); }
.drop-hint { margin: 10px 0 0; font-size: 12px; }
.panel h3 { margin: 0 0 6px; font-size: 15px; }
.panel h3.mt { margin-top: 20px; padding-top: 16px; border-top: 1px solid var(--line); }
.fld { display: flex; flex-direction: column; gap: 5px; font-size: 12px; color: var(--muted); margin-bottom: 10px; }
.fld input, .fld select, .fld textarea { color: var(--ink); }
.two { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; }
.upload-btn { display: block; text-align: center; border: 1px dashed var(--line); border-radius: 8px; padding: 12px; font-size: 13px; color: var(--muted); cursor: pointer; }
.upload-btn input { display: none; }
.overlay { position: fixed; inset: 0; background: rgba(20, 16, 12, 0.55); display: grid; place-items: center; z-index: 50; padding: 24px; }
.preview-box { width: min(900px, 92vw); max-height: 86vh; display: flex; flex-direction: column; }
.preview-head { display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; }
.preview-text { background: #171411; color: #e8dcc8; padding: 14px; border-radius: 10px; overflow: auto; flex: 1; white-space: pre-wrap; word-break: break-all; }
.preview-img { max-width: 100%; max-height: 76vh; object-fit: contain; border-radius: 8px; }
@media (max-width: 1050px) { .layout { grid-template-columns: 1fr; } }
</style>
