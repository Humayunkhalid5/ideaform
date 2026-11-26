"use client";

import {
  AlertTriangle,
  ArrowLeft,
  ArrowRight,
  Briefcase,
  Check,
  CheckCircle2,
  CircleHelp,
  Code,
  Cpu,
  Loader2,
  Lock,
  Plus,
  Sparkles,
} from "lucide-react";
import { useRouter } from "next/navigation";
import { useMemo, useState } from "react";

import { Button } from "@/components/ui/button";
import { api } from "@/lib/api";
import { CATEGORIES, HELP_LEVELS, HELP_LEVEL_LABEL } from "@/lib/idea";
import type { Category, HelpLevel } from "@/lib/types";
import { cn } from "@/lib/utils";

const STEPS = ["Category", "Describe idea", "Help level", "Review & start"];

const CATEGORY_ICON: Record<Category, typeof Code> = {
  business: Briefcase,
  software: Code,
  technology: Cpu,
};

const IDEA_HINTS = [
  { label: "The problem", text: "The problem it solves is " },
  { label: "Who it is for", text: "It is for " },
  { label: "How it works", text: "It works by " },
  { label: "Today's alternative", text: "Today people solve this by " },
];

const MAX_IDEA = 2000;

type Check_ = { label: string; hint: string; test: RegExp };

const READINESS_CHECKS: Check_[] = [
  {
    label: "Primary users named",
    hint: "e.g. undergraduate students, independent tutors",
    test: /(students?|users?|customers?|teams?|people|parents|teachers|smb|businesses|founders)/i,
  },
  {
    label: "Core problem stated",
    hint: "e.g. agency fees, opaque scheduling",
    test: /(problem|because|struggle|pain|costly|expensive|slow|manual|hard|difficult)/i,
  },
  {
    label: "Current alternative described",
    hint: "e.g. fragmented WhatsApp groups, notice boards",
    test: /(today|currently|instead|alternative|rely on|existing|manual)/i,
  },
  {
    label: "Solution mechanism explained",
    hint: "e.g. matching engine, sensor probe, marketplace",
    test: /(app|platform|api|service|marketplace|device|model|sensor|tool|engine|dashboard)/i,
  },
];

