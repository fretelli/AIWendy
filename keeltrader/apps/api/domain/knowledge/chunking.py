"""Knowledge base text chunking utilities."""

from __future__ import annotations

from typing import List


def chunk_text(text: str, max_chars: int = 900, overlap: int = 120) -> List[str]:
    cleaned = (text or "").strip()
    if not cleaned:
        return []

    chunks: List[str] = []
    start = 0
    length = len(cleaned)

    while start < length:
        end = min(length, start + max_chars)
        window = cleaned[start:end]

        split_points = [
            window.rfind("\n\n"),
            window.rfind("\n"),
            window.rfind("。"),
            window.rfind("."),
            window.rfind("!"),
            window.rfind("?"),
        ]
        split_at = max(split_points)
        if split_at >= int(max_chars * 0.6):
            end = start + split_at + 1
            window = cleaned[start:end]

        chunk = window.strip()
        if chunk:
            chunks.append(chunk)

        next_start = end - overlap
        if next_start <= start:
            next_start = end
        start = next_start

    return chunks
