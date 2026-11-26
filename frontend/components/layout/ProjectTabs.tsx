"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useLayoutEffect, useRef } from "react";

import { cn } from "@/lib/utils";

const useIsoLayoutEffect = typeof window === "undefined" ? useEffect : useLayoutEffect;

export function ProjectTabs({ projectId }: { projectId: string }) {
  const pathname = usePathname();
  const base = `/projects/${projectId}`;
  const listRef = useRef<HTMLDivElement>(null);
  const tabs = [
    { href: base, label: "Overview", exact: true },
    { href: `${base}/understand`, label: "Understanding", exact: false },
    { href: `${base}/research`, label: "Research", exact: false },
    { href: `${base}/evaluation`, label: "Evaluation", exact: false },
    { href: `${base}/compare`, label: "Compare", exact: false },
    { href: `${base}/blueprint`, label: "Blueprint", exact: false },
    { href: `${base}/documents`, label: "Documents", exact: false },
    { href: `${base}/versions`, label: "Versions", exact: false },
    { href: `${base}/export`, label: "Export", exact: false },
  ];
  const activeHref = tabs.find((t) => (t.exact ? pathname === t.href : pathname.startsWith(t.href)))?.href;

  // one indicator that slides to the active tab (transform only)
  useIsoLayoutEffect(() => {
    const list = listRef.current;
    const active = list?.querySelector<HTMLElement>('[aria-selected="true"]');
    if (!list || !active) return;
    const place = () => {
      list.style.setProperty("--tab-x", `${active.offsetLeft + 8}px`);
      list.style.setProperty("--tab-w", String((active.offsetWidth - 16) / 100));
    };
    place();
    active.scrollIntoView({ block: "nearest", inline: "nearest" });
    window.addEventListener("resize", place);
    return () => window.removeEventListener("resize", place);
  }, [activeHref]);

  return (
    <div
      ref={listRef}
      className="no-scrollbar relative -mb-px flex items-center gap-1 overflow-x-auto border-b border-line"
      role="tablist"
      aria-label="Project sections"
    >
      {tabs.map((tab) => {
        const active = tab.href === activeHref;
        return (
          <Link
            key={tab.href}
            href={tab.href}
            role="tab"
            aria-selected={active}
            className={cn(
              "relative inline-flex h-11 items-center gap-1.5 whitespace-nowrap px-3 text-[13.5px] font-medium transition-colors duration-200",
              active ? "text-primary" : "text-muted hover:text-ink",
            )}
          >
            {tab.label}
          </Link>
        );
      })}
      <span className="if-tab-indicator" aria-hidden="true" />
    </div>
  );
}
