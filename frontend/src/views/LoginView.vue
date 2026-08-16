<template>
  <div class="login">
    <aside>
      <div class="mark">
        <span></span><span></span><span></span>
      </div>
      <h1>把主机操作<br />收进一张桌子。</h1>
      <p>脚本、批处理、文件打包、进程与终端，同一套身份、同一条审计。为 SUSE 上的日常运维准备，而不是再做一个花哨面板。</p>
    </aside>
    <main>
      <form @submit.prevent="submit">
        <p class="kicker">Cedar Console</p>
        <h2>登录控制台</h2>
        <label>用户名<input v-model="username" autocomplete="username" /></label>
        <label>密码<input v-model="password" type="password" autocomplete="current-password" /></label>
        <p v-if="error" class="err">{{ error }}</p>
        <button type="submit" :disabled="loading">{{ loading ? "登录中…" : "进入" }}</button>
        <p class="hint">默认 admin / changeme，部署后请立刻改密。</p>
      </form>
    </main>
  </div>
</template>

<script setup lang="ts">
import { ref } from "vue";
import { useRouter } from "vue-router";
import { useSession } from "@/stores/session";

const username = ref("admin");
const password = ref("");
const error = ref("");
const loading = ref(false);
const session = useSession();
const router = useRouter();

async function submit() {
  error.value = "";
  loading.value = true;
  try {
    await session.login(username.value, password.value);
    router.push("/");
  } catch (err) {
    error.value = err instanceof Error ? err.message : "登录失败";
  } finally {
    loading.value = false;
  }
}
</script>

<style scoped>
.login {
  min-height: 100vh;
  display: grid;
  grid-template-columns: 1.1fr 0.9fr;
}
aside {
  background: #171411;
  color: #efe6d4;
  padding: 72px;
  display: flex;
  flex-direction: column;
  justify-content: center;
}
.mark {
  width: 42px;
  height: 42px;
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 4px;
  align-items: end;
  margin-bottom: 36px;
}
.mark span { background: #d7c4a3; border-radius: 2px 2px 0 0; }
.mark span:nth-child(1) { height: 18px; }
.mark span:nth-child(2) { height: 36px; background: #3d8f6a; }
.mark span:nth-child(3) { height: 26px; }
h1 {
  font-family: var(--serif);
  font-size: 44px;
  font-weight: 500;
  line-height: 1.15;
  margin: 0 0 20px;
}
aside p {
  max-width: 420px;
  color: #cbbfae;
  line-height: 1.7;
}
main {
  display: grid;
  place-items: center;
  padding: 40px;
}
form {
  width: min(380px, 100%);
  background: var(--card);
  border: 1px solid var(--line);
  border-radius: 18px;
  padding: 32px;
  box-shadow: var(--shadow);
}
.kicker {
  letter-spacing: 0.16em;
  text-transform: uppercase;
  font-size: 11px;
  color: var(--muted);
  margin: 0 0 8px;
}
h2 {
  font-family: var(--serif);
  font-weight: 500;
  margin: 0 0 24px;
}
label {
  display: flex;
  flex-direction: column;
  gap: 6px;
  font-size: 13px;
  color: var(--muted);
  margin-bottom: 14px;
}
input {
  border: 1px solid var(--line);
  border-radius: 10px;
  padding: 10px 12px;
  background: #fff;
}
button {
  width: 100%;
  margin-top: 8px;
  background: var(--accent);
  color: var(--accent-ink);
  border: 0;
  border-radius: 10px;
  padding: 12px;
  font-weight: 600;
}
.err { color: var(--danger); font-size: 13px; }
.hint { color: var(--muted); font-size: 12px; margin-top: 16px; }
@media (max-width: 860px) {
  .login { grid-template-columns: 1fr; }
  aside { display: none; }
}
</style>
