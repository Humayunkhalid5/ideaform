"""Research (Phase 2): run the Research Agent, list sources, upload documents, search.

Every endpoint is owner-only (others get 404) and every search applies the
isolation rule: public KB-A/B plus this project's own KB-C.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.api.projects import _dispatch, _version_or_409, get_owned_project
from app.config import get_settings
from app.db.session import get_db
from app.models.project import Project
from app.models.research import ResearchChunk, ResearchSource
from app.models.scrape import CrawlPage, ScrapeJob
from app.models.user import User
from app.schemas.research import (
    CrawlPageOut,
    DocumentUploadOut,
    KnowledgeStats,
    PassageOut,
    ResearchRequest,
    ScrapeJobOut,
    SearchRequest,
    SearchResponse,
    SourceDetail,
    SourceOut,
)
from app.services.knowledge import retrieval
from app.services.knowledge.ingest import DocumentIn, ingest_document
from app.services.knowledge.loaders import UnsupportedDocument, load_file
from app.services.knowledge.vector_store import uses_pgvector
from app.services.quota import ensure_within_quota
from app.services.research.discovery import credits_used_today

router = APIRouter(tags=["research"])


def _source_out(db: Session, source: ResearchSource) -> SourceOut:
    out = SourceOut.model_validate(source)
    out.chunk_count = db.scalar(
        select(func.count()).select_from(ResearchChunk).where(ResearchChunk.source_id == source.id)
    ) or 0
    first = db.scalar(
        select(ResearchChunk.content)
        .where(ResearchChunk.source_id == source.id)
        .order_by(ResearchChunk.chunk_index)
        .limit(1)
    )
    out.preview = (first[:400] + "…") if first and len(first) > 400 else first
    return out


def _passage_out(p: retrieval.Passage) -> PassageOut:
    return PassageOut(
        chunk_id=p.chunk_id, source_id=p.source_id, kb=p.kb, chunk_index=p.chunk_index,
        content=p.content, title=p.title, url=p.url, publisher=p.publisher,
        source_type=p.source_type, published_at=p.published_at, retrieved_at=p.retrieved_at,
        licence_note=p.licence_note, score=p.score, ranks=p.ranks,
    )


def _owned_source(db: Session, project: Project, source_id: uuid.UUID) -> ResearchSource:
    source = db.get(ResearchSource, source_id)
    if source is None or source.kb != "C" or source.project_id != project.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Source not found.")
    return source


@router.post("/projects/{project_id}/research", status_code=status.HTTP_202_ACCEPTED)
def start_research(
    payload: ResearchRequest | None = None,
    project: Project = Depends(get_owned_project),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, str]:
    """Run the Research Agent: plan queries, discover with Tavily, crawl into KB-C."""
    payload = payload or ResearchRequest()
    version = _version_or_409(db, project)
    ensure_within_quota(db, current_user)
    options = {}
    if payload.queries:
        options["extra_queries"] = [q for q in payload.queries if q.strip()]
    if payload.urls:
        options["extra_urls"] = [str(u) for u in payload.urls]
    return _dispatch(db, project, version, "research", "research_project", options)


@router.get("/projects/{project_id}/sources", response_model=list[SourceOut])
def list_sources(
    project: Project = Depends(get_owned_project),
    db: Session = Depends(get_db),
    source_type: str | None = Query(default=None),
) -> list[SourceOut]:
    """The project's private sources (KB-C): research pages and uploads."""
    stmt = select(ResearchSource).where(
        ResearchSource.kb == "C", ResearchSource.project_id == project.id
    )
    if source_type:
        stmt = stmt.where(ResearchSource.source_type == source_type)
    rows = db.scalars(stmt.order_by(ResearchSource.retrieved_at.desc())).all()
    return [_source_out(db, s) for s in rows]


@router.get("/projects/{project_id}/sources/{source_id}", response_model=SourceDetail)
def read_source(
    source_id: uuid.UUID,
    project: Project = Depends(get_owned_project),
    db: Session = Depends(get_db),
) -> SourceDetail:
    source = _owned_source(db, project, source_id)
    detail = SourceDetail(**_source_out(db, source).model_dump())
    chunks = db.scalars(
        select(ResearchChunk)
        .where(ResearchChunk.source_id == source.id)
        .order_by(ResearchChunk.chunk_index)
    ).all()
    detail.passages = [
        PassageOut(
            chunk_id=c.id, source_id=source.id, kb=c.kb, chunk_index=c.chunk_index,
            content=c.content, title=source.title, url=source.url, publisher=source.publisher,
            source_type=source.source_type, published_at=source.published_at,
            retrieved_at=source.retrieved_at, licence_note=source.licence_note,
        )
        for c in chunks
    ]
    return detail


