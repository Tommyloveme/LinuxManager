import { createRouter, createWebHistory } from "vue-router";
import { getToken } from "@/api/client";

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: "/login", component: () => import("@/views/LoginView.vue") },
    {
      path: "/",
      component: () => import("@/layouts/AppLayout.vue"),
      children: [
        { path: "", component: () => import("@/views/OverviewView.vue") },
        { path: "monitor", component: () => import("@/views/MonitorView.vue") },
        { path: "users", component: () => import("@/views/UsersView.vue") },
        { path: "scripts", component: () => import("@/views/ScriptsView.vue") },
        { path: "files", component: () => import("@/views/FilesView.vue") },
        { path: "terminal", component: () => import("@/views/TerminalView.vue") },
        { path: "settings", component: () => import("@/views/SettingsView.vue") },
      ],
    },
  ],
});

router.beforeEach((to) => {
  if (to.path !== "/login" && !getToken()) return "/login";
  if (to.path === "/login" && getToken()) return "/";
  return true;
});

export default router;
