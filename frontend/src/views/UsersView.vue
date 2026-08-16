<template>
  <div class="wrap">
    <div class="banner card">
      <div>
        <p class="kicker">当前执行身份</p>
        <h2>{{ session.linuxUser || session.hostUser }}</h2>
        <p class="muted mono">{{ who?.id_output || who?.id_error || "尚未获取 id 信息" }}</p>
      </div>
      <div class="badge" :class="{ ok: who?.verified, warn: who && !who.verified }">
        {{ who?.verified ? "已验证" : "未验证" }}
      </div>
    </div>

    <p class="lead">
      选择一个 Linux 用户作为执行身份，脚本、终端与命令都会以该用户运行。
      切换到非当前用户时需要输入其登录密码进行校验（通过 <span class="mono">su</span> 验证，密码只保存在服务内存中，不落库）。
    </p>

    <div class="toolbar">
      <input v-model="q" placeholder="过滤用户名" />
      <label class="chk"><input type="checkbox" v-model="showSystem" /> 显示系统用户</label>
    </div>

    <div class="grid">
      <div class="card table-card">
        <table>
          <thead>
            <tr><th></th><th>用户</th><th>UID</th><th>家目录</th><th>Shell</th></tr>
          </thead>
          <tbody>
            <tr v-for="u in filtered" :key="u.name" @click="pick(u)" :class="{ on: picked === u.name }">
              <td><input type="radio" :checked="picked === u.name" /></td>
              <td><strong>{{ u.name }}</strong></td>
              <td class="mono">{{ u.uid }}</td>
              <td class="mono">{{ u.home }}</td>
              <td class="mono">{{ u.shell }}</td>
            </tr>
          </tbody>
        </table>
      </div>

      <div class="card switch-card">
        <h3>切换到：{{ picked || "（未选择）" }}</h3>
        <label v-if="needPassword">
          登录密码
          <input v-model="password" type="password" placeholder="目标用户的 Linux 密码" @keydown.enter="apply" />
        </label>
        <p v-else class="muted small">切回当前用户或 root 进程下切换无需密码。</p>
        <button class="primary" :disabled="!picked || busy" @click="apply">
          {{ busy ? "校验中…" : "验证并切换" }}
        </button>
        <p v-if="msg" :class="['result', ok ? 'ok' : 'err']">{{ msg }}</p>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { api } from "@/api/client";
import { useSession } from "@/stores/session";

const items = ref<any[]>([]);
const who = ref<any>(null);
const q = ref("");
const showSystem = ref(false);
const picked = ref("");
const password = ref("");
const busy = ref(false);
const msg = ref("");
const ok = ref(false);
const session = useSession();

const filtered = computed(() =>
  items.value.filter((u) => (showSystem.value || !u.is_system) && u.name.includes(q.value))
);

const needPassword = computed(() => picked.value && picked.value !== session.hostUser);

function pick(u: any) {
  picked.value = u.name;
  msg.value = "";
}

async function refreshWho() {
  who.value = await api.get("/users/whoami");
}

onMounted(async () => {
  items.value = (await api.get("/users")).items;
  await refreshWho();
  picked.value = session.linuxUser || session.hostUser;
});

async function apply() {
  if (!picked.value) return;
  busy.value = true;
  msg.value = "";
  try {
    const res = await session.switchUser(picked.value, password.value);
    ok.value = true;
    msg.value = res.message || `已切换到 ${res.linux_user}`;
    password.value = "";
    await refreshWho();
  } catch (err) {
    ok.value = false;
    msg.value = err instanceof Error ? err.message : "切换失败";
  } finally {
    busy.value = false;
  }
}
</script>

<style scoped>
.wrap { display: flex; flex-direction: column; gap: 16px; }
.card { background: var(--card); border: 1px solid var(--line); border-radius: var(--radius); padding: 18px 20px; }
.banner { display: flex; justify-content: space-between; align-items: center; }
.kicker { color: var(--muted); letter-spacing: 0.08em; text-transform: uppercase; font-size: 11px; margin: 0 0 4px; }
.banner h2 { font-family: var(--serif); font-size: 26px; margin: 0 0 6px; font-weight: 500; }
.badge { padding: 6px 14px; border-radius: 999px; font-size: 13px; border: 1px solid var(--line); }
.badge.ok { background: #e5f0e9; color: var(--ok); border-color: #bcd8ca; }
.badge.warn { background: #f6ecd8; color: var(--warn); border-color: #e0cfa6; }
.lead { color: var(--muted); max-width: 780px; line-height: 1.7; margin: 0; }
.toolbar { display: flex; gap: 12px; align-items: center; }
.grid { display: grid; grid-template-columns: 1fr 300px; gap: 16px; align-items: start; }
input { border: 1px solid var(--line); border-radius: 8px; padding: 8px 12px; background: #fff; }
.chk { color: var(--muted); font-size: 13px; display: flex; gap: 6px; align-items: center; }
.table-card { padding: 6px 0; max-height: 60vh; overflow: auto; }
table { width: 100%; border-collapse: collapse; }
th, td { text-align: left; padding: 10px 14px; border-bottom: 1px solid var(--line); font-size: 14px; }
.mono { font-family: var(--mono); font-size: 12px; }
tr.on { background: #f3ead4; }
tbody tr { cursor: pointer; }
.switch-card { position: sticky; top: 12px; display: flex; flex-direction: column; gap: 12px; }
.switch-card h3 { margin: 0; font-size: 15px; }
.switch-card label { display: flex; flex-direction: column; gap: 6px; font-size: 13px; color: var(--muted); }
.primary { background: var(--accent); color: #fff; border: 0; border-radius: 8px; padding: 10px; font-weight: 600; }
.primary:disabled { opacity: 0.5; }
.result { font-size: 13px; margin: 0; }
.small { font-size: 12px; }
.result.ok, .ok { color: var(--ok); }
.result.err, .err { color: var(--danger); }
@media (max-width: 1000px) { .grid { grid-template-columns: 1fr; } }
</style>
