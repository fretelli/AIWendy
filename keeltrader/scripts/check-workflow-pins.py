#!/usr/bin/env python3
from __future__ import annotations

import pathlib
import re


ROOT = pathlib.Path(__file__).resolve().parents[2]
USES = re.compile(r"^\s*-?\s*uses:\s*([^\s#]+)")
PINNED = re.compile(r"^[^@\s]+@[0-9a-f]{40}$")


def main() -> int:
    failures: list[str] = []
    for path in sorted((ROOT / ".github" / "workflows").glob("*.yml")):
        for lineno, line in enumerate(path.read_text().splitlines(), start=1):
            match = USES.match(line)
            if not match:
                continue
            value = match.group(1)
            if value.startswith("./"):
                continue
            if not PINNED.fullmatch(value):
                failures.append(f"{path.relative_to(ROOT)}:{lineno}: {value}")
    if failures:
        print("[workflow-pins] mutable or invalid Action reference found:")
        print("\n".join(f"  - {item}" for item in failures))
        return 1
    print("[workflow-pins] ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
