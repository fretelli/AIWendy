#!/usr/bin/env python3
"""Validate relative Markdown links in tracked documentation."""

from __future__ import annotations

import re
import subprocess
from pathlib import Path


REPO_ROOT = Path(
    subprocess.check_output(
        ["git", "rev-parse", "--show-toplevel"], text=True
    ).strip()
)
LINK_PATTERN = re.compile(r"\[[^\]]+\]\(([^)]+)\)")


def tracked_markdown_files() -> list[str]:
    output = subprocess.check_output(
        ["git", "ls-files", "*.md"], cwd=REPO_ROOT, text=True
    )
    return output.splitlines()


def main() -> int:
    missing: list[str] = []

    for name in tracked_markdown_files():
        path = REPO_ROOT / name
        if not path.exists() or path.is_symlink():
            continue

        for target in LINK_PATTERN.findall(path.read_text(encoding="utf-8")):
            target = target.split("#", 1)[0]
            if not target or "://" in target or target.startswith("mailto:"):
                continue
            if not (path.parent / target).resolve().exists():
                missing.append(f"{name} -> {target}")

    if missing:
        for item in missing:
            print(f"[doc-links] missing: {item}")
        return 1

    print("[doc-links] ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
