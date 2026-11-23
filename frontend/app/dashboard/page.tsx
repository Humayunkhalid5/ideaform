"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { api, clearToken, getToken, type Project } from "../../lib/api";

export default function DashboardPage() {
  const router = useRouter();
  const [projects, setProjects] = useState<Project[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!getToken()) {
      router.replace("/login");
      return;
    }
    api
      .projects()
      .then(setProjects)
      .catch((err: Error) => setError(err.message));
  }, [router]);

  return (
    <main className="mx-auto flex min-h-screen max-w-3xl flex-col gap-6 p-8">
      <header className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold">Your projects</h1>
        <div className="flex gap-3 text-sm">
          <Link className="rounded bg-black px-3 py-2 text-white" href="/projects/new">
            New project
          </Link>
          <button
            className="rounded border px-3 py-2"
            onClick={() => {
              clearToken();
              router.push("/login");
            }}
          >
            Sign out
          </button>
        </div>
      </header>

      {error && <p className="text-sm text-red-600">{error}</p>}
      {projects.length === 0 && !error && (
        <p className="text-neutral-600">No projects yet. Start with a rough idea.</p>
      )}

      <ul className="flex flex-col gap-2">
        {projects.map((project) => (
          <li key={project.id}>
            <Link
              className="flex items-center justify-between rounded border p-4 hover:bg-neutral-50"
              href={`/projects/${project.id}`}
            >
              <span className="font-medium">{project.title}</span>
              <span className="text-sm text-neutral-500">
                {project.category} · {project.status}
              </span>
            </Link>
          </li>
        ))}
      </ul>
    </main>
  );
}
