"use client";

import {
  AlertTriangle,
  ArrowRight,
  Building2,
  Check,
  GitCompare,
  Loader2,
  Pencil,
  RotateCw,
  Scale,
  Skull,
  Sparkles,
  Swords,
  X,
} from "lucide-react";
import Link from "next/link";
import { useParams, useRouter, useSearchParams } from "next/navigation";
import { Suspense, useCallback, useEffect, useMemo, useState, type ReactNode } from "react";

import { DimensionRadar } from "@/components/evaluation/charts";
import {
  CitedText,
  ClaimChip,
  DeltaChip,
  Disclaimer,
  EvidenceItem,
  ScoreCard,
} from "@/components/evaluation/parts";
import { RadialGauge } from "@/components/scores/RadialGauge";
import { EmptyState } from "@/components/states/EmptyState";
import { ErrorNotice } from "@/components/states/ErrorNotice";
import { Badge } from "@/components/ui/badge";
import { Button, buttonStyles } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Select, Textarea } from "@/components/ui/field";
import { PageSkeleton } from "@/components/ui/skeleton";
import { api } from "@/lib/api";
import type {
  Decision,
  Evaluation,
  EvidenceRef,
  ImprovementSuggestion,
  Level,
  VersionSummary,
} from "@/lib/types";
import { cn, formatRelative } from "@/lib/utils";

type Section = "risks" | "competitors" | "business" | "improve" | "evidence";

const SECTIONS: { key: Section; label: string; icon: ReactNode }[] = [
  { key: "risks", label: "Risks & Devil's Advocate", icon: <Skull className="size-3.5" /> },
  { key: "competitors", label: "Competitors", icon: <Swords className="size-3.5" /> },
  { key: "business", label: "Business model", icon: <Building2 className="size-3.5" /> },
  { key: "improve", label: "Improve", icon: <Sparkles className="size-3.5" /> },
  { key: "evidence", label: "All evidence", icon: <Scale className="size-3.5" /> },
];

const LEVEL_TONE: Record<Level, "danger" | "warning" | "neutral"> = {
  high: "danger",
  medium: "warning",
  low: "neutral",
};

function Pill({ children }: { children: ReactNode }) {
  return <span className="rounded-md bg-surface-soft px-2 py-1 text-[12px] text-ink/85">{children}</span>;
}

function CiteRefs({ ids }: { ids: string[] | null | undefined }) {
  if (!ids || ids.length === 0) return null;
  return (
    <span className="inline-flex flex-wrap gap-1">
      {ids.map((id) => (
        <a
          key={id}
          href={`#evidence-${id}`}
          className="rounded bg-primary-soft px-1 font-mono text-[10.5px] font-semibold text-primary hover:underline"
        >
          {id}
        </a>
      ))}
    </span>
  );
}

// ------------------------------------------------------------------ sections

