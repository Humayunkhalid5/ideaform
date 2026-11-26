import type {
  Category,
  HelpLevel,
  Priority,
  ProjectStatus,
  RequirementType,
  StructuredIdea,
} from "./types";

export const CATEGORIES: {
  id: Category;
  title: string;
  blurb: string;
  bullets: string[];
}[] = [
  {
    id: "business",
    title: "Business",
    blurb: "A venture, service or go-to-market play.",
    bullets: ["Marketplaces", "Subscriptions", "Local services"],
  },
  {
    id: "software",
    title: "Software",
    blurb: "An app, tool or information system.",
    bullets: ["Web & mobile apps", "APIs and tools", "Automation"],
  },
  {
    id: "technology",
    title: "Technology",
    blurb: "A technical approach or capability.",
    bullets: ["Algorithms", "Hardware", "Infrastructure"],
  },
];

export const HELP_LEVELS: {
  id: HelpLevel;
  title: string;
  blurb: string;
  outputs: string[];
  time: string;
  recommended?: boolean;
}[] = [
  {
    id: "evaluate",
    title: "Evaluate it",
    blurb: "A clear read on whether the idea holds up.",
    outputs: ["Structured understanding", "Six-dimension score"],
    time: "About 2 minutes",
  },
  {
    id: "research",
    title: "Evaluate + research",
    blurb: "Adds market and competitor evidence.",
    outputs: ["Everything above", "Sources and competitors"],
    time: "About 4 minutes",
  },
  {
    id: "blueprint",
    title: "Through to blueprint",
    blurb: "Turns the analysis into buildable artifacts.",
    outputs: ["PRD, architecture, schema", "UI/UX and API spec"],
    time: "About 6 minutes",
  },
  {
    id: "everything",
    title: "Everything",
    blurb: "The full path, including a phased roadmap.",
    outputs: ["Every artifact", "Roadmap and business model"],
    time: "About 8 minutes",
    recommended: true,
  },
];

export const HELP_LEVEL_LABEL: Record<HelpLevel, string> = {
  evaluate: "Evaluate only",
  research: "Evaluate + research",
  blueprint: "Through to blueprint",
  everything: "Everything",
};

export const REQUIREMENT_GROUPS: { type: RequirementType; label: string; blurb: string }[] = [
  { type: "functional", label: "Functional", blurb: "What the product must do." },
  { type: "non_functional", label: "Non-functional", blurb: "Quality attributes." },
  { type: "constraint", label: "Constraints", blurb: "Limits you cannot change." },
  { type: "assumption", label: "Assumptions", blurb: "Taken as true for now." },
];

export const PRIORITY_LABEL: Record<Priority, string> = {
  must: "Must",
  should: "Should",
  could: "Could",
};

export const STATUS_LABEL: Record<ProjectStatus, string> = {
  draft: "Draft",
  analysing: "Analysing",
  ready: "Understood",
  failed: "Failed",
  archived: "Archived",
};

export function readStructured(value: unknown): StructuredIdea | null {
  if (!value || typeof value !== "object" || Array.isArray(value)) return null;
  const record = value as Record<string, unknown>;
  const strings = (key: string): string[] =>
    Array.isArray(record[key])
      ? (record[key] as unknown[]).filter((item): item is string => typeof item === "string")
      : [];
  const text = (key: string): string | undefined =>
    typeof record[key] === "string" ? (record[key] as string) : undefined;

  const idea: StructuredIdea = {
    problem: text("problem"),
    target_users: strings("target_users"),
    key_features: strings("key_features"),
    technologies_mentioned: strings("technologies_mentioned"),
    missing_information: strings("missing_information"),
  };
  const clarity = record.clarity as Record<string, unknown> | undefined;
  if (clarity && typeof clarity === "object" && typeof clarity.vague === "boolean") {
    const list = (v: unknown) => (Array.isArray(v) ? v.filter((x): x is string => typeof x === "string") : []);
    idea.clarity = { vague: clarity.vague, reasons: list(clarity.reasons), questions: list(clarity.questions) };
  }
  if (
    record.category === "business" ||
    record.category === "software" ||
    record.category === "technology"
  ) {
    idea.category = record.category;
  }
  return idea;
}
