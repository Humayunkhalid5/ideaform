# Ideaform: Software Requirements Specification (SRS)

| Field | Value |
| --- | --- |
| Project | Ideaform: From Idea to Implementation |
| Document | SRS.md |
| Version | 1.0 (blueprint freeze) |
| Course | AI / ML / NLP / LLMs and Agent-Based Systems (Lab Project) |
| Team | [Student names and IDs] |
| Related docs | architecture.md, database_design.md, implementation_plan.md, AI_DESIGN.md |

---

## 1. Introduction

### 1.1 Purpose
This document defines the functional and non-functional requirements of Ideaform, an AI-powered platform that researches, evaluates, designs, and documents business, software, and technology ideas. It is the reference for design, implementation, and testing.

### 1.2 Problem statement
People with an idea cannot easily judge feasibility, find competitors, or turn the idea into a plan. Generic AI tools return one unexplained score with no evidence. Ideaform produces **evidence-based, structured, sourced** analysis and a development-ready project blueprint.

### 1.3 Scope
Ideaform **will**:
- accept a free-text idea in one of three categories (Business Startup, Software Project, Technology Product);
- understand the idea with NLP and extract structured requirements;
- research competitors and the market using a self-hosted web scraper and a RAG knowledge base;
- produce a multi-dimension feasibility evaluation with citations, assumptions, and confidence;
- let the user improve the idea and compare evaluation versions;
- generate blueprint artifacts (PRD, architecture, database schema, API spec, UI/UX concepts, roadmap);
- store versions and export results as PDF, Markdown, and ZIP.

Ideaform **will not** (first release):
- write or deploy a full production application autonomously;
- train its own large language model;
- crawl the entire internet;
- predict the probability of startup success;
- produce Figma-quality editable designs;
- run complex financial simulations;
- call any third-party **AI** API: all reasoning runs on local models. The single external service is Tavily, used only to discover URLs for live research; page content is fetched by our own scraper.

### 1.4 Definitions
| Term | Meaning |
| --- | --- |
| RAG | Retrieval-Augmented Generation: retrieving relevant text and giving it to an LLM as context |
| Hybrid search | Combination of semantic (vector), keyword, metadata filtering, and reranking |
| Agent | An LLM-driven component with a defined role, prompt, and tools |
| Orchestrator | The central workflow that coordinates agents and shared services |
| Artifact | A generated output such as a PRD, diagram, or report |
| KB-A / KB-B / KB-C | Business, Technical, and Project knowledge collections |
| Claim label | Each statement is tagged `verified_fact`, `assumption`, or `ai_suggestion` |

### 1.5 Intended users
| User | Description | Main needs |
| --- | --- | --- |
| Student / Founder | Has an idea and little market knowledge | Validation, competitors, MVP scope |
| Software team lead | Has a software idea | Requirements, architecture, roadmap |
| Product innovator | Has a technology concept | Feasibility, resources, challenges |
| Instructor / evaluator | Reviews the lab project | Understand the pipeline, see test results |

---

## 2. Overall Description

### 2.1 Product perspective
A web application with a Next.js frontend, a FastAPI backend, PostgreSQL + pgvector storage, Redis/Celery for background jobs, a **locally hosted LLM runtime**, a **self-hosted scraper** for page content, and **Tavily** for live URL discovery. No AI provider API is used at run time. The six architecture layers are described in `architecture.md`.

### 2.2 Product functions (summary)
1. Account and project management
2. Idea understanding (NLP)
3. Research and knowledge retrieval (web + RAG)
4. Evaluation and improvement loop
5. Blueprint generation
6. Workspace, versioning, and export

### 2.3 Operating environment
- Browser: latest Chrome, Edge, Firefox, Safari.
- Server: Docker containers (Linux); developed on Windows/macOS/Linux with Docker Desktop.
- External services: Tavily (URL discovery only, key required); a local model runtime (Ollama, or in-process transformers); public web pages reached by the scraper; free public data endpoints for the knowledge bases (SEC EDGAR, GLEIF, World Bank, Wikidata, Hacker News).

