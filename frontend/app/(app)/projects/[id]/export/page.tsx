"use client";

import { Check, Download, FileArchive, FileText, FileType2, Loader2, Minus, NotebookText } from "lucide-react";
import { useParams } from "next/navigation";
import { useCallback, useEffect, useState } from "react";

import { Disclaimer } from "@/components/evaluation/parts";
import { ErrorNotice } from "@/components/states/ErrorNotice";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Select } from "@/components/ui/field";
import { PageSkeleton } from "@/components/ui/skeleton";
import { api } from "@/lib/api";
import type { Blueprint, ExportFormat, ReportsResponse, VersionSummary } from "@/lib/types";

const FORMATS: { format: ExportFormat; label: string; icon: typeof FileText; body: string }[] = [
  { format: "pdf", label: "PDF report", icon: FileText, body: "Cover, contents and every section, with the diagrams drawn in. Best for sharing." },
  { format: "docx", label: "Word document", icon: FileType2, body: "The same report as an editable .docx, diagrams as images." },
  { format: "md", label: "Markdown", icon: NotebookText, body: "One .md file; diagrams stay as Mermaid code. Best for a repository or wiki." },
  { format: "zip", label: "ZIP package", icon: FileArchive, body: "PDF, Word and Markdown reports, each section as its own file, Mermaid sources and project.json." },
];

const CONTENTS: { key: string; label: string }[] = [
  { key: "overview", label: "Idea, understanding and requirements" },
  { key: "feasibility_report", label: "Feasibility report and competitor analysis" },
  { key: "business_model", label: "Business model" },
  { key: "prd", label: "PRD" },
  { key: "ui_ux", label: "UI/UX concepts" },
  { key: "architecture", label: "Architecture" },
  { key: "database_schema", label: "Database schema" },
  { key: "api_spec", label: "API specification" },
  { key: "roadmap", label: "Development roadmap" },
];

function kb(bytes: number): string {
  return bytes > 1024 * 1024 ? `${(bytes / 1024 / 1024).toFixed(1)} MB` : `${Math.max(1, Math.round(bytes / 1024))} KB`;
}

export default function ExportPage() {
  const { id } = useParams<{ id: string }>();
  const [versions, setVersions] = useState<VersionSummary[] | null>(null);
  const [versionNo, setVersionNo] = useState<number | null>(null);
  const [blueprint, setBlueprint] = useState<Blueprint | null>(null);
  const [reports, setReports] = useState<ReportsResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState<ExportFormat | null>(null);
  const [done, setDone] = useState<Partial<Record<ExportFormat, string>>>({});

  useEffect(() => {
    api
      .versions(id)
      .then((list) => {
        setVersions(list);
        setVersionNo((list.find((v) => v.is_current) ?? list[0])?.version_no ?? null);
      })
      .catch((err: Error) => setError(err.message));
  }, [id]);

  const loadContents = useCallback(async () => {
    if (!versionNo) return;
    try {
      const [b, r] = await Promise.all([api.blueprint(id, versionNo), api.reports(id, versionNo)]);
      setBlueprint(b);
      setReports(r);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not read what this version contains.");
    }
  }, [id, versionNo]);

  useEffect(() => {
    setDone({});
    void loadContents();
  }, [loadContents]);

  async function download(format: ExportFormat) {
    if (!versionNo) return;
    setBusy(format);
    setError(null);
    try {
      const { filename, bytes } = await api.exportProject(id, format, versionNo);
      setDone((d) => ({ ...d, [format]: `${filename} · ${kb(bytes)}` }));
    } catch (err) {
      setError(err instanceof Error ? err.message : "The export failed.");
    } finally {
      setBusy(null);
    }
  }

  if (!versions) return error ? <ErrorNotice message={error} /> : <PageSkeleton cards={2} />;

  const present = new Set<string>(["overview"]);
  if (reports?.has_evaluation) {
    present.add("feasibility_report");
    present.add("business_model");
  }
  for (const a of blueprint?.artifacts ?? []) present.add(a.artifact_type);
  const count = CONTENTS.filter((c) => present.has(c.key)).length;

  return (
    <div className="flex flex-col gap-5">
      <div className="flex flex-col justify-between gap-3 sm:flex-row sm:items-center">
        <div className="flex items-baseline gap-2.5">
          <h2 className="t-title text-ink">Export</h2>
          <span className="font-mono text-[12px] text-muted">
            {count}/{CONTENTS.length} sections ready
          </span>
        </div>
        <label className="flex items-center gap-2 text-[12.5px] text-muted">
          Version
          <Select
            aria-label="Version to export"
            className="h-9 w-auto py-1 text-[13px]"
            value={versionNo ?? ""}
            onChange={(e) => setVersionNo(Number(e.target.value))}
          >
            {versions.map((v) => (
              <option key={v.id} value={v.version_no}>
                v{v.version_no}
                {v.is_current ? " (current)" : ""}
              </option>
            ))}
          </Select>
        </label>
      </div>

      <Disclaimer text="Exports carry the same disclaimer as the app: scores are evidence-based estimates, and blueprints are starting points for the team to review." />
      {error && <ErrorNotice message={error} />}

      <div className="grid gap-5 lg:grid-cols-[1fr_300px] lg:items-start">
        <div className="grid gap-4 sm:grid-cols-2">
          {FORMATS.map((f) => (
            <Card key={f.format} className="flex flex-col gap-3">
              <div className="flex items-center gap-2.5">
                <span className="grid size-9 place-items-center rounded-lg bg-primary-soft text-primary">
                  <f.icon className="size-[18px]" />
                </span>
                <h3 className="t-sub text-ink">{f.label}</h3>
              </div>
              <p className="text-[12.5px] leading-relaxed text-muted">{f.body}</p>
              <div className="mt-auto flex flex-wrap items-center gap-2 pt-1">
                <Button size="sm" variant={f.format === "pdf" ? "primary" : "secondary"} onClick={() => download(f.format)} disabled={busy !== null}>
                  {busy === f.format ? <Loader2 className="size-3.5 animate-spin" /> : <Download className="size-3.5" />}
                  {busy === f.format ? "Preparing…" : `Download .${f.format}`}
                </Button>
                {done[f.format] && (
                  <span className="flex items-center gap-1 text-[11.5px] text-success">
                    <Check className="size-3.5" /> {done[f.format]}
                  </span>
                )}
              </div>
            </Card>
          ))}
        </div>

        <Card className="flex flex-col gap-3">
          <h3 className="t-sub text-ink">What v{versionNo} contains</h3>
          <ul className="flex flex-col gap-1.5">
            {CONTENTS.map((c) => {
              const ok = present.has(c.key);
              return (
                <li key={c.key} className="flex items-center gap-2 text-[12.5px]">
                  {ok ? <Check className="size-3.5 shrink-0 text-success" /> : <Minus className="size-3.5 shrink-0 text-muted" />}
                  <span className={ok ? "text-ink" : "text-muted"}>{c.label}</span>
                </li>
              );
            })}
          </ul>
          {count < CONTENTS.length && (
            <p className="border-t border-line pt-3 text-[11.5px] leading-relaxed text-muted">
              Missing sections are listed as “not generated yet” inside the export. Run the full analysis on the Overview
              tab to fill them in.
            </p>
          )}
        </Card>
      </div>
    </div>
  );
}
