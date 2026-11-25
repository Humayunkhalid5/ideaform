import { Check, Loader2, X } from "lucide-react";

import { cn } from "@/lib/utils";

export function PipelineTimeline({
  steps,
  current,
  failed = false,
}: {
  steps: { label: string; detail: string }[];
  current: number;
  failed?: boolean;
}) {
  return (
    <ol className="flex flex-col gap-3 sm:flex-row sm:gap-2">
      {steps.map((step, index) => {
        const done = index < current;
        const active = index === current && !failed;
        const isFailed = index === current && failed;
        return (
          <li key={step.label} className="flex flex-1 gap-3 sm:flex-col sm:gap-2">
            <div className="flex items-center gap-2 sm:w-full">
              <span
                className={cn(
                  "grid size-8 shrink-0 place-items-center rounded-full border text-[11px] font-semibold transition",
                  done && "border-if-success/40 bg-if-success/10 text-if-success",
                  active && "border-transparent bg-primary text-white shadow-[0_0_0_4px_rgba(79,70,229,0.14)]",
                  isFailed && "border-if-danger/40 bg-if-danger/10 text-if-danger",
                  !done && !active && !isFailed && "border-if-border bg-if-surface text-if-muted",
                )}
              >
                {done ? (
                  <Check className="size-4" />
                ) : active ? (
                  <Loader2 className="size-4 animate-spin" />
                ) : isFailed ? (
                  <X className="size-4" />
                ) : (
                  index + 1
                )}
              </span>
              <span
                className={cn(
                  "hidden h-px flex-1 sm:block",
                  done ? "bg-if-success/40" : "bg-if-border",
                )}
              />
            </div>
            <div className="min-w-0 sm:pt-1">
              <p
                className={cn(
                  "text-[13px] font-medium",
                  active && "text-if-text",
                  done && "text-if-success",
                  isFailed && "text-if-danger",
                  !done && !active && !isFailed && "text-if-muted",
                )}
              >
                {step.label}
              </p>
              <p className="text-[11.5px] leading-snug text-if-muted">{step.detail}</p>
            </div>
          </li>
        );
      })}
    </ol>
  );
}
