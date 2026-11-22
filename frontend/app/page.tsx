const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

async function getHealth(): Promise<{ status: string }> {
  try {
    const res = await fetch(`${apiUrl}/health`, { cache: "no-store" });
    if (!res.ok) return { status: `HTTP ${res.status}` };
    return (await res.json()) as { status: string };
  } catch {
    return { status: "unreachable" };
  }
}

export default async function Home() {
  const health = await getHealth();
  const ok = health.status === "ok";

  return (
    <main className="mx-auto flex min-h-screen max-w-2xl flex-col justify-center gap-6 p-8">
      <h1 className="text-3xl font-semibold">Ideaform</h1>
      <p className="text-neutral-600">
        Turn a rough idea into evidence-backed evaluation and a buildable blueprint.
      </p>
      <div className="rounded-lg border p-4">
        <p className="text-sm text-neutral-500">API</p>
        <p className={ok ? "text-green-600" : "text-red-600"}>{health.status}</p>
      </div>
    </main>
  );
}
