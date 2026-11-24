import type { ComponentProps } from "react";

import { cn } from "@/lib/utils";

export function Card({ className, ...props }: ComponentProps<"div">) {
  return <div className={cn("if-card p-5", className)} {...props} />;
}

export function GlassCard({ className, ...props }: ComponentProps<"div">) {
  return <div className={cn("if-card p-5", className)} {...props} />;
}

export function SectionHeading({
  eyebrow,
  title,
  body,
  className,
}: {
  eyebrow?: string;
  title: string;
  body?: string;
  className?: string;
}) {
  return (
    <div className={cn("flex flex-col gap-1.5", className)}>
      {eyebrow && <span className="t-label text-primary">{eyebrow}</span>}
      <h2 className="t-section text-ink">{title}</h2>
      {body && <p className="max-w-2xl t-body text-muted">{body}</p>}
    </div>
  );
}
