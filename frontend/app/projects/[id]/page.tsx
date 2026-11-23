"use client";

import { useParams } from "next/navigation";
import { useCallback, useEffect, useState } from "react";

import { api, type ProjectDetail } from "../../../lib/api";

export default function ProjectPage() {
  const params = useParams<{ id: string }>();
  const id = params.id;
  const [project, setProject] = useState<ProjectDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [status, setStatus] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      setProject(await api.project(id));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not load the project");
    }
  }, [id]);

  useEffect(() => {
    void load();
  }, [load]);

  async function toggle(requirementId: string, confirmed: boolean) {
    if (!project) return;
    setProject({
      ...project,
      requirements: project.requirements.map((r) =>
        r.id === requirementId ? { ...r, confirmed } : r,
      ),
    });
    try {
      await api.updateRequirements(id, [{ id: requirementId, confirmed }]);
      setStatus("Saved");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not save");
    }
  }

  async function rerun() {
    setStatus("Extracting…");
    setError(null);
    try {
      const { status: runStatus } = await api.understand(id);
      if (runStatus === "succeeded") {
        await load();
        setStatus("Extraction finished");
      } else {
        setStatus("Extraction queued — reload in a moment");
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not start extraction");
      setStatus(null);
    }
  }

  if (!project) {
    return (
      <main className="mx-auto max-w-2xl p-8">
        <p className="text-neutral-600">{error ?? "Loading…"}</p>
      </main>
    );
  }

  const structured = project.version?.structured_idea as
    | { problem?: string; target_users?: string[]; key_features?: string[]; missing_information?: string[] }
    | null
    | undefined;

  return (
    <main className="mx-auto flex max-w-2xl flex-col gap-6 p-8">
      <header className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold">{project.title}</h1>
          <p className="text-sm text-neutral-500">
            {project.category} · {project.status}
          </p>
        </div>
        <button className="rounded border px-3 py-2 text-sm" onClick={rerun}>
          Re-run extraction
        </button>
      </header>

      {error && <p className="text-sm text-red-600">{error}</p>}
      {status && <p className="text-sm text-neutral-500">{status}</p>}

      {structured ? (
        <section className="flex flex-col gap-2 rounded border p-4">
          <h2 className="font-medium">Understanding</h2>
          {structured.problem && <p className="text-sm">{structured.problem}</p>}
          {!!structured.key_features?.length && (
            <p className="text-sm text-neutral-600">
              Features: {structured.key_features.join(", ")}
            </p>
          )}
          {!!structured.missing_information?.length && (
            <p className="text-sm text-amber-700">
              Missing: {structured.missing_information.join(", ")}
            </p>
          )}
        </section>
      ) : (
        <p className="text-sm text-neutral-600">
          No extraction yet. Press “Re-run extraction” once the worker and LLM provider are up.
        </p>
      )}

      <section className="flex flex-col gap-2">
        <h2 className="font-medium">Requirements ({project.requirements.length})</h2>
        {project.requirements.map((requirement) => (
          <label
            key={requirement.id}
            className="flex items-start gap-3 rounded border p-3 text-sm"
          >
            <input
              type="checkbox"
              checked={requirement.confirmed}
              onChange={(e) => toggle(requirement.id, e.target.checked)}
            />
            <span>
              <span className="text-xs uppercase text-neutral-500">
                {requirement.req_type} · {requirement.priority ?? "should"}
              </span>
              <br />
              {requirement.description}
            </span>
          </label>
        ))}
      </section>
    </main>
  );
}
