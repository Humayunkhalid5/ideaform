"use client";

import Link from "next/link";
import { useId } from "react";

import { APP_NAME } from "@/lib/constants";
import { cn } from "@/lib/utils";

/*
 * The IdeaForm mark, traced from the brand sheet: a hexagon drawn as one continuous line
 * that folds into a leaf across the top, an S-strand with a teardrop on the left, a light
 * bulb with a screw base in the middle and a pointed strand on the right.
 *
 * At rest it is one colour (currentColor). On hover of the nearest `.group` the
 * copper-to-teal line draws itself over it, like a filament lighting up.
 */
const PATHS = [
  // hexagon: upper-left corner, top, right side, down to the bottom-right point
  "M11 29.5Q9.6 25.6 13.4 23.6L46.4 6.6Q50 4.8 53.6 6.6L88.6 24.6Q92.4 26.6 92.4 31V75.4Q92.4 79.6 88.6 81.6L69.4 93.6",
  // left: S-strand into the teardrop, back up to the sharp point, down the left edge, along the bottom
  "M11 29.5C17 37 16.2 50 18.4 61.4C20.4 71.6 25.2 79.6 29.6 76.6C32.4 74.6 28.6 68.4 23 62L7.4 42.4V74.8Q7.4 79 11.2 81L46.2 96.4Q50.6 98.2 54.4 95.8",
  // leaf across the top, ending in the small drop
  "M88.6 29.4C76 20.4 60 17.6 46.4 21.8C37.4 24.6 26.4 28.8 21 34.6C18.2 37.8 20.6 41.8 24.8 39.8C31 36.8 37 32 41.6 27.4",
  // leaf returning under itself to the top of the bulb
  "M88.6 29.4C86.4 35.4 79 38 68 38.2C60 38.4 54 37.8 50 38",
  // bulb
  "M44.6 80.6V77.4C44.6 72 39 68.8 36.2 66.3A17.5 17.5 0 1 1 63.8 66.3C61 68.8 55.4 72 55.4 77.4V80.6",
  // screw base: neck, zig and the turn into the bottom of the hexagon
  "M44.6 80.6H55.4M43.8 85.6H53.6Q57.4 85.6 57 89.4Q56.6 92.6 54.4 95.8",
  // right inner strand coming down to the point at the bottom
  "M80.6 36.6C83.6 48 81 59.6 75.4 69.4C71.4 76.6 69 85.4 69.4 93.6",
];

export function BrandMark({ className, animated = true }: { className?: string; animated?: boolean }) {
  const gid = useId().replace(/:/g, "");
  return (
    <svg
      viewBox="0 0 100 100"
      fill="none"
      strokeWidth={3.6}
      strokeLinecap="round"
      strokeLinejoin="round"
      className={cn("size-8", className)}
      aria-hidden="true"
    >
      <defs>
        <linearGradient id={`${gid}-g`} x1="30" y1="6" x2="72" y2="96" gradientUnits="userSpaceOnUse">
          <stop offset="0%" stopColor="var(--if-brand-copper)" />
          <stop offset="42%" stopColor="var(--if-brand-copper)" />
          <stop offset="78%" stopColor="var(--if-brand-teal)" />
          <stop offset="100%" stopColor="var(--if-brand-teal)" />
        </linearGradient>
      </defs>
      {/* resting state: one colour */}
      <g
        stroke="currentColor"
        className={cn(animated && "transition-opacity duration-500 ease-out-soft group-hover:opacity-0")}
      >
        {PATHS.map((d) => (
          <path key={d} d={d} pathLength={1} />
        ))}
      </g>
      {/* hover state: the brand gradient draws itself along the line */}
      {animated && (
        <g stroke={`url(#${gid}-g)`}>
          {PATHS.map((d) => (
            <path
              key={d}
              d={d}
              pathLength={1}
              strokeDasharray="1 1"
              className="[stroke-dashoffset:1] transition-[stroke-dashoffset] duration-700 ease-out-soft group-hover:[stroke-dashoffset:0]"
            />
          ))}
        </g>
      )}
    </svg>
  );
}

/** Icon-only logo. The name stays available to screen readers. */
export function Logo({
  href = "/",
  className,
  size = "size-9",
}: {
  href?: string;
  className?: string;
  size?: string;
  /** kept for older call sites; the logo is icon-only now */
  showName?: boolean;
}) {
  return (
    <Link
      href={href}
      aria-label={`${APP_NAME} home`}
      title={APP_NAME}
      className={cn(
        "group inline-flex items-center rounded-lg text-ink transition-transform duration-150 active:scale-95",
        className,
      )}
    >
      <BrandMark className={size} />
    </Link>
  );
}
