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
        { path: "users", component: () => import("@/views/UsersView.vue") },
        { path: "scripts", component: () => import("@/views/ScriptsView.vue") },
        { path: "playbooks", component: () => import("@/views/PlaybooksView.vue") },
        { path: "files", component: () => import("@/views/FilesView.vue") },
        { path: "process", component: () => import("@/views/ProcessView.vue") },
        { path: "services", component: () => import("@/views/ServicesView.vue") },
        { path: "terminal", component: () => import("@/views/TerminalView.vue") },
        { path: "jobs", component: () => import("@/views/JobsView.vue") },
        { path: "audit", component: () => import("@/views/AuditView.vue") },
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
