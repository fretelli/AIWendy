"""Chat v2 — tool-use SSE chat endpoint.

Single endpoint that:
1. Takes user message
2. Calls LLM with tool definitions
3. Executes tool calls
4. Streams results back via SSE
"""

from __future__ import annotations

import asyncio
import json
from datetime import datetime
from typing import Any, AsyncIterator, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy import select, and_, desc
from sqlalchemy.ext.asyncio import AsyncSession

from config import get_settings
from core.auth import get_current_user
from core.database import get_session
from core.logging import get_logger
from domain.coach.models import ChatMessage as ChatMessageDB, ChatSession
from domain.user.models import User
from services.tool_executor import execute_tool, get_openai_tools, TOOL_DEFINITIONS

router = APIRouter()
logger = get_logger(__name__)
settings = get_settings()

SYSTEM_PROMPT = """你是 KeelTrader AI 交易助手。你帮助用户管理加密货币和美股交易。

你的能力：
- 查询持仓、盈亏、历史交易
- 分析交易表现和行为模式
- 获取市场行情和技术分析
- 执行交易（需用户确认）
- 回测交易策略
- 搜索知识库

回复规则：
- 用中文回复
- 简洁直接，不啰嗦
- 涉及金额用 $ 标注
- 交易建议必须给出理由
- 下单前必须确认
- 数据展示用结构化格式

当用户说"查持仓"、"看看仓位"等，调用 get_positions。
当用户说"今日盈亏"、"赚了多少"等，调用 get_pnl。
当用户说"买"、"卖"、"开多"、"开空"等，调用 place_order。
当用户说"分析"某个币/股时，调用 analyze_market。
当用户说"回测"时，调用 backtest_strategy。
"""


class ChatMessageRequest(BaseModel):
    message: str
    session_id: Optional[UUID] = None


class QuickActionRequest(BaseModel):
    action: str  # get_positions, get_pnl, analyze_performance, etc.
    params: Optional[dict] = None


