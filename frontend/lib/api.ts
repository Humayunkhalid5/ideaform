import type {
  Project,
  ProjectDetail,
  Requirement,
  Run,
  User,
} from "./types";

export const API_URL =
  process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

const TOKEN_KEY = "ideaform_token";

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

export class ApiError extends Error {
  status: number;

  constructor(message: string, status: number) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

function detailMessage(body: unknown, status: number): string {
  if (body && typeof body === "object") {
    const detail = (body as { detail?: unknown }).detail;
    if (typeof detail === "string") return detail;
    if (Array.isArray(detail) && detail.length > 0) {
      const first = detail[0] as { msg?: string; loc?: string[] };
      if (first?.msg) {
        const field = first.loc?.filter((part) => part !== "body").join(".");
        return field ? `${field}: ${first.msg}` : first.msg;
      }
    }
  }
  return `Request failed (HTTP ${status}).`;
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const token = getToken();
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...((init.headers as Record<string, string> | undefined) ?? {}),
  };
  if (token) headers.Authorization = `Bearer ${token}`;

  let response: Response;
  try {
    response = await fetch(`${API_URL}${path}`, {
      ...init,
      headers,
      cache: "no-store",
    });
  } catch {
    throw new ApiError(
      "Cannot reach the IdeaForm API. Is the backend running on port 8000?",
      0,
    );
  }

  if (response.status === 204) return undefined as T;

  const body = await response.json().catch(() => null);
  if (!response.ok) throw new ApiError(detailMessage(body, response.status), response.status);
  return body as T;
}

export const api = {
  health: () => request<{ status: string; service: string }>("/health"),
  register: (email: string, password: string, full_name?: string) =>
    request<User>("/auth/register", {
      method: "POST",
      body: JSON.stringify({ email, password, full_name: full_name || null }),
    }),
  login: (email: string, password: string) =>
    request<{ access_token: string; token_type: string; expires_in: number }>("/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    }),
  me: () => request<User>("/auth/me"),
  projects: () => request<Project[]>("/projects"),
  createProject: (payload: {
    title: string;
    idea_text: string;
    category?: string;
    help_level: string;
  }) => request<ProjectDetail>("/projects", { method: "POST", body: JSON.stringify(payload) }),
  project: (id: string) => request<ProjectDetail>(`/projects/${id}`),
  updateProject: (
    id: string,
    payload: Partial<Pick<Project, "title" | "category" | "help_level" | "status">>,
  ) => request<Project>(`/projects/${id}`, { method: "PATCH", body: JSON.stringify(payload) }),
  deleteProject: (id: string) =>
    request<void>(`/projects/${id}`, { method: "DELETE" }),
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
  run: (id: string) => request<Run>(`/runs/${id}`),
};
