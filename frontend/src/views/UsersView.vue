<template>
  <div class="wrap">
    <p class="lead">选择执行身份。后续脚本、批处理与终端都会以该 Linux 用户运行（需要 sudo 权限）。</p>
    <div class="toolbar">
      <input v-model="q" placeholder="过滤用户名" />
      <label class="chk"><input type="checkbox" v-model="showSystem" /> 显示系统用户</label>
      <button class="primary" :disabled="!picked" @click="apply">切换到选中用户</button>
    </div>
    <p v-if="who" class="who">当前 id：{{ who.id_output || who.id_error || who.name }}</p>
    <table>
      <thead>
        <tr><th></th><th>用户</th><th>UID</th><th>家目录</th><th>Shell</th></tr>
      </thead>
      <tbody>
        <tr v-for="u in filtered" :key="u.name" @click="picked = u.name" :class="{ on: picked === u.name }">
          <td><input type="radio" :checked="picked === u.name" /></td>
          <td>{{ u.name }}</td>
          <td class="mono">{{ u.uid }}</td>
          <td class="mono">{{ u.home }}</td>
          <td class="mono">{{ u.shell }}</td>
        </tr>
      </tbody>
    </table>
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
const session = useSession();

const filtered = computed(() =>
  items.value.filter((u) => (showSystem.value || !u.is_system) && u.name.includes(q.value))
);

onMounted(async () => {
  items.value = (await api.get("/users")).items;
  who.value = await api.get("/users/whoami");
  picked.value = session.linuxUser;
});

async function apply() {
  const user = items.value.find((u) => u.name === picked.value);
  await session.setIdentity(picked.value, user?.home || session.cwd);
  who.value = await api.get("/users/whoami");
}
</script>

<style scoped>
.lead { color: var(--muted); max-width: 640px; }
.toolbar { display: flex; gap: 12px; align-items: center; margin: 16px 0; }
input, button { border: 1px solid var(--line); border-radius: 8px; padding: 8px 12px; background: var(--card); }
.primary { background: var(--accent); color: #fff; border-color: var(--accent); }
.chk { color: var(--muted); font-size: 13px; display: flex; gap: 6px; align-items: center; }
table { width: 100%; border-collapse: collapse; background: var(--card); border-radius: 12px; overflow: hidden; }
th, td { text-align: left; padding: 10px 12px; border-bottom: 1px solid var(--line); font-size: 14px; }
.mono { font-family: var(--mono); font-size: 12px; }
tr.on { background: #f3ead4; }
tr { cursor: pointer; }
.who { font-family: var(--mono); font-size: 12px; color: var(--muted); }
</style>
