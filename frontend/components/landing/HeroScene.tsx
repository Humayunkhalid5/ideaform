"use client";

import { ArrowRight } from "lucide-react";
import Link from "next/link";
import { useRef } from "react";

import { buttonStyles } from "@/components/ui/button";
import { APP_NAME } from "@/lib/constants";

import {
  easeInCubic,
  easeOutCubic,
  span,
  usePointerTilt,
  useScrollScene,
} from "./useScrollScene";

const WORD = APP_NAME.toUpperCase(); // IDEAFORM
const HALVES = [WORD.slice(0, 4), WORD.slice(4)];

function Letters({ depth = false }: { depth?: boolean }) {
  return (
    <span className={depth ? "hero-word hero-word--depth" : "hero-word"} aria-hidden="true">
      {HALVES.map((half, h) => (
        <span key={half} className="hero-half">
          {half.split("").map((char, j) => {
            const i = h * 4 + j;
            return (
              <span key={i} className="hero-letter" style={{ "--i": i } as React.CSSProperties}>
                <span className="hero-letter-in">{char}</span>
              </span>
            );
          })}
        </span>
      ))}
    </span>
  );
}

/**
 * Scroll-driven hero. The name fills the screen; scrolling flies the letters past the
 * camera (each at its own depth and angle), and the statement behind them comes forward.
 * All movement is CSS transforms fed by four custom properties set once per frame.
 */
export function HeroScene() {
  const sceneRef = useRef<HTMLElement>(null);
  const stageRef = useRef<HTMLDivElement>(null);

  useScrollScene(sceneRef, (p, el) => {
    const s = el.style;
    s.setProperty("--fly", easeInCubic(span(p, 0, 0.82)).toFixed(4));
    s.setProperty("--fade", (1 - span(p, 0.42, 0.74)).toFixed(4));
    s.setProperty("--reveal", easeOutCubic(span(p, 0.38, 0.82)).toFixed(4));
    s.setProperty("--chrome", (1 - span(p, 0, 0.14)).toFixed(4));
    s.setProperty("--p", p.toFixed(4));
    el.toggleAttribute("data-revealed", p > 0.6);
  });
  usePointerTilt(stageRef);

  return (
    <section ref={sceneRef} className="hero-scene" aria-labelledby="hero-title">
      <div ref={stageRef} className="hero-stage">
        <div className="hero-light" aria-hidden="true" />
        <div className="hero-grain" aria-hidden="true" />

        {/* the statement waiting behind the type */}
        <div className="hero-reveal">
          <p className="t-label text-brand-copper">The intelligent idea workstation</p>
          <h2 className="mt-4 max-w-[17ch] text-balance text-[clamp(2rem,5.4vw,4.4rem)] font-semibold leading-[1.02] tracking-[-0.035em] text-ink">
            Describe it once. Leave with evidence, scores and a plan.
          </h2>
          <p className="mx-auto mt-5 max-w-[46ch] text-[15px] leading-relaxed text-muted">
            {APP_NAME} reads your idea, researches it, scores it on six dimensions with cited
            sources, and shows you exactly what changes when you improve it.
          </p>
          <div className="mt-8 flex flex-wrap items-center justify-center gap-3">
            <Link href="/register" className={buttonStyles("primary", "lg")}>
              Start a project <ArrowRight className="size-4" />
            </Link>
            <a href="#stages" className={buttonStyles("secondary", "lg")}>
              See the stages
            </a>
          </div>
        </div>

        {/* the name, in two layers for depth */}
        <h1 id="hero-title" className="hero-type">
          <span className="sr-only">{APP_NAME}: the intelligent idea workstation</span>
          <span className="hero-tilt">
            <Letters depth />
            <Letters />
          </span>
        </h1>

        {/* chrome that steps aside once you scroll */}
        <div className="hero-chrome">
          <p className="max-w-[30ch] text-[13.5px] leading-relaxed text-muted">
            From a rough paragraph to a plan you can defend, with every claim pointing at its
            source.
          </p>
          <div className="hero-scroll" aria-hidden="true">
            <span>Scroll</span>
            <span className="hero-scroll-line" />
          </div>
          <Link href="/register" className={buttonStyles("primary", "md")}>
            Start free <ArrowRight className="size-4" />
          </Link>
        </div>
      </div>
    </section>
  );
}
