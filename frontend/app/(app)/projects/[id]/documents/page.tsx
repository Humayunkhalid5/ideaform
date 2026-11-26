"use client";

import { ArrowRight, BriefcaseBusiness, Check, Copy, FileCheck2, Loader2, RotateCw } from "lucide-react";
import Link from "next/link";
import { useParams, useRouter, useSearchParams } from "next/navigation";
import { Suspense, useCallback, useEffect, useState } from "react";

import { MarkdownDoc } from "@/components/blueprint/MarkdownDoc";
import { Disclaimer } from "@/components/evaluation/parts";
import { EmptyState } from "@/components/states/EmptyState";
import { ErrorNotice } from "@/components/states/ErrorNotice";
import { Button, buttonStyles } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { PageSkeleton } from "@/components/ui/skeleton";
import { api } from "@/lib/api";
import type { ReportsResponse } from "@/lib/types";
import { cn } from "@/lib/utils";

const REPORTS = [
  { type: "feasibility_report", label: "Feasibility report", icon: FileCheck2, blurb: "Scores, evidence, risks, competitors, sources" },
  { type: "business_model", label: "Business model", icon: BriefcaseBusiness, blurb: "Customers, value, revenue, pricing" },
] as const;

function DocumentsView() {
  const params = useParams<{ id: string }>();
  const search = useSearchParams();
  const router = useRouter();
  const id = params.id;

  const [data, setData] = useState<ReportsResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [building, setBuilding] = useState(false);
  const [copied, setCopied] = useState(false);

  const load = useCallback(async () => {
    try {
      setData(await api.reports(id));
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not load the documents.");
    }
  }, [id]);

  useEffect(() => {
    void load();
  }, [load]);

  async function rebuild() {
    setBuilding(true);
    setError(null);
    try {
      setData(await api.rebuildReports(id));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not build the documents.");
    } finally {
      setBuilding(false);
    }
  }

  if (!data) return error ? <ErrorNotice message={error} onRetry={load} /> : <PageSkeleton cards={3} />;

  const selected = (search.get("doc") ?? "feasibility_report") as (typeof REPORTS)[number]["type"];
  const report = data.reports.find((r) => r.artifact_type === selected);

  async function copy() {
    if (!report) return;
    await navigator.clipboard.writeText(report.content);
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  }

  return (
    <div className="flex flex-col gap-5">
      <div className="flex flex-col justify-between gap-3 sm:flex-row sm:items-center">
        <div className="flex items-baseline gap-2.5">
          <h2 className="t-title text-ink">Documents</h2>
          <span className="font-mono text-[12px] text-muted">v{data.version_no}</span>
        </div>
        {data.has_evaluation && (
          <div className="flex items-center gap-2">
            <Button variant="secondary" size="sm" onClick={rebuild} disabled={building}>
              {building ? <Loader2 className="size-3.5 animate-spin" /> : <RotateCw className="size-3.5" />}
              {data.reports.length ? "Rebuild from evaluation" : "Build documents"}
            </Button>
            <Link href={`/projects/${id}/export`} className={buttonStyles("secondary", "sm")}>
              Export <ArrowRight className="size-3.5" />
            </Link>
          </div>
        )}
      </div>

      <Disclaimer text="Built by the Documentation Agent from the stored evaluation: no extra model call, and every citation is one the evidence validation accepted." />
      {error && <ErrorNotice message={error} onRetry={load} />}

      {!data.has_evaluation ? (
        <EmptyState
          title="Nothing to report yet"
          body="The feasibility report and business model are written from this version's evaluation. Evaluate it, or run the full analysis from the Overview tab."
          action={
            <Link href={`/projects/${id}/evaluation`} className={buttonStyles("primary", "md")}>
              Go to Evaluation <ArrowRight className="size-4" />
            </Link>
          }
        />
      ) : data.reports.length === 0 ? (
        <EmptyState
          title="Documents not built yet"
          body="This version has an evaluation. Build the feasibility report and business model from it; it takes a second and uses no tokens."
          action={
            <Button onClick={rebuild} disabled={building}>
              {building ? <Loader2 className="size-4 animate-spin" /> : <FileCheck2 className="size-4" />} Build documents
            </Button>
          }
        />
      ) : (
        <div className="grid gap-5 lg:grid-cols-[240px_1fr] lg:items-start">
          <nav aria-label="Documents" className="no-scrollbar flex gap-2 overflow-x-auto lg:sticky lg:top-20 lg:flex-col lg:gap-1">
            {REPORTS.map((r) => {
              const item = data.reports.find((x) => x.artifact_type === r.type);
              const active = r.type === selected;
              return (
                <button
                  key={r.type}
                  type="button"
                  onClick={() => router.replace(`/projects/${id}/documents?doc=${r.type}`, { scroll: false })}
                  aria-current={active ? "page" : undefined}
                  className={cn(
                    "flex min-w-[200px] items-start gap-2.5 rounded-lg border px-3 py-2.5 text-left transition-colors duration-150 lg:min-w-0",
                    active ? "border-primary/30 bg-primary-soft" : "border-transparent hover:bg-surface-soft",
                  )}
                >
                  <r.icon className={cn("mt-0.5 size-4 shrink-0", active ? "text-primary" : "text-muted")} />
                  <span className="flex min-w-0 flex-col gap-0.5">
                    <span className={cn("text-[13px] font-medium", active ? "text-primary" : "text-ink")}>{r.label}</span>
                    <span className="truncate text-[11.5px] text-muted">{item ? `v${item.artifact_version} · ${r.blurb}` : "Not built"}</span>
                  </span>
                </button>
              );
            })}
            <Link
              href={`/projects/${id}/blueprint`}
              className="flex min-w-[200px] items-center gap-2 rounded-lg px-3 py-2.5 text-[12.5px] text-muted transition-colors duration-150 hover:bg-surface-soft hover:text-ink lg:min-w-0"
            >
              Blueprint sections <ArrowRight className="size-3.5" />
            </Link>
          </nav>

          <Card className="flex min-w-0 flex-col gap-0 p-0">
            {report ? (
              <>
                <div className="flex flex-wrap items-center gap-2 border-b border-line px-5 py-4">
                  <h3 className="t-sub mr-auto text-ink">{REPORTS.find((r) => r.type === selected)?.label}</h3>
                  <span className="font-mono text-[11px] text-muted">
                    v{report.artifact_version} · {new Date(report.created_at).toLocaleString()}
                  </span>
                  <Button size="sm" variant="ghost" onClick={copy}>
                    {copied ? <Check className="size-3.5" /> : <Copy className="size-3.5" />}
                    {copied ? "Copied" : "Copy"}
                  </Button>
                </div>
                <div className="min-w-0 px-5 py-5">
                  <MarkdownDoc content={report.content} />
                </div>
              </>
            ) : (
              <div className="p-6 text-[13px] text-muted">This document has not been built for this version.</div>
            )}
          </Card>
        </div>
      )}
    </div>
  );
}

export default function DocumentsPage() {
  return (
    <Suspense fallback={<PageSkeleton cards={3} />}>
      <DocumentsView />
    </Suspense>
  );
}
