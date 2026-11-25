"use client";

import { Lock } from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";

import { cn } from "@/lib/utils";

const LOCKED = [
  "Research",
  "Evaluation",
  "Blueprint",
  "Versions",
  "Documents",
  "Export",
];

export function ProjectTabs({ projectId }: { projectId: string }) {
  const pathname = usePathname();
  const base = `/projects/${projectId}`;
  const tabs = [
    { href: base, label: "Overview", exact: true },
    { href: `${base}/understand`, label: "Understanding", exact: false },
  ];

  return (
    <div
      className="no-scrollbar -mb-px flex items-center gap-1 overflow-x-auto border-b border-line"
      role="tablist"
      aria-label="Project sections"
    >
      {tabs.map((tab) => {
        const active = tab.exact ? pathname === tab.href : pathname.startsWith(tab.href);
        return (
          <Link
            key={tab.href}
            href={tab.href}
            role="tab"
            aria-selected={active}
            className={cn(
              "relative inline-flex h-11 items-center gap-1.5 whitespace-nowrap px-3 text-[13.5px] font-medium transition-colors",
              active ? "text-primary" : "text-muted hover:text-ink",
            )}
          >
            {tab.label}
            <span
              className={cn(
                "absolute inset-x-2 -bottom-px h-[2px] rounded-full bg-primary transition-opacity",
                active ? "opacity-100" : "opacity-0",
              )}
            />
          </Link>
        );
      })}

      {LOCKED.map((label) => (
        <span
          key={label}
          aria-disabled="true"
          title="Available in a later phase"
          className="inline-flex h-11 cursor-not-allowed items-center gap-1.5 whitespace-nowrap px-3 text-[13.5px] text-muted/55"
        >
          {label}
          <Lock className="size-3" />
        </span>
      ))}
    </div>
  );
}
