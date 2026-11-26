"use client";

import { AlertTriangle, ArrowRight, Check, Clock, Download, Loader2, Minus } from "lucide-react";
import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import { RadialGauge } from "@/components/scores/RadialGauge";
import { ErrorNotice } from "@/components/states/ErrorNotice";
import { buttonStyles } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { api } from "@/lib/api";
import type { AnalysisOutput, AnalysisStep, StepName, TrackedRun } from "@/lib/types";
import { cn } from "@/lib/utils";

const PIPELINE: { step: StepName; label: string; detail: string; href: string }[] = [
  { step: "understanding", label: "Understanding", detail: "Category, structure and requirements", href: "understand" },
  { step: "research", label: "Research Agent", detail: "Sources found, fetched and indexed", href: "research" },
  { step: "evaluation", label: "Evaluation Agent", detail: "Six scored dimensions with evidence", href: "evaluation" },
  { step: "evidence_validation", label: "Evidence validation", detail: "Every citation and claim label checked", href: "evaluation" },
  { step: "business", label: "Business Agent", detail: "Customers, pricing and revenue", href: "documents" },
  { step: "product_design", label: "Product Design Agent", detail: "Requirements, flows and screens", href: "blueprint?section=ui_ux" },
  { step: "technical_architect", label: "Technical Architect Agent", detail: "Stack, architecture, schema and API", href: "blueprint?section=architecture" },
  { step: "documentation", label: "Documentation Agent", detail: "PRD, roadmap and reports", href: "documents" },
];

function StepIcon({ status }: { status?: AnalysisStep["status"] }) {
  if (status === "succeeded") return <Check className="size-4 text-success" />;
  if (status === "running") return <Loader2 className="size-4 animate-spin text-primary" />;
  if (status === "failed") return <AlertTriangle className="size-4 text-danger" />;
  if (status === "skipped") return <Minus className="size-4 text-muted" />;
  return <span className="size-3 rounded-full border border-line" aria-hidden="true" />;
}

