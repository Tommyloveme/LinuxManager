<template>
  <div class="shell">
    <aside class="side">
      <div class="brand">
        <div class="mark" aria-hidden="true">
          <span></span><span></span><span></span>
        </div>
        <div>
          <div class="name">Cedar</div>
          <div class="tag">主机控制台</div>
        </div>
      </div>
      <nav>
        <p class="group">观察</p>
        <RouterLink to="/">总览</RouterLink>
        <RouterLink to="/jobs">作业</RouterLink>
        <RouterLink to="/audit">审计</RouterLink>
        <p class="group">操作</p>
        <RouterLink to="/users">Linux 用户</RouterLink>
        <RouterLink to="/scripts">脚本</RouterLink>
        <RouterLink to="/playbooks">批处理</RouterLink>
        <RouterLink to="/files">文件</RouterLink>
        <RouterLink to="/process">进程</RouterLink>
        <RouterLink to="/services">服务</RouterLink>
        <RouterLink to="/terminal">终端</RouterLink>
      </nav>
      <div class="side-foot">
        <RouterLink to="/settings" class="quiet">设置</RouterLink>
        <button class="quiet" @click="logout">退出</button>
      </div>
    </aside>
    <div class="main">
      <header class="top">
        <div class="crumb">{{ title }}</div>
        <div class="identity">
          <label>
            用户
            <input v-model="linuxUser" @change="saveIdentity" />
          </label>
          <label class="cwd">
            目录
            <input v-model="cwd" @change="saveIdentity" />
          </label>
          <span class="who">{{ session.username }}</span>
        </div>
      </header>
      <section class="page">
        <RouterView />
      </section>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import { useSession } from "@/stores/session";

const session = useSession();
const route = useRoute();
const router = useRouter();
const linuxUser = ref(session.linuxUser);
const cwd = ref(session.cwd);

const titles: Record<string, string> = {
  "/": "总览",
  "/users": "Linux 用户",
  "/scripts": "脚本库",
  "/playbooks": "批处理",
  "/files": "文件与同步",
  "/process": "进程",
  "/services": "systemd 服务",
  "/terminal": "终端",
  "/jobs": "作业",
  "/audit": "审计",
  "/settings": "设置",
};

const title = computed(() => titles[route.path] || "Cedar");

onMounted(async () => {
  try {
    await session.refresh();
    linuxUser.value = session.linuxUser;
    cwd.value = session.cwd;
  } catch {
    session.logout();
    router.push("/login");
  }
});

async function saveIdentity() {
  await session.setIdentity(linuxUser.value, cwd.value);
}

function logout() {
  session.logout();
  router.push("/login");
}
</script>

<style scoped>
.shell {
  display: grid;
  grid-template-columns: 232px 1fr;
  min-height: 100vh;
}
.side {
  background: var(--sidebar);
  color: var(--sidebar-ink);
  display: flex;
  flex-direction: column;
  padding: 22px 16px 16px;
}
.brand {
  display: flex;
  gap: 12px;
  align-items: center;
  padding: 0 8px 24px;
}
.mark {
  width: 34px;
  height: 34px;
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 3px;
  align-items: end;
}
.mark span {
  background: #d7c4a3;
  border-radius: 2px 2px 0 0;
}
.mark span:nth-child(1) { height: 16px; }
.mark span:nth-child(2) { height: 28px; background: #3d8f6a; }
.mark span:nth-child(3) { height: 22px; }
.name {
  font-family: var(--serif);
  font-size: 22px;
  line-height: 1;
}
.tag {
  color: var(--sidebar-dim);
  font-size: 12px;
  margin-top: 4px;
}
nav {
  display: flex;
  flex-direction: column;
  gap: 2px;
  flex: 1;
}
.group {
  margin: 16px 8px 6px;
  font-size: 11px;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: var(--sidebar-dim);
}
nav a {
  padding: 8px 10px;
  border-radius: 8px;
  color: #d9d0c2;
}
nav a.router-link-exact-active,
nav a.router-link-active {
  background: #2a2622;
  color: #fff;
}
.side-foot {
  display: flex;
  justify-content: space-between;
  padding: 8px;
}
.quiet {
  background: none;
  border: 0;
  color: var(--sidebar-dim);
  padding: 0;
}
.main {
  display: flex;
  flex-direction: column;
  min-width: 0;
}
.top {
  height: 64px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 28px;
  border-bottom: 1px solid var(--line);
  background: rgba(247, 240, 226, 0.86);
  backdrop-filter: blur(8px);
  position: sticky;
  top: 0;
  z-index: 5;
}
.crumb {
  font-family: var(--serif);
  font-size: 22px;
}
.identity {
  display: flex;
  gap: 12px;
  align-items: center;
}
.identity label {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
  color: var(--muted);
}
.identity input {
  border: 1px solid var(--line);
  background: var(--card);
  border-radius: 8px;
  padding: 6px 10px;
  min-width: 120px;
  color: var(--ink);
}
.cwd input {
  min-width: 240px;
  font-family: var(--mono);
  font-size: 12px;
}
.who {
  font-size: 13px;
  color: var(--muted);
}
.page {
  padding: 24px 28px 48px;
}
</style>
