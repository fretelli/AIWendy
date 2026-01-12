"""Advanced Machine Learning Analytics for Trading Pattern Recognition."""

import json
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

import joblib
import numpy as np
import pandas as pd
import sklearn
from core.logging import get_logger
from domain.journal.models import Journal, TradeResult
from sklearn.cluster import DBSCAN, KMeans
from sklearn.decomposition import PCA
from sklearn.ensemble import IsolationForest, RandomForestClassifier
from sklearn.metrics import classification_report, silhouette_score
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import MinMaxScaler, StandardScaler

logger = get_logger(__name__)


class PatternType(str, Enum):
    """Trading pattern types."""

    REVENGE_TRADING = "revenge_trading"
    OVERTRADING = "overtrading"
    FOMO = "fomo"
    FEAR_OF_LOSS = "fear_of_loss"
    WINNING_STREAK = "winning_streak"
    LOSING_STREAK = "losing_streak"
    CONSISTENT_PROFIT = "consistent_profit"
    ERRATIC_BEHAVIOR = "erratic_behavior"
    RISK_AVERSION = "risk_aversion"
    OVERLEVERAGING = "overleveraging"


@dataclass
class TradingPattern:
    """Identified trading pattern."""

    pattern_type: PatternType
    confidence: float  # 0-1
    description: str
    affected_trades: List[str]  # Trade IDs
    time_period: Tuple[datetime, datetime]
    metrics: Dict[str, Any]
    recommendations: List[str]


@dataclass
class PerformancePrediction:
    """Performance prediction result."""

    predicted_win_rate: float
    confidence_interval: Tuple[float, float]
    expected_profit: float
    risk_score: float  # 0-100
    prediction_horizon: int  # Days
    factors: Dict[str, float]  # Feature importance