### 2.4 Constraints
- Lab time and team size limit the scope to Phases 1 to 4 (plus orchestration and export if time allows).
- Only pre-trained models and public/permitted data are used.
- No third-party AI APIs: all model inference runs locally, bounded by the machine's CPU/GPU, RAM, and disk.
- Tavily is the only paid external dependency and has a quota and per-request cost; live research must degrade gracefully when it is exhausted.
- Scraping is bounded by robots.txt, site terms of service, per-domain rate limits, and anti-bot protections.
- Web content must be used within permitted terms and cited, not copied.

### 2.5 Assumptions and dependencies
- Users have a stable internet connection for scraping (a pre-scraped corpus is kept as backup for offline demos).
- The local model runs within the demo machine's memory budget (cached sample runs are kept as backup).
- A Tavily API key with enough quota for demos is available, and cached discovery results cover quota exhaustion.
- Users provide ideas in English (first version).

---

## 3. Functional Requirements

Priority: **M** = Must (lab core), **S** = Should, **C** = Could (future).

### 3.1 Authentication and accounts (FR-AUTH)
| ID | Requirement | Priority |
| --- | --- | --- |
| FR-AUTH-1 | The system shall allow users to register with email and password. | M |
| FR-AUTH-2 | The system shall allow users to log in and log out securely (hashed passwords, token-based sessions). | M |
| FR-AUTH-3 | The system shall restrict each user to their own projects and documents. | M |
| FR-AUTH-4 | The system shall support password reset. | C |

### 3.2 Project management (FR-PROJ)
| ID | Requirement | Priority |
| --- | --- | --- |
| FR-PROJ-1 | The system shall let users create a project by choosing a category and describing the idea. | M |
| FR-PROJ-2 | The system shall let users choose the help level: Evaluate, Research, Blueprint, or Everything. | M |
| FR-PROJ-3 | The system shall display a dashboard listing the user's projects with status and last update. | M |
| FR-PROJ-4 | The system shall let users edit, archive, and delete projects. | M |
| FR-PROJ-5 | The system shall keep a version history of the idea and its evaluations. | M |

### 3.3 Idea understanding / NLP (FR-NLP)
| ID | Requirement | Priority |
| --- | --- | --- |
| FR-NLP-1 | The system shall classify the idea into a category and sub-domain. | M |
| FR-NLP-2 | The system shall extract target users, problem, key features, and technologies mentioned. | M |
| FR-NLP-3 | The system shall generate functional and non-functional requirement candidates from the idea. | M |
| FR-NLP-4 | The system shall show the extracted structure and let the user correct it before analysis. | M |
| FR-NLP-5 | The system shall flag missing information and ask clarifying questions. | S |

### 3.4 Research and knowledge (FR-RES)
| ID | Requirement | Priority |
| --- | --- | --- |
| FR-RES-1 | The system shall discover competitors, market information, and similar products with Tavily, then fetch and extract the pages with its own scraper. | M |
| FR-RES-2 | The system shall store each source with URL, title, retrieval date, and extracted passages. | M |
| FR-RES-3 | The system shall ingest documents into the knowledge bases (clean, chunk, embed, tag). | M |
| FR-RES-4 | The system shall support hybrid search (semantic + keyword + metadata filter + rerank). | M |
| FR-RES-5 | The system shall let users upload their own documents (PDF, DOCX, TXT, MD) into private Project Knowledge (KB-C). | S |
| FR-RES-6 | The system shall label every statement as `verified_fact`, `assumption`, or `ai_suggestion`. | M |
| FR-RES-7 | The system shall keep private project knowledge isolated from public knowledge and from other users. | M |
| FR-RES-8 | The system shall respect robots.txt, site terms, and per-domain rate limits before every fetch, and shall record the permission decision. | M |
| FR-RES-9 | The system shall record for every fetched page its URL, HTTP status, robots decision, fetch timestamp, and content hash. | M |
| FR-RES-10 | The system shall run all reasoning on local models: no third-party AI API shall be called at run time, and Tavily shall be used only for URL discovery. | M |
| FR-RES-11 | The system shall build the shared knowledge bases from the curated source catalogue (SEC EDGAR, GLEIF, World Bank, OECD/Eurostat, Wikipedia/Wikidata, Hacker News, open case studies, Kaggle/Hugging Face datasets, government reports), recording each source's licence and attribution. | M |
| FR-RES-12 | The system shall keep working when Tavily is unavailable or out of quota, falling back to cached discovery results and curated seed URLs. | S |

