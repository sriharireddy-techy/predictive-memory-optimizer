"""
Phase 4: System Memory Pressure Analyzer.

Evaluates system-wide memory stress by synthesizing:
1. Current physical RAM utilization (%) and remaining available memory (MB).
2. Swap space consumption (%) and paging activity.
3. System memory velocity (rate of increase in % RAM per second).
4. Explainable classification: NORMAL, MODERATE, HIGH, or CRITICAL.
"""

from dataclasses import dataclass, asdict
from enum import Enum
import time
from typing import Any, Dict, List, Optional

from src.analysis.trend_analyzer import SystemTrend, TrendClassification
from src.collector.monitor import SystemMetrics


class PressureState(str, Enum):
    """Explainable categories for host memory pressure."""
    NORMAL = "NORMAL"
    MODERATE = "MODERATE"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


@dataclass(frozen=True)
class PressureThresholds:
    """Configurable thresholds for classifying system memory pressure."""
    normal_max_percent: float = 70.0
    moderate_max_percent: float = 85.0
    high_max_percent: float = 92.0
    critical_available_ram_mb: float = 500.0
    moderate_swap_percent: float = 25.0
    high_swap_percent: float = 50.0
    critical_swap_percent: float = 80.0
    rapid_growth_rate_percent_s: float = 0.20  # Rate of RAM % increase per second


@dataclass(frozen=True)
class SystemPressure:
    """Holistic assessment of system-wide memory pressure."""
    timestamp: float
    state: PressureState
    score: float  # Composite pressure index from 0.0 to 100.0
    ram_used_percent: float
    available_ram_mb: float
    total_ram_mb: float
    used_ram_mb: float
    swap_used_percent: float
    swap_used_mb: float
    rate_percent_s: float
    contributing_factors: List[str]
    explanation: str

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["state"] = self.state.value
        return d


