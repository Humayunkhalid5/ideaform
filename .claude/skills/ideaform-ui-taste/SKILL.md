---
name: ideaform-ui-taste
description: >-
  Design taste and motion rules for the IdeaForm frontend (Next.js 15, React 19, Tailwind v4,
  lucide-react, Recharts in frontend/). Use whenever you design, build, redesign, restyle or
  polish a page, component, chart or layout in frontend/, when a screen looks generic,
  cluttered or "AI-made", and whenever you add or change animations, transitions, hover or
  press states, loading states or count-ups. Covers layout, typography, colour from the
  project tokens, components, motion and prefers-reduced-motion.
---

# IdeaForm UI taste

A working guide for making IdeaForm screens look deliberate rather than templated, and for
adding motion that helps instead of decorating. It adapts the ideas of
[taste-skill](https://github.com/Leonxlnx/taste-skill) by Leonxlnx (MIT licence) to this
codebase. That skill builds marketing websites with its own kit and checker scripts; this one
keeps only its principles and applies them to a data-heavy product app. See `CREDITS.md`.

## Sources of truth, in order

0. `DESIGN.md` (repo root): the project's design decisions: the icon-only logo and its sizes,
   brand colours, page tiers, motion per tier, how the landing scroll scenes work, and the
   checklist for when a phase ships. Read it first; it wins over everything below.
1. `frontend/app/globals.css`: the live tokens (`--if-*` variables, `@theme inline` mapping,
   type classes `t-hero` … `t-mono-xs`, surfaces `if-card`, `if-panel`, `if-glass`, `if-mesh`,
   keyframes `rise`, `shimmer`, `bar`, and the global reduced-motion rule).
2. Existing components in `frontend/components/` (`ui/button.tsx`, `ui/card.tsx`,
   `ui/badge.tsx`, `scores/RadialGauge.tsx`, …). Extend them; don't fork a second style.
3. `UI_BUILD_GUIDE.md`: product intent, page tiers, score and claim colours, accessibility.
   Where it disagrees with `globals.css` (it mentions Sora, 16px card radius, cyan accent,
   framer-motion, shadcn), **the code wins**: the built app uses Inter only, a 12px card
   radius, a teal accent, and no animation library.

Never hard-code a hex value or a new shadow in a component. If a token is missing, add it to
`globals.css` in both `:root` and `.dark`, then map it in `@theme inline`.

## Before you touch anything

Write three lines (in your head or the reply):

- **Tier** of the screen: Showcase, Product or Utility (`UI_BUILD_GUIDE.md` §2). This decides
  how much decoration and motion it may have.
- **The one job** of the screen and its **one primary action**.
- **What the user actually came to read** (a score, a list, a diff). That gets the space; chrome
  gets out of the way.

## Core rules

1. **One system.** One primary button style, one card style, one radius scale (`rounded-lg`
   controls, `rounded-card` or `if-card` for cards, `rounded-input` for fields), one link look, one icon set
   (lucide-react, 16px in text and buttons, 20px in headers, `strokeWidth` default). A second
   variant needs a reason.
2. **Hierarchy by size, weight and space, not by colour or boxes.** At most two boxes deep
   (a card inside a page section, never card in card in card). Prefer a divider or spacing over
   another border.
3. **Equal edges and a grid.** Content sits on the page container's left and right lines; grids
   use consistent gaps (`gap-4` / `gap-6`). Nothing drifts off to one side.
4. **Restraint with colour.** Neutrals carry the page; `primary` marks the one main action and
   the active state; status colours (`success`, `warning`, `danger`, `info`) only mean status.
   Never colour alone: pair with text or an icon (`UI_BUILD_GUIDE.md` §4.5).
5. **Real content.** Design with realistic data lengths (long idea titles, 0 and 100 scores,
   empty lists). No lorem ipsum, no fake testimonials or invented figures in shipped UI.
6. **Calm data, expressive edges.** Tables, evaluation text and documents stay flat and dense.
   Gradients, glass and mesh belong to Showcase screens and empty states only, never behind
   long text or tables.
7. **Every state designed.** Loading (skeleton matching the final layout), empty (what it is,
   one action), error (what happened, retry), and the long-text and narrow-screen cases.
8. **Copy is design.** Headings name things ("Evaluation scores", not "Overview"). Buttons are
   a verb plus an object ("Start analysis"). No filler sentences, no exclamation marks.

Details: `reference/layout-type-colour.md`.

## Motion in one paragraph

Motion explains a change; it never decorates a static page. Use **CSS and Tailwind transitions
first** (`transition-colors`, `transition-transform`, `duration-150`, the `animate-rise` /
`animate-shimmer` utilities already defined). Animate only `transform`, `opacity`, colour and
(sparingly) `clip-path`/`filter`; never `width`, `height`, `top/left`, `margin` or `padding`.
Keep UI feedback 120–200ms, panels 200–240ms, entrances about 350ms with the existing
`cubic-bezier(0.22, 1, 0.36, 1)` ease; no bounce or overshoot. No scroll-triggered fade-ins on
every card, no parallax, no scroll-jacking. Under `prefers-reduced-motion: reduce` everything
ends in its finished state and nothing stays hidden.

Add the `motion` package (`npm i motion`, import from `motion/react`) **only** for what CSS
can't do well: shared-layout indicators (`layoutId` tab underline), exit animations of items
removed from a list, or spring-driven gestures. Ask before adding it; one dependency, used in
client components only.

Details, tokens and code: `reference/motion.md`.

## Workflow

1. Read the target component/page and the tokens above. Look for an existing primitive first.
2. Sketch the hierarchy (tier, job, primary action), then build with tokens and type classes.
3. Add motion last, only where something changes state. Wire reduced motion.
4. Verify in the browser preview (light **and** dark, 1280 and 390 widths, keyboard Tab through,
   reduced motion emulated). Run `npm run build` in `frontend/`.
5. Walk the checklist in `reference/checklist.md` before saying it is done.

## Never

(Exception, by the user's decision: the **landing page** `/` is a scroll-driven 3D typography
showcase with section reveals and pointer tilt, built as described in `DESIGN.md` §7. Keep those
effects there only; the rules below hold for every other page.)

- New colours, fonts, radii or shadows outside `globals.css`.
- Glass, blur or gradient behind tables or paragraphs of analysis text.
- A fade/slide-in on every section or card as the page scrolls; parallax on text; tilt or
  3D hover on data cards; confetti on anything but a rare completion moment.
- Animating layout properties, or an animation that runs longer than ~1s on a Product screen.
- Information shown only by colour, or only on hover.
- Copying another product's look, copy or signature effect.
