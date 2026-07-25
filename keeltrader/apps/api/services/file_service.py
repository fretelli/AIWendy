"""Business logic for file upload, extraction, transcription, and access control."""

from __future__ import annotations

import base64
import io
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any

from fastapi import HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from config import get_settings
from core.i18n import t
from core.logging import get_logger
from domain.file.models import UploadedFile
from domain.user.models import User
from services.file_extractor import (
    can_extract_text,
    extract_text,
    get_file_category,
    get_file_size_limit,
)
from services.storage_service import StorageProvider

logger = get_logger(__name__)

ALLOWED_EXTENSIONS = {
    "image": {".jpg", ".jpeg", ".png", ".gif", ".webp"},
    "document": {".pdf", ".doc", ".docx", ".txt", ".md"},
    "audio": {".mp3", ".wav", ".ogg", ".m4a"},
}
MAX_IMAGE_PIXELS = 50_000_000
AUDIO_MAX_BYTES = 25 * 1024 * 1024


def _require_filename(file: UploadFile, locale: str) -> str:
    if not file.filename:
        raise HTTPException(status_code=400, detail=t("errors.filename_required", locale))
    return file.filename


def _validate_extension(filename: str, file_category: str, locale: str) -> None:
    allowed = ALLOWED_EXTENSIONS.get(file_category)
    if not allowed:
        return
    file_ext = Path(filename).suffix.lower()
    if file_ext not in allowed:
        raise HTTPException(
            status_code=400,
            detail=t(
                "errors.invalid_file_extension",
                locale,
                allowed=", ".join(sorted(allowed)),
            ),
        )


def _verify_image_content(content: bytes, locale: str) -> None:
    try:
        from PIL import Image

        img = Image.open(io.BytesIO(content))
        img.verify()
        img = Image.open(io.BytesIO(content))
        if img.width * img.height > MAX_IMAGE_PIXELS:
            raise HTTPException(status_code=400, detail=t("errors.image_too_large", locale))
    except HTTPException:
        raise
    except Exception as exc:
        logger.warning(f"Image validation failed: {exc}")
        raise HTTPException(status_code=400, detail=t("errors.invalid_image_file", locale))


def _thumbnail_base64(content: bytes) -> str | None:
    try:
        from PIL import Image

        img = Image.open(io.BytesIO(content))
        img.thumbnail((200, 200))
        if img.mode in ("RGBA", "P"):
            img = img.convert("RGB")

        thumb_io = io.BytesIO()
        img.save(thumb_io, format="JPEG", quality=80)
        return base64.b64encode(thumb_io.getvalue()).decode()
    except Exception as exc:
        logger.warning(f"Failed to generate thumbnail: {exc}")
        return None


def _download_filename(file_path: Path) -> str:
    filename = file_path.name
    if "-" in filename:
        prefix, suffix = filename.split("-", 1)
        if prefix and suffix:
            return suffix
    return filename


async def upload_user_file(
    *,
    file: UploadFile,
    current_user: User,
    storage: StorageProvider,
    session: AsyncSession,
    locale: str,
) -> dict[str, Any]:
    filename = _require_filename(file, locale)
    file_category = get_file_category(filename)
    max_size = get_file_size_limit(filename)
    content = await file.read()
    file_size = len(content)

    if file_size > max_size:
        raise HTTPException(
            status_code=400,
            detail=t(
                "errors.file_too_large",
                locale,
                file_category=file_category,
                max_mb=max_size // (1024 * 1024),
            ),
        )

    _validate_extension(filename, file_category, locale)

    content_type = file.content_type or "application/octet-stream"
    if file_category == "image":
        if not content_type.startswith("image/"):
            raise HTTPException(status_code=400, detail=t("errors.invalid_image_file", locale))
        _verify_image_content(content, locale)

    thumbnail = _thumbnail_base64(content) if file_category == "image" else None
    storage_path = await storage.upload(io.BytesIO(content), filename, content_type)
    download_url = await storage.get_url(storage_path)

    uploaded = UploadedFile(
        user_id=current_user.id,
        file_name=filename,
        file_size=file_size,
        mime_type=content_type,
        file_category=file_category,
        storage_path=storage_path,
        thumbnail_base64=thumbnail,
    )
    session.add(uploaded)
    await session.flush()

    logger.info(
        f"File uploaded by user {current_user.id}: {filename} "
        f"({file_category}, {file_size} bytes)"
    )

    return {
        "id": str(uploaded.id),
        "fileName": filename,
        "fileSize": file_size,
        "mimeType": content_type,
        "type": file_category,
        "url": download_url,
        "thumbnailBase64": thumbnail,
    }