export default function NewProjectPage() {
  const router = useRouter();
  const [step, setStep] = useState(0);
  const [category, setCategory] = useState<Category | null>(null);
  const [title, setTitle] = useState("");
  const [idea, setIdea] = useState("");
  const [helpLevel, setHelpLevel] = useState<HelpLevel>("everything");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const checks = useMemo(
    () => READINESS_CHECKS.map((check) => ({ ...check, passed: check.test.test(idea) })),
    [idea],
  );

  const passed = checks.filter((check) => check.passed).length;
  const density = Math.round(
    Math.min(100, (idea.trim().length / MAX_IDEA) * 55 + (passed / checks.length) * 45),
  );
  const readinessLabel =
    density >= 75 ? "High potential" : density >= 45 ? "Getting there" : "Needs detail";

  const canContinue =
    step === 0
      ? category !== null
      : step === 1
        ? title.trim().length >= 3 && idea.trim().length >= 20
        : true;

  function appendHint(text: string) {
    setIdea((current) => {
      const next = current ? `${current.trimEnd()} ${text}` : text;
      return next.slice(0, MAX_IDEA);
    });
  }

  function next() {
    if (!canContinue) return;
    setStep((value) => Math.min(STEPS.length - 1, value + 1));
  }

  async function submit() {
    if (!category) return;
    setBusy(true);
    setError(null);
    try {
      const project = await api.createProject({
        title: title.trim(),
        idea_text: idea.trim(),
        category,
        help_level: helpLevel,
      });
      try {
        const run = await api.understand(project.id);
        if (run.status === "queued") {
          router.push(`/projects/${project.id}/run?run=${run.run_id}`);
          return;
        }
      } catch {
        /* extraction can be retried from the project page */
      }
      router.push(`/projects/${project.id}/understand`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not create the project.");
      setBusy(false);
    }
  }

  return (
    <div className="mx-auto flex w-full max-w-[1120px] flex-col gap-6">
      {/* ---------------- Stepper ---------------- */}
      <section className="rounded-xl border border-line bg-surface px-4 py-3 shadow-sm">
        <div className="flex items-center justify-between gap-4">
          <nav aria-label="Wizard steps" className="no-scrollbar flex items-center gap-2 overflow-x-auto">
            {STEPS.map((label, index) => {
              const done = index < step;
              const active = index === step;
              return (
                <div key={label} className="flex items-center gap-2">
                  <div
                    aria-current={active ? "step" : undefined}
                    className={cn(
                      "flex items-center gap-1.5 whitespace-nowrap rounded-full py-1 pl-1 pr-2.5 text-[13px] transition-colors",
                      active && "bg-primary-soft font-semibold text-primary shadow-sm",
                      done && "font-medium text-ink",
                      !active && !done && "text-muted/70",
                    )}
                  >
                    <span
                      className={cn(
                        "grid size-6 place-items-center rounded-full font-mono text-[11px]",
                        active && "bg-primary text-white",
                        done && "bg-success-soft text-success",
                        !active && !done && "bg-surface-soft text-muted",
                      )}
                    >
                      {done ? <Check className="size-3.5" /> : index + 1}
                    </span>
                    {label}
                    {active && <span className="ml-0.5 size-1.5 animate-pulse rounded-full bg-primary" />}
                  </div>
                  {index < STEPS.length - 1 && (
                    <span className="hidden h-0.5 w-8 rounded-full bg-line sm:block" />
                  )}
                </div>
              );
            })}
          </nav>
          <div className="hidden items-center gap-1.5 font-mono text-[11.5px] text-muted lg:flex">
            <span className="size-1.5 rounded-full bg-success" />
            <span>Steps are saved on create</span>
          </div>
        </div>
      </section>

      <div className="grid grid-cols-1 items-start gap-6 lg:grid-cols-12">
        {/* ---------------- Main column ---------------- */}
        <div className="flex flex-col gap-5 lg:col-span-8">
          <div>
            <div className="mb-1 flex items-center gap-2">
              <span className="t-label font-semibold text-primary">
                Step {String(step + 1).padStart(2, "0")} / 04
              </span>
              <span className="text-muted">•</span>
              <span className="text-[12px] font-medium text-accent">
                {step === 0
                  ? "Category guides the extraction"
                  : step === 1
                    ? "Semantic parser ready"
                    : step === 2
                      ? "Depth is stored with the project"
                      : "Review before extraction runs"}
              </span>
            </div>
            <h1 className="t-section text-ink">
              {step === 0
                ? "What do you want to build?"
                : step === 1
                  ? "Describe your idea"
                  : step === 2
                    ? "What should IdeaForm help with?"
                    : "Review and start"}
            </h1>
            <p className="t-body mt-1 max-w-2xl text-muted">
              {step === 0
                ? "The category decides which questions matter. You can change it later."
                : step === 1
                  ? "Write it the way you would say it out loud. IdeaForm only records what you state and lists the rest as missing information."
                  : step === 2
                    ? "Depth is saved with the project so later phases know how far to take it."
                    : "Nothing is invented. Extraction reads this version of the idea text."}
            </p>
          </div>

          <div className="flex flex-col gap-5 rounded-xl border border-line bg-surface p-5 shadow-sm sm:p-6">
            {/* ---- Step 1: category ---- */}
            {step === 0 && (
              <div
                role="radiogroup"
                aria-label="Idea category"
                className="grid gap-3 sm:grid-cols-3"
              >
                {CATEGORIES.map((item) => {
                  const Icon = CATEGORY_ICON[item.id];
                  const selected = category === item.id;
                  return (
                    <button
                      key={item.id}
                      type="button"
                      role="radio"
                      aria-checked={selected}
                      onClick={() => setCategory(item.id)}
                      className={cn(
                        "flex flex-col gap-3 rounded-xl border p-4 text-left transition-colors",
                        selected
                          ? "border-primary bg-primary-soft/60 ring-1 ring-primary/20"
                          : "border-line hover:border-primary/30 hover:bg-surface-soft",
                      )}
                    >
                      <div className="flex items-center justify-between">
                        <span
                          className={cn(
                            "grid size-9 place-items-center rounded-lg",
                            selected ? "bg-primary text-white" : "bg-surface-soft text-primary",
                          )}
                        >
                          <Icon className="size-4.5" />
                        </span>
                        {selected && <CheckCircle2 className="size-4 text-primary" />}
                      </div>
                      <div>
                        <p className="text-[14.5px] font-semibold text-ink">{item.title}</p>
                        <p className="mt-0.5 text-[12.5px] leading-snug text-muted">{item.blurb}</p>
                      </div>
                      <ul className="mt-1 flex flex-col gap-1">
                        {item.bullets.map((bullet) => (
                          <li key={bullet} className="flex items-center gap-1.5 text-[11.5px] text-muted">
                            <span className="size-1 rounded-full bg-current" />
                            {bullet}
                          </li>
                        ))}
                      </ul>
                    </button>
                  );
                })}
              </div>
            )}

            {/* ---- Step 2: describe ---- */}
            {step === 1 && (
              <div className="flex flex-col gap-5">
                <div className="flex flex-col gap-1.5">
                  <label
                    htmlFor="project-title"
                    className="flex items-center justify-between text-[14px] font-medium text-ink"
                  >
                    <span>
                      Project title <span className="text-danger">*</span>
                    </span>
                    <span className="text-[12px] font-normal text-muted">
                      Public identifier in your workspace
                    </span>
                  </label>
                  <div className="relative flex items-center">
                    <input
                      id="project-title"
                      value={title}
                      maxLength={200}
                      onChange={(event) => setTitle(event.target.value)}
                      placeholder="e.g. Tutor Match — campus tutoring marketplace"
                      className="h-11 w-full rounded-lg border border-line bg-surface px-3.5 pr-10 text-[14px] text-ink outline-none transition-colors placeholder:text-muted/70 focus:border-primary/60 focus:ring-4 focus:ring-primary/10"
                    />
                    {title.trim().length >= 3 && (
                      <CheckCircle2 className="absolute right-3 size-4 text-success" />
                    )}
                  </div>
                </div>

                <div className="flex flex-col gap-1.5">
                  <div className="flex items-center justify-between">
                    <label htmlFor="idea" className="text-[14px] font-medium text-ink">
                      Detailed concept statement <span className="text-danger">*</span>
                    </label>
                    <div className="flex items-center gap-1.5 font-mono text-[11.5px]">
                      <Check
                        className={cn("size-3.5", idea.trim().length >= 20 ? "text-success" : "text-muted")}
                      />
                      <span
                        className={cn(
                          "font-medium",
                          idea.length > MAX_IDEA * 0.95 ? "text-warning" : "text-muted",
                        )}
                      >
                        {idea.length} / {MAX_IDEA} characters
                      </span>
                    </div>
                  </div>
                  <textarea
                    id="idea"
                    rows={7}
                    maxLength={MAX_IDEA}
                    value={idea}
                    onChange={(event) => setIdea(event.target.value)}
                    placeholder="Describe your customer's current alternative, pain point, and core mechanism…"
                    className="w-full resize-none rounded-lg border border-line bg-surface p-3.5 text-[14px] leading-relaxed text-ink outline-none transition-colors placeholder:text-muted/70 focus:border-primary/60 focus:ring-4 focus:ring-primary/10"
                  />
                  {idea.trim().length > 0 && idea.trim().length < 20 && (
                    <p className="flex items-center gap-1.5 text-[12px] text-warning">
                      <AlertTriangle className="size-3.5" /> Add a little more detail — 20 characters
                      minimum.
                    </p>
                  )}

                  <div className="flex flex-wrap items-center gap-2 pt-1">
                    <span className="text-[12px] text-muted">Add a prompt:</span>
                    {IDEA_HINTS.map((hint) => (
                      <button
                        key={hint.label}
                        type="button"
                        onClick={() => appendHint(hint.text)}
                        className="inline-flex items-center gap-1 rounded-md bg-surface-soft px-2 py-1 text-[11.5px] text-muted transition-colors hover:text-ink"
                      >
                        <Plus className="size-3" /> {hint.label}
                      </button>
                    ))}
                  </div>
                </div>

                <div className="rounded-lg bg-surface-soft p-3.5">
                  <p className="flex items-center gap-1.5 text-[12px] font-medium text-ink">
                    <Sparkles className="size-3.5 text-primary" />
                    {passed} of {checks.length} description signals detected
                  </p>
                  <div className="mt-2 flex gap-1">
                    {checks.map((check) => (
                      <span
                        key={check.label}
                        title={check.label}
                        className={cn(
                          "h-1.5 flex-1 rounded-full",
                          check.passed ? "bg-primary" : "bg-line",
                        )}
                      />
                    ))}
                  </div>
                </div>
              </div>
            )}

            {/* ---- Step 3: help level ---- */}
            {step === 2 && (
              <div role="radiogroup" aria-label="Depth" className="grid gap-3 sm:grid-cols-2">
                {HELP_LEVELS.map((level) => {
                  const selected = helpLevel === level.id;
                  return (
                    <button
                      key={level.id}
                      type="button"
                      role="radio"
                      aria-checked={selected}
                      onClick={() => setHelpLevel(level.id)}
                      className={cn(
                        "flex flex-col gap-2.5 rounded-xl border p-4 text-left transition-colors",
                        selected
                          ? "border-primary bg-primary-soft/60 ring-1 ring-primary/20"
                          : "border-line hover:border-primary/30 hover:bg-surface-soft",
                      )}
                    >
                      <div className="flex items-start justify-between gap-2">
                        <p className="text-[14.5px] font-semibold text-ink">{level.title}</p>
                        {selected ? (
                          <CheckCircle2 className="size-4 shrink-0 text-primary" />
                        ) : level.recommended ? (
                          <span className="rounded bg-primary-soft px-1.5 py-0.5 font-mono text-[10px] font-medium uppercase text-primary">
                            Recommended
                          </span>
                        ) : null}
                      </div>
                      <p className="text-[12.5px] leading-snug text-muted">{level.blurb}</p>
                      <ul className="mt-auto flex flex-col gap-1 border-t border-line/70 pt-2">
                        {level.outputs.map((output) => (
                          <li key={output} className="flex items-center gap-1.5 text-[11.5px] text-muted">
                            <Check className="size-3 text-success" /> {output}
                          </li>
                        ))}
                      </ul>
                    </button>
                  );
                })}
              </div>
            )}

            {/* ---- Step 4: review ---- */}
            {step === 3 && (
              <div className="flex flex-col gap-4">
                <dl className="flex flex-col divide-y divide-line overflow-hidden rounded-xl border border-line">
                  {[
                    { label: "Title", value: title.trim(), step: 1 },
                    { label: "Category", value: category ?? "—", step: 0 },
                    { label: "Depth", value: HELP_LEVEL_LABEL[helpLevel], step: 2 },
                  ].map((row) => (
                    <div
                      key={row.label}
                      className="flex items-center justify-between gap-3 px-3.5 py-2.5"
                    >
                      <dt className="t-label text-muted">{row.label}</dt>
                      <dd className="flex items-center gap-2 text-[13px] font-medium capitalize text-ink">
                        {row.value}
                        <button
                          type="button"
                          onClick={() => setStep(row.step)}
                          className="text-[11.5px] font-normal text-primary hover:underline"
                        >
                          Edit
                        </button>
                      </dd>
                    </div>
                  ))}
                  <div className="flex flex-col gap-1.5 px-3.5 py-3">
                    <dt className="t-label text-muted">Idea</dt>
                    <dd className="line-clamp-5 text-[12.5px] leading-relaxed text-muted">
                      {idea.trim()}
                    </dd>
                  </div>
                </dl>

                <div className="rounded-xl border border-primary/20 bg-primary-soft/50 p-4">
                  <p className="t-label text-primary">Extraction will produce</p>
                  <ul className="mt-2 grid gap-2 sm:grid-cols-2">
                    {[
                      "Category and problem statement",
                      "Target users and key features",
                      "Typed, prioritised requirements",
                      "A list of what is still missing",
                    ].map((item) => (
                      <li key={item} className="flex items-center gap-2 text-[12.5px] text-ink">
                        <Check className="size-3.5 shrink-0 text-success" />
                        {item}
                      </li>
                    ))}
                  </ul>
                </div>

                {error && (
                  <p
                    role="alert"
                    className="rounded-lg border border-danger/25 bg-danger-soft px-3 py-2 text-[12.5px] text-danger"
                  >
                    {error}
                  </p>
                )}
              </div>
            )}

            {/* ---- Actions ---- */}
            <div className="flex items-center justify-between gap-3 border-t border-line pt-4">
              <Button
                variant="secondary"
                onClick={() => setStep((value) => Math.max(0, value - 1))}
                disabled={step === 0 || busy}
              >
                <ArrowLeft className="size-4" /> Back
              </Button>

              {step < STEPS.length - 1 ? (
                <Button onClick={next} disabled={!canContinue}>
                  {step === 0 ? "Continue to description" : "Continue"} <ArrowRight className="size-4" />
                </Button>
              ) : (
                <Button onClick={submit} disabled={busy} size="md">
                  {busy ? (
                    <>
                      <Loader2 className="size-4 animate-spin" /> Reading your idea…
                    </>
                  ) : (
                    <>
                      <Sparkles className="size-4" /> Understand my idea
                    </>
                  )}
                </Button>
              )}
            </div>
            {busy && (
              <p className="-mt-2 text-right text-[11.5px] text-muted">
                A live model call usually takes 20–60 seconds. Keep this tab open.
              </p>
            )}
          </div>
        </div>

        {/* ---------------- Right rail ---------------- */}
        <aside className="flex flex-col gap-4 lg:col-span-4">
          <div className="rounded-xl border border-line bg-surface p-5 shadow-sm">
            <div className="mb-3 flex items-center justify-between">
              <span className="t-label text-muted">Description readiness</span>
              <span
                className={cn(
                  "rounded-full px-2 py-0.5 font-mono text-[10.5px] font-semibold",
                  density >= 75
                    ? "bg-success-soft text-success"
                    : density >= 45
                      ? "bg-warning-soft text-warning"
                      : "bg-surface-soft text-muted",
                )}
              >
                {readinessLabel}
              </span>
            </div>
            <div className="mb-2 flex items-baseline gap-2">
              <span className="t-section tabular text-ink">{density}%</span>
              <span className="text-[12px] text-muted">of prompt context density</span>
            </div>
            <div className="mb-4 h-2 w-full overflow-hidden rounded-full bg-surface-soft">
              <div
                className={cn(
                  "h-full rounded-full transition-all duration-300",
                  density >= 75 ? "bg-success" : density >= 45 ? "bg-warning" : "bg-primary",
                )}
                style={{ width: `${Math.max(3, density)}%` }}
              />
            </div>

            <div className="mb-3 flex items-center gap-2">
              <CircleHelp className="size-4 text-accent" />
              <h2 className="t-title text-ink">Tips for a clean extraction</h2>
            </div>
            <p className="mb-3 text-[12px] leading-snug text-muted">
              These four answers give the parser the most to work with. Nothing is invented on your
              behalf.
            </p>
            <ul className="flex flex-col gap-2">
              {checks.map((check) => (
                <li
                  key={check.label}
                  className="flex items-start gap-2.5 rounded-lg bg-surface-soft p-2"
                >
                  {check.passed ? (
                    <Check className="mt-0.5 size-4 shrink-0 text-success" />
                  ) : (
                    <CircleHelp className="mt-0.5 size-4 shrink-0 text-muted" />
                  )}
                  <div>
                    <p className="text-[13px] font-medium text-ink">{check.label}</p>
                    <p className="text-[11.5px] leading-snug text-muted">{check.hint}</p>
                  </div>
                </li>
              ))}
            </ul>

            <div className="mt-4 flex items-start gap-2 border-t border-line pt-3 text-muted">
              <Lock className="mt-0.5 size-3.5 shrink-0" />
              <p className="text-[11.5px] leading-tight">
                Your idea is private to your workspace and is never shared publicly.
              </p>
            </div>
          </div>

          <div className="rounded-xl bg-surface-soft p-4">
            <div className="flex items-center justify-between">
              <span className="flex items-center gap-1 text-[12px] font-semibold text-ink">
                <Sparkles className="size-3.5 text-primary" /> What runs next
              </span>
              <span className="font-mono text-[11px] text-muted">Understanding</span>
            </div>
            <p className="mt-1.5 text-[12px] leading-snug text-muted">
              Creating the project stores version 1 of your text, then the understanding engine
              classifies it and extracts requirements.
            </p>
          </div>
        </aside>
      </div>
    </div>
  );
}
