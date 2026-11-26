"use client";

import { useEffect } from "react";

const TARGET = ".if-card, [data-fx], [data-reveal]";
const LIGHT_TARGET = ".if-card, [data-fx]";

/**
 * One listener for the whole app (see app/motion.css):
 * - cursor light: sets --px/--py (and --mx/--my for [data-tilt]) on the hovered card;
 * - reveal: cards fade and rise in when they first enter the viewport, staggered.
 * Nothing runs under prefers-reduced-motion; content is never hidden without JS.
 */
export function MotionFX() {
  useEffect(() => {
    const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (reduce) return;
    const root = document.documentElement;

    // ---- reveal on entering the viewport
    let batch = 0;
    let batchTimer = 0;
    const io = new IntersectionObserver(
      (entries) => {
        for (const entry of entries) {
          if (!entry.isIntersecting) continue;
          const el = entry.target as HTMLElement;
          el.style.setProperty("--fx-delay", `${Math.min(batch, 8) * 70}ms`);
          el.dataset.shown = "";
          batch += 1;
          io.unobserve(el);
        }
        window.clearTimeout(batchTimer);
        batchTimer = window.setTimeout(() => (batch = 0), 120);
      },
      { rootMargin: "0px 0px -6% 0px", threshold: 0.04 },
    );
    const watch = (node: ParentNode) => {
      node.querySelectorAll<HTMLElement>(TARGET).forEach((el) => {
        if (!("shown" in el.dataset) && !el.dataset.fxWatched) {
          el.dataset.fxWatched = "";
          io.observe(el);
        }
      });
    };
    root.classList.add("fx-ready");
    watch(document);
    const mo = new MutationObserver((mutations) => {
      for (const m of mutations) {
        m.addedNodes.forEach((n) => {
          if (n instanceof HTMLElement) {
            if (n.matches(TARGET) && !n.dataset.fxWatched) {
              n.dataset.fxWatched = "";
              io.observe(n);
            }
            watch(n);
          }
        });
      }
    });
    mo.observe(document.body, { childList: true, subtree: true });

    // ---- cursor light and tilt (fine pointers only)
    const fine = window.matchMedia("(pointer: fine)").matches;
    let hot: HTMLElement | null = null;
    let frame = 0;
    let last: PointerEvent | null = null;
    const apply = () => {
      frame = 0;
      if (!last) return;
      const el = (last.target as Element | null)?.closest<HTMLElement>(LIGHT_TARGET) ?? null;
      if (el !== hot) {
        if (hot) {
          delete hot.dataset.hot;
          hot.style.setProperty("--mx", "0");
          hot.style.setProperty("--my", "0");
        }
        hot = el;
        if (hot) hot.dataset.hot = "";
      }
      if (!hot) return;
      const r = hot.getBoundingClientRect();
      const x = (last.clientX - r.left) / r.width;
      const y = (last.clientY - r.top) / r.height;
      hot.style.setProperty("--px", `${(x * 100).toFixed(1)}%`);
      hot.style.setProperty("--py", `${(y * 100).toFixed(1)}%`);
      if (hot.hasAttribute("data-tilt")) {
        hot.style.setProperty("--mx", (x * 2 - 1).toFixed(3));
        hot.style.setProperty("--my", (y * 2 - 1).toFixed(3));
      }
    };
    const onMove = (e: PointerEvent) => {
      last = e;
      if (!frame) frame = requestAnimationFrame(apply);
    };
    const onLeave = () => {
      if (hot) {
        delete hot.dataset.hot;
        hot.style.setProperty("--mx", "0");
        hot.style.setProperty("--my", "0");
        hot = null;
      }
    };
    if (fine) {
      document.addEventListener("pointermove", onMove, { passive: true });
      document.addEventListener("pointerleave", onLeave);
    }

    return () => {
      io.disconnect();
      mo.disconnect();
      root.classList.remove("fx-ready");
      document.removeEventListener("pointermove", onMove);
      document.removeEventListener("pointerleave", onLeave);
      cancelAnimationFrame(frame);
      window.clearTimeout(batchTimer);
    };
  }, []);
  return null;
}
