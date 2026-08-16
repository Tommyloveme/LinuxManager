<template>
  <div class="card">
    <h3>修改控制台密码</h3>
    <form @submit.prevent="change">
      <label>原密码<input v-model="oldPassword" type="password" /></label>
      <label>新密码<input v-model="nextPassword" type="password" /></label>
      <button class="primary" type="submit">保存</button>
      <p v-if="msg">{{ msg }}</p>
    </form>
    <h3>关于</h3>
    <p class="muted">Cedar 1.0.0 · 模块化主机运维控制台。新增能力请看 docs/ARCHITECTURE.md 与 docs/REPO_GUIDE.md。</p>
  </div>
</template>

<script setup lang="ts">
import { ref } from "vue";
import { api } from "@/api/client";

const oldPassword = ref("");
const nextPassword = ref("");
const msg = ref("");

async function change() {
  await api.post("/auth/password", { old_password: oldPassword.value, new_password: nextPassword.value });
  msg.value = "密码已更新";
  oldPassword.value = "";
  nextPassword.value = "";
}
</script>

<style scoped>
.card { background: var(--card); border: 1px solid var(--line); border-radius: var(--radius); padding: 24px; max-width: 520px; }
h3 { font-family: var(--serif); font-weight: 500; }
label { display: flex; flex-direction: column; gap: 6px; margin-bottom: 12px; color: var(--muted); }
input, button { border: 1px solid var(--line); border-radius: 8px; padding: 8px 12px; }
.primary { background: var(--accent); color: #fff; border-color: var(--accent); }
.muted { color: var(--muted); line-height: 1.6; }
</style>
