"""Report generation service."""

import asyncio
import json
from typing import List, Optional, Dict, Any, Tuple
from sqlalchemy import and_
from sqlalchemy.orm import Session
from uuid import UUID
from datetime import datetime, date, timedelta

from domain.report.models import Report, ReportType, ReportStatus, ReportSchedule, ReportTemplate
from domain.journal.models import Journal
from domain.coach.models import ChatSession
from domain.project.models import Project
from domain.user.models import User
from services.llm_router import LLMRouter
from core.database import get_db


class ReportService:
    """Service for generating and managing periodic reports."""

    def __init__(self, db: Session):
        self.db = db

    def _get_project_name(self, user_id: UUID, project_id: Optional[UUID]) -> Optional[str]:
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

    # Report Generation
    def generate_daily_report(
        self,
        user_id: UUID,
        report_date: Optional[date] = None,
        *,
        project_id: Optional[UUID] = None,
    ) -> Report:
        """Generate daily report for a user."""
        if not report_date:
            report_date = date.today() - timedelta(days=1)  # Yesterday's report

        period_start = report_date
        period_end = report_date

        project_name = self._get_project_name(user_id, project_id) if project_id else None
        title = f"交易日报 - {report_date.strftime('%Y年%m月%d日')}"
        if project_name:
            title = f"{title}（{project_name}）"

        return self._generate_report(
            user_id=user_id,
            report_type=ReportType.DAILY,
            period_start=period_start,
            period_end=period_end,
            title=title,
            project_id=project_id,
        )

    def generate_weekly_report(
        self,
        user_id: UUID,
        week_start: Optional[date] = None,
        *,
        project_id: Optional[UUID] = None,
    ) -> Report:
        """Generate weekly report for a user."""
        if not week_start:
            # Default to last week's Monday
            today = date.today()
            days_since_monday = today.weekday()
            last_monday = today - timedelta(days=days_since_monday + 7)
            week_start = last_monday

        period_start = week_start
        period_end = week_start + timedelta(days=6)

        project_name = self._get_project_name(user_id, project_id) if project_id else None
        title = f"交易周报 - 第{week_start.isocalendar()[1]}周"
        if project_name:
            title = f"{title}（{project_name}）"

        return self._generate_report(
            user_id=user_id,
            report_type=ReportType.WEEKLY,
            period_start=period_start,
            period_end=period_end,
            title=title,
            project_id=project_id,
        )

    def generate_monthly_report(self, user_id: UUID, year: Optional[int] = None,
                               month: Optional[int] = None, *, project_id: Optional[UUID] = None) -> Report:
        """Generate monthly report for a user."""
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

        project_name = self._get_project_name(user_id, project_id) if project_id else None
        title = f"交易月报 - {year}年{month}月"
        if project_name:
            title = f"{title}（{project_name}）"

        return self._generate_report(
            user_id=user_id,
            report_type=ReportType.MONTHLY,
            period_start=period_start,
            period_end=period_end,
            title=title,
            project_id=project_id,
        )

    def _generate_report(self, user_id: UUID, report_type: ReportType,
                        period_start: date, period_end: date, title: str, project_id: Optional[UUID] = None) -> Report:
        """Generate a report for the specified period."""
        start_time = datetime.now()

        # Create report record
        report = Report(
            user_id=user_id,
            project_id=project_id,
            report_type=report_type,
            title=title,
            subtitle=f"{period_start.strftime('%Y-%m-%d')} 至 {period_end.strftime('%Y-%m-%d')}",
            period_start=period_start,
            period_end=period_end,
            status=ReportStatus.GENERATING
        )
        self.db.add(report)
        self.db.commit()

        try:
            # Fetch trading journals for the period
            journals = self._fetch_journals(user_id, period_start, period_end, project_id)

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
            psych_metrics = self._calculate_psychological_metrics(journals)
            report.avg_mood_before = psych_metrics["avg_mood_before"]
            report.avg_mood_after = psych_metrics["avg_mood_after"]
            report.mood_improvement = psych_metrics["mood_improvement"]

            # Analyze trading patterns
            patterns = self._analyze_patterns(journals)
            report.top_mistakes = patterns["top_mistakes"]
            report.top_successes = patterns["top_successes"]
            report.improvements = patterns["improvements"]

            # Generate AI analysis and insights
            ai_insights = self._generate_ai_insights(
                user_id, journals, stats, psych_metrics, patterns, report_type
            )
            report.ai_analysis = ai_insights["analysis"]
            report.ai_recommendations = ai_insights["recommendations"]
            report.key_insights = ai_insights["key_insights"]
            report.action_items = ai_insights["action_items"]

            # Get coach insights
            coach_insights = self._get_coach_insights(user_id, period_start, period_end, project_id)
            report.coach_notes = coach_insights["notes"]
            report.primary_coach_id = coach_insights["primary_coach"]

            # Store structured content
            report.content = {
                "statistics": stats,
                "psychological": psych_metrics,
                "patterns": patterns,
                "journals_analyzed": len(journals),
                "period": {
                    "start": period_start.isoformat(),
                    "end": period_end.isoformat()
                }
            }

            # Generate summary
            report.summary = self._generate_summary(report)

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
                "max_loss": 0.0
            }

        total_trades = len(journals)
        winning_trades = sum(1 for j in journals if j.pnl_amount is not None and j.pnl_amount > 0)
        losing_trades = sum(1 for j in journals if j.pnl_amount is not None and j.pnl_amount < 0)

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
            "max_loss": round(max_loss, 2)
        }

    def _calculate_psychological_metrics(self, journals: List[Journal]) -> Dict[str, Any]:
        """Calculate psychological metrics from journals."""
        if not journals:
            return {
                "avg_mood_before": None,
                "avg_mood_after": None,
                "mood_improvement": None,
                "emotional_patterns": []
            }

        mood_befores = [j.emotion_before for j in journals if j.emotion_before is not None]
        mood_afters = [j.emotion_after for j in journals if j.emotion_after is not None]

        avg_mood_before = sum(mood_befores) / len(mood_befores) if mood_befores else None
        avg_mood_after = sum(mood_afters) / len(mood_afters) if mood_afters else None

        mood_improvement = None
        if avg_mood_before is not None and avg_mood_after is not None:
            mood_improvement = avg_mood_after - avg_mood_before

        # Analyze emotional patterns
        emotional_patterns = []
        if mood_befores:
            from collections import Counter
            labels = {
                1: "很紧张",
                2: "紧张",
                3: "一般",
                4: "平静",
                5: "很平静",
            }
            emotion_counts = Counter(labels.get(v, str(v)) for v in mood_befores)
            emotional_patterns = [
                {"emotion": emotion, "count": count}
                for emotion, count in emotion_counts.most_common(5)
            ]

        return {
            "avg_mood_before": round(avg_mood_before, 2) if avg_mood_before else None,
            "avg_mood_after": round(avg_mood_after, 2) if avg_mood_after else None,
            "mood_improvement": round(mood_improvement, 2) if mood_improvement else None,
            "emotional_patterns": emotional_patterns
        }

    def _analyze_patterns(self, journals: List[Journal]) -> Dict[str, Any]:
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
            winning_journals = [j for j in journals if j.pnl_amount is not None and j.pnl_amount > 0]
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
                    "early_exit": "提前退出：提前制定止盈/止损规则并严格执行",
                    "late_exit": "晚止损/止盈：设置条件单或提醒，避免犹豫",
                    "no_stop_loss": "未设止损：每笔交易必须先定义风险",
                    "over_leverage": "杠杆过高：降低杠杆与仓位，优先保证生存",
                    "revenge_trade": "报复性交易：亏损后强制冷静期，避免情绪决策",
                    "fomo": "FOMO：只做符合系统条件的机会，避免追涨杀跌",
                    "position_size": "仓位过大：用固定风险模型计算仓位",
                    "other": "其他：记录触发场景，针对性制定规则",
                }
                improvements = []
                for m in top_mistakes[:3]:
                    key = m.get("mistake")
                    tip = suggestions.get(str(key), f"减少 {key} 的发生频率")
                    improvements.append(f"{tip}（当前：{m.get('frequency')} 次）")

        return {
            "top_mistakes": top_mistakes,
            "top_successes": top_successes,
            "improvements": improvements
        }

    def _generate_ai_insights(self, user_id: UUID, journals: List[Journal],
                             stats: Dict, psych_metrics: Dict, patterns: Dict,
                             report_type: ReportType) -> Dict[str, Any]:
        """Generate AI insights for the report."""
        if not journals:
            return {
                "analysis": "本期无交易记录。",
                "recommendations": [],
                "key_insights": [],
                "action_items": []
            }

        # Prepare context for AI
        context = {
            "report_type": report_type.value,
            "statistics": stats,
            "psychological": psych_metrics,
            "patterns": patterns,
            "total_journals": len(journals)
        }

        # Generate analysis using LLM
        prompt = f"""
        作为专业的交易心理教练，请分析以下{report_type.value}交易报告数据：

        统计数据：
        - 总交易次数：{stats['total_trades']}
        - 胜率：{stats['win_rate']}%
        - 总盈亏：{stats['total_pnl']}
        - 平均盈亏：{stats['avg_pnl']}

        心理指标：
        - 交易前平均情绪：{psych_metrics['avg_mood_before']}
        - 交易后平均情绪：{psych_metrics['avg_mood_after']}
        - 情绪改善：{psych_metrics['mood_improvement']}

        请提供：
        1. 深度分析（200字以内）
        2. 3个关键洞察
        3. 3个具体的改进建议
        4. 3个可执行的行动项

        请用JSON格式返回。
        """

        try:
            user = self.db.query(User).filter(User.id == user_id).first()
            router = LLMRouter(user=user) if user else LLMRouter()
            response = self._run_llm_chat(router, prompt)
            insights = self._parse_llm_json(response)

            return {
                "analysis": insights.get("analysis", ""),
                "recommendations": insights.get("recommendations", []),
                "key_insights": insights.get("key_insights", []),
                "action_items": insights.get("action_items", [])
            }
        except Exception as e:
            # Fallback to rule-based insights
            return self._generate_rule_based_insights(stats, psych_metrics, patterns)

    def _run_llm_chat(self, router: LLMRouter, prompt: str) -> str:
        """Run an LLM chat call from sync code (best-effort)."""
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(
                router.chat(
                    prompt,
                    system="你是一位专业的交易心理教练，擅长总结交易表现、识别行为模式并给出改进建议。",
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

    def _generate_rule_based_insights(self, stats: Dict, psych_metrics: Dict,
                                     patterns: Dict) -> Dict[str, Any]:
        """Generate rule-based insights as fallback."""
        analysis = f"本期共完成{stats['total_trades']}笔交易，胜率{stats['win_rate']}%，"

        if stats['total_pnl'] > 0:
            analysis += f"总体盈利{stats['total_pnl']}。"
        else:
            analysis += f"总体亏损{abs(stats['total_pnl'])}。"

        recommendations = []
        if stats['win_rate'] < 50:
            recommendations.append("提高选择交易机会的标准，减少低质量交易")

        if psych_metrics['mood_improvement'] and psych_metrics['mood_improvement'] < 0:
            recommendations.append("关注交易对情绪的负面影响，考虑减小仓位或降低频率")

        if patterns['top_mistakes']:
            recommendations.append(f"重点解决最常见的错误：{patterns['top_mistakes'][0]['mistake']}")

        key_insights = []
        if stats['win_rate'] > 60:
            key_insights.append("交易系统表现良好，保持当前策略")
        if stats['max_profit'] and stats['max_loss'] is not None and stats['max_loss'] < stats['max_profit'] * 0.5:
            key_insights.append("风险控制得当，止损执行良好")
        if psych_metrics['avg_mood_after'] and psych_metrics['avg_mood_before']:
            if psych_metrics['avg_mood_after'] > psych_metrics['avg_mood_before']:
                key_insights.append("交易过程对心理状态有积极影响")

        action_items = [
            "回顾本期最大亏损交易，总结教训",
            "分析最成功的交易，提炼可复制模式",
            "制定下期交易计划和风险管理规则"
        ]

        return {
            "analysis": analysis,
            "recommendations": recommendations[:3],
            "key_insights": key_insights[:3],
            "action_items": action_items
        }

    def _get_coach_insights(
        self,
        user_id: UUID,
        start_date: date,
        end_date: date,
        project_id: Optional[UUID] = None,
    ) -> Dict[str, Any]:
        """Get insights from coach interactions."""
        # Query chat sessions for the period
        query = self.db.query(ChatSession).filter(
            and_(
                ChatSession.user_id == user_id,
                ChatSession.created_at >= datetime.combine(start_date, datetime.min.time()),
                ChatSession.created_at <= datetime.combine(end_date, datetime.max.time())
            )
        )
        if project_id is not None:
            query = query.filter(ChatSession.project_id == project_id)

        sessions = query.all()

        if not sessions:
            return {
                "notes": {},
                "primary_coach": None
            }

        # Count sessions per coach
        coach_sessions = {}
        for session in sessions:
            if session.coach_id not in coach_sessions:
                coach_sessions[session.coach_id] = 0
            coach_sessions[session.coach_id] += 1

        # Find primary coach
        primary_coach = max(coach_sessions, key=coach_sessions.get) if coach_sessions else None

        # Generate notes (simplified version)
        notes = {}
        for coach_id, count in coach_sessions.items():
            notes[coach_id] = f"共进行了{count}次对话"

        return {
            "notes": notes,
            "primary_coach": primary_coach
        }

    def _generate_summary(self, report: Report) -> str:
        """Generate a summary for the report."""
        period_str = f"{report.period_start.strftime('%Y年%m月%d日')}至{report.period_end.strftime('%Y年%m月%d日')}"

        summary = f"在{period_str}期间，您共完成{report.total_trades}笔交易。"

        if report.win_rate:
            summary += f"胜率为{report.win_rate}%，"

        if report.total_pnl:
            if report.total_pnl > 0:
                summary += f"总体盈利{report.total_pnl:.2f}。"
            else:
                summary += f"总体亏损{abs(report.total_pnl):.2f}。"

        if report.mood_improvement:
            if report.mood_improvement > 0:
                summary += "交易后情绪有所改善。"
            else:
                summary += "需要关注交易对情绪的影响。"

        return summary

    # Report Management
    def get_user_reports(self, user_id: UUID, report_type: Optional[ReportType] = None,
                        project_id: Optional[UUID] = None, limit: int = 10) -> List[Report]:
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

    def get_latest_report(self, user_id: UUID,
                         report_type: ReportType, project_id: Optional[UUID] = None) -> Optional[Report]:
        """Get the latest report of a specific type."""
        query = self.db.query(Report).filter(
            and_(
                Report.user_id == user_id,
                Report.report_type == report_type,
                Report.status == ReportStatus.COMPLETED
            )
        )
        if project_id is not None:
            query = query.filter(Report.project_id == project_id)
        return query.order_by(Report.created_at.desc()).first()

    # Schedule Management
    def get_user_schedule(self, user_id: UUID) -> Optional[ReportSchedule]:
        """Get user's report schedule preferences."""
        return self.db.query(ReportSchedule).filter(
            ReportSchedule.user_id == user_id
        ).first()

    def create_or_update_schedule(self, user_id: UUID,
                                 schedule_data: Dict[str, Any]) -> ReportSchedule:
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

    def should_generate_report(self, user_id: UUID,
                              report_type: ReportType) -> Tuple[bool, Optional[date]]:
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
                if schedule.last_monthly_generated.year == now.year and \
                   schedule.last_monthly_generated.month == now.month:
                    return False, None

            return True, None  # Will use default (last month)

        return False, None


def get_report_service(db: Session = None) -> ReportService:
    """Factory function to create ReportService instance."""
    if db is None:
        db = next(get_db())
    return ReportService(db)
