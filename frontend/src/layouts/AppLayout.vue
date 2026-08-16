<template>
  <div class="shell">
    <aside class="side">
      <div class="brand">
        <div class="mark" aria-hidden="true">
          <span></span><span></span><span></span>
        </div>
        <div>
          <div class="name">Cedar</div>
          <div class="tag">Linux 运维控制台</div>
        </div>
      </div>
      <nav>
        <p class="group">监控中心</p>
        <RouterLink to="/">
          <span class="nav-title">运行概览</span>
          <span class="nav-desc">资源、负载与网络实时摘要</span>
        </RouterLink>
        <RouterLink to="/monitor">
          <span class="nav-title">进程与服务</span>
          <span class="nav-desc">进程治理与 systemd 单元管理</span>
        </RouterLink>
        <p class="group">运维操作</p>
        <RouterLink to="/users">
          <span class="nav-title">执行身份</span>
          <span class="nav-desc">选择并验证 Linux 用户</span>
        </RouterLink>
        <RouterLink to="/scripts">
          <span class="nav-title">脚本中心</span>
          <span class="nav-desc">编辑、保存与批量执行</span>
        </RouterLink>
        <RouterLink to="/files">
          <span class="nav-title">文件管理</span>
          <span class="nav-desc">浏览、预览、上传与下载</span>
        </RouterLink>
        <RouterLink to="/terminal">
          <span class="nav-title">远程终端</span>
          <span class="nav-desc">交互式终端会话</span>
        </RouterLink>
      </nav>
      <div class="side-foot">
        <RouterLink to="/settings" class="quiet">系统设置</RouterLink>
        <button class="quiet" @click="logout">退出登录</button>
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
  "/": "运行概览",
  "/monitor": "进程与服务",
  "/users": "执行身份",
  "/scripts": "脚本中心",
  "/files": "文件管理",
  "/terminal": "远程终端",
  "/settings": "系统设置",
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
  display: flex;
  flex-direction: column;
  gap: 2px;
  padding: 8px 12px;
  border-radius: 9px;
  color: #d9d0c2;
}
nav a .nav-title { font-size: 14px; }
nav a .nav-desc { font-size: 11px; color: var(--sidebar-dim); line-height: 1.3; }
nav a:hover { background: #211d19; }
nav a.router-link-exact-active {
  background: #2a2622;
  color: #fff;
}
nav a.router-link-exact-active .nav-desc { color: #b6ab9a; }
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
