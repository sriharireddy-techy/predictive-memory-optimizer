"""
Analysis module: calculates memory growth rates and persistence (Phase 3).
"""

from src.analysis.trend_analyzer import (
    TrendClassification,
    ProcessTrend,
    SystemTrend,
    MemoryTrendAnalyzer,
    compute_linear_slope,
    calculate_persistence,
)
from src.analysis.service import analyze_active_processes, analyze_system_trend

__all__ = [
    "TrendClassification",
    "ProcessTrend",
    "SystemTrend",
    "MemoryTrendAnalyzer",
    "compute_linear_slope",
    "calculate_persistence",
    "analyze_active_processes",
    "analyze_system_trend",
]
