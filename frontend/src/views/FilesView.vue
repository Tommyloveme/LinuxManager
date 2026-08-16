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

      <div class="views-row">
        <span class="muted small vlabel">常用路径</span>
        <button
          v-for="v in pathViews"
          :key="v.id"
          class="chip"
          :class="{ on: v.path === listing.path }"
          :title="v.path"
          @click="goView(v)"
        >{{ v.name }}</button>
        <button class="chip ghost" @click="addPathView">＋保存当前</button>
        <button class="chip ghost" @click="managing = !managing">{{ managing ? "完成" : "管理" }}</button>
      </div>
      <div v-if="managing" class="views-manage">
        <div v-for="v in pathViews" :key="v.id" class="vm-row">
          <input v-model="v.name" class="vm-name" placeholder="视图名称" @change="savePathViews" />
          <input v-model="v.path" class="vm-path mono" placeholder="目录路径" @change="savePathViews" />
          <button class="mini" @click="v.path = listing.path; savePathViews()" title="设为当前目录">取当前</button>
          <button class="mini danger" @click="delPathView(v.id)">删除</button>
        </div>
        <button class="mini" @click="newPathView">＋新增视图</button>
        <p v-if="!pathViews.length" class="muted small">还没有视图，点击「保存当前」或「新增视图」创建。</p>
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

      <div class="views-row wrap">
        <span class="muted small vlabel">策略视图</span>
        <span v-for="v in dlViews" :key="v.id" class="chip-group">
          <button class="chip" :title="dlViewTip(v)" @click="applyDlView(v)">{{ v.name }}</button>
          <button class="chip-x" title="重命名" @click="renameDlView(v)">✎</button>
          <button class="chip-x" title="删除" @click="delDlView(v.id)">×</button>
        </span>
        <button class="chip ghost" @click="saveDlView">＋保存当前策略</button>
      </div>

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
          已打包 {{ archiveResult.file_count }} 个文件并开始下载 ·
          <a :href="dl(archiveResult.archive_path)" target="_blank">重新下载</a>
        </p>
      </template>
      <p v-if="copyMsg" :class="['small', copyOk ? 'ok' : 'err']">{{ copyMsg }}</p>

      <h3 class="mt">上传到当前目录</h3>
      <label class="upload-btn">
        选择本机文件（可多选），或直接拖拽到左侧文件区
        <input type="file" multiple @change="onPick" />
      </label>
      <p v-if="uploadMsg" class="small ok">{{ uploadMsg }}</p>
    </aside>

    <!-- 预览浮层 -->
    <div v-if="previewing" class="overlay" @click.self="closePreview">
      <div class="preview-box card" :class="{ full: pvFull }">
        <div class="preview-head">
          <strong class="mono name">{{ previewing.name }}</strong>
          <div class="pv-actions">
            <button class="mini" @click="pvFull = !pvFull">{{ pvFull ? "退出全屏" : "全屏" }}</button>
            <a class="mini" :href="dl(previewing.path)" target="_blank">下载</a>
            <button class="mini" @click="closePreview">退出预览</button>
          </div>
        </div>

        <div v-if="!isImage(previewing.name) && previewText !== null" class="pv-toolbar">
          <input v-model="pvQuery" class="pv-search" placeholder="搜索 / 高亮关键词…" />
          <label class="chk" title="全字匹配"><input type="checkbox" v-model="pvWord" /> 全字</label>
          <label class="chk" title="区分大小写"><input type="checkbox" v-model="pvCase" /> Aa</label>
          <label class="chk" title="正则表达式"><input type="checkbox" v-model="pvRegex" /> 正则</label>
          <label class="chk" title="在文本中高亮匹配项"><input type="checkbox" v-model="pvHighlight" /> 高亮</label>
          <button class="mini" @click="clearSearch">取消</button>
          <span class="muted small stat">
            <template v-if="pvQuery">{{ pvError ? "表达式无效" : `${totalMatches} 处 / ${results.length} 行` }}</template>
          </span>
        </div>

        <img v-if="isImage(previewing.name)" :src="dl(previewing.path)" class="preview-img" />
        <div v-else-if="previewText !== null" class="preview-text">
          <div v-for="(l, i) in pvLines" :key="i" class="pl" :id="`pl-${i}`" :class="{ flash: flashLine === i }">
            <span class="ln">{{ i + 1 }}</span><span class="lt" v-html="lineHtml(l)"></span>
          </div>
        </div>
        <p v-else class="muted">无法内联预览该文件（二进制或过大），请下载后用本机程序打开。</p>

        <div v-if="pvQuery && !pvError && previewText !== null" class="pv-results">
          <div class="pv-results-head">
            <span class="muted small">搜索结果 · 点击跳转到对应行</span>
            <span class="pager" v-if="pageCount > 1">
              <button class="mini" :disabled="page <= 0" @click="page--">‹ 上页</button>
              <span class="small muted">{{ page + 1 }} / {{ pageCount }}</span>
              <button class="mini" :disabled="page >= pageCount - 1" @click="page++">下页 ›</button>
            </span>
          </div>
          <div class="pv-results-list">
            <button v-for="r in pagedResults" :key="r.line" class="pv-result" @click="jump(r.line)">
              <span class="ln">{{ r.line }}</span>
              <span class="lt" v-html="lineHtml(r.text, true)"></span>
            </button>
            <p v-if="!results.length" class="muted small empty">无匹配结果</p>
          </div>
        </div>
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
const listing = ref<any>({ entries: [], path: "" });
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
const dragging = ref(false);

