# IdeaForm: notes for coding agents

- **UI work:** read `DESIGN.md` first and load the `ideaform-ui-taste` skill. Every page uses
  the same tokens, primitives, motion rules and the icon-only logo (`components/brand/Logo.tsx`).
  When a phase ships, follow the checklist in `DESIGN.md` §9.
- **Plan and specs:** `docs/implementation_plan.md` (phases), `docs/architecture.md`,
  `docs/AI_DESIGN.md`, and the per-phase notes in `docs/phase*.md`.
- **Run locally (Windows, no Docker):** `powershell -ExecutionPolicy Bypass -File scripts\run_local.ps1`
  (database on localhost:5434, API on :8000, web app on :3000).
- **Checks:** backend `cd backend; ..\.venv\Scripts\python -m pytest`; frontend
  `cd frontend; npx tsc --noEmit; npm run build`.
