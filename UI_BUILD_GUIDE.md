# IdeaForm: UI Build Guide for Freebuff

> **Superseded for visuals by [`DESIGN.md`](DESIGN.md).** The built app uses Inter, the
> hexagon-bulb icon (`components/brand/Logo.tsx`), indigo primary with copper/teal brand colours,
> 12px cards and CSS-only motion. Where this guide says otherwise (Sora, crystal brand object,
> cyan accent, 16px cards, framer-motion, shadcn), follow `DESIGN.md`. Keep using this guide for
> product intent, screen contents, score/claim semantics and accessibility.

> **For the coding agent:** This file is a **self-contained spec for building the whole IdeaForm frontend** in code. You do **not** need Stitch or any design tool. Build the UI directly from this guide. If `design/stitch/` contains exported screens, treat them as optional visual references only. For the longer design rationale and per-screen Stitch prompts, see `docs/STITCH_UI_BRIEF.md`. For backend contracts, see `docs/architecture.md` section 8.
>
> **Product name: IdeaForm.** Use it everywhere; keep it in one constant: `export const APP_NAME = "IdeaForm"`. Tagline: *From Idea to Implementation.*
>
> **Quality bar:** premium and modern, not a plain admin template. Depth, light, motion, and clear data presentation. But **readability always wins**: dense data screens stay calm and flat.

---

## 1. How to Work on the UI

1. Build in the order in section 13 (U0 to U10). Finish and verify each step before the next.
2. Start with **mock data** (section 6). Switch to the live API later with one environment flag.
3. Build **shared components first**, then pages.
4. After every step run `npm run lint` and `npm run build`; fix errors before continuing.
5. Update `PROGRESS.md` after each step with what was built and what is next.
6. Ask the user one clear question if something is unclear. Do not invent features.

---

## 2. Visual Direction: "Forged Depth"

**Idea:** a raw spark of an idea is forged into a precise structure. Brand object: a faceted glowing **crystal** that resolves into a **blueprint wireframe**.

### Three tiers of richness
| Tier | Screens | Treatment |
| --- | --- | --- |
| **Showcase** | Landing, auth, onboarding, wizard category cards, analysis progress, export success, empty states | 3D crystal, gradient mesh, glass, glow, large expressive type, motion |
| **Product** | Dashboard, project overview, research, evaluation, improvement loop, comparison, blueprint | Polished 2D with depth: glass sidebar, layered cards, radial gauges, gradient accents, micro-interactions |
| **Utility** | Tables, versions list, documents, knowledge sources, settings | Flat, crisp, minimal decoration |

**Rules:** no glass or blur behind dense tables or long text. One animated focal element per area. Respect `prefers-reduced-motion`. No stock photos; use illustration, gradients, and 3D shapes.

### Signature elements
Gradient mesh backgrounds with faint grain; glassmorphism panels; indigo-tinted multi-layer shadows; glow under primary actions; animated gradient borders on featured cards; radial score gauges with count-up; bento grids; card tilt on hover (Showcase and featured cards only); radar, risk matrix, positioning map, diff bars, Gantt.

---

## 3. Project Setup (U0)

```bash
npx create-next-app@latest frontend --typescript --tailwind --eslint --app --src-dir=false --import-alias "@/*"
cd frontend
npx shadcn@latest init
npx shadcn@latest add button card tabs dialog sheet dropdown-menu input textarea label badge table tooltip progress select switch checkbox accordion popover command skeleton scroll-area separator avatar sonner
npm i framer-motion recharts lucide-react next-themes mermaid react-markdown remark-gfm clsx tailwind-merge class-variance-authority zod
npm i three @react-three/fiber @react-three/drei
npm i -D @types/three vitest @testing-library/react @testing-library/jest-dom jsdom
```

Notes:
- If the installed Tailwind is **v4**, define the theme in `globals.css` with `@theme` (section 4.3). If **v3**, use `tailwind.config.ts`.
- Check that `framer-motion`, `three`, and `@react-three/fiber` versions are compatible with the installed React version. If they conflict, tell the user and pick compatible versions.
- Fonts via `next/font/google`: **Sora** (headings), **Inter** (UI), **JetBrains Mono** (code).

### Target folder layout
```
frontend/
  app/
    (marketing)/page.tsx                # landing
    (auth)/login/page.tsx, register/page.tsx
    (app)/layout.tsx                    # AppShell (sidebar + top bar)
    (app)/dashboard/page.tsx
    (app)/welcome/page.tsx
    (app)/knowledge/page.tsx
    (app)/settings/page.tsx
    (app)/projects/new/page.tsx
    (app)/projects/[id]/layout.tsx      # project header + tabs
    (app)/projects/[id]/page.tsx        # overview
    (app)/projects/[id]/understand/page.tsx
    (app)/projects/[id]/run/page.tsx
    (app)/projects/[id]/research/page.tsx
    (app)/projects/[id]/evaluation/page.tsx
    (app)/projects/[id]/improve/page.tsx
    (app)/projects/[id]/compare/page.tsx
    (app)/projects/[id]/blueprint/page.tsx
    (app)/projects/[id]/blueprint/architecture/page.tsx
    (app)/projects/[id]/blueprint/uiux/page.tsx
    (app)/projects/[id]/blueprint/roadmap/page.tsx
    (app)/projects/[id]/versions/page.tsx
    (app)/projects/[id]/documents/page.tsx
    (app)/projects/[id]/export/page.tsx
    not-found.tsx, error.tsx
  components/
    ui/                # shadcn primitives
    brand/             # Logo, Monogram, CrystalScene, CrystalHero, CrystalPoster
    layout/            # GlassSidebar, TopBar, ProjectTabs, CommandPalette, NotificationsPopover, ThemeToggle
    scores/            # RadialGauge, ScoreCard, ConfidenceBadge, ScoreDrawer, DimensionRadar
    evidence/          # ClaimChip, SourceCard, CitationMarker, Disclaimer
    wizard/            # StepIndicator, CategoryCard3D, HelpLevelCard
    run/               # PipelineTimeline, LogPanel
    compare/           # DiffRow, VersionCompare, ScoreBars
    risk/              # RiskMatrix
    research/          # CompetitorTable, PositioningMap
    blueprint/         # ArtifactList, MarkdownView, MarkdownEditor, DiagramViewer, Gantt, FlowDiagram
    states/            # EmptyState, ErrorState, Skeletons
  lib/
    constants.ts       # APP_NAME, DISCLAIMER
    tokens.css
    motion.ts
    types.ts
    api.ts
    utils.ts           # cn(), formatDate()
    mock/              # data from section 6
  public/3d/           # crystal-poster.svg (simple gradient crystal), optional .glb
```

