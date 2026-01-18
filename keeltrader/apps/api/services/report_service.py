"""Report generation service."""

import asyncio
import json
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID

from sqlalchemy import and_
from sqlalchemy.orm import Session

from core.database import get_db
from core.i18n import DEFAULT_LOCALE, Locale, normalize_locale, t
from domain.coach.models import ChatSession
from domain.journal.models import Journal
from domain.project.models import Project
from domain.report.models import (
    Report,
    ReportSchedule,
    ReportStatus,
    ReportTemplate,
    ReportType,
)
from domain.user.models import User
from services.llm_router import LLMRouter


class ReportService:
    """Service for generating and managing periodic reports."""

    def __init__(self, db: Session):
        self.db = db

    def _get_project_name(
        self, user_id: UUID, project_id: Optional[UUID]
    ) -> Optional[str]:
        if project_id is None:
            return None

        project = (
            self.db.query(Project)
            .filter(and_(Project.id == project_id, Project.user_id == user_id))
            .first()
        )
        if project is None:
            raise ValueError("Project not found")
        return project.name

    def _resolve_report_locale(
        self, user_id: UUID, override: Optional[str] = None
    ) -> Locale:
        if override:
            return normalize_locale(override)

        schedule = (
            self.db.query(ReportSchedule)
            .filter(ReportSchedule.user_id == user_id)
            .first()
        )
        if schedule and schedule.language:
            return normalize_locale(schedule.language)

        user = self.db.query(User).filter(User.id == user_id).first()
        if user and getattr(user, "language", None):
            return normalize_locale(getattr(user, "language"))

        return DEFAULT_LOCALE

    def _format_date(self, locale: Locale, value: date) -> str:
        if locale == "zh":
            return value.strftime("%Y年%m月%d日")
        return value.strftime("%Y-%m-%d")

    def _format_month(self, locale: Locale, year: int, month: int) -> str:
        if locale == "zh":
            return f"{year}年{month}月"
        return f"{year}-{month:02d}"

    def _report_type_label(self, locale: Locale, report_type: ReportType) -> str:
        return t(f"reports.type.{report_type.value}", locale)

    # Report Generation
    def generate_daily_report(
        self,
        user_id: UUID,
        report_date: Optional[date] = None,
        locale: Optional[str] = None,
        *,
        project_id: Optional[UUID] = None,
    ) -> Report:
        """Generate daily report for a user."""
        resolved_locale = self._resolve_report_locale(user_id, locale)
        if not report_date:
            report_date = date.today() - timedelta(days=1)  # Yesterday's report

        period_start = report_date
        period_end = report_date

        project_name = (
            self._get_project_name(user_id, project_id) if project_id else None
        )
        title = t(
            "reports.title.daily",
            resolved_locale,
            date=self._format_date(resolved_locale, report_date),
        )
        if project_name:
            title = t(
                "reports.title.with_project",
                resolved_locale,
                title=title,
                project=project_name,
            )

        return self._generate_report(
            user_id=user_id,
            report_type=ReportType.DAILY,
            period_start=period_start,
            period_end=period_end,
            title=title,
            project_id=project_id,
            locale=resolved_locale,
        )

    def generate_weekly_report(
        self,
        user_id: UUID,
        week_start: Optional[date] = None,
        locale: Optional[str] = None,
        *,
        project_id: Optional[UUID] = None,
    ) -> Report:
        """Generate weekly report for a user."""
        resolved_locale = self._resolve_report_locale(user_id, locale)
        if not week_start:
            # Default to last week's Monday
            today = date.today()
            days_since_monday = today.weekday()
            last_monday = today - timedelta(days=days_since_monday + 7)
            week_start = last_monday

        period_start = week_start
        period_end = week_start + timedelta(days=6)

        project_name = (
            self._get_project_name(user_id, project_id) if project_id else None
        )
        title = t(
            "reports.title.weekly",
            resolved_locale,
            week=week_start.isocalendar()[1],
        )
        if project_name:
            title = t(
                "reports.title.with_project",
                resolved_locale,
                title=title,
                project=project_name,
            )

        return self._generate_report(
            user_id=user_id,
            report_type=ReportType.WEEKLY,
            period_start=period_start,
            period_end=period_end,
            title=title,
            project_id=project_id,
            locale=resolved_locale,
        )

    def generate_monthly_report(
        self,
        user_id: UUID,
        year: Optional[int] = None,
        month: Optional[int] = None,
        locale: Optional[str] = None,
        *,
        project_id: Optional[UUID] = None,
    ) -> Report:
        """Generate monthly report for a user."""
        resolved_locale = self._resolve_report_locale(user_id, locale)
        if not year or not month:
            # Default to last month
            today = date.today()
            if today.month == 1:
                year = today.year - 1
                month = 12
            else:
                year = today.year
                month = today.month - 1

        period_start = date(year, month, 1)
        # Get last day of month
        if month == 12:
            period_end = date(year, 12, 31)
        else:
            period_end = date(year, month + 1, 1) - timedelta(days=1)

        project_name = (
            self._get_project_name(user_id, project_id) if project_id else None
        )
        title = t(
            "reports.title.monthly",
            resolved_locale,
            year=year,
            month=month,
            month_label=self._format_month(resolved_locale, year, month),
        )
        if project_name:
            title = t(
                "reports.title.with_project",
                resolved_locale,
                title=title,
                project=project_name,
            )

        return self._generate_report(
            user_id=user_id,
            report_type=ReportType.MONTHLY,
            period_start=period_start,
            period_end=period_end,
            title=title,
            project_id=project_id,
            locale=resolved_locale,
        )

    def generate_quarterly_report(
        self,
        user_id: UUID,
        year: Optional[int] = None,
        quarter: Optional[int] = None,
        locale: Optional[str] = None,
        *,
        project_id: Optional[UUID] = None,
    ) -> Report:
        """Generate quarterly report for a user."""
        resolved_locale = self._resolve_report_locale(user_id, locale)
        if not year or not quarter:
            # Default to last quarter
            today = date.today()
            current_quarter = (today.month - 1) // 3 + 1
            if current_quarter == 1:
                year = today.year - 1
                quarter = 4
            else:
                year = today.year
                quarter = current_quarter - 1

        # Calculate quarter start and end dates
        start_month = (quarter - 1) * 3 + 1
        period_start = date(year, start_month, 1)

        # Get last day of quarter
        end_month = quarter * 3
        if end_month == 12:
            period_end = date(year, 12, 31)
        else:
            period_end = date(year, end_month + 1, 1) - timedelta(days=1)

        project_name = (
            self._get_project_name(user_id, project_id) if project_id else None
        )

        quarter_label = f"Q{quarter}"
        if resolved_locale == "zh":
            title = f"{year}年第{quarter}季度报告"
        else:
            title = f"{quarter_label} {year} Report"

        if project_name:
            title = t(
                "reports.title.with_project",
                resolved_locale,
                title=title,
                project=project_name,
            )

        return self._generate_report(
            user_id=user_id,
            report_type=ReportType.QUARTERLY,
            period_start=period_start,
            period_end=period_end,
            title=title,
            project_id=project_id,
            locale=resolved_locale,
        )

    def generate_yearly_report(
        self,
        user_id: UUID,
        year: Optional[int] = None,
        locale: Optional[str] = None,
        *,
        project_id: Optional[UUID] = None,
    ) -> Report:
        """Generate yearly report for a user."""
        resolved_locale = self._resolve_report_locale(user_id, locale)
        if not year:
            # Default to last year
            today = date.today()
            year = today.year - 1

        period_start = date(year, 1, 1)
        period_end = date(year, 12, 31)

        project_name = (
            self._get_project_name(user_id, project_id) if project_id else None
        )

        if resolved_locale == "zh":
            title = f"{year}年度报告"
        else:
            title = f"{year} Annual Report"

        if project_name:
            title = t(
                "reports.title.with_project",
                resolved_locale,
                title=title,
                project=project_name,
            )

        return self._generate_report(
            user_id=user_id,
            report_type=ReportType.YEARLY,
            period_start=period_start,
            period_end=period_end,
            title=title,
            project_id=project_id,
            locale=resolved_locale,
        )

    def _generate_report(
        self,
        user_id: UUID,
        report_type: ReportType,
        period_start: date,
        period_end: date,
        title: str,
        project_id: Optional[UUID] = None,
        *,
        locale: Locale = DEFAULT_LOCALE,
    ) -> Report:
        """Generate a report for the specified period."""
        start_time = datetime.now()

        # Create report record
        report = Report(
            user_id=user_id,
            project_id=project_id,
            report_type=report_type,
            title=title,
            subtitle=t(
                "reports.subtitle.period",
                locale,
                start=self._format_date(locale, period_start),
                end=self._format_date(locale, period_end),
            ),
            period_start=period_start,
            period_end=period_end,
            status=ReportStatus.GENERATING,
        )
        self.db.add(report)
        self.db.commit()

        try:
            # Fetch trading journals for the period
            journals = self._fetch_journals(
                user_id, period_start, period_end, project_id
            )

            # Calculate statistics
            stats = self._calculate_statistics(journals)
            report.total_trades = stats["total_trades"]
            report.winning_trades = stats["winning_trades"]
            report.losing_trades = stats["losing_trades"]
            report.win_rate = stats["win_rate"]
            report.total_pnl = stats["total_pnl"]
            report.avg_pnl = stats["avg_pnl"]
            report.max_profit = stats["max_profit"]
            report.max_loss = stats["max_loss"]

            # Calculate psychological metrics
            psych_metrics = self._calculate_psychological_metrics(journals, locale)
            report.avg_mood_before = psych_metrics["avg_mood_before"]
            report.avg_mood_after = psych_metrics["avg_mood_after"]
            report.mood_improvement = psych_metrics["mood_improvement"]

            # Analyze trading patterns
            patterns = self._analyze_patterns(journals, locale)
            report.top_mistakes = patterns["top_mistakes"]
            report.top_successes = patterns["top_successes"]
            report.improvements = patterns["improvements"]

            # Generate AI analysis and insights
            ai_insights = self._generate_ai_insights(
                user_id, journals, stats, psych_metrics, patterns, report_type, locale
            )
            report.ai_analysis = ai_insights["analysis"]
            report.ai_recommendations = ai_insights["recommendations"]
            report.key_insights = ai_insights["key_insights"]
            report.action_items = ai_insights["action_items"]

            # Get coach insights
            coach_insights = self._get_coach_insights(
                user_id, period_start, period_end, locale, project_id
            )
            report.coach_notes = coach_insights["notes"]
            report.primary_coach_id = coach_insights["primary_coach"]

            # Store structured content
            report.content = {
                "statistics": stats,
                "psychological": psych_metrics,
                "patterns": patterns,
                "journals_analyzed": len(journals),
                "locale": locale,
                "period": {
                    "start": period_start.isoformat(),
                    "end": period_end.isoformat(),
                },
            }

            # Generate summary
            report.summary = self._generate_summary(report, locale)

            # Update status
            report.status = ReportStatus.COMPLETED
            report.generation_time = (datetime.now() - start_time).total_seconds()

        except Exception as e:
            report.status = ReportStatus.FAILED
            report.error_message = str(e)

        self.db.commit()
        self.db.refresh(report)
        return report

    def _fetch_journals(
        self,
        user_id: UUID,
        start_date: date,
        end_date: date,
        project_id: Optional[UUID] = None,
    ) -> List[Journal]:
        """Fetch journals for the specified period."""
        start_dt = datetime.combine(start_date, datetime.min.time())
        end_dt = datetime.combine(end_date + timedelta(days=1), datetime.min.time())
        query = self.db.query(Journal).filter(
            and_(
                Journal.user_id == user_id,
                Journal.trade_date >= start_dt,
                Journal.trade_date < end_dt,
            )
        )
        if project_id is not None:
            query = query.filter(Journal.project_id == project_id)
        return query.order_by(Journal.trade_date).all()

    def _calculate_statistics(self, journals: List[Journal]) -> Dict[str, Any]:
        """Calculate trading statistics from journals."""
        if not journals:
            return {
                "total_trades": 0,
                "winning_trades": 0,
                "losing_trades": 0,
                "win_rate": 0.0,
                "total_pnl": 0.0,
                "avg_pnl": 0.0,
                "max_profit": 0.0,
                "max_loss": 0.0,
            }

        total_trades = len(journals)
        winning_trades = sum(
            1 for j in journals if j.pnl_amount is not None and j.pnl_amount > 0
        )
        losing_trades = sum(
            1 for j in journals if j.pnl_amount is not None and j.pnl_amount < 0
        )

        pnls = [j.pnl_amount for j in journals if j.pnl_amount is not None]
        total_pnl = sum(pnls) if pnls else 0.0
        avg_pnl = total_pnl / len(pnls) if pnls else 0.0
        max_profit = max(pnls) if pnls else 0.0
        max_loss = min(pnls) if pnls else 0.0

        win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0.0

        return {
            "total_trades": total_trades,
            "winning_trades": winning_trades,
            "losing_trades": losing_trades,
            "win_rate": round(win_rate, 2),
            "total_pnl": round(total_pnl, 2),
            "avg_pnl": round(avg_pnl, 2),
            "max_profit": round(max_profit, 2),
            "max_loss": round(max_loss, 2),
        }

    def _calculate_psychological_metrics(
        self, journals: List[Journal], locale: Locale
    ) -> Dict[str, Any]:
        """Calculate psychological metrics from journals."""
        if not journals:
            return {
                "avg_mood_before": None,
                "avg_mood_after": None,
                "mood_improvement": None,
                "emotional_patterns": [],
            }

        mood_befores = [
            j.emotion_before for j in journals if j.emotion_before is not None
        ]
        mood_afters = [j.emotion_after for j in journals if j.emotion_after is not None]

        avg_mood_before = (
            sum(mood_befores) / len(mood_befores) if mood_befores else None
        )
        avg_mood_after = sum(mood_afters) / len(mood_afters) if mood_afters else None

        mood_improvement = None
        if avg_mood_before is not None and avg_mood_after is not None:
            mood_improvement = avg_mood_after - avg_mood_before

        # Analyze emotional patterns
        emotional_patterns = []
        if mood_befores:
            from collections import Counter

            labels = {
                1: t("reports.mood.1", locale),
                2: t("reports.mood.2", locale),
                3: t("reports.mood.3", locale),
                4: t("reports.mood.4", locale),
                5: t("reports.mood.5", locale),
            }
            emotion_counts = Counter(labels.get(v, str(v)) for v in mood_befores)
            emotional_patterns = [
                {"emotion": emotion, "count": count}
                for emotion, count in emotion_counts.most_common(5)
            ]

        return {
            "avg_mood_before": round(avg_mood_before, 2) if avg_mood_before else None,
            "avg_mood_after": round(avg_mood_after, 2) if avg_mood_after else None,
            "mood_improvement": (
                round(mood_improvement, 2) if mood_improvement else None
            ),
            "emotional_patterns": emotional_patterns,
        }

    def _analyze_patterns(
        self, journals: List[Journal], locale: Locale
    ) -> Dict[str, Any]:
        """Analyze trading patterns from journals."""
        top_mistakes = []
        top_successes = []
        improvements = []

        if journals:
            # Analyze mistakes
            all_mistakes = []
            for j in journals:
                if j.rule_violations:
                    all_mistakes.extend([str(v) for v in j.rule_violations])

            if all_mistakes:
                from collections import Counter

                mistake_counts = Counter(all_mistakes)
                top_mistakes = [
                    {"mistake": mistake, "frequency": count}
                    for mistake, count in mistake_counts.most_common(5)
                ]

            # Analyze successful patterns
            winning_journals = [
                j for j in journals if j.pnl_amount is not None and j.pnl_amount > 0
            ]
            if winning_journals:
                # Extract patterns from winning trades
                success_patterns = []
                for j in winning_journals:
                    if j.lessons_learned:
                        lesson = j.lessons_learned.strip()
                        if lesson:
                            success_patterns.append(lesson)

                if success_patterns:
                    # Unique (keep order)
                    seen: set[str] = set()
                    unique_successes: list[str] = []
                    for item in success_patterns:
                        if item in seen:
                            continue
                        seen.add(item)
                        unique_successes.append(item)
                    top_successes = unique_successes[:5]  # Top 5 successful patterns

            # Generate improvement suggestions based on mistakes
            if top_mistakes:
                suggestions = {
                    "early_exit": t("reports.improvement.early_exit", locale),
                    "late_exit": t("reports.improvement.late_exit", locale),
                    "no_stop_loss": t("reports.improvement.no_stop_loss", locale),
                    "over_leverage": t("reports.improvement.over_leverage", locale),
                    "revenge_trade": t("reports.improvement.revenge_trade", locale),
                    "fomo": t("reports.improvement.fomo", locale),
                    "position_size": t("reports.improvement.position_size", locale),
                    "other": t("reports.improvement.other", locale),
                }
                improvements = []
                for m in top_mistakes[:3]:
                    key = m.get("mistake")
                    tip = suggestions.get(
                        str(key), t("reports.improvement.generic", locale, key=str(key))
                    )
                    improvements.append(
                        t(
                            "reports.improvement.with_frequency",
                            locale,
                            tip=tip,
                            count=m.get("frequency"),
                        )
                    )

        return {
            "top_mistakes": top_mistakes,
            "top_successes": top_successes,
            "improvements": improvements,
        }

    def _generate_ai_insights(
        self,
        user_id: UUID,
        journals: List[Journal],
        stats: Dict,
        psych_metrics: Dict,
        patterns: Dict,
        report_type: ReportType,
        locale: Locale,
    ) -> Dict[str, Any]:
        """Generate AI insights for the report."""
        if not journals:
            return {
                "analysis": t("reports.ai.no_trades", locale),
                "recommendations": [],
                "key_insights": [],
                "action_items": [],
            }

        # Prepare context for AI
        context = {
            "report_type": report_type.value,
            "statistics": stats,
            "psychological": psych_metrics,
            "patterns": patterns,
            "total_journals": len(journals),
        }

        report_type_label = self._report_type_label(locale, report_type)
        prompt = t(
            "reports.ai.prompt",
            locale,
            report_type=report_type_label,
            total_trades=stats.get("total_trades"),
            win_rate=stats.get("win_rate"),
            total_pnl=stats.get("total_pnl"),
            avg_pnl=stats.get("avg_pnl"),
            avg_mood_before=psych_metrics.get("avg_mood_before"),
            avg_mood_after=psych_metrics.get("avg_mood_after"),
            mood_improvement=psych_metrics.get("mood_improvement"),
        )

        try:
            user = self.db.query(User).filter(User.id == user_id).first()
            router = LLMRouter(user=user) if user else LLMRouter()
            response = self._run_llm_chat(router, prompt, locale)
            insights = self._parse_llm_json(response)

            return {
                "analysis": insights.get("analysis", ""),
                "recommendations": insights.get("recommendations", []),
                "key_insights": insights.get("key_insights", []),
                "action_items": insights.get("action_items", []),
            }
        except Exception as e:
            # Fallback to rule-based insights
            return self._generate_rule_based_insights(
                stats, psych_metrics, patterns, locale
            )

    def _run_llm_chat(self, router: LLMRouter, prompt: str, locale: Locale) -> str:
        """Run an LLM chat call from sync code (best-effort)."""
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(
                router.chat(
                    prompt,
                    system=t("reports.ai.system_prompt", locale),
                    model="gpt-4o-mini",
                    temperature=0.7,
                    max_tokens=1000,
                )
            )

        raise RuntimeError("LLM chat cannot run inside an active event loop")

    def _parse_llm_json(self, text: str) -> Dict[str, Any]:
        """Parse JSON returned by an LLM (supports fenced code blocks)."""
        payload = text.strip()
        if payload.startswith("```"):
            lines = payload.splitlines()
            if len(lines) >= 3:
                payload = "\n".join(lines[1:-1]).strip()

        if payload.startswith("{") and payload.endswith("}"):
            return json.loads(payload)

        start = payload.find("{")
        end = payload.rfind("}")
        if start != -1 and end != -1 and end > start:
            return json.loads(payload[start : end + 1])

        raise ValueError("No JSON object found in LLM response")

    def _generate_rule_based_insights(
        self, stats: Dict, psych_metrics: Dict, patterns: Dict, locale: Locale
    ) -> Dict[str, Any]:
        """Generate rule-based insights as fallback."""
        analysis = t(
            "reports.fallback.analysis_header",
            locale,
            total_trades=stats.get("total_trades"),
            win_rate=stats.get("win_rate"),
        )

        if stats["total_pnl"] > 0:
            analysis += t(
                "reports.fallback.analysis_profit",
                locale,
                total_pnl=stats.get("total_pnl"),
            )
        else:
            analysis += t(
                "reports.fallback.analysis_loss",
                locale,
                total_loss=abs(stats.get("total_pnl") or 0),
            )

        recommendations = []
        if stats["win_rate"] < 50:
            recommendations.append(t("reports.fallback.rec.low_win_rate", locale))

        if (
            psych_metrics.get("mood_improvement")
            and psych_metrics.get("mood_improvement") < 0
        ):
            recommendations.append(t("reports.fallback.rec.mood_negative", locale))

        if patterns.get("top_mistakes"):
            recommendations.append(
                t(
                    "reports.fallback.rec.top_mistake",
                    locale,
                    mistake=patterns["top_mistakes"][0].get("mistake"),
                )
            )

        key_insights = []
        if stats.get("win_rate") and stats.get("win_rate") > 60:
            key_insights.append(t("reports.fallback.insight.system_good", locale))
        if (
            stats.get("max_profit") is not None
            and stats.get("max_loss") is not None
            and stats["max_profit"] != 0
            and stats["max_loss"] < stats["max_profit"] * 0.5
        ):
            key_insights.append(t("reports.fallback.insight.risk_good", locale))
        if psych_metrics.get("avg_mood_after") and psych_metrics.get("avg_mood_before"):
            if psych_metrics["avg_mood_after"] > psych_metrics["avg_mood_before"]:
                key_insights.append(t("reports.fallback.insight.mood_positive", locale))

        action_items = [
            t("reports.fallback.action.review_max_loss", locale),
            t("reports.fallback.action.analyze_best_trade", locale),
            t("reports.fallback.action.plan_next_period", locale),
        ]

        return {
            "analysis": analysis,
            "recommendations": recommendations[:3],
            "key_insights": key_insights[:3],
            "action_items": action_items,
        }

    def _get_coach_insights(
        self,
        user_id: UUID,
        start_date: date,
        end_date: date,
        locale: Locale,
        project_id: Optional[UUID] = None,
    ) -> Dict[str, Any]:
        """Get insights from coach interactions."""
        # Query chat sessions for the period
        query = self.db.query(ChatSession).filter(
            and_(
                ChatSession.user_id == user_id,
                ChatSession.created_at
                >= datetime.combine(start_date, datetime.min.time()),
                ChatSession.created_at
                <= datetime.combine(end_date, datetime.max.time()),
            )
        )
        if project_id is not None:
            query = query.filter(ChatSession.project_id == project_id)

        sessions = query.all()

        if not sessions:
            return {"notes": {}, "primary_coach": None}

        # Count sessions per coach
        coach_sessions = {}
        for session in sessions:
            if session.coach_id not in coach_sessions:
                coach_sessions[session.coach_id] = 0
            coach_sessions[session.coach_id] += 1

        # Find primary coach
        primary_coach = (
            max(coach_sessions, key=coach_sessions.get) if coach_sessions else None
        )

        # Generate notes (simplified version)
        notes = {}
        for coach_id, count in coach_sessions.items():
            notes[coach_id] = t("reports.coach.notes", locale, count=count)

        return {"notes": notes, "primary_coach": primary_coach}

    def _generate_summary(self, report: Report, locale: Locale) -> str:
        """Generate a summary for the report."""
        period_str = t(
            "reports.summary.period",
            locale,
            start=self._format_date(locale, report.period_start),
            end=self._format_date(locale, report.period_end),
        )

        summary = t(
            "reports.summary.base",
            locale,
            period=period_str,
            total_trades=report.total_trades,
        )

        if report.win_rate is not None and report.win_rate != 0:
            summary += t("reports.summary.win_rate", locale, win_rate=report.win_rate)

        if report.total_pnl is not None and report.total_pnl != 0:
            if report.total_pnl > 0:
                summary += t(
                    "reports.summary.profit", locale, total_pnl=report.total_pnl
                )
            else:
                summary += t(
                    "reports.summary.loss", locale, total_loss=abs(report.total_pnl)
                )

        if report.mood_improvement is not None and report.mood_improvement != 0:
            if report.mood_improvement > 0:
                summary += t("reports.summary.mood_improved", locale)
            else:
                summary += t("reports.summary.mood_worsened", locale)

        return summary

    # Report Management
    def get_user_reports(
        self,
        user_id: UUID,
        report_type: Optional[ReportType] = None,
        project_id: Optional[UUID] = None,
        limit: int = 10,
    ) -> List[Report]:
        """Get user's reports."""
        query = self.db.query(Report).filter(Report.user_id == user_id)

        if report_type:
            query = query.filter(Report.report_type == report_type)

        if project_id is not None:
            query = query.filter(Report.project_id == project_id)

        return query.order_by(Report.created_at.desc()).limit(limit).all()

    def get_report_by_id(self, report_id: UUID) -> Optional[Report]:
        """Get report by ID."""
        return self.db.query(Report).filter(Report.id == report_id).first()

    def get_latest_report(
        self, user_id: UUID, report_type: ReportType, project_id: Optional[UUID] = None
    ) -> Optional[Report]:
        """Get the latest report of a specific type."""
        query = self.db.query(Report).filter(
            and_(
                Report.user_id == user_id,
                Report.report_type == report_type,
                Report.status == ReportStatus.COMPLETED,
            )
        )
        if project_id is not None:
            query = query.filter(Report.project_id == project_id)
        return query.order_by(Report.created_at.desc()).first()

    # Schedule Management
    def get_user_schedule(self, user_id: UUID) -> Optional[ReportSchedule]:
        """Get user's report schedule preferences."""
        return (
            self.db.query(ReportSchedule)
            .filter(ReportSchedule.user_id == user_id)
            .first()
        )

    def create_or_update_schedule(
        self, user_id: UUID, schedule_data: Dict[str, Any]
    ) -> ReportSchedule:
        """Create or update user's report schedule."""
        schedule = self.get_user_schedule(user_id)

        if not schedule:
            schedule = ReportSchedule(user_id=user_id, **schedule_data)
            self.db.add(schedule)
        else:
            for key, value in schedule_data.items():
                if hasattr(schedule, key):
                    setattr(schedule, key, value)
            schedule.updated_at = datetime.utcnow()

        self.db.commit()
        self.db.refresh(schedule)
        return schedule

    def should_generate_report(
        self, user_id: UUID, report_type: ReportType
    ) -> Tuple[bool, Optional[date]]:
        """Check if a report should be generated for the user."""
        schedule = self.get_user_schedule(user_id)
        if not schedule or not schedule.is_active:
            return False, None

        now = datetime.utcnow()

        if report_type == ReportType.DAILY:
            if not schedule.daily_enabled:
                return False, None

            # Check if already generated today
            if schedule.last_daily_generated:
                if schedule.last_daily_generated.date() >= date.today():
                    return False, None

            return True, date.today() - timedelta(days=1)

        elif report_type == ReportType.WEEKLY:
            if not schedule.weekly_enabled:
                return False, None

            # Check if already generated this week
            if schedule.last_weekly_generated:
                days_since = (now - schedule.last_weekly_generated).days
                if days_since < 7:
                    return False, None

            # Calculate last week's start date
            days_since_monday = now.weekday()
            last_monday = now.date() - timedelta(days=days_since_monday + 7)
            return True, last_monday

        elif report_type == ReportType.MONTHLY:
            if not schedule.monthly_enabled:
                return False, None

            # Check if already generated this month
            if schedule.last_monthly_generated:
                if (
                    schedule.last_monthly_generated.year == now.year
                    and schedule.last_monthly_generated.month == now.month
                ):
                    return False, None

            return True, None  # Will use default (last month)

        return False, None


def get_report_service(db: Session = None) -> ReportService:
    """Factory function to create ReportService instance."""
    if db is None:
        db = next(get_db())
    return ReportService(db)
