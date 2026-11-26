import { ArrowRight, Briefcase, Code, Cpu } from "lucide-react";
import Link from "next/link";

import { Logo } from "@/components/brand/Logo";
import { HeroScene } from "@/components/landing/HeroScene";
import { Reveal, TiltSurface } from "@/components/landing/Reveal";
import { StagesScene, type Stage } from "@/components/landing/StagesScene";
import { buttonStyles } from "@/components/ui/button";
import { ThemeToggle } from "@/components/ui/theme-toggle";
import { APP_NAME, DISCLAIMER, TAGLINE } from "@/lib/constants";

import "./landing.css";

const stages: Stage[] = [
  {
    title: "Describe",
    body: "Write the idea the way you would say it out loud. No template, no jargon.",
    status: "Live",
    live: true,
  },
  {
    title: "Understand",
    body: "Category, problem, users, features and typed requirements, taken from your own words. Gaps are flagged, never filled in.",
    status: "Live",
    live: true,
  },
  {
    title: "Research",
    body: "Market and competitor sources gathered, ranked and stored, so every later claim can point at a passage.",
    status: "Live",
    live: true,
  },
  {
    title: "Evaluate",
    body: "Six scored dimensions with evidence, confidence, risks and a devil's advocate. Accept an improvement and see exactly what moved.",
    status: "Live",
    live: true,
  },
  {
    title: "Blueprint",
    body: "PRD, architecture, schema, UI/UX and a phased roadmap you can build from.",
    status: "Next phase",
    live: false,
  },
];

// Illustrative output only; labelled as an example on the page.
const exampleDimensions = [
  { label: "Technical feasibility", score: 72 },
  { label: "Market opportunity", score: 64 },
  { label: "Competition", score: 45 },
  { label: "Business model", score: 58 },
  { label: "Resource requirements", score: 66 },
  { label: "Execution complexity", score: 52 },
];

const categories = [
  { title: "Business", icon: Briefcase, body: "Marketplaces, services and go-to-market ideas.", note: "Competition, margins, demand" },
  { title: "Software", icon: Code, body: "Apps, tools and information systems.", note: "Feasibility, scope, stack" },
  { title: "Technology", icon: Cpu, body: "Algorithms, hardware and infrastructure.", note: "Novelty, risk, resources" },
];

const principles = [
  {
    title: "Evidence or a label",
    body: "Every claim is a verified fact with a source, an assumption, or an AI suggestion. You always know which.",
  },
  {
    title: "Gaps, not fiction",
    body: "What your idea does not say is listed as missing information instead of being filled in with plausible prose.",
  },
  {
    title: "Versions you can compare",
    body: "Each improvement creates a new version. Scores are re-run and every change states its reason.",
  },
];