/* ---------- 本地存储的小工具 ---------- */
function loadLS<T>(key: string, def: T): T {
  try {
    const raw = localStorage.getItem(key);
    return raw ? (JSON.parse(raw) as T) : def;
  } catch {
    return def;
  }
}
function saveLS(key: string, val: unknown) {
  localStorage.setItem(key, JSON.stringify(val));
}
function uid() {
  return Math.random().toString(36).slice(2, 10);
}

/* ---------- 常用路径视图 ---------- */
type PathView = { id: string; name: string; path: string };
const pathViews = ref<PathView[]>(loadLS("cedar.pathViews", []));
const managing = ref(false);

function savePathViews() {
  saveLS("cedar.pathViews", pathViews.value);
}
function addPathView() {
  const cur = listing.value.path || path.value;
  const name = prompt("视图名称", cur.split("/").filter(Boolean).pop() || "根目录");
  if (!name) return;
  pathViews.value.push({ id: uid(), name, path: cur });
  savePathViews();
}
function newPathView() {
  pathViews.value.push({ id: uid(), name: "新视图", path: listing.value.path || "/" });
  savePathViews();
}
function delPathView(id: string) {
  pathViews.value = pathViews.value.filter((v) => v.id !== id);
  savePathViews();
}
function goView(v: PathView) {
  path.value = v.path;
  ls();
}

/* ---------- 下载策略视图 ---------- */
type DlView = {
  id: string; name: string; sources: string; include: string; exclude: string;
  mode: string; fmt: string; outputName: string;
};
const dlViews = ref<DlView[]>(loadLS("cedar.downloadViews", []));

function saveDlViews() {
  saveLS("cedar.downloadViews", dlViews.value);
}
function saveDlView() {
  const name = prompt("策略视图名称", outputName.value || "下载策略");
  if (!name) return;
  dlViews.value.push({
    id: uid(), name,
    sources: sourcesText.value, include: include.value, exclude: exclude.value,
    mode: mode.value, fmt: fmt.value, outputName: outputName.value,
  });
  saveDlViews();
}
function applyDlView(v: DlView) {
  sourcesText.value = v.sources;
  include.value = v.include;
  exclude.value = v.exclude;
  mode.value = v.mode;
  fmt.value = v.fmt;
  outputName.value = v.outputName;
}
function renameDlView(v: DlView) {
  const name = prompt("重命名策略视图", v.name);
  if (!name) return;
  v.name = name;
  saveDlViews();
}
function delDlView(id: string) {
  dlViews.value = dlViews.value.filter((v) => v.id !== id);
  saveDlViews();
}
function dlViewTip(v: DlView) {
  const src = v.sources ? v.sources.split(/\n+/).filter(Boolean).length + " 个路径" : "当前目录";
  return `${src} · ${v.mode === "copy" ? "复制" : "打包 " + v.fmt}${v.include ? " · 含 " + v.include : ""}${v.exclude ? " · 排 " + v.exclude : ""}`;
}

/* ---------- 目录浏览 ---------- */
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

