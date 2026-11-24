# VentureAI: UI Design Brief for Google Stitch (via MCP)

> **For the coding agent (Freebuff or any MCP-capable agent):** Read this whole file first. Use the **Stitch MCP server** to design every screen listed in section 6, in the order given in section 3, using the shared design system in section 4 and the sample data in section 5. After each screen, fetch the HTML and screenshot and save them in the repo. Then rebuild the screens as a Next.js + TypeScript + Tailwind + shadcn/ui app (section 9).
>
> Product name: **VentureAI** (a placeholder; keep the name in one config constant so it can be renamed). Tagline: *From Idea to Implementation.*

---

## 1. Product Summary (what the UI is for)

VentureAI takes a business, software, or technology idea and returns a researched, evidence-based evaluation and a development-ready project blueprint.

Core user journey:
1. Sign in and create a **New Project** (category, idea description, help level).
2. Review the **extracted structure and requirements** and confirm.
3. Watch the **analysis progress** (research, evaluation, design, documents).
4. Read the **Research**, **Evaluation**, and **Blueprint** results with sources.
5. Use the **Improvement Loop** to change the idea and **compare versions**.
6. **Export** the project as PDF, Markdown, or ZIP.

Key UI principles:
- **Evidence first.** Every score and claim shows its sources, assumptions, and confidence. Never show a bare success percentage.
- **Honest.** Scores carry a visible note: *Scores are evidence-based estimates, not predictions of success.*
- **Calm and professional.** A tool for students, founders, and developers. Clear hierarchy, generous spacing, no clutter.
- **Section-level control.** Users can regenerate or edit one section without redoing everything.
- **Accessible.** WCAG AA contrast, visible focus states, keyboard navigation, labels on all controls, colour is never the only signal.

---

## 2. Stitch MCP Setup (for the user)

> Verify the current steps in Stitch's own documentation. The tool names below were current when this file was written.

1. Open **stitch.withgoogle.com**, sign in, and create an **API key** in Stitch settings (or use Google Cloud credentials).
2. Add the Stitch MCP server to Freebuff's MCP settings. Two common options:
   - **Official remote endpoint:** `https://stitch.googleapis.com/mcp` with your API key.
   - **Community server:** `npx @_davideast/stitch-mcp init` (guided auth), then `npx @_davideast/stitch-mcp doctor` to verify.
   ```json
   {
     "mcpServers": {
       "stitch": {
         "command": "npx",
         "args": ["@_davideast/stitch-mcp", "proxy"],
         "env": { "STITCH_API_KEY": "YOUR_KEY_HERE" }
       }
     }
   }
   ```
   (Adjust the command and arguments to the server you chose. Never commit the key. Keep it in an environment variable.)
3. Typical tools exposed: `create_project`, `list_projects`, `get_project`, `list_screens`, `get_screen`, `generate_screen_from_text`, and download tools for the screen **HTML** and **image**.

**If MCP does not work:** paste each prompt from section 6 into the Stitch web app, then export the HTML and screenshot and place them in `design/stitch/`.

---

## 3. Agent Workflow (follow in order)

1. `create_project` named **VentureAI**.
2. Generate **S00 Design System / Style Guide** first, from section 4. Treat it as the visual reference for everything else.
3. Generate screens **S01 to S22** from section 6, **one per call**. Start every prompt with the **Global Prompt Prefix** (section 4.1) so the style stays consistent. Use **desktop (web app)** unless the screen says *mobile*.
4. After each screen: call `get_screen`, save the HTML to `design/stitch/<screen-id>.html` and the image to `design/stitch/<screen-id>.png`.
5. Generate **2 variants** for S03 (Dashboard) and S12 (Evaluation) and pick the clearest.
6. If a screen drifts from the style guide (colours, fonts, spacing), regenerate it with the prefix and a one-line correction.
7. When all screens exist, write `design/stitch/INDEX.md` listing every screen, its route, and its file.
8. Then build the Next.js app (section 9). Do not paste raw Stitch HTML as the final code. Rebuild it as React components using the shared tokens and shadcn/ui.

---

## 4. Design System

### 4.1 Global Prompt Prefix (paste at the start of every Stitch prompt)

