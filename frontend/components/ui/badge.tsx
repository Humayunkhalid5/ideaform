import type { ComponentProps } from "react";

import { STATUS_LABEL } from "@/lib/idea";
import type { ProjectStatus } from "@/lib/types";
import { cn } from "@/lib/utils";

type Tone = "neutral" | "primary" | "success" | "warning" | "danger" | "accent" | "info";

const tones: Record<Tone, string> = {
  neutral: "bg-surface-soft text-muted",
  primary: "bg-primary-soft text-primary",
  success: "bg-success-soft text-success",
  warning: "bg-warning-soft text-warning",
  danger: "bg-danger-soft text-danger",
  accent: "bg-accent-soft text-accent",
  info: "bg-info-soft text-info",
};

export function Badge({
  tone = "neutral",
  className,
  ...props
}: ComponentProps<"span"> & { tone?: Tone }) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full px-2.5 py-[3px] text-[12px] font-medium whitespace-nowrap",
        tones[tone],
        className,
      )}
      {...props}
    />
  );
}

const statusTone: Record<ProjectStatus, Tone> = {
  draft: "neutral",
  analysing: "accent",
  ready: "success",
  failed: "danger",
  archived: "neutral",
};

export function StatusBadge({ status, className }: { status: ProjectStatus; className?: string }) {
  return (
    <Badge tone={statusTone[status]} className={className}>
      <span
        className={cn(
          "size-1.5 rounded-full bg-current",
          status === "analysing" && "animate-pulse",
        )}
      />
      {STATUS_LABEL[status]}
    </Badge>
  );
}
