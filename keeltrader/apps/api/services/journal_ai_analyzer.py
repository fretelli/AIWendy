"""AI-powered journal analysis service."""

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from core.logging import get_logger
from domain.journal.models import Journal
from domain.journal.schemas import JournalResponse, JournalStatistics
from services.llm_router import LLMRouter

logger = get_logger(__name__)


class JournalAIAnalyzer:
    """Analyze trading journals using AI to provide insights and recommendations."""

    def __init__(self, llm_router: LLMRouter):
        self.llm = llm_router

    async def analyze_single_journal(
        self, journal: JournalResponse, user_stats: Optional[JournalStatistics] = None
    ) -> Dict[str, Any]:
        """Analyze a single journal entry."""

        # Build analysis prompt
        prompt = self._build_single_analysis_prompt(journal, user_stats)

        # Get AI analysis
        analysis = await self.llm.chat(prompt)

        # Parse and structure the response
        return self._parse_ai_response(analysis, "single")

    async def analyze_recent_trades(
        self, journals: List[JournalResponse], user_stats: JournalStatistics
    ) -> Dict[str, Any]:
        """Analyze recent trading patterns and provide insights."""

        if not journals:
            return {
                "patterns": [],
                "recommendations": [
                    "Start journaling your trades to get personalized insights"
                ],
                "risk_assessment": "No data available",
                "psychological_insights": "No data available",
            }

        # Build comprehensive analysis prompt
        prompt = self._build_pattern_analysis_prompt(journals, user_stats)

        # Get AI analysis
        analysis = await self.llm.chat(prompt)

        # Parse and structure the response
        return self._parse_ai_response(analysis, "pattern")

    async def generate_improvement_plan(
        self, journals: List[JournalResponse], user_stats: JournalStatistics
    ) -> Dict[str, Any]:
        """Generate a personalized improvement plan based on trading history."""

        # Build improvement plan prompt
        prompt = self._build_improvement_prompt(journals, user_stats)

        # Get AI recommendations
        plan = await self.llm.chat(prompt)

        # Parse and structure the response
        return self._parse_ai_response(plan, "improvement")

    def _build_single_analysis_prompt(
        self, journal: JournalResponse, stats: Optional[JournalStatistics] = None
    ) -> str:
        """Build prompt for single journal analysis."""

        stats_context = ""
        if stats:
            stats_context = f"""
Overall Trading Statistics:
- Total trades: {stats.total_trades}
- Win rate: {stats.win_rate:.1f}%
- Average win: ${stats.average_win:.2f}
- Average loss: ${stats.average_loss:.2f}
- Current streak: {stats.current_streak}
- Rule violation rate: {stats.rule_violation_rate:.1f}%
"""

        return f"""You are an expert trading psychology coach and performance analyst. Analyze the following trading journal entry and provide actionable insights.

Trade Details:
- Symbol: {journal.symbol}
- Direction: {journal.direction}
- Result: {journal.result}
- P&L: ${journal.pnl_amount or 0:.2f}
- Entry Price: ${journal.entry_price or 0:.2f}
- Exit Price: ${journal.exit_price or 0:.2f}
- Position Size: {journal.position_size or 'N/A'}

Risk Management:
- Stop Loss: ${journal.stop_loss or 0:.2f}
- Take Profit: ${journal.take_profit or 0:.2f}
- Risk/Reward Ratio: {journal.risk_reward_ratio or 'N/A'}

Psychology & Emotions:
- Emotion Before: {journal.emotion_before or 'N/A'}/5
- Emotion During: {journal.emotion_during or 'N/A'}/5
- Emotion After: {journal.emotion_after or 'N/A'}/5
- Confidence Level: {journal.confidence_level or 'N/A'}/5
- Stress Level: {journal.stress_level or 'N/A'}/5
- Rules Followed: {'Yes' if journal.followed_rules else 'No'}
- Rule Violations: {', '.join(journal.rule_violations) if journal.rule_violations else 'None'}

Trade Notes:
- Setup: {journal.setup_description or 'N/A'}
- Exit Reason: {journal.exit_reason or 'N/A'}
- Lessons Learned: {journal.lessons_learned or 'N/A'}

{stats_context}

Please provide a structured analysis with:
1. **Trade Execution Assessment** (What went right/wrong)
2. **Psychological Analysis** (Emotional state and its impact)
3. **Risk Management Review** (Position sizing, stop loss placement)
4. **Key Patterns Identified** (Behavioral or technical patterns)
5. **Specific Improvements** (3-5 actionable recommendations)
6. **Mindset Coaching** (Mental game advice)

Format your response in a clear, structured way with bullet points."""

    def _build_pattern_analysis_prompt(
        self, journals: List[JournalResponse], stats: JournalStatistics
    ) -> str:
        """Build prompt for pattern analysis across multiple trades."""

        # Summarize recent trades
        recent_results = [j.result for j in journals[:10]]
        recent_pnl = sum(j.pnl_amount or 0 for j in journals[:10])
        violation_count = sum(1 for j in journals[:10] if not j.followed_rules)
        avg_confidence = sum(j.confidence_level or 0 for j in journals[:10]) / len(
            journals[:10]
        )
        avg_stress = sum(j.stress_level or 0 for j in journals[:10]) / len(
            journals[:10]
        )

        # Find common violations
        all_violations = []
        for j in journals[:10]:
            if j.rule_violations:
                all_violations.extend(j.rule_violations)

        from collections import Counter

        violation_frequency = Counter(all_violations)

        return f"""You are an expert trading psychology coach analyzing trading patterns. Review the following trading data and identify key patterns and areas for improvement.

Recent Trading Summary (Last 10 trades):
- Results: {', '.join(recent_results)}
- Total P&L: ${recent_pnl:.2f}
- Rule Violations: {violation_count}/10 trades
- Average Confidence: {avg_confidence:.1f}/5
- Average Stress: {avg_stress:.1f}/5

Most Common Rule Violations:
{chr(10).join(f'- {v}: {c} times' for v, c in violation_frequency.most_common(3))}

Overall Statistics:
- Total trades: {stats.total_trades}
- Win rate: {stats.win_rate:.1f}%
- Profit factor: {stats.profit_factor:.2f}
- Best trade: ${stats.best_trade:.2f}
- Worst trade: ${stats.worst_trade:.2f}
- Current streak: {stats.current_streak}

Please identify:
1. **Recurring Patterns** (Both positive and negative)
2. **Psychological Triggers** (What causes poor decisions)
3. **Strengths to Leverage** (What's working well)
4. **Critical Weaknesses** (Top priority issues)
5. **Risk Patterns** (Position sizing, stop loss issues)
6. **Recommended Focus Areas** (Next 30 days)

Provide specific, actionable insights based on the data."""

    def _build_improvement_prompt(
        self, journals: List[JournalResponse], stats: JournalStatistics
    ) -> str:
        """Build prompt for generating improvement plan."""

        # Identify key issues
        issues = []
        if stats.win_rate < 50:
            issues.append("Low win rate")
        if stats.rule_violation_rate > 30:
            issues.append("High rule violation rate")
        if stats.average_stress > 3.5:
            issues.append("High stress levels")
        if stats.current_streak < -3:
            issues.append("Current losing streak")

        return f"""You are a professional trading coach creating a personalized improvement plan. Based on the trading data, develop a comprehensive 30-day improvement plan.

Current Performance Metrics:
- Win rate: {stats.win_rate:.1f}%
- Average win: ${stats.average_win:.2f}
- Average loss: ${stats.average_loss:.2f}
- Profit factor: {stats.profit_factor:.2f}
- Rule violation rate: {stats.rule_violation_rate:.1f}%
- Average confidence: {stats.average_confidence:.1f}/5
- Average stress: {stats.average_stress:.1f}/5

Key Issues Identified:
{chr(10).join(f'- {issue}' for issue in issues) if issues else '- None identified (good performance)'}

Create a structured 30-day improvement plan with:

1. **Week 1 Goals** (Immediate focus areas)
   - Specific daily practices
   - Mental exercises
   - Risk management rules

2. **Week 2-3 Goals** (Building consistency)
   - Position sizing adjustments
   - Entry/exit refinements
   - Psychological training

3. **Week 4 Goals** (Performance review)
   - Metrics to track
   - Success criteria
   - Adjustment strategies

4. **Daily Routines**
   - Pre-market preparation
   - During-market practices
   - Post-market review

5. **Mental Game Exercises**
   - Visualization techniques
   - Stress management
   - Confidence building

6. **Risk Management Rules**
   - Position sizing formula
   - Stop loss guidelines
   - Maximum daily loss

Make the plan specific, measurable, and actionable."""

    def _parse_ai_response(self, response: str, analysis_type: str) -> Dict[str, Any]:
        """Parse and structure AI response based on analysis type."""

        # Basic parsing - in production, use more sophisticated parsing
        lines = response.split("\n")

        if analysis_type == "single":
            return {
                "analysis": response,
                "detected_patterns": self._extract_patterns(response),
                "recommendations": self._extract_recommendations(response),
                "risk_assessment": self._extract_section(response, "Risk Management"),
                "psychological_insights": self._extract_section(
                    response, "Psychological"
                ),
                "timestamp": datetime.utcnow().isoformat(),
            }

        elif analysis_type == "pattern":
            return {
                "patterns": self._extract_patterns(response),
                "triggers": self._extract_section(response, "Triggers"),
                "strengths": self._extract_section(response, "Strengths"),
                "weaknesses": self._extract_section(response, "Weaknesses"),
                "focus_areas": self._extract_recommendations(response),
                "full_analysis": response,
                "timestamp": datetime.utcnow().isoformat(),
            }

        elif analysis_type == "improvement":
            return {
                "plan": response,
                "week1_goals": self._extract_section(response, "Week 1"),
                "daily_routines": self._extract_section(response, "Daily Routines"),
                "mental_exercises": self._extract_section(response, "Mental Game"),
                "risk_rules": self._extract_section(response, "Risk Management Rules"),
                "success_metrics": self._extract_metrics(response),
                "timestamp": datetime.utcnow().isoformat(),
            }

        return {"analysis": response, "timestamp": datetime.utcnow().isoformat()}

    def _extract_patterns(self, text: str) -> List[str]:
        """Extract patterns from AI response."""
        patterns = []
        lines = text.split("\n")

        in_pattern_section = False
        for line in lines:
            if "pattern" in line.lower() or "recurring" in line.lower():
                in_pattern_section = True
            elif in_pattern_section and line.strip().startswith("-"):
                pattern = line.strip().lstrip("- ").strip()
                if pattern and len(pattern) > 10:
                    patterns.append(pattern)
            elif in_pattern_section and not line.strip():
                break

        return patterns[:5]  # Return top 5 patterns

    def _extract_recommendations(self, text: str) -> List[str]:
        """Extract recommendations from AI response."""
        recommendations = []
        lines = text.split("\n")

        in_rec_section = False
        for line in lines:
            if (
                "recommend" in line.lower()
                or "improvement" in line.lower()
                or "focus" in line.lower()
            ):
                in_rec_section = True
            elif in_rec_section and line.strip().startswith("-"):
                rec = line.strip().lstrip("- ").strip()
                if rec and len(rec) > 10:
                    recommendations.append(rec)
            elif in_rec_section and not line.strip():
                break

        return recommendations[:5]  # Return top 5 recommendations

    def _extract_section(self, text: str, section_name: str) -> str:
        """Extract a specific section from AI response."""
        lines = text.split("\n")

        section_content = []
        in_section = False

        for line in lines:
            if section_name.lower() in line.lower():
                in_section = True
            elif in_section:
                if line.strip().startswith("#") or line.strip().startswith("**"):
                    break
                if line.strip():
                    section_content.append(line.strip())

        return " ".join(section_content)[:500]  # Limit to 500 chars

    def _extract_metrics(self, text: str) -> List[str]:
        """Extract success metrics from improvement plan."""
        metrics = []
        lines = text.split("\n")

        for line in lines:
            if any(
                word in line.lower()
                for word in ["metric", "track", "measure", "target"]
            ):
                if line.strip().startswith("-"):
                    metric = line.strip().lstrip("- ").strip()
                    if metric:
                        metrics.append(metric)

        return metrics[:5]  # Return top 5 metrics
