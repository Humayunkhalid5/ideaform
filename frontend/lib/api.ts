import type {
  Artifact,
  ArtifactType,
  Blueprint,
  Comparison,
  ExportFormat,
  ProjectHistory,
  ReportsResponse,
  TrackedRun,
  Decision,
  Evaluation,
  Project,
  ProjectDetail,
  Requirement,
  Run,
  User,
  KnowledgeStats,
  RunWithOutput,
  ScrapeJob,
  SearchResult,
  Source,
  SourceDetail,
  VersionDetail,
  VersionSummary,
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
  const isForm = typeof FormData !== "undefined" && init.body instanceof FormData;
  const headers: Record<string, string> = {
    // the browser sets the multipart boundary itself for FormData bodies
    ...(isForm ? {} : { "Content-Type": "application/json" }),
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
  regenerateRequirements: (id: string) =>
    request<{ run_id: string; status: string }>(`/projects/${id}/requirements/regenerate`, {
      method: "POST",
    }),
  versions: (id: string) => request<VersionSummary[]>(`/projects/${id}/versions`),
  version: (id: string, versionNo: number) =>
    request<VersionDetail>(`/projects/${id}/versions/${versionNo}`),
  createVersion: (
    id: string,
    payload: { idea_text: string; change_summary?: string; copy_requirements?: boolean },
  ) =>
    request<ProjectDetail>(`/projects/${id}/versions`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  restoreVersion: (id: string, versionNo: number) =>
    request<ProjectDetail>(`/projects/${id}/versions/${versionNo}/restore`, { method: "POST" }),
  run: (id: string) => request<Run>(`/runs/${id}`),
  projectRuns: (id: string, agentName?: string) =>
    request<RunWithOutput[]>(
      `/runs/project/${id}${agentName ? `?agent_name=${encodeURIComponent(agentName)}` : ""}`,
    ),
  research: (id: string, payload: { queries?: string[]; urls?: string[] } = {}) =>
    request<{ run_id: string; status: string }>(`/projects/${id}/research`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  sources: (id: string) => request<Source[]>(`/projects/${id}/sources`),
  source: (id: string, sourceId: string) =>
    request<SourceDetail>(`/projects/${id}/sources/${sourceId}`),
  deleteSource: (id: string, sourceId: string) =>
    request<void>(`/projects/${id}/sources/${sourceId}`, { method: "DELETE" }),
  uploadDocument: (id: string, file: File) => {
    const form = new FormData();
    form.append("file", file);
    return request<{ status: "created" | "duplicate"; source: Source }>(
      `/projects/${id}/documents`,
      { method: "POST", body: form },
    );
  },
  search: (
    id: string,
    payload: { query: string; mode?: "hybrid" | "vector" | "keyword"; kbs?: string[]; k?: number },
  ) =>
    request<SearchResult>(`/projects/${id}/search`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  crawl: (id: string) => request<ScrapeJob[]>(`/projects/${id}/crawl?limit=1`),
  knowledgeStats: () => request<KnowledgeStats>("/knowledge/stats"),
  evaluate: (id: string) =>
    request<{ run_id: string; status: string }>(`/projects/${id}/evaluate`, { method: "POST" }),
  evaluations: (id: string, versionNo?: number) =>
    request<Evaluation[]>(
      `/projects/${id}/evaluations${versionNo ? `?version=${versionNo}` : ""}`,
    ),
  improve: (
    id: string,
    payload: {
      evaluation_id?: string;
      decisions: { improvement_id: string; decision: Decision; edited_text?: string }[];
      note?: string;
    },
  ) =>
    request<{ run_id: string; status: string }>(`/projects/${id}/improve`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  compare: (id: string, a: number, b: number) =>
    request<Comparison>(`/projects/${id}/compare?a=${a}&b=${b}`),
  generateBlueprint: (id: string) =>
    request<{ run_id: string; status: string }>(`/projects/${id}/blueprint`, { method: "POST" }),
  blueprint: (id: string, versionNo?: number) =>
    request<Blueprint>(`/projects/${id}/artifacts${versionNo ? `?version=${versionNo}` : ""}`),
  artifactHistory: (id: string, type: ArtifactType) =>
    request<Artifact[]>(`/projects/${id}/artifacts/${type}/history`),
  regenerateArtifact: (id: string, type: ArtifactType, instructions?: string) =>
    request<{ run_id: string; status: string }>(`/projects/${id}/artifacts/${type}/regenerate`, {
      method: "POST",
      body: JSON.stringify({ instructions: instructions || null }),
    }),
  editArtifact: (artifactId: string, content: string) =>
    request<Artifact>(`/artifacts/${artifactId}`, { method: "PATCH", body: JSON.stringify({ content }) }),
  analyse: (id: string, depth?: string) =>
    request<{ run_id: string; status: string; depth: string }>(`/projects/${id}/analyse`, {
      method: "POST",
      body: JSON.stringify(depth ? { depth } : {}),
    }),
  trackedRun: (runId: string) => request<TrackedRun>(`/runs/${runId}`),
  reports: (id: string, versionNo?: number) =>
    request<ReportsResponse>(`/projects/${id}/reports${versionNo ? `?version=${versionNo}` : ""}`),
  rebuildReports: (id: string) => request<ReportsResponse>(`/projects/${id}/reports`, { method: "POST" }),
  history: (id: string) => request<ProjectHistory>(`/projects/${id}/history`),
  /** Downloads an export and returns the file name the server chose. */
  exportProject: async (id: string, format: ExportFormat, versionNo?: number): Promise<{ filename: string; bytes: number }> => {
    const token = getToken();
    const query = new URLSearchParams({ format, ...(versionNo ? { version: String(versionNo) } : {}) });
    let response: Response;
    try {
      response = await fetch(`${API_URL}/projects/${id}/export?${query}`, {
        method: "POST",
        headers: token ? { Authorization: `Bearer ${token}` } : {},
      });
    } catch {
      throw new ApiError("Cannot reach the IdeaForm API. Is the backend running on port 8000?", 0);
    }
    if (!response.ok) {
      const body = await response.json().catch(() => null);
      throw new ApiError(detailMessage(body, response.status), response.status);
    }
    const blob = await response.blob();
    const disposition = response.headers.get("Content-Disposition") ?? "";
    const filename = /filename="([^"]+)"/.exec(disposition)?.[1] ?? `ideaform-export.${format}`;
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    link.remove();
    setTimeout(() => URL.revokeObjectURL(url), 2000);
    return { filename, bytes: blob.size };
  },
};