```
Design for VentureAI, an AI platform that researches, evaluates and plans business and software ideas. Style: clean, modern, professional SaaS dashboard. Light theme, white and soft slate-gray surfaces, indigo primary color (#4F46E5), teal accent (#0D9488), rounded 12px cards with subtle borders and very light shadows, generous whitespace, Inter font, clear typographic hierarchy, left sidebar navigation on desktop. Use consistent components: score cards, source chips, confidence badges, tabs, data tables, step indicators. Evidence-first look: every claim shows source and confidence. Desktop web app, 1440px wide, unless stated as mobile.
```

### 4.2 Colour tokens

| Token | Light value | Use |
| --- | --- | --- |
| `--primary` | #4F46E5 | Main buttons, active nav, links |
| `--primary-soft` | #EEF2FF | Selected rows, soft highlights |
| `--accent` | #0D9488 | Secondary actions, positive progress |
| `--bg` | #F8FAFC | Page background |
| `--surface` | #FFFFFF | Cards, panels |
| `--border` | #E2E8F0 | Dividers, card borders |
| `--text` | #0F172A | Main text |
| `--text-muted` | #64748B | Secondary text |
| `--success` | #16A34A | High score, verified |
| `--warning` | #D97706 | Medium score, assumption |
| `--danger` | #DC2626 | Low score, high risk, errors |
| `--info` | #7C3AED | AI suggestion label |

