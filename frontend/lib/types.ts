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