---

## 4. Design Tokens

### 4.1 Constants (`lib/constants.ts`)
```ts
export const APP_NAME = "IdeaForm";
export const TAGLINE = "From Idea to Implementation";
export const DISCLAIMER = "Scores are evidence-based estimates, not predictions of business success.";
```
Use `DISCLAIMER` exactly wherever scores appear.

### 4.2 `lib/tokens.css` (import in `app/globals.css`)
IdeaForm tokens use the `--if-` prefix so they never collide with shadcn variables.
```css
:root {
  --if-bg: #F6F7FB;
  --if-surface: #FFFFFF;
  --if-glass: rgba(255,255,255,0.66);
  --if-border: #E3E7F0;
  --if-border-glass: rgba(255,255,255,0.55);
  --if-text: #0B1020;
  --if-muted: #5B6479;
  --if-primary: #4F46E5;
  --if-primary-2: #7C3AED;
  --if-accent: #22D3EE;
  --if-spark: #F97316;
  --if-success: #16A34A;
  --if-warning: #D97706;
  --if-danger: #DC2626;
  --if-info: #7C3AED;

  --if-radius-card: 16px;
  --if-radius-input: 10px;

  --if-shadow-1: 0 1px 2px rgba(15,23,42,.06);
  --if-shadow-2: 0 8px 24px -8px rgba(15,23,42,.14);
  --if-shadow-3: 0 24px 48px -16px rgba(79,70,229,.28);
  --if-glow: 0 0 0 1px rgba(124,58,237,.4), 0 10px 36px rgba(124,58,237,.35);

  --if-forge: linear-gradient(135deg, #4F46E5 0%, #7C3AED 55%, #C026D3 100%);
  --if-aqua: linear-gradient(135deg, #4F46E5 0%, #22D3EE 100%);
  --if-spark-grad: linear-gradient(135deg, #F97316, #FACC15);
}
.dark {
  --if-bg: #070B1A;
  --if-surface: #0F1629;
  --if-glass: rgba(17,24,45,0.56);
  --if-border: #1E2742;
  --if-border-glass: rgba(255,255,255,0.08);
  --if-text: #F1F5FF;
  --if-muted: #95A0BC;
  --if-primary: #6366F1;
  --if-primary-2: #8B5CF6;
  --if-spark: #FB923C;
  --if-success: #22C55E;
  --if-warning: #F59E0B;
  --if-danger: #EF4444;
  --if-info: #A78BFA;
  --if-shadow-2: 0 8px 24px -8px rgba(0,0,0,.5);
  --if-shadow-3: 0 24px 48px -16px rgba(99,102,241,.35);
}

/* Reusable effect classes */
.if-glass {
  background: var(--if-glass);
  border: 1px solid var(--if-border-glass);
  backdrop-filter: blur(16px) saturate(140%);
  -webkit-backdrop-filter: blur(16px) saturate(140%);
  box-shadow: var(--if-shadow-2), inset 0 1px 0 rgba(255,255,255,.4);
}
.if-card { background: var(--if-surface); border: 1px solid var(--if-border); border-radius: var(--if-radius-card); box-shadow: var(--if-shadow-1); }
.if-card-hover { transition: transform .2s ease, box-shadow .2s ease; }
.if-card-hover:hover { transform: translateY(-4px); box-shadow: var(--if-shadow-3); }
.if-glow { box-shadow: var(--if-glow); }
.if-gradient-text { background: var(--if-forge); -webkit-background-clip: text; background-clip: text; color: transparent; }
.if-mesh {
  background:
    radial-gradient(600px 400px at 15% 10%, rgba(79,70,229,.22), transparent 60%),
    radial-gradient(500px 380px at 85% 15%, rgba(34,211,238,.18), transparent 60%),
    radial-gradient(520px 420px at 60% 90%, rgba(124,58,237,.18), transparent 60%),
    var(--if-bg);
}
.if-grain::after { content:""; position:absolute; inset:0; pointer-events:none; opacity:.035; background-image:url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='120' height='120'><filter id='n'><feTurbulence type='fractalNoise' baseFrequency='.9' numOctaves='2'/></filter><rect width='100%' height='100%' filter='url(%23n)'/></svg>"); }
.if-gradient-border { position:relative; border-radius:var(--if-radius-card); }
.if-gradient-border::before { content:""; position:absolute; inset:0; padding:1.5px; border-radius:inherit; background:var(--if-forge); -webkit-mask:linear-gradient(#000 0 0) content-box, linear-gradient(#000 0 0); -webkit-mask-composite:xor; mask-composite:exclude; pointer-events:none; }
.tabular { font-variant-numeric: tabular-nums; }
@media (prefers-reduced-motion: reduce) { *,*::before,*::after { animation-duration:.01ms !important; transition-duration:.01ms !important; } }
```
Sync shadcn's own variables (`--background`, `--foreground`, `--primary`, `--border`, `--ring`, `--radius`) so they visually match the values above in light and dark.

