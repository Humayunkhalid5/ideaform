import type { ComponentProps, ReactNode } from "react";

import { cn } from "@/lib/utils";

export const inputClass =
  "w-full rounded-lg border border-line bg-surface px-3.5 py-2.5 text-[14px] text-ink placeholder:text-muted/70 transition-colors outline-none focus:border-primary/60 focus:ring-4 focus:ring-primary/10 disabled:cursor-not-allowed disabled:opacity-60";

export function Label({ className, ...props }: ComponentProps<"label">) {
  return <label className={cn("text-[14px] font-medium text-ink", className)} {...props} />;
}

export function Input({ className, ...props }: ComponentProps<"input">) {
  return <input className={cn(inputClass, "h-11", className)} {...props} />;
}

export function Textarea({ className, ...props }: ComponentProps<"textarea">) {
  return <textarea className={cn(inputClass, "resize-y leading-relaxed", className)} {...props} />;
}

export function Select({ className, ...props }: ComponentProps<"select">) {
  return (
    <select
      className={cn(inputClass, "cursor-pointer appearance-none pr-9", className)}
      {...props}
    />
  );
}

export function Field({
  label,
  htmlFor,
  hint,
  error,
  children,
  className,
}: {
  label: string;
  htmlFor?: string;
  hint?: string;
  error?: string | null;
  children: ReactNode;
  className?: string;
}) {
  return (
    <div className={cn("flex flex-col gap-1.5", className)}>
      <div className="flex items-baseline justify-between gap-3">
        <Label htmlFor={htmlFor}>{label}</Label>
        {hint && <span className="text-[12px] text-muted">{hint}</span>}
      </div>
      {children}
      {error && <p className="text-[12px] font-medium text-danger">{error}</p>}
    </div>
  );
}
