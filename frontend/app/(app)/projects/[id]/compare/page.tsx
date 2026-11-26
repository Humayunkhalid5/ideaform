"use client";

import { ArrowRight, GitCompare, Minus, Plus, RotateCcw } from "lucide-react";
import Link from "next/link";
import { useParams, useRouter, useSearchParams } from "next/navigation";
import { Suspense, useCallback, useEffect, useState } from "react";

import { ScoreBars } from "@/components/evaluation/charts";
import { ConfidenceBadge, DeltaChip, Disclaimer } from "@/components/evaluation/parts";
import { EmptyState } from "@/components/states/EmptyState";
import { ErrorNotice } from "@/components/states/ErrorNotice";
import { Button, buttonStyles } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Select } from "@/components/ui/field";
import { PageSkeleton } from "@/components/ui/skeleton";
import { api } from "@/lib/api";
import type { Comparison, VersionSummary } from "@/lib/types";
import { cn } from "@/lib/utils";

function ChangeList({ title, added, removed }: { title: string; added: string[]; removed: string[] }) {
  return (
    <Card className="flex flex-col gap-2">
      <h4 className="t-sub text-ink">{title}</h4>
      {added.length === 0 && removed.length === 0 ? (
        <p className="text-[12.5px] text-muted">No change.</p>
      ) : (
        <ul className="flex flex-col gap-1.5 text-[12.5px]">
          {added.map((item, i) => (
            <li key={`a${i}`} className="flex gap-2 rounded-lg bg-success-soft px-2.5 py-1.5 text-ink">
              <Plus className="mt-0.5 size-3.5 shrink-0 text-success" /> {item}
            </li>
          ))}
          {removed.map((item, i) => (
            <li key={`r${i}`} className="flex gap-2 rounded-lg bg-danger-soft px-2.5 py-1.5 text-ink line-through decoration-danger/40">
              <Minus className="mt-0.5 size-3.5 shrink-0 text-danger" /> {item}
            </li>
          ))}
        </ul>
      )}
    </Card>
  );
}

