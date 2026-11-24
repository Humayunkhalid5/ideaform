import { FolderOpen } from "lucide-react";
import type { ReactNode } from "react";

import { cn } from "@/lib/utils";

export function EmptyState({
  title,
  body,
  action,
  className,
}: {
  title: string;
  body: string;
  action?: ReactNode;
  className?: string;
}) {
  return (
    <div
      className={cn(
        "flex flex-col items-center gap-4 rounded-xl border border-dashed border-line bg-surface px-6 py-12 text-center",
        className,
      )}
    >
      <span className="grid size-12 place-items-center rounded-full bg-surface-soft text-muted">
        <FolderOpen className="size-5" />
      </span>
      <div className="flex max-w-sm flex-col gap-1.5">
        <h3 className="t-title text-ink">{title}</h3>
        <p className="t-body text-muted">{body}</p>
      </div>
      {action}
    </div>
  );
}
