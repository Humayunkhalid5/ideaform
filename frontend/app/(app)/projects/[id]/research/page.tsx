"use client";

import {
  AlertTriangle,
  ArrowUpRight,
  BookOpen,
  ChevronDown,
  FileUp,
  Globe,
  Library,
  Link2,
  Loader2,
  Search,
  ShieldCheck,
  Sparkles,
  Trash2,
} from "lucide-react";
import { useParams } from "next/navigation";
import { useCallback, useEffect, useMemo, useRef, useState, type ReactNode } from "react";

import { EmptyState } from "@/components/states/EmptyState";
import { ErrorNotice } from "@/components/states/ErrorNotice";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input, Select } from "@/components/ui/field";
import { PageSkeleton } from "@/components/ui/skeleton";
import { api } from "@/lib/api";
import type {
  KnowledgeStats,
  Passage,
  ResearchSummary,
  RunWithOutput,
  ScrapeJob,
  SearchResult,
  Source,
  SourceDetail,
} from "@/lib/types";
import { cn, formatDate, formatRelative } from "@/lib/utils";

type Filter = "all" | "web" | "upload" | "technical";

const FILTERS: { key: Filter; label: string }[] = [
  { key: "all", label: "All sources" },
  { key: "web", label: "Web research" },
  { key: "technical", label: "Technical" },
  { key: "upload", label: "Uploaded" },
];

const KB_LABEL: Record<string, string> = {
  A: "KB-A business",
  B: "KB-B technical",
  C: "Project",
};

const TECHNICAL_TYPES = new Set(["docs", "github"]);

function domainOf(url: string | null): string {
  if (!url) return "uploaded file";
  try {
    return new URL(url).hostname.replace(/^www\./, "");
  } catch {
    return url;
  }
}

function matchesFilter(source: Source, filter: Filter): boolean {
  if (filter === "all") return true;
  if (filter === "upload") return source.source_type === "upload";
  if (filter === "technical") return TECHNICAL_TYPES.has(source.source_type ?? "");
  return source.source_type !== "upload" && !TECHNICAL_TYPES.has(source.source_type ?? "");
}

