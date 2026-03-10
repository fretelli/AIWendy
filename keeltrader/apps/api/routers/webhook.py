"""Webhook router — handles confirmation callbacks from Feishu/WeChat."""

from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from core.database import get_db_context
from core.logging import get_logger
from services.tool_executor import execute_tool

router = APIRouter()
logger = get_logger(__name__)


class ConfirmationCallback(BaseModel):
    """Callback from external messaging platforms to confirm an action."""
    action: str  # "confirm_order", "reject_order"
    order_data: Optional[dict] = None
    user_id: Optional[str] = None


@router.post("/confirm")
async def handle_confirmation(request: ConfirmationCallback):
    """Handle order confirmation from external channels."""
    if request.action == "confirm_order" and request.order_data:
        async with get_db_context() as session:
            # Re-execute the order with confirmed=True
            order_data = {**request.order_data, "confirmed": True}
            from uuid import UUID
            user_id = UUID(request.user_id) if request.user_id else None
            if not user_id:
                raise HTTPException(status_code=400, detail="Missing user_id")

            result = await execute_tool("place_order", order_data, session, user_id)
            return {"status": "processed", "result": result}

    elif request.action == "reject_order":
        return {"status": "rejected", "message": "Order cancelled"}

    return {"status": "ignored"}


@router.post("/feishu")
async def feishu_webhook(request: Request):
    """Handle Feishu event callback (URL verification + message events)."""
    body = await request.json()

    # URL verification challenge
    if "challenge" in body:
        return {"challenge": body["challenge"]}

    # Process message events
    event = body.get("event", {})
    message = event.get("message", {})
    content = message.get("content", "")

    logger.info("feishu_webhook_received", event_type=body.get("header", {}).get("event_type"))

    return {"code": 0, "msg": "ok"}


@router.post("/wechat")
async def wechat_webhook(request: Request):
    """Handle WeChat message callback."""
    body = await request.json()
    logger.info("wechat_webhook_received", body_keys=list(body.keys()))
    return {"code": 0, "msg": "ok"}
