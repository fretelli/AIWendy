"""File upload and management endpoints."""

from typing import Optional

from fastapi import APIRouter, Depends, File, Request, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from core.auth import get_authenticated_user, get_current_user
from core.database import get_session
from core.i18n import get_request_locale
from domain.user.models import User
from services.file_service import (
    delete_user_file,
    extract_file_text_payload,
    resolve_download_file,
    transcribe_audio_payload,
    upload_user_file,
)
from services.storage_service import StorageProvider, get_storage_provider

router = APIRouter()


# Response models
class FileUploadResponse(BaseModel):
    """Response for file upload."""

    id: str
    fileName: str
    fileSize: int
    mimeType: str
    type: (
        str  # 'image', 'audio', 'pdf', 'word', 'excel', 'ppt', 'text', 'code', 'binary'
    )
    url: str
    thumbnailBase64: Optional[str] = None


class TextExtractionResponse(BaseModel):
    """Response for text extraction."""

    success: bool
    text: Optional[str] = None
    error: Optional[str] = None
    fileType: Optional[str] = None
    pageCount: Optional[int] = None


class TranscriptionResponse(BaseModel):
    """Response for audio transcription."""

    text: str
    language: Optional[str] = None
    confidence: Optional[float] = None


@router.post("/upload", response_model=FileUploadResponse)
async def upload_file(
    http_request: Request,
    file: UploadFile = File(...),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_authenticated_user),
    storage: StorageProvider = Depends(get_storage_provider),
):
    """
    Upload a file (image, audio, document, etc.).

    Supported file types:
    - Images: JPEG, PNG, GIF, WebP (max 10MB)
    - Audio: WAV, MP3, WebM, OGG (max 25MB)
    - Documents: PDF, DOCX, XLSX, PPTX (max 50MB)
    - Text/Code: TXT, MD, JSON, PY, JS, etc. (max 10MB)
    - Other: Any file (max 100MB)
    """
    locale = get_request_locale(http_request)

    return await upload_user_file(
        file=file,
        current_user=current_user,
        storage=storage,
        session=session,
        locale=locale,
    )


@router.post("/extract", response_model=TextExtractionResponse)
async def extract_file_text(
    http_request: Request,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
):
    """
    Extract text content from a file.

    Supports: PDF, DOCX, XLSX, PPTX, TXT, MD, JSON, CSV, and code files.
    """
    locale = get_request_locale(http_request)

    _ = current_user
    return await extract_file_text_payload(file=file, locale=locale)


@router.post("/transcribe", response_model=TranscriptionResponse)
async def transcribe_audio(
    http_request: Request,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
):
    """
    Transcribe audio to text using OpenAI Whisper API.

    Supports: WAV, MP3, WebM, OGG, M4A (max 25MB)
    """
    locale = get_request_locale(http_request)

    return await transcribe_audio_payload(
        file=file,
        current_user=current_user,
        locale=locale,
    )


@router.get("/download/{path:path}")
async def download_file(
    http_request: Request,
    path: str,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
    storage: StorageProvider = Depends(get_storage_provider),
):
    """
    Download a file by its storage path.
    """
    locale = get_request_locale(http_request)
    file_path, filename = await resolve_download_file(
        storage_path=path,
        current_user=current_user,
        storage=storage,
        session=session,
        locale=locale,
    )

    return FileResponse(
        path=str(file_path),
        filename=filename,
        media_type="application/octet-stream",
    )


@router.delete("/{path:path}")
async def delete_file(
    http_request: Request,
    path: str,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_authenticated_user),
    storage: StorageProvider = Depends(get_storage_provider),
):
    """
    Delete a file by its storage path.
    """
    locale = get_request_locale(http_request)
    return await delete_user_file(
        storage_path=path,
        current_user=current_user,
        storage=storage,
        session=session,
        locale=locale,
    )
