const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
const TOKEN_KEY = "ideaform_token";

export type Project = {
  id: string;
  title: string;
  category: "business" | "software" | "technology";
  help_level: string;
  status: string;
  created_at: string;
  updated_at: string;
};

export type Requirement = {
  id: string;
  req_type: string;
  description: string;
  priority: "must" | "should" | "could" | null;
  source: string | null;
  confirmed: boolean;
};

export type ProjectDetail = Project & {
  version: {
    id: string;
    version_no: number;
    idea_text: string;
    structured_idea: Record<string, unknown> | null;
  } | null;
  requirements: Requirement[];
};

export function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return window.localStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string): void {
  window.localStorage.setItem(TOKEN_KEY, token);
}

export function clearToken(): void {
  window.localStorage.removeItem(TOKEN_KEY);
}

export class ApiError extends Error {}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const token = getToken();
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(init.headers as Record<string, string>),
  };
  if (token) headers.Authorization = `Bearer ${token}`;

  const res = await fetch(`${API_URL}${path}`, { ...init, headers, cache: "no-store" });

  if (res.status === 204) return undefined as T;
  const body = await res.json().catch(() => null);
  if (!res.ok) {
    const detail = body && typeof body.detail === "string" ? body.detail : `HTTP ${res.status}`;
    throw new ApiError(detail);
  }
  return body as T;
}

export const api = {
  register: (email: string, password: string, full_name?: string) =>
    request("/auth/register", {
      method: "POST",
      body: JSON.stringify({ email, password, full_name }),
    }),
  login: (email: string, password: string) =>
    request<{ access_token: string }>("/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    }),
  projects: () => request<Project[]>("/projects"),
  createProject: (payload: {
    title: string;
    idea_text: string;
    category?: string;
    help_level: string;
  }) => request<ProjectDetail>("/projects", { method: "POST", body: JSON.stringify(payload) }),
  project: (id: string) => request<ProjectDetail>(`/projects/${id}`),
  understand: (id: string) =>
    request<{ run_id: string; status: string }>(`/projects/${id}/understand`, {
      method: "POST",
    }),
  updateRequirements: (
    id: string,
    requirements: { id: string; description?: string; priority?: string; confirmed?: boolean }[],
  ) =>
    request<Requirement[]>(`/projects/${id}/requirements`, {
      method: "PATCH",
      body: JSON.stringify({ requirements }),
    }),
};
