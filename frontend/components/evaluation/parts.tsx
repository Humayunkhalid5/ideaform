"use client";

import {
  AlertTriangle,
  ArrowDownRight,
  ArrowUpRight,
  ChevronDown,
  Info,
  Lightbulb,
  ShieldCheck,
  Sparkles,
} from "lucide-react";
import { Fragment, useState, type ReactNode } from "react";

import { scoreTone } from "@/components/scores/RadialGauge";
import { Badge } from "@/components/ui/badge";
import type { Claim, ClaimLabel, Confidence, DimensionScore, EvidenceRef } from "@/lib/types";
import { cn, formatDate } from "@/lib/utils";

export const CLAIM_META: Record<ClaimLabel, { label: string; tone: "success" | "warning" | "accent"; hint: string }> = {
  verified_fact: {
    label: "Verified fact",
    tone: "success",
    hint: "Directly supported by at least one cited source.",
  },
  assumption: {
    label: "Assumption",
    tone: "warning",
    hint: "Needed to continue but not verified by the evidence.",
  },
  ai_suggestion: {
    label: "AI suggestion",
    tone: "accent",
    hint: "A recommendation or opinion from the model.",
  },
};

export const DIRECTION_NOTE: Partial<Record<string, string>> = {
  competition: "Higher = less threatening competition or stronger differentiation.",
  resource_requirements: "Higher = cheaper or lighter to resource.",
  execution_complexity: "Higher = easier to deliver.",
};

export function ClaimChip({ label }: { label: ClaimLabel }) {
  const meta = CLAIM_META[label];
  return (
    <Badge tone={meta.tone} title={meta.hint} className="px-2 py-[1px] text-[11px]">
      {label === "verified_fact" ? (
        <ShieldCheck className="size-3" />
      ) : label === "assumption" ? (
        <Info className="size-3" />
      ) : (
        <Sparkles className="size-3" />
      )}
      {meta.label}
    </Badge>
  );
}

export function ConfidenceBadge({ confidence }: { confidence: Confidence }) {
  const tone = confidence === "high" ? "success" : confidence === "medium" ? "info" : "warning";
  return (
    <Badge tone={tone} className="px-2 py-[1px] text-[11px]" title={CONFIDENCE_HINT[confidence]}>
      {confidence === "low" && <AlertTriangle className="size-3" />}
      {confidence} confidence
    </Badge>
  );
}

const CONFIDENCE_HINT: Record<Confidence, string> = {
  high: "At least 3 independent, relevant sources agree.",
  medium: "1-2 relevant sources, or sources partly conflict.",
  low: "Little or no direct evidence; mostly assumptions.",
};

export function Disclaimer({ text }: { text?: string | null }) {
  return (
    <div
      role="note"
      className="flex items-start gap-2.5 rounded-xl border border-warning/30 bg-warning-soft px-4 py-3 text-[13px] leading-relaxed text-ink"
    >
      <AlertTriangle className="mt-0.5 size-4 shrink-0 text-warning" />
      <p>
        <span className="font-semibold">Estimates, not predictions.</span>{" "}
        {text ||
          "Scores are evidence-based estimates from the retrieved sources, not predictions of business success."}
      </p>
    </div>
  );
}

export function DeltaChip({ delta, className }: { delta: number | null | undefined; className?: string }) {
  if (delta === null || delta === undefined) return null;
  const tone = delta > 0 ? "success" : delta < 0 ? "danger" : "neutral";
  return (
    <Badge tone={tone} className={cn("px-2 py-[1px] font-mono text-[11px]", className)}>
      {delta > 0 ? <ArrowUpRight className="size-3" /> : delta < 0 ? <ArrowDownRight className="size-3" /> : null}
      {delta > 0 ? `+${delta}` : delta === 0 ? "±0" : delta}
    </Badge>
  );
}

