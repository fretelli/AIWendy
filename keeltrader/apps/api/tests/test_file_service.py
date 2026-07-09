"""File service security and cleanup regressions."""

from io import BytesIO
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import HTTPException, UploadFile

from services.file_service import (
    delete_user_file,
    extract_file_text_payload,
    resolve_download_file,
    transcribe_audio_payload,
    upload_user_file,
)


def make_upload(filename: str, content: bytes, content_type: str = "text/plain"):
    return UploadFile(
        filename=filename,
        file=BytesIO(content),
        headers={"content-type": content_type},
    )


@pytest.mark.asyncio
async def test_upload_user_file_persists_metadata_and_response_shape():
    user = SimpleNamespace(id=uuid4(), is_admin=False)
    session = _FakeSession()
    storage = _FakeStorage()

    response = await upload_user_file(
        file=make_upload("memo.txt", b"alpha thesis"),
        current_user=user,
        storage=storage,
        session=session,
        locale="en",
    )

    uploaded = session.added[0]
    assert response == {
        "id": str(uploaded.id),
        "fileName": "memo.txt",
        "fileSize": 12,
        "mimeType": "text/plain",
        "type": "text",
        "url": "/api/v1/files/download/2026/01/fake-memo.txt",
        "thumbnailBase64": None,
    }
    assert uploaded.user_id == user.id
    assert uploaded.storage_path == "2026/01/fake-memo.txt"
    assert uploaded.deleted_at is None
    assert storage.uploaded == [("memo.txt", "text/plain", b"alpha thesis")]


@pytest.mark.asyncio
async def test_resolve_download_rejects_unowned_path(monkeypatch):
    async def deny_access(**kwargs):
        return False

    monkeypatch.setattr("services.file_service.user_can_access_storage_path", deny_access)

    with pytest.raises(HTTPException) as exc:
        await resolve_download_file(
            storage_path="2026/01/private.txt",
            current_user=SimpleNamespace(id=uuid4(), is_admin=False),
            storage=_FakeStorage(),
            session=_FakeSession(),
            locale="en",
        )

    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_delete_user_file_deletes_storage_and_marks_metadata(monkeypatch):
    calls = []

    async def allow_access(**kwargs):
        return True

    async def mark_deleted(**kwargs):
        calls.append(kwargs["storage_path"])

    monkeypatch.setattr("services.file_service.user_can_access_storage_path", allow_access)
    monkeypatch.setattr("services.file_service.mark_uploaded_file_deleted", mark_deleted)

    storage = _FakeStorage()
    response = await delete_user_file(
        storage_path="2026/01/fake-memo.txt",
        current_user=SimpleNamespace(id=uuid4(), is_admin=False),
        storage=storage,
        session=_FakeSession(),
        locale="en",
    )

    assert response == {"success": True, "message": "File deleted"}
    assert storage.deleted == ["2026/01/fake-memo.txt"]
    assert calls == ["2026/01/fake-memo.txt"]


@pytest.mark.asyncio
async def test_extract_file_text_uses_temp_file_and_cleans_it(monkeypatch):
    temp_paths = []

    async def fake_extract_text(file_path, filename):
        temp_paths.append(Path(file_path))
        assert Path(file_path).exists()
        assert filename == "memo.txt"
        return SimpleNamespace(
            success=True,
            text="alpha thesis",
            error=None,
            file_type="text",
            page_count=None,
        )

    monkeypatch.setattr("services.file_service.extract_text", fake_extract_text)

    response = await extract_file_text_payload(
        file=make_upload("memo.txt", b"alpha thesis"),
        locale="en",
    )

    assert response["success"] is True
    assert response["text"] == "alpha thesis"
    assert temp_paths and not temp_paths[0].exists()


@pytest.mark.asyncio
async def test_transcribe_audio_without_openai_key_returns_503(monkeypatch):
    monkeypatch.setattr(
        "services.file_service.get_settings",
        lambda: SimpleNamespace(openai_api_key=None),
    )

    with pytest.raises(HTTPException) as exc:
        await transcribe_audio_payload(
            file=make_upload("clip.mp3", b"audio", "audio/mpeg"),
            current_user=SimpleNamespace(id=uuid4(), is_admin=False),
            locale="en",
        )

    assert exc.value.status_code == 503


class _FakeSession:
    def __init__(self):
        self.added = []

    def add(self, item):
        self.added.append(item)

    async def flush(self):
        for item in self.added:
            if getattr(item, "id", None) is None:
                item.id = uuid4()


class _FakeStorage:
    def __init__(self):
        self.uploaded = []
        self.deleted = []

    async def upload(self, file, filename, content_type):
        content = file.read()
        self.uploaded.append((filename, content_type, content))
        return f"2026/01/fake-{filename}"

    async def get_url(self, path):
        return f"/api/v1/files/download/{path}"

    async def get_file_path(self, path):
        return None

    async def delete(self, path):
        self.deleted.append(path)
        return True

