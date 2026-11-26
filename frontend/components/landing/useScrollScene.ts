"use client";

import { useEffect, type RefObject } from "react";

export const clamp01 = (v: number) => Math.min(1, Math.max(0, v));
/** progress of `p` through the window [a, b], clamped to 0..1 */
export const span = (p: number, a: number, b: number) => clamp01((p - a) / (b - a));
export const easeInCubic = (t: number) => t * t * t;
export const easeOutCubic = (t: number) => 1 - Math.pow(1 - t, 3);
export const easeInOutCubic = (t: number) => (t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2);

export function prefersReducedMotion(): boolean {
  return typeof window !== "undefined" && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
}

/**
 * Calls `update(progress, el)` on every animation frame in which the page scrolled, where
 * progress is how far the sticky scene `el` has been scrolled through (0 at its top, 1 when
 * its end reaches the bottom of the viewport). One listener, one rAF, no layout writes:
 * `update` should only set CSS custom properties or attributes.
 * Does nothing when the user prefers reduced motion (the CSS then shows the static layout).
 */
export function useScrollScene(
  ref: RefObject<HTMLElement | null>,
  update: (progress: number, el: HTMLElement) => void,
) {
  useEffect(() => {
    const el = ref.current;
    if (!el || prefersReducedMotion()) return;

    let frame = 0;
    let visible = true;
    const measure = () => {
      frame = 0;
      const rect = el.getBoundingClientRect();
      const total = rect.height - window.innerHeight;
      update(total > 0 ? clamp01(-rect.top / total) : 0, el);
    };
    const schedule = () => {
      if (visible && !frame) frame = requestAnimationFrame(measure);
    };

    // stop work while the scene is far off screen
    const io = new IntersectionObserver(([entry]) => {
      visible = entry.isIntersecting;
      if (visible) schedule();
    }, { rootMargin: "50% 0px" });
    io.observe(el);

    measure();
    window.addEventListener("scroll", schedule, { passive: true });
    window.addEventListener("resize", schedule);
    return () => {
      io.disconnect();
      window.removeEventListener("scroll", schedule);
      window.removeEventListener("resize", schedule);
      cancelAnimationFrame(frame);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);
}

/** Pointer position over `el` as --mx / --my in -1..1 (fine pointers only). */
export function usePointerTilt(ref: RefObject<HTMLElement | null>) {
  useEffect(() => {
    const el = ref.current;
    if (!el || prefersReducedMotion() || !window.matchMedia("(pointer: fine)").matches) return;
    let frame = 0;
    let x = 0;
    let y = 0;
    const apply = () => {
      frame = 0;
      el.style.setProperty("--mx", x.toFixed(3));
      el.style.setProperty("--my", y.toFixed(3));
    };
    const onMove = (event: PointerEvent) => {
      const rect = el.getBoundingClientRect();
      x = ((event.clientX - rect.left) / rect.width) * 2 - 1;
      y = ((event.clientY - rect.top) / rect.height) * 2 - 1;
      if (!frame) frame = requestAnimationFrame(apply);
    };
    const onLeave = () => {
      x = 0;
      y = 0;
      if (!frame) frame = requestAnimationFrame(apply);
    };
    el.addEventListener("pointermove", onMove);
    el.addEventListener("pointerleave", onLeave);
    return () => {
      el.removeEventListener("pointermove", onMove);
      el.removeEventListener("pointerleave", onLeave);
      cancelAnimationFrame(frame);
    };
  }, [ref]);
}
