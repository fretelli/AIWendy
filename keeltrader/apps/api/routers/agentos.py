from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from core.auth import get_current_user
from core.database import get_session
from domain.user.models import User
from services.agentos import AgentOSService
from services.agent_platform.report_kb import ReportKBService
from services.content_brief_sink import (
    ContentBriefRejectedError,
    ContentBriefSinkError,
    submit_content_brief,
)

router = APIRouter()


def service(session: AsyncSession, user: User) -> AgentOSService:
    return AgentOSService(session, user.id)


def bad_request(exc: ValueError) -> HTTPException:
    status = 404 if "not found" in str(exc).lower() else 400
    return HTTPException(status, str(exc))


class PortfolioAccountCreate(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    account_type: Literal["manual", "csv"] = "manual"
    base_currency: str = Field(default="CNY", min_length=3, max_length=12)


class PortfolioAccountUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=160)
    base_currency: str | None = Field(default=None, min_length=3, max_length=12)
    status: Literal["active", "archived"] | None = None


class PortfolioTransactionCreate(BaseModel):
    transaction_type: Literal["opening", "buy", "sell", "cash", "dividend", "fee", "transfer", "adjustment"]
    trade_date: date
    symbol: str | None = Field(default=None, max_length=80)
    name: str | None = Field(default=None, max_length=160)
    market: str = Field(default="CN", max_length=30)
    asset_class: str = Field(default="other", max_length=40)
    instrument_type: Literal["stock", "etf", "open_fund", "future", "option", "convertible_bond", "cash", "fx", "alternative", "manual"] | None = None
    provider_symbol: str | None = Field(default=None, max_length=100)
    currency: str = Field(default="CNY", max_length=12)
    quantity: Decimal = Decimal("0")
    price: Decimal | None = Field(default=None, gt=0)
    manual_price: Decimal | None = Field(default=None, gt=0)
    cash_amount: Decimal = Decimal("0")
    fee: Decimal = Field(default=Decimal("0"), ge=0)
    multiplier: Decimal = Field(default=Decimal("1"), gt=0)
    direction: Literal["long", "short"] = "long"
    expiry: date | None = None
    strike: Decimal | None = Field(default=None, gt=0)
    option_type: Literal["call", "put"] | None = None
    external_ref: str | None = Field(default=None, max_length=160)
    note: str | None = Field(default=None, max_length=2000)


class ManualPriceCreate(BaseModel):
    instrument_id: UUID
    price_date: date
    price: Decimal = Field(gt=0)
    currency: str = Field(min_length=3, max_length=12)
    source_note: str | None = Field(default=None, max_length=240)


class ImportPreview(BaseModel):
    account_id: UUID
    import_type: Literal["positions", "transactions", "nav"]
    filename: str = Field(min_length=1, max_length=255)
    csv_text: str = Field(min_length=1, max_length=10_000_000)
    mapping: dict[str, str] = Field(default_factory=dict)


class EvidenceRef(BaseModel):
    report_id: str = Field(min_length=1, max_length=160)
    title: str | None = Field(default=None, max_length=300)
    page: str | None = Field(default=None, max_length=40)
    section: str | None = Field(default=None, max_length=240)
    quote: str | None = Field(default=None, max_length=3000)


class HypothesisCreate(BaseModel):
    title: str = Field(min_length=1, max_length=240)
    thesis: str = Field(min_length=1, max_length=20_000)
    falsification: str = Field(min_length=1, max_length=10_000)
    evidence: list[EvidenceRef] = Field(default_factory=list, max_length=100)
    outcome: dict[str, Any] = Field(default_factory=dict)
    status: Literal["draft", "active", "confirmed", "invalidated", "archived"] = "draft"
    review_date: date | None = None
    created_by: Literal["user", "agent"] = "user"


class ContentBriefSubmit(BaseModel):
    project_type: Literal["article", "social", "drama", "podcast", "course", "other"] = "article"
    audience: str = Field(min_length=1, max_length=1000)
    objective: str = Field(min_length=1, max_length=1000)
    requested_channels: list[str] = Field(default_factory=list, max_length=20)


