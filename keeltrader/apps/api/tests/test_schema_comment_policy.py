import ast
import re
import textwrap
from pathlib import Path


BASELINE_REVISION = 32
MIGRATIONS = Path(__file__).resolve().parents[3] / "migrations" / "versions"
IDENT = r'(?:"[^"]+"|[a-zA-Z_][\w$]*)'
QUALIFIED_IDENT = rf'{IDENT}(?:\s*\.\s*{IDENT})?'


def _revision_number(path: Path) -> int | None:
    match = re.match(r"(\d+)", path.name)
    return int(match.group(1)) if match else None


def _plain_identifier(value: str) -> str:
    return value.split(".")[-1].strip().strip('"').lower()


def _create_table_columns(source: str) -> list[tuple[str, list[str]]]:
    results: list[tuple[str, list[str]]] = []
    pattern = re.compile(
        rf"CREATE\s+TABLE(?:\s+IF\s+NOT\s+EXISTS)?\s+({QUALIFIED_IDENT})\s*\(",
        re.I,
    )
    for match in pattern.finditer(source):
        depth = 1
        quote: str | None = None
        index = match.end()
        while index < len(source) and depth:
            char = source[index]
            if quote:
                if char == quote and (index + 1 >= len(source) or source[index + 1] != quote):
                    quote = None
                elif char == quote and index + 1 < len(source) and source[index + 1] == quote:
                    index += 1
            elif char in "'\"":
                quote = char
            elif char == "(":
                depth += 1
            elif char == ")":
                depth -= 1
            index += 1
        body = source[match.end() : index - 1]
        parts: list[str] = []
        start = 0
        depth = 0
        quote = None
        for offset, char in enumerate(body):
            if quote:
                if char == quote:
                    quote = None
            elif char in "'\"":
                quote = char
            elif char == "(":
                depth += 1
            elif char == ")":
                depth -= 1
            elif char == "," and depth == 0:
                parts.append(body[start:offset])
                start = offset + 1
        parts.append(body[start:])
        columns = []
        for part in parts:
            token = re.match(rf"\s*({IDENT})", part)
            if not token:
                continue
            name = _plain_identifier(token.group(1))
            if name not in {"constraint", "primary", "foreign", "unique", "check", "exclude", "like"}:
                columns.append(name)
        results.append((_plain_identifier(match.group(1)), columns))
    return results


def _sql_comment_targets(source: str) -> tuple[set[str], set[tuple[str, str]]]:
    tables = {
        _plain_identifier(value)
        for value in re.findall(rf"COMMENT\s+ON\s+TABLE\s+({QUALIFIED_IDENT})\s+IS\b", source, re.I)
    }
    columns = {
        (_plain_identifier(table), _plain_identifier(column))
        for table, column in re.findall(
            rf"COMMENT\s+ON\s+COLUMN\s+({QUALIFIED_IDENT})\s*\.\s*({IDENT})\s+IS\b",
            source,
            re.I,
        )
    }
    return tables, columns


def _nonempty_keyword(call: ast.Call, keyword: str) -> bool:
    value = next((item.value for item in call.keywords if item.arg == keyword), None)
    return isinstance(value, ast.Constant) and isinstance(value.value, str) and bool(value.value.strip())


def _call_name(call: ast.Call) -> str:
    return call.func.attr if isinstance(call.func, ast.Attribute) else ""


def _alembic_violations(source: str) -> list[str]:
    violations: list[str] = []
    tree = ast.parse(textwrap.dedent(source))
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        if _call_name(node) == "create_table" and node.args and isinstance(node.args[0], ast.Constant):
            table = str(node.args[0].value)
            if not _nonempty_keyword(node, "comment"):
                violations.append(f"table:{table}")
            for argument in node.args[1:]:
                if isinstance(argument, ast.Call) and _call_name(argument) == "Column" and argument.args:
                    if isinstance(argument.args[0], ast.Constant) and not _nonempty_keyword(argument, "comment"):
                        violations.append(f"column:{table}.{argument.args[0].value}")
        elif _call_name(node) == "add_column" and len(node.args) >= 2:
            table_arg, column_arg = node.args[:2]
            if (
                isinstance(table_arg, ast.Constant)
                and isinstance(column_arg, ast.Call)
                and _call_name(column_arg) == "Column"
                and column_arg.args
                and isinstance(column_arg.args[0], ast.Constant)
                and not _nonempty_keyword(column_arg, "comment")
            ):
                violations.append(f"column:{table_arg.value}.{column_arg.args[0].value}")
    return violations


def comment_policy_violations(source: str) -> list[str]:
    violations = _alembic_violations(source)
    table_comments, column_comments = _sql_comment_targets(source)
    for table, columns in _create_table_columns(source):
        if table not in table_comments:
            violations.append(f"table:{table}")
        violations.extend(
            f"column:{table}.{column}" for column in columns if (table, column) not in column_comments
        )
    for table, column in re.findall(
        rf"ALTER\s+TABLE\s+({QUALIFIED_IDENT})\s+ADD\s+COLUMN(?:\s+IF\s+NOT\s+EXISTS)?\s+({IDENT})",
        source,
        re.I,
    ):
        target = (_plain_identifier(table), _plain_identifier(column))
        if target not in column_comments:
            violations.append(f"column:{target[0]}.{target[1]}")
    return list(dict.fromkeys(violations))


def test_future_migrations_cannot_add_undocumented_schema_objects():
    future = [
        path
        for path in MIGRATIONS.glob("*.py")
        if (_revision_number(path) or 0) > BASELINE_REVISION
    ]
    violations = {
        path.name: found
        for path in future
        if (found := comment_policy_violations(path.read_text(encoding="utf-8")))
    }
    assert not violations


def test_comment_policy_checks_each_sql_table_and_column():
    source = '''
        op.execute("CREATE TABLE public.sample (id UUID, note TEXT, PRIMARY KEY (id))")
        op.execute("COMMENT ON TABLE public.sample IS 'sample'; COMMENT ON COLUMN public.sample.id IS 'id'")
        op.execute("ALTER TABLE public.sample ADD COLUMN extra TEXT")
    '''
    assert comment_policy_violations(source) == ["column:sample.note", "column:sample.extra"]


def test_comment_policy_checks_each_alembic_object():
    source = '''
from alembic import op
import sqlalchemy as sa
op.create_table("sample", sa.Column("id", sa.UUID(), comment="id"), sa.Column("note", sa.Text()), comment="sample")
op.add_column("sample", sa.Column("extra", sa.Text()))
'''
    assert comment_policy_violations(source) == ["column:sample.note", "column:sample.extra"]
