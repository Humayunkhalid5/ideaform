"use client";

import {
  AlertTriangle,
  ArrowRight,
  ArrowUpRight,
  Check,
  Info,
  Lock,
  Sparkles,
  Users,
} from "lucide-react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useCallback, useEffect, useState } from "react";

import { RadialGauge } from "@/components/scores/RadialGauge";
import { ErrorNotice } from "@/components/states/ErrorNotice";
import { Badge } from "@/components/ui/badge";
import { buttonStyles } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { PageSkeleton } from "@/components/ui/skeleton";
import { api } from "@/lib/api";
import { DISCLAIMER } from "@/lib/constants";
import { HELP_LEVEL_LABEL, readStructured, REQUIREMENT_GROUPS } from "@/lib/idea";
import type { ProjectDetail } from "@/lib/types";

const NEXT_PHASES = [
  { phase: "Phase 2", title: "Research", body: "Market and technical sources you can open and check.", path: "research" },
  { phase: "Phase 3", title: "Evaluation", body: "Six scored dimensions with evidence, risks, competitors and an improvement loop.", path: "evaluation" },
  { phase: "Phase 4", title: "Blueprint", body: "PRD, architecture, schema, UI/UX and a roadmap.", path: null },
];

export default function ProjectOverviewPage() {
  const params = useParams<{ id: string }>();
  const id = params.id;
  const [project, setProject] = useState<ProjectDetail | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(() => {
    setError(null);
    api
      .project(id)
      .then(setProject)
      .catch((err: Error) => setError(err.message));
  }, [id]);

  useEffect(() => {
    load();
  }, [load]);

  if (!project) {
    return error ? <ErrorNotice message={error} onRetry={load} /> : <PageSkeleton cards={3} />;
  }

  const structured = readStructured(project.version?.structured_idea);
  const confirmed = project.requirements.filter((item) => item.confirmed).length;
  const total = project.requirements.length;
  const percentage = total === 0 ? 0 : Math.round((confirmed / total) * 100);

  if (!structured) {
    return (
      <div className="flex flex-col gap-4">
        {error && <ErrorNotice message={error} onRetry={load} />}
        <Card className="flex flex-col items-start gap-4">
          <span className="grid size-11 place-items-center rounded-lg bg-warning-soft text-warning">
            <AlertTriangle className="size-5" />
          </span>
          <div className="flex flex-col gap-1.5">
            <h3 className="t-title text-ink">This idea has not been understood yet</h3>
            <p className="max-w-xl text-[13px] leading-relaxed text-muted">
              Nothing is invented before extraction runs. Start it now — the model reads version{" "}
              {project.version?.version_no ?? 1} and fills in structure, gaps and requirements.
            </p>
          </div>
          <Link href={`/projects/${id}/understand`} className={buttonStyles("primary", "md")}>
            <Sparkles className="size-4" /> Understand this idea
          </Link>
        </Card>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-4">
      {error && <ErrorNotice message={error} onRetry={load} />}

      <div className="flex items-start gap-2 rounded-xl border border-primary/20 bg-primary-soft/60 px-4 py-3 text-[12.5px] text-ink">
        <Info className="mt-0.5 size-4 shrink-0 text-primary" />
        <p>
          {DISCLAIMER} Phase 1 shows the extracted structure only — scores and blueprints arrive in
          later phases.
        </p>
      </div>

      <div className="grid gap-4 lg:grid-cols-3">
        {/* Idea summary */}
        <Card className="flex flex-col gap-4 lg:col-span-2">
          <div className="flex items-center justify-between gap-3">
            <h3 className="t-sub text-ink">The problem</h3>
            <Badge tone="success">
              <Check className="size-3" /> Understood
            </Badge>
          </div>
          <p className="text-[14px] leading-relaxed text-ink/90">
            {structured.problem ?? "No problem statement was extracted."}
          </p>

          <div className="grid gap-4 border-t border-line pt-4 sm:grid-cols-2">
            <div className="flex flex-col gap-2">
              <p className="t-label flex items-center gap-1.5 text-muted">
                <Users className="size-3.5" /> Target users
              </p>
              <div className="flex flex-wrap gap-1.5">
                {(structured.target_users ?? []).length > 0 ? (
                  structured.target_users?.map((user) => (
                    <span
                      key={user}
                      className="rounded-md bg-surface-soft px-2 py-0.5 text-[12px] text-ink"
                    >
                      {user}
                    </span>
                  ))
                ) : (
                  <span className="text-[12px] text-muted">Not stated in the idea.</span>
                )}
              </div>
            </div>
            <div className="flex flex-col gap-2">
              <p className="t-label text-muted">Technologies mentioned</p>
              <div className="flex flex-wrap gap-1.5">
                {(structured.technologies_mentioned ?? []).length > 0 ? (
                  structured.technologies_mentioned?.map((tech) => (
                    <span
                      key={tech}
                      className="rounded-md bg-surface-soft px-2 py-0.5 font-mono text-[11.5px] text-ink"
                    >
                      {tech}
                    </span>
                  ))
                ) : (
                  <span className="text-[12px] text-muted">No specific stack was named.</span>
                )}
              </div>
            </div>
          </div>
        </Card>

        {/* Requirements */}
        <Card className="flex flex-col gap-3">
          <div className="flex items-center justify-between gap-2">
            <h3 className="t-sub text-ink">Requirements</h3>
            <Link
              href={`/projects/${id}/understand`}
              className="flex items-center gap-1 text-[12px] font-medium text-primary hover:underline"
            >
              Review <ArrowUpRight className="size-3.5" />
            </Link>
          </div>
          <div className="flex items-center gap-4">
            <RadialGauge value={percentage} size={96} stroke={8} label="confirmed" />
            <div className="flex flex-col gap-1">
              <p className="text-[13px] font-medium tabular text-ink">
                {confirmed} of {total}
              </p>
              <p className="text-[11.5px] leading-snug text-muted">
                Confirm the ones that match your intent.
              </p>
            </div>
          </div>
          <div className="flex flex-col gap-1.5 border-t border-line pt-3">
            {REQUIREMENT_GROUPS.map((group) => {
              const count = project.requirements.filter((item) => item.req_type === group.type).length;
              return (
                <div key={group.type} className="flex items-center justify-between text-[12px]">
                  <span className="text-muted">{group.label}</span>
                  <span className="font-medium tabular text-ink">{count}</span>
                </div>
              );
            })}
          </div>
        </Card>

        {/* Features */}
        <Card className="flex flex-col gap-3 lg:col-span-2">
          <h3 className="t-sub text-ink">Key features</h3>
          <ol className="grid gap-2 sm:grid-cols-2">
            {(structured.key_features ?? []).map((feature, index) => (
              <li
                key={feature}
                className="flex items-start gap-2.5 rounded-lg bg-surface-soft px-3 py-2.5 text-[12.5px] leading-snug text-ink"
              >
                <span className="mt-0.5 grid size-5 shrink-0 place-items-center rounded-full bg-primary-soft font-mono text-[10px] text-primary">
                  {index + 1}
                </span>
                {feature}
              </li>
            ))}
            {(structured.key_features ?? []).length === 0 && (
              <li className="text-[12.5px] text-muted">No features were stated.</li>
            )}
          </ol>
        </Card>

        {/* Missing information */}
        <Card className="flex flex-col gap-3">
          <h3 className="flex items-center gap-1.5 t-sub text-ink">
            <AlertTriangle className="size-4 text-warning" /> Missing information
          </h3>
          {(structured.missing_information ?? []).length > 0 ? (
            <ul className="flex flex-col gap-1.5">
              {structured.missing_information?.map((item) => (
                <li
                  key={item}
                  className="flex items-start gap-2 rounded-lg border border-warning/20 bg-warning-soft/60 px-2.5 py-2 text-[12px] leading-snug text-ink/85"
                >
                  <span className="mt-1.5 size-1.5 shrink-0 rounded-full bg-warning" />
                  {item}
                </li>
              ))}
            </ul>
          ) : (
            <p className="flex items-center gap-2 rounded-lg border border-success/20 bg-success-soft px-2.5 py-2 text-[12px] text-success">
              <Check className="size-3.5" /> Nothing major was missing.
            </p>
          )}
        </Card>

        {/* Original text */}
        <Card className="flex flex-col gap-3 lg:col-span-3">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <h3 className="t-sub text-ink">Original description</h3>
            <div className="flex items-center gap-1.5">
              <Badge tone="neutral">v{project.version?.version_no ?? 1}</Badge>
              <Badge tone="neutral">{HELP_LEVEL_LABEL[project.help_level]}</Badge>
            </div>
          </div>
          <details className="group rounded-lg border border-line bg-surface-soft px-3.5 py-3">
            <summary className="cursor-pointer list-none text-[12.5px] font-medium text-muted transition-colors hover:text-ink">
              Show the exact words extraction worked from
            </summary>
            <p className="mt-3 whitespace-pre-wrap text-[13px] leading-relaxed text-ink/80">
              {project.version?.idea_text}
            </p>
          </details>
        </Card>
      </div>

      {/* Next phases */}
      <div className="mt-2 flex flex-col gap-3">
        <div className="flex items-center justify-between gap-3">
          <h3 className="text-[14px] font-semibold text-ink">What unlocks next</h3>
          <span className="font-mono text-[11px] text-muted">Understanding is phase 1</span>
        </div>
        <div className="grid gap-3 md:grid-cols-3">
          {NEXT_PHASES.map((phase) => {
            const body = (
              <>
                <span
                  className={
                    phase.path
                      ? "grid size-9 shrink-0 place-items-center rounded-lg bg-primary-soft text-primary"
                      : "grid size-9 shrink-0 place-items-center rounded-lg bg-surface-soft text-muted"
                  }
                >
                  {phase.path ? <ArrowUpRight className="size-4" /> : <Lock className="size-4" />}
                </span>
                <div className="flex flex-col gap-1">
                  <p className="t-label text-muted">
                    {phase.phase}
                    {phase.path ? " · live" : ""}
                  </p>
                  <p className="text-[13px] font-medium text-ink">{phase.title}</p>
                  <p className="text-[11.5px] leading-snug text-muted">{phase.body}</p>
                </div>
              </>
            );
            return phase.path ? (
              <Link
                key={phase.title}
                href={`/projects/${id}/${phase.path}`}
                className="flex items-start gap-3 rounded-xl border border-line bg-surface p-4 transition-colors hover:border-primary/40"
              >
                {body}
              </Link>
            ) : (
              <div key={phase.title} className="flex items-start gap-3 rounded-xl border border-line bg-surface p-4">
                {body}
              </div>
            );
          })}
        </div>
        <Link
          href={`/projects/${id}/understand`}
          className="mt-1 flex w-fit items-center gap-1.5 text-[12.5px] font-medium text-primary hover:underline"
        >
          Review requirements and gaps <ArrowRight className="size-3.5" />
        </Link>
      </div>
    </div>
  );
}
