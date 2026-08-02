from __future__ import annotations

import csv
import hashlib
import html
import io
import json
import math
from collections import defaultdict
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any
from uuid import UUID

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from domain.agentos.models import (
    ConsensusSnapshot,
    DecisionRecord,
    DecisionRevision,
    PortfolioAccount,
    PortfolioDailySnapshot,
    PortfolioImportBatch,
    PortfolioInstrument,
    PortfolioManualPrice,
    PortfolioTransaction,
    ResearchDocument,
    ResearchDocumentDownload,
    ResearchDocumentVersion,
    ResearchHypothesis,
    ResearchHypothesisRevision,
    StrategyExperiment,
    StrategyRunVersion,
)
from services.agent_platform.tushare import TushareReadService


ZERO = Decimal("0")
INSTRUMENT_ALIASES = {
    "stock": "stock", "equity": "stock", "a_share": "stock", "etf": "etf",
    "fund": "open_fund", "open_fund": "open_fund", "mutual_fund": "open_fund",
    "future": "future", "futures": "future", "option": "option", "options": "option",
    "convertible_bond": "convertible_bond", "cb": "convertible_bond", "cash": "cash",
    "fx": "fx", "foreign_exchange": "fx", "alternative": "alternative", "alternatives": "alternative",
    "manual": "manual",
}
STRATEGY_TEMPLATES = {
    "dividend_low_vol": {
        "name": "红利低波",
        "name_en": "Dividend Low Volatility",
        "rebalance": "monthly",
        "default_cost_bps": 10,
        "description": "股息率与反向 60 日波动率综合排名，月度前 30 等权。",
    },
    "momentum_trend": {
        "name": "动量趋势",
        "name_en": "Momentum Trend",
        "rebalance": "monthly",
        "default_cost_bps": 10,
        "description": "12-1 动量且价格高于 200 日均线，月度前 20 等权。",
    },
    "quality_growth": {
        "name": "质量成长",
        "name_en": "Quality Growth",
        "rebalance": "quarterly",
        "default_cost_bps": 10,
        "description": "ROE、现金流质量、营收与净利润增长综合排名，季度前 30 等权。",
    },
}


def _decimal(value: Any, field: str, *, allow_empty: bool = False) -> Decimal | None:
    if value is None or str(value).strip() == "":
        if allow_empty:
            return None
        raise ValueError(f"{field} is required")
    try:
        return Decimal(str(value).replace(",", "").strip())
    except InvalidOperation as exc:
        raise ValueError(f"{field} must be numeric") from exc


def _date(value: Any, field: str) -> date:
    try:
        return date.fromisoformat(str(value).strip())
    except ValueError as exc:
        raise ValueError(f"{field} must use YYYY-MM-DD") from exc


def _json_number(value: Decimal | None) -> float | None:
    return None if value is None else float(value)


