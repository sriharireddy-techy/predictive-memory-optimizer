"""
Phase 7: Dashboard Component & Visualization Regression Tests.

Validates the correctness of KPI rendering, chart generation,
data filtering, and recommendation displays under various edge cases.
"""

import pytest
import time
from typing import Dict, Any, List

from src.dashboard.components import (
    format_timestamp,
    get_pressure_color,
    get_urgency_badge_class,
)
from src.dashboard.charts import (
    create_historical_ram_chart,
    create_forecast_chart,
    create_process_memory_bar_chart,
)
from src.dashboard.styles import get_custom_css
from src.detection.growth_detector import AbnormalProcessGrowth, GrowthFlag, GrowthSeverity
from src.detection.impact_scorer import ImpactWeights, ProcessImpact
from src.detection.pressure_analyzer import PressureState, SystemPressure
from src.detection.service import DetectionReport
from src.prediction.forecaster import (
    ForecastPoint,
    PressureForecast,
    ThresholdBreachEstimate,
    TrajectoryState,
)
from src.optimization.recommendation_engine import (
    ActionRecommendation,
    ActionType,
    OptimizationPlan,
    RiskPriority,
)


def test_format_timestamp():
    """Verify epoch timestamp is properly formatted into HH:MM:SS."""
    ts = 1700000000.0
    result = format_timestamp(ts)
    assert isinstance(result, str)
    parts = result.split(":")
    assert len(parts) == 3


def test_get_pressure_color():
    """Verify color mappings for pressure states."""
    assert get_pressure_color("NORMAL") == "#00FFFF"
    assert get_pressure_color("MODERATE") == "#FFC107"
    assert get_pressure_color("HIGH") == "#FF9800"
    assert get_pressure_color("CRITICAL") == "#F44336"
    assert get_pressure_color("UNKNOWN") == "white"


def test_get_urgency_badge_class():
    """Verify badge CSS class generation."""
    assert get_urgency_badge_class("CRITICAL") == "badge-critical"
    assert get_urgency_badge_class("ALREADY BREACHED") == "badge-critical"
    assert get_urgency_badge_class("HIGH") == "badge-high"
    assert get_urgency_badge_class("MODERATE") == "badge-moderate"
    assert get_urgency_badge_class("NORMAL") == "badge-normal"
    assert get_urgency_badge_class("STABLE") == "badge-normal"


def test_styles_css_generation():
    """Verify CSS style string generation."""
    css = get_custom_css()
    assert isinstance(css, str)
    assert "<style>" in css
    assert "--bg-primary" in css
    assert "metric-card" in css


def test_historical_chart_empty_and_populated():
    """Verify historical chart handles empty and populated datasets."""
    # Empty data
    fig_empty = create_historical_ram_chart([])
    assert fig_empty is not None
    assert len(fig_empty.data) == 0

    # Populated data
    sample_data = [
        {"timestamp": 1000.0, "percent_used": 50.0, "used_ram_mb": 8000.0, "available_ram_mb": 8000.0, "total_ram_mb": 16000.0},
        {"timestamp": 1010.0, "percent_used": 55.0, "used_ram_mb": 8800.0, "available_ram_mb": 7200.0, "total_ram_mb": 16000.0},
        {"timestamp": 1020.0, "percent_used": 60.0, "used_ram_mb": 9600.0, "available_ram_mb": 6400.0, "total_ram_mb": 16000.0},
    ]
    fig = create_historical_ram_chart(sample_data)
    assert fig is not None
    assert len(fig.data) >= 1
    assert fig.data[0].name == "Observed RAM (%)"


