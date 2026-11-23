"""Import every model so ``Base.metadata`` is complete for Alembic."""

from app.models.agent import AgentRun, ProjectArtifact
from app.models.evaluation import (
    Competitor,
    Evaluation,
    EvaluationDimension,
    EvaluationEvidence,
)
from app.models.project import (
    Project,
    ProjectFeedback,
    ProjectRequirement,
    ProjectVersion,
)
from app.models.research import Embedding, ResearchChunk, ResearchSource
from app.models.scrape import CrawlPage, ScrapeJob
from app.models.user import User

__all__ = [
    "AgentRun",
    "Competitor",
    "CrawlPage",
    "Embedding",
    "Evaluation",
    "EvaluationDimension",
    "EvaluationEvidence",
    "Project",
    "ProjectArtifact",
    "ProjectFeedback",
    "ProjectRequirement",
    "ProjectVersion",
    "ResearchChunk",
    "ResearchSource",
    "ScrapeJob",
    "User",
]
