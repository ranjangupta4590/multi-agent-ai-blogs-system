// Frontend API client interacting with FastAPI backend
const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

export class ApiError extends Error {
  code: string;
  status: number;
  details?: Record<string, any>;

  constructor(message: string, code: string = "API_ERROR", status: number = 500, details?: Record<string, any>) {
    super(message);
    this.name = "ApiError";
    this.code = code;
    this.status = status;
    this.details = details;
  }
}

async function request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  const token = typeof window !== "undefined" ? localStorage.getItem("token") : null;
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string>),
  };

  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  const url = `${API_BASE}${endpoint}`;
  try {
    const res = await fetch(url, {
      ...options,
      headers,
      credentials: "include",
    });

    if (res.status === 204) {
      return {} as T;
    }

    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      const err = data.error || {};
      throw new ApiError(
        err.message || `Request failed with status ${res.status}`,
        err.code || "REQUEST_FAILED",
        res.status,
        err.details
      );
    }
    return data as T;
  } catch (err: any) {
    if (err instanceof ApiError) throw err;
    throw new ApiError(err.message || "Network error", "NETWORK_ERROR", 0);
  }
}

export const api = {
  // Auth
  register: (body: any) => request<any>("/auth/register", { method: "POST", body: JSON.stringify(body) }),
  login: (body: any) => request<any>("/auth/login", { method: "POST", body: JSON.stringify(body) }),
  logout: () => request<any>("/auth/logout", { method: "POST" }),
  getMe: () => request<any>("/auth/me"),

  // Providers
  getProviders: () => request<any[]>("/providers/"),
  setActiveProvider: (provider_name: string, model_name?: string) =>
    request<any>("/providers/active", { method: "POST", body: JSON.stringify({ provider_name, model_name }) }),
  configureProvider: (provider_name: string, api_key: string, default_model?: string) =>
    request<any>("/providers/configure", {
      method: "POST",
      body: JSON.stringify({ provider_name, api_key, default_model }),
    }),
  checkProviderHealth: (provider_name: string) => request<any>(`/providers/${provider_name}/health`),

  // Projects
  getProjects: () => request<any[]>("/projects/"),
  createProject: (body: any) => request<any>("/projects/", { method: "POST", body: JSON.stringify(body) }),
  getProject: (id: string) => request<any>(`/projects/${id}`),

  // Articles
  getArticles: (projectId: string) => request<any[]>(`/articles/?project_id=${projectId}`),
  createArticleDraft: (body: any) => request<any>("/articles/", { method: "POST", body: JSON.stringify(body) }),
  getArticle: (id: string) => request<any>(`/articles/${id}`),
  updateArticle: (id: string, body: any) => request<any>(`/articles/${id}`, { method: "PUT", body: JSON.stringify(body) }),
  generateArticle: (id: string) => request<any>(`/articles/${id}/generate`, { method: "POST" }),
  getArticleVersions: (id: string) => request<any[]>(`/articles/${id}/versions`),
  restoreVersion: (id: string, versionNumber: number) =>
    request<any>(`/articles/${id}/versions/${versionNumber}/restore`, { method: "POST" }),

  // Evidence & SEO
  getSources: (id: string) => request<any[]>(`/articles/${id}/sources`),
  getClaims: (id: string) => request<any[]>(`/articles/${id}/claims`),
  getSEO: (id: string) => request<any>(`/articles/${id}/seo`),

  // Publishing
  publishWordPress: (body: any) => request<any>("/publishing/wordpress", { method: "POST", body: JSON.stringify(body) }),

  // Admin
  getUsers: () => request<any[]>("/admin/users"),
  updateUserRole: (userId: string, role: string) =>
    request<any>(`/admin/users/${userId}/role`, { method: "PUT", body: JSON.stringify({ role }) }),
  toggleUserActive: (userId: string, is_active: boolean) =>
    request<any>(`/admin/users/${userId}/active`, { method: "PUT", body: JSON.stringify({ is_active }) }),
  getPrompts: () => request<any[]>("/admin/prompts"),
  createPromptVersion: (promptId: string, system_prompt: string, user_template: string) =>
    request<any>(`/admin/prompts/${promptId}/versions`, {
      method: "POST",
      body: JSON.stringify({ system_prompt, user_template }),
    }),
  getAuditLogs: (limit: number = 100) => request<any[]>(`/admin/audit-logs?limit=${limit}`),
  getAnalytics: () => request<any>("/admin/analytics"),
};
