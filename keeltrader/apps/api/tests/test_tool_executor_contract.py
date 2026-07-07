"""Contract tests for the shared tool executor surface."""

from uuid import uuid4

import pytest

from services.tool_executor import (
    TOOL_DEFINITIONS,
    TOOL_HANDLERS,
    execute_tool,
    get_openai_tools,
    get_tool_names,
)


def test_every_declared_tool_has_a_handler():
    declared_names = {tool["name"] for tool in TOOL_DEFINITIONS}

    assert declared_names == get_tool_names()
    assert declared_names == set(TOOL_HANDLERS)


def test_tool_names_are_unique():
    names = [tool["name"] for tool in TOOL_DEFINITIONS]

    assert len(names) == len(set(names))


def test_openai_tools_preserve_public_schema_shape():
    openai_tools = get_openai_tools()

    assert len(openai_tools) == len(TOOL_DEFINITIONS)
    assert {tool["function"]["name"] for tool in openai_tools} == {
        tool["name"] for tool in TOOL_DEFINITIONS
    }
    assert all(tool["type"] == "function" for tool in openai_tools)
    assert all("parameters" in tool["function"] for tool in openai_tools)


@pytest.mark.asyncio
async def test_unknown_tool_keeps_compatible_error_shape():
    result = await execute_tool(
        "missing_tool",
        {},
        session=None,  # type: ignore[arg-type]
        user_id=uuid4(),
    )

    assert result == {"error": "Unknown tool: missing_tool"}