@router.delete(
    "/projects/{project_id}/sources/{source_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_model=None,
)
def delete_source(
    source_id: uuid.UUID,
    project: Project = Depends(get_owned_project),
    db: Session = Depends(get_db),
) -> None:
    db.delete(_owned_source(db, project, source_id))  # chunks and embeddings cascade
    db.commit()


@router.post(
    "/projects/{project_id}/documents",
    response_model=DocumentUploadOut,
    status_code=status.HTTP_201_CREATED,
)
async def upload_document(
    file: UploadFile = File(...),
    project: Project = Depends(get_owned_project),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> DocumentUploadOut:
    """Upload a PDF, DOCX, TXT or MD file into this project's private KB-C."""
    limit = get_settings().max_upload_bytes
    data = await file.read(limit + 1)
    if len(data) > limit:
        raise HTTPException(
            413, f"File is larger than {limit // 1_000_000} MB."
        )
    if not data:
        raise HTTPException(422, "The file is empty.")
    filename = file.filename or "upload.txt"
    try:
        loaded = load_file(data, filename)
    except UnsupportedDocument as exc:
        raise HTTPException(status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, str(exc)) from exc

    result = ingest_document(
        db,
        DocumentIn(
            title=loaded.title,
            text=loaded.text,
            kb="C",
            url=None,
            source_type="upload",
            publisher=current_user.full_name or current_user.email,
            licence_note="Private upload: visible only to this project",
            attribution=f"Uploaded by the project owner ({filename})",
            category=project.category,
            adapter="upload",
            user_id=current_user.id,
            project_id=project.id,
        ),
        min_words=5,
    )
    if result.status == "rejected":
        db.rollback()
        raise HTTPException(422, f"Not ingested: {result.reason}")
    db.commit()
    source = db.get(ResearchSource, result.source_id)
    return DocumentUploadOut(status=result.status, source=_source_out(db, source))


@router.post("/projects/{project_id}/search", response_model=SearchResponse)
def search_knowledge(
    payload: SearchRequest,
    project: Project = Depends(get_owned_project),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> SearchResponse:
    """Hybrid retrieval over KB-A/B and this project's KB-C (the internal retrieval service)."""
    passages = retrieval.search(
        db,
        payload.query,
        scope=retrieval.Scope(user_id=current_user.id, project_id=project.id),
        filters=retrieval.Filters(
            kbs=payload.kbs,
            categories=payload.categories,
            source_types=payload.source_types,
            published_after=payload.published_after,
        ),
        mode=payload.mode,
        rerank=payload.rerank,
        k=payload.k,
    )
    return SearchResponse(
        query=payload.query,
        mode=payload.mode,
        passages=[_passage_out(p) for p in passages],
        evidence_block=retrieval.format_evidence(passages),
    )


@router.get("/projects/{project_id}/crawl", response_model=list[ScrapeJobOut])
def list_crawl_jobs(
    project: Project = Depends(get_owned_project),
    db: Session = Depends(get_db),
    limit: int = Query(default=5, ge=1, le=50),
) -> list[ScrapeJobOut]:
    """Provenance: recent scrape jobs with every URL's robots decision and status."""
    jobs = db.scalars(
        select(ScrapeJob)
        .where(ScrapeJob.project_id == project.id)
        .order_by(ScrapeJob.created_at.desc())
        .limit(limit)
    ).all()
    out = []
    for job in jobs:
        item = ScrapeJobOut.model_validate(job)
        item.pages = [
            CrawlPageOut.model_validate(p)
            for p in db.scalars(
                select(CrawlPage).where(CrawlPage.job_id == job.id).order_by(CrawlPage.fetched_at)
            )
        ]
        out.append(item)
    return out


@router.get("/knowledge/stats", response_model=KnowledgeStats)
def knowledge_stats(
    db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
) -> KnowledgeStats:
    """Size of the shared knowledge bases (KB-C counted for the caller only)."""
    def count(model, kb: str) -> int:
        stmt = select(func.count()).select_from(model).where(model.kb == kb)
        if kb == "C":
            stmt = stmt.where(model.user_id == current_user.id)
        return db.scalar(stmt) or 0

    column = "vector(384)" if uses_pgvector(db) else "real[] (pgvector not installed)"
    return KnowledgeStats(
        kb={kb: count(ResearchSource, kb) for kb in "ABC"},
        chunks={kb: count(ResearchChunk, kb) for kb in "ABC"},
        embedding_column=column,
        tavily_credits_today=credits_used_today(db),
        tavily_daily_cap=get_settings().tavily_daily_credit_cap,
    )
