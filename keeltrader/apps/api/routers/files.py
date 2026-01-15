"""File upload and management endpoints."""

import base64
import io
from pathlib import Path
from typing import Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel

from core.auth import get_authenticated_user, get_current_user
from core.i18n import get_request_locale, t
from core.logging import get_logger
from domain.user.models import User
from services.file_extractor import (
    can_extract_text,
    extract_text,
    get_file_category,
    get_file_size_limit,
)
from services.storage_service import StorageProvider, get_storage_provider

router = APIRouter()
logger = get_logger(__name__)


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

    if not file.filename:
        raise HTTPException(
            status_code=400, detail=t("errors.filename_required", locale)
        )

    # Get file category and size limit
    file_category = get_file_category(file.filename)
    max_size = get_file_size_limit(file.filename)

    # Read file content
    content = await file.read()
    file_size = len(content)

    # Validate file size
    if file_size > max_size:
        max_mb = max_size // (1024 * 1024)
        raise HTTPException(
            status_code=400,
            detail=t(
                "errors.file_too_large",
                locale,
                file_category=file_category,
                max_mb=max_mb,
            ),
        )

    # Validate content type for images (security check)
    content_type = file.content_type or "application/octet-stream"

    # Validate file extension
    allowed_extensions = {
        "image": {".jpg", ".jpeg", ".png", ".gif", ".webp"},
        "document": {".pdf", ".doc", ".docx", ".txt", ".md"},
        "audio": {".mp3", ".wav", ".ogg", ".m4a"},
    }

    file_ext = Path(file.filename).suffix.lower()
    if file_category in allowed_extensions:
        if file_ext not in allowed_extensions[file_category]:
            raise HTTPException(
                status_code=400,
                detail=t(
                    "errors.invalid_file_extension",
                    locale,
                    allowed=", ".join(allowed_extensions[file_category]),
                ),
            )

    # Validate content type matches category
    if file_category == "image":
        if not content_type.startswith("image/"):
            raise HTTPException(
                status_code=400, detail=t("errors.invalid_image_file", locale)
            )

        # Verify actual file content (magic bytes check)
        try:
            from PIL import Image

            img = Image.open(io.BytesIO(content))
            img.verify()  # Verify it's a valid image
            # Re-open after verify (verify closes the file)
            img = Image.open(io.BytesIO(content))

            # Check image dimensions (prevent decompression bombs)
            max_pixels = 50_000_000  # 50 megapixels
            if img.width * img.height > max_pixels:
                raise HTTPException(
                    status_code=400,
                    detail=t("errors.image_too_large", locale),
                )
        except Exception as e:
            logger.warning(f"Image validation failed: {e}")
            raise HTTPException(
                status_code=400,
                detail=t("errors.invalid_image_file", locale),
            )

    # Generate thumbnail for images
    thumbnail_base64 = None
    if file_category == "image":
        try:
            from PIL import Image

            img = Image.open(io.BytesIO(content))
            img.thumbnail((200, 200))

            # Convert to RGB if necessary (for PNG with transparency)
            if img.mode in ("RGBA", "P"):
                img = img.convert("RGB")

            thumb_io = io.BytesIO()
            img.save(thumb_io, format="JPEG", quality=80)
            thumbnail_base64 = base64.b64encode(thumb_io.getvalue()).decode()
        except Exception as e:
            logger.warning(f"Failed to generate thumbnail: {e}")

    # Upload to storage
    file_obj = io.BytesIO(content)
    storage_path = await storage.upload(file_obj, file.filename, content_type)
    download_url = await storage.get_url(storage_path)

    # Generate unique ID
    file_id = str(uuid4())

    logger.info(
        f"File uploaded by user {current_user.id}: {file.filename} "
        f"({file_category}, {file_size} bytes)"
    )

    return FileUploadResponse(
        id=file_id,
        fileName=file.filename,
        fileSize=file_size,
        mimeType=content_type,
        type=file_category,
        url=download_url,
        thumbnailBase64=thumbnail_base64,
    )