### 4.3 Tailwind mapping
**Tailwind v3 (`tailwind.config.ts`):**
```ts
extend: {
  colors: { if: {
    bg:"var(--if-bg)", surface:"var(--if-surface)", border:"var(--if-border)",
    text:"var(--if-text)", muted:"var(--if-muted)", primary:"var(--if-primary)",
    primary2:"var(--if-primary-2)", accent:"var(--if-accent)", spark:"var(--if-spark)",
    success:"var(--if-success)", warning:"var(--if-warning)", danger:"var(--if-danger)", info:"var(--if-info)"
  }},
  fontFamily: { display:["var(--font-sora)"], sans:["var(--font-inter)"], mono:["var(--font-mono)"] },
  borderRadius: { card:"16px", input:"10px" },
  boxShadow: { e1:"var(--if-shadow-1)", e2:"var(--if-shadow-2)", e3:"var(--if-shadow-3)", glow:"var(--if-glow)" },
  keyframes: { shimmer:{ "100%":{ transform:"translateX(100%)" } }, float:{ "0%,100%":{ transform:"translateY(0)" }, "50%":{ transform:"translateY(-8px)" } } },
  animation: { float:"float 6s ease-in-out infinite" }
}
```
**Tailwind v4:** in `globals.css`
```css
@theme inline {
  --color-if-bg: var(--if-bg); --color-if-surface: var(--if-surface); --color-if-border: var(--if-border);
  --color-if-text: var(--if-text); --color-if-muted: var(--if-muted); --color-if-primary: var(--if-primary);
  --color-if-primary2: var(--if-primary-2); --color-if-accent: var(--if-accent); --color-if-spark: var(--if-spark);
  --color-if-success: var(--if-success); --color-if-warning: var(--if-warning); --color-if-danger: var(--if-danger); --color-if-info: var(--if-info);
  --font-display: var(--font-sora); --font-sans: var(--font-inter); --font-mono: var(--font-mono);
}
```

### 4.4 Type scale
Display 56/60 (landing hero), H1 36/44, H2 26/34, H3 19/28, body 15/24, small 13/20, caption 12/16. Headings use `font-display` with tracking -0.02em. Scores use `tabular`.

### 4.5 Score and claim colours
| Score | Tone | Colour token |
| --- | --- | --- |
| 80 to 100 | Strong | `--if-success` |
| 60 to 79 | Good | `--if-accent` |
| 40 to 59 | Mixed | `--if-warning` |
| 0 to 39 | Weak | `--if-danger` |

| Claim label | Colour | Icon (Lucide) |
| --- | --- | --- |
| verified_fact | success | `BadgeCheck` |
| assumption | warning | `HelpCircle` |
| ai_suggestion | info | `Sparkles` |

Confidence: `low` (alert-triangle icon, warning), `medium` (minus-circle, accent), `high` (shield-check, success). Always show text plus icon, never colour alone.

---

## 5. Types (`lib/types.ts`)

```ts
export type Category = "business" | "software" | "technology";
export type HelpLevel = "evaluate" | "research" | "blueprint" | "everything";
export type ProjectStatus = "draft" | "analysing" | "ready" | "failed" | "archived";
export type Confidence = "low" | "medium" | "high";
export type ClaimLabel = "verified_fact" | "assumption" | "ai_suggestion";
export type DimensionKey =
  | "technical_feasibility" | "market_opportunity" | "competition"
  | "business_model" | "resource_requirements" | "execution_complexity";

export interface Project { id: string; title: string; category: Category; helpLevel: HelpLevel;
  status: ProjectStatus; updatedAt: string; versionCount: number; currentVersionId: string;
  progress?: number; scores?: Partial<Record<DimensionKey, number>>; }

export interface Requirement { id: string; type: "functional"|"non_functional"|"constraint"|"assumption";
  description: string; priority: "must"|"should"|"could"; source: "extracted"|"ai_suggestion"; confirmed: boolean; }

export interface StructuredIdea { oneLineSummary: string; category: Category; subDomain: string; problem: string;
  targetUsers: string[]; keyFeatures: string[]; technologies: string[]; missingInformation: string[];
  clarifyingQuestions: string[]; requirements: Requirement[]; }

export interface Source { id: string; evidenceId: string; title: string; domain: string; url: string;
  publishedAt?: string; retrievedAt: string; snippet: string; kb: "A"|"B"|"C"; label: ClaimLabel; }

export interface Claim { text: string; label: ClaimLabel; evidenceIds: string[]; }

export interface Dimension { key: DimensionKey; name: string; score: number; confidence: Confidence;
  reason: string; explanation: string; claims: Claim[]; assumptions: string[]; recommendations: string[];
  history: number[]; }

export interface Risk { id: string; title: string; likelihood: "low"|"medium"|"high"; impact: "low"|"medium"|"high";
  severity: "low"|"medium"|"high"; mitigation: string[]; }

export interface Improvement { id: string; title: string; rationale: string; expectedEffect: string;
  dimension: DimensionKey; direction: "up"|"down"; decision?: "accepted"|"rejected"|"edited"; }

export interface Competitor { id: string; name: string; targetCustomers: string; pricing: string;
  strengths: string[]; weaknesses: string[]; opportunity: string; sourceEvidenceId?: string;
  priceLevel: number; universityFocus: number; /* 0 to 100 for the positioning map */ }

export interface Evaluation { versionNo: number; summary: string; dimensions: Dimension[]; risks: Risk[];
  devilsAdvocate: string; improvements: Improvement[]; alternatives: string[]; disclaimer: string; }

export interface Artifact { id: string; type: "prd"|"architecture"|"database_schema"|"api_spec"|"ui_ux"|"business_model"|"roadmap";
  title: string; format: "markdown"|"mermaid"|"json"; content: string; version: number; editedByUser: boolean; }

export type StepStatus = "queued" | "running" | "done" | "failed";
export interface AgentStep { id: string; name: string; description: string; status: StepStatus; elapsedSec?: number; log: string[]; }
```

---

