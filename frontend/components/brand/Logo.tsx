import Link from "next/link";

import { APP_NAME } from "@/lib/constants";
import { cn } from "@/lib/utils";

export function BrandMark({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 32 32" className={cn("size-8", className)} aria-hidden="true">
      <defs>
        <linearGradient id="if-mark" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0%" stopColor="#4F46E5" />
          <stop offset="100%" stopColor="#7C3AED" />
        </linearGradient>
      </defs>
      <rect width="32" height="32" rx="9" fill="url(#if-mark)" />
      <path
        d="M16 7 17.9 13.4 24 16 17.9 18.6 16 25 14.1 18.6 8 16 14.1 13.4Z"
        fill="#FFFFFF"
        opacity="0.95"
      />
      <circle cx="16" cy="16" r="1.9" fill="url(#if-mark)" />
    </svg>
  );
}

export function Logo({
  href = "/",
  className,
  showName = true,
}: {
  href?: string;
  className?: string;
  showName?: boolean;
}) {
  return (
    <Link href={href} className={cn("inline-flex items-center gap-2.5", className)}>
      <BrandMark className="size-[30px]" />
      {showName && (
        <span className="text-[16px] font-semibold tracking-[-0.02em] text-ink">{APP_NAME}</span>
      )}
    </Link>
  );
}
