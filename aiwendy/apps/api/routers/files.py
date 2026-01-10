"""File upload and management endpoints."""

import io
import base64
from pathlib import Path
from typing import Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel

from core.auth import get_current_user
from core.logging import get_logger
from domain.user.models import User
from services.storage_service import get_storage_provider, StorageProvider
from services.file_extractor import (
    get_file_category,
    get_file_size_limit,
    can_extract_text,
    extract_text,
)

router = APIRouter()
logger = get_logger(__name__)


# Response models
class FileUploadResponse(BaseModel):
    """Response for file upload."""
    id: str
    fileName: str
    fileSize: int
    mimeType: str
    type: str  # 'image', 'audio', 'pdf', 'word', 'excel', 'ppt', 'text', 'code', 'binary'
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
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
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
    if not file.filename:
        raise HTTPException(status_code=400, detail="Filename is required")

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
            detail=f"File too large. Maximum size for {file_category} files is {max_mb}MB"
        )

    # Validate content type for images (security check)
    content_type = file.content_type or "application/octet-stream"
    if file_category == 'image':
        if not content_type.startswith('image/'):
            raise HTTPException(status_code=400, detail="Invalid image file")

    # Generate thumbnail for images
    thumbnail_base64 = None
    if file_category == 'image':
        try:
            from PIL import Image
            img = Image.open(io.BytesIO(content))
            img.thumbnail((200, 200))

            # Convert to RGB if necessary (for PNG with transparency)
            if img.mode in ('RGBA', 'P'):
                img = img.convert('RGB')

            thumb_io = io.BytesIO()
            img.save(thumb_io, format='JPEG', quality=80)
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
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    storage: StorageProvider = Depends(get_storage_provider),
):
    """
    Extract text content from a file.

    Supports: PDF, DOCX, XLSX, PPTX, TXT, MD, JSON, CSV, and code files.
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="Filename is required")

    # Check if text can be extracted
    if not can_extract_text(file.filename):
        file_category = get_file_category(file.filename)
        return TextExtractionResponse(
            success=False,
            error=f"Cannot extract text from {file_category} files",
            fileType=file_category,
        )

    # Save to temporary file for extraction
    content = await file.read()
    file_obj = io.BytesIO(content)

    # Upload temporarily
    storage_path = await storage.upload(file_obj, file.filename, file.content_type or "")
    file_path = await storage.get_file_path(storage_path)

    if not file_path:
        return TextExtractionResponse(
            success=False,
            error="Failed to process file",
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
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
):
    """
    Transcribe audio to text using OpenAI Whisper API.

    Supports: WAV, MP3, WebM, OGG, M4A (max 25MB)
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="Filename is required")

    # Validate file type
    file_category = get_file_category(file.filename)
    if file_category != 'audio':
        raise HTTPException(
            status_code=400,
            detail="Only audio files are supported for transcription"
        )

    # Check file size
    content = await file.read()
    max_size = 25 * 1024 * 1024  # 25MB
    if len(content) > max_size:
        raise HTTPException(
            status_code=400,
            detail="Audio file too large. Maximum size is 25MB"
        )

    # Use OpenAI Whisper API
    try:
        from openai import AsyncOpenAI
        from config import get_settings

        settings = get_settings()
        if not settings.openai_api_key:
            raise HTTPException(
                status_code=503,
                detail="OpenAI API key not configured. Cannot transcribe audio."
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

        logger.info(f"Audio transcribed for user {current_user.id}: {len(response.text)} chars")

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
            detail=f"Transcription failed: {str(e)}"
        )


@router.get("/download/{path:path}")
async def download_file(
    path: str,
    current_user: User = Depends(get_current_user),
    storage: StorageProvider = Depends(get_storage_provider),
):
    """
    Download a file by its storage path.
    """
    file_path = await storage.get_file_path(path)

    if not file_path or not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")

    # Get filename from path
    filename = file_path.name
    # Remove UUID prefix if present
    if '-' in filename:
        parts = filename.split('-', 1)
        if len(parts) > 1:
            filename = parts[1]

    return FileResponse(
        path=str(file_path),
        filename=filename,
        media_type="application/octet-stream",
    )


@router.delete("/{path:path}")
async def delete_file(
    path: str,
    current_user: User = Depends(get_current_user),
    storage: StorageProvider = Depends(get_storage_provider),
):
    """
    Delete a file by its storage path.
    """
    success = await storage.delete(path)

    if not success:
        raise HTTPException(status_code=404, detail="File not found or already deleted")

    logger.info(f"File deleted by user {current_user.id}: {path}")

    return {"success": True, "message": "File deleted"}