## 6. Mock Data (`lib/mock/`)

Create these files so every page works before the backend exists. All data below is **fictional sample data**.

**`projects.ts`**
```ts
export const projects: Project[] = [
  { id:"p1", title:"Tutor Match", category:"software", helpLevel:"everything", status:"ready", updatedAt:"2 hours ago", versionCount:3, currentVersionId:"v3",
    scores:{technical_feasibility:85,market_opportunity:70,competition:55,business_model:75,resource_requirements:65,execution_complexity:60} },
  { id:"p2", title:"Campus Food Bank", category:"business", helpLevel:"evaluate", status:"analysing", updatedAt:"10 minutes ago", versionCount:1, currentVersionId:"v1", progress:42 },
  { id:"p3", title:"Smart Irrigation Sensor", category:"technology", helpLevel:"research", status:"draft", updatedAt:"Yesterday", versionCount:1, currentVersionId:"v1" },
  { id:"p4", title:"Freelance Invoice Assistant", category:"software", helpLevel:"blueprint", status:"ready", updatedAt:"3 days ago", versionCount:2, currentVersionId:"v2",
    scores:{technical_feasibility:80,market_opportunity:62,competition:48,business_model:70,resource_requirements:72,execution_complexity:68} },
];
```

**`evaluation.ts`** (Tutor Match, v3 shown; also export v1 and v2 for comparison)
- Dimensions: Technical feasibility 85 High ("Core features use well-known technology"); Market opportunity 70 Medium ("Large student population, limited local data"); Competition 55 Medium ("Several established tutor platforms exist"); Business model 75 Medium ("Commission model is common in marketplaces"); Resource requirements 65 Low ("Cost estimates rely on assumptions"); Execution complexity 60 Medium ("Two-sided marketplace needs both sides at launch").
- Each dimension: `explanation` (2 to 3 sentences with `[E1]` style markers), `claims` with labels, `assumptions` (1 to 3), `recommendations` (2 to 3), `history` array across versions (e.g. competition `[55, 59, 63]`).
- Risks: Cold-start problem (likelihood high, impact high); Payments arranged outside the platform (medium, high); Tutor quality control (medium, medium); Data privacy compliance (low, high).
- Improvements: "Focus on one university first" (competition, up); "Add a verified-tutor badge" (execution_complexity, up); "Offer a first-session guarantee" (business_model, up).
- `devilsAdvocate`: a short paragraph on why it might fail, plus bullets "What would have to be true".
- v1 to v2 comparison: Competition 55 to 63 (+8), Execution complexity 60 to 66 (+6), Business model 75 to 74 (-1), each with a one-sentence reason.

**`research.ts`**
- Sources (evidence ids E1 to E3): "Example Market Report 2025" (example.org, 10 Mar 2025), "Online Tutoring Industry Overview" (example.com, 2 Jan 2025), "Marketplace Cold Start Guide" (example.net, 14 Aug 2024).
- Competitors: TutorHub (global marketplace, 20% commission, priceLevel 70, universityFocus 25), StudyLink (subject courses, subscription, 55, 40), CampusTutors (university peer tutoring, free, 10, 85).

**`idea.ts`**: structured idea for Tutor Match (summary, problem, target users, key features, missing information, 5 sample requirements with priorities).

**`artifacts.ts`**: seven artifacts. Include a real Mermaid architecture diagram:
```
flowchart LR
  Web[Next.js Web App] --> API[FastAPI API]
  API --> DB[(PostgreSQL + pgvector)]
  API --> Redis[(Redis)]
  Redis --> Worker[Celery Worker]
  Worker --> LLM[LLM Service]
  Worker --> Search[Search API]
  Worker --> DB
```
Also an ER diagram (`erDiagram`) for users, projects, project_versions, evaluations, competitors; a short PRD in Markdown (goals, users, scope, features, requirements, metrics); a UI/UX concept list; a roadmap object: phases `Foundation weeks 1-3`, `Marketplace core 4-6`, `Payments and reviews 7-9`, `Launch pilot 10-12`.

**`run.ts`**: six `AgentStep` items (Research, Evaluation, Business, Product Design, Technical Architect, Documentation) with sample log lines ("Searching for competitors", "Found 8 sources", "Scoring six dimensions").

**`user.ts`**: Ayesha Khan, ayesha@example.com.

---

## 7. Motion (`lib/motion.ts`)

```ts
export const ease = [0.22, 1, 0.36, 1] as const;
export const fadeUp = { hidden:{ opacity:0, y:12 }, show:{ opacity:1, y:0, transition:{ duration:.4, ease } } };
export const stagger = (s = 0.04) => ({ hidden:{}, show:{ transition:{ staggerChildren:s } } });
export const scaleIn = { hidden:{ opacity:0, scale:.96 }, show:{ opacity:1, scale:1, transition:{ duration:.25, ease } } };
```
| Moment | Behaviour |
| --- | --- |
| Page load | Staggered `fadeUp` (40ms steps) |
| Gauge | Arc fills and number counts up over 900ms |
| Cards | Hover lift 4px plus `--if-shadow-3`; optional 3 degree tilt on featured cards |
| Primary buttons | Glow increases on hover; press scale .98 |
| Tabs and wizard | Shared `layoutId` indicator slides |
| Analysis | Crystal rotates and pulses; light travels along the pipeline; spark burst on step completion |
| Completion | Brief confetti once (small indigo, cyan, ember particles); skip when reduced motion |
Use `useReducedMotion()` from Framer Motion and replace movement with simple fades.

---

## 8. Core Components (build in U3 to U5)

