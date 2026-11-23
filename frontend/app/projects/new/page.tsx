"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { api } from "../../../lib/api";

export default function NewProjectPage() {
  const router = useRouter();
  const [title, setTitle] = useState("");
  const [idea, setIdea] = useState("");
  const [helpLevel, setHelpLevel] = useState("everything");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const project = await api.createProject({
        title,
        idea_text: idea,
        help_level: helpLevel,
      });
      await api.understand(project.id).catch(() => undefined);
      router.push(`/projects/${project.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not create the project");
      setBusy(false);
    }
  }

  return (
    <main className="mx-auto flex min-h-screen max-w-xl flex-col justify-center gap-6 p-8">
      <h1 className="text-2xl font-semibold">New project</h1>
      <form onSubmit={submit} className="flex flex-col gap-4">
        <label className="flex flex-col gap-1 text-sm">
          Title
          <input
            className="rounded border p-2"
            required
            minLength={3}
            value={title}
            onChange={(e) => setTitle(e.target.value)}
          />
        </label>

        <label className="flex flex-col gap-1 text-sm">
          Describe your idea
          <textarea
            className="min-h-40 rounded border p-2"
            required
            minLength={20}
            placeholder="What problem does it solve, for whom, and how?"
            value={idea}
            onChange={(e) => setIdea(e.target.value)}
          />
          <span className="text-xs text-neutral-500">{idea.length} characters</span>
        </label>

        <label className="flex flex-col gap-1 text-sm">
          How much help do you want?
          <select
            className="rounded border p-2"
            value={helpLevel}
            onChange={(e) => setHelpLevel(e.target.value)}
          >
            <option value="evaluate">Just evaluate it</option>
            <option value="research">Evaluate and research the market</option>
            <option value="blueprint">Everything up to a technical blueprint</option>
            <option value="everything">Everything, including a roadmap</option>
          </select>
        </label>

        {error && <p className="text-sm text-red-600">{error}</p>}
        <button
          className="rounded bg-black px-4 py-2 text-white disabled:opacity-50"
          disabled={busy}
          type="submit"
        >
          {busy ? "Creating…" : "Create project"}
        </button>
      </form>
    </main>
  );
}
