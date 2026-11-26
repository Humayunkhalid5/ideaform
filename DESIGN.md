# IdeaForm design system

**This is the single source of truth for how IdeaForm looks and moves.** Every page in every
phase (Blueprint, Documents, Export, Settings, anything new) follows it. If this file, the code
and `UI_BUILD_GUIDE.md` disagree, the order is: **this file → `frontend/app/globals.css` →
existing components → `UI_BUILD_GUIDE.md`** (the guide is older and partly superseded; see §11).

Agents: also load the `ideaform-ui-taste` skill (`.claude/skills/ideaform-ui-taste/`) before UI
work. It has the detailed taste rules and the checklist; this file has the project decisions.

---

## 1. Brand

| Element | Rule |
| --- | --- |
| Name | `APP_NAME` from `frontend/lib/constants.ts`. Never type "IdeaForm" into JSX. |
| Lines | `TAGLINE` = "From Idea to Implementation". `BRAND_LINE` = "The intelligent idea workstation". |
| Mark | The line-drawn hexagon with the light bulb from the brand sheet. **Icon only, no wordmark next to it.** |
| Colours | Copper `--if-brand-copper`, teal `--if-brand-teal`, navy `--if-brand-navy`. Brand colours are for the mark, brand panels and showcase accents, never for status or data. |
| Wordmark | Only on the landing page, as the giant `IDEAFORM` typography (uppercase, weight 800). |

### The logo, everywhere

Use **only** `components/brand/Logo.tsx`:

```tsx
import { Logo, BrandMark } from "@/components/brand/Logo";

<Logo href="/dashboard" />            // clickable icon, aria-label "IdeaForm home"
<Logo href="/" size="size-10" />      // standalone pages
<BrandMark className="size-10 text-ink" animated={false} />  // non-link, e.g. loading screen
```

- **Sizes:** `size-9` (36px) in app chrome (sidebar), `size-8` in the mobile header, `size-10`
  (40px) on standalone pages (landing nav, sign-in/register, 404, error).
- **Colour at rest:** one colour, `currentColor`: `text-ink` on light surfaces, `text-white` on
  the navy brand panel. Never recolour the paths by hand.
- **Hover:** the copper→teal line draws itself over the mark (stroke-dashoffset, 700ms). This
  comes from the `group` class on `Logo`; for a bare `BrandMark`, put `group` on its parent.
- **Favicon:** `frontend/app/icon.svg`, generated from the same `PATHS`. If the mark changes,
  run `node scripts/gen-icon.mjs` in `frontend/`.
- Never: draw another logo, use a lucide icon (Sparkles, Lightbulb…) as the logo, put the mark
  in a coloured square, or add the word "IdeaForm" beside it.

## 2. Tokens (the only colours, radii and shadows)

All live in `frontend/app/globals.css` (`:root` and `.dark`, mapped in `@theme inline`).

| Use | Tailwind |
| --- | --- |
| Page / card / soft panel | `bg-canvas`, `bg-surface` / `if-card`, `bg-surface-soft` |
| Text | `text-ink` (primary), `text-muted` (secondary) |
| Lines | `border-line` |
| Primary action, active state, links | `primary`, `primary-hover`, `primary-soft` (indigo) |
| Accent (rare highlight) | `accent`, `accent-soft` (teal) |
| Status only | `success`, `warning`, `danger`, `info` (+ `-soft`) |
| Brand | `brand-copper`, `brand-teal`, `brand-navy` |
| Radius | `rounded-lg` controls, `if-card` / `rounded-xl` cards (12px), `rounded-input` fields |
| Shadow | `shadow-e1` … `shadow-e3`, focus `shadow-[var(--if-ring)]` |
| Easing | `ease-out-soft` (Tailwind) / `var(--if-ease)` (plain CSS) |

**Never** put a hex, `rgba()`, Tailwind palette colour (`emerald-300`, `indigo-500`, …) or a new
shadow in a component. Missing token → add it to `globals.css` (both themes) and map it.

Claim labels (Phase 3): `verified_fact` → success, `assumption` → warning, `ai_suggestion` →
info, always with the text label (`ClaimChip` in `components/evaluation/parts.tsx`).

## 3. Type

Inter only (400–800), JetBrains Mono for numbers, ids and code. Use the classes, not new sizes:

| Class | Use |
| --- | --- |
| `t-hero` 30px | page title on Showcase screens |
| `t-section` 24px | section heading |
| `t-title` 18px | card / panel title |
| `t-sub` 16px | sub-heading |
| `t-body` 14px | body text |
| `t-meta` 12px | meta lines |
| `t-label` 11px uppercase | eyebrow labels (`text-primary` or `text-muted`) |
| `t-mono`, `t-mono-xs` | numbers, versions, ids (tabular) |

Big marketing headings on the landing page use `clamp()` sizes with `tracking-[-0.03em]` to
`-0.045em`; nowhere else.

## 4. Page tiers

| Tier | Pages | Allowed |
| --- | --- | --- |
| **Showcase** | landing `/`, sign-in/register brand panel | brand colours, lighting, 3D, scroll scenes, big type |
| **Product** | dashboard, project overview, understanding, research, evaluation, compare, blueprint, documents | calm and flat; cards, tables, charts; motion only for feedback and state |
| **Utility** | settings, export, 404, error | plainest; tokens and components only |

Gradients, glass, mesh and brand lighting never go behind tables or paragraphs of analysis.

## 5. Layout and components

- App pages live inside `AppShell` (sidebar 248px, sticky header, `max-w-[1220px]` content).
  Project pages live inside `projects/[id]/layout.tsx` with `ProjectTabs`. A new project tab
  (Blueprint, Documents, Export) is added to `ProjectTabs.tsx` and unlocked there; do not build
  a second tab bar.