/** Render text with [E#] markers as clickable citation chips. */
export function CitedText({
  text,
  evidence,
  onCite,
}: {
  text: string;
  evidence: Map<string, EvidenceRef>;
  onCite?: (id: string) => void;
}) {
  const parts = text.split(/(\[E\d+\])/g);
  return (
    <>
      {parts.map((part, i) => {
        const match = /^\[(E\d+)\]$/.exec(part);
        if (!match) return <Fragment key={i}>{part}</Fragment>;
        const ref = evidence.get(match[1]);
        return (
          <button
            key={i}
            type="button"
            onClick={() => onCite?.(match[1])}
            title={ref?.title ?? match[1]}
            className="mx-0.5 rounded bg-primary-soft px-1 py-[1px] align-baseline font-mono text-[10.5px] font-semibold text-primary hover:underline"
          >
            {match[1]}
          </button>
        );
      })}
    </>
  );
}

export function EvidenceItem({ item, highlighted }: { item: EvidenceRef; highlighted?: boolean }) {
  const host = item.url
    ? (() => {
        try {
          return new URL(item.url).hostname.replace(/^www\./, "");
        } catch {
          return item.url;
        }
      })()
    : "uploaded document";
  return (
    <li
      id={`evidence-${item.id}`}
      className={cn(
        "flex flex-col gap-1 rounded-lg border bg-surface p-3 transition-colors",
        highlighted ? "border-primary/60 ring-2 ring-primary/15" : "border-line",
      )}
    >
      <div className="flex flex-wrap items-center gap-1.5 text-[12px]">
        <span className="font-mono text-[11px] font-semibold text-primary">[{item.id}]</span>
        <Badge tone={item.kb === "C" ? "primary" : item.kb === "B" ? "accent" : "info"} className="px-2 py-0 text-[10.5px]">
          {item.kb === "C" ? "Project" : item.kb === "B" ? "KB-B technical" : "KB-A business"}
        </Badge>
        {item.url ? (
          <a
            href={item.url}
            target="_blank"
            rel="noreferrer noopener"
            className="inline-flex min-w-0 items-center gap-1 truncate font-medium text-ink hover:text-primary"
          >
            {item.title || host} <ArrowUpRight className="size-3 shrink-0" />
          </a>
        ) : (
          <span className="font-medium text-ink">{item.title || host}</span>
        )}
        <span className="text-muted">{item.published_at ? formatDate(item.published_at) : "n.d."}</span>
      </div>
      <p className="line-clamp-3 text-[12px] leading-relaxed text-ink/80">{item.snippet}</p>
    </li>
  );
}

function ListBlock({ title, icon, items }: { title: string; icon: ReactNode; items: string[] }) {
  if (items.length === 0) return null;
  return (
    <div className="flex flex-col gap-1.5">
      <p className="flex items-center gap-1.5 t-label text-muted">
        {icon} {title}
      </p>
      <ul className="flex flex-col gap-1 pl-1">
        {items.map((item, i) => (
          <li key={i} className="flex gap-2 text-[12.5px] leading-relaxed text-ink/85">
            <span className="mt-[7px] size-1 shrink-0 rounded-full bg-muted/60" />
            {item}
          </li>
        ))}
      </ul>
    </div>
  );
}

function ClaimRow({ claim, evidence, onCite }: { claim: Claim; evidence: Map<string, EvidenceRef>; onCite: (id: string) => void }) {
  return (
    <li className="flex flex-col gap-1 rounded-lg bg-surface-soft p-2.5">
      <div className="flex flex-wrap items-center gap-1.5">
        <ClaimChip label={claim.label} />
        {claim.evidence_ids.map((ref) => (
          <button
            key={ref}
            type="button"
            onClick={() => onCite(ref)}
            className="rounded bg-primary-soft px-1 font-mono text-[10.5px] font-semibold text-primary hover:underline"
          >
            {ref}
          </button>
        ))}
      </div>
      <p className="text-[12.5px] leading-relaxed text-ink/90">{claim.text}</p>
    </li>
  );
}