/* ---------- 预览：搜索 / 高亮 / 全屏 ---------- */
const previewing = ref<any>(null);
const previewText = ref<string | null>(null);
const pvFull = ref(false);
const pvQuery = ref("");
const pvWord = ref(false);
const pvCase = ref(false);
const pvRegex = ref(false);
const pvHighlight = ref(true);
const page = ref(0);
const PAGE_SIZE = 100;
const flashLine = ref(-1);

const matcher = computed<{ re: RegExp | null; error: boolean }>(() => {
  if (!pvQuery.value) return { re: null, error: false };
  try {
    let pat = pvRegex.value
      ? pvQuery.value
      : pvQuery.value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
    if (pvWord.value) pat = `\\b(?:${pat})\\b`;
    return { re: new RegExp(pat, pvCase.value ? "g" : "gi"), error: false };
  } catch {
    return { re: null, error: true };
  }
});
const pvError = computed(() => matcher.value.error);
const pvLines = computed(() => (previewText.value ?? "").split("\n"));
const results = computed(() => {
  const re = matcher.value.re;
  if (!re) return [] as { line: number; text: string; count: number }[];
  const out: { line: number; text: string; count: number }[] = [];
  pvLines.value.forEach((text, i) => {
    re.lastIndex = 0;
    let count = 0;
    let m: RegExpExecArray | null;
    while ((m = re.exec(text))) {
      count++;
      if (m[0].length === 0) re.lastIndex++;
    }
    if (count) out.push({ line: i + 1, text, count });
  });
  return out;
});
const totalMatches = computed(() => results.value.reduce((s, r) => s + r.count, 0));
const pageCount = computed(() => Math.max(1, Math.ceil(results.value.length / PAGE_SIZE)));
const pagedResults = computed(() =>
  results.value.slice(page.value * PAGE_SIZE, (page.value + 1) * PAGE_SIZE)
);

watch([pvQuery, pvWord, pvCase, pvRegex], () => {
  page.value = 0;
});

function escHtml(s: string) {
  return s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}
function lineHtml(raw: string, forceMark = false): string {
  const re = matcher.value.re;
  if (!re || (!pvHighlight.value && !forceMark)) return escHtml(raw) || "&nbsp;";
  let html = "";
  let last = 0;
  re.lastIndex = 0;
  let m: RegExpExecArray | null;
  while ((m = re.exec(raw))) {
    html += escHtml(raw.slice(last, m.index));
    html += `<mark>${escHtml(m[0])}</mark>`;
    last = m.index + m[0].length;
    if (m[0].length === 0) re.lastIndex++;
  }
  html += escHtml(raw.slice(last));
  return html || "&nbsp;";
}
function jump(line: number) {
  const el = document.getElementById(`pl-${line - 1}`);
  if (el) {
    el.scrollIntoView({ block: "center" });
    flashLine.value = line - 1;
    setTimeout(() => (flashLine.value = -1), 1200);
  }
}
function clearSearch() {
  pvQuery.value = "";
  page.value = 0;
}

async function preview(e: any) {
  previewing.value = e;
  previewText.value = null;
  pvQuery.value = "";
  pvFull.value = false;
  page.value = 0;
  if (isImage(e.name)) return;
  try {
    const data = await api.get(`/files/read?path=${encodeURIComponent(e.path)}`);
    previewText.value = data.content;
  } catch {
    previewText.value = null;
  }
}
function closePreview() {
  previewing.value = null;
  previewText.value = null;
  pvFull.value = false;
}

/* ---------- 下载到本地 ---------- */
function sources(): string[] {
  const list = sourcesText.value.split(/\n+/).map((s) => s.trim()).filter(Boolean);
  return list.length ? list : [listing.value.path];
}

async function archive() {
  archiving.value = true;
  archiveResult.value = null;
  copyMsg.value = "";
  try {
    const res = await api.post("/files/archive", {
      sources: sources(),
      include: include.value || null,
      exclude: exclude.value || null,
      format: fmt.value,
      output_name: outputName.value,
    });
    archiveResult.value = res;
    // 打包完成后立即触发浏览器下载，而不是只给出链接
    triggerDownload(dl(res.archive_path), res.archive_path.split("/").pop() || "archive");
  } catch (err) {
    copyOk.value = false;
    copyMsg.value = err instanceof Error ? err.message : "打包失败";
  } finally {
    archiving.value = false;
  }
}

