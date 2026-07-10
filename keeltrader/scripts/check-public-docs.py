#!/usr/bin/env python3
"""Enforce the exact public Markdown inventory for the repository."""

from __future__ import annotations

import argparse
import re
import subprocess
from pathlib import Path, PurePosixPath


PRIVATE_PARTS = {
    "internal",
    "notes",
    "private",
    "runbook",
    "runbooks",
    "temp",
    "tmp",
}
PRIVATE_NAME_PATTERN = re.compile(
    r"(^|[-_.])(credential|credentials|incident|meeting[-_]?notes?|"
    r"secret|secrets|todo[-_]?report)([-_.]|$)",
    re.IGNORECASE,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=None,
        help="Repository root. Defaults to git rev-parse --show-toplevel.",
    )
    return parser.parse_args()


def resolve_repo_root(value: Path | None) -> Path:
    if value is not None:
        return value.resolve()
    return Path(
        subprocess.check_output(
            ["git", "rev-parse", "--show-toplevel"], text=True
        ).strip()
    )


def tracked_markdown(repo_root: Path) -> set[str]:
    output = subprocess.check_output(
        ["git", "ls-files", "*.md"], cwd=repo_root, text=True
    )
    return set(output.splitlines())


def load_allowlist(repo_root: Path) -> tuple[list[str], set[str]]:
    path = repo_root / ".github/public-docs-allowlist.txt"
    if not path.is_file():
        raise ValueError(f"missing allowlist: {path.relative_to(repo_root)}")

    entries = [
        line.strip()
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]
    if entries != sorted(entries):
        raise ValueError("public documentation allowlist must be sorted")
    if len(entries) != len(set(entries)):
        raise ValueError("public documentation allowlist contains duplicates")
    return entries, set(entries)


def private_path_reason(name: str) -> str | None:
    path = PurePosixPath(name)
    if path.is_absolute() or ".." in path.parts:
        return "path must be repository-relative"
    if any(part.lower() in PRIVATE_PARTS for part in path.parts[:-1]):
        return "private operations directory is not allowed"
    if PRIVATE_NAME_PATTERN.search(path.stem):
        return "private documentation filename is not allowed"
    return None


def main() -> int:
    repo_root = resolve_repo_root(parse_args().repo_root)
    failures: list[str] = []

    try:
        _, allowed = load_allowlist(repo_root)
    except ValueError as exc:
        print(f"[public-docs] {exc}")
        return 1

    tracked = tracked_markdown(repo_root)
    for name in sorted(tracked - allowed):
        failures.append(f"tracked Markdown is not allowlisted: {name}")
    for name in sorted(allowed - tracked):
        failures.append(f"allowlisted Markdown is not tracked: {name}")
    for name in sorted(tracked):
        reason = private_path_reason(name)
        if reason:
            failures.append(f"{reason}: {name}")

    if failures:
        for failure in failures:
            print(f"[public-docs] {failure}")
        return 1

    print(f"[public-docs] ok ({len(tracked)} tracked Markdown files)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
