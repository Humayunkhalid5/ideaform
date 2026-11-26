"use client";

import {
  BookOpen,
  LayoutDashboard,
  Lock,
  LogOut,
  Plus,
  Settings,
} from "lucide-react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { BrandMark, Logo } from "@/components/brand/Logo";
import { ThemeToggle } from "@/components/ui/theme-toggle";
import { api, clearToken, getToken } from "@/lib/api";
import { PRODUCT_STATUS, PRODUCT_STATUS_DETAIL } from "@/lib/constants";
import type { User } from "@/lib/types";
import { cn, initials } from "@/lib/utils";

const NAV = [
  { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { href: "/projects/new", label: "New project", icon: Plus },
];

const LATER = [
  { href: "/knowledge", label: "Knowledge sources", icon: BookOpen },
  { href: "/settings", label: "Settings", icon: Settings },
];

const SEGMENTS: { match: RegExp; crumbs: string[] }[] = [
  { match: /^\/dashboard$/, crumbs: ["Workspace", "Dashboard"] },
  { match: /^\/projects\/new$/, crumbs: ["Workspace", "New project"] },
  { match: /^\/projects\/[^/]+\/understand$/, crumbs: ["Workspace", "Project", "Understanding"] },
  { match: /^\/projects\/[^/]+\/run$/, crumbs: ["Workspace", "Project", "Analysis run"] },
  { match: /^\/projects\/[^/]+$/, crumbs: ["Workspace", "Project", "Overview"] },
];

function breadcrumbFor(pathname: string): string[] {
  return SEGMENTS.find((segment) => segment.match.test(pathname))?.crumbs ?? ["Workspace"];
}

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const [user, setUser] = useState<User | null>(null);
  const [checking, setChecking] = useState(true);

  useEffect(() => {
    if (!getToken()) {
      router.replace("/login");
      return;
    }
    let cancelled = false;
    api
      .me()
      .then((me) => {
        if (cancelled) return;
        setUser(me);
        setChecking(false);
      })
      .catch(() => {
        clearToken();
        router.replace("/login");
      });
    return () => {
      cancelled = true;
    };
  }, [router]);

  function signOut() {
    clearToken();
    router.push("/login");
  }

  if (checking || !user) {
    return (
      <div className="grid min-h-screen place-items-center bg-canvas">
        <div className="flex flex-col items-center gap-3">
          <BrandMark className="size-10 animate-pulse text-ink" animated={false} />
          <p className="text-[13px] text-muted">Preparing your workspace…</p>
        </div>
      </div>
    );
  }

  const crumbs = breadcrumbFor(pathname);
  const name = user.full_name || user.email.split("@")[0];

  return (
    <div className="min-h-screen bg-canvas">
      <a
        href="#content"
        className="sr-only focus:not-sr-only focus:absolute focus:left-4 focus:top-4 focus:z-50 focus:rounded-lg focus:bg-surface focus:px-4 focus:py-2 focus:text-[13px] focus:shadow-e2"
      >
        Skip to content
      </a>

      {/* ---------------- Sidebar ---------------- */}
      <aside className="fixed inset-y-0 left-0 z-40 hidden w-[248px] flex-col border-r border-line bg-surface lg:flex">
        <div className="flex h-14 items-center gap-2 border-b border-line px-4">
          <Logo href="/dashboard" />
          <span className="ml-auto rounded-md bg-surface-soft px-1.5 py-0.5 font-mono text-[10px] text-muted">
            v1
          </span>
        </div>

        <nav className="flex flex-col gap-1 px-3 py-4" aria-label="Main">
          <p className="t-label px-2 pb-1 text-muted">Workspace</p>
          {NAV.map((item) => {
            const active =
              pathname === item.href ||
              (item.href !== "/dashboard" && pathname.startsWith(item.href));
            return (
              <Link
                key={item.href}
                href={item.href}
                className={cn(
                  "flex h-9 items-center gap-2.5 rounded-lg px-2.5 text-[13.5px] font-medium transition-colors",
                  active
                    ? "bg-primary-soft text-primary"
                    : "text-muted hover:bg-surface-soft hover:text-ink",
                )}
              >
                <item.icon className="size-4" />
                {item.label}
              </Link>
            );
          })}

          <p className="t-label px-2 pb-1 pt-5 text-muted">Later phases</p>
          {LATER.map((item) => (
            <span
              key={item.href}
              aria-disabled="true"
              title="Not available in this build"
              className="flex h-9 cursor-not-allowed items-center gap-2.5 rounded-lg px-2.5 text-[13.5px] text-muted/60"
            >
              <item.icon className="size-4" />
              {item.label}
              <Lock className="ml-auto size-3" />
            </span>
          ))}
        </nav>

        <div className="mt-auto flex flex-col gap-3 px-3 pb-4">
          <div className="rounded-xl border border-line bg-surface-soft p-3">
            <p className="flex items-center gap-1.5 text-[11.5px] font-semibold text-primary">
              <span className="size-1.5 rounded-full bg-success" />
              {PRODUCT_STATUS}
            </p>
            <p className="mt-1 text-[11.5px] leading-snug text-muted">{PRODUCT_STATUS_DETAIL}</p>
          </div>

          <div className="flex items-center gap-2.5 rounded-xl border border-line p-2">
            <span className="grid size-8 shrink-0 place-items-center rounded-full bg-primary-soft text-[11.5px] font-semibold text-primary">
              {initials(user.full_name || user.email)}
            </span>
            <div className="min-w-0 flex-1">
              <p className="truncate text-[12.5px] font-medium text-ink">{name}</p>
              <p className="truncate text-[11px] text-muted">{user.email}</p>
            </div>
            <button
              type="button"
              onClick={signOut}
              title="Sign out"
              aria-label="Sign out"
              className="grid size-7 shrink-0 place-items-center rounded-lg text-muted transition-colors hover:bg-surface-soft hover:text-ink"
            >
              <LogOut className="size-3.5" />
            </button>
          </div>
        </div>
      </aside>

      {/* ---------------- Content ---------------- */}
      <div className="lg:pl-[248px]">
        <header className="sticky top-0 z-30 flex h-14 items-center gap-3 border-b border-line bg-surface/90 px-4 backdrop-blur-md sm:px-6">
          <div className="lg:hidden">
            <Logo href="/dashboard" size="size-8" />
          </div>
          <nav aria-label="Breadcrumb" className="flex min-w-0 items-center gap-1.5">
            {crumbs.map((crumb, index) => (
              <span key={crumb} className="flex items-center gap-1.5">
                {index > 0 && <span className="text-[11px] text-muted/50">/</span>}
                <span
                  className={cn(
                    "truncate text-[12.5px]",
                    index === crumbs.length - 1 ? "font-medium text-ink" : "text-muted",
                  )}
                >
                  {crumb}
                </span>
              </span>
            ))}
          </nav>
          <div className="ml-auto flex items-center gap-2">
            <ThemeToggle />
            <span
              className="hidden size-8 place-items-center rounded-full bg-primary-soft text-[11px] font-semibold text-primary sm:grid"
              title={user.email}
            >
              {initials(user.full_name || user.email)}
            </span>
          </div>
        </header>

        <main
          id="content"
          className="mx-auto w-full max-w-[1220px] animate-rise px-4 pb-28 pt-6 sm:px-6 lg:px-8 lg:pb-12 lg:pt-7"
        >
          {children}
        </main>
      </div>

      {/* ---------------- Mobile tab bar ---------------- */}
      <nav
        aria-label="Mobile"
        className="fixed inset-x-3 bottom-3 z-40 flex items-center justify-around rounded-xl border border-line bg-surface/95 p-1.5 shadow-e2 backdrop-blur-md lg:hidden"
      >
        {NAV.map((item) => {
          const active =
            pathname === item.href ||
            (item.href !== "/dashboard" && pathname.startsWith(item.href));
          return (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                "flex min-w-20 flex-col items-center gap-1 rounded-lg px-3 py-1.5 text-[10.5px] font-medium transition-colors",
                active ? "bg-primary-soft text-primary" : "text-muted",
              )}
            >
              <item.icon className="size-4.5" />
              {item.label}
            </Link>
          );
        })}
        <button
          type="button"
          onClick={signOut}
          className="flex min-w-20 flex-col items-center gap-1 rounded-lg px-3 py-1.5 text-[10.5px] font-medium text-muted"
        >
          <LogOut className="size-4.5" />
          Sign out
        </button>
      </nav>
    </div>
  );
}