### 3.5 Evaluation (FR-EVAL)
| ID | Requirement | Priority |
| --- | --- | --- |
| FR-EVAL-1 | The system shall score six dimensions: technical feasibility, market opportunity, competition, business model, resource requirements, execution complexity. | M |
| FR-EVAL-2 | Each score shall include explanation, citations, assumptions, confidence level, and recommendations. | M |
| FR-EVAL-3 | The system shall produce a competitor analysis table. | M |
| FR-EVAL-4 | The system shall produce a business model summary (customers, pricing, revenue). | M |
| FR-EVAL-5 | The system shall list risks and a Devil's Advocate critique. | M |
| FR-EVAL-6 | The system shall display a notice that scores are illustrative estimates, not predictions of success. | M |
| FR-EVAL-7 | The system shall suggest improvements and alternative approaches. | M |

### 3.6 Idea Improvement Loop (FR-LOOP)
| ID | Requirement | Priority |
| --- | --- | --- |
| FR-LOOP-1 | The user shall be able to accept, reject, or edit each suggested improvement. | M |
| FR-LOOP-2 | The system shall create a new idea version from the accepted changes. | M |
| FR-LOOP-3 | The system shall re-evaluate the new version and show a side-by-side comparison with the previous version. | M |

### 3.7 Blueprint generation (FR-GEN)
| ID | Requirement | Priority |
| --- | --- | --- |
| FR-GEN-1 | The system shall generate a Product Requirements Document (PRD). | M |
| FR-GEN-2 | The system shall generate a system architecture description and Mermaid diagrams. | M |
| FR-GEN-3 | The system shall generate a database schema (tables, relationships). | M |
| FR-GEN-4 | The system shall generate an API specification. | M |
| FR-GEN-5 | The system shall generate UI/UX concepts (user flows, screen lists, wireframe descriptions). | S |
| FR-GEN-6 | The system shall generate a phased development roadmap. | M |
| FR-GEN-7 | The user shall be able to regenerate any single section without regenerating the whole project. | M |

### 3.8 Workspace and export (FR-EXP)
| ID | Requirement | Priority |
| --- | --- | --- |
| FR-EXP-1 | The system shall display all artifacts in an editable project workspace. | M |
| FR-EXP-2 | The system shall keep version history for each artifact. | S |
| FR-EXP-3 | The system shall export artifacts as Markdown and PDF. | M |
| FR-EXP-4 | The system shall export the complete project as a ZIP package. | S |

### 3.9 Orchestration and monitoring (FR-ORC)
| ID | Requirement | Priority |
| --- | --- | --- |
| FR-ORC-1 | The system shall coordinate six agents through a central orchestrator. | S |
| FR-ORC-2 | The system shall run long tasks in the background and show progress to the user. | M |
| FR-ORC-3 | The system shall record each agent run (inputs, outputs, status, duration, token usage). | S |
| FR-ORC-4 | The system shall handle failures with retries and clear error messages. | M |

### 3.10 Future features (not in first release)
Idea comparison, what-if simulator, MVP scope generator, project knowledge chat, architecture critic, customer validation planner, change impact analysis, progress tracker, code scaffolding, test generation, GitHub integration, security analysis (priority C).

---

## 4. Non-Functional Requirements