Dark theme: invert surfaces (bg #0B1020, surface #111827, border #1F2937, text #F1F5F9) and keep the same accent hues. Provide a theme toggle in the header.

### 4.3 Typography
- UI font: **Inter**. Code and diagrams: **JetBrains Mono**.
- Scale: H1 30/36 semibold, H2 24/32 semibold, H3 18/28 semibold, body 14/22, small 12/18.

### 4.4 Spacing, shape, motion
- 4px base grid (8, 12, 16, 24, 32). Card radius 12px, input and button radius 8px.
- Subtle motion only (150 to 200ms fades and slides). Respect reduced-motion settings.

### 4.5 Core components (design these on S00)
1. **Sidebar** (logo, nav items, user menu) and **top bar** (breadcrumbs, search, theme toggle, user).
2. **Buttons:** primary, secondary, ghost, destructive; sizes S/M/L; loading state.
3. **Score card:** dimension name, score out of 100 with a progress bar, colour by range (80+ green, 60 to 79 teal, 40 to 59 amber, below 40 red), confidence badge, one-line reason, "View evidence" link.
4. **Confidence badge:** Low / Medium / High (with icon, not colour alone).
5. **Claim label chips:** **Verified fact** (green, check icon), **Assumption** (amber, question icon), **AI suggestion** (violet, sparkle icon).
6. **Source chip / citation:** `[E1]` marker plus a card showing title, domain, date, and an open-link icon.
7. **Step indicator** (wizard) and **progress timeline** (agent run).
8. **Tabs** for the project workspace: Overview, Research, Evaluation, Blueprint, Versions, Documents, Export.
9. **Data table** (sortable) for competitors and projects.
10. **Diff row:** old value, arrow, new value, change badge (+8, -3).
11. **Editor panel** for Markdown artifacts with Edit / Preview toggle and a **Regenerate** button.
12. **Mermaid diagram viewer** frame with zoom and download.
13. **Disclaimer banner** (info style).
14. **Empty state, skeleton loader, error state, toast** components.

---

## 5. Sample Data (use the same data on every screen so the design feels real)

**User:** Ayesha Khan, ayesha@example.com.

**Projects (dashboard):**
| Title | Category | Status | Updated | Versions |
| --- | --- | --- | --- | --- |
| Tutor Match | Software Project | Ready | 2 hours ago | 3 |
| Campus Food Bank | Business Startup | Analysing | 10 minutes ago | 1 |
| Smart Irrigation Sensor | Technology Product | Draft | Yesterday | 1 |
| Freelance Invoice Assistant | Software Project | Ready | 3 days ago | 2 |

**Main project: "Tutor Match"** (Software Project)
Idea text: *"An AI-powered platform that helps university students find affordable tutors."*

**Extracted structure:** Problem: students struggle to find affordable, trustworthy tutors. Target users: university students, tutors. Key features: tutor search, AI matching, booking, reviews, payments. Missing information: pricing model, target universities, platform (web or mobile).

**Requirements (examples):** Students can search tutors by subject and price (Must). Tutors can set availability (Must). Secure in-app payments (Should). Page load under 2 seconds (Non-functional, Should).

**Evaluation (illustrative scores):**
| Dimension | Score | Confidence | One-line reason |
| --- | --- | --- | --- |
| Technical feasibility | 85 | High | Core features use well-known technology |
| Market opportunity | 70 | Medium | Large student population, limited local data |
| Competition | 55 | Medium | Several established tutor platforms exist |
| Business model | 75 | Medium | Commission model is common in marketplaces |
| Resource requirements | 65 | Low | Cost estimates rely on assumptions |
| Execution complexity | 60 | Medium | Two-sided marketplace needs both sides at launch |

**Competitors (sample, fictional):** TutorHub (global tutor marketplace, commission 20%), StudyLink (subject-specific courses, subscription), CampusTutors (university-run peer tutoring, free). Columns: name, target customers, pricing, strengths, weaknesses, differentiation opportunity.

**Sources (sample):** "Example Market Report 2025" (example.org, 10 Mar 2025), "Online Tutoring Industry Overview" (example.com, 2 Jan 2025), "Marketplace Cold Start Guide" (example.net, 14 Aug 2024).

**Risks (sample):** Cold-start problem on a two-sided marketplace (High). Users arranging payments outside the platform (Medium). Tutor quality control (Medium).

**Improvement suggestions (sample):** Focus on one university first (affects Competition). Add a verified-tutor badge (affects Execution complexity). Offer a first-session guarantee (affects Business model).

**Version comparison (v1 to v2):** Competition 55 to 63 (+8), Execution complexity 60 to 66 (+6), Business model 75 to 74 (-1).

**Agents (progress screen):** Research Agent, Evaluation Agent, Business Agent, Product Design Agent, Technical Architect Agent, Documentation Agent.

**Blueprint artifacts:** PRD, Architecture (Mermaid diagram), Database schema (ER diagram), API specification, UI/UX concepts, Development roadmap.

---

## 6. Screens and Prompts

Routes are suggestions for the later Next.js build. Each prompt assumes the **Global Prompt Prefix** is pasted before it.

### S00. Design System / Style Guide (`/design-system`, internal)
```
Create a style guide page for VentureAI showing: color palette with the tokens listed (primary indigo, accent teal, success, warning, danger, info violet, neutrals), typography scale in Inter, buttons (primary, secondary, ghost, destructive, loading), form inputs, tabs, score cards at four score levels (88 green, 70 teal, 52 amber, 30 red), confidence badges (Low, Medium, High), claim label chips (Verified fact, Assumption, AI suggestion), source citation chips [E1] [E2], a step indicator, a progress timeline, a data table row, a diff row with +8 and -3 badges, a disclaimer banner, an empty state, a skeleton loader and a toast.
```

### S01. Landing Page (`/`)
```
Marketing landing page for VentureAI. Hero: headline "From Idea to Implementation", subheadline "VentureAI researches, validates, plans and designs your business, software or technology idea with evidence you can check." Primary button "Start a project", secondary "See how it works". Show a product preview card with six small score bars. Sections: "How it works" in 4 steps (Describe your idea, Research and evidence, Evaluate and improve, Get your blueprint), three category cards (Business Startup, Software Project, Technology Product), a feature grid (cited sources, six-dimension evaluation, improvement loop, version comparison, blueprint documents, export), an honesty note "Scores are evidence-based estimates, not predictions of success", FAQ accordion, final call to action, footer.
```

### S02. Sign In / Register (`/login`, `/register`)
```
Split-screen authentication page. Left: brand panel with logo, tagline and three short benefit bullets. Right: card with tabs Sign in / Create account, email and password fields with show-password toggle, full name field on register, primary submit button, "Forgot password" link, inline validation and error message states, small privacy note "Your projects are private to your account."
```

### S03. Dashboard (`/dashboard`)
```
Dashboard for a logged-in user with left sidebar (Dashboard, Projects, Knowledge Sources, Settings) and top bar. Header "Your projects" with primary button "New project". Summary row of 3 stat cards (Projects, Evaluations run, Ideas improved). Search input and filters (category, status). Grid of project cards showing title, category tag, status badge (Draft, Analysing with progress, Ready), last updated, version count, a mini bar of the six scores for ready projects, and a card menu (Open, Duplicate, Archive, Delete). Use the sample projects: Tutor Match, Campus Food Bank, Smart Irrigation Sensor, Freelance Invoice Assistant. Include an empty-state variant illustration for new users.
```

### S04. New Project, Step 1: Choose Category (`/projects/new`)
```
Wizard page with a step indicator (1 Category, 2 Describe, 3 Help level, 4 Review). Question "What do you want to build?" Three large selectable cards: Business Startup (evaluate business models, market, competitors, revenue, risks), Software Project (requirements, UI/UX, architecture, database, APIs, docs), Technology Product (technical feasibility, technologies, prototype needs, resources). Selected state with indigo border and check icon. Buttons Back (disabled) and Continue.
```

### S05. New Project, Step 2: Describe the Idea
```
Wizard step 2 titled "Describe your idea". Large textarea with placeholder "I want to build an AI-powered platform that helps university students find affordable tutors", character counter, tips panel on the right ("Who is it for?", "What problem does it solve?", "How do people solve it today?"), optional field for project title, optional upload area for private documents (PDF, DOCX, TXT, MD) with file chips. Buttons Back and Continue. Show a gentle inline hint if the text is too short.
```

### S06. New Project, Step 3: Help Level
```
Wizard step 3 titled "What do you want VentureAI to help with?" Four selectable option cards: Evaluate and validate my idea, Research competitors and the market, Create a complete software blueprint, Everything (complete project analysis, recommended badge). Each card lists what outputs it includes. A small estimate note "Analysis usually takes a few minutes". Buttons Back and Continue.
```

### S07. New Project, Step 4: Review and Preview
```
Wizard step 4 "Review and start". Left: summary card of category, idea text, help level with Edit links. Right: "Preview of VentureAI analysis" panel listing the outputs that will be created (idea understanding, research findings with links, feasibility report, competitor analysis, risks and improvements, business model, architecture, UI/UX concepts, documents). Primary button "Understand my idea", secondary "Save as draft".
```

### S08. Idea Understanding and Requirements (`/projects/[id]/understand`)
```
Review screen after NLP extraction. Header "Here is how VentureAI understood your idea". Left column: structured idea card with editable fields: one-line summary, category and sub-domain (with a mismatch notice if needed), problem, target users as chips, key features as chips, technologies mentioned. Right column: requirements list grouped as Functional, Non-functional, Constraints, Assumptions, each item with priority badge (Must, Should, Could), source tag (Extracted or AI suggestion), edit and delete icons, and an "Add requirement" button. Below: "Missing information" card with up to 5 clarifying questions and answer inputs. Bottom bar: "Confirm and start analysis" primary button, "Back to edit idea" secondary.
```

### S09. Analysis Progress (`/projects/[id]/run`)
```
Analysis progress screen. Large vertical timeline of six agent steps (Research Agent, Evaluation Agent, Business Agent, Product Design Agent, Technical Architect Agent, Documentation Agent), each with status icon (done, running with spinner, queued, failed), short description, elapsed time, and expandable log lines (for example "Searching for competitors", "Found 8 sources", "Scoring six dimensions"). Top: overall progress bar and percentage. Side card with sources found counter and tokens used. Buttons Cancel run and "Continue in background". Include an error state card with Retry for a failed step and a low-confidence warning when research found little evidence.
```

### S10. Project Workspace Overview (`/projects/[id]`)
```
Project workspace overview for "Tutor Match". Header with title, category tag, status badge, version selector dropdown (v3 current), and buttons Improve idea and Export. Tabs: Overview, Research, Evaluation, Blueprint, Versions, Documents, Export. Overview content: idea summary card, six mini score cards in a 3 by 2 grid with confidence badges, a radar or bar chart of the six dimensions, top 3 risks card, top 3 suggested improvements card with a "Start improvement loop" button, and a "Recent activity" list. Disclaimer banner at the top of the scores.
```

### S11. Research Tab (`/projects/[id]/research`)
```
Research tab. Top: summary of findings (sources found, competitors found, market notes). Left: filter list (All, Competitors, Market, Technical, Uploaded documents). Main: list of source cards with title, domain, publication date, retrieved date, short passage preview with highlighted keywords, claim label chips, citation marker [E1], and an open-link button. Second section: Competitor analysis data table with columns Name, Target customers, Pricing, Strengths, Weaknesses, Differentiation opportunity, and a Source link column. Add buttons "Run research again" and "Add source manually". Use the sample competitors TutorHub, StudyLink, CampusTutors.
```

### S12. Evaluation Tab (`/projects/[id]/evaluation`)
```
Evaluation tab, the most important screen. Disclaimer banner "Scores are evidence-based estimates, not predictions of success." Grid of six large score cards (Technical feasibility 85 High, Market opportunity 70 Medium, Competition 55 Medium, Business model 75 Medium, Resource requirements 65 Low, Execution complexity 60 Medium), each with a progress bar, confidence badge, one-line reason, recommendation preview and "View evidence" link. Below: tabs Summary, Risks, Devil's Advocate, Improvements and alternatives. Risks shown as a table with severity badge, likelihood, mitigation. Devil's Advocate as a distinct card titled "Why this idea might fail". Right rail: legend explaining claim labels (Verified fact, Assumption, AI suggestion) and the confidence levels. Buttons Regenerate evaluation and Start improvement loop.
```

### S13. Score Detail Drawer
```
Right-side drawer opened from a score card, for "Competition 55/100". Sections: Why this score (explanation paragraph with citation markers [E1] [E3]), Evidence (list of source cards with dates and links), Claims (each claim with label chip Verified fact, Assumption or AI suggestion), Assumptions (bullet list), Confidence (Medium with the rule explanation), Recommendations to improve the score (checklist with an "Add to improvement loop" button). Close button and keyboard focus trap indicated.
```

### S14. Improvement Loop (`/projects/[id]/improve`)
```
Improvement loop screen with a 6-step stepper (Original idea, Analyse, Weaknesses, Suggestions, Your changes, Re-evaluate) with the current step highlighted. Main area: list of suggestion cards, each with title, rationale, expected effect and the affected dimension chip, and three actions Accept, Reject, Edit. Right panel: live "New idea version" draft showing the rewritten idea text with accepted changes highlighted, and a summary "3 accepted, 1 rejected, 1 edited". Bottom bar: button "Create version 2 and re-evaluate" and "Cancel".
```

### S15. Version Comparison (`/projects/[id]/compare`)
```
Version comparison screen comparing v1 and v2 with two dropdown selectors. Top: change summary text. Section 1: table of six dimensions with columns v1 score, v2 score, change badge (+8, +6, -1 with arrows), and a one-sentence reason for each change. Section 2: side-by-side idea text with highlighted additions and removals. Section 3: Risks added and removed lists. Section 4: Requirements changed. Include a small bar chart comparing v1 and v2 scores. Footer button "Make v2 the current version".
```

### S16. Blueprint Tab (`/projects/[id]/blueprint`)
```
Blueprint tab. Left sidebar list of artifacts (PRD, Architecture, Database schema, API specification, UI/UX concepts, Business model, Development roadmap), each with a status dot and version number. Main area: document panel with title, Edit / Preview toggle, rendered Markdown content, and toolbar with Regenerate section (opens a small box to add instructions), Version history, Copy, Download. For the Architecture artifact show an embedded Mermaid component diagram viewer with zoom controls. Show a small "Generated from evaluation v3" note and a user-edited badge when edited.
```

### S17. Database Schema and API Spec View
```
Two-panel screen inside the Blueprint tab. Left: entity relationship diagram with tables as boxes (users, projects, project_versions, evaluations, competitors) and connecting lines. Right: tab switcher Schema SQL and API endpoints; the API view shows a table of Method (GET, POST, PATCH colored tags), Endpoint, Purpose. Include a code block with monospace font, a copy button, and a Regenerate button.
```

### S18. Versions and History (`/projects/[id]/versions`)
```
Version history screen with a vertical timeline of idea versions (v1, v2, v3 current). Each item shows date, change summary, who edited, score delta chips, and buttons View, Compare with previous, Restore. A second section lists artifact versions with a filter by artifact type.
```

### S19. Documents / Private Knowledge (`/projects/[id]/documents`)
```
Documents tab for private project knowledge. Drag-and-drop upload area (PDF, DOCX, TXT, MD), list of uploaded files with status (Uploading, Processing, Indexed, Failed), size, chunk count, date and delete button. Privacy note "Only you can see these documents. They are never added to the public knowledge base." A search box "Ask your project documents" with sample answer card showing citations.
```

### S20. Export (`/projects/[id]/export`)
```
Export screen or modal. Choose format cards: PDF report, Markdown files, ZIP package (all artifacts). Checklist of items to include (Feasibility report, Competitor analysis, Business model, Risk assessment, PRD, Architecture, Database schema, API spec, UI/UX concepts, Roadmap, Sources list). Option "Include version history". Primary button "Generate export", then a progress state and a success state with a download button.
```

### S21. Knowledge Sources (`/knowledge`)
```
Knowledge sources screen showing the public knowledge base. Top stats: documents, chunks, sources by KB-A Business and KB-B Technical. Searchable table with columns Title, Source type (Wikipedia, World Bank, arXiv, Documentation, GitHub, Manual), KB badge, Category, Licence note, Retrieved date, URL. A "Test retrieval" box where the user types a query and sees top passages with similarity score, source and date. Admin-style, clean and dense.
```

### S22. Settings and Usage (`/settings`)
```
Settings page with tabs Profile, Preferences, Usage, Security. Profile: name, email. Preferences: theme (light, dark, system), default help level, language. Usage: daily token limit progress bar, runs this week chart, cost-saving toggle "Use faster model for drafts". Security: change password, active sessions, delete account with confirmation modal.
```

### S23. System States (design as one sheet)
```
Sheet showing empty states (no projects, no sources found, no versions yet), loading skeletons (dashboard cards, score cards, document panel), error states (analysis failed with retry, search API unavailable, session expired), a 404 page, and toast notifications (success, warning, error).
```

### S24. Mobile Screens (mobile, 390px wide)
```
Design these as mobile screens with a bottom tab bar (Home, Projects, New, Settings): (1) Dashboard with stacked project cards, (2) New project wizard step 2 with large textarea, (3) Evaluation tab with six score cards in a single column and swipeable tabs, (4) Score detail as a bottom sheet, (5) Analysis progress timeline.
```

---

## 7. Interaction and Content Rules

- **Wizard:** keyboard accessible; Continue disabled until required fields are valid; progress is saved as a draft.
- **Long tasks:** always show progress; the user can leave and return; a toast and a badge show when results are ready.
- **Citations:** `[E#]` markers are clickable and scroll to or open the matching source card.
- **Claim labels:** always shown next to factual statements in Evaluation and Research.
- **Regeneration:** opens a small box for optional instructions and shows a confirmation that previous versions are kept.
- **Destructive actions** (delete project, delete document) need a confirmation modal that names the item.
- **Copy tone:** plain, direct, encouraging. Avoid hype and never promise success.
- **Disclaimer text (use exactly):** "Scores are evidence-based estimates, not predictions of business success."

---

## 8. Responsive and Accessibility Requirements

- Breakpoints: mobile 390, tablet 768, desktop 1280 to 1440. Sidebar collapses to icons on tablet and to a bottom tab bar on mobile.
- Tables scroll horizontally inside their own container on small screens. Page body never scrolls sideways.
- Text contrast at least 4.5:1; focus rings 2px indigo; touch targets at least 44px on mobile.
- Do not rely on colour alone: score cards include numbers and labels; chips include icons.
- Provide alt text and aria labels for charts and icon buttons.

---

## 9. Handoff: Build the App from the Designs

Target stack: **Next.js (App Router) + TypeScript + Tailwind CSS + shadcn/ui**, charts with **Recharts**, diagrams with **Mermaid**. The backend is FastAPI (separate service).

### 9.1 Route map
| Route | Screen |
| --- | --- |
| `/` | S01 Landing |
| `/login`, `/register` | S02 |
| `/dashboard` | S03 |
| `/projects/new` | S04 to S07 (wizard, step in URL or state) |
| `/projects/[id]/understand` | S08 |
| `/projects/[id]/run` | S09 |
| `/projects/[id]` | S10 Overview |
| `/projects/[id]/research` | S11 |
| `/projects/[id]/evaluation` | S12 (+ S13 drawer) |
| `/projects/[id]/improve` | S14 |
| `/projects/[id]/compare` | S15 |
| `/projects/[id]/blueprint` | S16, S17 |
| `/projects/[id]/versions` | S18 |
| `/projects/[id]/documents` | S19 |
| `/projects/[id]/export` | S20 |
| `/knowledge` | S21 |
| `/settings` | S22 |

### 9.2 Folder layout
```
frontend/
  app/                    # routes above
  components/
    ui/                   # shadcn/ui primitives
    layout/               # Sidebar, TopBar, ProjectTabs
    scores/               # ScoreCard, ConfidenceBadge, ScoreDrawer, ScoreChart
    evidence/             # ClaimChip, SourceCard, CitationMarker
    wizard/               # StepIndicator, CategoryCard, HelpLevelCard
    run/                  # AgentTimeline
    compare/              # DiffRow, VersionCompare
    blueprint/            # ArtifactList, MarkdownEditor, MermaidViewer
    states/               # EmptyState, Skeletons, ErrorState
  lib/
    tokens.css            # CSS variables from section 4.2 (light and dark)
    api.ts                # typed client for the FastAPI backend
    types.ts              # Project, Version, Evaluation, Dimension, Source, Artifact
    mock/                 # sample data from section 5 for development
```

### 9.3 Build rules
1. Put the colour tokens in `tokens.css` and map them in `tailwind.config` so components never use hard-coded colours.
2. Build the shared components first (section 4.5), then pages.
3. Start with **mock data** from section 5 so every page works before the backend exists. Replace it with API calls through `lib/api.ts` later.
4. Keep the product name in one constant (`APP_NAME`).
5. Add loading, empty, and error states to every data-driven page.
6. Use Server Components where possible and Client Components only for interactive parts (wizard, drawers, editors, charts).
7. Do not store secrets or API keys in the frontend.

### 9.4 Backend endpoints the UI will call
`POST /auth/login`, `POST /auth/register`, `GET/POST /projects`, `GET/PATCH/DELETE /projects/{id}`, `POST /projects/{id}/understand`, `PATCH /projects/{id}/requirements`, `POST /projects/{id}/analyse`, `GET /runs/{run_id}`, `GET /projects/{id}/sources`, `GET /projects/{id}/evaluations?version=`, `POST /projects/{id}/improve`, `GET /projects/{id}/compare?a=&b=`, `GET /projects/{id}/artifacts`, `POST /projects/{id}/artifacts/{type}/regenerate`, `PATCH /artifacts/{id}`, `POST /projects/{id}/documents`, `POST /projects/{id}/export`.

---

## 10. Acceptance Checklist

- [ ] All screens S00 to S24 exist in Stitch and their HTML and PNG files are saved in `design/stitch/`.
- [ ] `design/stitch/INDEX.md` maps each screen to its route and file.
- [ ] Colours, fonts, spacing, and components are consistent across all screens.
- [ ] Every score is shown with explanation access, sources, assumptions, and a confidence badge.
- [ ] The disclaimer text appears wherever scores are shown.
- [ ] Mobile versions exist for the dashboard, wizard, evaluation, and progress screens.
- [ ] Light and dark themes both work and meet contrast requirements.
- [ ] The Next.js app reproduces the designs with shared components and mock data.
- [ ] No API keys or secrets are committed.

---

## 11. Notes for the Team

- This brief describes the interface for the lab prototype. Phase 1 to 4 screens (S01 to S12, S14 to S16, S20) are the core. S17 to S19, S21, S22, and S24 can follow if time allows.
- Keep the generated Stitch designs as the visual reference, but treat the React components as the source of truth for code.
- Update the sample data and prompts here if the product name, scoring dimensions, or flows change.