class TradingPatternAnalyzer:
    """Analyze trading patterns using machine learning."""

    def __init__(self):
        self.models = {}
        self.scalers = {}
        self.feature_columns = []

    def extract_features(self, trades: List[Journal]) -> pd.DataFrame:
        """Extract features from trading journals."""

        features = []

        for trade in trades:
            # Calculate trade metrics
            duration = (
                trade.exit_time - trade.entry_time
            ).total_seconds() / 3600  # Hours
            pnl_percentage = (trade.pnl / (trade.entry_price * trade.quantity)) * 100

            # Time-based features
            hour = trade.entry_time.hour
            day_of_week = trade.entry_time.weekday()
            month = trade.entry_time.month

            # Emotional and rule features
            emotional_score = self._calculate_emotional_score(trade)
            rule_violations = len(trade.rule_violations) if trade.rule_violations else 0

            feature_dict = {
                "duration_hours": duration,
                "pnl": trade.pnl,
                "pnl_percentage": pnl_percentage,
                "quantity": trade.quantity,
                "entry_price": trade.entry_price,
                "exit_price": trade.exit_price,
                "side": 1 if trade.side == "long" else -1,
                "result": 1 if trade.result == TradeResult.WIN else 0,
                "hour": hour,
                "day_of_week": day_of_week,
                "month": month,
                "emotional_score": emotional_score,
                "rule_violations": rule_violations,
                "confidence_level": trade.confidence_level or 5,
                "is_revenge_trade": 1 if trade.is_revenge_trade else 0,
            }

            features.append(feature_dict)

        df = pd.DataFrame(features)
        self.feature_columns = df.columns.tolist()
        return df

    def identify_patterns(
        self, trades: List[Journal], lookback_days: int = 30
    ) -> List[TradingPattern]:
        """Identify trading patterns in recent trades."""

        if len(trades) < 10:
            return []

        # Extract features
        df = self.extract_features(trades)

        patterns = []

        # 1. Detect Revenge Trading
        revenge_pattern = self._detect_revenge_trading(trades, df)
        if revenge_pattern:
            patterns.append(revenge_pattern)

        # 2. Detect Overtrading
        overtrade_pattern = self._detect_overtrading(trades, df)
        if overtrade_pattern:
            patterns.append(overtrade_pattern)

        # 3. Detect FOMO
        fomo_pattern = self._detect_fomo(trades, df)
        if fomo_pattern:
            patterns.append(fomo_pattern)

        # 4. Detect Winning/Losing Streaks
        streak_patterns = self._detect_streaks(trades, df)
        patterns.extend(streak_patterns)

        # 5. Detect Risk Patterns
        risk_pattern = self._detect_risk_patterns(trades, df)
        if risk_pattern:
            patterns.append(risk_pattern)

        # 6. Use clustering for behavioral patterns
        behavioral_patterns = self._cluster_behavioral_patterns(trades, df)
        patterns.extend(behavioral_patterns)

        return patterns

    def _detect_revenge_trading(
        self, trades: List[Journal], df: pd.DataFrame
    ) -> Optional[TradingPattern]:
        """Detect revenge trading pattern."""

        revenge_trades = []
        for i, trade in enumerate(trades[1:], 1):
            prev_trade = trades[i - 1]

            # Check if previous trade was a loss
            if prev_trade.result == TradeResult.LOSS:
                # Check if current trade was entered quickly after loss
                time_diff = (
                    trade.entry_time - prev_trade.exit_time
                ).total_seconds() / 60

                if time_diff < 30:  # Within 30 minutes
                    # Check if position size increased
                    if trade.quantity > prev_trade.quantity * 1.2:
                        revenge_trades.append(str(trade.id))

        if len(revenge_trades) >= 2:
            return TradingPattern(
                pattern_type=PatternType.REVENGE_TRADING,
                confidence=min(0.9, len(revenge_trades) / 5),
                description="Detected pattern of revenge trading after losses",
                affected_trades=revenge_trades,
                time_period=(trades[0].entry_time, trades[-1].exit_time),
                metrics={
                    "occurrence_count": len(revenge_trades),
                    "avg_loss_after_revenge": df.loc[
                        df.index.isin(revenge_trades), "pnl"
                    ].mean(),
                },
                recommendations=[
                    "Implement a mandatory cool-down period after losses",
                    "Set maximum daily loss limits",
                    "Practice mindfulness techniques before entering new trades",
                ],
            )

        return None

    def _detect_overtrading(
        self, trades: List[Journal], df: pd.DataFrame
    ) -> Optional[TradingPattern]:
        """Detect overtrading pattern."""

        # Group trades by date
        df["date"] = pd.to_datetime([t.entry_time.date() for t in trades])
        daily_trades = df.groupby("date").size()

        # Calculate statistics
        avg_daily_trades = daily_trades.mean()
        std_daily_trades = daily_trades.std()

        # Find days with excessive trading
        overtrade_days = daily_trades[
            daily_trades > avg_daily_trades + 2 * std_daily_trades
        ]

        if len(overtrade_days) >= 3:
            affected_trades = []
            for date in overtrade_days.index:
                day_trades = [
                    str(t.id) for t in trades if t.entry_time.date() == date.date()
                ]
                affected_trades.extend(day_trades)

            return TradingPattern(
                pattern_type=PatternType.OVERTRADING,
                confidence=0.8,
                description=f"Excessive trading detected: avg {avg_daily_trades:.1f} trades/day, peaks at {daily_trades.max()}",
                affected_trades=affected_trades,
                time_period=(trades[0].entry_time, trades[-1].exit_time),
                metrics={
                    "avg_daily_trades": float(avg_daily_trades),
                    "max_daily_trades": int(daily_trades.max()),
                    "overtrade_days": len(overtrade_days),
                },
                recommendations=[
                    "Set a maximum number of trades per day",
                    "Focus on quality over quantity",
                    "Implement trade planning the night before",
                ],
            )

        return None

    def _detect_fomo(
        self, trades: List[Journal], df: pd.DataFrame
    ) -> Optional[TradingPattern]:
        """Detect FOMO (Fear of Missing Out) pattern."""

        fomo_trades = []

        for i, trade in enumerate(trades):
            # FOMO indicators:
            # 1. High emotional score
            # 2. Entering at market extremes
            # 3. No clear setup mentioned
            # 4. Quick entry after market move

            emotional_score = self._calculate_emotional_score(trade)

            if emotional_score > 7:
                # Check if entered at highs (for long) or lows (for short)
                if trade.side == "long" and trade.entry_price > df[
                    "entry_price"
                ].quantile(0.9):
                    fomo_trades.append(str(trade.id))
                elif trade.side == "short" and trade.entry_price < df[
                    "entry_price"
                ].quantile(0.1):
                    fomo_trades.append(str(trade.id))

        if len(fomo_trades) >= 3:
            return TradingPattern(
                pattern_type=PatternType.FOMO,
                confidence=0.75,
                description="Pattern of entering trades due to fear of missing out",
                affected_trades=fomo_trades,
                time_period=(trades[0].entry_time, trades[-1].exit_time),
                metrics={
                    "fomo_trade_count": len(fomo_trades),
                    "avg_loss_fomo_trades": df.loc[
                        df.index.isin(fomo_trades), "pnl"
                    ].mean(),
                },
                recommendations=[
                    "Wait for proper setups and confirmations",
                    "Create a pre-trade checklist",
                    "Practice patience and discipline",
                ],
            )

        return None

    def _detect_streaks(
        self, trades: List[Journal], df: pd.DataFrame
    ) -> List[TradingPattern]:
        """Detect winning and losing streaks."""

        patterns = []
        current_streak = []
        streak_type = None

        for trade in trades:
            if not current_streak:
                current_streak.append(trade)
                streak_type = trade.result
            elif trade.result == streak_type:
                current_streak.append(trade)
            else:
                # Streak ended
                if len(current_streak) >= 5:
                    pattern_type = (
                        PatternType.WINNING_STREAK
                        if streak_type == TradeResult.WIN
                        else PatternType.LOSING_STREAK
                    )

                    patterns.append(
                        TradingPattern(
                            pattern_type=pattern_type,
                            confidence=0.85,
                            description=f"{len(current_streak)}-trade {streak_type.value} streak detected",
                            affected_trades=[str(t.id) for t in current_streak],
                            time_period=(
                                current_streak[0].entry_time,
                                current_streak[-1].exit_time,
                            ),
                            metrics={
                                "streak_length": len(current_streak),
                                "total_pnl": sum(t.pnl for t in current_streak),
                            },
                            recommendations=self._get_streak_recommendations(
                                pattern_type
                            ),
                        )
                    )

                current_streak = [trade]
                streak_type = trade.result

        return patterns

    def _detect_risk_patterns(
        self, trades: List[Journal], df: pd.DataFrame
    ) -> Optional[TradingPattern]:
        """Detect risk management patterns."""

        # Calculate risk metrics
        position_sizes = df["quantity"].values
        avg_position = position_sizes.mean()
        std_position = position_sizes.std()

        # Find overleveraged trades
        overleveraged = df[df["quantity"] > avg_position + 2 * std_position]

        if len(overleveraged) >= 3:
            return TradingPattern(
                pattern_type=PatternType.OVERLEVERAGING,
                confidence=0.8,
                description="Pattern of taking excessive position sizes",
                affected_trades=[str(trades[i].id) for i in overleveraged.index],
                time_period=(trades[0].entry_time, trades[-1].exit_time),
                metrics={
                    "avg_position": float(avg_position),
                    "max_position": float(position_sizes.max()),
                    "overleveraged_count": len(overleveraged),
                },
                recommendations=[
                    "Implement fixed position sizing rules",
                    "Use Kelly Criterion for optimal sizing",
                    "Never risk more than 2% per trade",
                ],
            )

        return None

    def _cluster_behavioral_patterns(
        self, trades: List[Journal], df: pd.DataFrame
    ) -> List[TradingPattern]:
        """Use clustering to identify behavioral patterns."""

        if len(df) < 20:
            return []

        patterns = []

        try:
            # Prepare features for clustering
            features = df[
                ["emotional_score", "rule_violations", "confidence_level"]
            ].values

            # Scale features
            scaler = StandardScaler()
            scaled_features = scaler.fit_transform(features)

            # Apply DBSCAN clustering
            dbscan = DBSCAN(eps=0.5, min_samples=3)
            clusters = dbscan.fit_predict(scaled_features)

            # Analyze each cluster
            for cluster_id in set(clusters):
                if cluster_id == -1:  # Noise
                    continue

                cluster_indices = np.where(clusters == cluster_id)[0]
                cluster_trades = [trades[i] for i in cluster_indices]

                if len(cluster_trades) >= 5:
                    # Determine pattern type based on cluster characteristics
                    cluster_df = df.iloc[cluster_indices]

                    if cluster_df["emotional_score"].mean() > 7:
                        pattern_type = PatternType.ERRATIC_BEHAVIOR
                        description = "Cluster of emotionally driven trades"
                    elif cluster_df["confidence_level"].mean() < 3:
                        pattern_type = PatternType.FEAR_OF_LOSS
                        description = "Cluster of low-confidence trades"
                    else:
                        continue

                    patterns.append(
                        TradingPattern(
                            pattern_type=pattern_type,
                            confidence=0.7,
                            description=description,
                            affected_trades=[str(t.id) for t in cluster_trades],
                            time_period=(
                                cluster_trades[0].entry_time,
                                cluster_trades[-1].exit_time,
                            ),
                            metrics={
                                "cluster_size": len(cluster_trades),
                                "avg_pnl": cluster_df["pnl"].mean(),
                                "win_rate": cluster_df["result"].mean(),
                            },
                            recommendations=self._get_behavioral_recommendations(
                                pattern_type
                            ),
                        )
                    )

        except Exception as e:
            logger.error(f"Clustering failed: {e}")

        return patterns

    def predict_performance(
        self, trades: List[Journal], horizon_days: int = 30
    ) -> Optional[PerformancePrediction]:
        """Predict future trading performance using ML."""

        if len(trades) < 50:
            return None

        try:
            # Extract features
            df = self.extract_features(trades)

            # Prepare training data
            X = df.drop(["pnl", "result"], axis=1)
            y = df["result"]  # Win/Loss

            # Split data
            X_train, X_test, y_train, y_test = train_test_split(
                X, y, test_size=0.2, random_state=42
            )

            # Scale features
            scaler = StandardScaler()
            X_train_scaled = scaler.fit_transform(X_train)
            X_test_scaled = scaler.transform(X_test)

            # Train Random Forest
            rf = RandomForestClassifier(n_estimators=100, random_state=42)
            rf.fit(X_train_scaled, y_train)

            # Make predictions
            y_pred = rf.predict(X_test_scaled)
            y_pred_proba = rf.predict_proba(X_test_scaled)

            # Calculate metrics
            predicted_win_rate = y_pred.mean()
            confidence = y_pred_proba.max(axis=1).mean()

            # Feature importance
            feature_importance = dict(zip(X.columns, rf.feature_importances_))
            top_features = dict(
                sorted(feature_importance.items(), key=lambda x: x[1], reverse=True)[:5]
            )

            # Calculate expected profit
            recent_avg_win = df[df["result"] == 1]["pnl"].mean()
            recent_avg_loss = abs(df[df["result"] == 0]["pnl"].mean())
            expected_profit = (predicted_win_rate * recent_avg_win) - (
                (1 - predicted_win_rate) * recent_avg_loss
            )

            # Risk score (0-100)
            risk_score = self._calculate_risk_score(df, predicted_win_rate)

            return PerformancePrediction(
                predicted_win_rate=float(predicted_win_rate),
                confidence_interval=(
                    float(predicted_win_rate - (1 - confidence)),
                    float(predicted_win_rate + (1 - confidence)),
                ),
                expected_profit=float(expected_profit),
                risk_score=float(risk_score),
                prediction_horizon=horizon_days,
                factors=top_features,
            )

        except Exception as e:
            logger.error(f"Performance prediction failed: {e}")
            return None

    def detect_anomalies(self, trades: List[Journal]) -> List[Dict[str, Any]]:
        """Detect anomalous trades using Isolation Forest."""

        if len(trades) < 20:
            return []

        try:
            # Extract features
            df = self.extract_features(trades)
            features = df.select_dtypes(include=[np.number]).values

            # Scale features
            scaler = StandardScaler()
            scaled_features = scaler.fit_transform(features)

            # Train Isolation Forest
            iso_forest = IsolationForest(contamination=0.1, random_state=42)
            predictions = iso_forest.fit_predict(scaled_features)

            # Find anomalies
            anomalies = []
            for i, pred in enumerate(predictions):
                if pred == -1:  # Anomaly
                    trade = trades[i]
                    anomalies.append(
                        {
                            "trade_id": str(trade.id),
                            "entry_time": trade.entry_time.isoformat(),
                            "symbol": trade.symbol,
                            "pnl": trade.pnl,
                            "anomaly_score": float(
                                iso_forest.score_samples([scaled_features[i]])[0]
                            ),
                            "reason": self._explain_anomaly(df.iloc[i], df),
                        }
                    )

            return anomalies

        except Exception as e:
            logger.error(f"Anomaly detection failed: {e}")
            return []

    def _calculate_emotional_score(self, trade: Journal) -> float:
        """Calculate emotional score from trade data."""

        score = 5.0  # Neutral

        # Check emotional state
        if trade.emotional_state:
            emotional_map = {
                "fearful": 8,
                "anxious": 7,
                "greedy": 8,
                "confident": 3,
                "calm": 2,
                "frustrated": 9,
            }
            score = emotional_map.get(trade.emotional_state.lower(), 5)

        # Adjust based on rule violations
        if trade.rule_violations:
            score += len(trade.rule_violations) * 0.5

        # Adjust based on revenge trade flag
        if trade.is_revenge_trade:
            score += 2

        return min(10, score)

    def _get_streak_recommendations(self, pattern_type: PatternType) -> List[str]:
        """Get recommendations for streak patterns."""

        if pattern_type == PatternType.WINNING_STREAK:
            return [
                "Stay disciplined and don't increase position sizes",
                "Review and reinforce successful strategies",
                "Prepare for eventual mean reversion",
                "Take some profits off the table",
            ]
        else:  # Losing streak
            return [
                "Consider reducing position sizes",
                "Take a break to reset mentally",
                "Review and identify what's not working",
                "Focus on process over outcomes",
                "Consider paper trading until confidence returns",
            ]

    def _get_behavioral_recommendations(self, pattern_type: PatternType) -> List[str]:
        """Get recommendations for behavioral patterns."""

        recommendations_map = {
            PatternType.ERRATIC_BEHAVIOR: [
                "Implement strict trading rules",
                "Practice emotional regulation techniques",
                "Keep a detailed trading journal",
                "Consider automated trading systems",
            ],
            PatternType.FEAR_OF_LOSS: [
                "Work on building confidence gradually",
                "Start with smaller position sizes",
                "Focus on high-probability setups",
                "Practice with demo account first",
            ],
            PatternType.RISK_AVERSION: [
                "Gradually increase position sizes",
                "Focus on risk-reward ratios",
                "Set realistic profit targets",
                "Understand that losses are part of trading",
            ],
        }

        return recommendations_map.get(pattern_type, ["Continue monitoring patterns"])

    def _calculate_risk_score(
        self, df: pd.DataFrame, predicted_win_rate: float
    ) -> float:
        """Calculate risk score (0-100)."""

        score = 50  # Start neutral

        # Factor 1: Win rate
        if predicted_win_rate < 0.4:
            score += 20
        elif predicted_win_rate > 0.6:
            score -= 10

        # Factor 2: Position size variance
        position_variance = df["quantity"].std() / df["quantity"].mean()
        if position_variance > 0.5:
            score += 15

        # Factor 3: Rule violations
        avg_violations = df["rule_violations"].mean()
        score += min(20, avg_violations * 5)

        # Factor 4: Emotional scores
        avg_emotional = df["emotional_score"].mean()
        if avg_emotional > 6:
            score += 10

        # Factor 5: Recent performance
        recent_trades = df.tail(10)
        recent_win_rate = recent_trades["result"].mean()
        if recent_win_rate < 0.3:
            score += 15

        return min(100, max(0, score))

    def _explain_anomaly(self, trade_row: pd.Series, df: pd.DataFrame) -> str:
        """Explain why a trade is anomalous."""

        reasons = []

        # Check each feature
        for col in trade_row.index:
            if col in ["pnl", "quantity", "duration_hours"]:
                value = trade_row[col]
                mean = df[col].mean()
                std = df[col].std()

                if abs(value - mean) > 2 * std:
                    if value > mean:
                        reasons.append(
                            f"Unusually high {col}: {value:.2f} (avg: {mean:.2f})"
                        )
                    else:
                        reasons.append(
                            f"Unusually low {col}: {value:.2f} (avg: {mean:.2f})"
                        )

        return (
            "; ".join(reasons)
            if reasons
            else "Multiple unusual characteristics detected"
        )
