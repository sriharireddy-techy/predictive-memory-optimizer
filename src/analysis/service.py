"""
Phase 3 Service: Batch Analysis of Active Processes from Historical Storage.
"""

from typing import List, Optional
from src.storage.database import MetricsDatabase
from src.analysis.trend_analyzer import (
    MemoryTrendAnalyzer,
    ProcessTrend,
    SystemTrend,
)


def analyze_active_processes(
    db: MetricsDatabase,
    window_seconds: float = 60.0,
    analyzer: Optional[MemoryTrendAnalyzer] = None,
) -> List[ProcessTrend]:
    """
    Evaluate memory trends for all processes active within the specified time window.

    Args:
        db: Active MetricsDatabase instance.
        window_seconds: Historical window in seconds to analyze.
        analyzer: Optional custom MemoryTrendAnalyzer instance.

    Returns:
        List[ProcessTrend]: Analyzed processes, sorted by growth rate descending.
    """
    if analyzer is None:
        analyzer = MemoryTrendAnalyzer()

    active_pids = db.get_active_pids_in_window(window_seconds=window_seconds)
    results: List[ProcessTrend] = []

    for pid in active_pids:
        history = db.get_process_history(pid=pid)
        trend = analyzer.analyze_process(history, pid=pid)
        results.append(trend)

    # Sort descending by growth rate so rapidly expanding processes appear first
    results.sort(key=lambda t: t.growth_rate_mb_s, reverse=True)
    return results


def analyze_system_trend(
    db: MetricsDatabase,
    window_seconds: float = 60.0,
    analyzer: Optional[MemoryTrendAnalyzer] = None,
) -> SystemTrend:
    """
    Evaluate system memory utilization trend within the specified time window.
    """
    if analyzer is None:
        analyzer = MemoryTrendAnalyzer()

    history = db.get_system_history()
    return analyzer.analyze_system(history)