### 8.1 RadialGauge (reference implementation)
```tsx
"use client";
import { motion, useMotionValue, useTransform, animate, useReducedMotion } from "framer-motion";
import { useEffect, useId } from "react";

export function scoreTone(score: number) {
  if (score >= 80) return { label: "Strong", color: "var(--if-success)" };
  if (score >= 60) return { label: "Good", color: "var(--if-accent)" };
  if (score >= 40) return { label: "Mixed", color: "var(--if-warning)" };
  return { label: "Weak", color: "var(--if-danger)" };
}

export function RadialGauge({ score, size = 120, stroke = 10, name }: { score: number; size?: number; stroke?: number; name: string }) {
  const reduce = useReducedMotion();
  const r = (size - stroke) / 2, c = 2 * Math.PI * r, id = useId();
  const tone = scoreTone(score);
  const mv = useMotionValue(0);
  const offset = useTransform(mv, (v) => c - (v / 100) * c);
  const text = useTransform(mv, (v) => Math.round(v).toString());
  useEffect(() => {
    const ctl = animate(mv, score, { duration: reduce ? 0 : 0.9, ease: "easeOut" });
    return () => ctl.stop();
  }, [score, reduce, mv]);
  return (
    <svg width={size} height={size} role="img" aria-label={`${name}: ${score} out of 100, ${tone.label}`}>
      <defs>
        <linearGradient id={id} x1="0" y1="0" x2="1" y2="1">
          <stop offset="0%" stopColor="var(--if-primary)" />
          <stop offset="100%" stopColor={tone.color} />
        </linearGradient>
      </defs>
      <circle cx={size/2} cy={size/2} r={r} fill="none" stroke="var(--if-border)" strokeWidth={stroke} />
      <motion.circle cx={size/2} cy={size/2} r={r} fill="none" stroke={`url(#${id})`} strokeWidth={stroke}
        strokeLinecap="round" strokeDasharray={c} style={{ strokeDashoffset: offset }}
        transform={`rotate(-90 ${size/2} ${size/2})`} />
      <motion.text x="50%" y="50%" textAnchor="middle" dominantBaseline="central"
        className="tabular" fill="var(--if-text)" fontSize={size * 0.3} fontWeight={600}>{text}</motion.text>
    </svg>
  );
}
```
Add a Vitest test for `scoreTone` boundaries (39, 40, 59, 60, 79, 80).

### 8.2 CrystalScene and CrystalHero (3D, Showcase screens only)
```tsx
// components/brand/CrystalScene.tsx
"use client";
import { Canvas, useFrame } from "@react-three/fiber";
import { Float, MeshTransmissionMaterial, ContactShadows, Environment } from "@react-three/drei";
import { useRef } from "react";
import * as THREE from "three";

function Crystal({ progress = 0 }: { progress?: number }) {
  const ref = useRef<THREE.Mesh>(null!);
  useFrame((_, d) => { ref.current.rotation.y += d * 0.3; ref.current.rotation.x += d * 0.08; });
  return (
    <Float speed={1.4} rotationIntensity={0.35} floatIntensity={0.9}>
      <mesh ref={ref}>
        <icosahedronGeometry args={[1.2, 0]} />
        <MeshTransmissionMaterial transmission={1} thickness={0.6} roughness={0.12} ior={1.4}
          chromaticAberration={0.05} color="#7C6CFF" />
      </mesh>
      <mesh scale={0.34}><sphereGeometry args={[1, 32, 32]} /><meshBasicMaterial color="#F97316" /></mesh>
      <mesh scale={1.55}>
        <icosahedronGeometry args={[1.2, 1]} />
        <meshBasicMaterial wireframe color="#22D3EE" transparent opacity={0.15 + progress * 0.6} />
      </mesh>
    </Float>
  );
}

export default function CrystalScene({ progress = 0 }: { progress?: number }) {
  return (
    <Canvas dpr={[1, 2]} camera={{ position: [0, 0, 5], fov: 45 }}>
      <ambientLight intensity={0.6} />
      <pointLight position={[4, 4, 4]} intensity={30} color="#22D3EE" />
      <Environment preset="city" />
      <Crystal progress={progress} />
      <ContactShadows position={[0, -1.8, 0]} opacity={0.35} scale={8} blur={2.5} />
    </Canvas>
  );
}
```
```tsx
// components/brand/CrystalHero.tsx : lazy, safe wrapper with fallbacks
"use client";
import dynamic from "next/dynamic";
import { useEffect, useState } from "react";
const CrystalScene = dynamic(() => import("./CrystalScene"), { ssr: false });

export function CrystalHero({ progress = 0, className = "" }: { progress?: number; className?: string }) {
  const [ok, setOk] = useState(false);
  useEffect(() => {
    const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    const small = window.matchMedia("(max-width: 768px)").matches;
    const gl = !!document.createElement("canvas").getContext("webgl");
    setOk(!reduce && !small && gl);
  }, []);
  return (
    <div className={className} aria-hidden="true">
      {ok ? <CrystalScene progress={progress} /> : <img src="/3d/crystal-poster.svg" alt="" className="mx-auto h-full object-contain animate-float" />}
    </div>
  );
}
```
Notes: `Environment preset="city"` loads a map from a CDN; for production, replace it with a local HDR or `Lightformer`s. Create `public/3d/crystal-poster.svg` as a simple faceted gradient crystal (indigo, violet, cyan facets with an orange core). Pause rendering when off-screen with an IntersectionObserver (`frameloop="demand"` or unmount). If `MeshTransmissionMaterial` is too slow, fall back to `meshPhysicalMaterial` with `transparent` and `opacity`.

### 8.3 Evidence components
- **ClaimChip({ label })**: pill with icon and text from the claim table (4.5). Tooltip explains the label.
- **ConfidenceBadge({ level })**: pill with icon and text (4.5); tooltip shows the rule (High: 3+ independent recent sources; Medium: 1 to 2 sources or partial conflict; Low: mostly assumptions).
- **CitationMarker({ id })**: small `[E1]` chip; click scrolls to or opens the matching `SourceCard` (use a Sheet).
- **SourceCard({ source })**: favicon placeholder, title, domain, dates, snippet, `ClaimChip`, external-link button (`target="_blank" rel="noopener noreferrer"`).
- **Disclaimer()**: info-style banner with `DISCLAIMER`.
- **Markdown citations:** render text with `react-markdown` + `remark-gfm`; before rendering replace `[E1]` with a link `#E1` and render links starting with `#E` as `CitationMarker`. Do not enable raw HTML.