class MemoryPressureAnalyzer:
    """
    Evaluates instantaneous telemetry and temporal trend metrics
    to compute an explainable system memory pressure score and state.
    """

    def __init__(self, thresholds: Optional[PressureThresholds] = None):
        self.thresholds = thresholds or PressureThresholds()

    def evaluate(
        self,
        system_metrics: SystemMetrics,
        system_trend: Optional[SystemTrend] = None,
    ) -> SystemPressure:
        """
        Evaluate memory pressure given current system metrics and optional trend.

        Args:
            system_metrics: Instantaneous telemetry from collector or storage.
            system_trend: Optional historical trend analysis over time window.

        Returns:
            SystemPressure: Composite pressure assessment with explanation.
        """
        ram_pct = max(0.0, min(100.0, system_metrics.percent_used))
        swap_pct = max(0.0, min(100.0, system_metrics.swap_percent))
        avail_mb = max(0.0, system_metrics.available_ram_mb)
        total_mb = max(0.0, system_metrics.total_ram_mb)
        used_mb = max(0.0, system_metrics.used_ram_mb)
        swap_used_mb = max(0.0, system_metrics.swap_used_mb)

        rate_s = 0.0
        if system_trend is not None and system_trend.classification != TrendClassification.INSUFFICIENT_DATA:
            rate_s = system_trend.rate_percent_s

        # 1. Calculate Continuous Composite Pressure Score [0.0 - 100.0]
        # Formulation:
        # Base RAM: up to 75 points (ram_pct * 0.75)
        # Swap usage: up to 15 points (swap_pct * 0.15)
        # Velocity penalty: up to 10 points for positive growth rate
        ram_component = ram_pct * 0.75
        swap_component = swap_pct * 0.15

        # Velocity contribution: 0.5% per sec -> 10 points
        velocity_component = 0.0
        if rate_s > 0:
            velocity_component = min(10.0, rate_s * 20.0)

        composite_score = round(min(100.0, ram_component + swap_component + velocity_component), 2)

        # 2. Determine State and Collect Contributing Factors
        factors: List[str] = []

        is_critical = False
        is_high = False
        is_moderate = False

        # Available RAM checks
        if avail_mb <= self.thresholds.critical_available_ram_mb:
            is_critical = True
            factors.append(
                f"Critically low available physical RAM ({avail_mb:.1f} MB remaining, threshold {self.thresholds.critical_available_ram_mb:.1f} MB)"
            )

        # RAM utilization checks
        if ram_pct >= self.thresholds.high_max_percent:
            is_critical = True
            factors.append(
                f"Extremely high RAM utilization ({ram_pct:.1f}%, critical threshold {self.thresholds.high_max_percent:.1f}%)"
            )
        elif ram_pct >= self.thresholds.moderate_max_percent:
            is_high = True
            factors.append(
                f"High RAM utilization ({ram_pct:.1f}%, warning threshold {self.thresholds.moderate_max_percent:.1f}%)"
            )
        elif ram_pct >= self.thresholds.normal_max_percent:
            is_moderate = True
            factors.append(
                f"Elevated RAM utilization ({ram_pct:.1f}%, moderate threshold {self.thresholds.normal_max_percent:.1f}%)"
            )

        # Swap utilization checks
        if swap_pct >= self.thresholds.critical_swap_percent:
            is_critical = True
            factors.append(
                f"Critical swap exhaustion ({swap_pct:.1f}%, critical threshold {self.thresholds.critical_swap_percent:.1f}%)"
            )
        elif swap_pct >= self.thresholds.high_swap_percent:
            is_high = True
            factors.append(
                f"High swap paging activity ({swap_pct:.1f}%, threshold {self.thresholds.high_swap_percent:.1f}%)"
            )
        elif swap_pct >= self.thresholds.moderate_swap_percent:
            is_moderate = True
            factors.append(
                f"Moderate swap usage ({swap_pct:.1f}%, threshold {self.thresholds.moderate_swap_percent:.1f}%)"
            )

        # Velocity checks
        if rate_s >= self.thresholds.rapid_growth_rate_percent_s:
            factors.append(
                f"Rapid upward memory trajectory (+{rate_s:.3f}%/s)"
            )
            # Velocity escalation: escalate Moderate to High, or High to Critical
            if is_high or ram_pct >= self.thresholds.moderate_max_percent:
                is_critical = True
            elif is_moderate or ram_pct >= self.thresholds.normal_max_percent:
                is_high = True
            else:
                is_moderate = True

        # Score checks
        if composite_score >= 90.0:
            is_critical = True
        elif composite_score >= 75.0 and not is_critical:
            is_high = True
        elif composite_score >= 55.0 and not is_critical and not is_high:
            is_moderate = True

        # Resolve final State
        if is_critical:
            state = PressureState.CRITICAL
        elif is_high:
            state = PressureState.HIGH
        elif is_moderate:
            state = PressureState.MODERATE
        else:
            state = PressureState.NORMAL
            if not factors:
                factors.append("System memory consumption is within healthy nominal thresholds.")

        explanation = (
            f"System memory pressure is {state.value} (Score: {composite_score}/100). "
            f"RAM Used: {ram_pct:.1f}% ({used_mb:.1f} MB / {total_mb:.1f} MB), "
            f"Available: {avail_mb:.1f} MB, Swap: {swap_pct:.1f}%. "
            + "; ".join(factors)
        )

        return SystemPressure(
            timestamp=system_metrics.timestamp,
            state=state,
            score=composite_score,
            ram_used_percent=round(ram_pct, 2),
            available_ram_mb=round(avail_mb, 2),
            total_ram_mb=round(total_mb, 2),
            used_ram_mb=round(used_mb, 2),
            swap_used_percent=round(swap_pct, 2),
            swap_used_mb=round(swap_used_mb, 2),
            rate_percent_s=round(rate_s, 4),
            contributing_factors=factors,
            explanation=explanation,
        )
