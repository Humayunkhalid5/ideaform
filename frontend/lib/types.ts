export type Category = "business" | "software" | "technology";
export type HelpLevel = "evaluate" | "research" | "blueprint" | "everything";
export type ProjectStatus = "draft" | "analysing" | "ready" | "failed" | "archived";
export type RequirementType = "functional" | "non_functional" | "constraint" | "assumption";
export type Priority = "must" | "should" | "could";
export type Confidence = "low" | "medium" | "high";
export type ClaimLabel = "verified_fact" | "assumption" | "ai_suggestion";
export type DimensionKey =
  | "technical_feasibility"
  | "market_opportunity"
  | "competition"
  | "business_model"
  | "resource_requirements"
  | "execution_complexity";

export interface StructuredIdea {
  category?: Category;
  problem?: string;
  target_users?: string[];
  key_features?: string[];
  technologies_mentioned?: string[];
  missing_information?: string[];
}

export interface Requirement {
  id: string;
  req_type: RequirementType;
  description: string;
  priority: Priority | null;
  source: string | null;
  confirmed: boolean;
}

export interface Project {
  id: string;
  title: string;
  category: Category;
  help_level: HelpLevel;
  status: ProjectStatus;
  current_version_id: string | null;
  created_at: string;
  updated_at: string;
}

export interface ProjectVersion {
  id: string;
  version_no: number;
  idea_text: string;
  structured_idea: Record<string, unknown> | null;
  change_summary: string | null;
  created_at: string;
}

export interface VersionSummary {
  id: string;
  version_no: number;
  change_summary: string | null;
  parent_version_id: string | null;
  has_structure: boolean;
  is_current: boolean;
  created_at: string;
}

export interface VersionDetail extends ProjectVersion {
  parent_version_id: string | null;
  is_current: boolean;
  requirements: Requirement[];
}

export interface ProjectDetail extends Project {
  version: ProjectVersion | null;
  requirements: Requirement[];
}

export interface User {
  id: string;
  email: string;
  full_name: string | null;
  daily_token_limit: number | null;
  created_at: string;
}

export interface Run {
  id: string;
  project_id: string;
  version_id: string | null;
  agent_name: string;
  status: "queued" | "running" | "succeeded" | "failed";
  model_name: string | null;
  tokens_in: number | null;
  tokens_out: number | null;
  error_message: string | null;
  started_at: string | null;
  finished_at: string | null;
}

export type KnowledgeBase = "A" | "B" | "C";

export interface Source {
  id: string;
  kb: KnowledgeBase;
  title: string | null;
  url: string | null;
  publisher: string | null;
  source_type: string | null;
  published_at: string | null;
  retrieved_at: string;
  licence_note: string | null;
  attribution: string | null;
  restricted: boolean;
  adapter: string | null;
  category: string | null;
  chunk_count: number;
  preview: string | null;
}

export interface Passage {
  chunk_id: string;
  source_id: string;
  kb: KnowledgeBase;
  chunk_index: number;
  content: string;
  title: string | null;
  url: string | null;
  publisher: string | null;
  source_type: string | null;
  published_at: string | null;
  retrieved_at: string | null;
  licence_note: string | null;
  score: number;
  ranks: Record<string, number | boolean>;
}

export interface SourceDetail extends Source {
  passages: Passage[];
}

export interface SearchResult {
  query: string;
  mode: "hybrid" | "vector" | "keyword";
  passages: Passage[];
  evidence_block: string;
}

export interface CrawlPage {
  id: string;
  url: string;
  final_url: string | null;
  domain: string;
  http_status: number | null;
  robots_allowed: boolean;
  skip_reason: string | null;
  fetch_ms: number | null;
  discovery_source: string | null;
  source_id: string | null;
  error_message: string | null;
  fetched_at: string;
}

export interface ScrapeJob {
  id: string;
  run_id: string | null;
  status: string;
  pages_requested: number | null;
  pages_fetched: number | null;
  pages_skipped_robots: number | null;
  pages_rejected: number | null;
  started_at: string | null;
  finished_at: string | null;
  pages: CrawlPage[];
}

