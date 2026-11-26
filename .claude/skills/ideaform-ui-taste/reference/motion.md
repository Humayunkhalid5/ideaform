# Motion for IdeaForm

## Why anything moves

Each animation must answer one of these, or it is cut:

- **Feedback:** the control heard you (hover, press, focus, toggle).
- **Continuity:** something changed place or state and the eye should follow it (tab indicator,
  drawer opening, item added or removed, a score updating).
- **Progress:** work is happening (skeleton shimmer, pipeline step running, spinner).
- **Arrival:** a Showcase screen or a finished result appears once (hero entrance, gauge fill on
  first view, export success).

Content must be complete and readable at rest, without JavaScript and with reduced motion on.
Motion only adds on top.

## Where motion goes, by tier

| Tier | Motion |
| --- | --- |
| Showcase | one entrance on load (~350–700ms total, once), one focal animated element, hover layer |
| Product | hover/press layer, state transitions, gauge count-up once, skeletons; at most a single short `animate-rise` for the page body |
| Utility | hover/press layer and state transitions only |

Never: a reveal on every card as you scroll, staggered rows in tables, parallax, scroll-jacking or
smooth-scroll libraries, tilt on data cards, shine sweeps, bouncing, looping decoration with no
meaning, a second entrance when you navigate back.

## Timing and easing

| Use | Duration | Tailwind |
| --- | --- | --- |
| Hover in (colour, lift) | 150ms | `duration-150` |
| Hover out / close | 120ms | `duration-[120ms]` |
| Press | 90ms | `active:duration-75` |
| Popover / menu / tooltip open | 160–200ms | `duration-200` |
| Drawer, dialog, tab indicator travel | 200–240ms | `duration-200` / `duration-[240ms]` |
| Entrance (element arriving) | 350ms | `animate-rise` |
| Gauge fill / number count-up | 900ms, once | `RadialGauge` already does this |
| Loops (shimmer, indeterminate bar) | 1.2–1.6s linear | `animate-shimmer`, `animate-bar` |

Easing: ease-out for anything entering or responding (`ease-out`, or the project curve
`ease-[cubic-bezier(0.22,1,0.36,1)]` already used by `rise`); `ease-in-out` only for something
travelling between two points; `linear` only for loops. No overshoot or spring bounce on
Product screens.

If you need these more than twice, add tokens to `@theme inline` in `globals.css`, e.g.
`--ease-out-soft: cubic-bezier(0.22, 1, 0.36, 1);` (gives `ease-out-soft`) and new keyframes with
`--animate-*`, rather than repeating arbitrary values.

## Distances

Small and consistent: card lift `-translate-y-0.5` (2px), button press `active:scale-[0.98]`,
arrow nudge `translate-x-0.5`, popover drop 4–6px, entrance rise 8px (the `rise` keyframe).
Nothing grows, shifts its neighbours, or resizes its box on hover.

## Properties

Animate `transform`, `opacity`, `color`, `background-color`, `border-color`, `box-shadow`
(sparingly), `stroke-dashoffset` for SVG. Avoid `transition-all`; name the properties
(`transition-colors`, `transition-transform`, `transition-[transform,box-shadow]`). Never animate
`width`, `height`, `max-height`, `top/left`, `margin`, `padding`. For a progress bar use
`scale-x` with `origin-left`, not width.

## Patterns (CSS / Tailwind first)

Hover layer on a clickable card:

```tsx
<Link
  href={href}
  className="if-card block p-5 transition-[transform,box-shadow,border-color] duration-150 ease-out
             hover:-translate-y-0.5 hover:shadow-e2 motion-reduce:hover:translate-y-0
             focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary"
>
```

Button press (extend `base` in `components/ui/button.tsx` instead of per-call):

```ts
"transition-[color,background-color,transform] duration-150 active:scale-[0.98] motion-reduce:active:scale-100"
```

Entrance of a page body or a result that just loaded (once):

```tsx
<section className="animate-rise motion-reduce:animate-none">…</section>
```