export default function LandingPage() {
  return (
    <div className="bg-canvas">
      {/* ---------------- Nav ---------------- */}
      <header className="fixed inset-x-0 top-0 z-50 bg-canvas/70 backdrop-blur-md">
        <div className="mx-auto flex w-full max-w-[1180px] items-center gap-6 px-5 py-4 sm:px-8">
          <Logo href="/" size="size-10" />
          <nav className="ml-2 hidden items-center gap-7 text-[13px] text-muted md:flex">
            <a className="transition-colors duration-150 hover:text-ink" href="#stages">Stages</a>
            <a className="transition-colors duration-150 hover:text-ink" href="#evaluation">Evaluation</a>
            <a className="transition-colors duration-150 hover:text-ink" href="#principles">Principles</a>
          </nav>
          <div className="ml-auto flex items-center gap-2">
            <ThemeToggle />
            <Link href="/login" className={buttonStyles("ghost", "sm")}>
              Sign in
            </Link>
          </div>
        </div>
      </header>

      <main>
        <HeroScene />
        <StagesScene stages={stages} />

        {/* ---------------- Evaluation preview ---------------- */}
        <section id="evaluation" className="border-t border-line">
          <div className="mx-auto grid w-full max-w-[1180px] items-center gap-14 px-5 py-28 sm:px-8 lg:grid-cols-[0.9fr_1.1fr]">
            <Reveal className="flex flex-col gap-5">
              <p className="t-label text-primary">Evaluation</p>
              <h2 className="text-[clamp(2rem,4.2vw,3.25rem)] font-semibold leading-[1.04] tracking-[-0.035em] text-ink">
                Scores that show their working.
              </h2>
              <p className="max-w-[44ch] t-body text-muted">
                Each dimension carries a confidence level, the passages it relied on, and the
                assumptions it could not verify. Low evidence lowers confidence instead of
                inflating certainty.
              </p>
              <Link href="/register" className={buttonStyles("secondary", "md", "w-fit")}>
                Evaluate an idea <ArrowRight className="size-4" />
              </Link>
            </Reveal>

            <Reveal delay={120}>
              <TiltSurface>
                <div className="if-card p-6 shadow-e3">
                  <div className="flex items-start justify-between gap-4">
                    <div>
                      <p className="t-label text-muted">Example output</p>
                      <p className="mt-1 t-title text-ink">Tutor Match · v2</p>
                    </div>
                    <div className="text-right">
                      <p className="font-display text-[40px] font-semibold leading-none tabular text-ink">60</p>
                      <p className="mt-1 font-mono text-[11px] text-success">+4 vs v1</p>
                    </div>
                  </div>
                  <ul className="mt-6 flex flex-col gap-3.5">
                    {exampleDimensions.map((dim) => (
                      <li key={dim.label} className="grid grid-cols-[1fr_auto] items-center gap-x-4 gap-y-1.5">
                        <span className="text-[12.5px] text-ink">{dim.label}</span>
                        <span className="font-mono text-[12px] tabular text-muted">{dim.score}</span>
                        <span className="col-span-2 h-1.5 overflow-hidden rounded-full bg-surface-soft">
                          <span
                            className="grow-x block h-full rounded-full bg-gradient-to-r from-brand-copper to-brand-teal"
                            style={{ "--v": dim.score / 100 } as React.CSSProperties}
                          />
                        </span>
                      </li>
                    ))}
                  </ul>
                  <div className="mt-6 flex flex-wrap gap-2 border-t border-line pt-4 text-[11px]">
                    <span className="rounded-full bg-success-soft px-2.5 py-0.5 font-medium text-success">Verified fact · E3</span>
                    <span className="rounded-full bg-warning-soft px-2.5 py-0.5 font-medium text-warning">Assumption</span>
                    <span className="rounded-full bg-info-soft px-2.5 py-0.5 font-medium text-info">AI suggestion</span>
                  </div>
                </div>
              </TiltSurface>
            </Reveal>
          </div>
        </section>

        {/* ---------------- Categories ---------------- */}
        <section className="border-t border-line">
          <div className="mx-auto w-full max-w-[1180px] px-5 py-24 sm:px-8">
            <Reveal>
              <p className="t-label text-primary">Three kinds of idea</p>
              <h2 className="mt-1.5 max-w-[24ch] text-[clamp(1.75rem,3.4vw,2.6rem)] font-semibold leading-[1.08] tracking-[-0.03em] text-ink">
                Each one gets the questions it deserves.
              </h2>
            </Reveal>
            <Reveal delay={100} className="mt-12 grid border-t border-line md:grid-cols-3">
              {categories.map((category, index) => (
                <div
                  key={category.title}
                  className="group flex flex-col gap-4 border-b border-line py-8 md:border-b-0 md:border-l md:px-8 md:first:border-l-0 md:first:pl-0"
                >
                  <div className="flex items-center justify-between">
                    <category.icon className="size-5 text-muted transition-colors duration-150 group-hover:text-primary" />
                    <span className="font-mono text-[11px] text-muted/70">0{index + 1}</span>
                  </div>
                  <h3 className="text-[clamp(1.75rem,3vw,2.25rem)] font-semibold tracking-[-0.035em] text-ink">
                    {category.title}
                  </h3>
                  <p className="t-body text-muted">{category.body}</p>
                  <p className="mt-auto font-mono text-[11.5px] text-muted">{category.note}</p>
                </div>
              ))}
            </Reveal>
          </div>
        </section>

        {/* ---------------- Principles ---------------- */}
        <section id="principles" className="border-t border-line bg-surface">
          <div className="mx-auto grid w-full max-w-[1180px] gap-12 px-5 py-24 sm:px-8 lg:grid-cols-[0.8fr_1.2fr]">
            <Reveal>
              <p className="t-label text-primary">Why it feels different</p>
              <h2 className="mt-1.5 max-w-[16ch] text-[clamp(1.75rem,3.4vw,2.6rem)] font-semibold leading-[1.08] tracking-[-0.03em] text-ink">
                Structure you can inspect, not prose you have to trust.
              </h2>
            </Reveal>
            <Reveal delay={100}>
              <ol className="flex flex-col">
                {principles.map((item, index) => (
                  <li key={item.title} className="grid grid-cols-[3rem_1fr] gap-4 border-t border-line py-6 last:border-b">
                    <span className="font-mono text-[12px] text-muted">0{index + 1}</span>
                    <div className="flex flex-col gap-1.5">
                      <h3 className="t-title text-ink">{item.title}</h3>
                      <p className="max-w-[56ch] t-body text-muted">{item.body}</p>
                    </div>
                  </li>
                ))}
              </ol>
            </Reveal>
          </div>
        </section>

        {/* ---------------- CTA ---------------- */}
        <section className="border-t border-line">
          <Reveal className="mx-auto flex w-full max-w-[1180px] flex-col items-center px-5 py-28 text-center sm:px-8">
            <h2 className="max-w-[18ch] text-[clamp(2.25rem,6vw,4.75rem)] font-semibold leading-[1] tracking-[-0.045em] text-ink">
              Your idea deserves a real answer.
            </h2>
            <p className="mt-5 max-w-[44ch] t-body text-muted">
              Describe it once. Get the structure, the evidence and the scores, free while {APP_NAME} is in
              development.
            </p>
            <div className="mt-8 flex flex-wrap items-center justify-center gap-3">
              <Link href="/register" className={buttonStyles("primary", "lg")}>
                Start your project <ArrowRight className="size-4" />
              </Link>
              <Link href="/login" className={buttonStyles("secondary", "lg")}>
                I already have an account
              </Link>
            </div>
          </Reveal>
        </section>
      </main>

      {/* ---------------- Footer ---------------- */}
      <footer className="overflow-hidden border-t border-line bg-surface">
        <div className="mx-auto flex w-full max-w-[1180px] flex-col gap-6 px-5 pt-12 sm:px-8 md:flex-row md:items-start md:justify-between">
          <div className="flex max-w-sm flex-col gap-3">
            <Logo href="/" />
            <p className="text-[12.5px] leading-relaxed text-muted">
              {TAGLINE}. An evidence-first idea analysis workspace.
            </p>
          </div>
          <div className="grid grid-cols-2 gap-x-10 gap-y-2 text-[12.5px] text-muted sm:grid-cols-3">
            <a className="transition-colors duration-150 hover:text-ink" href="#stages">Stages</a>
            <a className="transition-colors duration-150 hover:text-ink" href="#evaluation">Evaluation</a>
            <a className="transition-colors duration-150 hover:text-ink" href="#principles">Principles</a>
            <Link className="transition-colors duration-150 hover:text-ink" href="/login">Sign in</Link>
            <Link className="transition-colors duration-150 hover:text-ink" href="/register">Create account</Link>
          </div>
        </div>
        <div className="mx-auto w-full max-w-[1180px] px-5 sm:px-8">
          <p className="mt-10 rounded-lg border border-line bg-canvas px-4 py-3 text-[11.5px] leading-relaxed text-muted">
            {DISCLAIMER} Blueprint and document generation are the next phase.
          </p>
        </div>
        <p
          aria-hidden="true"
          className="outline-word mt-6 select-none text-center text-[19vw] font-extrabold leading-[0.78] tracking-[-0.06em]"
        >
          {APP_NAME.toUpperCase()}
        </p>
        <p className="mx-auto w-full max-w-[1180px] px-5 pb-8 pt-4 text-[11px] text-muted/70 sm:px-8">
          © {new Date().getFullYear()} {APP_NAME}. All rights reserved.
        </p>
      </footer>
    </div>
  );
}
