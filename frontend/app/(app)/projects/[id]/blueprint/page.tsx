"use client";

import {
  AlertTriangle,
  ArrowRight,
  Braces,
  Check,
  Copy,
  Database,
  FileText,
  LayoutPanelTop,
  Loader2,
  Network,
  PencilLine,
  RotateCw,
  Route,
  Sparkles,
  X,
} from "lucide-react";
import Link from "next/link";
import { useParams, useRouter, useSearchParams } from "next/navigation";
import { Suspense, useCallback, useEffect, useMemo, useRef, useState } from "react";

import { MarkdownDoc } from "@/components/blueprint/MarkdownDoc";
import { Disclaimer } from "@/components/evaluation/parts";
import { EmptyState } from "@/components/states/EmptyState";
import { ErrorNotice } from "@/components/states/ErrorNotice";
import { Button, buttonStyles } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Select, Textarea } from "@/components/ui/field";
import { PageSkeleton } from "@/components/ui/skeleton";
import { api } from "@/lib/api";
import type { Artifact, ArtifactType, Blueprint } from "@/lib/types";
import { cn } from "@/lib/utils";

/** Reading order in the navigation (generation order is ui_ux → … → roadmap). */
const SECTIONS: { type: ArtifactType; label: string; icon: typeof FileText; blurb: string }[] = [
  { type: "prd", label: "PRD", icon: FileText, blurb: "Goals, users, scope, features, metrics" },
  { type: "ui_ux", label: "UI/UX concepts", icon: LayoutPanelTop, blurb: "Flows, screens, principles" },
  { type: "architecture", label: "Architecture", icon: Network, blurb: "Stack, components, security" },
  { type: "database_schema", label: "Database schema", icon: Database, blurb: "Tables and ER diagram" },
  { type: "api_spec", label: "API specification", icon: Braces, blurb: "Endpoints and conventions" },
  { type: "roadmap", label: "Roadmap", icon: Route, blurb: "Phases, tasks, estimates" },
];
const GENERATION_ORDER: ArtifactType[] = ["ui_ux", "architecture", "database_schema", "api_spec", "prd", "roadmap"];
const LABEL = Object.fromEntries(SECTIONS.map((s) => [s.type, s.label])) as Record<ArtifactType, string>;