class DecisionCreate(BaseModel):
    title: str = Field(min_length=1, max_length=240)
    rationale: str = Field(min_length=1, max_length=20_000)
    action: dict[str, Any] = Field(default_factory=dict)
    conditions: list[dict[str, Any]] = Field(default_factory=list, max_length=100)
    evidence: list[EvidenceRef] = Field(default_factory=list, max_length=100)
    attribution: dict[str, Any] = Field(default_factory=dict)
    hypothesis_id: UUID | None = None
    status: Literal["draft", "confirmed", "invalidated", "closed", "archived"] = "draft"
    review_date: date | None = None
    created_by: Literal["user", "agent"] = "user"


class ExperimentCreate(BaseModel):
    name: str = Field(min_length=1, max_length=180)
    template_key: Literal["dividend_low_vol", "momentum_trend", "quality_growth"]
    parameters: dict[str, Any] = Field(default_factory=dict)


class ExperimentRun(BaseModel):
    symbols: list[str] = Field(min_length=1, max_length=50)
    lookback_days: int = Field(default=750, ge=60, le=1200)
    top_n: int = Field(default=20, ge=1, le=50)
    cost_bps: float = Field(default=10, ge=0, le=500)
    fundamentals: dict[str, dict[str, float]] = Field(default_factory=dict, deprecated=True,
        description="Deprecated and ignored. The backend joins point-in-time published fundamentals.")


class DocumentCreate(BaseModel):
    title: str = Field(min_length=1, max_length=240)
    document_type: Literal["research_note", "portfolio_report", "decision_review"] = "research_note"


class DocumentGenerate(BaseModel):
    bodies: dict[Literal["zh-CN", "en-US"], str]
    structured: dict[str, Any] = Field(default_factory=dict)
    source_snapshot: dict[str, Any] = Field(default_factory=dict)


class DocumentBilingualGenerate(BaseModel):
    summary: str | None = Field(default=None, max_length=4000)
    structured: dict[str, Any] = Field(default_factory=dict)
    source_snapshot: dict[str, Any] = Field(default_factory=dict)


@router.get("/os/overview")
async def overview(session: AsyncSession = Depends(get_session), user: User = Depends(get_current_user)):
    return await service(session, user).overview()


@router.get("/portfolio/accounts")
async def portfolio_accounts(session: AsyncSession = Depends(get_session), user: User = Depends(get_current_user)):
    return await service(session, user).list_accounts()


@router.post("/portfolio/accounts")
async def create_portfolio_account(body: PortfolioAccountCreate, session: AsyncSession = Depends(get_session),
                                   user: User = Depends(get_current_user)):
    return await service(session, user).create_account(body.model_dump())


@router.patch("/portfolio/accounts/{account_id}")
async def update_portfolio_account(account_id: UUID, body: PortfolioAccountUpdate,
                                   session: AsyncSession = Depends(get_session), user: User = Depends(get_current_user)):
    try:
        return await service(session, user).update_account(account_id, body.model_dump(exclude_unset=True))
    except ValueError as exc:
        raise bad_request(exc) from exc


@router.get("/portfolio/accounts/{account_id}/transactions")
async def transactions(account_id: UUID, session: AsyncSession = Depends(get_session),
                       user: User = Depends(get_current_user)):
    try:
        return await service(session, user).list_transactions(account_id)
    except ValueError as exc:
        raise bad_request(exc) from exc


@router.post("/portfolio/accounts/{account_id}/transactions")
async def create_transaction(account_id: UUID, body: PortfolioTransactionCreate,
                             session: AsyncSession = Depends(get_session), user: User = Depends(get_current_user)):
    try:
        return await service(session, user).add_transaction(account_id, body.model_dump())
    except ValueError as exc:
        raise bad_request(exc) from exc


@router.post("/portfolio/manual-prices")
async def create_manual_price(body: ManualPriceCreate, session: AsyncSession = Depends(get_session),
                              user: User = Depends(get_current_user)):
    try:
        return await service(session, user).set_manual_price(**body.model_dump())
    except ValueError as exc:
        raise bad_request(exc) from exc


@router.post("/portfolio/imports/preview")
async def preview_import(body: ImportPreview, session: AsyncSession = Depends(get_session),
                         user: User = Depends(get_current_user)):
    try:
        return await service(session, user).preview_import(**body.model_dump())
    except ValueError as exc:
        raise bad_request(exc) from exc


