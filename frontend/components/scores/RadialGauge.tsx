"use client";

import { useEffect, useId, useState } from "react";

import { cn } from "@/lib/utils";

export function scoreTone(score: number): { label: string; color: string } {
  if (score >= 80) return { label: "Strong", color: "var(--if-success)" };
  if (score >= 60) return { label: "Good", color: "var(--if-accent)" };
  if (score >= 40) return { label: "Mixed", color: "var(--if-warning)" };
  return { label: "Weak", color: "var(--if-danger)" };
}

export function RadialGauge({
  value,
  size = 132,
  stroke = 10,
  label,
  suffix = "",
  className,
}: {
  value: number;
  size?: number;
  stroke?: number;
  label?: string;
  suffix?: string;
  className?: string;
}) {
  const gradientId = useId();
  const [shown, setShown] = useState(0);
  const clamped = Math.max(0, Math.min(100, value));

  useEffect(() => {
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
      setShown(clamped);
      return;
    }
    let frame = 0;
    const start = performance.now();
    const duration = 900;
    const tick = (now: number) => {
      const progress = Math.min(1, (now - start) / duration);
      const eased = 1 - Math.pow(1 - progress, 3);
      setShown(clamped * eased);
      if (progress < 1) frame = requestAnimationFrame(tick);
    };
    frame = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(frame);
  }, [clamped]);

  const radius = (size - stroke) / 2;
  const circumference = 2 * Math.PI * radius;
  const tone = scoreTone(clamped);

  return (
    <div
      className={cn("relative grid shrink-0 place-items-center", className)}
      style={{ width: size, height: size }}
    >
      <svg
        width={size}
        height={size}
        role="img"
        aria-label={`${label ?? "Score"}: ${Math.round(clamped)} out of 100, ${tone.label}`}
      >
        <defs>
          <linearGradient id={gradientId} x1="0" y1="0" x2="1" y2="1">
            <stop offset="0%" stopColor="var(--if-primary)" />
            <stop offset="100%" stopColor={tone.color} />
          </linearGradient>
        </defs>
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke="var(--if-border)"
          strokeWidth={stroke}
        />
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke={`url(#${gradientId})`}
          strokeWidth={stroke}
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={circumference - (shown / 100) * circumference}
          transform={`rotate(-90 ${size / 2} ${size / 2})`}
        />
      </svg>
      <div className="absolute flex flex-col items-center">
        <span className="font-display text-[26px] font-semibold tabular leading-none">
          {Math.round(shown)}
          {suffix}
        </span>
        {label && (
          <span className="mt-1 text-[10px] uppercase tracking-[0.14em] text-if-muted">
            {label}
          </span>
        )}
      </div>
    </div>
  );
}
