import type { ComponentProps } from "react";

import { cn } from "@/lib/utils";

type Variant = "primary" | "secondary" | "glass" | "ghost" | "solid" | "danger";
type Size = "sm" | "md" | "lg";

const base =
  "inline-flex items-center justify-center gap-2 rounded-lg text-[14px] font-medium whitespace-nowrap transition-colors duration-150 select-none disabled:pointer-events-none disabled:opacity-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/45 focus-visible:ring-offset-2 focus-visible:ring-offset-canvas";

const variants: Record<Variant, string> = {
  primary: "bg-primary text-white shadow-sm hover:bg-primary-hover",
  secondary:
    "border border-line bg-surface text-ink shadow-sm hover:bg-surface-soft",
  glass: "border border-line bg-surface text-ink shadow-sm hover:bg-surface-soft",
  ghost: "text-muted hover:bg-surface-soft hover:text-ink",
  solid: "bg-ink text-canvas hover:opacity-90",
  danger: "border border-danger/30 bg-danger-soft text-danger hover:bg-danger/15",
};

const sizes: Record<Size, string> = {
  sm: "h-9 px-3 text-[13px]",
  md: "h-10 px-4",
  lg: "h-11 px-5",
};

export function buttonStyles(
  variant: Variant = "primary",
  size: Size = "md",
  className?: string,
): string {
  return cn(base, sizes[size], variants[variant], className);
}

export function Button({
  variant = "primary",
  size = "md",
  className,
  ...props
}: ComponentProps<"button"> & { variant?: Variant; size?: Size }) {
  return <button className={buttonStyles(variant, size, className)} {...props} />;
}
