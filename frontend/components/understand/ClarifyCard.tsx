"use client";

import { HelpCircle, Loader2 } from "lucide-react";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Textarea } from "@/components/ui/field";
import { api } from "@/lib/api";
import type { IdeaClarity } from "@/lib/types";

/**
 * SRS UC-1 alternate flow: the idea is too vague, so IdeaForm asks clarifying questions
 * instead of guessing. Answers are appended to the idea as the next version, which is then
 * understood again.
 */
export function ClarifyCard({
  projectId,
  ideaText,
  versionNo,
  clarity,
}: {
  projectId: string;
  ideaText: string;
  versionNo: number;
  clarity: IdeaClarity;
}) {
  const router = useRouter();
  const [answers, setAnswers] = useState<string[]>(clarity.questions.map(() => ""));
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const answered = answers.filter((a) => a.trim()).length;

  async function save() {
    setBusy(true);
    setError(null);
    try {
      const details = clarity.questions
        .map((q, i) => (answers[i].trim() ? `${q}\n${answers[i].trim()}` : ""))
        .filter(Boolean)
        .join("\n\n");
      await api.createVersion(projectId, {
        idea_text: `${ideaText.trim()}\n\n${details}`,
        change_summary: `Answered ${answered} clarifying question${answered === 1 ? "" : "s"}`,
      });
      const run = await api.understand(projectId);
      router.push(run.status === "queued" ? `/projects/${projectId}/run?run=${run.run_id}` : `/projects/${projectId}/understand`);
      router.refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not save your answers.");
      setBusy(false);
    }
  }

  return (
    <Card className="flex flex-col gap-3 border-warning/30">
      <h3 className="flex items-center gap-1.5 t-sub text-ink">
        <HelpCircle className="size-4 text-warning" /> This idea is too vague to analyse well
      </h3>
      <ul className="flex flex-col gap-1 text-[12px] text-muted">
        {clarity.reasons.map((r) => (
          <li key={r}>{r}</li>
        ))}
      </ul>
      <p className="text-[12.5px] text-ink/85">
        Answer what you can. Your answers become version {versionNo + 1}, which is understood again; nothing is
        filled in for you.
      </p>
      <div className="flex flex-col gap-3">
        {clarity.questions.map((q, i) => (
          <label key={q} className="flex flex-col gap-1.5">
            <span className="text-[12.5px] font-medium text-ink">{q}</span>
            <Textarea
              rows={2}
              maxLength={600}
              value={answers[i]}
              onChange={(e) => setAnswers((list) => list.map((a, j) => (j === i ? e.target.value : a)))}
              className="text-[13px]"
            />
          </label>
        ))}
      </div>
      {error && <p className="text-[12px] text-danger">{error}</p>}
      <Button size="sm" onClick={save} disabled={busy || answered === 0} className="self-start">
        {busy ? <Loader2 className="size-3.5 animate-spin" /> : null}
        Save as version {versionNo + 1} and re-run
      </Button>
    </Card>
  );
}