function triggerDownload(url: string, name: string) {
  const a = document.createElement("a");
  a.href = url;
  a.download = name;
  document.body.appendChild(a);
  a.click();
  a.remove();
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
        triggerDownload(dl(f.path), f.rel.split("/").pop() || "file");
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

/* ---------- 上传 ---------- */
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

/* 视图（常用路径 / 下载策略） */
.views-row { display: flex; align-items: center; gap: 6px; flex-wrap: wrap; margin-bottom: 10px; }
.views-row.wrap { margin-bottom: 12px; }
.vlabel { white-space: nowrap; }
.chip {
  padding: 3px 10px; font-size: 12px; border-radius: 999px; cursor: pointer;
  background: #faf6ec; border: 1px solid var(--line); max-width: 160px;
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}
.chip.on { background: #f3ead4; border-color: var(--accent); }
.chip.ghost { background: transparent; color: var(--muted); border-style: dashed; }
.chip-group { display: inline-flex; align-items: center; }
.chip-group .chip { border-radius: 999px 0 0 999px; }
.chip-x {
  padding: 3px 6px; font-size: 11px; border-left: 0; cursor: pointer;
  background: #faf6ec; border: 1px solid var(--line);
}
.chip-group .chip-x:last-child { border-radius: 0 999px 999px 0; }
.views-manage { border: 1px dashed var(--line); border-radius: 10px; padding: 10px; margin-bottom: 10px; display: flex; flex-direction: column; gap: 6px; }
.vm-row { display: flex; gap: 6px; align-items: center; }
.vm-name { width: 130px; font-size: 12px; padding: 5px 8px; }
.vm-path { flex: 1; font-size: 12px; padding: 5px 8px; }

/* 预览浮层 */
.overlay { position: fixed; inset: 0; background: rgba(20, 16, 12, 0.55); display: grid; place-items: center; z-index: 50; padding: 24px; }
.preview-box { width: min(980px, 94vw); height: min(86vh, 900px); display: flex; flex-direction: column; }
.preview-box.full { position: fixed; inset: 0; width: auto; height: auto; max-height: none; border-radius: 0; }
.preview-head { display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px; gap: 8px; }
.preview-head .name { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.pv-actions { white-space: nowrap; }
.pv-toolbar { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; margin-bottom: 8px; }
.pv-search { flex: 1; min-width: 180px; font-family: var(--mono); font-size: 13px; padding: 6px 8px; }
.stat { min-width: 90px; }
.preview-text {
  background: #171411; color: #e8dcc8; padding: 10px 0; border-radius: 10px;
  overflow: auto; flex: 1; font-family: var(--mono); font-size: 12.5px; line-height: 1.55;
}
.pl { display: flex; padding: 0 12px; }
.pl.flash { background: rgba(214, 158, 46, 0.35); }
.pl .ln { color: #6f6555; min-width: 44px; text-align: right; padding-right: 12px; user-select: none; flex: 0 0 auto; }
.pl .lt { white-space: pre-wrap; word-break: break-all; flex: 1; }
.preview-text :deep(mark), .pv-results-list :deep(mark) { background: #d69e2e; color: #171411; border-radius: 2px; padding: 0 1px; }
.preview-img { max-width: 100%; max-height: 70vh; object-fit: contain; border-radius: 8px; }

/* 搜索结果面板 */
.pv-results { margin-top: 10px; border-top: 1px solid var(--line); padding-top: 8px; flex: 0 0 auto; }
.pv-results-head { display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px; }
.pager { display: inline-flex; align-items: center; gap: 6px; }
.pv-results-list { max-height: 180px; overflow-y: auto; display: flex; flex-direction: column; }
.pv-result {
  display: flex; gap: 8px; text-align: left; border: 0; background: transparent;
  padding: 3px 6px; border-radius: 6px; cursor: pointer; font-family: var(--mono); font-size: 12px;
}
.pv-result:hover { background: #f3ead4; }
.pv-result .ln { color: var(--muted); min-width: 42px; text-align: right; flex: 0 0 auto; }
.pv-result .lt { white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
@media (max-width: 1050px) { .layout { grid-template-columns: 1fr; } }
</style>
