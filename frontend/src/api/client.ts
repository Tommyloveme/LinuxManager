export type Json = Record<string, unknown>;

const TOKEN_KEY = "cedar.token";

export function getToken(): string {
  return localStorage.getItem(TOKEN_KEY) || "";
}

export function setToken(token: string) {
  localStorage.setItem(TOKEN_KEY, token);
}

export function clearToken() {
  localStorage.removeItem(TOKEN_KEY);
}

function headers(): HeadersInit {
  const h: Record<string, string> = { "Content-Type": "application/json" };
  const token = getToken();
  if (token) h.Authorization = `Bearer ${token}`;
  const linux = sessionStorage.getItem("cedar.linux_user");
  const cwd = sessionStorage.getItem("cedar.cwd");
  if (linux) h["X-Linux-User"] = linux;
  if (cwd) h["X-Cwd"] = cwd;
  return h;
}

async function parse(res: Response) {
  const text = await res.text();
  const data = text ? JSON.parse(text) : {};
  if (!res.ok) {
    const detail = data.detail || data.message || res.statusText;
    throw new Error(typeof detail === "string" ? detail : JSON.stringify(detail));
  }
  return data;
}

export const api = {
  get: (path: string) => fetch(`/api/v1${path}`, { headers: headers() }).then(parse),
  post: (path: string, body?: unknown) =>
    fetch(`/api/v1${path}`, { method: "POST", headers: headers(), body: JSON.stringify(body ?? {}) }).then(parse),
  patch: (path: string, body?: unknown) =>
    fetch(`/api/v1${path}`, { method: "PATCH", headers: headers(), body: JSON.stringify(body ?? {}) }).then(parse),
  put: (path: string, body?: unknown) =>
    fetch(`/api/v1${path}`, { method: "PUT", headers: headers(), body: JSON.stringify(body ?? {}) }).then(parse),
  del: (path: string) => fetch(`/api/v1${path}`, { method: "DELETE", headers: headers() }).then(parse),
};
