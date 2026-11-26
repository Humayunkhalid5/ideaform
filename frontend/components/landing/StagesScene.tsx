"use client";

import { useRef } from "react";

import { clamp01, easeInOutCubic, useScrollScene } from "./useScrollScene";

export interface Stage {
  title: string;
  body: string;
}

const STEP_DEG = 36; // angle between faces of the drum

/**
 * The five stages as words on a turning drum. Scrolling turns it one face at a time (each
 * face holds for a moment, then rolls on); the copy for the face in front cross-fades.
 */
export function StagesScene({ stages }: { stages: Stage[] }) {
  const sceneRef = useRef<HTMLElement>(null);
  const last = stages.length - 1;

  useScrollScene(sceneRef, (p, el) => {
    const x = p * last;
    const base = Math.min(Math.floor(x), last);
    // hold on each face for the first and last quarter of its slot
    const a = base + easeInOutCubic(clamp01((x - base - 0.25) / 0.5));
    el.style.setProperty("--a", a.toFixed(4));
    el.style.setProperty("--p", p.toFixed(4));
    const active = String(Math.round(a));
    if (el.dataset.active !== active) el.dataset.active = active;
    el.querySelectorAll<HTMLElement>(".drum-face").forEach((face, k) => {
      face.style.opacity = (1 - Math.min(1, Math.abs(k - a)) * 0.82).toFixed(3);
    });
  });

  return (
    <section ref={sceneRef} id="stages" className="stages-scene" data-active="0" aria-labelledby="stages-title">
      <div className="stages-stage">
        <div className="mx-auto grid h-full w-full max-w-[1180px] grid-rows-[auto_1fr_auto] px-5 py-[max(5.5rem,12vh)] sm:px-8">
          <div className="flex items-end justify-between gap-6">
            <div>
              <p className="t-label text-primary">How it works</p>
              <h2 id="stages-title" className="t-section mt-1.5 max-w-[22ch] text-ink">
                Five stages, one versioned record of your idea.
              </h2>
            </div>
            <div className="stages-rail" aria-hidden="true">
              <span className="stages-rail-fill" />
            </div>
          </div>

          <div className="stages-drum-wrap" aria-hidden="true">
            <div className="stages-drum">
              {stages.map((stage, k) => (
                <span
                  key={stage.title}
                  className="drum-face"
                  style={{ "--k": k, "--step": `${STEP_DEG}deg` } as React.CSSProperties}
                >
                  {stage.title}
                </span>
              ))}
            </div>
          </div>

          <ol className="stages-copy">
            {stages.map((stage, k) => (
              <li key={stage.title} data-k={k} className="stage-copy">
                <span className="font-mono text-[12px] text-muted">
                  0{k + 1} / 0{stages.length}
                </span>
                <h3 className="t-title text-ink">{stage.title}</h3>
                <p className="max-w-[52ch] text-[14px] leading-relaxed text-muted">{stage.body}</p>
              </li>
            ))}
          </ol>
        </div>
      </div>
    </section>
  );
}
