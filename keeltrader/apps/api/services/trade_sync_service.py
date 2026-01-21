"""Trade sync service for importing exchange trades and triggering pattern checks."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Iterable, List, Optional

import ccxt
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from config import get_settings
from core.encryption import get_encryption_service
from core.logging import get_logger
from domain.analysis.models import BehaviorPattern, PatternType as AnalysisPatternType
from domain.analytics.ml_analytics import MLAnalytics, TradingPattern, PatternType as MlPatternType
from domain.exchange.models import ExchangeConnection, ExchangeTrade
from domain.journal.models import Journal, TradeDirection, TradeResult
from tasks.notification_tasks import send_pattern_alert_task

logger = get_logger(__name__)


@dataclass
class SyncResult:
    connection_id: str
    exchange_type: str
    trades_fetched: int
    trades_inserted: int
    journals_created: int
    patterns_detected: int
    warnings: List[str]


class TradeSyncService:
    """Sync user exchange trades into raw storage and journals."""

    def __init__(self, db: Session) -> None:
        self.db = db
        self.settings = get_settings()
        self.encryption = get_encryption_service()
        self.ml = MLAnalytics()

    def sync_all_connections(self) -> Dict[str, Any]:
        """Sync trades for all active exchange connections."""
        connections = (
            self.db.query(ExchangeConnection)
            .filter(ExchangeConnection.is_active == True)
            .all()
        )

        results: List[SyncResult] = []
        for connection in connections:
            try:
                result = self.sync_connection(connection)
                results.append(result)
            except Exception as exc:
                logger.error(
                    "trade_sync_failed",
                    connection_id=str(connection.id),
                    error=str(exc),
                )
                results.append(
                    SyncResult(
                        connection_id=str(connection.id),
                        exchange_type=connection.exchange_type.value,
                        trades_fetched=0,
                        trades_inserted=0,
                        journals_created=0,
                        patterns_detected=0,
                        warnings=[str(exc)],
                    )
                )

        return {
            "status": "success",
            "connections": [result.__dict__ for result in results],
            "timestamp": datetime.utcnow().isoformat(),
        }

    def sync_connection(self, connection: ExchangeConnection) -> SyncResult:
        """Sync trades for a single exchange connection."""
        exchange = self._build_exchange(connection)
        try:
            symbols = connection.sync_symbols or []
            trades = self._fetch_trades(exchange, symbols, connection.last_trade_sync_at)

            trade_rows = [self._build_trade_row(connection, trade) for trade in trades]
            inserted = self._insert_trades(trade_rows)
            journals_created = 0

            if self.settings.trade_sync_import_to_journal and inserted:
                journals_created = self._import_trades_to_journals(connection, inserted)

            self._update_last_sync(connection, trades)
            patterns_detected = self._detect_and_store_patterns(connection.user_id)

            return SyncResult(
                connection_id=str(connection.id),
                exchange_type=connection.exchange_type.value,
                trades_fetched=len(trades),
                trades_inserted=len(inserted),
                journals_created=journals_created,
                patterns_detected=patterns_detected,
                warnings=[],
            )
        finally:
            if hasattr(exchange, "close"):
                try:
                    exchange.close()
                except Exception:
                    pass

    def _build_exchange(self, connection: ExchangeConnection) -> ccxt.Exchange:
        creds = self._decrypt_credentials(connection)
        exchange_class = getattr(ccxt, connection.exchange_type.value)
        exchange_config: Dict[str, Any] = {
            "apiKey": creds["api_key"],
            "secret": creds["api_secret"],
            "enableRateLimit": True,
        }

        if creds.get("passphrase"):
            exchange_config["password"] = creds["passphrase"]

        if connection.is_testnet:
            exchange_config["options"] = {"defaultType": "future"}
            if hasattr(exchange_class, "set_sandbox_mode"):
                exchange_config["sandbox"] = True

        return exchange_class(exchange_config)

    def _decrypt_credentials(self, connection: ExchangeConnection) -> Dict[str, Any]:
        return {
            "api_key": self.encryption.decrypt(connection.api_key_encrypted),
            "api_secret": self.encryption.decrypt(connection.api_secret_encrypted),
            "passphrase": (
                self.encryption.decrypt(connection.passphrase_encrypted)
                if connection.passphrase_encrypted
                else None
            ),
        }

    def _fetch_trades(
        self,
        exchange: ccxt.Exchange,
        symbols: List[str],
        last_sync_at: Optional[datetime],
    ) -> List[Dict[str, Any]]:
        since = last_sync_at or (datetime.utcnow() - timedelta(days=7))
        since_ms = int(since.timestamp() * 1000)

        trades: List[Dict[str, Any]] = []
        if symbols:
            for symbol in symbols:
                trades.extend(
                    exchange.fetch_my_trades(
                        symbol=symbol,
                        since=since_ms,
                        limit=self.settings.trade_sync_default_limit,
                    )
                )
            return trades

        try:
            trades = exchange.fetch_my_trades(
                since=since_ms,
                limit=self.settings.trade_sync_default_limit,
            )
        except Exception as exc:
            logger.warning("trade_sync_symbols_required", error=str(exc))
        return trades

    def _build_trade_row(
        self,
        connection: ExchangeConnection,
        trade: Dict[str, Any],
    ) -> Dict[str, Any]:
        trade_timestamp = self._parse_trade_time(trade)
        fee = trade.get("fee") or {}
        symbol = trade.get("symbol") or "unknown"
        trade_id = trade.get("id") or trade.get("order") or trade.get("tradeId")
        if not trade_id:
            trade_id = f"{symbol}-{int(trade_timestamp.timestamp())}" if trade_timestamp else f"{symbol}-unknown"
        return {
            "user_id": connection.user_id,
            "exchange_connection_id": connection.id,
            "exchange_trade_id": str(trade_id),
            "symbol": symbol,
            "side": trade.get("side"),
            "price": trade.get("price"),
            "amount": trade.get("amount"),
            "cost": trade.get("cost"),
            "fee_cost": fee.get("cost"),
            "fee_currency": fee.get("currency"),
            "fee_rate": fee.get("rate"),
            "trade_timestamp": trade_timestamp,
            "raw": trade,
        }

    def _parse_trade_time(self, trade: Dict[str, Any]) -> Optional[datetime]:
        ts = trade.get("timestamp")
        if ts:
            return datetime.utcfromtimestamp(ts / 1000)

        iso = trade.get("datetime")
        if iso:
            try:
                parsed = datetime.fromisoformat(iso.replace("Z", "+00:00"))
                return parsed.astimezone(timezone.utc).replace(tzinfo=None)
            except ValueError:
                return None
        return None

    def _insert_trades(self, trade_rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        trade_rows = [row for row in trade_rows if row.get("exchange_trade_id")]
        if not trade_rows:
            return []

        dialect = self.db.bind.dialect.name if self.db.bind else ""
        if dialect == "postgresql":
            stmt = pg_insert(ExchangeTrade).values(trade_rows)
            stmt = stmt.on_conflict_do_nothing(
                index_elements=[
                    ExchangeTrade.exchange_connection_id,
                    ExchangeTrade.exchange_trade_id,
                ]
            ).returning(
                ExchangeTrade.id,
                ExchangeTrade.exchange_trade_id,
                ExchangeTrade.symbol,
                ExchangeTrade.side,
                ExchangeTrade.price,
                ExchangeTrade.amount,
                ExchangeTrade.trade_timestamp,
            )
            result = self.db.execute(stmt)
            rows = [dict(row._mapping) for row in result.fetchall()]
            self.db.commit()
            return rows

        inserted: List[Dict[str, Any]] = []
        for row in trade_rows:
            exists = (
                self.db.query(ExchangeTrade)
                .filter(
                    ExchangeTrade.exchange_connection_id == row["exchange_connection_id"],
                    ExchangeTrade.exchange_trade_id == row["exchange_trade_id"],
                )
                .first()
            )
            if exists:
                continue
            trade = ExchangeTrade(**row)
            self.db.add(trade)
            self.db.flush()
            inserted.append(
                {
                    "id": trade.id,
                    "exchange_trade_id": trade.exchange_trade_id,
                    "symbol": trade.symbol,
                    "side": trade.side,
                    "price": trade.price,
                    "amount": trade.amount,
                    "trade_timestamp": trade.trade_timestamp,
                }
            )

        self.db.commit()
        return inserted

    def _import_trades_to_journals(
        self,
        connection: ExchangeConnection,
        inserted: List[Dict[str, Any]],
    ) -> int:
        journals_created = 0
        for row in inserted:
            direction = self._map_trade_direction(row.get("side"))
            if not direction:
                continue

            trade_time = row.get("trade_timestamp") or datetime.utcnow()
            journal = Journal(
                user_id=connection.user_id,
                symbol=row.get("symbol") or "",
                market="crypto",
                direction=direction,
                trade_date=trade_time,
                entry_time=trade_time,
                entry_price=row.get("price"),
                position_size=row.get("amount"),
                result=TradeResult.OPEN,
                notes=(
                    f"Imported from {connection.exchange_type.value} trade "
                    f"{row.get('exchange_trade_id')}"
                ),
                tags=["imported"],
            )
            self.db.add(journal)
            self.db.flush()

            self.db.query(ExchangeTrade).filter(
                ExchangeTrade.id == row["id"]
            ).update(
                {
                    "journal_id": journal.id,
                    "is_imported": True,
                    "imported_at": datetime.utcnow(),
                }
            )

            journals_created += 1

        self.db.commit()
        return journals_created

    def _map_trade_direction(self, side: Optional[str]) -> Optional[TradeDirection]:
        if not side:
            return None
        if side.lower() == "buy":
            return TradeDirection.LONG
        if side.lower() == "sell":
            return TradeDirection.SHORT
        return None

    def _update_last_sync(
        self,
        connection: ExchangeConnection,
        trades: List[Dict[str, Any]],
    ) -> None:
        if not trades:
            return

        timestamps = [
            self._parse_trade_time(t) for t in trades if t is not None
        ]
        timestamps = [ts for ts in timestamps if ts]
        latest = max(timestamps) if timestamps else None
        if latest:
            connection.last_trade_sync_at = latest
        connection.last_sync_at = datetime.utcnow()
        self.db.add(connection)
        self.db.commit()

    def _detect_and_store_patterns(self, user_id: UUID) -> int:
        recent_journals = (
            self.db.query(Journal)
            .filter(Journal.user_id == user_id, Journal.deleted_at.is_(None))
            .order_by(Journal.trade_date.desc())
            .limit(50)
            .all()
        )

        patterns = self.ml.detect_patterns(recent_journals)
        stored = 0
        for pattern in patterns:
            mapped = self._map_pattern_type(pattern.pattern_type)
            if not mapped or pattern.confidence < 0.7:
                continue

            if self._has_recent_pattern(user_id, mapped):
                continue

            behavior = BehaviorPattern(
                user_id=user_id,
                pattern_type=mapped,
                confidence_score=pattern.confidence,
                severity=max(1, int(pattern.confidence * 5)),
                context=pattern.metrics,
                evidence=pattern.recommendations,
                related_trades=pattern.affected_trades,
                intervention_suggested=pattern.description,
            )
            self.db.add(behavior)
            stored += 1

            send_pattern_alert_task.delay(
                user_id=str(user_id),
                pattern_type=mapped.value,
                description=pattern.description,
                confidence=pattern.confidence,
                recommendations=pattern.recommendations,
            )

        self.db.commit()
        return stored

    def _has_recent_pattern(self, user_id: UUID, pattern_type: AnalysisPatternType) -> bool:
        since = datetime.utcnow() - timedelta(hours=6)
        existing = (
            self.db.query(BehaviorPattern)
            .filter(
                BehaviorPattern.user_id == user_id,
                BehaviorPattern.pattern_type == pattern_type,
                BehaviorPattern.detected_at >= since,
                BehaviorPattern.resolved_at.is_(None),
            )
            .first()
        )
        return existing is not None

    def _map_pattern_type(
        self, pattern_type: MlPatternType
    ) -> Optional[AnalysisPatternType]:
        mapping = {
            MlPatternType.REVENGE_TRADING: AnalysisPatternType.REVENGE_TRADING,
            MlPatternType.OVERTRADING: AnalysisPatternType.OVERTRADING,
            MlPatternType.FOMO: AnalysisPatternType.FOMO,
            MlPatternType.FEAR_OF_LOSS: AnalysisPatternType.FEAR_OF_LOSS,
            MlPatternType.ERRATIC_BEHAVIOR: AnalysisPatternType.EMOTIONAL_TRADING,
            MlPatternType.OVERLEVERAGING: AnalysisPatternType.DISCIPLINE_BREACH,
            MlPatternType.RISK_AVERSION: AnalysisPatternType.FEAR_OF_LOSS,
        }
        return mapping.get(pattern_type)
