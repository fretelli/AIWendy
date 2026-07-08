"""Pure RPG calculations for ranks, attributes, and achievements."""

from datetime import datetime

from domain.rpg.models import Achievement, Rank, TradingCharacter

# XP thresholds per level (cumulative XP needed)
XP_PER_LEVEL = 100  # 100 XP per level


def calculate_rank(level: int) -> Rank:
    """Calculate rank from level. 1-19 Bronze, 20-39 Silver, 40-59 Gold, 60-79 Platinum, 80-99 Diamond."""
    if level >= 80:
        return Rank.DIAMOND
    elif level >= 60:
        return Rank.PLATINUM
    elif level >= 40:
        return Rank.GOLD
    elif level >= 20:
        return Rank.SILVER
    return Rank.BRONZE


def calculate_level(xp: int) -> int:
    """Calculate level from XP. Capped at 99."""
    return min(99, max(1, xp // XP_PER_LEVEL + 1))


def calculate_discipline(journals: list) -> int:
    """Calculate discipline attribute (0-100).
    Based on: stop_loss set rate, followed_rules rate, no revenge trading.
    """
    if not journals:
        return 50

    total = len(journals)
    stop_loss_set = sum(1 for j in journals if j.stop_loss is not None)
    followed_rules = sum(1 for j in journals if j.followed_rules)
    no_revenge = sum(
        1 for j in journals
        if not j.rule_violations or "revenge_trade" not in (j.rule_violations or [])
    )

    stop_loss_rate = stop_loss_set / total
    rules_rate = followed_rules / total
    no_revenge_rate = no_revenge / total

    score = int((stop_loss_rate * 40 + rules_rate * 40 + no_revenge_rate * 20) * 100)
    return max(0, min(100, score))


def calculate_patience(journals: list) -> int:
    """Calculate patience attribute (0-100).
    Based on: average hold duration, daily trade frequency (fewer = more patient).
    """
    if not journals:
        return 50

    # Average hold duration
    durations = []
    for j in journals:
        if j.entry_time and j.exit_time:
            delta = (j.exit_time - j.entry_time).total_seconds() / 3600  # hours
            durations.append(delta)

    avg_duration_score = 50
    if durations:
        avg_hours = sum(durations) / len(durations)
        # Longer holds = more patience. Cap at 48h for max score.
        avg_duration_score = min(100, int(avg_hours / 48 * 100))

    # Trade frequency (trades per day — fewer is better)
    dates = set()
    for j in journals:
        if j.trade_date:
            dates.add(j.trade_date.date() if hasattr(j.trade_date, 'date') else j.trade_date)

    freq_score = 50
    if dates:
        trades_per_day = len(journals) / len(dates)
        # 1-2 trades/day = 100, 10+ = 0
        freq_score = max(0, min(100, int((1 - (trades_per_day - 1) / 9) * 100)))

    return max(0, min(100, int(avg_duration_score * 0.5 + freq_score * 0.5)))


def calculate_risk_management(journals: list) -> int:
    """Calculate risk management attribute (0-100).
    Based on: risk/reward ratio, position size consistency.
    """
    if not journals:
        return 50

    # Average risk/reward ratio
    rr_ratios = [j.risk_reward_ratio for j in journals if j.risk_reward_ratio and j.risk_reward_ratio > 0]
    rr_score = 50
    if rr_ratios:
        avg_rr = sum(rr_ratios) / len(rr_ratios)
        # 2:1 = 100, <1:1 = 0
        rr_score = max(0, min(100, int(avg_rr / 2 * 100)))

    # Position size consistency (lower std dev relative to mean = better)
    sizes = [j.position_size for j in journals if j.position_size and j.position_size > 0]
    size_score = 50
    if len(sizes) >= 3:
        mean_size = sum(sizes) / len(sizes)
        variance = sum((s - mean_size) ** 2 for s in sizes) / len(sizes)
        std_dev = variance ** 0.5
        cv = std_dev / mean_size if mean_size > 0 else 1  # coefficient of variation
        # CV < 0.1 = 100, CV > 0.5 = 0
        size_score = max(0, min(100, int((1 - cv / 0.5) * 100)))

    return max(0, min(100, int(rr_score * 0.6 + size_score * 0.4)))


def calculate_decisiveness(journals: list) -> int:
    """Calculate decisiveness attribute (0-100).
    Based on: entry timing precision, no hesitation cancels.
    """
    if not journals:
        return 50

    total = len(journals)
    # Trades with both entry and exit = decisive execution
    completed = sum(1 for j in journals if j.entry_price and j.exit_price)
    completion_rate = completed / total if total > 0 else 0

    # Trades with setup descriptions = planned entries
    planned = sum(1 for j in journals if j.setup_description)
    planned_rate = planned / total if total > 0 else 0

    score = int((completion_rate * 60 + planned_rate * 40) * 100)
    return max(0, min(100, score))


def calculate_consistency(journals: list) -> int:
    """Calculate consistency attribute (0-100).
    Based on: rolling window win rate standard deviation (lower = more consistent).
    """
    if len(journals) < 5:
        return 50

    # Calculate win rate in rolling windows of 5 trades
    window_size = 5
    win_rates = []
    sorted_journals = sorted(journals, key=lambda j: j.trade_date or datetime.min)

    for i in range(len(sorted_journals) - window_size + 1):
        window = sorted_journals[i:i + window_size]
        wins = sum(1 for j in window if j.result and j.result.value == "win")
        win_rates.append(wins / window_size)

    if not win_rates:
        return 50

    mean_wr = sum(win_rates) / len(win_rates)
    variance = sum((wr - mean_wr) ** 2 for wr in win_rates) / len(win_rates)
    std_dev = variance ** 0.5

    # std_dev 0 = perfect consistency (100), std_dev 0.4+ = 0
    score = max(0, min(100, int((1 - std_dev / 0.4) * 100)))
    return score


def check_achievement_criteria(achievement: Achievement, journals: list, character: TradingCharacter) -> bool:
    """Check if an achievement's criteria are met."""
    criteria = achievement.criteria
    criteria_type = criteria.get("type")

    if criteria_type == "win_count":
        wins = sum(1 for j in journals if j.result and j.result.value == "win")
        return wins >= criteria.get("threshold", 1)

    elif criteria_type == "trade_count":
        return len(journals) >= criteria.get("threshold", 1)

    elif criteria_type == "win_streak":
        target = criteria.get("threshold", 3)
        streak = 0
        max_streak = 0
        for j in sorted(journals, key=lambda x: x.trade_date or datetime.min):
            if j.result and j.result.value == "win":
                streak += 1
                max_streak = max(max_streak, streak)
            else:
                streak = 0
        return max_streak >= target

    elif criteria_type == "no_violations_streak":
        target = criteria.get("threshold", 10)
        streak = 0
        max_streak = 0
        for j in sorted(journals, key=lambda x: x.trade_date or datetime.min):
            if j.followed_rules and not j.rule_violations:
                streak += 1
                max_streak = max(max_streak, streak)
            else:
                streak = 0
        return max_streak >= target

    elif criteria_type == "level_reached":
        return character.level >= criteria.get("threshold", 10)

    elif criteria_type == "attribute_score":
        attr = criteria.get("attribute")
        threshold = criteria.get("threshold", 80)
        if attr and hasattr(character, attr):
            return getattr(character, attr) >= threshold

    elif criteria_type == "win_rate":
        if len(journals) < criteria.get("min_trades", 10):
            return False
        wins = sum(1 for j in journals if j.result and j.result.value == "win")
        return (wins / len(journals) * 100) >= criteria.get("threshold", 60)

    elif criteria_type == "profit_total":
        total_pnl = sum(j.pnl_amount or 0 for j in journals)
        return total_pnl >= criteria.get("threshold", 1000)

    elif criteria_type == "stop_loss_rate":
        if not journals:
            return False
        sl_set = sum(1 for j in journals if j.stop_loss is not None)
        return (sl_set / len(journals) * 100) >= criteria.get("threshold", 90)

    elif criteria_type == "daily_journal":
        # Check if user journaled for N consecutive days
        target = criteria.get("threshold", 7)
        dates = sorted(set(
            (j.trade_date.date() if hasattr(j.trade_date, 'date') else j.trade_date)
            for j in journals if j.trade_date and j.notes
        ))
        if len(dates) < target:
            return False
        streak = 1
        max_streak = 1
        for i in range(1, len(dates)):
            if (dates[i] - dates[i - 1]).days == 1:
                streak += 1
                max_streak = max(max_streak, streak)
            else:
                streak = 1
        return max_streak >= target

    return False