function RisksSection({ ev, evidence }: { ev: Evaluation; evidence: Map<string, EvidenceRef> }) {
  const order: Record<Level, number> = { high: 0, medium: 1, low: 2 };
  const risks = [...ev.risks].sort(
    (a, b) => order[a.severity] - order[b.severity] || order[a.likelihood] - order[b.likelihood],
  );
  return (
    <div className="grid gap-4 lg:grid-cols-[1.4fr_1fr]">
      <Card className="flex flex-col gap-3 p-0">
        <div className="border-b border-line px-5 py-3">
          <h3 className="t-sub text-ink">Risk register</h3>
          <p className="text-[12px] text-muted">Sorted by severity, then likelihood.</p>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-left text-[12.5px]">
            <thead className="text-[11px] uppercase tracking-wide text-muted">
              <tr className="border-b border-line">
                <th className="px-5 py-2 font-medium">Risk</th>
                <th className="px-2 py-2 font-medium">Severity</th>
                <th className="px-2 py-2 font-medium">Likelihood</th>
                <th className="px-5 py-2 font-medium">Mitigation</th>
              </tr>
            </thead>
            <tbody>
              {risks.map((r) => (
                <tr key={r.id} className="border-b border-line/70 align-top last:border-0">
                  <td className="px-5 py-3">
                    <p className="font-medium text-ink">{r.title}</p>
                    <p className="mt-0.5 text-muted">{r.description}</p>
                    <div className="mt-1">
                      <CiteRefs ids={r.evidence_ids} />
                    </div>
                  </td>
                  <td className="px-2 py-3">
                    <Badge tone={LEVEL_TONE[r.severity]}>{r.severity}</Badge>
                  </td>
                  <td className="px-2 py-3">
                    <Badge tone={LEVEL_TONE[r.likelihood]}>{r.likelihood}</Badge>
                  </td>
                  <td className="px-5 py-3 text-ink/85">{r.mitigation || "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>

      <div className="flex flex-col gap-4">
        <div className="flex flex-col gap-3 rounded-xl bg-ink p-5 text-canvas shadow-sm">
          <p className="flex items-center gap-2 t-label text-canvas/70">
            <Skull className="size-3.5" /> Devil&apos;s Advocate
          </p>
          <h3 className="t-title">Why this idea might fail</h3>
          <p className="whitespace-pre-line text-[13px] leading-relaxed text-canvas/90">
            <CitedText text={ev.devils_advocate || "No critique was returned."} evidence={evidence} />
          </p>
        </div>
        {(ev.critique.hidden_assumptions?.length ?? 0) > 0 && (
          <Card className="flex flex-col gap-2">
            <h4 className="t-sub text-ink">Hidden assumptions</h4>
            <ul className="flex flex-col gap-1.5">
              {ev.critique.hidden_assumptions!.map((a, i) => (
                <li key={i} className="flex items-start gap-2 text-[12.5px] text-ink/85">
                  <ClaimChip label="assumption" /> <span className="pt-[1px]">{a}</span>
                </li>
              ))}
            </ul>
          </Card>
        )}
        {(ev.critique.must_be_true?.length ?? 0) > 0 && (
          <Card className="flex flex-col gap-2">
            <h4 className="t-sub text-ink">What would have to be true</h4>
            <ol className="flex list-decimal flex-col gap-1 pl-5 text-[12.5px] text-ink/85">
              {ev.critique.must_be_true!.map((a, i) => (
                <li key={i}>{a}</li>
              ))}
            </ol>
          </Card>
        )}
      </div>
    </div>
  );
}

function CompetitorsSection({ ev }: { ev: Evaluation }) {
  if (ev.competitors.length === 0) {
    return (
      <EmptyState
        title="No competitors named in the evidence"
        body="Competitors are only listed when a retrieved source names them. Run Research with a competitor query, then evaluate again."
      />
    );
  }
  return (
    <Card className="overflow-x-auto p-0">
      <table className="w-full min-w-[860px] text-left text-[12.5px]">
        <thead className="text-[11px] uppercase tracking-wide text-muted">
          <tr className="border-b border-line">
            {["Competitor", "Customers", "Pricing", "Strengths", "Weaknesses", "Our opening", "Source"].map((h) => (
              <th key={h} className="px-4 py-2.5 font-medium">
                {h}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {ev.competitors.map((c) => (
            <tr key={c.id} className="border-b border-line/70 align-top last:border-0">
              <td className="px-4 py-3">
                <p className="font-semibold text-ink">{c.name}</p>
                {c.website ? (
                  <a href={c.website} target="_blank" rel="noreferrer noopener" className="text-[11.5px] text-primary hover:underline">
                    {c.website.replace(/^https?:\/\/(www\.)?/, "")}
                  </a>
                ) : (
                  <p className="text-[11.5px] text-muted">site not verified</p>
                )}
                {c.description && <p className="mt-1 text-muted">{c.description}</p>}
              </td>
              <td className="px-4 py-3 text-ink/85">{c.target_customers || "—"}</td>
              <td className="px-4 py-3 text-ink/85">{c.pricing || <span className="text-muted">not stated</span>}</td>
              <td className="px-4 py-3">
                <ul className="flex flex-col gap-1">
                  {(c.strengths ?? []).map((s, i) => (
                    <li key={i} className="text-success">+ <span className="text-ink/85">{s}</span></li>
                  ))}
                </ul>
              </td>
              <td className="px-4 py-3">
                <ul className="flex flex-col gap-1">
                  {(c.weaknesses ?? []).map((s, i) => (
                    <li key={i} className="text-danger">− <span className="text-ink/85">{s}</span></li>
                  ))}
                </ul>
              </td>
              <td className="px-4 py-3 text-ink/85">{c.differentiation_opportunity || "—"}</td>
              <td className="px-4 py-3">
                <div className="flex flex-col gap-1">
                  <CiteRefs ids={c.evidence_ids} />
                  {c.source_url && (
                    <a href={c.source_url} target="_blank" rel="noreferrer noopener" className="text-[11.5px] text-primary hover:underline">
                      open source
                    </a>
                  )}
                </div>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </Card>
  );
}

function BusinessSection({ ev }: { ev: Evaluation }) {
  const bm = ev.business_model;
  if (!bm) {
    return <EmptyState title="No business model analysis" body="The business model step did not return a result. Evaluate again." />;
  }
  const blocks: { title: string; items: string[] }[] = [
    { title: "Customer segments", items: bm.customer_segments },
    { title: "Channels", items: bm.channels },
    { title: "Revenue streams", items: bm.revenue_streams },
    { title: "Cost structure", items: bm.cost_structure },
    { title: "Key metrics", items: bm.key_metrics },
  ];
  return (
    <div className="flex flex-col gap-4">
      <Card className="flex flex-col gap-1.5">
        <p className="t-label text-primary">Value proposition</p>
        <p className="text-[14px] leading-relaxed text-ink">{bm.value_proposition || "—"}</p>
        <CiteRefs ids={bm.evidence_ids} />
      </Card>
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {blocks.map((b) => (
          <Card key={b.title} className="flex flex-col gap-2">
            <h4 className="t-sub text-ink">{b.title}</h4>
            {b.items.length ? (
              <div className="flex flex-wrap gap-1.5">
                {b.items.map((item, i) => (
                  <Pill key={i}>{item}</Pill>
                ))}
              </div>
            ) : (
              <p className="text-[12px] text-muted">Not identified.</p>
            )}
          </Card>
        ))}
        <Card className="flex flex-col gap-2">
          <h4 className="t-sub text-ink">Assumptions</h4>
          <ul className="flex flex-col gap-1.5">
            {bm.assumptions.map((a, i) => (
              <li key={i} className="flex items-start gap-2 text-[12.5px] text-ink/85">
                <ClaimChip label="assumption" /> <span className="pt-[1px]">{a}</span>
              </li>
            ))}
          </ul>
        </Card>
      </div>
      {bm.pricing_options.length > 0 && (
        <div className="grid gap-4 md:grid-cols-3">
          {bm.pricing_options.map((p, i) => (
            <Card key={i} className="flex flex-col gap-1.5">
              <p className="t-label text-muted">Pricing option {i + 1}</p>
              <h4 className="t-sub text-ink">{p.name}</h4>
              <p className="font-mono text-[13px] text-primary">{p.price_point || p.model}</p>
              {p.price_point && p.model && <p className="text-[12px] text-muted">{p.model}</p>}
              <p className="text-[12.5px] leading-relaxed text-ink/85">{p.rationale}</p>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}

function ImproveSection({
  ev,
  projectId,
  isCurrent,
}: {
  ev: Evaluation;
  projectId: string;
  isCurrent: boolean;
}) {
  const router = useRouter();
  const [decisions, setDecisions] = useState<Record<string, Decision | undefined>>({});
  const [edits, setEdits] = useState<Record<string, string>>({});
  const [note, setNote] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const scoreOf = useMemo(
    () => Object.fromEntries(ev.dimensions.map((d) => [d.dimension, d.score])),
    [ev.dimensions],
  );

  const chosen = Object.entries(decisions).filter(([, d]) => d && d !== "rejected").length;
  const canSubmit = !busy && (chosen > 0 || note.trim().length > 0);

  function set(item: ImprovementSuggestion, decision: Decision | undefined) {
    setDecisions((prev) => ({ ...prev, [item.id]: prev[item.id] === decision ? undefined : decision }));
    if (decision === "edited" && !edits[item.id]) {
      setEdits((prev) => ({ ...prev, [item.id]: item.change || item.title }));
    }
  }

  async function submit() {
    setBusy(true);
    setError(null);
    try {
      const payload = Object.entries(decisions)
        .filter(([, d]) => d)
        .map(([improvement_id, decision]) => ({
          improvement_id,
          decision: decision as Decision,
          ...(decision === "edited" ? { edited_text: edits[improvement_id] ?? "" } : {}),
        }));
      const run = await api.improve(projectId, {
        evaluation_id: ev.id,
        decisions: payload,
        note: note.trim() || undefined,
      });
      if (run.status === "queued") {
        router.push(`/projects/${projectId}/run?run=${run.run_id}`);
        return;
      }
      const output = (await api.run(run.run_id)) as unknown as { output?: { compare?: { a: number; b: number } } };
      const pair = output.output?.compare;
      router.push(
        pair ? `/projects/${projectId}/compare?a=${pair.a}&b=${pair.b}` : `/projects/${projectId}/compare`,
      );
    } catch (err) {
      setError(err instanceof Error ? err.message : "The improvement loop failed.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="flex flex-col gap-4">
      <Card className="flex flex-col gap-1">
        <h3 className="t-title text-ink">Improvement loop</h3>
        <p className="max-w-3xl text-[13px] leading-relaxed text-muted">
          Accept, reject or edit each suggestion. Accepted and edited changes are written into
          version {ev.version_no + 1} of the idea, which is then understood and evaluated again
          against this evaluation, so every score change comes with a reason.
        </p>
        {!isCurrent && (
          <p className="mt-1 flex items-center gap-1.5 text-[12px] text-warning">
            <AlertTriangle className="size-3.5" /> This is not the current version; the new version
            will branch from v{ev.version_no}.
          </p>
        )}
      </Card>

      <ul className="flex flex-col gap-3">
        {ev.improvements.map((item) => {
          const decision = decisions[item.id];
          const previous = item.decision;
          return (
            <li
              key={item.id}
              className={cn(
                "if-card flex flex-col gap-3 p-4 transition-colors",
                decision === "accepted" && "border-success/50",
                decision === "edited" && "border-info/50",
                decision === "rejected" && "opacity-60",
              )}
            >
              <div className="flex flex-col justify-between gap-3 sm:flex-row sm:items-start">
                <div className="min-w-0">
                  <div className="flex flex-wrap items-center gap-1.5">
                    <ClaimChip label="ai_suggestion" />
                    {item.dimension_affected && (
                      <Badge tone="neutral" className="px-2 py-[1px] text-[11px]">
                        {item.dimension_label || item.dimension_affected} · now {scoreOf[item.dimension_affected] ?? "—"}
                      </Badge>
                    )}
                    {previous && (
                      <Badge tone="info" className="px-2 py-[1px] text-[11px]">
                        earlier: {previous}
                      </Badge>
                    )}
                    <CiteRefs ids={item.evidence_ids} />
                  </div>
                  <h4 className="mt-1.5 t-sub text-ink">{item.title}</h4>
                  <p className="mt-0.5 text-[12.5px] leading-relaxed text-muted">{item.rationale}</p>
                </div>
                <div className="flex shrink-0 gap-1.5">
                  <Button size="sm" variant={decision === "accepted" ? "primary" : "secondary"} onClick={() => set(item, "accepted")}>
                    <Check className="size-3.5" /> Accept
                  </Button>
                  <Button size="sm" variant={decision === "edited" ? "primary" : "secondary"} onClick={() => set(item, "edited")}>
                    <Pencil className="size-3.5" /> Edit
                  </Button>
                  <Button size="sm" variant={decision === "rejected" ? "danger" : "ghost"} onClick={() => set(item, "rejected")}>
                    <X className="size-3.5" /> Reject
                  </Button>
                </div>
              </div>
              {decision === "edited" ? (
                <Textarea
                  rows={3}
                  value={edits[item.id] ?? ""}
                  onChange={(e) => setEdits((prev) => ({ ...prev, [item.id]: e.target.value }))}
                  aria-label={`Edit the change for ${item.title}`}
                />
              ) : (
                <p className="rounded-lg bg-surface-soft px-3 py-2 text-[12.5px] leading-relaxed text-ink/90">
                  <span className="font-medium">Change: </span>
                  {item.change || item.title}
                  {item.expected_effect && <span className="text-muted"> — {item.expected_effect}</span>}
                </p>
              )}
            </li>
          );
        })}
      </ul>

      {ev.alternatives.length > 0 && (
        <Card className="flex flex-col gap-2">
          <h4 className="t-sub text-ink">Alternative directions</h4>
          <div className="flex flex-wrap gap-1.5">
            {ev.alternatives.map((a, i) => (
              <Pill key={i}>{a}</Pill>
            ))}
          </div>
        </Card>
      )}

      <Card className="flex flex-col gap-3">
        <label htmlFor="own-change" className="t-sub text-ink">
          Your own change (optional)
        </label>
        <Textarea
          id="own-change"
          rows={3}
          placeholder="e.g. Start with one university and add a free tier for first-year students."
          value={note}
          onChange={(e) => setNote(e.target.value)}
        />
        {error && <ErrorNotice message={error} />}
        <div className="flex flex-wrap items-center justify-between gap-3">
          <p className="text-[12px] text-muted">
            {chosen} change{chosen === 1 ? "" : "s"} selected. Rewriting and re-evaluating takes a few
            minutes on the free Groq tier.
          </p>
          <Button onClick={submit} disabled={!canSubmit}>
            {busy ? <Loader2 className="size-4 animate-spin" /> : <Sparkles className="size-4" />}
            {busy ? "Building the next version…" : `Create v${ev.version_no + 1} and re-evaluate`}
          </Button>
        </div>
      </Card>
    </div>
  );
}

// ------------------------------------------------------------------ page

function EvaluationView() {
  const params = useParams<{ id: string }>();
  const search = useSearchParams();
  const router = useRouter();
  const id = params.id;
  const versionParam = search.get("version");

  const [evaluation, setEvaluation] = useState<Evaluation | null>(null);
  const [versions, setVersions] = useState<VersionSummary[]>([]);
  const [loaded, setLoaded] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [running, setRunning] = useState(false);
  const [section, setSection] = useState<Section>("risks");

  const load = useCallback(async () => {
    setError(null);
    try {
      const [list, vers] = await Promise.all([
        api.evaluations(id, versionParam ? Number(versionParam) : undefined),
        api.versions(id),
      ]);
      setEvaluation(list[0] ?? null);
      setVersions(vers);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not load the evaluation.");
    } finally {
      setLoaded(true);
    }
  }, [id, versionParam]);

  useEffect(() => {
    void load();
  }, [load]);

  const evidence = useMemo(
    () => new Map((evaluation?.evidence ?? []).map((e) => [e.id, e])),
    [evaluation],
  );
  const current = versions.find((v) => v.is_current);
  const shownVersion = versionParam ? Number(versionParam) : current?.version_no;
  const isCurrent = !versionParam || shownVersion === current?.version_no;

  async function runEvaluation() {
    setRunning(true);
    setError(null);
    try {
      const run = await api.evaluate(id);
      if (run.status === "queued") {
        router.push(`/projects/${id}/run?run=${run.run_id}`);
        return;
      }
      if (versionParam) router.replace(`/projects/${id}/evaluation`);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Evaluation failed.");
    } finally {
      setRunning(false);
    }
  }

  if (!loaded) return <PageSkeleton cards={6} />;

  const header = (
    <div className="flex flex-col justify-between gap-3 sm:flex-row sm:items-center">
      <div className="flex flex-wrap items-center gap-2">
        <h2 className="t-title text-ink">Evaluation</h2>
        {versions.length > 1 && (
          <Select
            aria-label="Version"
            className="h-9 w-auto py-1 text-[13px]"
            value={shownVersion ?? ""}
            onChange={(e) => router.push(`/projects/${id}/evaluation?version=${e.target.value}`)}
          >
            {versions.map((v) => (
              <option key={v.id} value={v.version_no}>
                v{v.version_no}
                {v.is_current ? " (current)" : ""}
              </option>
            ))}
          </Select>
        )}
        {evaluation && (
          <span className="text-[12px] text-muted">
            v{evaluation.version_no} · {formatRelative(evaluation.created_at)}
            {evaluation.model_name ? ` · ${evaluation.model_name}` : ""}
          </span>
        )}
      </div>
      <div className="flex gap-2">
        {versions.length > 1 && (
          <Link href={`/projects/${id}/compare`} className={buttonStyles("secondary", "md")}>
            <GitCompare className="size-4" /> Compare versions
          </Link>
        )}
        {isCurrent && (
          <Button onClick={runEvaluation} disabled={running}>
            {running ? <Loader2 className="size-4 animate-spin" /> : evaluation ? <RotateCw className="size-4" /> : <Sparkles className="size-4" />}
            {running ? "Evaluating…" : evaluation ? "Evaluate again" : "Run evaluation"}
          </Button>
        )}
      </div>
    </div>
  );

  if (!evaluation) {
    return (
      <div className="flex flex-col gap-4">
        {header}
        <Disclaimer />
        {error && <ErrorNotice message={error} onRetry={load} />}
        {running ? (
          <Card className="flex items-center gap-3">
            <Loader2 className="size-5 animate-spin text-primary" />
            <div>
              <p className="t-sub text-ink">Scoring six dimensions…</p>
              <p className="text-[12.5px] text-muted">
                Gathering evidence, scoring, critiquing, extracting competitors and the business
                model. This takes one to four minutes on the free Groq tier.
              </p>
            </div>
          </Card>
        ) : (
          <EmptyState
            title={`No evaluation for v${shownVersion ?? 1} yet`}
            body="The Evaluation Agent scores six dimensions with cited evidence, lists risks and competitors, and suggests improvements. Run Research first for stronger evidence."
            action={
              <div className="flex flex-wrap justify-center gap-2">
                <Link href={`/projects/${id}/research`} className={buttonStyles("secondary", "md")}>
                  Research first <ArrowRight className="size-4" />
                </Link>
                {isCurrent && (
                  <Button onClick={runEvaluation}>
                    <Sparkles className="size-4" /> Run evaluation
                  </Button>
                )}
              </div>
            }
          />
        )}
      </div>
    );
  }

  const radar = evaluation.dimensions.map((d) => ({
    dimension: d.dimension,
    label: d.label,
    score: d.score,
    previous: d.previous_score,
  }));
  const previousOverall = evaluation.dimensions.every((d) => d.previous_score !== null)
    ? Math.round(evaluation.dimensions.reduce((s, d) => s + (d.previous_score ?? 0), 0) / evaluation.dimensions.length)
    : null;
  const lowCount = evaluation.dimensions.filter((d) => d.confidence === "low").length;

  return (
    <div className="flex flex-col gap-5">
      {header}
      <Disclaimer text={evaluation.disclaimer} />
      {error && <ErrorNotice message={error} onRetry={load} />}
      {running && (
        <Card className="flex items-center gap-3 py-3">
          <Loader2 className="size-4 animate-spin text-primary" />
          <p className="text-[13px] text-muted">Re-evaluating… this takes one to four minutes.</p>
        </Card>
      )}

      <div className="grid gap-4 lg:grid-cols-[1fr_1.15fr]">
        <Card className="flex flex-col gap-4 sm:flex-row sm:items-center">
          <RadialGauge value={evaluation.overall_score ?? 0} label="Overall" />
          <div className="flex min-w-0 flex-col gap-2">
            <div className="flex flex-wrap items-center gap-1.5">
              <span className="t-label text-muted">Mean of six dimensions</span>
              {previousOverall !== null && (
                <DeltaChip delta={(evaluation.overall_score ?? 0) - previousOverall} />
              )}
            </div>
            <p className="text-[13.5px] leading-relaxed text-ink">{evaluation.summary}</p>
            <div className="flex flex-wrap gap-1.5 text-[11.5px] text-muted">
              <span>{evaluation.evidence.length} passages</span>·
              <span>{evaluation.risks.length} risks</span>·
              <span>{evaluation.competitors.length} competitors</span>
              {lowCount > 0 && (
                <>
                  ·<span className="text-warning">{lowCount} low-confidence</span>
                </>
              )}
            </div>
            <div className="flex flex-wrap gap-1.5">
              <ClaimChip label="verified_fact" />
              <ClaimChip label="assumption" />
              <ClaimChip label="ai_suggestion" />
            </div>
          </div>
        </Card>
        <Card className="p-3">
          <DimensionRadar data={radar} previousLabel="Previous version" />
        </Card>
      </div>

      {evaluation.notices.length > 0 && (
        <details className="rounded-xl border border-line bg-surface px-4 py-3 text-[12.5px]">
          <summary className="cursor-pointer font-medium text-ink">
            Evidence checks ({evaluation.notices.length})
          </summary>
          <ul className="mt-2 flex flex-col gap-1 text-muted">
            {evaluation.notices.map((n, i) => (
              <li key={i}>• {n}</li>
            ))}
          </ul>
        </details>
      )}

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
        {evaluation.dimensions.map((d) => (
          <ScoreCard key={d.dimension} dim={d} evidence={evidence} />
        ))}
      </div>

      <div className="flex flex-col gap-4">
        <div className="no-scrollbar flex gap-1 overflow-x-auto border-b border-line" role="tablist">
          {SECTIONS.map((s) => (
            <button
              key={s.key}
              type="button"
              role="tab"
              aria-selected={section === s.key}
              onClick={() => setSection(s.key)}
              className={cn(
                "relative inline-flex h-10 items-center gap-1.5 whitespace-nowrap px-3 text-[13px] font-medium",
                section === s.key ? "text-primary" : "text-muted hover:text-ink",
              )}
            >
              {s.icon}
              {s.label}
              {s.key === "improve" && evaluation.improvements.length > 0 && (
                <span className="rounded-full bg-primary-soft px-1.5 text-[10.5px] text-primary">
                  {evaluation.improvements.length}
                </span>
              )}
              <span
                className={cn(
                  "absolute inset-x-2 -bottom-px h-[2px] rounded-full bg-primary transition-opacity",
                  section === s.key ? "opacity-100" : "opacity-0",
                )}
              />
            </button>
          ))}
        </div>
        {section === "risks" && <RisksSection ev={evaluation} evidence={evidence} />}
        {section === "competitors" && <CompetitorsSection ev={evaluation} />}
        {section === "business" && <BusinessSection ev={evaluation} />}
        {section === "improve" && <ImproveSection ev={evaluation} projectId={id} isCurrent={isCurrent} />}
        {section === "evidence" && (
          <ul className="grid gap-2 md:grid-cols-2">
            {evaluation.evidence.map((e) => (
              <EvidenceItem key={e.id} item={e} />
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}

export default function EvaluationPage() {
  return (
    <Suspense fallback={<PageSkeleton cards={6} />}>
      <EvaluationView />
    </Suspense>
  );
}
