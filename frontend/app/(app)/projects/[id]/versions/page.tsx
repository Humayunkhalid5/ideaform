"use client";

import { GitCompare, History, Loader2, RotateCcw } from "lucide-react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useCallback, useEffect, useState } from "react";

import { ErrorNotice } from "@/components/states/ErrorNotice";
import { Button, buttonStyles } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { PageSkeleton } from "@/components/ui/skeleton";
import { api } from "@/lib/api";
import type { HistoryVersion, ProjectHistory, TrackedRun } from "@/lib/types";
import { cn } from "@/lib/utils";

const RUN_LABEL: Record<string, string> = {
  analysis: "Full analysis",
  understanding: "Understanding",
  requirements: "Requirements",
  research: "Research",
  evaluation: "Evaluation",
  improvement: "Improvement",
  blueprint: "Blueprint",
  export: "Export",
};

const STATUS_STYLE: Record<string, string> = {
  succeeded: "bg-success-soft text-success",
  failed: "bg-danger-soft text-danger",
  running: "bg-accent-soft text-accent",
  queued: "bg-surface-soft text-muted",
};

function artifactHref(projectId: string, type: string): string {
  return ["feasibility_report", "business_model"].includes(type)
    ? `/projects/${projectId}/documents?doc=${type}`
    : `/projects/${projectId}/blueprint?section=${type}`;
}