export function ScoreCard({
  dim,
  evidence,
  defaultOpen = false,
}: {
  dim: DimensionScore;
  evidence: Map<string, EvidenceRef>;
  defaultOpen?: boolean;
}) {
  const [open, setOpen] = useState(defaultOpen);
  const [cited, setCited] = useState<string | null>(null);
  const tone = scoreTone(dim.score);
  const delta = dim.previous_score !== null ? dim.score - dim.previous_score : null;
  const sources = dim.evidence_ids.map((id) => evidence.get(id)).filter(Boolean) as EvidenceRef[];

  function cite(id: string) {
    setOpen(true);
    setCited(id);
    window.setTimeout(() => {
      document.getElementById(`evidence-${id}`)?.scrollIntoView({ behavior: "smooth", block: "nearest" });
    }, 50);
  }

  return (
    <article
      className={cn(
        "if-card flex flex-col gap-3 p-4",
        dim.confidence === "low" && "border-warning/40",
      )}
      data-testid="score-card"
    >
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
        className="flex w-full flex-col gap-3 text-left"
      >
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0">
            <h3 className="t-sub text-ink">{dim.label}</h3>
            {DIRECTION_NOTE[dim.dimension] && (
              <p className="mt-0.5 text-[11px] text-muted">{DIRECTION_NOTE[dim.dimension]}</p>
            )}
          </div>
          <div className="flex shrink-0 items-baseline gap-1">
            <span className="font-display text-[28px] font-semibold leading-none tabular" style={{ color: tone.color }}>
              {dim.score}
            </span>
            <span className="text-[11px] text-muted">/100</span>
          </div>
        </div>
        <div className="h-1.5 w-full overflow-hidden rounded-full bg-surface-soft">
          <div
            className="h-full rounded-full transition-[width] duration-700"
            style={{ width: `${dim.score}%`, background: tone.color }}
          />
        </div>
        <div className="flex flex-wrap items-center gap-1.5">
          <span className="text-[12px] font-medium" style={{ color: tone.color }}>
            {tone.label}
          </span>
          <ConfidenceBadge confidence={dim.confidence} />
          <Badge tone="neutral" className="px-2 py-[1px] text-[11px]">
            {sources.length} {sources.length === 1 ? "source" : "sources"}
          </Badge>
          {delta !== null && <DeltaChip delta={delta} />}
          <ChevronDown className={cn("ml-auto size-4 text-muted transition-transform", open && "rotate-180")} />
        </div>
      </button>

      <p className={cn("text-[13px] leading-relaxed text-ink/90", !open && "line-clamp-3")}>
        <CitedText text={dim.explanation} evidence={evidence} onCite={cite} />
      </p>

      {dim.change_reason && (
        <p className="rounded-lg border border-info/25 bg-info-soft px-3 py-2 text-[12.5px] leading-relaxed text-ink">
          <span className="font-semibold">
            {delta === 0 ? "Why it stayed" : "Why it moved"}
            {dim.previous_score !== null ? ` (${dim.previous_score} → ${dim.score})` : ""}:
          </span>{" "}
          {dim.change_reason}
        </p>
      )}

      {open && (
        <div className="flex flex-col gap-3 border-t border-line pt-3">
          {dim.claims.length > 0 && (
            <div className="flex flex-col gap-1.5">
              <p className="t-label text-muted">Claims</p>
              <ul className="flex flex-col gap-1.5">
                {dim.claims.map((c, i) => (
                  <ClaimRow key={i} claim={c} evidence={evidence} onCite={cite} />
                ))}
              </ul>
            </div>
          )}
          <ListBlock title="Assumptions" icon={<Info className="size-3" />} items={dim.assumptions} />
          <ListBlock title="Recommendations" icon={<Lightbulb className="size-3" />} items={dim.recommendations} />
          <div className="flex flex-col gap-1.5">
            <p className="t-label text-muted">Sources</p>
            {sources.length === 0 ? (
              <p className="rounded-lg bg-warning-soft px-3 py-2 text-[12px] text-ink">
                No retrieved source supports this dimension, so the score rests on assumptions.
              </p>
            ) : (
              <ul className="flex flex-col gap-1.5">
                {sources.map((s) => (
                  <EvidenceItem key={s.id} item={s} highlighted={cited === s.id} />
                ))}
              </ul>
            )}
          </div>
        </div>
      )}
    </article>
  );
}
