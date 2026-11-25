"use client";

import { ArrowRight, ChevronRight, Sparkles } from "lucide-react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useCallback, useEffect, useState } from "react";

import { ProjectTabs } from "@/components/layout/ProjectTabs";
import { StatusBadge } from "@/components/ui/badge";
import { buttonStyles } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { api } from "@/lib/api";
import { HELP_LEVEL_LABEL } from "@/lib/idea";
import type { ProjectDetail } from "@/lib/types";
import { formatRelative } from "@/lib/utils";

export default function ProjectLayout({ children }: { children: React.ReactNode }) {
  const params = useParams<{ id: string }>();
  const id = params.id;
  const [project, setProject] = useState<ProjectDetail | null>(null);
  const [failed, setFailed] = useState(false);

  const load = useCallback(() => {
    api
      .project(id)
      .then((data) => {
        setProject(data);
        setFailed(false);
      })
      .catch(() => setFailed(true));
  }, [id]);

  useEffect(() => {
    load();
  }, [load]);

  return (
    <div className="flex flex-col gap-4">
      <Link
        href="/dashboard"
        className="flex w-fit items-center gap-1 font-mono text-[11px] uppercase tracking-[0.08em] text-muted transition-colors hover:text-ink"
      >
        Projects <ChevronRight className="size-3" />
        <span className="text-ink">Dossier</span>
      </Link>

      {project ? (
        <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-start">
          <div className="flex min-w-0 flex-col gap-1.5">
            <div className="flex flex-wrap items-center gap-1.5">
              <StatusBadge status={project.status} />
              <span className="rounded bg-surface-soft px-2 py-0.5 text-[12px] capitalize text-muted">
                {project.category}
              </span>
              <span className="rounded bg-surface-soft px-2 py-0.5 font-mono text-[11px] text-muted">
                v{project.version?.version_no ?? 1}
              </span>
              <span className="text-[12px] text-muted">
                updated {formatRelative(project.updated_at)}
              </span>
            </div>
            <h1 className="truncate t-section text-ink">{project.title}</h1>
            <p className="text-[12.5px] text-muted">
              Depth · {HELP_LEVEL_LABEL[project.help_level]}
            </p>
          </div>

          <div className="flex shrink-0 items-center gap-2">
            <Link href={`/projects/${id}/understand`} className={buttonStyles("secondary", "md")}>
              Requirements
            </Link>
            <Link href={`/projects/${id}/understand`} className={buttonStyles("primary", "md")}>
              <Sparkles className="size-4" /> Re-run extraction
            </Link>
          </div>
        </div>
      ) : (
        <div className="flex flex-col gap-2">
          <Skeleton className="h-4 w-40" />
          <Skeleton className="h-8 w-80 max-w-full" />
          {failed && (
            <p className="flex items-center gap-1.5 text-[12px] text-danger">
              This project could not be loaded. Check that the API is running.
              <ArrowRight className="size-3" />
            </p>
          )}
        </div>
      )}

      <ProjectTabs projectId={id} />

      <div className="pt-2">{children}</div>
    </div>
  );
}