### 8.4 Score components
- **ScoreCard({ dimension, onOpen })**: glass-free card (`if-card if-card-hover`), `RadialGauge` 96 to 120px, name, `ConfidenceBadge`, one-line reason, sparkline (Recharts `LineChart` with no axes) from `history`, "View evidence" button. Whole card keyboard focusable; Enter opens the drawer.
- **ScoreDrawer({ dimension })**: shadcn `Sheet` (right). Sections: big gauge, "Why this score" with citation markers, Evidence (SourceCards), Claims (with ClaimChips), Assumptions, Confidence rule, Recommendations (checkboxes plus "Add to improvement loop").
- **DimensionRadar({ dimensions, compare? })**: Recharts `RadarChart` with a gradient-filled polygon (optional second polygon for the previous version); direct labels; accessible table fallback (`sr-only`).

### 8.5 Other specialised components
| Component | Spec |
| --- | --- |
| **StepIndicator({ steps, current })** | Numbered glass pills connected by a line; active step has gradient fill; completed shows check; `aria-current="step"` |
| **CategoryCard3D({ category, selected, onSelect })** | Large card with isometric illustration (inline SVG or CSS 3D stacked layers), title, bullets; hover tilt (max 4 degrees, via pointer position); selected: gradient border, glow, check badge; radio-group semantics |
| **HelpLevelCard** | Option card with output icons and estimated time; "Recommended" badge on Everything |
| **PipelineTimeline({ steps })** | Horizontal on desktop, vertical on mobile; six nodes joined by a line; running node pulses and a light travels along the active segment; done shows check; failed shows red with Retry; click expands log lines |
| **LogPanel** | Monospace live log with timestamps; auto-scroll; `aria-live="polite"` |
| **DiffRow({ label, from, to, reason })** | Old value, arrow, new value, change badge (+8 green, -1 red), reason text |
| **ScoreBars** | Recharts grouped bar chart (v1 vs v2) with value labels |
| **RiskMatrix({ risks })** | 3 by 3 grid (likelihood on y, impact on x), tinted cells (green to red), numbered dots with tooltips; below it a list keyed by the same numbers; keyboard focusable dots |
| **CompetitorTable** | shadcn `Table`, sortable, sticky header, source link column |
| **PositioningMap({ competitors })** | Recharts `ScatterChart`: x = priceLevel, y = universityFocus, bubbles labelled; highlighted "open space" rectangle; axis titles; table fallback |
| **ArtifactList** | Vertical list with icon, title, version chip, status dot |
| **MarkdownView / MarkdownEditor** | View uses `react-markdown`; Editor is a `Textarea` with Edit/Preview toggle, "Regenerate section" popover (optional instructions textarea), "Version history" button; shows "Edited by you" badge |
| **DiagramViewer({ code, kind })** | Dynamic `import("mermaid")` on the client, `mermaid.initialize({ startOnLoad:false, securityLevel:"strict", theme: dark ? "dark" : "neutral" })`, `mermaid.render(uniqueId, code)`; pan and zoom (wheel and buttons), fullscreen, download SVG; error state shows the code and a message |
| **FlowDiagram** | For UI/UX user flows: nodes as rounded glass chips joined by arrows (CSS flex or SVG) |
| **Gantt({ phases })** | CSS grid of weeks; coloured phase bars; milestone diamonds; task rows; toggle Gantt, Kanban, List; label durations as "estimate" |
| **EmptyState({ title, body, action })** | Small crystal-on-platform illustration (SVG), text, action button |
| **Skeletons** | `Skeleton` variants for ScoreCard, ProjectCard, DocumentPanel with shimmer |
| **CommandPalette** | shadcn `Command` in a `Dialog`, opens on Ctrl/Cmd+K; groups: Projects, Actions (New project, Export, Toggle theme), Pages; keyboard hints |
| **NotificationsPopover** | Bell with unread dot; list of items (analysis finished, source failed, export ready) |
| **ThemeToggle** | `next-themes` with `attribute="class"`; light, dark, system |

---

## 9. Layouts

- **AppShell `(app)/layout.tsx`:** `if-mesh` page background. **GlassSidebar** 264px (collapsible to 72px icons; tablet defaults collapsed; mobile hidden and replaced by a floating glass bottom tab bar: Home, Projects, New, Settings). Items: Dashboard, Projects, Knowledge, Settings; project switcher at the bottom; user menu. **TopBar** 64px: breadcrumbs, search button showing "Ctrl K", notifications, theme toggle, avatar. Content: `max-w-[1280px]`, padding 24 (mobile 16).
- **Project layout `projects/[id]/layout.tsx`:** header (title, category tag, status badge, version dropdown, buttons "Improve idea" and "Export") plus `ProjectTabs`: Overview, Research, Evaluation, Blueprint, Versions, Documents, Export (animated underline with `layoutId`).
- **Marketing and auth layouts:** no sidebar; dark Showcase styling allowed.

---

## 10. Pages (what to build, per route)

For each page: loading skeleton, empty state, error state, and responsive behaviour.

