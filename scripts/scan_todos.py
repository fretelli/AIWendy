#!/usr/bin/env python3
"""Scan codebase for TODO, FIXME, HACK, and XXX comments.

Usage:
    python scripts/scan_todos.py                    # Scan all files
    python scripts/scan_todos.py --format markdown  # Output as markdown
    python scripts/scan_todos.py --category security # Filter by category
"""

import argparse
import re
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Tuple


class TodoItem:
    """Represents a TODO comment in the codebase."""

    def __init__(
        self,
        file_path: str,
        line_number: int,
        todo_type: str,
        category: str,
        description: str,
        context: List[str],
    ):
        self.file_path = file_path
        self.line_number = line_number
        self.todo_type = todo_type  # TODO, FIXME, HACK, XXX
        self.category = category  # security, feature, performance, etc.
        self.description = description
        self.context = context  # Surrounding lines for context

    def __repr__(self):
        return f"{self.file_path}:{self.line_number} [{self.todo_type}({self.category})] {self.description}"


def scan_file(file_path: Path) -> List[TodoItem]:
    """Scan a single file for TODO comments."""
    todos = []

    # Pattern to match TODO comments with optional category
    # Examples: TODO(security): ..., FIXME: ..., TODO: ...
    pattern = re.compile(
        r'#\s*(TODO|FIXME|HACK|XXX)(?:\(([^)]+)\))?:\s*(.+)',
        re.IGNORECASE
    )

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        for i, line in enumerate(lines, start=1):
            match = pattern.search(line)
            if match:
                todo_type = match.group(1).upper()
                category = match.group(2) or "general"
                description = match.group(3).strip()

                # Collect context (current line + next few lines if they're continuations)
                context = [line.strip()]
                j = i
                while j < len(lines) and lines[j].strip().startswith('#'):
                    if not pattern.search(lines[j]):  # Not a new TODO
                        context.append(lines[j].strip())
                    j += 1

                todos.append(TodoItem(
                    file_path=str(file_path.relative_to(Path.cwd())),
                    line_number=i,
                    todo_type=todo_type,
                    category=category,
                    description=description,
                    context=context
                ))
    except Exception as e:
        print(f"Error scanning {file_path}: {e}")

    return todos


def scan_directory(root_dir: Path, exclude_dirs: List[str]) -> List[TodoItem]:
    """Recursively scan directory for TODO comments."""
    all_todos = []

    for file_path in root_dir.rglob("*.py"):
        # Skip excluded directories
        if any(excluded in file_path.parts for excluded in exclude_dirs):
            continue

        todos = scan_file(file_path)
        all_todos.extend(todos)

    return all_todos


def group_by_category(todos: List[TodoItem]) -> Dict[str, List[TodoItem]]:
    """Group TODOs by category."""
    grouped = defaultdict(list)
    for todo in todos:
        grouped[todo.category].append(todo)
    return dict(grouped)


def group_by_type(todos: List[TodoItem]) -> Dict[str, List[TodoItem]]:
    """Group TODOs by type (TODO, FIXME, etc.)."""
    grouped = defaultdict(list)
    for todo in todos:
        grouped[todo.todo_type].append(todo)
    return dict(grouped)


def format_text(todos: List[TodoItem]) -> str:
    """Format TODOs as plain text."""
    output = []
    output.append(f"Found {len(todos)} TODO items\n")
    output.append("=" * 80)

    by_category = group_by_category(todos)

    for category, items in sorted(by_category.items()):
        output.append(f"\n## {category.upper()} ({len(items)} items)")
        output.append("-" * 80)

        for todo in items:
            output.append(f"\n{todo.file_path}:{todo.line_number}")
            output.append(f"[{todo.todo_type}] {todo.description}")
            if len(todo.context) > 1:
                output.append("Context:")
                for line in todo.context[1:]:
                    output.append(f"  {line}")

    return "\n".join(output)


def format_markdown(todos: List[TodoItem]) -> str:
    """Format TODOs as markdown."""
    output = []
    output.append(f"# TODO Report\n")
    output.append(f"**Total items:** {len(todos)}\n")

    by_category = group_by_category(todos)

    for category, items in sorted(by_category.items()):
        output.append(f"## {category.title()} ({len(items)} items)\n")

        for todo in items:
            output.append(f"### {todo.file_path}:{todo.line_number}")
            output.append(f"**Type:** `{todo.todo_type}`")
            output.append(f"**Description:** {todo.description}\n")

            if len(todo.context) > 1:
                output.append("**Details:**")
                output.append("```")
                for line in todo.context[1:]:
                    output.append(line.lstrip('#').strip())
                output.append("```\n")

    return "\n".join(output)


def format_summary(todos: List[TodoItem]) -> str:
    """Format TODOs as summary statistics."""
    output = []
    output.append(f"TODO Summary Report")
    output.append("=" * 80)
    output.append(f"Total items: {len(todos)}\n")

    # By type
    by_type = group_by_type(todos)
    output.append("By Type:")
    for todo_type, items in sorted(by_type.items()):
        output.append(f"  {todo_type}: {len(items)}")

    # By category
    by_category = group_by_category(todos)
    output.append("\nBy Category:")
    for category, items in sorted(by_category.items(), key=lambda x: -len(x[1])):
        output.append(f"  {category}: {len(items)}")

    # Top files
    file_counts = defaultdict(int)
    for todo in todos:
        file_counts[todo.file_path] += 1

    output.append("\nTop 10 Files:")
    for file_path, count in sorted(file_counts.items(), key=lambda x: -x[1])[:10]:
        output.append(f"  {file_path}: {count}")

    return "\n".join(output)


def main():
    parser = argparse.ArgumentParser(description="Scan codebase for TODO comments")
    parser.add_argument(
        "--format",
        choices=["text", "markdown", "summary"],
        default="text",
        help="Output format"
    )
    parser.add_argument(
        "--category",
        help="Filter by category (e.g., security, feature)"
    )
    parser.add_argument(
        "--type",
        choices=["TODO", "FIXME", "HACK", "XXX"],
        help="Filter by type"
    )
    parser.add_argument(
        "--output",
        help="Output file (default: stdout)"
    )

    args = parser.parse_args()

    # Scan codebase
    root_dir = Path.cwd()
    exclude_dirs = [
        ".venv", "venv", "node_modules", ".next", "__pycache__",
        ".git", ".pytest_cache", "htmlcov", "dist", "build"
    ]

    print(f"Scanning {root_dir}...")
    todos = scan_directory(root_dir, exclude_dirs)

    # Filter
    if args.category:
        todos = [t for t in todos if t.category.lower() == args.category.lower()]

    if args.type:
        todos = [t for t in todos if t.todo_type == args.type.upper()]

    # Format output
    if args.format == "markdown":
        output = format_markdown(todos)
    elif args.format == "summary":
        output = format_summary(todos)
    else:
        output = format_text(todos)

    # Write output
    if args.output:
        with open(args.output, 'w', encoding='utf-8') as f:
            f.write(output)
        print(f"Report written to {args.output}")
    else:
        print(output)


if __name__ == "__main__":
    main()