@router.post("/send")
async def chat_send(
    request: ChatMessageRequest,
    http_request: Request,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Tool-use chat with SSE streaming."""
    # Get or create chat session
    chat_session = None
    if request.session_id:
        result = await session.execute(
            select(ChatSession).where(
                ChatSession.id == request.session_id,
                ChatSession.user_id == current_user.id,
            )
        )
        chat_session = result.scalar_one_or_none()

    if not chat_session:
        chat_session = ChatSession(
            user_id=current_user.id,
            coach_id="keeltrader-ai",
            title=request.message[:50],
            message_count=0,
        )
        session.add(chat_session)
        await session.commit()
        await session.refresh(chat_session)

    # Save user message
    user_msg = ChatMessageDB(
        session_id=chat_session.id,
        role="user",
        content=request.message,
    )
    session.add(user_msg)
    chat_session.message_count = (chat_session.message_count or 0) + 1
    chat_session.updated_at = datetime.utcnow()
    await session.commit()

    # Load recent history
    history = await _load_history(session, chat_session.id, limit=20)

    return StreamingResponse(
        _stream_tool_use_response(
            user_message=request.message,
            history=history,
            session=session,
            user_id=current_user.id,
            chat_session=chat_session,
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/quick")
async def quick_action(
    request: QuickActionRequest,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Execute a quick action (tool call without LLM)."""
    tool_names = {t["name"] for t in TOOL_DEFINITIONS}
    if request.action not in tool_names:
        raise HTTPException(status_code=400, detail=f"未知操作: {request.action}")

    result = await execute_tool(
        name=request.action,
        args=request.params or {},
        session=session,
        user_id=current_user.id,
    )
    return {"action": request.action, "result": result}


@router.get("/sessions")
async def list_sessions(
    skip: int = 0,
    limit: int = 20,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """List chat sessions."""
    stmt = (
        select(ChatSession)
        .where(ChatSession.user_id == current_user.id)
        .order_by(desc(ChatSession.updated_at))
        .offset(skip)
        .limit(limit)
    )
    result = await session.execute(stmt)
    sessions = result.scalars().all()

    return {
        "sessions": [
            {
                "id": str(s.id),
                "title": s.title,
                "message_count": s.message_count,
                "updated_at": s.updated_at.isoformat() if s.updated_at else None,
            }
            for s in sessions
        ],
    }


@router.get("/sessions/{session_id}/messages")
async def get_session_messages(
    session_id: UUID,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Get messages for a chat session."""
    # Verify ownership
    cs_result = await session.execute(
        select(ChatSession).where(
            ChatSession.id == session_id,
            ChatSession.user_id == current_user.id,
        )
    )
    if not cs_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="会话不存在")

    stmt = (
        select(ChatMessageDB)
        .where(ChatMessageDB.session_id == session_id)
        .order_by(ChatMessageDB.created_at.asc())
    )
    result = await session.execute(stmt)
    messages = result.scalars().all()

    return {
        "messages": [
            {
                "id": str(m.id),
                "role": m.role,
                "content": m.content,
                "tool_calls": m.message_metadata.get("tool_calls") if m.message_metadata else None,
                "created_at": m.created_at.isoformat() if m.created_at else None,
            }
            for m in messages
        ],
    }


async def _load_history(
    session: AsyncSession, session_id: UUID, limit: int = 20
) -> list[dict]:
    """Load recent chat history as OpenAI messages."""
    stmt = (
        select(ChatMessageDB)
        .where(ChatMessageDB.session_id == session_id)
        .order_by(desc(ChatMessageDB.created_at))
        .limit(limit)
    )
    result = await session.execute(stmt)
    messages = list(reversed(result.scalars().all()))

    return [{"role": m.role, "content": m.content} for m in messages[:-1]]  # Exclude current message


async def _stream_tool_use_response(
    user_message: str,
    history: list[dict],
    session: AsyncSession,
    user_id: UUID,
    chat_session: ChatSession,
) -> AsyncIterator[str]:
    """Stream LLM response with tool use."""
    from openai import AsyncOpenAI

    client = AsyncOpenAI(
        api_key=settings.openai_api_key,
        base_url=settings.openai_base_url if hasattr(settings, "openai_base_url") else None,
    )

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        *history,
        {"role": "user", "content": user_message},
    ]

    tools = get_openai_tools()
    accumulated_text = ""
    tool_calls_made = []

    try:
        # First LLM call (may include tool calls)
        response = await client.chat.completions.create(
            model="claude-sonnet-4-20250514",
            messages=messages,
            tools=tools,
            tool_choice="auto",
            max_tokens=2000,
            stream=False,  # Non-streaming for tool-use loop
        )

        choice = response.choices[0]
        max_iterations = 5
        iteration = 0

        while choice.finish_reason == "tool_calls" and iteration < max_iterations:
            iteration += 1
            # Execute tool calls
            tool_results = []
            for tc in choice.message.tool_calls:
                tool_name = tc.function.name
                try:
                    tool_args = json.loads(tc.function.arguments)
                except json.JSONDecodeError:
                    tool_args = {}

                # Stream tool call event
                yield f"data: {json.dumps({'type': 'tool_call', 'name': tool_name, 'args': tool_args})}\n\n"

                result = await execute_tool(tool_name, tool_args, session, user_id)
                tool_calls_made.append({"name": tool_name, "args": tool_args, "result": result})

                # Stream tool result event
                yield f"data: {json.dumps({'type': 'tool_result', 'name': tool_name, 'result': result}, ensure_ascii=False, default=str)}\n\n"

                tool_results.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": json.dumps(result, ensure_ascii=False, default=str),
                })

            # Add assistant message + tool results to context
            messages.append(choice.message.model_dump())
            messages.extend(tool_results)

            # Call LLM again with tool results
            response = await client.chat.completions.create(
                model="claude-sonnet-4-20250514",
                messages=messages,
                tools=tools,
                tool_choice="auto",
                max_tokens=2000,
                stream=False,
            )
            choice = response.choices[0]

        # Stream final text response
        final_text = choice.message.content or ""
        if final_text:
            # Stream in chunks for smooth display
            chunk_size = 20
            for i in range(0, len(final_text), chunk_size):
                chunk = final_text[i:i + chunk_size]
                accumulated_text += chunk
                yield f"data: {json.dumps({'type': 'text', 'content': chunk})}\n\n"
                await asyncio.sleep(0.02)

        yield f"data: {json.dumps({'type': 'done', 'session_id': str(chat_session.id)})}\n\n"

    except Exception as e:
        logger.error("chat_stream_error", error=str(e), exc_info=True)
        yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"
        accumulated_text = f"[错误] {str(e)}"

    # Save assistant message
    try:
        assistant_msg = ChatMessageDB(
            session_id=chat_session.id,
            role="assistant",
            content=accumulated_text,
            message_metadata={"tool_calls": tool_calls_made} if tool_calls_made else None,
        )
        session.add(assistant_msg)
        chat_session.message_count = (chat_session.message_count or 0) + 1
        chat_session.updated_at = datetime.utcnow()
        await session.commit()
    except Exception as e:
        logger.error("save_assistant_msg_failed", error=str(e))
