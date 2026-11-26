import { Compass } from "lucide-react";
import Link from "next/link";

import { Logo } from "@/components/brand/Logo";
import { buttonStyles } from "@/components/ui/button";

export default function NotFound() {
  return (
    <main className="relative grid min-h-screen place-items-center overflow-hidden bg-canvas px-5 py-16">
      <p aria-hidden="true" className="if-outline-display pointer-events-none absolute inset-x-0 top-1/2 -translate-y-1/2 text-center text-[clamp(10rem,34vw,30rem)]">
        {"404".split("").map((ch, i) => (
          <span key={i} style={{ "--i": i } as React.CSSProperties}>
            {ch}
          </span>
        ))}
      </p>
      <Logo href="/" className="absolute left-5 top-5 sm:left-8" size="size-10" />
      <div className="relative z-10 flex max-w-md flex-col items-center gap-5 text-center">
        <span className="grid size-12 place-items-center rounded-xl bg-primary-soft text-primary">
          <Compass className="size-6" />
        </span>
        <div className="flex flex-col gap-2">
          <p className="font-mono text-[11px] uppercase tracking-[0.14em] text-muted">404 · not found</p>
          <h1 className="text-[clamp(1.75rem,3vw,2.4rem)] font-semibold leading-[1.08] tracking-[-0.035em]"><span className="if-heading">This page does not exist.</span></h1>
          <p className="t-body text-muted">
            The route was moved or never existed. Your projects are untouched.
          </p>
        </div>
        <div className="flex flex-wrap items-center justify-center gap-2">
          <Link href="/dashboard" className={buttonStyles("primary", "md")}>
            Go to dashboard
          </Link>
          <Link href="/" className={buttonStyles("secondary", "md")}>
            Back to landing
          </Link>
        </div>
      </div>
    </main>
  );
}