For a short stagger in a Showcase hero (three or four items, not lists), set
`style={{ animationDelay: `${i * 60}ms` }}` on `animate-rise` elements; keep total under 400ms.

Popover/menu open without a library: render it always, toggle state classes.

```tsx
<div
  data-open={open}
  className="pointer-events-none translate-y-1 opacity-0 transition-[opacity,transform] duration-200 ease-out
             data-[open=true]:pointer-events-auto data-[open=true]:translate-y-0 data-[open=true]:opacity-100"
/>
```

Height changes (accordion, expanding log): use the CSS grid trick instead of animating height:

```tsx
<div className="grid transition-[grid-template-rows] duration-200 ease-out data-[open=true]:grid-rows-[1fr] grid-rows-[0fr]" data-open={open}>
  <div className="overflow-hidden">…</div>
</div>
```

(`grid-template-rows` is the one layout-ish property allowed, because it doesn't thrash layout
like `height: auto` hacks; keep it to small panels.)

Loading: skeletons with `animate-shimmer` (see `components/ui/skeleton.tsx`) that match the
final layout; spinners (`animate-spin` on a lucide `Loader2`) only inside buttons or inline
status, 16px.

Route changes: Next.js 15 has no stable view transitions; don't fake page transitions. Let the
new page's content use `animate-rise` once if it is a Showcase screen.

## Charts and numbers

- `RadialGauge` already counts up over 900ms and jumps to the value under reduced motion. Reuse
  it; copy its `matchMedia` pattern for any other count-up.
- Recharts animates by default. Keep `animationDuration` around 600–800ms with
  `animationEasing="ease-out"`, and pass `isAnimationActive={!reduce}`. Don't re-animate on
  every re-render: memoise data so the chart doesn't replay.
- Numbers that update live (token counters, sources found) change in place with `tabular`; no
  rolling digits on Product screens.

## Reduced motion

`globals.css` already ends at the bottom with a global rule that cuts every animation and
transition to 0.01ms under `prefers-reduced-motion: reduce`. That is the safety net, not the
whole job:

- Anything that starts hidden (`opacity-0`) must still end visible: the `rise` keyframe uses
  `both`, so it lands on its final frame. Check your own keyframes do too.
- Movement becomes nothing or a plain fade; colour and opacity changes may stay.
- Use Tailwind variants: `motion-safe:` to opt in to movement, `motion-reduce:` to turn it off.
- In JS (count-ups, Recharts, canvas): read the preference.

```tsx
"use client";
import { useSyncExternalStore } from "react";

const query = "(prefers-reduced-motion: reduce)";
export function usePrefersReducedMotion() {
  return useSyncExternalStore(
    (cb) => {
      const m = window.matchMedia(query);
      m.addEventListener("change", cb);
      return () => m.removeEventListener("change", cb);
    },
    () => window.matchMedia(query).matches,
    () => false,
  );
}
```

If a hook like this is needed in more than one place, put it in `frontend/lib/` once.

- Anything that loops for more than ~5 seconds and isn't a loading indicator needs a pause
  control, or shouldn't loop.

## When to add the `motion` library

CSS covers almost everything here. Add `motion` (the successor of framer-motion; `npm i motion`
in `frontend/`, `import { motion, AnimatePresence, useReducedMotion } from "motion/react"`) only
for:

- a shared indicator that slides between tabs or nav items (`layoutId`), e.g. `ProjectTabs`;
- exit animations when items leave a list or a dialog unmounts (`AnimatePresence`);
- layout animation of reordering items (`layout` prop);
- gesture- or spring-driven interaction (drag to reorder).

Rules when it is used: ask the user before adding the dependency; only in `"use client"`
components; pass `transition={{ duration: 0.2, ease: [0.22, 1, 0.36, 1] }}` (no bouncy springs on
Product screens); honour `useReducedMotion()` by dropping `x/y/scale` and keeping opacity; keep
server components free of it. Don't use it for simple hover or entrance effects that CSS does.

Never add GSAP, Lottie, Three.js scenes, smooth-scroll libraries or animation-on-scroll
libraries for Product or Utility screens.