export interface ResearchSummary {
  queries: { query: string; intent: string; hits: number; origin: string }[];
  pages_requested: number;
  pages_fetched: number;
  pages_stored: number;
  pages_skipped_robots: number;
  pages_rejected: number;
  sources: number;
  unanswered_questions: string[];
  seconds: number;
}

export interface RunWithOutput extends Run {
  output: ResearchSummary | Record<string, unknown> | null;
}

export interface KnowledgeStats {
  kb: Record<KnowledgeBase, number>;
  chunks: Record<KnowledgeBase, number>;
  embedding_column: string;
  tavily_credits_today: number;
  tavily_daily_cap: number;
}

// ------------------------------------------------------------------ Phase 3: evaluation

export interface Claim {
  text: string;
  label: ClaimLabel;
  evidence_ids: string[];
}

export interface EvidenceRef {
  id: string;
  chunk_id: string;
  source_id: string;
  kb: KnowledgeBase;
  title: string | null;
  url: string | null;
  publisher: string | null;
  published_at: string | null;
  snippet: string;
}

export interface DimensionScore {
  dimension: DimensionKey;
  label: string;
  score: number;
  confidence: Confidence;
  explanation: string;
  evidence_ids: string[];
  claims: Claim[];
  assumptions: string[];
  recommendations: string[];
  change_reason: string | null;
  previous_score: number | null;
}

export type Level = "low" | "medium" | "high";

export interface EvaluationRisk {
  id: string;
  title: string;
  description: string;
  severity: Level;
  likelihood: Level;
  mitigation: string;
  dimension: DimensionKey | null;
  evidence_ids: string[];
}

export type Decision = "accepted" | "rejected" | "edited";

export interface ImprovementSuggestion {
  id: string;
  title: string;
  rationale: string;
  change: string;
  expected_effect: string;
  dimension_affected: DimensionKey | null;
  dimension_label: string;
  evidence_ids: string[];
  decision: Decision | null;
  edited_text?: string;
}

export interface CompetitorRow {
  id: string;
  name: string;
  website: string | null;
  description: string | null;
  target_customers: string | null;
  pricing: string | null;
  strengths: string[] | null;
  weaknesses: string[] | null;
  differentiation_opportunity: string | null;
  source_url: string | null;
  evidence_ids: string[] | null;
}

export interface BusinessModel {
  customer_segments: string[];
  value_proposition: string;
  channels: string[];
  revenue_streams: string[];
  cost_structure: string[];
  pricing_options: { name: string; model: string; price_point: string; rationale: string }[];
  key_metrics: string[];
  assumptions: string[];
  evidence_ids: string[];
}

export interface Evaluation {
  id: string;
  version_id: string;
  version_no: number;
  created_at: string;
  summary: string | null;
  overall_score: number | null;
  disclaimer: string | null;
  dimensions: DimensionScore[];
  risks: EvaluationRisk[];
  devils_advocate: string | null;
  critique: { hidden_assumptions?: string[]; must_be_true?: string[] };
  improvements: ImprovementSuggestion[];
  alternatives: string[];
  business_model: BusinessModel | null;
  competitors: CompetitorRow[];
  evidence: EvidenceRef[];
  notices: string[];
  baseline_evaluation_id: string | null;
  run_id: string | null;
  model_name: string | null;
  prompt_version: string | null;
}

export interface DimensionDiff {
  dimension: DimensionKey;
  label: string;
  score_a: number | null;
  score_b: number | null;
  delta: number | null;
  confidence_a: Confidence | null;
  confidence_b: Confidence | null;
  reason: string;
}

export interface Comparison {
  project_id: string;
  a: number;
  b: number;
  evaluation_a: string;
  evaluation_b: string;
  overall_a: number | null;
  overall_b: number | null;
  overall_delta: number | null;
  summary: string;
  dimensions: DimensionDiff[];
  risks_added: string[];
  risks_removed: string[];
  requirements_added: string[];
  requirements_removed: string[];
  idea_diff: { op: "equal" | "added" | "removed"; text: string }[];
  change_summary: string | null;
}