function CompareView() {
  const params = useParams<{ id: string }>();
  const search = useSearchParams();
  const router = useRouter();
  const id = params.id;

  const [versions, setVersions] = useState<VersionSummary[] | null>(null);
  const [result, setResult] = useState<Comparison | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [restoring, setRestoring] = useState(false);

  useEffect(() => {
    api
      .versions(id)
      .then(setVersions)
      .catch((err: Error) => setError(err.message));
  }, [id]);

  const current = versions?.find((v) => v.is_current);
  const fallbackB = current?.version_no ?? versions?.[0]?.version_no;
  const parentNo = versions?.find((v) => v.id === current?.parent_version_id)?.version_no;
  const fallbackA = parentNo ?? (fallbackB && fallbackB > 1 ? fallbackB - 1 : undefined);
  const a = Number(search.get("a")) || fallbackA;
  const b = Number(search.get("b")) || fallbackB;

  const load = useCallback(async () => {
    if (!a || !b) return;
    setLoading(true);
    setError(null);
    try {
      setResult(await api.compare(id, a, b));
    } catch (err) {
      setResult(null);
      setError(err instanceof Error ? err.message : "Could not compare these versions.");
    } finally {
      setLoading(false);
    }
  }, [id, a, b]);

  useEffect(() => {
    void load();
  }, [load]);

  function pick(which: "a" | "b", value: string) {
    const next = new URLSearchParams({ a: String(a ?? ""), b: String(b ?? "") });
    next.set(which, value);
    router.replace(`/projects/${id}/compare?${next.toString()}`);
  }

  async function makeCurrent(versionNo: number) {
    setRestoring(true);
    try {
      await api.restoreVersion(id, versionNo);
      const fresh = await api.versions(id);
      setVersions(fresh);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not restore that version.");
    } finally {
      setRestoring(false);
    }
  }

  if (!versions) return error ? <ErrorNotice message={error} /> : <PageSkeleton cards={3} />;

  if (versions.length < 2) {
    return (
      <EmptyState
        title="Only one version so far"
        body="Open the Evaluation tab, accept or edit improvement suggestions, and create the next version. Its re-evaluation is compared here."
        action={
          <Link href={`/projects/${id}/evaluation`} className={buttonStyles("primary", "md")}>
            Go to Evaluation <ArrowRight className="size-4" />
          </Link>
        }
      />
    );
  }

  return (
    <div className="flex flex-col gap-5">
      <div className="flex flex-col justify-between gap-3 sm:flex-row sm:items-center">
        <h2 className="flex items-center gap-2 t-title text-ink">
          <GitCompare className="size-5 text-primary" /> Version comparison
        </h2>
        <div className="flex items-center gap-2">
          <Select aria-label="Earlier version" className="h-9 w-auto py-1 text-[13px]" value={a ?? ""} onChange={(e) => pick("a", e.target.value)}>
            {versions.map((v) => (
              <option key={v.id} value={v.version_no}>
                v{v.version_no}
              </option>
            ))}
          </Select>
          <ArrowRight className="size-4 text-muted" />
          <Select aria-label="Later version" className="h-9 w-auto py-1 text-[13px]" value={b ?? ""} onChange={(e) => pick("b", e.target.value)}>
            {versions.map((v) => (
              <option key={v.id} value={v.version_no}>
                v{v.version_no}
                {v.is_current ? " (current)" : ""}
              </option>
            ))}
          </Select>
        </div>
      </div>

      <Disclaimer text="Score changes are evidence-based estimates for the edited idea, not predictions. Every change states its reason." />
      {error && <ErrorNotice message={error} onRetry={load} />}
      {loading && !result && <PageSkeleton cards={2} />}

      {result && (
        <>
          <div className="grid gap-4 lg:grid-cols-[1fr_1.3fr]">
            <Card className="flex flex-col gap-3">
              <div className="flex items-end gap-3">
                <div className="flex flex-col">
                  <span className="t-label text-muted">v{result.a}</span>
                  <span className="font-display text-[30px] font-semibold tabular text-muted">{result.overall_a ?? "—"}</span>
                </div>
                <ArrowRight className="mb-3 size-5 text-muted" />
                <div className="flex flex-col">
                  <span className="t-label text-primary">v{result.b}</span>
                  <span className="font-display text-[30px] font-semibold tabular text-ink">{result.overall_b ?? "—"}</span>
                </div>
                <DeltaChip delta={result.overall_delta} className="mb-3" />
              </div>
              <p className="text-[13.5px] leading-relaxed text-ink">{result.summary}</p>
              {result.change_summary && (
                <p className="rounded-lg bg-surface-soft px-3 py-2 text-[12.5px] text-ink/85">
                  <span className="font-medium">What changed in v{result.b}: </span>
                  {result.change_summary}
                </p>
              )}
              <div className="flex flex-wrap gap-2">
                <Link href={`/projects/${id}/evaluation?version=${result.b}`} className={buttonStyles("secondary", "sm")}>
                  Open v{result.b} evaluation
                </Link>
                {versions.find((v) => v.version_no === result.a && !v.is_current) && (
                  <Button size="sm" variant="ghost" onClick={() => makeCurrent(result.a)} disabled={restoring}>
                    <RotateCcw className="size-3.5" /> Make v{result.a} current
                  </Button>
                )}
                {versions.find((v) => v.version_no === result.b && !v.is_current) && (
                  <Button size="sm" variant="ghost" onClick={() => makeCurrent(result.b)} disabled={restoring}>
                    <RotateCcw className="size-3.5" /> Make v{result.b} current
                  </Button>
                )}
              </div>
            </Card>
            <Card className="p-3">
              <ScoreBars
                labelA={`v${result.a}`}
                labelB={`v${result.b}`}
                data={result.dimensions.map((d) => ({ dimension: d.dimension, label: d.label, a: d.score_a, b: d.score_b }))}
              />
            </Card>
          </div>

          <Card className="flex flex-col p-0">
            <div className="border-b border-line px-5 py-3">
              <h3 className="t-sub text-ink">Per-dimension changes</h3>
            </div>
            <ul>
              {result.dimensions.map((d) => (
                <li key={d.dimension} className="grid gap-2 border-b border-line/70 px-5 py-3.5 last:border-0 md:grid-cols-[200px_150px_1fr] md:items-start">
                  <div className="flex flex-col gap-1">
                    <span className="t-sub text-ink">{d.label}</span>
                    <div className="flex flex-wrap gap-1">
                      {d.confidence_b && <ConfidenceBadge confidence={d.confidence_b} />}
                    </div>
                  </div>
                  <div className="flex items-center gap-2 font-mono text-[14px] tabular">
                    <span className="text-muted">{d.score_a ?? "—"}</span>
                    <ArrowRight className="size-3.5 text-muted" />
                    <span className="font-semibold text-ink">{d.score_b ?? "—"}</span>
                    <DeltaChip delta={d.delta} />
                  </div>
                  <p className={cn("text-[12.5px] leading-relaxed", d.delta ? "text-ink" : "text-muted")}>{d.reason}</p>
                </li>
              ))}
            </ul>
          </Card>

          <div className="grid gap-4 md:grid-cols-2">
            <ChangeList title="Risks" added={result.risks_added} removed={result.risks_removed} />
            <ChangeList title="Requirements" added={result.requirements_added} removed={result.requirements_removed} />
          </div>

          <Card className="flex flex-col gap-2">
            <h4 className="t-sub text-ink">Idea text</h4>
            <p className="text-[13px] leading-relaxed">
              {result.idea_diff.map((part, i) => (
                <span
                  key={i}
                  className={cn(
                    part.op === "added" && "rounded bg-success-soft px-0.5 text-ink",
                    part.op === "removed" && "rounded bg-danger-soft px-0.5 text-muted line-through",
                    part.op === "equal" && "text-ink/80",
                  )}
                >
                  {part.text}{" "}
                </span>
              ))}
            </p>
          </Card>
        </>
      )}
    </div>
  );
}

export default function ComparePage() {
  return (
    <Suspense fallback={<PageSkeleton cards={3} />}>
      <CompareView />
    </Suspense>
  );
}