@router.post("/extract", response_model=TextExtractionResponse)
async def extract_file_text(
    http_request: Request,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    storage: StorageProvider = Depends(get_storage_provider),
):
    """
    Extract text content from a file.

    Supports: PDF, DOCX, XLSX, PPTX, TXT, MD, JSON, CSV, and code files.
    """
    locale = get_request_locale(http_request)

    if not file.filename:
        raise HTTPException(
            status_code=400, detail=t("errors.filename_required", locale)
        )

    # Check if text can be extracted
    if not can_extract_text(file.filename):
        file_category = get_file_category(file.filename)
        return TextExtractionResponse(
            success=False,
            error=t(
                "errors.cannot_extract_text_from_category",
                locale,
                file_category=file_category,
            ),
            fileType=file_category,
        )

    # Save to temporary file for extraction
    content = await file.read()
    file_obj = io.BytesIO(content)

    # Upload temporarily
    storage_path = await storage.upload(
        file_obj, file.filename, file.content_type or ""
    )
    file_path = await storage.get_file_path(storage_path)

    if not file_path:
        return TextExtractionResponse(
            success=False,
            error=t("errors.failed_to_process_file", locale),
        )

    # Extract text
    result = await extract_text(file_path, file.filename)

    # Clean up temp file (optional - you may want to keep it)
    # await storage.delete(storage_path)

    return TextExtractionResponse(
        success=result.success,
        text=result.text,
        error=result.error,
        fileType=result.file_type,
        pageCount=result.page_count,
    )


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

    if not file.filename:
        raise HTTPException(
            status_code=400, detail=t("errors.filename_required", locale)
        )

    # Validate file type
    file_category = get_file_category(file.filename)
    if file_category != "audio":
        raise HTTPException(
            status_code=400,
            detail=t("errors.only_audio_supported_for_transcription", locale),
        )

    # Check file size
    content = await file.read()
    max_size = 25 * 1024 * 1024  # 25MB
    if len(content) > max_size:
        raise HTTPException(
            status_code=400,
            detail=t("errors.audio_file_too_large", locale, max_mb=25),
        )

    # Use OpenAI Whisper API
    try:
        from openai import AsyncOpenAI

        from config import get_settings

        settings = get_settings()
        if not settings.openai_api_key:
            raise HTTPException(
                status_code=503,
                detail=t("errors.openai_api_key_not_configured", locale),
            )

        client = AsyncOpenAI(api_key=settings.openai_api_key)

        # Create a file-like object
        audio_file = io.BytesIO(content)
        audio_file.name = file.filename  # OpenAI needs the filename

        # Transcribe
        response = await client.audio.transcriptions.create(
            model="whisper-1",
            file=audio_file,
        )

        logger.info(
            f"Audio transcribed for user {current_user.id}: {len(response.text)} chars"
        )

        return TranscriptionResponse(
            text=response.text,
            language=None,  # Whisper auto-detects
            confidence=None,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Transcription failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=t("errors.transcription_failed", locale),
        )


@router.get("/download/{path:path}")
async def download_file(
    http_request: Request,
    path: str,
    current_user: User = Depends(get_current_user),
    storage: StorageProvider = Depends(get_storage_provider),
):
    """
    Download a file by its storage path.
    """
    locale = get_request_locale(http_request)
    file_path = await storage.get_file_path(path)

    if not file_path or not file_path.exists():
        raise HTTPException(status_code=404, detail=t("errors.file_not_found", locale))

    # Get filename from path
    filename = file_path.name
    # Remove UUID prefix if present
    if "-" in filename:
        parts = filename.split("-", 1)
        if len(parts) > 1:
            filename = parts[1]

    return FileResponse(
        path=str(file_path),
        filename=filename,
        media_type="application/octet-stream",
    )


@router.delete("/{path:path}")
async def delete_file(
    http_request: Request,
    path: str,
    current_user: User = Depends(get_authenticated_user),
    storage: StorageProvider = Depends(get_storage_provider),
):
    """
    Delete a file by its storage path.
    """
    locale = get_request_locale(http_request)
    success = await storage.delete(path)

    if not success:
        raise HTTPException(
            status_code=404, detail=t("errors.file_not_found_or_deleted", locale)
        )

    logger.info(f"File deleted by user {current_user.id}: {path}")

    return {"success": True, "message": t("messages.file_deleted", locale)}