def test_forecast_chart_rendering():
    """Verify forecast chart renders observed and projected traces."""
    sample_data = [
        {"timestamp": 1000.0, "percent_used": 50.0},
        {"timestamp": 1010.0, "percent_used": 55.0},
    ]
    warning_breach = ThresholdBreachEstimate(
        threshold_name="Warning",
        target_value=85.0,
        current_value=55.0,
        is_already_breached=False,
        is_breach_predicted=True,
        seconds_to_breach=60.0,
        breach_timestamp=1070.0,
        explanation="Warning predicted in 60s",
    )
    critical_breach = ThresholdBreachEstimate(
        threshold_name="Critical",
        target_value=92.0,
        current_value=55.0,
        is_already_breached=False,
        is_breach_predicted=False,
        seconds_to_breach=None,
        breach_timestamp=None,
        explanation="No critical breach predicted",
    )
    projections = [
        ForecastPoint(timestamp=1040.0, horizon_seconds=30.0, projected_ram_percent=60.0, projected_available_mb=6400.0, projected_used_mb=9600.0),
        ForecastPoint(timestamp=1070.0, horizon_seconds=60.0, projected_ram_percent=65.0, projected_available_mb=5600.0, projected_used_mb=10400.0),
    ]
    forecast = PressureForecast(
        timestamp=1010.0,
        current_percent=55.0,
        current_available_mb=7200.0,
        current_used_mb=8800.0,
        total_ram_mb=16000.0,
        rate_percent_s=0.5,
        rate_used_mb_s=80.0,
        r_squared=0.98,
        confidence_score=0.95,
        trajectory=TrajectoryState.RAPID_INCREASE,
        projections=projections,
        warning_breach=warning_breach,
        critical_breach=critical_breach,
        explanation="Rapid increase detected.",
    )

    fig = create_forecast_chart(sample_data, forecast)
    assert fig is not None
    # Check trace count: 1 observed, 1 projected
    assert len(fig.data) == 2
    assert fig.data[0].name == "Observed Telemetry"
    assert "Projections" in fig.data[1].name


def test_forecast_chart_already_breached():
    """Verify forecast chart renders already breached state correctly."""
    sample_data = [{"timestamp": 1000.0, "percent_used": 95.0}]
    critical_breach = ThresholdBreachEstimate(
        threshold_name="Critical",
        target_value=92.0,
        current_value=95.0,
        is_already_breached=True,
        is_breach_predicted=True,
        seconds_to_breach=0.0,
        breach_timestamp=1000.0,
        explanation="Critical actively breached.",
    )
    forecast = PressureForecast(
        timestamp=1000.0,
        current_percent=95.0,
        current_available_mb=500.0,
        current_used_mb=15500.0,
        total_ram_mb=16000.0,
        rate_percent_s=0.0,
        rate_used_mb_s=0.0,
        r_squared=0.0,
        confidence_score=0.0,
        trajectory=TrajectoryState.STABLE,
        projections=[],
        warning_breach=critical_breach,
        critical_breach=critical_breach,
        explanation="Actively breached.",
    )

    fig = create_forecast_chart(sample_data, forecast)
    assert fig is not None
    assert len(fig.layout.annotations) >= 1


def test_process_memory_bar_chart():
    """Verify top processes bar chart generation."""
    weights = ImpactWeights()
    impacts = [
        ProcessImpact(
            pid=1234,
            name="chrome.exe",
            rank=1,
            impact_score=0.85,
            current_rss_mb=2048.0,
            growth_rate_mb_s=5.0,
            persistence_score=0.9,
            normalized_memory=0.8,
            normalized_growth=0.9,
            normalized_persistence=0.9,
            weights=weights,
            explanation="High memory consumer",
        ),
        ProcessImpact(
            pid=5678,
            name="code.exe",
            rank=2,
            impact_score=0.45,
            current_rss_mb=1024.0,
            growth_rate_mb_s=1.0,
            persistence_score=0.5,
            normalized_memory=0.4,
            normalized_growth=0.5,
            normalized_persistence=0.5,
            weights=weights,
            explanation="Moderate consumer",
        ),
    ]

    fig = create_process_memory_bar_chart(impacts)
    assert fig is not None
    assert len(fig.data) == 1
