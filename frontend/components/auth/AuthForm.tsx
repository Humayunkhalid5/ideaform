"use client";

import { ArrowRight, Check, Eye, EyeOff, Loader2, Lock } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { Logo } from "@/components/brand/Logo";
import { Button } from "@/components/ui/button";
import { Field, Input } from "@/components/ui/field";
import { api, setToken } from "@/lib/api";
import { APP_NAME, BRAND_LINE, PRODUCT_STATUS } from "@/lib/constants";
import { cn } from "@/lib/utils";

type Mode = "login" | "register";

export function AuthForm({ mode }: { mode: Mode }) {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [name, setName] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const isLogin = mode === "login";

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    setError(null);

    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
      setError("Enter a valid email address.");
      return;
    }
    if (password.length < 8) {
      setError("Password must be at least 8 characters.");
      return;
    }

    setBusy(true);
    try {
      if (!isLogin) {
        await api.register(email, password, name.trim() || undefined);
      }
      const { access_token } = await api.login(email, password);
      setToken(access_token);
      router.push("/dashboard");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong. Try again.");
      setBusy(false);
    }
  }

  return (
    <main className="grid min-h-screen lg:grid-cols-[1fr_1fr]">
      {/* ---------------- Brand panel ---------------- */}
      <section className="if-brand-stage relative hidden flex-col justify-between overflow-hidden border-r border-line p-10 lg:flex">
        <div className="pointer-events-none absolute inset-0 opacity-[0.08] if-grid" aria-hidden="true" />
        <div className="relative z-10">
          <Logo href="/" className="text-white" size="size-10" />
        </div>

        <div className="relative z-10 mx-auto flex w-full max-w-md flex-col gap-7">
          <div className="flex flex-col gap-3">
            <span className="inline-flex w-fit items-center gap-2 rounded-full border border-white/20 bg-white/10 px-3 py-1 text-[11.5px] text-white/80">
              <span className="size-1.5 rounded-full bg-brand-teal" />
              {PRODUCT_STATUS}
            </span>
            <h2 className="text-[32px] font-semibold leading-[1.15] tracking-[-0.025em]">
              A rough idea, turned into something precise.
            </h2>
            <p className="max-w-sm text-[14px] leading-relaxed text-white/70">
              {APP_NAME} reads what you actually wrote, researches it and scores it on six
              dimensions, with every claim pointing at its source.
            </p>
          </div>

          <ul className="flex flex-col gap-3">
            {[
              "Structure extracted from your own words",
              "Scores backed by cited evidence",
              "Every project private to your account",
            ].map((item) => (
              <li key={item} className="flex items-center gap-2.5 text-[13px] text-white/85">
                <span className="grid size-5 place-items-center rounded-full bg-white/10 text-brand-teal">
                  <Check className="size-3" />
                </span>
                {item}
              </li>
            ))}
          </ul>

          <div className="rounded-xl border border-white/15 bg-white/10 p-4 backdrop-blur-sm">
            <p className="font-mono text-[10.5px] uppercase tracking-[0.1em] text-white/60">
              Example output
            </p>
            <div className="mt-2 flex flex-col gap-1.5 text-[12.5px] text-white/90">
              <p className="flex items-center justify-between">
                <span className="text-white/60">Category</span> Software project
              </p>
              <p className="flex items-center justify-between">
                <span className="text-white/60">Requirements</span> 11 typed
              </p>
              <p className="flex items-center justify-between">
                <span className="text-white/60">Open gaps</span> 3 flagged
              </p>
            </div>
          </div>
        </div>

        <p className="relative z-10 text-[12px] text-white/50">
          {BRAND_LINE}
        </p>
      </section>

      {/* ---------------- Form panel ---------------- */}
      <section className="flex flex-col justify-center bg-canvas px-5 py-10 sm:px-10">
        <div className="mx-auto w-full max-w-[400px]">
          <div className="mb-8 lg:hidden">
            <Logo href="/" />
          </div>

          <div className="mb-6 flex flex-col gap-1.5">
            <p className="t-label text-primary">
              {isLogin ? "Welcome back" : "Create your workspace"}
            </p>
            <h1 className="t-section text-ink">
              {isLogin ? `Sign in to ${APP_NAME}` : "Start understanding ideas"}
            </h1>
            <p className="t-body text-muted">
              {isLogin
                ? "Pick up where your last idea left off."
                : "Free while in development. No card, no noise."}
            </p>
          </div>

          <div className="mb-6 grid grid-cols-2 gap-1 rounded-lg border border-line bg-surface p-1">
            {(["login", "register"] as const).map((tab) => (
              <Link
                key={tab}
                href={tab === "login" ? "/login" : "/register"}
                className={cn(
                  "rounded-md px-3 py-1.5 text-center text-[13px] font-medium transition-colors",
                  mode === tab
                    ? "bg-primary-soft text-primary shadow-sm"
                    : "text-muted hover:text-ink",
                )}
              >
                {tab === "login" ? "Sign in" : "Create account"}
              </Link>
            ))}
          </div>

          <form onSubmit={submit} className="flex flex-col gap-4" noValidate>
            {!isLogin && (
              <Field label="Full name" htmlFor="name" hint="Optional">
                <Input
                  id="name"
                  autoComplete="name"
                  placeholder="Ayesha Khan"
                  value={name}
                  onChange={(event) => setName(event.target.value)}
                />
              </Field>
            )}

            <Field label="Email" htmlFor="email">
              <Input
                id="email"
                type="email"
                autoComplete="email"
                placeholder="you@example.com"
                value={email}
                onChange={(event) => setEmail(event.target.value)}
              />
            </Field>

            <Field
              label="Password"
              htmlFor="password"
              hint={isLogin ? undefined : "At least 8 characters"}
            >
              <div className="relative">
                <Input
                  id="password"
                  type={showPassword ? "text" : "password"}
                  autoComplete={isLogin ? "current-password" : "new-password"}
                  placeholder="••••••••"
                  className="pr-11"
                  value={password}
                  onChange={(event) => setPassword(event.target.value)}
                />
                <button
                  type="button"
                  onClick={() => setShowPassword((value) => !value)}
                  aria-label={showPassword ? "Hide password" : "Show password"}
                  className="absolute right-1.5 top-1/2 grid size-8 -translate-y-1/2 place-items-center rounded-md text-muted transition-colors hover:bg-surface-soft hover:text-ink"
                >
                  {showPassword ? <EyeOff className="size-4" /> : <Eye className="size-4" />}
                </button>
              </div>
            </Field>

            {error && (
              <p
                role="alert"
                className="rounded-lg border border-danger/25 bg-danger-soft px-3 py-2 text-[12.5px] text-danger"
              >
                {error}
              </p>
            )}

            <Button type="submit" size="lg" className="mt-1 w-full" disabled={busy}>
              {busy ? (
                <>
                  <Loader2 className="size-4 animate-spin" /> Working…
                </>
              ) : (
                <>
                  {isLogin ? "Sign in" : "Create account"}
                  <ArrowRight className="size-4" />
                </>
              )}
            </Button>
          </form>

          <p className="mt-6 flex items-center justify-center gap-1.5 text-[12px] text-muted">
            <Lock className="size-3.5" /> Your projects are private to your account.
          </p>
        </div>
      </section>
    </main>
  );
}
