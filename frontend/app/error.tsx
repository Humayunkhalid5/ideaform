"use client";

import { AlertTriangle } from "lucide-react";
import { useEffect } from "react";

import { Logo } from "@/components/brand/Logo";
import { Button } from "@/components/ui/button";

export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error(error);
  }, [error]);

  return (
    <main className="relative grid min-h-screen place-items-center bg-canvas px-5 py-16">
      <Logo href="/" className="absolute left-5 top-5 sm:left-8" size="size-10" />
      <div className="flex max-w-md flex-col items-center gap-5 text-center">
        <span className="grid size-12 place-items-center rounded-xl bg-danger-soft text-danger">
          <AlertTriangle className="size-6" />
        </span>
        <div className="flex flex-col gap-2">
          <p className="font-mono text-[11px] uppercase tracking-[0.14em] text-danger">
            Something went wrong
          </p>
          <h1 className="text-[clamp(1.75rem,3vw,2.4rem)] font-semibold leading-[1.08] tracking-[-0.035em]"><span className="if-heading">That screen failed to render.</span></h1>
          <p className="t-body text-muted">
            Your data is untouched. Retry the screen, or head back to the dashboard.
          </p>
        </div>
        <div className="flex flex-wrap items-center justify-center gap-3">
          <Button onClick={reset}>Try again</Button>
          <a href="/dashboard" className="text-[12.5px] text-muted hover:text-ink">
            Go to dashboard
          </a>
        </div>
      </div>
    </main>
  );
}
