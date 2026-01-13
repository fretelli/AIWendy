"""Project management endpoints."""

from datetime import datetime
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from core.auth import get_current_user
from core.database import get_session
from core.i18n import Locale, get_request_locale, t
from domain.project.models import Project
from domain.user.models import User

router = APIRouter()


class ProjectCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=2000)


class ProjectUpdateRequest(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=2000)
    is_archived: Optional[bool] = None
    is_default: Optional[bool] = None


class ProjectResponse(BaseModel):
    id: UUID
    user_id: UUID
    name: str
    description: Optional[str]
    is_default: bool
    is_archived: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True


@router.get("", response_model=List[ProjectResponse])
@router.get("/", response_model=List[ProjectResponse])
async def list_projects(
    http_request: Request,
    include_archived: bool = Query(False),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    locale: Locale = get_request_locale(http_request)
    query = select(Project).where(Project.user_id == current_user.id)
    if not include_archived:
        query = query.where(Project.is_archived == False)  # noqa: E712
    query = query.order_by(Project.is_default.desc(), Project.updated_at.desc())
    result = await session.execute(query)
    projects = result.scalars().all()

    # Backfill for legacy users: ensure at least one default project exists.
    if not projects:
        default_project = Project(
            user_id=current_user.id,
            name=t("projects.default.name", locale),
            description=t("projects.default.description", locale),
            is_default=True,
        )
        session.add(default_project)
        await session.commit()
        await session.refresh(default_project)
        projects = [default_project]

    return projects


@router.post("", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
@router.post("/", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
async def create_project(
    request: ProjectCreateRequest,
    http_request: Request,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    locale: Locale = get_request_locale(http_request)
    name = request.name.strip()
    if not name:
        raise HTTPException(
            status_code=400, detail=t("errors.project_name_required", locale)
        )

    existing = await session.execute(
        select(Project).where(
            Project.user_id == current_user.id,
            func.lower(Project.name) == func.lower(name),
            Project.is_archived == False,  # noqa: E712
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=409, detail=t("errors.project_name_exists", locale)
        )

    # First project defaults to active/default
    count_result = await session.execute(
        select(func.count())
        .select_from(Project)
        .where(Project.user_id == current_user.id)
    )
    has_any = (count_result.scalar() or 0) > 0

    project = Project(
        user_id=current_user.id,
        name=name,
        description=request.description.strip() if request.description else None,
        is_default=not has_any,
    )
    session.add(project)

    if project.is_default:
        # Ensure uniqueness of default per user
        await session.execute(
            Project.__table__.update()
            .where(Project.user_id == current_user.id)
            .values(is_default=False)
        )
        project.is_default = True

    await session.commit()
    await session.refresh(project)
    return project


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: UUID,
    http_request: Request,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    locale: Locale = get_request_locale(http_request)
    result = await session.execute(
        select(Project).where(
            Project.id == project_id, Project.user_id == current_user.id
        )
    )
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(
            status_code=404, detail=t("errors.project_not_found", locale)
        )
    return project


@router.patch("/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: UUID,
    request: ProjectUpdateRequest,
    http_request: Request,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    locale: Locale = get_request_locale(http_request)
    result = await session.execute(
        select(Project).where(
            Project.id == project_id, Project.user_id == current_user.id
        )
    )
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(
            status_code=404, detail=t("errors.project_not_found", locale)
        )

    if request.name is not None:
        name = request.name.strip()
        if not name:
            raise HTTPException(
                status_code=400, detail=t("errors.project_name_cannot_be_empty", locale)
            )
        # Check conflicts
        existing = await session.execute(
            select(Project).where(
                Project.user_id == current_user.id,
                func.lower(Project.name) == func.lower(name),
                Project.id != project_id,
                Project.is_archived == False,  # noqa: E712
            )
        )
        if existing.scalar_one_or_none():
            raise HTTPException(
                status_code=409, detail=t("errors.project_name_exists", locale)
            )
        project.name = name

    if request.description is not None:
        project.description = (
            request.description.strip() if request.description else None
        )

    if request.is_archived is not None:
        project.is_archived = request.is_archived
        if project.is_archived and project.is_default:
            project.is_default = False

    if request.is_default is not None:
        if request.is_default:
            await session.execute(
                Project.__table__.update()
                .where(Project.user_id == current_user.id)
                .values(is_default=False)
            )
            project.is_default = True
            project.is_archived = False
        else:
            project.is_default = False

    project.updated_at = datetime.utcnow()
    await session.commit()
    await session.refresh(project)
    return project


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(
    project_id: UUID,
    http_request: Request,
    hard_delete: bool = Query(False, description="Permanently delete the project"),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    locale: Locale = get_request_locale(http_request)
    result = await session.execute(
        select(Project).where(
            Project.id == project_id, Project.user_id == current_user.id
        )
    )
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(
            status_code=404, detail=t("errors.project_not_found", locale)
        )

    if hard_delete:
        await session.delete(project)
    else:
        project.is_archived = True
        if project.is_default:
            project.is_default = False
        project.updated_at = datetime.utcnow()

    await session.commit()
    return None
