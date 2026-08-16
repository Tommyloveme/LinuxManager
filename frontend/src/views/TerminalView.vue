<template>
  <div class="wrap">
    <div class="bar card">
      <span class="mono">{{ liveUser || session.linuxUser || session.hostUser }}</span>
      <span class="sep">·</span>
      <span class="mono cwd">{{ liveCwd || session.cwd }}</span>
      <span class="hint">当前目录随 shell 里的 `cd` 实时更新。</span>
    </div>
    <div class="term card" ref="host"></div>
  </div>
</template>

<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref } from "vue";
import { Terminal } from "@xterm/xterm";
import { FitAddon } from "@xterm/addon-fit";
import { WebLinksAddon } from "@xterm/addon-web-links";
import "@xterm/xterm/css/xterm.css";
import { getToken } from "@/api/client";
import { useSession } from "@/stores/session";

const session = useSession();
const host = ref<HTMLElement | null>(null);
const liveUser = ref("");
const liveCwd = ref("");
let term: Terminal | null = null;
let socket: WebSocket | null = null;
let fit: FitAddon | null = null;

onMounted(() => {
  if (!host.value) return;
  term = new Terminal({
    cursorBlink: true,
    fontFamily: "IBM Plex Mono, ui-monospace, monospace",
    fontSize: 13,
    theme: {
      background: "#171411",
      foreground: "#efe6d4",
      cursor: "#3d8f6a",
      selectionBackground: "#3d8f6a55",
    },
  });
  fit = new FitAddon();
  term.loadAddon(fit);
  term.loadAddon(new WebLinksAddon());
  term.open(host.value);
  fit.fit();
  // 后端 PROMPT_COMMAND 通过 OSC 0 上报 "user@host:cwd"
  term.onTitleChange((title) => {
    const at = title.indexOf("@");
    const colon = title.indexOf(":", at);
    if (at > 0 && colon > at) {
      liveUser.value = title.slice(0, at);
      liveCwd.value = title.slice(colon + 1);
    } else if (title) {
      liveCwd.value = title;
    }
  });
  const proto = location.protocol === "https:" ? "wss" : "ws";
  const qs = new URLSearchParams({
    token: getToken(),
    user: session.linuxUser,
    cwd: session.cwd,
    cols: String(term.cols),
    rows: String(term.rows),
  });
  socket = new WebSocket(`${proto}://${location.host}/api/v1/ws/terminal?${qs}`);
  socket.binaryType = "arraybuffer";
  socket.onmessage = (ev) => {
    if (typeof ev.data === "string") {
      try {
        const msg = JSON.parse(ev.data);
        if (msg.type === "ready") term?.writeln(`\r\n# ${msg.user}  ${msg.cwd}`);
        if (msg.type === "error") term?.writeln(`\r\n${msg.message}`);
      } catch {
        term?.write(ev.data);
      }
    } else {
      term?.write(new Uint8Array(ev.data as ArrayBuffer));
    }
  };
  term.onData((data) => {
    if (socket?.readyState === WebSocket.OPEN) {
      socket.send(JSON.stringify({ type: "input", data }));
    }
  });
  const onResize = () => {
    fit?.fit();
    if (term && socket?.readyState === WebSocket.OPEN) {
      socket.send(JSON.stringify({ type: "resize", cols: term.cols, rows: term.rows }));
    }
  };
  window.addEventListener("resize", onResize);
  (host.value as HTMLElement & { _onResize?: () => void })._onResize = onResize;
});

onBeforeUnmount(() => {
  const extra = host.value as (HTMLElement & { _onResize?: () => void }) | null;
  if (extra?._onResize) window.removeEventListener("resize", extra._onResize);
  socket?.close();
  term?.dispose();
});
</script>

<style scoped>
.wrap { display: flex; flex-direction: column; gap: 12px; height: calc(100vh - 120px); }
.bar { display: flex; gap: 10px; align-items: baseline; flex-wrap: wrap; }
.card { background: var(--card); border: 1px solid var(--line); border-radius: var(--radius); padding: 12px 16px; }
.term { flex: 1; background: #171411; padding: 10px; min-height: 360px; }
.mono { font-family: var(--mono); }
.cwd { color: #3d8f6a; }
.hint { color: var(--muted); font-size: 12px; margin-left: auto; }
.sep { color: var(--muted); }
</style>