/** Live progress of a full analysis run (one row per agent step). */
export function AnalysisProgress({ runId, projectId }: { runId: string; projectId: string }) {
  const [run, setRun] = useState<TrackedRun | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      setRun(await api.trackedRun(runId));
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not read the run.");
    }
  }, [runId]);

  const done = run?.status === "succeeded" || run?.status === "failed";
  useEffect(() => {
    void load();
    if (done) return;
    const timer = setInterval(() => void load(), 2500);
    return () => clearInterval(timer);
  }, [load, done]);

  const output = (run?.output ?? null) as AnalysisOutput | null;
  const steps = Object.fromEntries((output?.steps ?? []).map((s) => [s.step, s])) as Partial<Record<StepName, AnalysisStep>>;
  const finished = PIPELINE.filter((p) => steps[p.step] && steps[p.step]?.status !== "running").length;
  const progress = run?.status === "succeeded" ? 100 : Math.max(4, Math.round((finished / PIPELINE.length) * 100));
  const failed = run?.status === "failed";
  const seconds = output?.seconds ?? run?.duration_seconds ?? null;

  return (
    <div className="flex flex-col gap-4">
      {error && <ErrorNotice message={error} onRetry={load} />}
      <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_340px]">
        <Card className="flex flex-col gap-5">
          <div className="flex flex-col gap-1.5">
            <span className="t-label text-primary">Full analysis</span>
            <h3 className="t-section text-ink">
              {failed ? "The analysis stopped." : run?.status === "succeeded" ? "Analysis complete." : "Analysing your idea."}
            </h3>
            <p className="max-w-xl text-[12.5px] leading-relaxed text-muted">
              {failed
                ? "Understanding failed, so nothing after it could run. Fix the idea text or try again; finished work is kept."
                : "Each agent runs in order and is checked before the next one starts. A failing step is retried once; if it fails again the analysis continues and marks it low confidence."}
            </p>
          </div>

          <div className="flex flex-wrap items-start gap-6">
            <RadialGauge value={progress} size={112} stroke={9} label="progress" suffix="%" />
            <ol className="flex min-w-0 flex-1 flex-col">
              {PIPELINE.map((p) => {
                const s = steps[p.step];
                const canOpen = s?.status === "succeeded";
                return (
                  <li key={p.step} className="flex items-start gap-3 border-b border-line/70 py-2.5 last:border-0">
                    <span className="mt-0.5 grid size-5 place-items-center">
                      <StepIcon status={s?.status} />
                    </span>
                    <div className="flex min-w-0 flex-1 flex-col gap-0.5">
                      <div className="flex flex-wrap items-center gap-2">
                        <span className={cn("text-[13px] font-medium", s ? "text-ink" : "text-muted")}>{p.label}</span>
                        {s?.attempt && s.attempt > 1 && (
                          <span className="rounded-full bg-warning-soft px-2 py-0.5 text-[10.5px] font-medium text-warning">retried</span>
                        )}
                        {output?.low_confidence.includes(p.step) && (
                          <span className="rounded-full bg-warning-soft px-2 py-0.5 text-[10.5px] font-medium text-warning">low confidence</span>
                        )}
                      </div>
                      <span className="text-[11.5px] text-muted">
                        {s?.status === "skipped"
                          ? `Skipped: ${s.reason}`
                          : s?.status === "failed"
                            ? s.error ?? "Failed"
                            : p.detail}
                      </span>
                    </div>
                    <span className="flex items-center gap-2 font-mono text-[11px] text-muted">
                      {s?.seconds != null && `${s.seconds}s`}
                      {canOpen && (
                        <Link href={`/projects/${projectId}/${p.href}`} className="text-primary hover:underline">
                          open
                        </Link>
                      )}
                    </span>
                  </li>
                );
              })}
            </ol>
          </div>

          {run?.status === "succeeded" && (
            <div className="flex flex-wrap items-center gap-2 border-t border-line pt-4">
              <Link href={`/projects/${projectId}/documents`} className={buttonStyles("primary", "md")}>
                Open the reports <ArrowRight className="size-4" />
              </Link>
              <Link href={`/projects/${projectId}/export`} className={buttonStyles("secondary", "md")}>
                <Download className="size-4" /> Export PDF or ZIP
              </Link>
            </div>
          )}
        </Card>

        <Card className="flex flex-col gap-4">
          <div className="flex items-center justify-between">
            <p className="text-[12px] font-semibold text-ink">Run</p>
            <span
              className={cn(
                "flex items-center gap-1.5 rounded-full px-2 py-0.5 font-mono text-[10.5px] font-medium",
                failed ? "bg-danger-soft text-danger" : run?.status === "succeeded" ? "bg-success-soft text-success" : "bg-accent-soft text-accent",
              )}
            >
              <span className={cn("size-1.5 rounded-full bg-current", !done && "animate-pulse")} />
              {run?.status ?? "connecting"}
            </span>
          </div>
          <dl className="grid grid-cols-2 gap-x-3 gap-y-2 text-[12px]">
            <dt className="text-muted">Help level</dt>
            <dd className="text-right text-ink">{output?.depth ?? String(run?.input?.depth ?? "—")}</dd>
            <dt className="text-muted">Time</dt>
            <dd className="text-right font-mono text-ink">{seconds != null ? `${Math.round(seconds)} s` : "—"}</dd>
            <dt className="text-muted">Tokens</dt>
            <dd className="text-right font-mono text-ink">{(output?.tokens ?? 0).toLocaleString()}</dd>
            <dt className="text-muted">Overall score</dt>
            <dd className="text-right font-mono text-ink">{output?.overall_score ?? "—"}</dd>
            <dt className="text-muted">Sources stored</dt>
            <dd className="text-right font-mono text-ink">{output?.sources ?? "—"}</dd>
          </dl>
          {output?.stopped && (
            <p className="rounded-lg bg-warning-soft px-3 py-2 text-[12px] text-ink">Stopped early: {output.stopped}</p>
          )}
          {(output?.notices ?? []).length > 0 && (
            <ul className="flex flex-col gap-1.5">
              {output!.notices.map((n) => (
                <li key={n} className="rounded-lg bg-surface-soft px-3 py-2 text-[11.5px] text-muted">
                  {n}
                </li>
              ))}
            </ul>
          )}
          {(output?.errors ?? []).length > 0 && (
            <ul className="flex flex-col gap-1.5">
              {output!.errors.map((e) => (
                <li key={e} className="rounded-lg bg-danger-soft px-3 py-2 text-[11.5px] text-danger">
                  {e}
                </li>
              ))}
            </ul>
          )}
          <p className="mt-auto flex items-center gap-1.5 border-t border-line pt-3 text-[11px] text-muted">
            <Clock className="size-3.5" />
            {done ? "Finished. Every step is listed on the Versions tab." : "Updates every few seconds. You can leave this page; the run continues."}
          </p>
        </Card>
      </div>
    </div>
  );
}
