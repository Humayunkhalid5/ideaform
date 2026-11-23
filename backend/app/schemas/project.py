"""Project, version and requirement schemas."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

Category = Literal["business", "software", "technology"]
HelpLevel = Literal["evaluate", "research", "blueprint", "everything"]
ProjectStatus = Literal["draft", "analysing", "ready", "failed", "archived"]
ReqType = Literal["functional", "non_functional", "constraint", "assumption"]
Priority = Literal["must", "should", "could"]


class ProjectCreate(BaseModel):
    title: str = Field(min_length=3, max_length=200)
    idea_text: str = Field(min_length=20, max_length=20_000)
    category: Category | None = None
    help_level: HelpLevel = "everything"


class ProjectUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=3, max_length=200)
    category: Category | None = None
    help_level: HelpLevel | None = None
    status: ProjectStatus | None = None


class RequirementOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    req_type: ReqType
    description: str
    priority: Priority | None = None
    source: str | None = None
    confirmed: bool = False


class RequirementPatch(BaseModel):
    id: uuid.UUID
    description: str | None = Field(default=None, min_length=3, max_length=2_000)
    priority: Priority | None = None
    confirmed: bool | None = None


class RequirementUpdateRequest(BaseModel):
    requirements: list[RequirementPatch] = Field(min_length=1, max_length=200)


class VersionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    version_no: int
    idea_text: str
    structured_idea: dict | None = None
    change_summary: str | None = None
    created_at: datetime


class ProjectOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str
    category: Category
    help_level: HelpLevel
    status: ProjectStatus
    current_version_id: uuid.UUID | None = None
    created_at: datetime
    updated_at: datetime


class ProjectDetail(ProjectOut):
    version: VersionOut | None = None
    requirements: list[RequirementOut] = Field(default_factory=list)
