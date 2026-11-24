import {
  ArrowRight,
  Briefcase,
  Check,
  CircleHelp,
  Code,
  Cpu,
  Lock,
  Search,
  ShieldCheck,
  Sparkles,
} from "lucide-react";
import Link from "next/link";

import { Logo } from "@/components/brand/Logo";
import { buttonStyles } from "@/components/ui/button";
import { APP_NAME, DISCLAIMER, TAGLINE } from "@/lib/constants";

const steps = [
  {
    title: "Describe",
    body: "Write the idea the way you would say it out loud. No template, no jargon.",
    icon: Sparkles,
    status: "Available now",
    live: true,
  },
  {
    title: "Understand",
    body: "Category, problem, users, features, technologies and the gaps you left open.",
    icon: Search,
    status: "Available now",
    live: true,
  },
  {
    title: "Evaluate",
    body: "Six scored dimensions, each with evidence, assumptions and confidence.",
    icon: Check,
    status: "Phase 2",
    live: false,
  },
  {
    title: "Blueprint",
    body: "PRD, architecture, schema, UI/UX and a phased roadmap you can build from.",
    icon: Code,
    status: "Phase 3",
    live: false,
  },
];

const categories = [
  { title: "Business startup", icon: Briefcase, body: "Marketplaces, services and go-to-market ideas.", note: "Competition, margins, demand" },
  { title: "Software project", icon: Code, body: "Apps, tools and information systems.", note: "Feasibility, scope, stack" },
  { title: "Technology product", icon: Cpu, body: "Algorithms, hardware and infrastructure.", note: "Novelty, risk, resources" },
];