@router.post("/portfolio/imports/{batch_id}/commit")
async def commit_import(batch_id: UUID, session: AsyncSession = Depends(get_session),
                        user: User = Depends(get_current_user)):
    try:
        return await service(session, user).commit_import(batch_id)
    except ValueError as exc:
        raise bad_request(exc) from exc


@router.get("/portfolio/accounts/{account_id}/valuation")
async def valuation(account_id: UUID, as_of: date | None = None, session: AsyncSession = Depends(get_session),
                    user: User = Depends(get_current_user)):
    try:
        return await service(session, user).valuation(account_id, as_of or date.today())
    except ValueError as exc:
        raise bad_request(exc) from exc


@router.get("/portfolio/accounts/{account_id}/nav")
async def nav(account_id: UUID, session: AsyncSession = Depends(get_session), user: User = Depends(get_current_user)):
    try:
        return await service(session, user).nav_history(account_id)
    except ValueError as exc:
        raise bad_request(exc) from exc


@router.get("/portfolio/accounts/{account_id}/analytics")
async def portfolio_analytics(account_id: UUID, period: Literal["1M", "3M", "1Y", "3Y"] = "1Y",
                              session: AsyncSession = Depends(get_session), user: User = Depends(get_current_user)):
    try:
        return await service(session, user).portfolio_analytics(account_id, period)
    except ValueError as exc:
        raise bad_request(exc) from exc


@router.get("/portfolio/accounts/{account_id}/holdings/{instrument_id}/detail")
async def holding_detail(account_id: UUID, instrument_id: UUID, session: AsyncSession = Depends(get_session),
                         user: User = Depends(get_current_user)):
    try:
        return await service(session, user).holding_detail(account_id, instrument_id)
    except ValueError as exc:
        raise bad_request(exc) from exc


@router.get("/hypotheses")
async def hypotheses(session: AsyncSession = Depends(get_session), user: User = Depends(get_current_user)):
    return await service(session, user).list_hypotheses()


@router.post("/hypotheses")
async def create_hypothesis(body: HypothesisCreate, session: AsyncSession = Depends(get_session),
                            user: User = Depends(get_current_user)):
    try:
        return await service(session, user).create_hypothesis(body.model_dump())
    except ValueError as exc:
        raise bad_request(exc) from exc


@router.post("/hypotheses/{hypothesis_id}/revisions")
async def revise_hypothesis(hypothesis_id: UUID, body: HypothesisCreate,
                            session: AsyncSession = Depends(get_session), user: User = Depends(get_current_user)):
    try:
        return await service(session, user).revise_hypothesis(hypothesis_id, body.model_dump())
    except ValueError as exc:
        raise bad_request(exc) from exc