| Route | Tier | Build |
| --- | --- | --- |
| `/` | Showcase | Dark hero with mesh and grain; headline **"Forge your idea into a plan."**; subhead "IdeaForm researches, evaluates and designs your business, software or technology idea, with evidence you can check."; primary glowing "Start your project", glass "Watch how it works"; `CrystalHero` on the right with floating glass cards (gauge, source chip, mini diagram). Then light sections: How it works (4 connected tiles), 3 category cards, bento feature grid, product preview in a glass browser frame, honesty note, FAQ accordion, final dark CTA band, footer |
| `/login`, `/register` | Showcase | Split screen: dark mesh panel with crystal, tagline, 3 glass benefit cards; right glass card with Sign in / Create account tabs, floating-label inputs, show-password toggle, Google button (disabled placeholder), validation and error states (zod) |
| `/welcome` | Showcase | Blurred dashboard backdrop, glass modal "Welcome to IdeaForm, Ayesha" with 3-step mini tour, coach marks on New project and Ctrl+K |
| `/dashboard` | Product | Greeting, glowing "New project", 3 stat cards with sparklines, featured "Continue where you left off" card (mini radar, version chip), filter chips and search, project card grid (isometric category icon, status badge, analysing progress ring, mini score bar, hover lift, menu: Open, Duplicate, Archive, Delete with confirm), right rail with activity feed and tip card |
| `/projects/new` | Showcase | 4-step wizard with `StepIndicator`: (1) `CategoryCard3D` x3; (2) glass textarea with live counter, clickable hint chips, clarity meter, file dropzone (PDF, DOCX, TXT, MD), optional title; (3) four `HelpLevelCard`s plus estimated time; (4) review summary with Edit links and "What you will get" checklist; "Understand my idea" glowing button; "Save as draft". Continue disabled until valid; draft kept in state |
| `/projects/[id]/understand` | Product | Left: editable structured idea card (summary, category and sub-domain, problem, chips for users, features, technologies). Right: requirements grouped Functional, Non-functional, Constraints, Assumptions with priority badge, source tag, edit and delete, "Add requirement". Missing-information card with up to 5 questions and inputs. Sticky bottom bar: "Confirm and start analysis", "Back to idea" |
| `/projects/[id]/run` | Showcase | Dark mesh; large `CrystalHero` driven by progress; headline "Forging your blueprint"; progress ring; `PipelineTimeline`; glass `LogPanel`; counters (sources found, tokens used); "Continue in background", Cancel; failed-step state with Retry; low-confidence warning card; polls `GET /runs/{id}` every 2 seconds when live |
| `/projects/[id]` | Product | Bento grid: idea summary, `DimensionRadar`, six mini `ScoreCard`s (3 by 2), top 3 risks, top 3 improvements with "Start improvement loop", blueprint completeness card, recent activity; `Disclaimer` above scores |
| `/projects/[id]/research` | Product | Summary strip; filter panel (All, Competitors, Market, Technical, Uploaded); `SourceCard` list; `CompetitorTable`; `PositioningMap`; "Run research again", "Add source" |
| `/projects/[id]/evaluation` | Product | `Disclaimer`; 3 by 2 grid of `ScoreCard`s (open `ScoreDrawer`); sticky summary with radar and legend (claim labels, confidence rules); tabs Summary, Risks (RiskMatrix plus table), Devil's Advocate (distinct dark card "Why this idea might fail"), Improvements and alternatives; "Regenerate evaluation", "Start improvement loop" |
| `/projects/[id]/improve` | Product | Six-step stepper; suggestion cards with Accept, Reject, Edit (accepted tinted green, rejected dimmed, affected-dimension chip with arrow); sticky glass "New idea version" draft with accepted changes highlighted and counts; bottom glowing button "Create version 2 and re-evaluate" |
| `/projects/[id]/compare` | Product | Two version selectors; summary sentence; `DiffRow` list for six dimensions plus `ScoreBars`; split text diff (green additions, red removals); risks added and removed; requirements changed; "Make v2 the current version" |
| `/projects/[id]/blueprint` | Product | `ArtifactList` left; `MarkdownView` or `MarkdownEditor` main; toolbar (Regenerate section with instructions popover, Version history, Copy, Download); outline of headings on the right that highlights while scrolling; notes "Generated from evaluation v3" and "Edited by you" |
| `.../blueprint/architecture` | Product | `DiagramViewer` for architecture on a dot-grid canvas; tabs ER diagram, Schema SQL (monospace, copy button), API endpoints (method tags GET, POST, PATCH); Regenerate |
| `.../blueprint/uiux` | Product | `FlowDiagram` (Landing, Sign up, Search tutors, Tutor profile, Book session, Pay, Review); gallery of low-fidelity wireframe thumbnails in glass frames; design principles and screen list |
| `.../blueprint/roadmap` | Product | `Gantt` with four phases, milestones, tasks, owner avatars, effort ranges labelled "estimate"; view toggle; linked risks and MVP scope (Must, Should, Could) |
| `/projects/[id]/versions` | Utility | Vertical timeline of versions with date, change summary, editor, delta chips, View, Compare, Restore; artifact versions table with type filter |
| `/projects/[id]/documents` | Utility | Dashed dropzone; file list with status chips (Uploading, Processing, Indexed, Failed), size, chunk count, delete; privacy note "Only you can see these documents. They are never added to the public knowledge base."; "Ask your project documents" box with an example answer and citations |
| `/projects/[id]/export` | Showcase | Format cards (PDF, Markdown, ZIP); include checklist; "Include version history" switch; glowing "Generate export"; states: progress bar, then success with the crystal resolved into a blueprint cube, brief confetti, file size, Download |
| `/knowledge` | Utility | Stat cards; searchable table (Title, Source type, KB badge, Category, Licence note, Retrieved date, URL); "Test retrieval" panel returning passages with similarity score, source, date |
| `/settings` | Utility | Tabs Profile, Preferences (theme preview cards, default help level, language, reduced-motion switch), Usage (token gauge, runs chart, faster-model switch), Security (change password, sessions, delete account with confirm) |
| `not-found`, `error` | Showcase | Crystal-themed 404 with "Go to dashboard"; error boundary with retry |

**Cross-page rules**
- Evaluation and research text always shows `ClaimChip`s and `CitationMarker`s.
- Destructive actions use a confirmation dialog naming the item.
- Regenerate actions open a small instruction box and state that earlier versions are kept.
- Long tasks show progress and a toast plus badge when finished.