| ID | Category | Requirement |
| --- | --- | --- |
| NFR-1 | Performance | Page loads shall take under 2 seconds on a normal connection. A single section generation should complete within 60 seconds; a full analysis within 10 minutes, with progress shown. |
| NFR-2 | Reliability | Failed external calls shall be retried up to 3 times with backoff. Partial results shall be saved so work is not lost. |
| NFR-3 | Accuracy / Trust | Factual claims shall have a citation or be labelled as assumption or suggestion. Target at least 90% of cited claims point to a working source. |
| NFR-4 | Reproducibility | Prompts, model names, parameters, and retrieved sources for each run shall be stored so results can be traced and repeated as closely as possible. |
| NFR-5 | Security | Passwords hashed (bcrypt/argon2); API keys stored in environment variables, never in code; HTTPS in deployment; input validation on all endpoints. |
| NFR-6 | Privacy | Private projects and uploaded documents are visible only to their owner. Queries to public KBs shall never expose private data. |
| NFR-7 | Usability | A new user shall be able to create a project and get a first report within 5 minutes using the guided workflow. |
| NFR-8 | Maintainability | Modular engines, typed code (TypeScript, Python type hints), linting, README, and documented configuration. |
| NFR-9 | Portability | The whole system shall start with one command (`docker compose up`). |
| NFR-10 | Cost control | The system shall run AI inference at zero provider cost (local models, quantised settings, caching) and shall cap Tavily spending with per-user daily limits and a per-run search budget. |
| NFR-11 | Compliance | External sources are cited, not copied; licences of datasets and libraries are acknowledged. |
| NFR-12 | Scalability (design) | The design shall allow replacing the LLM provider, search provider, or any engine without rewriting the others. |

---

## 5. Use Cases

### UC-1: Create and analyse a project
- **Actor:** User
- **Precondition:** User is logged in.
- **Main flow:** (1) choose category; (2) describe the idea; (3) choose help level; (4) system extracts structure; (5) user confirms or corrects; (6) system researches, evaluates, and generates; (7) user views results.
- **Alternate flow:** Idea too vague, so the system asks clarifying questions.
- **Postcondition:** Project, version 1, evaluation, and artifacts are saved.

### UC-2: Improve an idea
- **Main flow:** User opens an evaluation, reviews suggested improvements, accepts/rejects/edits, system creates version 2, re-evaluates, and shows the comparison.

### UC-3: Regenerate a section
- **Main flow:** User selects a section (e.g., database schema), optionally adds instructions, and the system regenerates only that section and saves a new artifact version.

### UC-4: Upload private documents
- **Main flow:** User uploads files to a project, system ingests them into KB-C, and later answers and analysis can use them.

### UC-5: Export the project
- **Main flow:** User chooses PDF, Markdown, or ZIP, and the system compiles and offers a download.

---

## 6. Interface Requirements

### 6.1 User interface
- Guided "New Project" workflow (category, description, help level, preview).
- Dashboard, project workspace with tabs (Overview, Research, Evaluation, Blueprint, Versions, Export).
- Score cards with expandable explanation, sources, assumptions, and confidence.
- Diagrams rendered from Mermaid.

### 6.2 External interfaces
| Interface | Purpose |
| --- | --- |
| Local LLM runtime (Ollama or in-process transformers) | Reasoning and generation, no network calls |
| Tavily Search API | URL discovery for live web research (the only paid API) |
| Self-hosted scraper (httpx + Playwright) | Page fetching and passage extraction for discovered and curated URLs |
| robots.txt and site terms | Crawl-permission decision before every fetch |
| PostgreSQL / Redis | Storage and queue |

---

## 7. Acceptance Criteria (summary)

The lab prototype is accepted when:
1. A user can register, log in, create a project, and see extracted requirements.
2. For a sample idea, the system returns research findings with working source links.
3. A six-dimension evaluation is generated, each with explanation, citations, assumptions, and confidence.
4. The user can modify the idea and see a before/after comparison.
5. A PRD, architecture diagram, schema, API spec, and roadmap are generated and any one can be regenerated alone.
6. At least Markdown and PDF export work.
7. The system starts with `docker compose up` and passes the test plan in `AI_DESIGN.md` section 10.
8. The system completes a full analysis with **no AI-provider key configured** — only `TAVILY_API_KEY` — using the local model, Tavily discovery, and the self-hosted scraper.

---

## 8. Traceability

| Objective | Requirements |
| --- | --- |
| Understand ideas with NLP | FR-NLP-1 to 5 |
| Hybrid RAG with sources | FR-RES-1 to 7 |
| Evidence-based evaluation | FR-EVAL-1 to 7 |
| Improvement loop | FR-LOOP-1 to 3 |
| Blueprint generation | FR-GEN-1 to 7 |
| Workspace and export | FR-EXP-1 to 4 |
| Agent orchestration | FR-ORC-1 to 4 |