- Use the primitives: `Button` / `buttonStyles` (one primary per view), `Card`, `Badge`,
  `Field` / `Input` / `Select`, `PageSkeleton`, `EmptyState`, `ErrorNotice`, `RadialGauge`,
  `ConfidenceBadge`, `ClaimChip`, `DeltaChip`, `Disclaimer`. Extend them instead of restyling.
- Every page has: a loading skeleton shaped like the result, an empty state (what it is + one
  action), an error state (`ErrorNotice` with retry), long-text and 390px-wide behaviour.
- Icons: lucide-react, 16px in text and buttons, 20px in headers. `Sparkles` means "run the AI
  step" (Understand, Research, Evaluate, Improve, Generate); keep that meaning.
- Generated documents (Blueprint, later Export previews) use `MarkdownDoc` (GitHub-flavoured
  Markdown styled by `.if-doc` in `globals.css`) and `MermaidDiagram` (lazy-loaded Mermaid,
  `securityLevel: "strict"`, theme-aware, falls back to the source). Never render model HTML
  directly, and never let the model write diagram code that is shown unsanitised: build
  diagrams in the backend (`services/blueprint/render.py`).
- Long-running work starts a background run and sends the user to `/projects/{id}/run?run=…`.
  A full analysis shows `AnalysisProgress` (one row per agent step: status, retry, low
  confidence, time, link to the result); never block a page on a multi-minute request.
- Files are downloaded with `api.exportProject` (authenticated fetch + the server's file name);
  never put the token in a URL.
- Pages that call `useSearchParams` wrap their content in `<Suspense>`.
- Two boxes deep at most. Prefer dividers and spacing to another bordered card.

## 6. Motion

Motion explains a change; it never decorates a still page.

| Where | What |
| --- | --- |
| Everywhere | buttons press (`active:scale-[0.98]`, built into `buttonStyles`), colour transitions 150ms |
| Clickable cards | `hover:-translate-y-0.5 hover:shadow-e2 hover:border-primary/25`, 150ms |
| App content | one `animate-rise` on first load of `<main>` (in `AppShell`); never on tab change |
| Loading | `PageSkeleton` / `animate-shimmer`, `animate-bar` for indeterminate progress |
| Scores | `RadialGauge` count-up once |
| Logo | the hover draw-in (§1) |
| Landing only | scroll scenes (§7), one-time section `Reveal`, `TiltSurface` |

Rules: animate `transform`, `opacity`, colours and `stroke-dashoffset` only. 120–200ms for UI
feedback, ~350ms for entrances, `ease-out-soft`, no bounce. No scroll reveals, parallax or tilt
on Product pages. **Reduced motion:** the global rule in `globals.css` ends every animation in
its final state; scroll scenes switch to a static layout in their own
`@media (prefers-reduced-motion: reduce)` block. Nothing may stay hidden.

No animation library is installed. Do not add GSAP, Three.js or framer-motion/motion without
asking the user first; the landing page proves CSS + one rAF is enough.

## 7. The landing page (how it works, so it can be extended)

- `app/page.tsx` (server) composes `components/landing/*` and imports `app/landing.css`.
- `useScrollScene(ref, update)` gives a sticky scene its scroll progress 0..1 once per frame;
  `update` only writes CSS custom properties (`--fly`, `--fade`, `--reveal`, `--a`, `--p`).
  All visuals read those variables in `landing.css` through `transform` / `opacity`.
- `HeroScene`: the `IDEAFORM` letters (`--i` 0..7) fly past the camera, the statement behind
  them comes forward. `StagesScene`: stage names on a 3D drum, one face per stage. When a phase
  ships, edit the `stages` array in `app/page.tsx` (status `"Live"`).
- `Reveal` shows a whole section once; `TiltSurface` leans toward the pointer.
- Copy on the landing page must be true today. Example numbers are labelled "Example output".

## 8. Copy

- Headings name the thing ("Evaluation scores"), buttons are verb + object ("Run evaluation").
- No filler, no exclamation marks, no fake testimonials or invented metrics.
- Scores always carry the disclaimer: `DISCLAIMER` / the `Disclaimer` component.

## 9. When a phase ships (checklist)

1. `frontend/lib/constants.ts`: update `PRODUCT_STATUS` and `PRODUCT_STATUS_DETAIL` (sidebar
   card and sign-in panel read them).
2. `ProjectTabs.tsx`: unlock the new tab(s).
3. `projects/[id]/page.tsx`: set `path` on the phase card in `NEXT_PHASES`.
4. `app/page.tsx`: update the `stages` status and the footer note.
5. Search for stale text: `grep -rn "Phase [0-9]\|arrives\|later phase\|coming" frontend/app frontend/components`.
6. Build the new screens from §4–§6 with the existing primitives; then walk §10.

## 10. Done means

- [ ] Only tokens and the type classes; no hex / rgba / palette colours in components.
- [ ] Logo via `Logo` / `BrandMark` only, right size for the context.
- [ ] Loading, empty, error, long text and 390px states all work.
- [ ] Light and dark theme both checked.
- [ ] Keyboard: everything reachable, visible focus ring.
- [ ] Reduced motion: content complete and visible.
- [ ] `npx tsc --noEmit` and `npm run build` pass in `frontend/`.
- [ ] Checked in the browser at 1280px and 390px.

## 11. What changed from `UI_BUILD_GUIDE.md`

The guide's "Forged Depth" direction (Sora, crystal brand object, cyan accent, 16px cards,
framer-motion, shadcn) was never built. The live app is: Inter, the hexagon-bulb mark,
indigo primary with teal accent and copper/teal brand colours, 12px cards, CSS-only motion,
own primitives. Use the guide for product intent, screen contents, score/claim semantics and
accessibility; use this file for everything visual.
