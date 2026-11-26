"use client";

import { AlertTriangle, ArrowLeft, Clock, Loader2, RotateCw, Sparkles } from "lucide-react";
import Link from "next/link";
import { useParams, useRouter, useSearchParams } from "next/navigation";
import { Suspense, useCallback, useEffect, useMemo, useState } from "react";

import { AnalysisProgress } from "@/components/run/AnalysisProgress";
import { PipelineTimeline } from "@/components/run/PipelineTimeline";
import { RadialGauge } from "@/components/scores/RadialGauge";
import { ErrorNotice } from "@/components/states/ErrorNotice";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { PageSkeleton } from "@/components/ui/skeleton";
import { api } from "@/lib/api";
import type { Run, RunWithOutput } from "@/lib/types";
import { cn } from "@/lib/utils";

const STEPS = [
  { label: "Queued", detail: "Run accepted for this version." },
  { label: "Classify", detail: "Picks business, software or technology." },
  { label: "Extract", detail: "Structure, gaps and requirements." },
  { label: "Save", detail: "Writes the understanding record." },
];

function progressFor(run: Run | null): number {
  if (!run) return 4;
  if (run.status === "queued") return 12;
  if (run.status === "running") return 58;
  if (run.status === "succeeded") return 100;
  return 58;
}

function currentStep(run: Run | null): number {
  if (!run) return 0;
  if (run.status === "queued") return 0;
  if (run.status === "running") return 2;
  if (run.status === "succeeded") return STEPS.length;
  return 2;
}