function VersionCard({ v, projectId, previous, onRestore, restoring }: {
  v: HistoryVersion;
  projectId: string;
  previous?: HistoryVersion;
  onRestore: (n: number) => void;
  restoring: boolean;
}) {
  const [open, setOpen] = useState(v.is_current);
  const score = v.evaluations[0]?.overall_score;
  return (
    <li className="relative pl-7">
      <span
        className={cn(
          "absolute left-0 top-5 grid size-[18px] place-items-center rounded-full border-2",
          v.is_current ? "border-primary bg-primary-soft" : "border-line bg-surface",
        )}
        aria-hidden="true"
      />
      <Card className="flex flex-col gap-3">
        <div className="flex flex-wrap items-center gap-2">
          <h3 className="t-sub text-ink">Version {v.version_no}</h3>
          {v.is_current && <span className="rounded-full bg-primary-soft px-2 py-0.5 text-[11px] font-medium text-primary">current</span>}
          <span className="font-mono text-[11.5px] text-muted">{new Date(v.created_at).toLocaleString()}</span>
          <span className="ml-auto flex flex-wrap items-center gap-2">
            {score != null && (
              <span className="rounded-full bg-surface-soft px-2.5 py-0.5 font-mono text-[11.5px] text-ink">score {score}</span>
            )}
            {previous && (
              <Link href={`/projects/${projectId}/compare?a=${previous.version_no}&b=${v.version_no}`} className={buttonStyles("ghost", "sm")}>
                <GitCompare className="size-3.5" /> Compare with v{previous.version_no}
              </Link>
            )}
            {!v.is_current && (
              <Button size="sm" variant="secondary" onClick={() => onRestore(v.version_no)} disabled={restoring}>
                {restoring ? <Loader2 className="size-3.5 animate-spin" /> : <RotateCcw className="size-3.5" />} Make current
              </Button>
            )}
          </span>
        </div>

        <button type="button" onClick={() => setOpen((o) => !o)} className="text-left text-[13px] leading-relaxed text-ink/85" aria-expanded={open}>
          <span className={cn(!open && "line-clamp-2")}>{v.idea_text}</span>
          <span className="ml-1 text-[12px] font-medium text-primary">{open ? "Show less" : "Show more"}</span>
        </button>

        <div className="flex flex-wrap gap-x-6 gap-y-1 text-[12px] text-muted">
          <span>{v.understood ? "Understood" : "Not understood yet"}</span>
          <span>
            {v.evaluations.length} evaluation{v.evaluations.length === 1 ? "" : "s"}
          </span>
          <span>{v.artifacts.length} document types</span>
        </div>

        {v.artifacts.length > 0 && (
          <div className="overflow-x-auto rounded-lg border border-line">
            <table className="w-full text-[12.5px]">
              <thead className="bg-surface-soft text-left text-muted">
                <tr>
                  <th className="px-3 py-2 font-medium">Document</th>
                  <th className="px-3 py-2 font-medium">Versions (newest first)</th>
                </tr>
              </thead>
              <tbody>
                {v.artifacts.map((a) => (
                  <tr key={a.artifact_type} className="border-t border-line">
                    <td className="whitespace-nowrap px-3 py-2">
                      <Link href={artifactHref(projectId, a.artifact_type)} className="font-medium text-ink hover:text-primary">
                        {a.title}
                      </Link>
                    </td>
                    <td className="px-3 py-2">
                      <span className="flex flex-wrap gap-1.5">
                        {a.versions.map((x) => (
                          <span
                            key={x.id}
                            title={`${new Date(x.created_at).toLocaleString()}${x.instructions ? ` · instructions: ${x.instructions}` : ""}`}
                            className={cn(
                              "rounded-md px-1.5 py-0.5 font-mono text-[11px]",
                              x.edited_by_user ? "bg-info-soft text-info" : x.instructions ? "bg-warning-soft text-warning" : "bg-surface-soft text-ink",
                            )}
                          >
                            v{x.artifact_version}
                            {x.edited_by_user ? " edited" : x.instructions ? " instr." : ""}
                          </span>
                        ))}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>
    </li>
  );
}

function RunRow({ run, projectId }: { run: TrackedRun; projectId: string }) {
  const tokens = (run.tokens_in ?? 0) + (run.tokens_out ?? 0);
  return (
    <tr className="border-t border-line align-top">
      <td className="whitespace-nowrap px-3 py-2">
        {run.agent_name === "analysis" ? (
          <Link href={`/projects/${projectId}/run?run=${run.id}`} className="font-medium text-ink hover:text-primary">
            {RUN_LABEL[run.agent_name]}
          </Link>
        ) : (
          <span className="font-medium text-ink">{RUN_LABEL[run.agent_name] ?? run.agent_name}</span>
        )}
      </td>
      <td className="px-3 py-2">
        <span className={cn("rounded-full px-2 py-0.5 text-[11px] font-medium", STATUS_STYLE[run.status] ?? "bg-surface-soft text-muted")}>
          {run.status}
        </span>
      </td>
      <td className="whitespace-nowrap px-3 py-2 font-mono text-[11.5px] text-muted">{run.started_at ? new Date(run.started_at).toLocaleString() : "—"}</td>
      <td className="px-3 py-2 text-right font-mono text-[11.5px] text-ink">{run.duration_seconds != null ? `${Math.round(run.duration_seconds)} s` : "—"}</td>
      <td className="px-3 py-2 text-right font-mono text-[11.5px] text-ink">{tokens ? tokens.toLocaleString() : "0"}</td>
      <td className="px-3 py-2 text-[11.5px] text-muted">
        <span className="block font-mono">{run.model_name ?? "—"}</span>
        {run.prompt_version && <span className="block font-mono text-muted/80">{run.prompt_version}</span>}
        {run.error_message && <span className="mt-1 block text-danger">{run.error_message}</span>}
      </td>
    </tr>
  );
}

export default function VersionsPage() {
  const { id } = useParams<{ id: string }>();
  const [history, setHistory] = useState<ProjectHistory | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [restoring, setRestoring] = useState(false);

  const load = useCallback(async () => {
    try {
      setHistory(await api.history(id));
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not load the history.");
    }
  }, [id]);

  useEffect(() => {
    void load();
  }, [load]);

  async function restore(versionNo: number) {
    setRestoring(true);
    try {
      await api.restoreVersion(id, versionNo);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not restore that version.");
    } finally {
      setRestoring(false);
    }
  }

  if (!history) return error ? <ErrorNotice message={error} onRetry={load} /> : <PageSkeleton cards={3} />;

  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-baseline gap-2.5">
        <h2 className="flex items-center gap-2 t-title text-ink">
          <History className="size-5 text-primary" /> Versions
        </h2>
        <span className="font-mono text-[12px] text-muted">
          {history.versions.length} idea version{history.versions.length === 1 ? "" : "s"}
        </span>
      </div>
      {error && <ErrorNotice message={error} onRetry={load} />}

      <ol className="relative flex flex-col gap-4 before:absolute before:bottom-4 before:left-[8.5px] before:top-6 before:w-px before:bg-line">
        {history.versions.map((v, i) => (
          <VersionCard
            key={v.id}
            v={v}
            projectId={id}
            previous={history.versions[i + 1]}
            onRestore={restore}
            restoring={restoring}
          />
        ))}
      </ol>

      <Card className="flex flex-col gap-0 p-0">
        <div className="border-b border-line px-5 py-3">
          <h3 className="t-sub text-ink">Run history</h3>
          <p className="text-[12px] text-muted">Every agent run with its model, prompt version, tokens, time and errors.</p>
        </div>
        {history.runs.length === 0 ? (
          <p className="px-5 py-4 text-[12.5px] text-muted">No runs yet.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-[12.5px]">
              <thead className="text-left text-muted">
                <tr>
                  <th className="px-3 py-2 font-medium">Run</th>
                  <th className="px-3 py-2 font-medium">Status</th>
                  <th className="px-3 py-2 font-medium">Started</th>
                  <th className="px-3 py-2 text-right font-medium">Time</th>
                  <th className="px-3 py-2 text-right font-medium">Tokens</th>
                  <th className="px-3 py-2 font-medium">Model · prompts · errors</th>
                </tr>
              </thead>
              <tbody>
                {history.runs.map((r) => (
                  <RunRow key={r.id} run={r} projectId={id} />
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>
    </div>
  );
}