export default function LandingPage() {
  return (
    <div className="overflow-hidden bg-canvas">
      {/* ---------------- Nav ---------------- */}
      <header className="mx-auto flex w-full max-w-[1180px] items-center gap-6 px-5 py-4 sm:px-8">
        <Logo href="/" />
        <nav className="ml-4 hidden items-center gap-7 text-[13px] text-muted md:flex">
          <a className="transition-colors hover:text-ink" href="#how">How it works</a>
          <a className="transition-colors hover:text-ink" href="#categories">Categories</a>
          <a className="transition-colors hover:text-ink" href="#principles">Principles</a>
        </nav>
        <div className="ml-auto flex items-center gap-2">
          <Link href="/login" className={buttonStyles("ghost", "sm")}>
            Sign in
          </Link>
          <Link href="/register" className={buttonStyles("primary", "sm")}>
            Start free <ArrowRight className="size-3.5" />
          </Link>
        </div>
      </header>

      {/* ---------------- Hero ---------------- */}
      <section className="if-mesh border-y border-line">
        <div className="mx-auto grid w-full max-w-[1180px] items-center gap-12 px-5 py-16 sm:px-8 lg:grid-cols-[1.02fr_0.98fr] lg:py-20">
          <div className="flex max-w-xl flex-col items-start gap-6">
            <span className="inline-flex items-center gap-2 rounded-full border border-line bg-surface px-3 py-1.5 text-[11.5px] text-muted shadow-sm">
              <span className="size-1.5 rounded-full bg-success" />
              Phase 1 live — the understanding engine
            </span>

            <h1 className="text-[38px] font-semibold leading-[1.08] tracking-[-0.03em] text-ink sm:text-[50px]">
              {TAGLINE}.
            </h1>

            <p className="max-w-lg text-[15px] leading-relaxed text-muted">
              {APP_NAME} researches, evaluates and plans your business, software or technology idea
              — with evidence you can check, not a wall of confident prose.
            </p>

            <div className="flex flex-wrap items-center gap-3">
              <Link href="/register" className={buttonStyles("primary", "lg")}>
                Start a project <ArrowRight className="size-4" />
              </Link>
              <a href="#how" className={buttonStyles("secondary", "lg")}>
                See how it works
              </a>
            </div>

            <ul className="flex flex-wrap items-center gap-x-5 gap-y-2 pt-1 text-[12.5px] text-muted">
              {["Groq-powered extraction", "Evidence-first design", "Private by default"].map((item) => (
                <li key={item} className="flex items-center gap-1.5">
                  <Check className="size-3.5 text-success" />
                  {item}
                </li>
              ))}
            </ul>
          </div>

          {/* Product preview */}
          <div className="relative mx-auto w-full max-w-[470px]">
            <div className="rounded-xl border border-line bg-surface p-4 shadow-e3">
              <div className="flex items-center gap-2 border-b border-line pb-3">
                <span className="size-2 rounded-full bg-line" />
                <span className="size-2 rounded-full bg-line" />
                <span className="size-2 rounded-full bg-line" />
                <span className="mx-auto rounded-md bg-surface-soft px-2.5 py-0.5 font-mono text-[10px] text-muted">
                  ideaform.app/projects
                </span>
              </div>

              <div className="pt-4">
                <div className="flex items-center gap-1.5">
                  <span className="rounded-full bg-success-soft px-2 py-0.5 text-[11px] font-medium text-success">
                    Understood
                  </span>
                  <span className="rounded bg-surface-soft px-2 py-0.5 text-[11px] text-muted">Software</span>
                  <span className="rounded bg-surface-soft px-2 py-0.5 font-mono text-[10.5px] text-muted">v1</span>
                </div>
                <h2 className="mt-2 text-[16px] font-semibold text-ink">Tutor Match</h2>
                <p className="mt-1 text-[12px] leading-relaxed text-muted">
                  Students struggle to find affordable, trustworthy tutors for one subject.
                </p>

                <div className="mt-3 rounded-lg bg-canvas p-3">
                  <p className="t-label text-muted">Target users</p>
                  <div className="mt-1.5 flex flex-wrap gap-1">
                    {["University students", "Peer tutors"].map((chip) => (
                      <span key={chip} className="rounded-md bg-surface px-2 py-0.5 text-[11px] text-ink">
                        {chip}
                      </span>
                    ))}
                  </div>
                  <p className="t-label mt-3 text-muted">Requirements</p>
                  <div className="mt-1.5 flex flex-col gap-1">
                    {[
                      { text: "Search tutors by subject and price", tag: "Must" },
                      { text: "Tutors publish availability", tag: "Must" },
                      { text: "Secure in-app payments", tag: "Should" },
                    ].map((row) => (
                      <div key={row.text} className="flex items-center gap-2 text-[11.5px] text-ink">
                        <Check className="size-3 shrink-0 text-success" />
                        <span className="min-w-0 flex-1 truncate">{row.text}</span>
                        <span className="rounded bg-surface-soft px-1.5 py-0.5 text-[10px] text-muted">
                          {row.tag}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>

                <div className="mt-3 flex items-center justify-between text-[11px] text-muted">
                  <span className="flex items-center gap-1">
                    <CircleHelp className="size-3" /> 3 gaps flagged
                  </span>
                  <span className="font-mono">11 requirements</span>
                </div>
              </div>
            </div>

            <div className="absolute -bottom-4 -left-3 hidden items-center gap-2 rounded-lg border border-line bg-surface px-3 py-2 shadow-e2 sm:flex">
              <ShieldCheck className="size-4 text-success" />
              <span className="text-[11.5px] font-medium text-ink">Grounded in your words</span>
            </div>
          </div>
        </div>
      </section>

      {/* ---------------- How it works ---------------- */}
      <section id="how" className="mx-auto w-full max-w-[1180px] px-5 py-16 sm:px-8">
        <span className="t-label text-primary">How it works</span>
        <h2 className="t-section mt-1.5 max-w-2xl text-ink">
          From a paragraph to a plan you can defend.
        </h2>
        <p className="mt-2 max-w-xl t-body text-muted">
          Each stage builds on a versioned record of your idea, so nothing is thrown away and every
          conclusion keeps its trail.
        </p>

        <div className="mt-8 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {steps.map((step, index) => (
            <div key={step.title} className="flex flex-col gap-4 rounded-xl border border-line bg-surface p-5 shadow-sm">
              <div className="flex items-center justify-between">
                <span className="grid size-10 place-items-center rounded-lg bg-primary-soft text-primary">
                  <step.icon className="size-5" />
                </span>
                <span className="font-mono text-[11px] text-muted/70">0{index + 1}</span>
              </div>
              <div className="flex flex-col gap-1.5">
                <h3 className="text-[15px] font-semibold text-ink">{step.title}</h3>
                <p className="text-[12.5px] leading-relaxed text-muted">{step.body}</p>
              </div>
              <span
                className={
                  step.live
                    ? "mt-auto w-fit rounded-full bg-success-soft px-2.5 py-0.5 text-[11px] font-medium text-success"
                    : "mt-auto w-fit rounded-full bg-surface-soft px-2.5 py-0.5 text-[11px] font-medium text-muted"
                }
              >
                {step.status}
              </span>
            </div>
          ))}
        </div>
      </section>

      {/* ---------------- Categories ---------------- */}
      <section id="categories" className="border-y border-line bg-surface">
        <div className="mx-auto w-full max-w-[1180px] px-5 py-16 sm:px-8">
          <span className="t-label text-primary">Three kinds of idea</span>
          <h2 className="t-section mt-1.5 text-ink">Each one gets the questions it deserves.</h2>

          <div className="mt-8 grid gap-4 md:grid-cols-3">
            {categories.map((category) => (
              <div key={category.title} className="flex flex-col gap-4 rounded-xl border border-line bg-canvas p-6">
                <span className="grid size-11 place-items-center rounded-lg bg-surface text-primary shadow-sm">
                  <category.icon className="size-5" />
                </span>
                <div className="flex flex-col gap-1.5">
                  <h3 className="text-[16px] font-semibold text-ink">{category.title}</h3>
                  <p className="text-[13px] leading-relaxed text-muted">{category.body}</p>
                </div>
                <p className="mt-auto flex items-center gap-1.5 border-t border-line pt-3 text-[11.5px] text-muted">
                  <span className="size-1 rounded-full bg-accent" />
                  {category.note}
                </p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ---------------- Principles ---------------- */}
      <section id="principles" className="mx-auto w-full max-w-[1180px] px-5 py-16 sm:px-8">
        <span className="t-label text-primary">Why it feels different</span>
        <h2 className="t-section mt-1.5 max-w-2xl text-ink">
          Structure you can inspect, not a summary you have to trust.
        </h2>

        <div className="mt-8 grid gap-4 md:grid-cols-3">
          <div className="rounded-xl border border-line bg-surface p-6 shadow-sm md:col-span-2">
            <div className="flex items-center justify-between gap-3">
              <h3 className="text-[15px] font-semibold text-ink">Requirements you can argue with</h3>
              <span className="rounded-full bg-primary-soft px-2.5 py-0.5 text-[11px] font-medium text-primary">
                Editable
              </span>
            </div>
            <p className="mt-2 max-w-lg text-[13px] leading-relaxed text-muted">
              Every requirement is typed, prioritised and marked as extracted or suggested. Confirm
              the ones you mean — the record changes with you.
            </p>
            <div className="mt-4 flex flex-col gap-2">
              {[
                { text: "Tutors publish subject availability and hourly rate", tag: "Must" },
                { text: "Students book and pay for a session in one flow", tag: "Must" },
                { text: "Payouts settle weekly to a verified bank account", tag: "Should" },
              ].map((row) => (
                <div key={row.text} className="flex items-center gap-3 rounded-lg bg-canvas px-3 py-2.5">
                  <span className="grid size-4 shrink-0 place-items-center rounded-[5px] bg-success-soft">
                    <Check className="size-3 text-success" />
                  </span>
                  <span className="min-w-0 flex-1 truncate text-[12.5px] text-ink">{row.text}</span>
                  <span className="rounded bg-surface px-1.5 py-0.5 text-[10.5px] text-muted">{row.tag}</span>
                </div>
              ))}
            </div>
          </div>

          <div className="flex flex-col gap-3 rounded-xl border border-line bg-surface p-6 shadow-sm">
            <h3 className="text-[15px] font-semibold text-ink">Gaps surfaced, not invented</h3>
            <p className="text-[13px] leading-relaxed text-muted">
              Anything your idea does not state is listed as missing information instead of being
              filled in with plausible fiction.
            </p>
            <ul className="mt-auto flex flex-col gap-2 pt-2">
              {["Pricing model", "Launch region", "Regulatory checks"].map((item) => (
                <li
                  key={item}
                  className="flex items-center gap-2 rounded-lg border border-warning/20 bg-warning-soft/70 px-2.5 py-2 text-[12px] text-ink/80"
                >
                  <span className="size-1.5 rounded-full bg-warning" />
                  {item}
                </li>
              ))}
            </ul>
          </div>

          <div className="flex flex-col gap-3 rounded-xl border border-line bg-surface p-6 shadow-sm">
            <span className="grid size-10 place-items-center rounded-lg bg-primary-soft text-primary">
              <Lock className="size-5" />
            </span>
            <h3 className="text-[15px] font-semibold text-ink">Private by default</h3>
            <p className="text-[13px] leading-relaxed text-muted">
              Your ideas live in your account. Documents and project knowledge never join a shared
              public corpus.
            </p>
          </div>

          <div className="flex flex-col gap-4 rounded-xl border border-line bg-surface p-6 shadow-sm md:col-span-2">
            <h3 className="text-[15px] font-semibold text-ink">One idea, one versioned record</h3>
            <p className="max-w-lg text-[13px] leading-relaxed text-muted">
              Understanding is stored against a version, so every later score and blueprint can
              point back to exactly what was known when it was made.
            </p>
            <div className="flex flex-wrap gap-2">
              {["Problem", "Target users", "Key features", "Technologies", "Missing info", "Requirements"].map((chip) => (
                <span
                  key={chip}
                  className="rounded-full border border-line bg-canvas px-3 py-1 text-[11.5px] text-muted"
                >
                  {chip}
                </span>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* ---------------- CTA ---------------- */}
      <section className="mx-auto w-full max-w-[1180px] px-5 pb-16 sm:px-8">
        <div className="relative overflow-hidden rounded-xl border border-line bg-primary px-6 py-14 text-center text-white sm:px-10">
          <div className="pointer-events-none absolute inset-0 opacity-40 if-grid" aria-hidden="true" />
          <div className="relative">
            <h2 className="text-[28px] font-semibold tracking-[-0.02em] sm:text-[34px]">
              Your idea deserves a real answer.
            </h2>
            <p className="mx-auto mt-2 max-w-md text-[13.5px] leading-relaxed text-white/75">
              Describe it once. Get the structure, the gaps and the requirements — free while{" "}
              {APP_NAME} is in development.
            </p>
            <div className="mt-6 flex flex-wrap items-center justify-center gap-3">
              <Link
                href="/register"
                className="inline-flex h-11 items-center gap-2 rounded-lg bg-white px-5 text-[14px] font-medium text-primary transition-colors hover:bg-white/90"
              >
                Start your project <ArrowRight className="size-4" />
              </Link>
              <Link
                href="/login"
                className="inline-flex h-11 items-center rounded-lg border border-white/25 px-5 text-[14px] font-medium text-white transition-colors hover:bg-white/10"
              >
                I already have an account
              </Link>
            </div>
          </div>
        </div>
      </section>

      {/* ---------------- Footer ---------------- */}
      <footer className="border-t border-line bg-surface">
        <div className="mx-auto flex w-full max-w-[1180px] flex-col gap-6 px-5 py-10 sm:px-8 md:flex-row md:items-start md:justify-between">
          <div className="flex max-w-sm flex-col gap-3">
            <Logo href="/" />
            <p className="text-[12.5px] leading-relaxed text-muted">
              {TAGLINE}. An evidence-first idea analysis workspace.
            </p>
          </div>
          <div className="grid grid-cols-2 gap-x-10 gap-y-2 text-[12.5px] text-muted sm:grid-cols-3">
            <a className="transition-colors hover:text-ink" href="#how">How it works</a>
            <a className="transition-colors hover:text-ink" href="#categories">Categories</a>
            <a className="transition-colors hover:text-ink" href="#principles">Principles</a>
            <Link className="transition-colors hover:text-ink" href="/login">Sign in</Link>
            <Link className="transition-colors hover:text-ink" href="/register">Create account</Link>
          </div>
        </div>
        <div className="mx-auto w-full max-w-[1180px] px-5 pb-8 sm:px-8">
          <p className="rounded-lg border border-line bg-canvas px-4 py-3 text-[11.5px] leading-relaxed text-muted">
            {DISCLAIMER} Phase 1 covers understanding only; evaluation, research and blueprint
            screens are marked as later phases.
          </p>
          <p className="mt-4 text-[11px] text-muted/70">
            © {new Date().getFullYear()} {APP_NAME}. All rights reserved.
          </p>
        </div>
      </footer>
    </div>
  );
}