function RunView() {
  const params = useParams<{ id: string }>();
  const search = useSearchParams();
  const router = useRouter();
  const projectId = params.id;
  const runId = search.get("run");

  const [run, setRun] = useState<Run | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [retrying, setRetrying] = useState(false);

  const poll = useCallback(async () => {
    if (!runId) return;
    try {
      const data = await api.run(runId);
      setRun(data);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not read the run status.");
    }
  }, [runId]);

  useEffect(() => {
    if (!runId) return;
    let timer: ReturnType<typeof setInterval> | undefined;

    const tick = async () => {
      await poll();
    };

    void tick();
    timer = setInterval(() => {
      void tick();
    }, 2000);

    return () => {
      if (timer) clearInterval(timer);
    };
  }, [poll, runId]);

  const finished = run?.status === "succeeded";
  useEffect(() => {
    if (!finished || !run || run.agent_name === "analysis") return;
    const output = (run as RunWithOutput).output as { compare?: { a: number; b: number } } | null;
    const target =
      run.agent_name === "evaluation"
        ? `/projects/${projectId}/evaluation`
        : run.agent_name === "improvement" && output?.compare
          ? `/projects/${projectId}/compare?a=${output.compare.a}&b=${output.compare.b}`
          : run.agent_name === "research"
            ? `/projects/${projectId}/research`
            : run.agent_name === "blueprint"
              ? `/projects/${projectId}/blueprint`
              : `/projects/${projectId}/understand`;
    const timer = setTimeout(() => {
      router.replace(target);
    }, 1400);
    return () => clearTimeout(timer);
  }, [finished, run, projectId, router]);

  const progress = progressFor(run);
  const step = currentStep(run);
  const failed = run?.status === "failed";

  const logLines = useMemo(() => {
    const stamp = run?.started_at
      ? new Date(run.started_at).toLocaleTimeString([], { hour12: false })
      : "--:--:--";
    const reached = run?.status === "succeeded" ? 99 : step;
    const lines = [
      `${stamp}  run ${run ? run.id.slice(0, 8) : "--------"} accepted`,
      `${stamp}  agent=${run?.agent_name ?? "understanding"}  provider=groq`,
    ];
    if (reached >= 1) lines.push(`${stamp}  classifying category`);
    if (reached >= 2) lines.push(`${stamp}  extracting structure and requirements`);
    if (reached >= 3) lines.push(`${stamp}  persisting version record`);
    if (run?.status === "succeeded") lines.push(`${stamp}  run succeeded`);
    if (run?.status === "failed") lines.push(`${stamp}  run failed: ${run.error_message ?? "unknown error"}`);
    if (run?.model_name) lines.push(`${stamp}  model=${run.model_name}`);
    if (run?.tokens_in || run?.tokens_out) {
      lines.push(`${stamp}  tokens in=${run.tokens_in ?? 0} out=${run.tokens_out ?? 0}`);
    }
    return lines;
  }, [run, step]);

  async function retry() {
    setRetrying(true);
    setError(null);
    try {
      const next = await api.understand(projectId);
      if (next.status === "queued") {
        router.replace(`/projects/${projectId}/run?run=${next.run_id}`);
        setRun(null);
      } else {
        router.replace(`/projects/${projectId}/understand`);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not restart extraction.");
    } finally {
      setRetrying(false);
    }
  }

  if (!runId) {
    return (
      <Card className="flex flex-col items-start gap-3">
        <h3 className="t-sub text-ink">No run selected</h3>
        <p className="text-[13px] text-muted">
          This page tracks an extraction run. Start one from the understanding tab.
        </p>
        <Link
          href={`/projects/${projectId}/understand`}
          className="text-[12.5px] font-medium text-primary hover:underline"
        >
          Go to understanding
        </Link>
      </Card>
    );
  }

  if (run?.agent_name === "analysis") return <AnalysisProgress runId={runId} projectId={projectId} />;

  return (
    <div className="flex flex-col gap-4">
      {error && <ErrorNotice message={error} onRetry={poll} />}

      <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_360px]">
        <Card className="flex flex-col gap-6">
          <div className="flex flex-col gap-1.5">
            <span className="t-label text-primary">Understanding run</span>
            <h3 className="t-section text-ink">
              {failed
                ? "The run stopped early."
                : finished
                  ? "Done. Opening the record…"
                  : "Reading your idea."}
            </h3>
            <p className="max-w-md text-[12.5px] leading-relaxed text-muted">
              {failed
                ? "The model call or the write did not complete. Nothing was lost — the version is untouched."
                : "Classification, structured extraction and requirement typing, grounded only in the words of this version."}
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-6">
            <RadialGauge value={progress} size={120} stroke={9} label="progress" suffix="%" />
            <div className="flex min-w-0 flex-1 flex-col gap-3">
              <PipelineTimeline steps={STEPS} current={step} failed={failed} />
            </div>
          </div>

          {failed ? (
            <div className="flex flex-col gap-3 rounded-lg border border-danger/25 bg-danger-soft p-4">
              <p className="flex items-center gap-2 text-[12.5px] font-medium text-danger">
                <AlertTriangle className="size-4" /> {run?.error_message ?? "Extraction failed."}
              </p>
              <div className="flex flex-wrap items-center gap-3">
                <Button size="sm" onClick={retry} disabled={retrying}>
                  {retrying ? <Loader2 className="size-3.5 animate-spin" /> : <RotateCw className="size-3.5" />}
                  Try again
                </Button>
                <Link
                  href={`/projects/${projectId}`}
                  className="text-[12px] text-muted underline-offset-4 hover:underline"
                >
                  Back to project
                </Link>
              </div>
            </div>
          ) : (
            <div className="flex flex-wrap items-center justify-between gap-3 border-t border-line pt-4">
              <p className="flex items-center gap-1.5 text-[11.5px] text-muted">
                <Clock className="size-3.5" />
                {finished
                  ? "Done. Redirecting to the understanding tab."
                  : "Polling every 2 seconds. You can leave this tab open."}
              </p>
              <Link
                href={`/projects/${projectId}`}
                className="flex items-center gap-1 text-[12px] font-medium text-muted transition-colors hover:text-ink"
              >
                <ArrowLeft className="size-3.5" /> Continue in background
              </Link>
            </div>
          )}
        </Card>

        <Card className="flex flex-col gap-0 p-0">
          <div className="flex items-center justify-between gap-2 border-b border-line px-4 py-3">
            <p className="text-[12px] font-semibold text-ink">Run log</p>
            <span
              className={cn(
                "flex items-center gap-1.5 rounded-full px-2 py-0.5 font-mono text-[10.5px] font-medium",
                failed
                  ? "bg-danger-soft text-danger"
                  : finished
                    ? "bg-success-soft text-success"
                    : "bg-accent-soft text-accent",
              )}
            >
              <span className={cn("size-1.5 rounded-full bg-current", !finished && !failed && "animate-pulse")} />
              {run?.status ?? "connecting"}
            </span>
          </div>
          <div
            className="min-h-52 flex-1 overflow-x-auto px-4 py-3 font-mono text-[11px] leading-relaxed text-muted"
            aria-live="polite"
          >
            {logLines.map((line) => (
              <p key={line} className="whitespace-pre">
                <span className="text-primary">›</span> {line}
              </p>
            ))}
            {!finished && !failed && <p className="animate-pulse text-muted/70">› …</p>}
          </div>
          <div className="border-t border-line px-4 py-3">
            <p className="t-label text-muted">Run</p>
            <p className="mt-1 break-all font-mono text-[11px] text-ink/80">{runId}</p>
          </div>
        </Card>
      </div>

      <p className="flex items-center gap-1.5 px-1 text-[11.5px] text-muted">
        <Sparkles className="size-3.5 text-primary" />
        Extraction runs against this version only; earlier text is never overwritten.
      </p>
    </div>
  );
}

export default function RunPage() {
  return (
    <Suspense fallback={<PageSkeleton cards={2} />}>
      <RunView />
    </Suspense>
  );
}
