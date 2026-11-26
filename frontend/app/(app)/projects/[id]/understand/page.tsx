"use client";

import {
  AlertTriangle,
  Check,
  CheckCheck,
  Loader2,
  Sparkles,
  UserPen,
  Wand2,
} from "lucide-react";
import { useParams, useRouter } from "next/navigation";
import { useCallback, useEffect, useMemo, useState } from "react";

import { ErrorNotice } from "@/components/states/ErrorNotice";
import { ClarifyCard } from "@/components/understand/ClarifyCard";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { PageSkeleton } from "@/components/ui/skeleton";
import { api } from "@/lib/api";
import { PRIORITY_LABEL, readStructured, REQUIREMENT_GROUPS } from "@/lib/idea";
import type { ProjectDetail, Requirement } from "@/lib/types";
import { cn } from "@/lib/utils";

export default function UnderstandPage() {
  const params = useParams<{ id: string }>();
  const id = params.id;
  const router = useRouter();

  const [project, setProject] = useState<ProjectDetail | null>(null);
  const [requirements, setRequirements] = useState<Requirement[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [savingId, setSavingId] = useState<string | null>(null);
  const [bulkBusy, setBulkBusy] = useState(false);
  const [rerunning, setRerunning] = useState(false);
  const [regenerating, setRegenerating] = useState(false);

  const load = useCallback(async () => {
    setError(null);
    try {
      const data = await api.project(id);
      setProject(data);
      setRequirements(data.requirements);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not load this project.");
    }
  }, [id]);

  useEffect(() => {
    void load();
  }, [load]);

  const structured = readStructured(project?.version?.structured_idea);
  const confirmed = requirements.filter((item) => item.confirmed).length;

  const grouped = useMemo(
    () =>
      REQUIREMENT_GROUPS.map((group) => ({
        ...group,
        items: requirements.filter((item) => item.req_type === group.type),
      })),
    [requirements],
  );

  async function toggle(requirement: Requirement) {
    const next = !requirement.confirmed;
    setSavingId(requirement.id);
    setRequirements((list) =>
      list.map((item) => (item.id === requirement.id ? { ...item, confirmed: next } : item)),
    );
    try {
      const updated = await api.updateRequirements(id, [
        { id: requirement.id, confirmed: next },
      ]);
      setRequirements(updated);
    } catch (err) {
      setRequirements((list) =>
        list.map((item) =>
          item.id === requirement.id ? { ...item, confirmed: requirement.confirmed } : item,
        ),
      );
      setError(err instanceof Error ? err.message : "Could not save that change.");
    } finally {
      setSavingId(null);
    }
  }

  async function confirmAll() {
    const pending = requirements.filter((item) => !item.confirmed);
    if (pending.length === 0) return;
    setBulkBusy(true);
    try {
      const updated = await api.updateRequirements(
        id,
        pending.map((item) => ({ id: item.id, confirmed: true })),
      );
      setRequirements(updated);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not confirm requirements.");
    } finally {
      setBulkBusy(false);
    }
  }

  async function rerun() {
    setRerunning(true);
    setError(null);
    try {
      const run = await api.understand(id);
      if (run.status === "queued") {
        router.push(`/projects/${id}/run?run=${run.run_id}`);
        return;
      }
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not start extraction.");
    } finally {
      setRerunning(false);
    }
  }

  async function regenerate() {
    setRegenerating(true);
    setError(null);
    try {
      const run = await api.regenerateRequirements(id);
      if (run.status === "queued") {
        router.push(`/projects/${id}/run?run=${run.run_id}`);
        return;
      }
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not regenerate requirements.");
    } finally {
      setRegenerating(false);
    }
  }

  const busy = rerunning || regenerating;

  if (!project) {
    return error ? <ErrorNotice message={error} onRetry={load} /> : <PageSkeleton cards={2} />;
  }

  return (
    <div className="flex flex-col gap-4">
      {error && <ErrorNotice message={error} onRetry={load} />}

      <div className="flex flex-col justify-between gap-3 sm:flex-row sm:items-end">
        <div>
          <p className="t-label text-primary">Extracted requirements</p>
          <h2 className="t-section mt-0.5 text-ink">Here is how IdeaForm understood your idea</h2>
          <p className="t-body mt-0.5 text-muted">
            Everything below comes from your own words. Confirm what is true before the analysis builds on it.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <span className="rounded-full bg-surface px-3 py-1.5 font-mono text-[12px] tabular text-muted shadow-sm">
            {confirmed}/{requirements.length} confirmed
          </span>
          <Button
            variant="secondary"
            size="md"
            onClick={confirmAll}
            disabled={bulkBusy || confirmed === requirements.length}
          >
            {bulkBusy ? <Loader2 className="size-3.5 animate-spin" /> : <CheckCheck className="size-3.5" />}
            Confirm all
          </Button>
        </div>
      </div>

      <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_320px]">
        <section className="flex min-w-0 flex-col gap-4">
          {requirements.length === 0 ? (
            <Card className="flex flex-col items-start gap-3">
              <span className="grid size-10 place-items-center rounded-lg bg-warning-soft text-warning">
                <AlertTriangle className="size-5" />
              </span>
              <div>
                <h4 className="t-sub text-ink">No requirements yet</h4>
                <p className="mt-1 max-w-md text-[12.5px] leading-relaxed text-muted">
                  Extraction has not run for this version, or it returned no requirements. Run it
                  again to fill this list.
                </p>
              </div>
              <Button size="md" onClick={rerun} disabled={rerunning}>
                {rerunning ? <Loader2 className="size-4 animate-spin" /> : <Sparkles className="size-4" />}
                {rerunning ? "Reading your idea…" : "Run extraction"}
              </Button>
            </Card>
          ) : (
            grouped.map((group) =>
              group.items.length === 0 ? null : (
                <div key={group.type} className="flex flex-col gap-2">
                  <div className="flex items-baseline gap-2 px-1">
                    <h4 className="t-label text-muted">{group.label}</h4>
                    <span className="font-mono text-[11px] text-muted/70">{group.items.length}</span>
                    <span className="text-[11px] text-muted/70">· {group.blurb}</span>
                  </div>
                  <ul className="flex flex-col gap-2">
                    {group.items.map((requirement) => (
                      <li
                        key={requirement.id}
                        className={cn(
                          "flex items-start gap-3 rounded-xl border p-3.5 transition-colors",
                          requirement.confirmed
                            ? "border-success/25 bg-success-soft/40"
                            : "border-line bg-surface hover:border-primary/25",
                        )}
                      >
                        <button
                          type="button"
                          onClick={() => toggle(requirement)}
                          role="checkbox"
                          aria-checked={requirement.confirmed}
                          aria-label={requirement.description}
                          className={cn(
                            "mt-0.5 grid size-5 shrink-0 place-items-center rounded-md border transition-colors",
                            requirement.confirmed
                              ? "border-transparent bg-success text-white"
                              : "border-line bg-surface text-transparent hover:border-primary/40",
                          )}
                        >
                          {savingId === requirement.id ? (
                            <Loader2 className="size-3 animate-spin text-muted" />
                          ) : (
                            <Check className="size-3.5" />
                          )}
                        </button>
                        <div className="flex min-w-0 flex-1 flex-col gap-1.5">
                          <p className="text-[13.5px] leading-snug text-ink">
                            {requirement.description}
                          </p>
                          <div className="flex flex-wrap items-center gap-1.5">
                            {requirement.priority && (
                              <Badge tone={requirement.priority === "must" ? "primary" : "neutral"}>
                                {PRIORITY_LABEL[requirement.priority]}
                              </Badge>
                            )}
                            {requirement.source === "ai_suggestion" ? (
                              <Badge tone="info">
                                <Wand2 className="size-3" /> AI suggestion
                              </Badge>
                            ) : requirement.source === "user" ? (
                              <Badge tone="success">
                                <UserPen className="size-3" /> Yours
                              </Badge>
                            ) : (
                              <Badge tone="neutral">Extracted</Badge>
                            )}
                          </div>
                        </div>
                      </li>
                    ))}
                  </ul>
                </div>
              ),
            )
          )}
        </section>

        <aside className="flex flex-col gap-4">
          {structured?.clarity?.vague && project?.version && (
            <ClarifyCard
              projectId={id}
              ideaText={project.version.idea_text}
              versionNo={project.version.version_no}
              clarity={structured.clarity}
            />
          )}
          {structured && (
            <Card className="flex flex-col gap-3">
              <h3 className="t-sub text-ink">What we understood</h3>
              {structured.problem && (
                <p className="text-[12.5px] leading-relaxed text-muted">{structured.problem}</p>
              )}

              {(structured.target_users ?? []).length > 0 && (
                <div className="flex flex-col gap-1.5">
                  <p className="t-label text-muted">For</p>
                  <div className="flex flex-wrap gap-1">
                    {structured.target_users?.map((user) => (
                      <span key={user} className="rounded-md bg-surface-soft px-2 py-0.5 text-[11.5px] text-ink">
                        {user}
                      </span>
                    ))}
                  </div>
                </div>
              )}

              {(structured.key_features ?? []).length > 0 && (
                <div className="flex flex-col gap-1.5">
                  <p className="t-label text-muted">Features</p>
                  <ul className="flex flex-col gap-1">
                    {structured.key_features?.map((feature) => (
                      <li key={feature} className="flex items-start gap-1.5 text-[12px] leading-snug text-muted">
                        <Check className="mt-1 size-3 shrink-0 text-success" />
                        {feature}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </Card>
          )}

          <Card className="flex flex-col gap-2.5">
            <h3 className="flex items-center gap-1.5 t-sub text-ink">
              <AlertTriangle className="size-4 text-warning" /> Still missing
            </h3>
            {(structured?.missing_information ?? []).length > 0 ? (
              <ul className="flex flex-col gap-1.5">
                {structured?.missing_information?.map((item) => (
                  <li
                    key={item}
                    className="rounded-lg border border-warning/20 bg-warning-soft/60 px-2.5 py-2 text-[11.5px] leading-snug text-ink/85"
                  >
                    {item}
                  </li>
                ))}
              </ul>
            ) : (
              <p className="text-[12px] text-muted">
                Nothing was flagged as missing for this version.
              </p>
            )}
            <p className="text-[11px] leading-snug text-muted/80">
              IdeaForm lists what your text does not answer instead of guessing.
            </p>
          </Card>
        </aside>
      </div>

      <div className="sticky bottom-20 z-20 flex flex-wrap items-center justify-between gap-3 rounded-xl border border-line bg-surface px-4 py-3 shadow-e1 lg:bottom-4">
        <div className="flex min-w-0 items-center gap-2.5">
          <span className="grid size-8 place-items-center rounded-lg bg-primary-soft text-primary">
            <CheckCheck className="size-4" />
          </span>
          <div className="min-w-0">
            <p className="text-[12.5px] font-medium text-ink">
              {confirmed} of {requirements.length} requirements confirmed
            </p>
            <p className="text-[11px] text-muted">
              Regenerating keeps confirmed and edited requirements; re-running replaces everything.
            </p>
          </div>
        </div>
        <div className="flex flex-wrap items-center gap-2">
        <Button
          variant="secondary"
          onClick={regenerate}
          disabled={busy || requirements.length === 0}
          size="md"
        >
          {regenerating ? (
            <Loader2 className="size-4 animate-spin" />
          ) : (
            <Wand2 className="size-4" />
          )}
          {regenerating ? "Regenerating…" : "Regenerate requirements"}
        </Button>
        <Button onClick={rerun} disabled={busy} size="md">
          {rerunning ? (
            <>
              <Loader2 className="size-4 animate-spin" /> Reading your idea…
            </>
          ) : (
            <>
              <Sparkles className="size-4" /> Re-run extraction
            </>
          )}
        </Button>
        </div>
      </div>
    </div>
  );
}