async def extract_file_text_payload(*, file: UploadFile, locale: str) -> dict[str, Any]:
    filename = _require_filename(file, locale)
    if not can_extract_text(filename):
        file_category = get_file_category(filename)
        return {
            "success": False,
            "error": t(
                "errors.cannot_extract_text_from_category",
                locale,
                file_category=file_category,
            ),
            "fileType": file_category,
        }

    content = await file.read()
    suffix = Path(filename).suffix
    temp_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(content)
            temp_path = Path(tmp.name)

        result = await extract_text(temp_path, filename)
        return {
            "success": result.success,
            "text": result.text,
            "error": result.error,
            "fileType": result.file_type,
            "pageCount": result.page_count,
        }
    finally:
        if temp_path is not None:
            try:
                temp_path.unlink(missing_ok=True)
            except Exception as exc:
                logger.warning(f"Failed to clean text extraction temp file: {exc}")


async def transcribe_audio_payload(
    *,
    file: UploadFile,
    current_user: User,
    locale: str,
) -> dict[str, Any]:
    filename = _require_filename(file, locale)
    if get_file_category(filename) != "audio":
        raise HTTPException(
            status_code=400,
            detail=t("errors.only_audio_supported_for_transcription", locale),
        )

    content = await file.read()
    if len(content) > AUDIO_MAX_BYTES:
        raise HTTPException(
            status_code=400,
            detail=t("errors.audio_file_too_large", locale, max_mb=25),
        )

    try:
        from openai import AsyncOpenAI

        settings = get_settings()
        if not settings.openai_api_key:
            raise HTTPException(
                status_code=503,
                detail=t("errors.openai_api_key_not_configured", locale),
            )

        audio_file = io.BytesIO(content)
        audio_file.name = filename
        response = await AsyncOpenAI(api_key=settings.openai_api_key).audio.transcriptions.create(
            model="whisper-1",
            file=audio_file,
        )

        logger.info(
            f"Audio transcribed for user {current_user.id}: {len(response.text)} chars"
        )
        return {"text": response.text, "language": None, "confidence": None}
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"Transcription failed: {exc}")
        raise HTTPException(status_code=500, detail=t("errors.transcription_failed", locale))


async def user_can_access_storage_path(
    *,
    storage_path: str,
    current_user: User,
    session: AsyncSession,
) -> bool:
    uploaded = await _find_uploaded_file(storage_path, session, user_id=current_user.id)
    return uploaded is not None


async def mark_uploaded_file_deleted(
    *,
    storage_path: str,
    current_user: User,
    session: AsyncSession,
) -> None:
    stmt = select(UploadedFile).where(
        UploadedFile.storage_path == storage_path,
        UploadedFile.deleted_at.is_(None),
    )
    stmt = stmt.where(UploadedFile.user_id == current_user.id)
    result = await session.execute(stmt)
    uploaded = result.scalar_one_or_none()
    if uploaded is not None:
        uploaded.deleted_at = datetime.utcnow()
        await session.flush()


async def resolve_download_file(
    *,
    storage_path: str,
    current_user: User,
    storage: StorageProvider,
    session: AsyncSession,
    locale: str,
) -> tuple[Path, str]:
    if not await user_can_access_storage_path(
        storage_path=storage_path,
        current_user=current_user,
        session=session,
    ):
        raise HTTPException(status_code=404, detail=t("errors.file_not_found", locale))

    file_path = await storage.get_file_path(storage_path)
    if not file_path or not file_path.exists():
        raise HTTPException(status_code=404, detail=t("errors.file_not_found", locale))
    return file_path, _download_filename(file_path)


async def delete_user_file(
    *,
    storage_path: str,
    current_user: User,
    storage: StorageProvider,
    session: AsyncSession,
    locale: str,
) -> dict[str, Any]:
    if not await user_can_access_storage_path(
        storage_path=storage_path,
        current_user=current_user,
        session=session,
    ):
        raise HTTPException(
            status_code=404,
            detail=t("errors.file_not_found_or_deleted", locale),
        )

    if not await storage.delete(storage_path):
        raise HTTPException(
            status_code=404,
            detail=t("errors.file_not_found_or_deleted", locale),
        )
    await mark_uploaded_file_deleted(
        storage_path=storage_path,
        current_user=current_user,
        session=session,
    )
    logger.info(f"File deleted by user {current_user.id}: {storage_path}")
    return {"success": True, "message": t("messages.file_deleted", locale)}


async def _find_uploaded_file(
    storage_path: str,
    session: AsyncSession,
    *,
    user_id: Any | None = None,
) -> UploadedFile | None:
    stmt = select(UploadedFile).where(
        UploadedFile.storage_path == storage_path,
        UploadedFile.deleted_at.is_(None),
    )
    if user_id is not None:
        stmt = stmt.where(UploadedFile.user_id == user_id)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()
