# Stitch design reference — IdeaForm

Screens pulled from the Stitch project **ideaform** (`projects/6612295154740999549`).
The Stitch project still labels its screens "VentureAI"; the product name in the app is **IdeaForm** everywhere.

| Screen | Stitch title | Route implemented | Files |
| --- | --- | --- | --- |
| S03 | VentureAI - Dashboard | `/dashboard` | `S03-dashboard.html`, `S03-dashboard.png` |
| S05 | VentureAI - New Project Wizard | `/projects/new` | `S05-new-project-wizard.html`, `S05-new-project-wizard.png` |
| S12 | VentureAI - Project Evaluation (Tutor Match) | not wired — Phase 2 | `S12-evaluation.html`, `S12-evaluation.png` |
| S16 | VentureAI - Architecture Blueprint (Tutor Match) | not wired — Phase 4 | `S16-blueprint.html`, `S16-blueprint.png` |

`STITCH_UI_BRIEF.md` is the brief that generated these screens (design tokens, component
inventory, sample data).

## Where each design landed in the code

- Tokens, type scale, surfaces: `frontend/app/globals.css`
- Shell (sidebar + top bar + mobile tabs): `frontend/components/layout/AppShell.tsx`
- Dashboard: `frontend/app/(app)/dashboard/page.tsx`
- Wizard: `frontend/app/(app)/projects/new/page.tsx`
- Project header + tab bar: `frontend/app/(app)/projects/[id]/layout.tsx`, `components/layout/ProjectTabs.tsx`
- Overview / Understanding / Run: same routes as before, restyled to these tokens
- Auth split screen: `frontend/components/auth/AuthForm.tsx`
- Marketing page: `frontend/app/page.tsx`

S12 and S16 depend on backend phases that do not exist yet (evaluation, research,
blueprint). Their tabs are rendered locked rather than filled with invented scores.
