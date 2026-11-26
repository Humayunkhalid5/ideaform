# Layout, type and colour for IdeaForm

All class names below exist in `frontend/app/globals.css` (Tailwind v4, `@theme inline`).
Check that file before relying on one; it is the source of truth.

## Tiers decide richness

| Tier | Screens | Allowed |
| --- | --- | --- |
| Showcase | landing, login/register, empty states, analysis progress, export success | `if-mesh`, `if-grid`, `if-glass`, larger type (`t-hero`), one animated focal element |
| Product | dashboard, project overview, evaluation, research, compare, blueprint | flat cards (`if-card`, `if-card-hover` if clickable), gauges and charts, micro-interactions |
| Utility | tables, versions, documents, settings | flat surfaces, no decoration, no entrance motion |

## Layout

- Page container: whatever `components/layout/AppShell.tsx` sets (currently `max-w-[1220px]`);
  pages don't add their own outer max-width.
  Every block aligns to its left and right edge; full-bleed only on Showcase heroes.
- Spacing scale: stick to Tailwind steps 1, 2, 3, 4, 6, 8, 12, 16. Inside a card `p-5` or
  `p-6`; between cards `gap-4` (dense) or `gap-6` (airy); between page sections `space-y-8`.
  Related things are closer together than unrelated things.
- One heading per section, first in the section, left-aligned. Section header row = title on
  the left, at most one or two actions on the right.
- Grids: bento layouts are fine on overview pages, but each tile has one idea. Prefer 12-column
  thinking (`grid-cols-12`, spans of 4/6/8) over arbitrary widths. Stack to one column under
  `md`; never horizontal page scroll (tables scroll inside their own `overflow-x-auto`).
- Two boxes deep at most. A list inside a card is rows with dividers (`divide-y divide-line`),
  not more cards.
- Touch targets at least 44px tall on mobile (`h-11`); buttons go full width on phones when
  they are the screen's main action.

## Typography

- One family: Inter for UI (`font-sans`), JetBrains Mono (`font-mono`, `t-mono`) for ids,
  evidence markers, code, and numbers that line up. Don't add display fonts.
- Use the scale classes, not ad-hoc sizes: `t-hero` 30/36, `t-section` 24/32, `t-title` 18/28,
  `t-sub` 16/24, `t-body` 14/22, `t-meta` 12/18, `t-label` 11/14 uppercase. Body is 14px.
- Weight: 600 for headings, 500 for labels and buttons, 400 for body. No 700+ outside the hero
  number on a gauge.
- Colour: `text-ink` for headings and body, `text-muted` for secondary text and meta. Don't
  make body text muted; muted is for things you could skip.
- Numbers that change or compare (scores, counts, deltas): `tabular` / `t-mono`.
- Line length for analysis text 60–80 characters (`max-w-prose` or `max-w-[68ch]`).
- Headings name the thing. Sentence case. No trailing full stop.

## Colour

Semantic tokens (Tailwind utilities `bg-*`, `text-*`, `border-*`):

| Role | Token | Use |
| --- | --- | --- |
| Page | `canvas` | app background |
| Surfaces | `surface`, `surface-soft` | cards; inset panels, hovered rows |
| Lines | `line` | borders, dividers |
| Text | `ink`, `muted` | primary and secondary text |
| Action | `primary`, `primary-hover`, `primary-soft` | the main action, active nav/tab, focus |
| Accent | `accent`, `accent-soft` | "Good" scores, secondary highlight; rarely |
| Status | `success`, `warning`, `danger`, `info` (+ `-soft`) | status only: scores, claims, confidence, alerts |

- Status pairs: `-soft` background with the solid colour for text/icon (`bg-success-soft
  text-success`). Use `badge.tsx` rather than rebuilding pills.
- Score bands come from `scoreTone()` in `components/scores/RadialGauge.tsx` (80+ success,
  60–79 accent, 40–59 warning, under 40 danger). Reuse it; don't re-derive thresholds.
- Claim labels: verified fact = success + `BadgeCheck`, assumption = warning + `HelpCircle`,
  AI suggestion = info + `Sparkles`. Always icon plus text.
- Shadows: `shadow-e1` resting, `shadow-e2` hover/raised, `shadow-e3` overlays. No coloured
  glows on Product or Utility screens.
- Both themes: every new token gets a `.dark` value. Check contrast at 4.5:1 for text in both.
- Gradients: only on Showcase surfaces and at most one per screen; never on text you must read.

## Components

- Start from `components/ui/` (`button.tsx` variants primary, secondary, ghost, solid, danger;
  `card.tsx` with `Card`, `GlassCard`, `SectionHeading`; `badge.tsx` with `Badge`,
  `StatusBadge`; `field.tsx`; `skeleton.tsx` with `Skeleton`, `PageSkeleton`). Add a variant there if needed instead
  of styling a one-off.
- Use `cn()` from `lib/utils` to merge classes.
- Icons: lucide-react, `size={16}` inline, `aria-hidden` when next to a text label; icon-only
  buttons need `aria-label`.
- Charts (Recharts): colours from CSS variables (`stroke="var(--if-primary)"`), axis and grid
  in `var(--if-line)` / `var(--if-muted)`, `t-meta` sized ticks, no 3D, no chart-junk legends
  when direct labels fit. Give each chart an `aria-label` and a text or `sr-only` table fallback.
  Set `isAnimationActive={false}` when the user prefers reduced motion (see `motion.md`).
- Focus: keep the global `:focus-visible` ring or the button's `ring-primary/45`; never remove an
  outline without replacing it.

## Making a screen look less generic

- Cut before you add: remove a border, a background, a redundant heading or icon first.
- Give the one important number or sentence real size; shrink everything else.
- Vary composition between sections (a wide chart, then a two-column list) instead of a wall of
  identical cards.
- Replace vague labels ("Insights", "Details") with the actual content name.
- Align everything; most "off" screens are misaligned edges or inconsistent gaps.