@router.post("/hypotheses/{hypothesis_id}/content-brief")
async def submit_hypothesis_content_brief(
    hypothesis_id: UUID,
    body: ContentBriefSubmit,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    try:
        hypothesis = await service(session, user).get_hypothesis(hypothesis_id)
        return await submit_content_brief(
            hypothesis=hypothesis,
            request=body.model_dump(),
            user_id=user.id,
        )
    except ValueError as exc:
        raise bad_request(exc) from exc
    except ContentBriefRejectedError as exc:
        raise HTTPException(409, str(exc)) from exc
    except ContentBriefSinkError as exc:
        raise HTTPException(503, str(exc)) from exc


@router.get("/decisions")
async def decisions(session: AsyncSession = Depends(get_session), user: User = Depends(get_current_user)):
    return await service(session, user).list_decisions()


@router.post("/decisions")
async def create_decision(body: DecisionCreate, session: AsyncSession = Depends(get_session),
                          user: User = Depends(get_current_user)):
    try:
        return await service(session, user).create_decision(body.model_dump())
    except ValueError as exc:
        raise bad_request(exc) from exc


@router.post("/decisions/{decision_id}/revisions")
async def revise_decision(decision_id: UUID, body: DecisionCreate, session: AsyncSession = Depends(get_session),
                          user: User = Depends(get_current_user)):
    try:
        return await service(session, user).revise_decision(decision_id, body.model_dump())
    except ValueError as exc:
        raise bad_request(exc) from exc


@router.get("/strategy-experiments/templates")
async def strategy_templates(session: AsyncSession = Depends(get_session), user: User = Depends(get_current_user)):
    return await service(session, user).strategy_templates()


@router.get("/strategy-experiments")
async def experiments(session: AsyncSession = Depends(get_session), user: User = Depends(get_current_user)):
    return await service(session, user).list_experiments()


@router.post("/strategy-experiments")
async def create_experiment(body: ExperimentCreate, session: AsyncSession = Depends(get_session),
                            user: User = Depends(get_current_user)):
    try:
        return await service(session, user).create_experiment(body.model_dump())
    except ValueError as exc:
        raise bad_request(exc) from exc


@router.post("/strategy-experiments/{experiment_id}/runs")
async def run_experiment(experiment_id: UUID, body: ExperimentRun, session: AsyncSession = Depends(get_session),
                         user: User = Depends(get_current_user)):
    try:
        return await service(session, user).run_experiment(experiment_id, body.model_dump())
    except ValueError as exc:
        raise bad_request(exc) from exc


@router.get("/consensus")
async def consensus(subject_type: str | None = None, subject_code: str | None = None,
                    session: AsyncSession = Depends(get_session), user: User = Depends(get_current_user)):
    return await service(session, user).consensus(subject_type, subject_code)


@router.get("/research/library")
async def research_library(
    query: str | None = Query(default=None, max_length=240),
    institution: str | None = Query(default=None, max_length=160),
    source_family: str | None = Query(default=None, max_length=80),
    date_from: date | None = None,
    date_to: date | None = None,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    user: User = Depends(get_current_user),
):
    del user
    client = ReportKBService()
    if query and query.strip():
        items = await client.search_reports(query.strip(), top_k=min(limit, 20))
        return {"available": True, "items": items, "limit": min(limit, 20), "offset": 0, "search": True}
    return await client.list_reports(limit=limit, offset=offset, institution=institution, source_family=source_family,
                                     date_from=date_from, date_to=date_to)


@router.get("/research/library/status")
async def research_library_status(user: User = Depends(get_current_user)):
    del user
    return await ReportKBService().report_freshness()


@router.get("/research/library/{report_id}")
async def research_library_detail(report_id: UUID, user: User = Depends(get_current_user)):
    del user
    return await ReportKBService().report_detail(str(report_id))


@router.get("/research/library/{report_id}/pdf")
async def research_library_pdf(report_id: UUID, user: User = Depends(get_current_user)):
    del user
    return await ReportKBService().report_pdf_link(str(report_id))


@router.get("/research-documents")
async def documents(session: AsyncSession = Depends(get_session), user: User = Depends(get_current_user)):
    return await service(session, user).list_documents()


@router.post("/research-documents")
async def create_document(body: DocumentCreate, session: AsyncSession = Depends(get_session),
                          user: User = Depends(get_current_user)):
    return await service(session, user).create_document(body.title, body.document_type)


@router.post("/research-documents/{document_id}/generate")
async def generate_document(document_id: UUID, body: DocumentGenerate, session: AsyncSession = Depends(get_session),
                            user: User = Depends(get_current_user)):
    try:
        return await service(session, user).generate_document(document_id, body.model_dump())
    except ValueError as exc:
        raise bad_request(exc) from exc


@router.post("/research-documents/{document_id}/generate-bilingual")
async def generate_bilingual_document(document_id: UUID, body: DocumentBilingualGenerate,
                                      session: AsyncSession = Depends(get_session),
                                      user: User = Depends(get_current_user)):
    try:
        return await service(session, user).generate_bilingual_document(document_id, body.model_dump())
    except ValueError as exc:
        raise bad_request(exc) from exc


@router.get("/research-documents/{document_id}/versions")
async def document_versions(document_id: UUID, session: AsyncSession = Depends(get_session),
                            user: User = Depends(get_current_user)):
    try:
        return await service(session, user).list_document_versions(document_id)
    except ValueError as exc:
        raise bad_request(exc) from exc


@router.get("/research-document-versions/{version_id}/download")
async def download_document(version_id: UUID, session: AsyncSession = Depends(get_session),
                            user: User = Depends(get_current_user)):
    try:
        version, path = await service(session, user).document_version(version_id)
        await service(session, user).record_document_download(version_id)
    except ValueError as exc:
        raise bad_request(exc) from exc
    filename = f"keeltrader-agentos-v{version.version}-{version.locale}.pdf"
    return FileResponse(path=str(path), media_type="application/pdf", filename=filename)
