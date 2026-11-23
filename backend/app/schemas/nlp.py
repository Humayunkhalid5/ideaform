"""Schemas for structured LLM output (validated, repaired once on failure)."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

Category = Literal["business", "software", "technology"]


class IdeaClassification(BaseModel):
    category: Category
    confidence: Literal["low", "medium", "high"]
    rationale: str = Field(max_length=600)


class StructuredIdea(BaseModel):
    category: Category
    problem: str
    target_users: list[str] = Field(default_factory=list)
    key_features: list[str] = Field(default_factory=list)
    technologies_mentioned: list[str] = Field(default_factory=list)
    missing_information: list[str] = Field(default_factory=list)


class RequirementItem(BaseModel):
    req_type: Literal["functional", "non_functional", "constraint", "assumption"]
    description: str = Field(max_length=1_000)
    priority: Literal["must", "should", "could"] = "should"
    source: Literal["extracted", "ai_suggestion"] = "extracted"


class RequirementList(BaseModel):
    requirements: list[RequirementItem] = Field(default_factory=list, max_length=40)