class AgentOSService:
    def __init__(self, session: AsyncSession, user_id: UUID):
        self.session = session
        self.user_id = user_id
        self.tushare = TushareReadService(session)

    async def _account(self, account_id: UUID) -> PortfolioAccount:
        item = await self.session.scalar(select(PortfolioAccount).where(
            PortfolioAccount.id == account_id, PortfolioAccount.user_id == self.user_id,
        ))
        if item is None:
            raise ValueError("Portfolio account not found")
        return item

    async def list_accounts(self) -> dict[str, Any]:
        rows = (await self.session.scalars(select(PortfolioAccount).where(
            PortfolioAccount.user_id == self.user_id,
        ).order_by(PortfolioAccount.updated_at.desc()))).all()
        return {"items": [self._account_json(row) for row in rows]}

    async def create_account(self, payload: dict[str, Any]) -> dict[str, Any]:
        item = PortfolioAccount(user_id=self.user_id, **payload)
        self.session.add(item)
        await self.session.flush()
        return self._account_json(item)

    async def update_account(self, account_id: UUID, payload: dict[str, Any]) -> dict[str, Any]:
        item = await self._account(account_id)
        for key, value in payload.items():
            setattr(item, key, value)
        item.updated_at = datetime.utcnow()
        await self.session.flush()
        return self._account_json(item)

    @staticmethod
    def _account_json(item: PortfolioAccount) -> dict[str, Any]:
        return {
            "id": str(item.id), "name": item.name, "account_type": item.account_type,
            "base_currency": item.base_currency, "status": item.status,
            "created_at": item.created_at.isoformat(), "updated_at": item.updated_at.isoformat(),
        }

    async def _instrument(self, row: dict[str, Any]) -> PortfolioInstrument:
        symbol = str(row.get("symbol", "")).strip().upper()
        market = str(row.get("market", "CN")).strip().upper()
        if not symbol:
            raise ValueError("symbol is required")
        item = await self.session.scalar(select(PortfolioInstrument).where(
            PortfolioInstrument.user_id == self.user_id,
            PortfolioInstrument.symbol == symbol,
            PortfolioInstrument.market == market,
        ))
        requested_type = self._instrument_type(row.get("instrument_type"), row.get("asset_class"))
        provider_symbol = str(row.get("provider_symbol") or symbol).strip().upper() if requested_type not in {"manual", "alternative", "cash"} else row.get("provider_symbol")
        if item is not None:
            if row.get("instrument_type") and item.instrument_type in {None, "manual"}:
                item.instrument_type = requested_type
                item.provider_symbol = provider_symbol
            return item
        item = PortfolioInstrument(
            user_id=self.user_id,
            symbol=symbol,
            name=str(row.get("name") or symbol).strip(),
            market=market,
            asset_class=str(row.get("asset_class") or "other").strip(),
            instrument_type=requested_type,
            provider_symbol=provider_symbol,
            currency=str(row.get("currency") or "CNY").strip().upper(),
            direction=str(row.get("direction") or "long").strip(),
            multiplier=_decimal(row.get("multiplier", 1), "multiplier"),
            expiry=_date(row["expiry"], "expiry") if row.get("expiry") else None,
            strike=_decimal(row.get("strike"), "strike", allow_empty=True),
            option_type=str(row["option_type"]).strip() if row.get("option_type") else None,
        )
        self.session.add(item)
        await self.session.flush()
        return item

    @staticmethod
    def _instrument_type(explicit: Any, asset_class: Any) -> str:
        if explicit:
            value = INSTRUMENT_ALIASES.get(str(explicit).strip().lower())
            if value:
                return value
            raise ValueError("Unsupported instrument_type")
        return INSTRUMENT_ALIASES.get(str(asset_class or "").strip().lower(), "manual")

    async def add_transaction(self, account_id: UUID, payload: dict[str, Any]) -> dict[str, Any]:
        await self._account(account_id)
        instrument = await self._instrument(payload) if payload.get("symbol") else None
        item = PortfolioTransaction(
            user_id=self.user_id,
            account_id=account_id,
            instrument_id=instrument.id if instrument else None,
            transaction_type=payload["transaction_type"],
            trade_date=payload["trade_date"],
            quantity=payload.get("quantity", ZERO),
            price=payload.get("price"),
            cash_amount=payload.get("cash_amount", ZERO),
            fee=payload.get("fee", ZERO),
            currency=payload.get("currency", instrument.currency if instrument else "CNY"),
            external_ref=payload.get("external_ref"),
            note=payload.get("note"),
            metadata_json=payload.get("metadata_json", {}),
        )
        self.session.add(item)
        await self.session.flush()
        if instrument and payload.get("manual_price") is not None:
            await self.set_manual_price(instrument.id, payload["trade_date"], payload["manual_price"], item.currency, "transaction")
        return self._transaction_json(item, instrument)

    async def list_transactions(self, account_id: UUID) -> dict[str, Any]:
        await self._account(account_id)
        rows = (await self.session.execute(select(PortfolioTransaction, PortfolioInstrument).outerjoin(
            PortfolioInstrument, PortfolioInstrument.id == PortfolioTransaction.instrument_id,
        ).where(
            PortfolioTransaction.user_id == self.user_id,
            PortfolioTransaction.account_id == account_id,
        ).order_by(PortfolioTransaction.trade_date.desc(), PortfolioTransaction.created_at.desc()))).all()
        return {"items": [self._transaction_json(tx, instrument) for tx, instrument in rows]}

    @staticmethod
    def _transaction_json(item: PortfolioTransaction, instrument: PortfolioInstrument | None) -> dict[str, Any]:
        return {
            "id": str(item.id), "account_id": str(item.account_id),
            "instrument_id": str(item.instrument_id) if item.instrument_id else None,
            "symbol": instrument.symbol if instrument else None, "name": instrument.name if instrument else None,
            "transaction_type": item.transaction_type, "trade_date": item.trade_date.isoformat(),
            "quantity": _json_number(item.quantity), "price": _json_number(item.price),
            "cash_amount": _json_number(item.cash_amount), "fee": _json_number(item.fee),
            "currency": item.currency, "note": item.note,
        }

    async def set_manual_price(self, instrument_id: UUID, price_date: date, price: Decimal,
                               currency: str, source_note: str | None) -> dict[str, Any]:
        instrument = await self.session.scalar(select(PortfolioInstrument).where(
            PortfolioInstrument.id == instrument_id, PortfolioInstrument.user_id == self.user_id,
        ))
        if instrument is None:
            raise ValueError("Portfolio instrument not found")
        item = await self.session.scalar(select(PortfolioManualPrice).where(
            PortfolioManualPrice.user_id == self.user_id,
            PortfolioManualPrice.instrument_id == instrument_id,
            PortfolioManualPrice.price_date == price_date,
        ))
        if item is None:
            item = PortfolioManualPrice(user_id=self.user_id, instrument_id=instrument_id, price_date=price_date,
                                        price=price, currency=currency, source_note=source_note)
            self.session.add(item)
        else:
            item.price = price
            item.currency = currency
            item.source_note = source_note
        await self.session.flush()
        return {"id": str(item.id), "instrument_id": str(instrument_id), "price_date": price_date.isoformat(),
                "price": float(price), "currency": currency, "source_note": source_note}

    async def preview_import(self, account_id: UUID, import_type: str, filename: str,
                             csv_text: str, mapping: dict[str, str]) -> dict[str, Any]:
        await self._account(account_id)
        content = csv_text.encode("utf-8")
        content_hash = hashlib.sha256(content).hexdigest()
        existing = await self.session.scalar(select(PortfolioImportBatch).where(
            PortfolioImportBatch.user_id == self.user_id,
            PortfolioImportBatch.account_id == account_id,
            PortfolioImportBatch.content_hash == content_hash,
        ))
        if existing is not None:
            return self._batch_json(existing)
        reader = csv.DictReader(io.StringIO(csv_text.lstrip("\ufeff")))
        if not reader.fieldnames:
            raise ValueError("CSV header is required")
        rows: list[dict[str, Any]] = []
        errors: list[dict[str, Any]] = []
        for line, source in enumerate(reader, start=2):
            try:
                rows.append(self._normalize_import_row(import_type, source, mapping, line))
            except ValueError as exc:
                errors.append({"line": line, "message": str(exc)})
        item = PortfolioImportBatch(
            user_id=self.user_id, account_id=account_id, import_type=import_type, filename=filename,
            content_hash=content_hash, mapping_json=mapping, rows_json=rows, row_count=len(rows),
            status="invalid" if errors else "preview", error_json=errors,
        )
        self.session.add(item)
        await self.session.flush()
        return self._batch_json(item)

    @staticmethod
    def _value(source: dict[str, Any], mapping: dict[str, str], key: str, default: Any = None) -> Any:
        header = mapping.get(key, key)
        value = source.get(header, default)
        return value.strip() if isinstance(value, str) else value

    def _normalize_import_row(self, import_type: str, source: dict[str, Any], mapping: dict[str, str], line: int) -> dict[str, Any]:
        get = lambda key, default=None: self._value(source, mapping, key, default)
        common = {"line": line, "currency": str(get("currency", "CNY")).upper()}
        if import_type == "positions":
            symbol = str(get("symbol", "")).upper()
            if not symbol:
                raise ValueError("symbol is required")
            return {**common, "symbol": symbol, "name": get("name") or symbol,
                    "market": str(get("market", "CN")).upper(), "asset_class": get("asset_class", "other"),
                    "quantity": str(_decimal(get("quantity"), "quantity")),
                    "price": str(_decimal(get("price"), "price", allow_empty=True)) if get("price") else None,
                    "as_of": _date(get("as_of"), "as_of").isoformat(),
                    "multiplier": str(_decimal(get("multiplier", 1), "multiplier"))}
        if import_type == "transactions":
            transaction_type = str(get("transaction_type", "")).lower()
            if transaction_type not in {"opening", "buy", "sell", "cash", "dividend", "fee", "transfer", "adjustment"}:
                raise ValueError("transaction_type is invalid")
            return {**common, "symbol": str(get("symbol", "")).upper() or None, "name": get("name") or get("symbol"),
                    "market": str(get("market", "CN")).upper(), "asset_class": get("asset_class", "other"),
                    "transaction_type": transaction_type,
                    "trade_date": _date(get("trade_date"), "trade_date").isoformat(),
                    "quantity": str(_decimal(get("quantity", 0), "quantity")),
                    "price": str(_decimal(get("price"), "price", allow_empty=True)) if get("price") else None,
                    "cash_amount": str(_decimal(get("cash_amount", 0), "cash_amount")),
                    "fee": str(_decimal(get("fee", 0), "fee"))}
        if import_type == "nav":
            return {**common, "snapshot_date": _date(get("snapshot_date"), "snapshot_date").isoformat(),
                    "nav": str(_decimal(get("nav"), "nav")), "net_flow": str(_decimal(get("net_flow", 0), "net_flow"))}
        raise ValueError("Unsupported import type")

    async def commit_import(self, batch_id: UUID) -> dict[str, Any]:
        item = await self.session.scalar(select(PortfolioImportBatch).where(
            PortfolioImportBatch.id == batch_id, PortfolioImportBatch.user_id == self.user_id,
        ))
        if item is None:
            raise ValueError("Import batch not found")
        if item.status == "committed":
            return self._batch_json(item)
        if item.error_json:
            raise ValueError("Import batch contains validation errors")
        account = await self._account(item.account_id)
        for index, row in enumerate(item.rows_json):
            if item.import_type == "nav":
                self.session.add(PortfolioDailySnapshot(
                    user_id=self.user_id, account_id=account.id, snapshot_date=_date(row["snapshot_date"], "snapshot_date"),
                    base_currency=row["currency"], nav=_decimal(row["nav"], "nav"),
                    net_flow=_decimal(row["net_flow"], "net_flow"), data_status="complete",
                    source_snapshot={"source": "csv", "batch_id": str(item.id)},
                ))
                continue
            instrument = await self._instrument(row) if row.get("symbol") else None
            tx_date = _date(row.get("as_of") or row.get("trade_date"), "trade_date")
            price = _decimal(row.get("price"), "price", allow_empty=True)
            transaction = PortfolioTransaction(
                user_id=self.user_id, account_id=account.id, instrument_id=instrument.id if instrument else None,
                transaction_type="opening" if item.import_type == "positions" else row["transaction_type"],
                trade_date=tx_date, quantity=_decimal(row.get("quantity", 0), "quantity"), price=price,
                cash_amount=_decimal(row.get("cash_amount", 0), "cash_amount"), fee=_decimal(row.get("fee", 0), "fee"),
                currency=row["currency"], external_ref=f"import:{item.id}:{index}", metadata_json={"import_batch_id": str(item.id)},
            )
            self.session.add(transaction)
            if instrument and price is not None:
                await self.set_manual_price(instrument.id, tx_date, price, row["currency"], f"CSV {item.filename}")
        item.status = "committed"
        item.committed_at = datetime.utcnow()
        await self.session.flush()
        return self._batch_json(item)

    @staticmethod
    def _batch_json(item: PortfolioImportBatch) -> dict[str, Any]:
        return {"id": str(item.id), "account_id": str(item.account_id), "import_type": item.import_type,
                "filename": item.filename, "content_hash": item.content_hash, "row_count": item.row_count,
                "status": item.status, "errors": item.error_json, "rows": item.rows_json,
                "committed_at": item.committed_at.isoformat() if item.committed_at else None}

    async def valuation(self, account_id: UUID, as_of: date) -> dict[str, Any]:
        account = await self._account(account_id)
        rows = (await self.session.execute(select(PortfolioTransaction, PortfolioInstrument).outerjoin(
            PortfolioInstrument, PortfolioInstrument.id == PortfolioTransaction.instrument_id,
        ).where(
            PortfolioTransaction.user_id == self.user_id,
            PortfolioTransaction.account_id == account_id,
            PortfolioTransaction.trade_date <= as_of,
        ).order_by(PortfolioTransaction.trade_date, PortfolioTransaction.created_at))).all()
        state: dict[UUID, dict[str, Any]] = {}
        cash = defaultdict(lambda: ZERO)
        for tx, instrument in rows:
            explicit_cash = Decimal(tx.cash_amount)
            trade_cash = explicit_cash
            if instrument is None:
                cash[tx.currency] += explicit_cash - Decimal(tx.fee)
                continue
            bucket = state.setdefault(instrument.id, {"instrument": instrument, "quantity": ZERO, "cost": ZERO,
                                                       "last_price": None, "last_price_date": None})
            old_qty = bucket["quantity"]
            qty = Decimal(tx.quantity)
            # CSV/manual ledgers commonly record a positive quantity for a
            # sell.  Normalize the position delta from the immutable event
            # type while preserving explicitly signed adjustments.
            if instrument.direction == "short" and tx.transaction_type in {"buy", "sell"}:
                # A buy covers a short; a sell opens/increases one.  The
                # explicit opening event remains a positive position delta.
                qty = -abs(qty) if tx.transaction_type == "buy" else abs(qty)
            elif tx.transaction_type in {"sell", "reduced", "close", "redeem"}:
                qty = -abs(qty)
            elif tx.transaction_type in {"buy", "opening", "increased", "subscribe"}:
                qty = abs(qty)
            price = Decimal(tx.price) if tx.price is not None else None
            multiplier = Decimal(instrument.multiplier)
            direction_sign = Decimal("-1") if instrument.direction == "short" else Decimal("1")
            if price is not None and explicit_cash == ZERO and tx.transaction_type in {"buy", "sell", "opening"}:
                trade_cash = -(qty * price * multiplier * direction_sign)
            cash[tx.currency] += trade_cash - Decimal(tx.fee)
            if qty > 0 and price is not None:
                bucket["cost"] += qty * price * multiplier
            elif qty < 0 and old_qty > 0:
                average_notional = bucket["cost"] / old_qty if old_qty else ZERO
                closed = min(old_qty, abs(qty))
                if price is not None:
                    bucket["realized_pnl"] = bucket.get("realized_pnl", ZERO) + (
                        price * multiplier - average_notional
                    ) * closed * direction_sign
                bucket["cost"] = max(ZERO, bucket["cost"] - average_notional * closed)
            bucket["quantity"] += qty
            if price is not None:
                bucket["last_price"] = price
                bucket["last_price_date"] = tx.trade_date
        positions = []
        total = ZERO
        missing: list[dict[str, Any]] = []
        cash_detail = {}
        for currency, amount in cash.items():
            fx = await self.tushare.direct_fx_rate(currency, account.base_currency, as_of)
            converted = amount * Decimal(str(fx["rate"])) if fx else None
            if converted is None:
                missing.append({"kind": "cash", "currency": currency, "reason": "direct_fx_unavailable"})
            else:
                total += converted
            cash_detail[currency] = {"amount": float(amount), "base_value": _json_number(converted),
                "fx_source": fx.get("source") if fx else None,
                "fx_as_of": str(fx.get("fx_as_of")) if fx and fx.get("fx_as_of") else None}
        for instrument_id, bucket in state.items():
            quantity = bucket["quantity"]
            if quantity == 0:
                continue
            instrument = bucket["instrument"]
            resolved = await self._resolve_price(instrument, as_of, bucket["last_price"], bucket["last_price_date"])
            price, price_date = resolved.get("price"), resolved.get("price_as_of")
            market_value = None
            if price is None:
                missing.append({"kind": "position", "symbol": instrument.symbol, "reason": resolved.get("reason", "price_unavailable")})
            else:
                native_value = quantity * price * Decimal(instrument.multiplier) * (Decimal("-1") if instrument.direction == "short" else Decimal("1"))
                fx = await self.tushare.direct_fx_rate(instrument.currency, account.base_currency, as_of)
                if fx is None:
                    missing.append({"kind": "position", "symbol": instrument.symbol,
                                    "reason": f"direct_fx_unavailable:{instrument.currency}/{account.base_currency}"})
                else:
                    market_value = native_value * Decimal(str(fx["rate"]))
                    total += market_value
                    resolved["fx_source"] = fx.get("source")
                    resolved["fx_as_of"] = fx.get("fx_as_of")
            if resolved.get("price_status") == "stale":
                missing.append({"kind": "position", "symbol": instrument.symbol, "reason": "price_stale",
                                "price_as_of": str(price_date) if price_date else None})
            direction_sign = Decimal("-1") if instrument.direction == "short" else Decimal("1")
            cost_basis = bucket["cost"] * direction_sign
            positions.append({
                "instrument_id": str(instrument_id), "symbol": instrument.symbol, "name": instrument.name,
                "market": instrument.market, "asset_class": instrument.asset_class,
                "instrument_type": instrument.instrument_type, "provider_symbol": instrument.provider_symbol,
                "direction": instrument.direction, "multiplier": float(instrument.multiplier), "currency": instrument.currency,
                "quantity": float(quantity), "average_cost": float(bucket["cost"] / quantity / Decimal(instrument.multiplier)) if quantity else None,
                "price": _json_number(price), "price_status": resolved.get("price_status"),
                "price_as_of": price_date.isoformat() if isinstance(price_date, date) else (str(price_date) if price_date else None),
                "price_date": price_date.isoformat() if isinstance(price_date, date) else (str(price_date) if price_date else None),
                "price_source": resolved.get("price_source"), "fx_source": resolved.get("fx_source"),
                "fx_as_of": str(resolved.get("fx_as_of")) if resolved.get("fx_as_of") else None,
                "valuation_method": resolved.get("valuation_method"), "market_value": _json_number(market_value),
                "realized_pnl": _json_number(bucket.get("realized_pnl", ZERO)),
                "unrealized_pnl": _json_number(market_value - cost_basis) if market_value is not None else None,
                "gap_reason": resolved.get("reason"),
            })
        return {
            "account": self._account_json(account), "as_of": as_of.isoformat(),
            "data_status": "partial" if missing else "complete", "total_value": float(total),
            "base_currency": account.base_currency, "cash": cash_detail,
            "positions": positions, "missing": missing,
        }

    async def _resolve_price(self, instrument: PortfolioInstrument, as_of: date,
                             transaction_price: Decimal | None, transaction_date: date | None) -> dict[str, Any]:
        manual = await self.session.scalar(select(PortfolioManualPrice).where(
            PortfolioManualPrice.user_id == self.user_id,
            PortfolioManualPrice.instrument_id == instrument.id,
            PortfolioManualPrice.price_date <= as_of,
        ).order_by(PortfolioManualPrice.price_date.desc()).limit(1))
        # Provider-native prices always win for typed instruments.  Transaction
        # imports also create a manual price row, so looking at that first
        # would silently make a historical trade price masquerade as a quote.
        official = await self.tushare.latest_instrument_price(
            instrument.instrument_type, instrument.provider_symbol or instrument.symbol, as_of)
        if official and official.get("price") is not None:
            raw_date = official.get("price_as_of")
            price_date = raw_date if isinstance(raw_date, date) else date.fromisoformat(str(raw_date)[:10])
            age = (as_of - price_date).days
            threshold = 14 if instrument.instrument_type == "open_fund" else 7
            return {"price": Decimal(str(official["price"])), "price_as_of": price_date,
                    "price_source": official["source"], "price_status": "current" if age <= threshold else "stale",
                    "valuation_method": official["valuation_method"], "reason": None if age <= threshold else "published_price_stale"}
        if manual is not None:
            age = (as_of - manual.price_date).days
            if instrument.instrument_type in {"alternative", "manual"}:
                threshold = 45
                return {"price": Decimal(manual.price), "price_as_of": manual.price_date, "price_source": "manual",
                        "price_status": "current" if age <= threshold else "stale", "valuation_method": "dated_manual_nav",
                        "reason": None if age <= threshold else "manual_price_stale"}
            # For typed instruments a manual row is only a short-lived gap
            # fallback and is always labelled stale; it never becomes a
            # durable substitute for the provider's official series.
            if age <= 3:
                return {"price": Decimal(manual.price), "price_as_of": manual.price_date, "price_source": "manual",
                        "price_status": "stale", "valuation_method": "dated_manual_fallback",
                        "reason": "official_price_unavailable"}
        if transaction_price is not None and transaction_date is not None and (as_of - transaction_date).days <= 3:
            return {"price": transaction_price, "price_as_of": transaction_date, "price_source": "transaction",
                    "price_status": "stale", "valuation_method": "recent_transaction_fallback",
                    "reason": "official_price_unavailable"}
        return {"price": None, "price_as_of": None, "price_source": None, "price_status": "unavailable",
                "valuation_method": None, "reason": "official_or_dated_manual_price_unavailable"}

    async def nav_history(self, account_id: UUID) -> dict[str, Any]:
        await self._account(account_id)
        rows = (await self.session.scalars(select(PortfolioDailySnapshot).where(
            PortfolioDailySnapshot.user_id == self.user_id,
            PortfolioDailySnapshot.account_id == account_id,
        ).order_by(PortfolioDailySnapshot.snapshot_date))).all()
        points = []
        prior: PortfolioDailySnapshot | None = None
        for row in rows:
            daily_return = None
            if prior and Decimal(prior.nav) != 0:
                daily_return = (Decimal(row.nav) - Decimal(row.net_flow)) / Decimal(prior.nav) - 1
            points.append({"date": row.snapshot_date.isoformat(), "nav": float(row.nav), "net_flow": float(row.net_flow),
                           "return": _json_number(daily_return), "data_status": row.data_status})
            prior = row
        return {"items": points, "history_available": bool(points)}

    async def list_hypotheses(self) -> dict[str, Any]:
        rows = (await self.session.scalars(select(ResearchHypothesis).where(
            ResearchHypothesis.user_id == self.user_id,
        ).order_by(ResearchHypothesis.updated_at.desc()))).all()
        return {"items": [await self._hypothesis_json(item) for item in rows]}

    async def create_hypothesis(self, payload: dict[str, Any]) -> dict[str, Any]:
        self._validate_evidence(payload.get("evidence", []))
        item = ResearchHypothesis(user_id=self.user_id, title=payload["title"], status=payload.get("status", "draft"),
                                  review_date=payload.get("review_date"), current_version=1)
        self.session.add(item)
        await self.session.flush()
        self.session.add(ResearchHypothesisRevision(
            hypothesis_id=item.id, version=1, thesis=payload["thesis"], falsification=payload["falsification"],
            evidence_json=payload.get("evidence", []), outcome_json=payload.get("outcome", {}),
            created_by=payload.get("created_by", "user"),
        ))
        await self.session.flush()
        return await self._hypothesis_json(item)

    async def revise_hypothesis(self, hypothesis_id: UUID, payload: dict[str, Any]) -> dict[str, Any]:
        item = await self.session.scalar(select(ResearchHypothesis).where(
            ResearchHypothesis.id == hypothesis_id, ResearchHypothesis.user_id == self.user_id,
        ))
        if item is None:
            raise ValueError("Research hypothesis not found")
        self._validate_evidence(payload.get("evidence", []))
        item.current_version += 1
        item.status = payload.get("status", item.status)
        item.review_date = payload.get("review_date", item.review_date)
        item.updated_at = datetime.utcnow()
        self.session.add(ResearchHypothesisRevision(
            hypothesis_id=item.id, version=item.current_version, thesis=payload["thesis"],
            falsification=payload["falsification"], evidence_json=payload.get("evidence", []),
            outcome_json=payload.get("outcome", {}), created_by=payload.get("created_by", "user"),
        ))
        await self.session.flush()
        return await self._hypothesis_json(item)

    async def _hypothesis_json(self, item: ResearchHypothesis) -> dict[str, Any]:
        revision = await self.session.scalar(select(ResearchHypothesisRevision).where(
            ResearchHypothesisRevision.hypothesis_id == item.id,
            ResearchHypothesisRevision.version == item.current_version,
        ))
        return {"id": str(item.id), "title": item.title, "status": item.status, "current_version": item.current_version,
                "review_date": item.review_date.isoformat() if item.review_date else None,
                "thesis": revision.thesis if revision else "", "falsification": revision.falsification if revision else "",
                "evidence": revision.evidence_json if revision else [], "outcome": revision.outcome_json if revision else {}}

    async def list_decisions(self) -> dict[str, Any]:
        rows = (await self.session.scalars(select(DecisionRecord).where(
            DecisionRecord.user_id == self.user_id,
        ).order_by(DecisionRecord.updated_at.desc()))).all()
        return {"items": [await self._decision_json(item) for item in rows]}

    async def create_decision(self, payload: dict[str, Any]) -> dict[str, Any]:
        self._validate_evidence(payload.get("evidence", []))
        status = payload.get("status", "draft")
        item = DecisionRecord(user_id=self.user_id, title=payload["title"], status=status,
                              hypothesis_id=payload.get("hypothesis_id"), review_date=payload.get("review_date"),
                              decided_at=datetime.utcnow() if status == "confirmed" else None, current_version=1)
        self.session.add(item)
        await self.session.flush()
        self.session.add(DecisionRevision(
            decision_id=item.id, version=1, rationale=payload["rationale"], action_json=payload.get("action", {}),
            conditions_json=payload.get("conditions", []), evidence_json=payload.get("evidence", []),
            attribution_json=payload.get("attribution", {}), created_by=payload.get("created_by", "user"),
        ))
        await self.session.flush()
        return await self._decision_json(item)

    async def revise_decision(self, decision_id: UUID, payload: dict[str, Any]) -> dict[str, Any]:
        item = await self.session.scalar(select(DecisionRecord).where(
            DecisionRecord.id == decision_id, DecisionRecord.user_id == self.user_id,
        ))
        if item is None:
            raise ValueError("Decision record not found")
        self._validate_evidence(payload.get("evidence", []))
        item.current_version += 1
        item.status = payload.get("status", item.status)
        item.review_date = payload.get("review_date", item.review_date)
        if item.status == "confirmed" and item.decided_at is None:
            item.decided_at = datetime.utcnow()
        item.updated_at = datetime.utcnow()
        self.session.add(DecisionRevision(
            decision_id=item.id, version=item.current_version, rationale=payload["rationale"],
            action_json=payload.get("action", {}), conditions_json=payload.get("conditions", []),
            evidence_json=payload.get("evidence", []), attribution_json=payload.get("attribution", {}),
            created_by=payload.get("created_by", "user"),
        ))
        await self.session.flush()
        return await self._decision_json(item)

    async def _decision_json(self, item: DecisionRecord) -> dict[str, Any]:
        revision = await self.session.scalar(select(DecisionRevision).where(
            DecisionRevision.decision_id == item.id, DecisionRevision.version == item.current_version,
        ))
        return {"id": str(item.id), "title": item.title, "status": item.status, "current_version": item.current_version,
                "hypothesis_id": str(item.hypothesis_id) if item.hypothesis_id else None,
                "decided_at": item.decided_at.isoformat() if item.decided_at else None,
                "review_date": item.review_date.isoformat() if item.review_date else None,
                "rationale": revision.rationale if revision else "", "action": revision.action_json if revision else {},
                "conditions": revision.conditions_json if revision else [], "evidence": revision.evidence_json if revision else [],
                "attribution": revision.attribution_json if revision else {}}

    @staticmethod
    def _validate_evidence(evidence: list[dict[str, Any]]) -> None:
        for item in evidence:
            if not item.get("report_id") or not (item.get("page") or item.get("section")):
                raise ValueError("Each evidence item requires report_id and page or section")

    async def strategy_templates(self) -> dict[str, Any]:
        return {"items": [{"key": key, **value} for key, value in STRATEGY_TEMPLATES.items()]}

    async def list_experiments(self) -> dict[str, Any]:
        rows = (await self.session.scalars(select(StrategyExperiment).where(
            StrategyExperiment.user_id == self.user_id,
        ).order_by(StrategyExperiment.updated_at.desc()))).all()
        return {"items": [self._experiment_json(row) for row in rows]}

    async def create_experiment(self, payload: dict[str, Any]) -> dict[str, Any]:
        if payload["template_key"] not in STRATEGY_TEMPLATES:
            raise ValueError("Unsupported strategy template")
        item = StrategyExperiment(user_id=self.user_id, name=payload["name"], template_key=payload["template_key"],
                                  parameters_json=payload.get("parameters", {}))
        self.session.add(item)
        await self.session.flush()
        return self._experiment_json(item)

    @staticmethod
    def _experiment_json(item: StrategyExperiment) -> dict[str, Any]:
        return {"id": str(item.id), "name": item.name, "template_key": item.template_key,
                "status": item.status, "parameters": item.parameters_json}

    async def run_experiment(self, experiment_id: UUID, payload: dict[str, Any]) -> dict[str, Any]:
        experiment = await self.session.scalar(select(StrategyExperiment).where(
            StrategyExperiment.id == experiment_id, StrategyExperiment.user_id == self.user_id,
        ))
        if experiment is None:
            raise ValueError("Strategy experiment not found")
        latest = await self.session.scalar(select(func.max(StrategyRunVersion.version)).where(
            StrategyRunVersion.experiment_id == experiment.id,
        ))
        version = int(latest or 0) + 1
        run = StrategyRunVersion(experiment_id=experiment.id, version=version, status="running",
                                 parameters_json={**experiment.parameters_json, **payload})
        self.session.add(run)
        await self.session.flush()
        try:
            result = await self._backtest(experiment.template_key, run.parameters_json)
        except ValueError as exc:
            run.status = "failed"
            run.error_message = str(exc)
            run.completed_at = datetime.utcnow()
        else:
            run.status = "completed"
            run.data_snapshot = result["data_snapshot"]
            run.metrics_json = result["metrics"]
            run.series_json = result["series"]
            run.trades_json = result["trades"]
            run.completed_at = datetime.utcnow()
        await self.session.flush()
        return self._run_json(run)

    async def _backtest(self, template_key: str, parameters: dict[str, Any]) -> dict[str, Any]:
        symbols = [str(value).strip().upper() for value in parameters.get("symbols", []) if str(value).strip()]
        if not symbols:
            raise ValueError("At least one symbol is required")
        histories: dict[str, dict[str, float]] = {}
        for symbol in symbols[:50]:
            bars = await self.tushare.daily_bars(symbol, limit=min(int(parameters.get("lookback_days", 750)), 1200), adjusted=True)
            normalized = {}
            for bar in bars:
                close = bar.get("close") or bar.get("adj_close")
                raw_date = str(bar.get("trade_date", ""))[:10]
                if close is not None and len(raw_date) == 10:
                    normalized[raw_date] = float(close)
            if len(normalized) >= 60:
                histories[symbol] = normalized
        if not histories:
            raise ValueError("No symbol has enough published price history")
        dates = sorted(set.intersection(*(set(values) for values in histories.values())))
        if len(dates) < 60:
            raise ValueError("Published histories do not have enough common trading dates")
        cost_bps = max(0.0, min(float(parameters.get("cost_bps", STRATEGY_TEMPLATES[template_key]["default_cost_bps"])), 500.0))
        rebalance = STRATEGY_TEMPLATES[template_key]["rebalance"]
        month_ends = {value for index, value in enumerate(dates) if index == len(dates) - 1 or dates[index + 1][:7] != value[:7]}
        rebalance_dates = {value for value in month_ends if rebalance == "monthly" or int(value[5:7]) in {3, 6, 9, 12}}
        top_n = min(int(parameters.get("top_n", 20)), len(histories))
        current_weights = {symbol: 0.0 for symbol in histories}
        nav, benchmark_nav = 1.0, 1.0
        series, trades = [], []
        start_index = 252 if template_key == "momentum_trend" and len(dates) > 252 else 60
        for index in range(start_index, len(dates)):
            day, previous = dates[index], dates[index - 1]
            if previous in rebalance_dates or not any(current_weights.values()):
                signal_day = previous
                prices = {symbol: histories[symbol][signal_day] for symbol in histories}
                factors = {} if template_key == "momentum_trend" else await self.tushare.point_in_time_factors(
                    list(histories), date.fromisoformat(signal_day), prices)
                scored = []
                for symbol, price_history in histories.items():
                    available_dates = dates[:index]
                    closes = [price_history[value] for value in available_dates]
                    recent = closes[-60:]
                    daily_returns = [recent[pos] / recent[pos - 1] - 1 for pos in range(1, len(recent))]
                    mean = sum(daily_returns) / len(daily_returns)
                    volatility = math.sqrt(252) * (sum((value - mean) ** 2 for value in daily_returns) / max(1, len(daily_returns) - 1)) ** .5
                    if template_key == "momentum_trend":
                        moving = sum(closes[-200:]) / min(200, len(closes))
                        score = closes[-22] / closes[-252] - 1 if len(closes) >= 252 and closes[-1] > moving else -999.0
                    elif template_key == "dividend_low_vol":
                        dividend_yield = (factors.get(symbol) or {}).get("dividend_yield")
                        if dividend_yield is None:
                            continue
                        score = float(dividend_yield) - volatility
                    else:
                        values = factors.get(symbol) or {}
                        required = [values.get(key) for key in ("roe", "cash_quality", "revenue_growth", "profit_growth")]
                        if any(value is None for value in required):
                            continue
                        score = sum(float(value) for value in required) / 4
                    if score > -900:
                        scored.append((score, symbol))
                selected = [symbol for _, symbol in sorted(scored, reverse=True)[:top_n]]
                if not selected:
                    raise ValueError(f"Required point-in-time factors are missing at {signal_day}")
                target = {symbol: (1 / len(selected) if symbol in selected else 0.0) for symbol in histories}
                turnover = sum(abs(target[symbol] - current_weights[symbol]) for symbol in histories)
                transaction_cost = turnover * cost_bps / 10_000
                nav *= max(0, 1 - transaction_cost)
                for symbol in histories:
                    if abs(target[symbol] - current_weights[symbol]) > 1e-12:
                        trades.append({"date": signal_day, "symbol": symbol, "from_weight": current_weights[symbol],
                            "to_weight": target[symbol], "turnover": abs(target[symbol] - current_weights[symbol]),
                            "cost_bps": cost_bps, "action": "rebalance"})
                current_weights = target
            day_return = sum(current_weights[symbol] * (histories[symbol][day] / histories[symbol][previous] - 1)
                             for symbol in histories)
            benchmark_return = sum(histories[symbol][day] / histories[symbol][previous] - 1 for symbol in histories) / len(histories)
            nav *= 1 + day_return
            benchmark_nav *= 1 + benchmark_return
            series.append({"date": day, "nav": nav, "benchmark_nav": benchmark_nav})
        if not series:
            raise ValueError("Backtest produced no point-in-time observations")
        total_return = series[-1]["nav"] - 1
        years = max(len(series) / 252, 1 / 252)
        cagr = series[-1]["nav"] ** (1 / years) - 1
        nav_returns = [series[index]["nav"] / series[index - 1]["nav"] - 1 for index in range(1, len(series))]
        mean = sum(nav_returns) / max(1, len(nav_returns))
        vol = math.sqrt(252) * (sum((value - mean) ** 2 for value in nav_returns) / max(1, len(nav_returns) - 1)) ** 0.5
        peak = 0.0
        max_drawdown = 0.0
        for point in series:
            peak = max(peak, point["nav"])
            max_drawdown = min(max_drawdown, point["nav"] / peak - 1 if peak else 0)
        return {
            "data_snapshot": {"source": "tushare", "symbols": selected, "universe": sorted(histories), "as_of": series[-1]["date"],
                              "cost_bps": cost_bps,
                              "rebalance": rebalance, "fundamentals_parameter_ignored": bool(parameters.get("fundamentals")),
                              "note": "Backend joins published point-in-time fundamentals by announcement date; every rebalance charges turnover cost and no caller-supplied factor is used."},
            "metrics": {"total_return": total_return, "cagr": cagr, "volatility": vol,
                        "max_drawdown": max_drawdown, "sharpe": cagr / vol if vol else None,
                        "benchmark_total_return": series[-1]["benchmark_nav"] - 1,
                        "excess_return": series[-1]["nav"] - series[-1]["benchmark_nav"]},
            "series": series,
            "trades": trades,
        }

    @staticmethod
    def _run_json(run: StrategyRunVersion) -> dict[str, Any]:
        return {"id": str(run.id), "experiment_id": str(run.experiment_id), "version": run.version,
                "status": run.status, "parameters": run.parameters_json, "data_snapshot": run.data_snapshot,
                "metrics": run.metrics_json, "series": run.series_json, "trades": run.trades_json,
                "error_message": run.error_message}

    async def consensus(self, subject_type: str | None = None, subject_code: str | None = None) -> dict[str, Any]:
        query = select(ConsensusSnapshot).where(ConsensusSnapshot.user_id == self.user_id)
        if subject_type:
            query = query.where(ConsensusSnapshot.subject_type == subject_type)
        if subject_code:
            query = query.where(ConsensusSnapshot.subject_code == subject_code)
        rows = (await self.session.scalars(query.order_by(ConsensusSnapshot.as_of.desc()))).all()
        return {"items": [{"id": str(row.id), "subject_type": row.subject_type, "subject_code": row.subject_code,
                           "as_of": row.as_of.isoformat(), "status": row.status, "claims": row.claims_json,
                           "summary": row.summary_json} for row in rows]}

    async def create_document(self, title: str, document_type: str) -> dict[str, Any]:
        item = ResearchDocument(user_id=self.user_id, title=title, document_type=document_type)
        self.session.add(item)
        await self.session.flush()
        return self._document_json(item)

    async def list_documents(self) -> dict[str, Any]:
        rows = (await self.session.scalars(select(ResearchDocument).where(
            ResearchDocument.user_id == self.user_id,
        ).order_by(ResearchDocument.updated_at.desc()))).all()
        return {"items": [self._document_json(row) for row in rows]}

    @staticmethod
    def _document_json(item: ResearchDocument) -> dict[str, Any]:
        return {"id": str(item.id), "title": item.title, "document_type": item.document_type,
                "current_version": item.current_version, "status": item.status,
                "updated_at": item.updated_at.isoformat()}

    async def generate_document(self, document_id: UUID, payload: dict[str, Any]) -> dict[str, Any]:
        document = await self.session.scalar(select(ResearchDocument).where(
            ResearchDocument.id == document_id, ResearchDocument.user_id == self.user_id,
        ))
        if document is None:
            raise ValueError("Research document not found")
        document.current_version += 1
        document.status = "ready"
        document.updated_at = datetime.utcnow()
        source_snapshot = payload.get("source_snapshot", {})
        if not source_snapshot.get("as_of") or not source_snapshot.get("citations"):
            raise ValueError("A dated source_snapshot with citations is required")
        fact_snapshot = {"structured": payload.get("structured", {}), "source_snapshot": source_snapshot}
        fact_snapshot_sha256 = hashlib.sha256(json.dumps(fact_snapshot, ensure_ascii=False, sort_keys=True,
            separators=(",", ":"), default=str).encode()).hexdigest()
        versions = []
        for locale in ("zh-CN", "en-US"):
            body = payload["bodies"].get(locale)
            if not body:
                raise ValueError(f"Missing {locale} report body")
            pdf = self._render_pdf(document.title, body, locale, payload.get("structured", {}), source_snapshot)
            if not pdf.startswith(b"%PDF"):
                raise ValueError(f"Generated {locale} artifact is not a valid PDF")
            digest = hashlib.sha256(pdf).hexdigest()
            relative = Path("agentos") / str(self.user_id) / str(document.id) / str(document.current_version) / f"{locale}.pdf"
            target = Path("./uploads") / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(pdf)
            version = ResearchDocumentVersion(
                document_id=document.id, version=document.current_version, locale=locale, template_version="agentos-v1",
                markdown_body=body, structured_json=payload.get("structured", {}), source_snapshot=source_snapshot,
                storage_path=str(relative), content_sha256=digest, fact_snapshot_sha256=fact_snapshot_sha256,
                size_bytes=len(pdf), status="ready",
            )
            self.session.add(version)
            await self.session.flush()
            versions.append(self._version_json(version))
        return {"document": self._document_json(document), "versions": versions,
                "fact_snapshot_sha256": fact_snapshot_sha256, "generation_mode": "background_ready"}

    async def list_document_versions(self, document_id: UUID) -> dict[str, Any]:
        document = await self.session.scalar(select(ResearchDocument).where(
            ResearchDocument.id == document_id, ResearchDocument.user_id == self.user_id,
        ))
        if document is None:
            raise ValueError("Research document not found")
        rows = (await self.session.scalars(select(ResearchDocumentVersion).where(
            ResearchDocumentVersion.document_id == document_id,
        ).order_by(ResearchDocumentVersion.version.desc(), ResearchDocumentVersion.locale))).all()
        return {"items": [self._version_json(row) for row in rows]}

    @staticmethod
    def _render_pdf(title: str, markdown: str, locale: str, structured: dict[str, Any], sources: dict[str, Any]) -> bytes:
        buffer = io.BytesIO()
        font = "Helvetica"
        if locale == "zh-CN":
            try:
                pdfmetrics.registerFont(UnicodeCIDFont("STSong-Light"))
                font = "STSong-Light"
            except KeyError:
                font = "Helvetica"
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle("AgentOSTitle", parent=styles["Title"], fontName=font, fontSize=21, leading=28,
                                     textColor=colors.HexColor("#111820"), alignment=TA_LEFT)
        body_style = ParagraphStyle("AgentOSBody", parent=styles["BodyText"], fontName=font, fontSize=10.5, leading=17,
                                    textColor=colors.HexColor("#26313A"))
        doc = SimpleDocTemplate(buffer, pagesize=A4, leftMargin=42, rightMargin=42, topMargin=42, bottomMargin=42,
                                title=title, author="KeelTrader AgentOS")
        story = [Paragraph(html.escape(title), title_style), Spacer(1, 12)]
        for paragraph in [part.strip() for part in markdown.split("\n\n") if part.strip()]:
            story.extend([Paragraph(html.escape(paragraph).replace("\n", "<br/>"), body_style), Spacer(1, 8)])
        if structured:
            data = [["Field", "Value"]] + [[str(key), str(value)] for key, value in structured.items()]
            table = Table(data, colWidths=[120, 360])
            table.setStyle(TableStyle([("FONTNAME", (0, 0), (-1, -1), font), ("FONTSIZE", (0, 0), (-1, -1), 8),
                                       ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E8EDF2")),
                                       ("GRID", (0, 0), (-1, -1), .25, colors.HexColor("#8A97A3")),
                                       ("VALIGN", (0, 0), (-1, -1), "TOP")]))
            story.extend([Spacer(1, 10), table])
        if sources:
            source_text = ("资料快照：" if locale == "zh-CN" else "Source snapshot: ") + str(sources)
            story.extend([Spacer(1, 14), Paragraph(html.escape(source_text), body_style)])
        doc.build(story)
        return buffer.getvalue()

    async def document_version(self, version_id: UUID) -> tuple[ResearchDocumentVersion, Path]:
        version = await self.session.scalar(select(ResearchDocumentVersion).join(
            ResearchDocument, ResearchDocument.id == ResearchDocumentVersion.document_id,
        ).where(ResearchDocumentVersion.id == version_id, ResearchDocument.user_id == self.user_id))
        if version is None or not version.storage_path:
            raise ValueError("Research document version not found")
        base = Path("./uploads").resolve()
        target = (base / version.storage_path).resolve()
        if base not in target.parents or not target.is_file():
            raise ValueError("Research document file not found")
        return version, target

    async def record_document_download(self, version_id: UUID) -> None:
        self.session.add(ResearchDocumentDownload(version_id=version_id, user_id=self.user_id))
        await self.session.flush()

    @staticmethod
    def _version_json(item: ResearchDocumentVersion) -> dict[str, Any]:
        return {"id": str(item.id), "document_id": str(item.document_id), "version": item.version,
                "locale": item.locale, "template_version": item.template_version, "status": item.status,
                "content_sha256": item.content_sha256, "size_bytes": item.size_bytes,
                "fact_snapshot_sha256": item.fact_snapshot_sha256,
                "download_url": f"/api/v1/agent/research-document-versions/{item.id}/download"}

    async def overview(self) -> dict[str, Any]:
        accounts = (await self.session.scalars(select(PortfolioAccount).where(
            PortfolioAccount.user_id == self.user_id, PortfolioAccount.status == "active",
        ).order_by(PortfolioAccount.updated_at.desc()))).all()
        valuation = await self.valuation(accounts[0].id, date.today()) if accounts else None
        counts = {}
        for key, model in (("hypotheses", ResearchHypothesis), ("decisions", DecisionRecord),
                           ("experiments", StrategyExperiment), ("documents", ResearchDocument)):
            counts[key] = int(await self.session.scalar(select(func.count()).select_from(model).where(model.user_id == self.user_id)) or 0)
        return {
            "as_of": date.today().isoformat(), "data_status": valuation["data_status"] if valuation else "partial",
            "portfolio": valuation or {"data_status": "unavailable", "reason": "no_portfolio_account"},
            "research": counts,
            "sections": {
                "allocation": {"data_status": "complete", "source": "/api/v1/agent/saa-policy-versions"},
                "market": {"data_status": "complete", "source": "/api/v1/markets/data-status"},
                "opportunities": {"data_status": "complete", "source": "/api/v1/markets/opportunities"},
                "agent": {"data_status": "complete", "source": "/api/v1/agent/runs"},
            },
        }
