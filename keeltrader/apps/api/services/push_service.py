"""Push service — sends notifications via feishu-aibot and wechat-aibot webhooks."""

from __future__ import annotations

from typing import Optional
from uuid import UUID

import httpx

from core.logging import get_logger

logger = get_logger(__name__)

# Webhook endpoints (local services on the same Docker network)
FEISHU_WEBHOOK = "http://feishu-aibot:8000/api/push"
WECHAT_WEBHOOK = "http://services-wechat-aibot:18080/api/push"


async def push_message(
    user_id: UUID,
    message: str,
    channel: str = "all",
    title: Optional[str] = None,
) -> dict:
    """Push a message to external channels.

    Args:
        user_id: The user ID (for routing)
        message: Message content
        channel: "feishu", "wechat", or "all"
        title: Optional title for the message
    """
    results = {}

    if channel in ("feishu", "all"):
        results["feishu"] = await _push_feishu(message, title)

    if channel in ("wechat", "all"):
        results["wechat"] = await _push_wechat(message, title)

    return results


async def _push_feishu(message: str, title: Optional[str] = None) -> dict:
    """Push via feishu-aibot webhook."""
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            payload = {
                "msg_type": "text",
                "content": {"text": message},
            }
            if title:
                payload["content"]["title"] = title

            resp = await client.post(FEISHU_WEBHOOK, json=payload)
            if resp.status_code == 200:
                return {"success": True}
            else:
                logger.warning("feishu_push_failed", status=resp.status_code, body=resp.text[:200])
                return {"success": False, "error": f"HTTP {resp.status_code}"}
    except httpx.ConnectError:
        logger.debug("feishu_aibot_not_reachable")
        return {"success": False, "error": "feishu-aibot 不可达"}
    except Exception as e:
        logger.warning("feishu_push_error", error=str(e))
        return {"success": False, "error": str(e)}


async def _push_wechat(message: str, title: Optional[str] = None) -> dict:
    """Push via wechat-aibot webhook."""
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            payload = {
                "msg_type": "text",
                "content": {"text": message},
            }
            if title:
                payload["content"]["title"] = title

            resp = await client.post(WECHAT_WEBHOOK, json=payload)
            if resp.status_code == 200:
                return {"success": True}
            else:
                logger.warning("wechat_push_failed", status=resp.status_code)
                return {"success": False, "error": f"HTTP {resp.status_code}"}
    except httpx.ConnectError:
        logger.debug("wechat_aibot_not_reachable")
        return {"success": False, "error": "wechat-aibot 不可达"}
    except Exception as e:
        logger.warning("wechat_push_error", error=str(e))
        return {"success": False, "error": str(e)}