---

## 11. API Client (`lib/api.ts`)

Typed wrapper, mock by default:
```ts
const USE_MOCK = process.env.NEXT_PUBLIC_USE_MOCK !== "false";
const BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
```
Functions (return the types in section 5): `login`, `register`, `listProjects`, `createProject`, `getProject`, `updateProject`, `deleteProject`, `understandIdea`, `updateRequirements`, `startAnalysis`, `getRun`, `getSources`, `getEvaluation(projectId, versionNo)`, `improve`, `compare(a, b)`, `listArtifacts`, `regenerateArtifact(type, instructions?)`, `updateArtifact`, `uploadDocument`, `exportProject(format)`.
Rules: store the JWT in memory or an httpOnly cookie via the backend (never `localStorage` for production); one `request()` helper adds the token, handles 401 (redirect to login) and shows errors through toasts; in mock mode simulate latency (400 to 900 ms) so loading states are visible.

---

## 12. Responsive, Accessibility, Performance

- Breakpoints: mobile 390, tablet 768, desktop 1280 to 1440. Tables scroll inside their own container; the page body never scrolls sideways.
- Contrast at least 4.5:1 in both themes; visible 2px focus rings; touch targets at least 44px on mobile.
- Keyboard: Ctrl/Cmd+K palette, Esc closes overlays, focus trap in dialogs and drawers, arrow keys in radio groups and tabs.
- Charts and gauges have `aria-label`s and table fallbacks; colour is never the only signal.
- Respect `prefers-reduced-motion`.
- Performance: Server Components by default; Client Components only where interactive; lazy-load 3D, Mermaid, and Recharts-heavy views with `next/dynamic`; use `next/image` for images; cap the 3D devicePixelRatio at 2; pause the 3D scene off-screen; aim for Lighthouse performance 80+ on the dashboard.
- Security: no raw HTML rendering of generated content; Mermaid `securityLevel: "strict"`; external links use `rel="noopener noreferrer"`; no secrets in the frontend.

---

## 13. Build Order (U0 to U10)

| Step | Build | Done when |
| --- | --- | --- |
| **U0** | Scaffold, install packages, shadcn init, fonts, folder layout, `APP_NAME` constant | `npm run dev` and `npm run build` pass |
| **U1** | `tokens.css`, Tailwind mapping, global classes, theme toggle, light and dark | A test page shows tokens, glass, glow, mesh in both themes |
| **U2** | `types.ts`, all mock data, `api.ts` with mock switch | Pages can import typed mock data |
| **U3** | Primitives: Button variants (gradient glow primary, glass secondary), GlassCard, Badge variants, Skeletons, EmptyState, ErrorState, toasts | A `/design-system` page shows every primitive |
| **U4** | Evidence and score components: RadialGauge (+ test), ScoreCard, ConfidenceBadge, ClaimChip, CitationMarker, SourceCard, Disclaimer, DimensionRadar, RiskMatrix, PositioningMap, DiffRow, ScoreBars | `/design-system` shows all with mock data; tests pass |
| **U5** | AppShell: GlassSidebar, TopBar, ProjectTabs, CommandPalette, NotificationsPopover; responsive behaviour | Navigation works on desktop, tablet, and mobile |
| **U6** | Auth pages, dashboard, New Project wizard (4 steps), `/welcome` | Full flow from login to a created mock project |
| **U7** | Understand page, analysis progress page (CrystalHero, PipelineTimeline, LogPanel), project overview | A mock run animates through six steps and lands on the overview |
| **U8** | Research, evaluation (+ drawer, risks tab, Devil's Advocate), improvement loop, version comparison | Evidence is clickable end to end; v1 vs v2 comparison works |
| **U9** | Blueprint pages (documents, architecture with Mermaid, UI/UX, roadmap Gantt), versions, documents, export | Regenerate-section UI works with mock; export success state shows |
| **U10** | Landing page with 3D hero, knowledge page, settings, 404 and error pages, mobile polish, accessibility and performance pass, switch from mock to live API where the backend exists | All routes in section 3 exist; checklist in section 14 passes |

Map to backend phases: U0 to U6 pair with Phase 1; U7 and U8 with Phases 2 and 3; U9 with Phases 4 and 5; U10 is final polish.

---

## 14. Acceptance Checklist

- [ ] The product is called **IdeaForm** everywhere; `APP_NAME` is used instead of literals.
- [ ] All routes in section 3 exist and render with mock data; each has loading, empty, and error states.
- [ ] Tokens drive all colours; light and dark both work and meet contrast.
- [ ] Showcase screens use the 3D crystal (with fallback), Product screens use polished 2D, Utility screens stay flat.
- [ ] Every score view shows explanation access, sources, assumptions, confidence, and the exact disclaimer.
- [ ] Charts present: radar, radial gauges, risk matrix, positioning map, diff bars, Gantt.
- [ ] Citations `[E#]` are clickable and open the matching source.
- [ ] Command palette (Ctrl/Cmd+K), notifications, theme toggle work.
- [ ] Reduced-motion, WebGL-failure, and mobile fallbacks work for 3D.
- [ ] Mobile layouts exist for dashboard, wizard, evaluation, and progress.
- [ ] `npm run lint`, `npm run build`, and unit tests pass; no secrets committed.
- [ ] `PROGRESS.md` is up to date.

---

## 15. Starter Prompts for the User

1. *"Read docs/UI_BUILD_GUIDE.md and knowledge.md. Summarise the UI plan in 10 lines, then do step U0."*
2. *"Do the next step in section 13 of UI_BUILD_GUIDE.md and verify it."*
3. *"Build the RadialGauge and ScoreCard exactly as specified, with a Vitest test."*
4. *"Build the evaluation page from section 10 using mock data."*
5. *"Run the section 14 checklist and fix whatever fails."*
