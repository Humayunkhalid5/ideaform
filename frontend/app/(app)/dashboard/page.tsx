"use client";

import {
  ArrowRight,
  Briefcase,
  Check,
  Code,
  Cpu,
  Eye,
  FolderOpen,
  LayoutGrid,
  MoreVertical,
  Plus,
  Rows3,
  Search,
  Trash2,
  TrendingUp,
} from "lucide-react";
import Link from "next/link";
import { useCallback, useEffect, useMemo, useState } from "react";

import { EmptyState } from "@/components/states/EmptyState";
import { ErrorNotice } from "@/components/states/ErrorNotice";
import { StatusBadge } from "@/components/ui/badge";
import { buttonStyles } from "@/components/ui/button";
import { PageSkeleton } from "@/components/ui/skeleton";
import { api } from "@/lib/api";
import { APP_NAME, DISCLAIMER } from "@/lib/constants";
import { HELP_LEVEL_LABEL, STATUS_LABEL } from "@/lib/idea";
import type { Category, Project, ProjectStatus } from "@/lib/types";
import { cn, formatRelative } from "@/lib/utils";

const CATEGORY_ICON: Record<Category, typeof Code> = {
  business: Briefcase,
  software: Code,
  technology: Cpu,
};

type ViewMode = "grid" | "list";

const STATUS_DETAIL: Record<ProjectStatus, string> = {
  draft: "No extraction yet. Open the idea and run the understanding engine.",
  analysing: "The understanding engine is reading this version.",
  ready: "Structure, gaps and requirements are stored for this version.",
  failed: "The last extraction stopped early. Open the project to retry.",
  archived: "Archived — kept for reference only.",
};

function ProjectMenu({ onDelete }: { onDelete: () => void }) {
  const [open, setOpen] = useState(false);
  return (
    <div className="relative">
      <button
        type="button"
        aria-label="Project actions"
        aria-expanded={open}
        onClick={() => setOpen((value) => !value)}
        className="grid size-7 place-items-center rounded-lg text-muted transition-colors hover:bg-surface-soft hover:text-ink"
      >
        <MoreVertical className="size-4" />
      </button>
      {open && (
        <>
          <div className="fixed inset-0 z-20" onClick={() => setOpen(false)} aria-hidden="true" />
          <div className="absolute right-0 z-30 mt-1 w-36 rounded-lg border border-line bg-surface py-1 shadow-e2">
            <button
              type="button"
              onClick={() => {
                setOpen(false);
                onDelete();
              }}
              className="flex w-full items-center gap-2 px-3 py-2 text-left text-[13px] text-danger transition-colors hover:bg-danger-soft"
            >
              <Trash2 className="size-3.5" /> Delete project
            </button>
          </div>
        </>
      )}
    </div>
  );
}

function StatTile({
  label,
  value,
  icon: Icon,
  tone,
  footer,
}: {
  label: string;
  value: number;
  icon: typeof Code;
  tone: string;
  footer: React.ReactNode;
}) {
  return (
    <div className="flex flex-col justify-between rounded-xl border border-line bg-surface p-5 shadow-sm">
      <div className="flex items-start justify-between gap-3">
        <div>
          <span className="t-label text-muted">{label}</span>
          <div className="t-hero mt-1 tabular text-ink">{value}</div>
        </div>
        <span className={cn("grid size-10 place-items-center rounded-lg", tone)}>
          <Icon className="size-[21px]" />
        </span>
      </div>
      <div className="mt-4 flex flex-wrap items-center gap-x-2 gap-y-1 border-t border-line/70 pt-3">
        {footer}
      </div>
    </div>
  );
}

