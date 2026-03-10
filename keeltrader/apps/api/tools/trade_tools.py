"""Trade-related tools: get_positions, query_trades, manage_journal."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Optional
from uuid import UUID

from sqlalchemy import select, and_, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from apps.exchange.factory import create_adapter
from core.encryption import get_encryption_service
from core.logging import get_logger
from domain.exchange.models import ExchangeConnection, ExchangeTrade
from domain.journal.models import Journal, TradeDirection, TradeResult

logger = get_logger(__name__)
encryption = get_encryption_service()


async def get_positions(
    session: AsyncSession,
    user_id: UUID,
    exchange: Optional[str] = None,
    symbol: Optional[str] = None,
) -> dict[str, Any]:
    """获取当前持仓。"""
    connections = await _get_active_connections(session, user_id, exchange)
    if not connections:
        return {"positions": [], "message": "没有配置交易所连接"}

    all_positions = []
    for conn in connections:
        try:
            adapter = _build_adapter(conn)
            positions = await adapter.fetch_positions(symbol)
            for pos in positions:
                all_positions.append({
                    "exchange": conn.exchange_type.value,
                    "symbol": pos.symbol,
                    "side": pos.side,
                    "size": pos.size,
                    "notional": pos.notional,
                    "entry_price": pos.entry_price,
                    "mark_price": pos.mark_price,
                    "unrealized_pnl": pos.unrealized_pnl,
                    "leverage": pos.leverage,
                    "liquidation_price": pos.liquidation_price,
                    "margin_mode": pos.margin_mode,
                })
            await adapter.close()
        except Exception as e:
            logger.warning("fetch_positions_failed", exchange=conn.exchange_type.value, error=str(e))
            all_positions.append({
                "exchange": conn.exchange_type.value,
                "error": str(e),
            })

    total_unrealized_pnl = sum(
        p.get("unrealized_pnl", 0) for p in all_positions if "error" not in p
    )
    return {
        "positions": all_positions,
        "total_unrealized_pnl": total_unrealized_pnl,
        "count": len([p for p in all_positions if "error" not in p]),
    }


async def query_trades(
    session: AsyncSession,
    user_id: UUID,
    symbol: Optional[str] = None,
    days: int = 7,
    limit: int = 50,
) -> dict[str, Any]:
    """查询历史交易记录。"""
    since = datetime.utcnow() - timedelta(days=days)
    conditions = [
        ExchangeTrade.user_id == user_id,
        ExchangeTrade.trade_timestamp >= since,
    ]
    if symbol:
        conditions.append(ExchangeTrade.symbol.ilike(f"%{symbol}%"))

    stmt = (
        select(ExchangeTrade)
        .where(and_(*conditions))
        .order_by(desc(ExchangeTrade.trade_timestamp))
        .limit(limit)
    )
    result = await session.execute(stmt)
    trades = result.scalars().all()

    return {
        "trades": [
            {
                "id": str(t.id),
                "symbol": t.symbol,
                "side": t.side,
                "price": float(t.price) if t.price else None,
                "amount": float(t.amount) if t.amount else None,
                "cost": float(t.cost) if t.cost else None,
                "fee_cost": float(t.fee_cost) if t.fee_cost else None,
                "timestamp": t.trade_timestamp.isoformat() if t.trade_timestamp else None,
            }
            for t in trades
        ],
        "count": len(trades),
        "period_days": days,
    }


async def manage_journal(
    session: AsyncSession,
    user_id: UUID,
    action: str = "list",
    journal_id: Optional[str] = None,
    data: Optional[dict] = None,
    days: int = 30,
    limit: int = 20,
) -> dict[str, Any]:
    """管理交易日志：list/create/update/get。"""
    if action == "list":
        since = datetime.utcnow() - timedelta(days=days)
        stmt = (
            select(Journal)
            .where(
                Journal.user_id == user_id,
                Journal.deleted_at.is_(None),
                Journal.trade_date >= since,
            )
            .order_by(desc(Journal.trade_date))
            .limit(limit)
        )
        result = await session.execute(stmt)
        journals = result.scalars().all()
        return {
            "journals": [_journal_to_dict(j) for j in journals],
            "count": len(journals),
        }

    elif action == "get" and journal_id:
        stmt = select(Journal).where(
            Journal.id == journal_id,
            Journal.user_id == user_id,
            Journal.deleted_at.is_(None),
        )
        result = await session.execute(stmt)
        journal = result.scalar_one_or_none()
        if not journal:
            return {"error": "日志不存在"}
        return {"journal": _journal_to_dict(journal)}

    elif action == "create" and data:
        direction = TradeDirection.LONG if data.get("direction", "long").lower() == "long" else TradeDirection.SHORT
        journal = Journal(
            user_id=user_id,
            symbol=data.get("symbol", ""),
            market=data.get("market", "crypto"),
            direction=direction,
            trade_date=datetime.utcnow(),
            entry_time=datetime.utcnow(),
            entry_price=data.get("entry_price"),
            exit_price=data.get("exit_price"),
            position_size=data.get("position_size"),
            result=TradeResult.OPEN,
            notes=data.get("notes", ""),
            tags=data.get("tags", []),
        )
        session.add(journal)
        await session.commit()
        await session.refresh(journal)
        return {"journal": _journal_to_dict(journal), "message": "日志已创建"}

    return {"error": f"不支持的操作: {action}"}


def _journal_to_dict(j: Journal) -> dict:
    return {
        "id": str(j.id),
        "symbol": j.symbol,
        "market": j.market,
        "direction": j.direction.value if j.direction else None,
        "trade_date": j.trade_date.isoformat() if j.trade_date else None,
        "entry_price": float(j.entry_price) if j.entry_price else None,
        "exit_price": float(j.exit_price) if j.exit_price else None,
        "position_size": float(j.position_size) if j.position_size else None,
        "result": j.result.value if j.result else None,
        "pnl": float(j.pnl) if j.pnl else None,
        "pnl_percentage": float(j.pnl_percentage) if j.pnl_percentage else None,
        "notes": j.notes,
        "tags": j.tags,
    }


async def _get_active_connections(
    session: AsyncSession,
    user_id: UUID,
    exchange: Optional[str] = None,
) -> list:
    conditions = [
        ExchangeConnection.user_id == user_id,
        ExchangeConnection.is_active == True,
    ]
    if exchange:
        conditions.append(ExchangeConnection.exchange_type == exchange)
    stmt = select(ExchangeConnection).where(and_(*conditions))
    result = await session.execute(stmt)
    return result.scalars().all()


def _build_adapter(conn: ExchangeConnection):
    creds = {
        "api_key": encryption.decrypt(conn.api_key_encrypted),
        "api_secret": encryption.decrypt(conn.api_secret_encrypted),
        "passphrase": (
            encryption.decrypt(conn.passphrase_encrypted)
            if conn.passphrase_encrypted
            else None
        ),
    }
    mode = conn.trading_mode.value if conn.trading_mode else "swap"
    return create_adapter(
        exchange_name=conn.exchange_type.value,
        api_key=creds["api_key"],
        api_secret=creds["api_secret"],
        passphrase=creds["passphrase"],
        trading_mode=mode,
        is_testnet=conn.is_testnet,
        use_cache=False,
    )