function BlueprintView() {
  const params = useParams<{ id: string }>();
  const search = useSearchParams();
  const router = useRouter();
  const id = params.id;

  const [blueprint, setBlueprint] = useState<Blueprint | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [generating, setGenerating] = useState(false);
  const [regenerating, setRegenerating] = useState<ArtifactType | null>(null);
  const [showRegen, setShowRegen] = useState(false);
  const [instructions, setInstructions] = useState("");
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState("");
  const [saving, setSaving] = useState(false);
  const [history, setHistory] = useState<Artifact[]>([]);
  const [viewingId, setViewingId] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);
  const poll = useRef<ReturnType<typeof setInterval> | null>(null);

  const load = useCallback(async () => {
    try {
      setBlueprint(await api.blueprint(id));
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not load the blueprint.");
    }
  }, [id]);

  useEffect(() => {
    void load();
    return () => {
      if (poll.current) clearInterval(poll.current);
    };
  }, [load]);

  const byType = useMemo(
    () => Object.fromEntries((blueprint?.artifacts ?? []).map((a) => [a.artifact_type, a])) as Partial<Record<ArtifactType, Artifact>>,
    [blueprint],
  );
  const selected = (search.get("section") as ArtifactType | null) ?? SECTIONS.find((s) => byType[s.type])?.type ?? "prd";
  const latest = byType[selected];
  const viewing = history.find((h) => h.id === viewingId) ?? latest;
  const isLatest = !latest || viewing?.id === latest.id;

  // version history of the open section
  useEffect(() => {
    setViewingId(null);
    setEditing(false);
    setShowRegen(false);
    if (!latest) {
      setHistory([]);
      return;
    }
    api.artifactHistory(id, selected).then(setHistory).catch(() => setHistory([]));
  }, [id, selected, latest]);

  function select(type: ArtifactType) {
    router.replace(`/projects/${id}/blueprint?section=${type}`, { scroll: false });
  }

  function startPolling() {
    if (poll.current) clearInterval(poll.current);
    poll.current = setInterval(() => void load(), 3000);
  }
  function stopPolling() {
    if (poll.current) clearInterval(poll.current);
    poll.current = null;
  }

  async function generateAll() {
    setGenerating(true);
    setError(null);
    startPolling();
    try {
      await api.generateBlueprint(id);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Blueprint generation failed.");
    } finally {
      stopPolling();
      setGenerating(false);
      await load();
    }
  }

  async function regenerate(type: ArtifactType) {
    setRegenerating(type);
    setError(null);
    try {
      await api.regenerateArtifact(id, type, instructions.trim() || undefined);
      setInstructions("");
      setShowRegen(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Regeneration failed.");
    } finally {
      setRegenerating(null);
      await load();
    }
  }

  async function save() {
    if (!viewing) return;
    setSaving(true);
    setError(null);
    try {
      await api.editArtifact(viewing.id, draft);
      setEditing(false);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not save your edit.");
    } finally {
      setSaving(false);
    }
  }

  async function copy() {
    if (!viewing) return;
    await navigator.clipboard.writeText(viewing.content);
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  }

  if (!blueprint) return error ? <ErrorNotice message={error} onRetry={load} /> : <PageSkeleton cards={3} />;

  const done = blueprint.artifacts.length;
  const busy = generating || regenerating !== null;

  return (
    <div className="flex flex-col gap-5">
      <div className="flex flex-col justify-between gap-3 sm:flex-row sm:items-center">
        <div className="flex items-baseline gap-2.5">
          <h2 className="t-title text-ink">Blueprint</h2>
          <span className="font-mono text-[12px] text-muted">
            v{blueprint.version_no} · {done}/6 sections
          </span>
        </div>
        {done > 0 && (
          <Button variant="secondary" size="sm" onClick={generateAll} disabled={busy}>
            {generating ? <Loader2 className="size-3.5 animate-spin" /> : <RotateCw className="size-3.5" />}
            {generating ? "Generating…" : "Regenerate all"}
          </Button>
        )}
      </div>

      <Disclaimer text="Generated blueprints are starting points for a team to review, not finished designs. Durations and efforts are estimates." />
      {!blueprint.has_evaluation && (
        <p className="flex flex-wrap items-center gap-2 rounded-lg border border-line bg-surface-soft px-3 py-2 text-[12.5px] text-muted">
          This version has not been evaluated, so the blueprint will not use scores or risks.
          <Link href={`/projects/${id}/evaluation`} className="inline-flex items-center gap-1 font-medium text-primary">
            Evaluate first <ArrowRight className="size-3.5" />
          </Link>
        </p>
      )}
      {error && <ErrorNotice message={error} onRetry={load} />}

      {generating && (
        <Card className="flex flex-col gap-3">
          <div className="flex items-center gap-2">
            <Loader2 className="size-4 animate-spin text-primary" />
            <p className="t-sub text-ink">Generating the blueprint</p>
          </div>
          <p className="text-[12.5px] text-muted">
            Six sections, each built on the ones before it. This takes two to five minutes on the free Groq tier.
          </p>
          <ol className="grid gap-2 sm:grid-cols-3">
            {GENERATION_ORDER.map((type, i) => {
              const ready = Boolean(byType[type]) && done > 0;
              const current = !ready && GENERATION_ORDER.slice(0, i).every((t) => byType[t]);
              return (
                <li key={type} className="flex items-center gap-2 rounded-lg bg-surface-soft px-3 py-2 text-[12.5px]">
                  {ready ? (
                    <Check className="size-3.5 text-success" />
                  ) : current ? (
                    <Loader2 className="size-3.5 animate-spin text-primary" />
                  ) : (
                    <span className="size-3.5 rounded-full border border-line" />
                  )}
                  <span className={ready ? "text-ink" : "text-muted"}>{LABEL[type]}</span>
                </li>
              );
            })}
          </ol>
        </Card>
      )}

      {done === 0 && !generating ? (
        <EmptyState
          title="No blueprint yet"
          body="Turn this version into a PRD, UI/UX concepts, an architecture with diagrams, a database schema, an API specification and a roadmap. Any section can be regenerated or edited later."
          action={
            <Button onClick={generateAll} disabled={busy}>
              <Sparkles className="size-4" /> Generate blueprint
            </Button>
          }
        />
      ) : done > 0 ? (
        <div className="grid gap-5 lg:grid-cols-[240px_1fr] lg:items-start">
          {/* ---------------- section list ---------------- */}
          <nav aria-label="Blueprint sections" className="no-scrollbar flex gap-2 overflow-x-auto lg:sticky lg:top-20 lg:flex-col lg:gap-1">
            {SECTIONS.map((section) => {
              const artifact = byType[section.type];
              const active = section.type === selected;
              return (
                <button
                  key={section.type}
                  type="button"
                  onClick={() => select(section.type)}
                  aria-current={active ? "page" : undefined}
                  className={cn(
                    "group flex min-w-[180px] items-start gap-2.5 rounded-lg border px-3 py-2.5 text-left transition-colors duration-150 lg:min-w-0",
                    active ? "border-primary/30 bg-primary-soft" : "border-transparent hover:bg-surface-soft",
                  )}
                >
                  <section.icon className={cn("mt-0.5 size-4 shrink-0", active ? "text-primary" : "text-muted")} />
                  <span className="flex min-w-0 flex-col gap-0.5">
                    <span className={cn("flex items-center gap-1.5 text-[13px] font-medium", active ? "text-primary" : "text-ink")}>
                      {section.label}
                      {artifact?.stale_inputs.length ? (
                        <AlertTriangle className="size-3 text-warning" aria-label="Built on older inputs" />
                      ) : null}
                    </span>
                    <span className="truncate text-[11.5px] text-muted">
                      {artifact
                        ? `v${artifact.artifact_version}${artifact.edited_by_user ? " · edited" : ""}`
                        : regenerating === section.type
                          ? "Generating…"
                          : "Not generated"}
                    </span>
                  </span>
                </button>
              );
            })}
          </nav>

          {/* ---------------- document ---------------- */}
          <Card className="flex min-w-0 flex-col gap-4 p-0">
            {!latest ? (
              <div className="flex flex-col items-start gap-3 p-6">
                <p className="t-sub text-ink">{LABEL[selected]} has not been generated.</p>
                <Button size="sm" onClick={() => regenerate(selected)} disabled={busy}>
                  {regenerating === selected ? <Loader2 className="size-3.5 animate-spin" /> : <Sparkles className="size-3.5" />}
                  Generate this section
                </Button>
              </div>
            ) : (
              <>
                <div className="flex flex-col gap-3 border-b border-line px-5 py-4">
                  <div className="flex flex-wrap items-center gap-2">
                    <h3 className="t-sub mr-auto text-ink">{LABEL[selected]}</h3>
                    {history.length > 1 && (
                      <Select
                        aria-label="Version of this section"
                        className="h-8 w-auto py-0 text-[12.5px]"
                        value={viewing?.id ?? ""}
                        onChange={(e) => {
                          setViewingId(e.target.value);
                          setEditing(false);
                        }}
                      >
                        {history.map((h) => (
                          <option key={h.id} value={h.id}>
                            v{h.artifact_version}
                            {h.edited_by_user ? " (edited)" : h.instructions ? " (instructions)" : ""}
                            {h.id === latest.id ? " · latest" : ""}
                          </option>
                        ))}
                      </Select>
                    )}
                    <Button size="sm" variant="ghost" onClick={copy}>
                      {copied ? <Check className="size-3.5" /> : <Copy className="size-3.5" />}
                      {copied ? "Copied" : "Copy"}
                    </Button>
                    <Button
                      size="sm"
                      variant="secondary"
                      disabled={!isLatest || busy || editing}
                      onClick={() => {
                        setDraft(viewing?.content ?? "");
                        setEditing(true);
                        setShowRegen(false);
                      }}
                    >
                      <PencilLine className="size-3.5" /> Edit
                    </Button>
                    <Button
                      size="sm"
                      variant="secondary"
                      disabled={busy || editing}
                      onClick={() => setShowRegen((v) => !v)}
                      aria-expanded={showRegen}
                    >
                      {regenerating === selected ? <Loader2 className="size-3.5 animate-spin" /> : <RotateCw className="size-3.5" />}
                      Regenerate
                    </Button>
                  </div>

                  <p className="flex flex-wrap items-center gap-x-3 gap-y-1 font-mono text-[11px] text-muted">
                    <span>v{viewing?.artifact_version}</span>
                    <span>{viewing?.edited_by_user ? "edited by you" : viewing?.data?.model ?? "generated"}</span>
                    <span>{viewing ? new Date(viewing.created_at).toLocaleString() : ""}</span>
                  </p>
                  {viewing?.instructions && (
                    <p className="rounded-lg bg-surface-soft px-3 py-2 text-[12.5px] text-ink/85">
                      <span className="font-medium">Your instructions: </span>
                      {viewing.instructions}
                    </p>
                  )}
                  {!isLatest && (
                    <p className="text-[12.5px] text-muted">
                      You are viewing an earlier version. The latest is v{latest.artifact_version}.
                    </p>
                  )}
                  {isLatest && latest.stale_inputs.length > 0 && (
                    <div className="flex flex-wrap items-center gap-2 rounded-lg border border-warning/25 bg-warning-soft px-3 py-2 text-[12.5px] text-ink">
                      <AlertTriangle className="size-4 text-warning" />
                      Built on an older {latest.stale_inputs.map((t) => LABEL[t]).join(", ")}. Regenerate to bring it up to date.
                    </div>
                  )}

                  {showRegen && (
                    <div className="flex flex-col gap-2 rounded-lg border border-line bg-surface-soft p-3">
                      <label htmlFor="regen-instructions" className="text-[12.5px] font-medium text-ink">
                        Regenerate {LABEL[selected]} only
                      </label>
                      <Textarea
                        id="regen-instructions"
                        rows={3}
                        maxLength={2000}
                        value={instructions}
                        onChange={(e) => setInstructions(e.target.value)}
                        placeholder="Optional instructions, e.g. “Use Supabase for auth and storage” or “Plan for a team of two”."
                        className="text-[13px]"
                      />
                      <div className="flex items-center gap-2">
                        <Button size="sm" onClick={() => regenerate(selected)} disabled={busy}>
                          {regenerating === selected ? <Loader2 className="size-3.5 animate-spin" /> : <Sparkles className="size-3.5" />}
                          {regenerating === selected ? "Regenerating…" : "Regenerate section"}
                        </Button>
                        <Button size="sm" variant="ghost" onClick={() => setShowRegen(false)} disabled={busy}>
                          Cancel
                        </Button>
                        <span className="ml-auto text-[11.5px] text-muted">Other sections stay as they are.</span>
                      </div>
                    </div>
                  )}
                </div>

                {editing ? (
                  <div className="grid gap-4 px-5 pb-5 xl:grid-cols-2">
                    <div className="flex flex-col gap-2">
                      <label htmlFor="artifact-editor" className="t-label text-muted">
                        Markdown
                      </label>
                      <Textarea
                        id="artifact-editor"
                        value={draft}
                        onChange={(e) => setDraft(e.target.value)}
                        rows={26}
                        spellCheck={false}
                        className="font-mono text-[12.5px] leading-relaxed"
                      />
                      <div className="flex items-center gap-2">
                        <Button size="sm" onClick={save} disabled={saving || draft.trim() === (viewing?.content ?? "").trim()}>
                          {saving ? <Loader2 className="size-3.5 animate-spin" /> : <Check className="size-3.5" />}
                          Save as v{(history[0]?.artifact_version ?? latest.artifact_version) + 1}
                        </Button>
                        <Button size="sm" variant="ghost" onClick={() => setEditing(false)} disabled={saving}>
                          <X className="size-3.5" /> Cancel
                        </Button>
                      </div>
                    </div>
                    <div className="flex min-w-0 flex-col gap-2">
                      <span className="t-label text-muted">Preview</span>
                      <div className="max-h-[640px] overflow-y-auto rounded-lg border border-line p-4">
                        <MarkdownDoc content={draft} />
                      </div>
                    </div>
                  </div>
                ) : (
                  <div className="min-w-0 px-5 pb-6">
                    {viewing?.data?.notices?.map((notice) => (
                      <p key={notice} className="mb-3 rounded-lg bg-surface-soft px-3 py-2 text-[12px] text-muted">
                        {notice}
                      </p>
                    ))}
                    {viewing && <MarkdownDoc content={viewing.content} />}
                  </div>
                )}
              </>
            )}
          </Card>
        </div>
      ) : null}

      {done > 0 && (
        <p className="text-[12px] text-muted">
          Want the next idea version first?{" "}
          <Link href={`/projects/${id}/evaluation`} className={cn(buttonStyles("ghost", "sm"), "h-auto px-1 py-0 text-[12px] text-primary")}>
            Improve it on the Evaluation tab
          </Link>
          , then generate its blueprint.
        </p>
      )}
    </div>
  );
}

export default function BlueprintPage() {
  return (
    <Suspense fallback={<PageSkeleton cards={3} />}>
      <BlueprintView />
    </Suspense>
  );
}