export default function DashboardPage() {
  const [projects, setProjects] = useState<Project[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [query, setQuery] = useState("");
  const [category, setCategory] = useState<Category | "all">("all");
  const [status, setStatus] = useState<ProjectStatus | "all">("all");
  const [view, setView] = useState<ViewMode>("grid");

  const load = useCallback(async () => {
    setError(null);
    try {
      setProjects(await api.projects());
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not load your projects.");
      setProjects([]);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const counts = useMemo(() => {
    const list = projects ?? [];
    return {
      all: list.length,
      draft: list.filter((project) => project.status === "draft").length,
      analysing: list.filter((project) => project.status === "analysing").length,
      ready: list.filter((project) => project.status === "ready").length,
    };
  }, [projects]);

  const visible = useMemo(() => {
    const list = projects ?? [];
    const needle = query.trim().toLowerCase();
    return list.filter(
      (project) =>
        (category === "all" || project.category === category) &&
        (status === "all" || project.status === status) &&
        (!needle ||
          project.title.toLowerCase().includes(needle) ||
          HELP_LEVEL_LABEL[project.help_level].toLowerCase().includes(needle)),
    );
  }, [projects, query, category, status]);

  async function remove(project: Project) {
    if (!window.confirm(`Delete “${project.title}”? This cannot be undone.`)) return;
    try {
      await api.deleteProject(project.id);
      setProjects((list) => (list ?? []).filter((item) => item.id !== project.id));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not delete that project.");
    }
  }

  function resetFilters() {
    setQuery("");
    setCategory("all");
    setStatus("all");
  }

  if (!projects) return <PageSkeleton cards={4} />;

  return (
    <div className="flex flex-col gap-6">
      {/* ---------------- Header ---------------- */}
      <header className="flex flex-col justify-between gap-4 sm:flex-row sm:items-center">
        <div>
          <div className="mb-1 flex items-center gap-2 font-mono text-[11px] uppercase tracking-[0.08em] text-muted">
            <span>Workspace portfolio</span>
            <span>•</span>
            <span className="font-medium text-accent">Synced with {APP_NAME}</span>
          </div>
          <h1 className="t-section text-ink">Your projects</h1>
          <p className="t-body mt-0.5 text-muted">
            Manage and inspect the structure extracted from every idea in your workspace.
          </p>
        </div>
        <div className="flex items-center gap-2 self-start sm:self-center">
          <Link href="/projects/new" className={buttonStyles("primary", "md")}>
            <Plus className="size-4" /> New project
          </Link>
        </div>
      </header>

      {error && <ErrorNotice message={error} onRetry={load} />}

      {/* ---------------- Summary tiles ---------------- */}
      <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
        <StatTile
          label="Total projects"
          value={counts.all}
          icon={FolderOpen}
          tone="bg-surface-soft text-primary"
          footer={
            <>
              <span className="inline-flex items-center gap-1 text-[12px] font-medium text-success">
                <span className="size-1.5 rounded-full bg-success" />
                {counts.ready} understood
              </span>
              <span className="text-[12px] text-muted/50">•</span>
              <span className="inline-flex items-center gap-1 text-[12px] font-medium text-accent">
                <span className="size-1.5 rounded-full bg-accent animate-pulse" />
                {counts.analysing} analysing
              </span>
              <span className="text-[12px] text-muted/50">•</span>
              <span className="inline-flex items-center gap-1 text-[12px] text-muted">
                <span className="size-1.5 rounded-full bg-line" />
                {counts.draft} draft
              </span>
            </>
          }
        />
        <StatTile
          label="Understood"
          value={counts.ready}
          icon={Check}
          tone="bg-primary-soft text-primary"
          footer={
            <>
              <span className="font-mono text-[12px] font-medium text-success">
                <TrendingUp className="mr-0.5 inline size-3.5" />
                Phase 1 output
              </span>
              <span className="ml-auto text-[12px] text-muted">
                {counts.all === 0 ? "No ideas yet" : "Versioned records"}
              </span>
            </>
          }
        />
        <StatTile
          label="In progress"
          value={counts.draft + counts.analysing}
          icon={Cpu}
          tone="bg-surface-soft text-accent"
          footer={
            <>
              <span className="rounded bg-surface-soft px-1.5 py-0.5 font-mono text-[11px] font-medium text-accent">
                Live
              </span>
              <span className="font-mono text-[12px] font-medium text-accent">
                {counts.analysing + counts.draft} active
              </span>
              <span className="ml-auto text-[12px] text-muted">Awaiting extraction</span>
            </>
          }
        />
      </div>

      {/* ---------------- Search & filters ---------------- */}
      <div className="rounded-xl border border-line bg-surface p-3 shadow-sm">
        <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
          <div className="relative flex-1">
            <Search className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted" />
            <input
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder="Filter by project title or depth…"
              aria-label="Filter projects"
              className="h-10 w-full rounded-lg bg-canvas pl-9 pr-3 text-[13.5px] text-ink outline-none transition-colors placeholder:text-muted/70 focus:bg-surface-soft focus:ring-4 focus:ring-primary/10"
            />
          </div>

          <div className="flex flex-wrap items-center gap-2">
            <div className="flex h-10 items-center gap-1.5 rounded-lg bg-canvas px-2.5">
              <Briefcase className="size-3.5 text-muted" />
              <label className="sr-only" htmlFor="category-filter">
                Category
              </label>
              <select
                id="category-filter"
                value={category}
                onChange={(event) => setCategory(event.target.value as Category | "all")}
                className="cursor-pointer appearance-none bg-transparent pr-1 text-[13px] text-ink outline-none"
              >
                <option value="all">All categories</option>
                <option value="business">Business</option>
                <option value="software">Software</option>
                <option value="technology">Technology</option>
              </select>
            </div>

            <div className="flex h-10 items-center gap-1.5 rounded-lg bg-canvas px-2.5">
              <Rows3 className="size-3.5 text-muted" />
              <label className="sr-only" htmlFor="status-filter">
                Status
              </label>
              <select
                id="status-filter"
                value={status}
                onChange={(event) => setStatus(event.target.value as ProjectStatus | "all")}
                className="cursor-pointer appearance-none bg-transparent pr-1 text-[13px] text-ink outline-none"
              >
                <option value="all">All statuses</option>
                <option value="draft">{STATUS_LABEL.draft}</option>
                <option value="analysing">{STATUS_LABEL.analysing}</option>
                <option value="ready">{STATUS_LABEL.ready}</option>
                <option value="failed">{STATUS_LABEL.failed}</option>
              </select>
            </div>

            <div className="hidden items-center gap-0.5 rounded-lg bg-canvas p-1 sm:flex">
              {(
                [
                  { id: "grid" as const, icon: LayoutGrid, label: "Grid view" },
                  { id: "list" as const, icon: Rows3, label: "List view" },
                ]
              ).map((option) => (
                <button
                  key={option.id}
                  type="button"
                  aria-label={option.label}
                  aria-pressed={view === option.id}
                  onClick={() => setView(option.id)}
                  className={cn(
                    "grid size-8 place-items-center rounded-md transition-colors",
                    view === option.id
                      ? "bg-surface text-primary shadow-sm"
                      : "text-muted hover:text-ink",
                  )}
                >
                  <option.icon className="size-4" />
                </button>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* ---------------- Project list ---------------- */}
      {visible.length === 0 ? (
        projects.length === 0 ? (
          <EmptyState
            title="No projects yet"
            body="Describe a business, software or technology idea and IdeaForm will extract its structure, gaps and requirements."
            action={
              <Link href="/projects/new" className={buttonStyles("primary", "md")}>
                <Plus className="size-4" /> Start your first project
              </Link>
            }
          />
        ) : (
          <div className="flex flex-col items-center justify-center rounded-xl border border-line bg-surface p-10 text-center shadow-sm">
            <span className="mb-3 grid size-12 place-items-center rounded-full bg-surface-soft text-muted">
              <FolderOpen className="size-5" />
            </span>
            <p className="t-title text-ink">No matching projects found</p>
            <p className="t-body mt-1 max-w-sm text-muted">
              Adjust your search query or reset the category and status filters.
            </p>
            <button
              type="button"
              onClick={resetFilters}
              className={cn(buttonStyles("secondary", "md"), "mt-4")}
            >
              Reset filters
            </button>
          </div>
        )
      ) : view === "grid" ? (
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
          {visible.map((project) => {
            const Icon = CATEGORY_ICON[project.category];
            return (
              <article
                key={project.id}
                className="group flex flex-col justify-between rounded-xl border border-line bg-surface p-5 shadow-sm transition-shadow hover:shadow-e2"
              >
                <div>
                  <div className="mb-3 flex items-start justify-between gap-2">
                    <div className="flex flex-wrap items-center gap-1.5">
                      <StatusBadge status={project.status} />
                      <span className="rounded bg-canvas px-2 py-0.5 text-[12px] capitalize text-muted">
                        {project.category}
                      </span>
                    </div>
                    <ProjectMenu onDelete={() => remove(project)} />
                  </div>

                  <div className="flex items-center gap-2">
                    <span className="grid size-7 place-items-center rounded-lg bg-surface-soft text-primary">
                      <Icon className="size-3.5" />
                    </span>
                    <h2 className="t-title truncate text-ink transition-colors group-hover:text-primary">
                      {project.title}
                    </h2>
                  </div>
                  <p className="t-body mt-1.5 line-clamp-2 text-muted">
                    {STATUS_DETAIL[project.status]}
                  </p>

                  <div className="mt-4 rounded-lg bg-canvas p-3.5">
                    <div className="mb-2 flex items-center justify-between">
                      <span className="t-label text-muted">Project record</span>
                      <span className="font-mono text-[11.5px] text-muted">
                        {HELP_LEVEL_LABEL[project.help_level]}
                      </span>
                    </div>
                    <dl className="grid grid-cols-2 gap-x-4 gap-y-1.5 font-mono text-[11.5px]">
                      <div className="flex items-center justify-between">
                        <dt className="text-muted">Created</dt>
                        <dd className="font-medium text-ink">{formatRelative(project.created_at)}</dd>
                      </div>
                      <div className="flex items-center justify-between">
                        <dt className="text-muted">Updated</dt>
                        <dd className="font-medium text-ink">{formatRelative(project.updated_at)}</dd>
                      </div>
                      <div className="flex items-center justify-between">
                        <dt className="text-muted">Category</dt>
                        <dd className="font-medium capitalize text-ink">{project.category}</dd>
                      </div>
                      <div className="flex items-center justify-between">
                        <dt className="text-muted">Status</dt>
                        <dd className="font-medium text-ink">{STATUS_LABEL[project.status]}</dd>
                      </div>
                    </dl>
                  </div>
                </div>

                <div className="mt-4 flex items-center justify-between border-t border-line/70 pt-3 text-[12px] text-muted">
                  <span className="inline-flex items-center gap-1">
                    <Eye className="size-3.5" /> {formatRelative(project.updated_at)}
                  </span>
                  <Link
                    href={`/projects/${project.id}`}
                    className="inline-flex items-center gap-1 text-[13px] font-medium text-primary hover:text-primary-hover"
                  >
                    View dossier <ArrowRight className="size-3.5" />
                  </Link>
                </div>
              </article>
            );
          })}
        </div>
      ) : (
        <div className="overflow-hidden rounded-xl border border-line bg-surface shadow-sm">
          {visible.map((project, index) => (
            <Link
              key={project.id}
              href={`/projects/${project.id}`}
              className={cn(
                "flex items-center gap-3 px-4 py-3 transition-colors hover:bg-surface-soft",
                index > 0 && "border-t border-line",
              )}
            >
              <span className="grid size-8 shrink-0 place-items-center rounded-lg bg-surface-soft text-primary">
                {(() => {
                  const Icon = CATEGORY_ICON[project.category];
                  return <Icon className="size-4" />;
                })()}
              </span>
              <div className="min-w-0 flex-1">
                <p className="truncate text-[13.5px] font-medium text-ink">{project.title}</p>
                <p className="truncate text-[12px] text-muted">
                  {HELP_LEVEL_LABEL[project.help_level]} · updated{" "}
                  {formatRelative(project.updated_at)}
                </p>
              </div>
              <StatusBadge status={project.status} />
              <ArrowRight className="size-4 shrink-0 text-muted" />
            </Link>
          ))}
        </div>
      )}

      {/* ---------------- Honesty banner ---------------- */}
      <div className="flex flex-col justify-between gap-2 rounded-xl bg-surface-soft px-4 py-3 text-[12px] text-muted sm:flex-row sm:items-center">
        <span className="flex items-center gap-2">
          <Check className="size-3.5 text-success" />
          {DISCLAIMER}
        </span>
        <span className="font-mono text-[11px]">Understanding engine · phase 1</span>
      </div>
    </div>
  );
}