function Highlight({ text, terms }: { text: string; terms: string[] }) {
  if (terms.length === 0) return <>{text}</>;
  const escaped = terms.map((t) => t.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"));
  const parts = text.split(new RegExp(`(${escaped.join("|")})`, "gi"));
  return (
    <>
      {parts.map((part, i) =>
        terms.some((t) => t.toLowerCase() === part.toLowerCase()) ? (
          <mark key={i} className="rounded bg-primary-soft px-0.5 text-primary">
            {part}
          </mark>
        ) : (
          <span key={i}>{part}</span>
        ),
      )}
    </>
  );
}

function termsFrom(text: string): string[] {
  const stop = new Set(["the", "and", "for", "with", "that", "this", "from", "into", "your", "app"]);
  return Array.from(
    new Set(
      text
        .toLowerCase()
        .split(/[^a-z0-9]+/)
        .filter((w) => w.length > 3 && !stop.has(w)),
    ),
  ).slice(0, 8);
}

function Stat({ label, value, hint, icon }: { label: string; value: ReactNode; hint?: string; icon: ReactNode }) {
  return (
    <Card className="flex items-start gap-3 p-4">
      <span className="grid size-9 shrink-0 place-items-center rounded-lg bg-primary-soft text-primary">
        {icon}
      </span>
      <div className="min-w-0">
        <p className="t-label text-muted">{label}</p>
        <p className="mt-0.5 font-mono text-[20px] font-semibold tabular text-ink">{value}</p>
        {hint && <p className="mt-0.5 truncate text-[11.5px] text-muted">{hint}</p>}
      </div>
    </Card>
  );
}

function SourceCard({
  source,
  marker,
  terms,
  projectId,
  onDelete,
}: {
  source: Source;
  marker: number;
  terms: string[];
  projectId: string;
  onDelete: (source: Source) => void;
}) {
  const [open, setOpen] = useState(false);
  const [detail, setDetail] = useState<SourceDetail | null>(null);
  const [loading, setLoading] = useState(false);

  async function toggle() {
    const next = !open;
    setOpen(next);
    if (next && !detail) {
      setLoading(true);
      try {
        setDetail(await api.source(projectId, source.id));
      } finally {
        setLoading(false);
      }
    }
  }

  return (
    <li className="if-card flex flex-col gap-3 p-4" data-testid="source-card">
      <div className="flex items-start gap-3">
        <span className="mt-0.5 rounded-md bg-primary-soft px-1.5 py-0.5 font-mono text-[11px] font-semibold text-primary">
          E{marker}
        </span>
        <div className="min-w-0 flex-1">
          <h4 className="t-sub leading-snug text-ink">{source.title || "Untitled source"}</h4>
          <p className="mt-1 flex flex-wrap items-center gap-x-2 gap-y-1 text-[12px] text-muted">
            <span className="inline-flex items-center gap-1">
              <Globe className="size-3" />
              {source.publisher || domainOf(source.url)}
            </span>
            <span>·</span>
            <span>
              {source.published_at ? `published ${formatDate(source.published_at)}` : "date unknown"}
            </span>
            <span>·</span>
            <span>retrieved {formatRelative(source.retrieved_at)}</span>
          </p>
        </div>
        <div className="flex shrink-0 items-center gap-1">
          {source.url && (
            <a
              href={source.url}
              target="_blank"
              rel="noreferrer noopener"
              className="grid size-8 place-items-center rounded-lg text-muted transition-colors hover:bg-surface-soft hover:text-ink"
              aria-label={`Open ${source.title ?? "source"}`}
            >
              <ArrowUpRight className="size-4" />
            </a>
          )}
          <button
            type="button"
            onClick={() => onDelete(source)}
            className="grid size-8 place-items-center rounded-lg text-muted transition-colors hover:bg-danger-soft hover:text-danger"
            aria-label={`Remove ${source.title ?? "source"}`}
          >
            <Trash2 className="size-4" />
          </button>
        </div>
      </div>

      {source.preview && (
        <p className="line-clamp-3 text-[13px] leading-relaxed text-ink/85">
          <Highlight text={source.preview} terms={terms} />
        </p>
      )}

      <div className="flex flex-wrap items-center gap-1.5">
        <Badge tone="info">{source.source_type ?? "web"}</Badge>
        <Badge tone="neutral">{source.chunk_count} passages</Badge>
        {source.licence_note && (
          <span className="text-[11px] text-muted/80" title={source.attribution ?? undefined}>
            {source.licence_note}
          </span>
        )}
        <button
          type="button"
          onClick={toggle}
          className="ml-auto inline-flex items-center gap-1 text-[12px] font-medium text-primary hover:underline"
          aria-expanded={open}
        >
          {open ? "Hide passages" : "Show passages"}
          <ChevronDown className={cn("size-3.5 transition-transform", open && "rotate-180")} />
        </button>
      </div>

      {open && (
        <div className="flex flex-col gap-2 border-t border-line pt-3">
          {loading && <Loader2 className="size-4 animate-spin text-muted" />}
          {detail?.passages.map((p) => (
            <p key={p.chunk_id} className="rounded-lg bg-surface-soft p-3 text-[12.5px] leading-relaxed text-ink/85">
              <span className="mr-1.5 font-mono text-[10.5px] text-muted">#{p.chunk_index + 1}</span>
              <Highlight text={p.content} terms={terms} />
            </p>
          ))}
        </div>
      )}
    </li>
  );
}

function PassageRow({ passage, index, terms }: { passage: Passage; index: number; terms: string[] }) {
  const when = passage.published_at ?? passage.retrieved_at;
  return (
    <li className="flex flex-col gap-1.5 rounded-lg border border-line bg-surface p-3" data-testid="passage">
      <div className="flex flex-wrap items-center gap-1.5 text-[12px]">
        <span className="font-mono text-[11px] font-semibold text-primary">[E{index}]</span>
        <Badge tone={passage.kb === "C" ? "primary" : passage.kb === "B" ? "accent" : "info"}>
          {KB_LABEL[passage.kb]}
        </Badge>
        {passage.url ? (
          <a
            href={passage.url}
            target="_blank"
            rel="noreferrer noopener"
            className="inline-flex min-w-0 items-center gap-1 truncate font-medium text-ink hover:text-primary"
          >
            {passage.title || domainOf(passage.url)} <ArrowUpRight className="size-3 shrink-0" />
          </a>
        ) : (
          <span className="font-medium text-ink">{passage.title}</span>
        )}
        <span className="text-muted">{when ? formatDate(when) : "n.d."}</span>
      </div>
      <p className="line-clamp-4 text-[12.5px] leading-relaxed text-ink/85">
        <Highlight text={passage.content} terms={terms} />
      </p>
    </li>
  );
}

export default function ResearchPage() {
  const params = useParams<{ id: string }>();
  const id = params.id;
  const fileInput = useRef<HTMLInputElement>(null);

  const [sources, setSources] = useState<Source[] | null>(null);
  const [lastRun, setLastRun] = useState<RunWithOutput | null>(null);
  const [crawl, setCrawl] = useState<ScrapeJob | null>(null);
  const [stats, setStats] = useState<KnowledgeStats | null>(null);
  const [title, setTitle] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [filter, setFilter] = useState<Filter>("all");
  const [running, setRunning] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [showAdd, setShowAdd] = useState(false);
  const [extraUrl, setExtraUrl] = useState("");
  const [extraQuery, setExtraQuery] = useState("");

  const [query, setQuery] = useState("");
  const [mode, setMode] = useState<"hybrid" | "vector" | "keyword">("hybrid");
  const [searching, setSearching] = useState(false);
  const [result, setResult] = useState<SearchResult | null>(null);

  const load = useCallback(async () => {
    setError(null);
    try {
      const [project, list, runs, jobs, kstats] = await Promise.all([
        api.project(id),
        api.sources(id),
        api.projectRuns(id, "research"),
        api.crawl(id),
        api.knowledgeStats(),
      ]);
      setTitle(project.title);
      setSources(list);
      setLastRun(runs[0] ?? null);
      setCrawl(jobs[0] ?? null);
      setStats(kstats);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not load research.");
    }
  }, [id]);

  useEffect(() => {
    void load();
  }, [load]);

  const inFlight = lastRun?.status === "running" || lastRun?.status === "queued";

  // a run started elsewhere (another tab, Celery) is polled until it finishes
  useEffect(() => {
    if (!inFlight || running) return;
    const timer = window.setInterval(() => void load(), 5000);
    return () => window.clearInterval(timer);
  }, [inFlight, running, load]);

  const busy = running || inFlight;
  const summary = (lastRun?.output ?? null) as ResearchSummary | null;
  const visible = useMemo(
    () => (sources ?? []).filter((s) => matchesFilter(s, filter)),
    [sources, filter],
  );
  const terms = useMemo(() => termsFrom(result?.query || title), [result, title]);
  const passages = (sources ?? []).reduce((n, s) => n + s.chunk_count, 0);

  async function runResearch() {
    setRunning(true);
    setError(null);
    setNotice(null);
    try {
      const payload: { queries?: string[]; urls?: string[] } = {};
      if (extraQuery.trim()) payload.queries = [extraQuery.trim()];
      if (extraUrl.trim()) payload.urls = [extraUrl.trim()];
      const run = await api.research(id, payload);
      if (run.status === "queued") {
        setNotice("Research is running in the background. Refresh in a minute to see new sources.");
      } else {
        setNotice("Research finished.");
      }
      setExtraQuery("");
      setExtraUrl("");
      setShowAdd(false);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Research failed.");
    } finally {
      setRunning(false);
    }
  }

  async function onUpload(event: React.ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    event.target.value = "";
    if (!file) return;
    setUploading(true);
    setError(null);
    setNotice(null);
    try {
      const res = await api.uploadDocument(id, file);
      setNotice(
        res.status === "duplicate"
          ? `"${file.name}" is already in this project.`
          : `Added "${res.source.title}" (${res.source.chunk_count} passages).`,
      );
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Upload failed.");
    } finally {
      setUploading(false);
    }
  }

  async function onDelete(source: Source) {
    if (!window.confirm(`Remove "${source.title}" from this project's knowledge?`)) return;
    try {
      await api.deleteSource(id, source.id);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not remove the source.");
    }
  }

  async function onSearch(event: React.FormEvent) {
    event.preventDefault();
    if (query.trim().length < 2) return;
    setSearching(true);
    setError(null);
    try {
      setResult(await api.search(id, { query: query.trim(), mode, k: 8 }));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Search failed.");
    } finally {
      setSearching(false);
    }
  }

  if (!sources) {
    return error ? <ErrorNotice message={error} onRetry={load} /> : <PageSkeleton cards={3} />;
  }

  const blocked = crawl?.pages.filter((p) => !p.robots_allowed) ?? [];

  return (
    <div className="flex flex-col gap-5">
      {error && <ErrorNotice message={error} onRetry={load} />}
      {busy && (
        <p role="status" className="flex items-center gap-2 rounded-lg border border-primary/20 bg-primary-soft/50 px-4 py-2.5 text-[13px] text-primary">
          <Loader2 className="size-4 animate-spin" />
          Planning queries, searching with Tavily and reading the pages that allow it. This usually takes 2 to 3 minutes.
        </p>
      )}
      {notice && (
        <p role="status" className="rounded-lg border border-success/25 bg-success-soft/50 px-4 py-2.5 text-[13px] text-success">
          {notice}
        </p>
      )}

      <div className="flex flex-col justify-between gap-3 sm:flex-row sm:items-end">
        <div>
          <p className="t-label text-primary">Research</p>
          <h2 className="t-section mt-0.5 text-ink">Evidence for this idea</h2>
          <p className="t-body mt-0.5 max-w-2xl text-muted">
            Sources found on the web with Tavily, fetched by our own scraper (robots.txt respected),
            plus documents you upload. Every passage keeps its link and date.
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <input
            ref={fileInput}
            type="file"
            accept=".pdf,.docx,.txt,.md"
            className="hidden"
            onChange={onUpload}
            data-testid="upload-input"
          />
          <Button variant="secondary" onClick={() => fileInput.current?.click()} disabled={uploading}>
            {uploading ? <Loader2 className="size-4 animate-spin" /> : <FileUp className="size-4" />}
            Upload document
          </Button>
          <Button variant="secondary" onClick={() => setShowAdd((v) => !v)}>
            <Link2 className="size-4" /> Add source
          </Button>
          <Button onClick={runResearch} disabled={busy}>
            {busy ? <Loader2 className="size-4 animate-spin" /> : <Sparkles className="size-4" />}
            {busy ? "Researching…" : sources.length ? "Run research again" : "Run research"}
          </Button>
        </div>
      </div>

      {showAdd && (
        <Card className="flex flex-col gap-3 p-4">
          <p className="text-[13px] text-muted">
            Add a page you trust and/or an extra search query; both are included in the next research run.
          </p>
          <div className="grid gap-2 sm:grid-cols-2">
            <Input
              placeholder="https://example.com/market-report"
              value={extraUrl}
              onChange={(e) => setExtraUrl(e.target.value)}
              aria-label="Source URL"
            />
            <Input
              placeholder="Extra search query, e.g. peer tutoring apps Pakistan"
              value={extraQuery}
              onChange={(e) => setExtraQuery(e.target.value)}
              aria-label="Extra query"
            />
          </div>
          <div>
            <Button size="sm" onClick={runResearch} disabled={busy || (!extraUrl.trim() && !extraQuery.trim())}>
              Research with these
            </Button>
          </div>
        </Card>
      )}

      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <Stat label="Project sources" value={sources.length} hint={`${passages} passages`} icon={<BookOpen className="size-4" />} />
        <Stat
          label="Last research"
          value={lastRun ? (lastRun.status === "succeeded" ? "Done" : lastRun.status) : "—"}
          hint={
            lastRun?.finished_at
              ? `${formatRelative(lastRun.finished_at)}${summary?.seconds ? ` · ${Math.round(summary.seconds)}s` : ""}`
              : "not run yet"
          }
          icon={<Sparkles className="size-4" />}
        />
        <Stat
          label="Robots.txt respected"
          value={crawl ? `${crawl.pages_skipped_robots ?? 0} skipped` : "—"}
          hint={crawl ? `${crawl.pages_fetched ?? 0} fetched · ${crawl.pages_rejected ?? 0} rejected` : "no crawl yet"}
          icon={<ShieldCheck className="size-4" />}
        />
        <Stat
          label="Shared knowledge"
          value={stats ? `${(stats.kb.A ?? 0) + (stats.kb.B ?? 0)}` : "—"}
          hint={stats ? `KB-A ${stats.kb.A} · KB-B ${stats.kb.B} sources` : undefined}
          icon={<Library className="size-4" />}
        />
      </div>

      {lastRun?.status === "failed" && (
        <ErrorNotice message={`Last research run failed: ${lastRun.error_message ?? "unknown error"}`} />
      )}

      {summary && summary.unanswered_questions?.length > 0 && (
        <Card className="flex gap-3 border-warning/30 bg-warning-soft/40 p-4">
          <AlertTriangle className="mt-0.5 size-4 shrink-0 text-warning" />
          <div>
            <p className="text-[13px] font-medium text-ink">Thin evidence for some questions</p>
            <ul className="mt-1 list-disc pl-4 text-[12.5px] text-muted">
              {summary.unanswered_questions.map((q) => (
                <li key={q}>{q}</li>
              ))}
            </ul>
          </div>
        </Card>
      )}

      <div className="grid gap-5 lg:grid-cols-[200px_minmax(0,1fr)]">
        <nav className="flex gap-1 overflow-x-auto lg:flex-col" aria-label="Filter sources">
          {FILTERS.map((f) => {
            const count = sources.filter((s) => matchesFilter(s, f.key)).length;
            return (
              <button
                key={f.key}
                type="button"
                onClick={() => setFilter(f.key)}
                aria-pressed={filter === f.key}
                className={cn(
                  "flex items-center justify-between gap-3 whitespace-nowrap rounded-lg px-3 py-2 text-left text-[13px] transition-colors",
                  filter === f.key ? "bg-primary-soft font-medium text-primary" : "text-muted hover:bg-surface-soft hover:text-ink",
                )}
              >
                {f.label}
                <span className="font-mono text-[11px]">{count}</span>
              </button>
            );
          })}
        </nav>

        <div className="flex min-w-0 flex-col gap-5">
          {visible.length === 0 ? (
            <EmptyState
              title={sources.length ? "Nothing in this filter" : "No research yet"}
              body={
                sources.length
                  ? "Pick another filter to see the other sources."
                  : "Run research to find competitors, market data and similar products, or upload your own documents."
              }
              action={
                !sources.length ? (
                  <Button onClick={runResearch} disabled={busy}>
                    {busy ? <Loader2 className="size-4 animate-spin" /> : <Sparkles className="size-4" />}
                    Run research
                  </Button>
                ) : undefined
              }
            />
          ) : (
            <ul className="flex flex-col gap-3">
              {visible.map((source) => (
                <SourceCard
                  key={source.id}
                  source={source}
                  marker={sources.indexOf(source) + 1}
                  terms={terms}
                  projectId={id}
                  onDelete={onDelete}
                />
              ))}
            </ul>
          )}

          <Card className="flex flex-col gap-3 p-4">
            <div>
              <h3 className="t-sub text-ink">Ask the knowledge base</h3>
              <p className="text-[12.5px] text-muted">
                Hybrid search over shared KB-A/KB-B and this project only: semantic + keyword, fused and reranked.
              </p>
            </div>
            <form onSubmit={onSearch} className="flex flex-col gap-2 sm:flex-row">
              <Input
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="e.g. how do tutoring marketplaces charge commission?"
                aria-label="Search query"
                className="flex-1"
              />
              <Select
                value={mode}
                onChange={(e) => setMode(e.target.value as typeof mode)}
                aria-label="Retrieval mode"
                className="h-11 sm:w-40"
              >
                <option value="hybrid">Hybrid</option>
                <option value="vector">Vector only</option>
                <option value="keyword">Keyword only</option>
              </Select>
              <Button type="submit" className="h-11" disabled={searching || query.trim().length < 2}>
                {searching ? <Loader2 className="size-4 animate-spin" /> : <Search className="size-4" />}
                Search
              </Button>
            </form>
            {result && (
              result.passages.length === 0 ? (
                <p className="text-[12.5px] text-muted">No passages matched. Try other words or run research first.</p>
              ) : (
                <ol className="flex flex-col gap-2">
                  {result.passages.map((p, i) => (
                    <PassageRow key={p.chunk_id} passage={p} index={i + 1} terms={terms} />
                  ))}
                </ol>
              )
            )}
          </Card>

          {summary?.queries?.length ? (
            <details className="if-card p-4 text-[12.5px]">
              <summary className="cursor-pointer font-medium text-ink">
                Queries used in the last run ({summary.queries.length})
              </summary>
              <ul className="mt-2 flex flex-col gap-1 text-muted">
                {summary.queries.map((q) => (
                  <li key={q.query}>
                    <span className="text-ink">{q.query}</span> · {q.intent} · {q.hits} results ({q.origin})
                  </li>
                ))}
              </ul>
            </details>
          ) : null}

          {crawl && crawl.pages.length > 0 && (
            <details className="if-card p-4 text-[12.5px]">
              <summary className="cursor-pointer font-medium text-ink">
                Crawl log: {crawl.pages.length} URLs, {blocked.length} blocked by robots.txt or terms
              </summary>
              <div className="mt-2 overflow-x-auto">
                <table className="w-full min-w-[560px] text-left">
                  <thead className="text-muted">
                    <tr>
                      <th className="py-1 pr-3 font-medium">URL</th>
                      <th className="py-1 pr-3 font-medium">Robots</th>
                      <th className="py-1 pr-3 font-medium">HTTP</th>
                      <th className="py-1 font-medium">Result</th>
                    </tr>
                  </thead>
                  <tbody>
                    {crawl.pages.map((p) => (
                      <tr key={p.id} className="border-t border-line">
                        <td className="max-w-[320px] truncate py-1 pr-3" title={p.url}>{p.domain}</td>
                        <td className="py-1 pr-3">{p.robots_allowed ? "allowed" : "blocked"}</td>
                        <td className="py-1 pr-3 font-mono">{p.http_status ?? "—"}</td>
                        <td className="py-1 text-muted">{p.source_id && !p.skip_reason ? "stored" : p.skip_reason ?? p.error_message ?? "—"}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </details>
          )}

          <Card className="flex items-start gap-3 border-dashed p-4">
            <span className="grid size-9 shrink-0 place-items-center rounded-lg bg-surface-soft text-muted">
              <BookOpen className="size-4" />
            </span>
            <div>
              <p className="text-[13px] font-medium text-ink">Competitor analysis table</p>
              <p className="text-[12.5px] text-muted">
                Competitors are extracted from these sources on the Evaluation tab, each with its link.
              </p>
            </div>
          </Card>
        </div>
      </div>
    </div>
  );
}
