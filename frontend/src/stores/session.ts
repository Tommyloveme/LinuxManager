import { defineStore } from "pinia";
import { api, clearToken, getToken, setToken } from "@/api/client";

export interface ModuleSpec {
  key: string;
  title: string;
  description: string;
  api_prefix: string;
  nav_group: string;
  icon: string;
}

export const useSession = defineStore("session", {
  state: () => ({
    token: getToken(),
    username: "",
    mustChange: false,
    linuxUser: sessionStorage.getItem("cedar.linux_user") || "",
    cwd: sessionStorage.getItem("cedar.cwd") || "",
    hostUser: "",
    modules: [] as ModuleSpec[],
  }),
  actions: {
    persistIdentity() {
      sessionStorage.setItem("cedar.linux_user", this.linuxUser);
      sessionStorage.setItem("cedar.cwd", this.cwd);
    },
    async login(username: string, password: string) {
      const data = await api.post("/auth/login", { username, password });
      this.token = data.token;
      setToken(data.token);
      this.username = data.user.username;
      this.mustChange = data.user.must_change_password;
      this.modules = data.modules;
      await this.refresh();
    },
    async refresh() {
      if (!this.token) return;
      const data = await api.get("/auth/me");
      this.username = data.user.username;
      this.mustChange = data.user.must_change_password;
      this.linuxUser = data.identity.linux_user;
      this.cwd = data.identity.cwd;
      this.hostUser = data.identity.host_user;
      this.modules = data.modules;
      this.persistIdentity();
    },
    async setIdentity(linuxUser: string, cwd: string) {
      await api.put("/auth/identity", { linux_user: linuxUser, cwd });
      this.linuxUser = linuxUser;
      this.cwd = cwd;
      this.persistIdentity();
    },
    logout() {
      this.token = "";
      this.username = "";
      clearToken();
    },
  },
});
