# Done checklist for UI work

Check each line in the browser preview, not from the code alone.

## System
- [ ] Every colour, shadow, radius and font comes from `globals.css` tokens; no new hex values
      in components.
- [ ] Reuses `components/ui/` primitives; one primary button per screen area, one card style.
- [ ] At most two boxes deep; edges line up with the page container.

## Hierarchy and copy
- [ ] The screen's main content is the largest, clearest thing; chrome is quieter.
- [ ] Headings name the content; buttons are verb + object; no filler text.
- [ ] Type classes (`t-*`) used; numbers that compare are `tabular`.

## States
- [ ] Loading skeleton matches the final layout; empty state has one action; error state offers
      a retry.
- [ ] Long titles, 0/100 scores and empty lists don't break the layout.

## Themes and sizes
- [ ] Light and dark both look right; text contrast at least 4.5:1 in both.
- [ ] 1280 and 390 widths: no sideways page scroll, tables scroll in their own container, tap
      targets at least 44px on mobile.

## Accessibility
- [ ] Tab reaches every control in order with a visible focus ring.
- [ ] Icon-only buttons have `aria-label`; decorative icons `aria-hidden`.
- [ ] Charts and gauges have an `aria-label` and a text fallback; colour is never the only signal.

## Motion
- [ ] Every animation has a reason (feedback, continuity, progress, arrival).
- [ ] Only transform/opacity/colour animate; durations within the table in `motion.md`.
- [ ] No scroll reveals, parallax or tilt on Product/Utility screens.
- [ ] With reduced motion emulated (Browser pane: DevTools rendering, or
      `matchMedia` check), nothing moves and nothing stays hidden; gauges show final values.
- [ ] Any new dependency (e.g. `motion`) was agreed with the user.

## Build
- [ ] `npm run build` passes in `frontend/`.
