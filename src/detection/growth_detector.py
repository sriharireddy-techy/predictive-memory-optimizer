"""
Phase 4: Abnormal Process Memory Growth Detector.

Detects abnormal, sustained, or rapid memory expansion patterns in individual
processes based on statistical behavior over time:
1. Sustained growth persistence (unbounded accumulation vs. transient caches).
2. Growth velocity (rapid expansion vs. slow baseline increments).
3. Memory footprint magnitude (high absolute RAM impact).
4. Distinguishing transient spikes from persistent expansion.
"""

from dataclasses import dataclass, asdict
from enum import Enum
from typing import Any, Dict, List, Optional

from src.analysis.trend_analyzer import ProcessTrend, TrendClassification


class GrowthSeverity(str, Enum):
    """Severity classification for process memory growth."""
    NONE = "NONE"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class GrowthFlag(str, Enum):
    """Categorical indicators for abnormal memory patterns."""
    STABLE = "STABLE"
    SUSTAINED_GROWTH = "SUSTAINED_GROWTH"
    RAPID_GROWTH = "RAPID_GROWTH"
    LARGE_FOOTPRINT_GROWING = "LARGE_FOOTPRINT_GROWING"
    TRANSIENT_SPIKE = "TRANSIENT_SPIKE"
    GRADUAL_GROWTH = "GRADUAL_GROWTH"


@dataclass(frozen=True)
class GrowthDetectionConfig:
    """Configurable criteria for abnormal growth detection."""
    min_growth_rate_mb_s: float = 0.05
    sustained_persistence_threshold: float = 0.70
    rapid_growth_rate_mb_s: float = 5.0
    critical_growth_rate_mb_s: float = 15.0
    large_footprint_mb: float = 1024.0
    critical_footprint_mb: float = 4096.0


@dataclass(frozen=True)
class AbnormalProcessGrowth:
    """Detailed evaluation of anomalous memory behavior for a process."""
    pid: int
    name: str
    is_abnormal: bool
    severity: GrowthSeverity
    flags: List[GrowthFlag]
    growth_rate_mb_s: float
    persistence_score: float
    current_rss_mb: float
    net_change_mb: float
    reasons: List[str]
    explanation: str

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["severity"] = self.severity.value
        d["flags"] = [f.value for f in self.flags]
        return d


class AbnormalGrowthDetector:
    """
    Evaluates process memory trends to detect anomalous growth patterns
    and assign explainable severity levels.
    """

    def __init__(self, config: Optional[GrowthDetectionConfig] = None):
        self.config = config or GrowthDetectionConfig()

    def evaluate_process(
        self,
        trend: ProcessTrend,
        current_rss_mb: Optional[float] = None,
    ) -> AbnormalProcessGrowth:
        """
        Evaluate a single process trend for abnormal memory expansion.

        Args:
            trend: Statistical process trend from Phase 3 analysis.
            current_rss_mb: Optional current RSS memory (defaults to trend.end_memory_mb).

        Returns:
            AbnormalProcessGrowth: Detailed classification, flags, and severity.
        """
        rss = current_rss_mb if current_rss_mb is not None else trend.end_memory_mb
        rate = trend.growth_rate_mb_s
        persistence = trend.persistence_score
        net_change = trend.net_change_mb

        # If data is insufficient or process is stable/shrinking
        if (
            trend.classification == TrendClassification.INSUFFICIENT_DATA
            or trend.classification == TrendClassification.STABLE
            or (rate <= self.config.min_growth_rate_mb_s and net_change <= 0)
        ):
            return AbnormalProcessGrowth(
                pid=trend.pid,
                name=trend.name,
                is_abnormal=False,
                severity=GrowthSeverity.NONE,
                flags=[GrowthFlag.STABLE],
                growth_rate_mb_s=round(rate, 4),
                persistence_score=round(persistence, 4),
                current_rss_mb=round(rss, 2),
                net_change_mb=round(net_change, 2),
                reasons=["Memory behavior is stable or negative across the observation period."],
                explanation=f"Process {trend.name} (PID {trend.pid}) exhibits normal, non-expanding memory consumption.",
            )

        flags: List[GrowthFlag] = []
        reasons: List[str] = []

        is_sustained = (
            persistence >= self.config.sustained_persistence_threshold
            and net_change > 0
            and rate >= self.config.min_growth_rate_mb_s
        )
        is_rapid = rate >= self.config.rapid_growth_rate_mb_s
        is_large_footprint = rss >= self.config.large_footprint_mb and rate > self.config.min_growth_rate_mb_s
        is_transient = is_rapid and persistence < 0.50

        if is_transient:
            flags.append(GrowthFlag.TRANSIENT_SPIKE)
            reasons.append(
                f"Transient memory burst observed (+{rate:.2f} MB/s) with low persistence ({persistence * 100:.1f}%)."
            )
        elif is_rapid:
            flags.append(GrowthFlag.RAPID_GROWTH)
            reasons.append(
                f"Rapid growth velocity (+{rate:.2f} MB/s, exceeds rapid threshold of {self.config.rapid_growth_rate_mb_s:.1f} MB/s)."
            )

        if is_sustained:
            flags.append(GrowthFlag.SUSTAINED_GROWTH)
            reasons.append(
                f"Sustained monotonic expansion ({persistence * 100:.1f}% positive growth intervals, net change +{net_change:.1f} MB)."
            )
        elif not is_rapid and rate > self.config.min_growth_rate_mb_s and net_change > 0:
            flags.append(GrowthFlag.GRADUAL_GROWTH)
            reasons.append(
                f"Gradual upward drift (+{rate:.2f} MB/s, net change +{net_change:.1f} MB)."
            )

        if is_large_footprint:
            flags.append(GrowthFlag.LARGE_FOOTPRINT_GROWING)
            reasons.append(
                f"Substantial existing memory footprint ({rss:.1f} MB) currently undergoing expansion."
            )

        # Determine Severity Level
        if is_transient:
            severity = GrowthSeverity.LOW
        elif (
            rate >= self.config.critical_growth_rate_mb_s
            or (rss >= self.config.critical_footprint_mb and is_sustained)
            or (is_rapid and persistence >= 0.80)
        ):
            severity = GrowthSeverity.CRITICAL
        elif (
            is_rapid
            or (is_sustained and rss >= self.config.large_footprint_mb)
            or (is_sustained and rate >= 1.0)
        ):
            severity = GrowthSeverity.HIGH
        elif is_sustained or (rate >= 0.5 and net_change >= 20.0):
            severity = GrowthSeverity.MEDIUM
        elif rate > self.config.min_growth_rate_mb_s:
            severity = GrowthSeverity.LOW
        else:
            severity = GrowthSeverity.NONE

        is_abnormal = severity in (GrowthSeverity.MEDIUM, GrowthSeverity.HIGH, GrowthSeverity.CRITICAL)

        explanation = (
            f"Process {trend.name} (PID {trend.pid}) assessed with {severity.value} growth severity "
            f"(Rate: +{rate:.2f} MB/s, Persistence: {persistence * 100:.1f}%, RSS: {rss:.1f} MB). "
            + " ".join(reasons)
        )

        return AbnormalProcessGrowth(
            pid=trend.pid,
            name=trend.name,
            is_abnormal=is_abnormal,
            severity=severity,
            flags=flags,
            growth_rate_mb_s=round(rate, 4),
            persistence_score=round(persistence, 4),
            current_rss_mb=round(rss, 2),
            net_change_mb=round(net_change, 2),
            reasons=reasons,
            explanation=explanation,
        )

    def evaluate_processes(
        self,
        trends: List[ProcessTrend],
    ) -> List[AbnormalProcessGrowth]:
        """
        Evaluate a collection of process trends.

        Returns:
            List of AbnormalProcessGrowth sorted by severity descending and growth rate descending.
        """
        severity_order = {
            GrowthSeverity.CRITICAL: 4,
            GrowthSeverity.HIGH: 3,
            GrowthSeverity.MEDIUM: 2,
            GrowthSeverity.LOW: 1,
            GrowthSeverity.NONE: 0,
        }

        results = [self.evaluate_process(t) for t in trends]
        results.sort(
            key=lambda a: (severity_order.get(a.severity, 0), a.growth_rate_mb_s, a.current_rss_mb),
            reverse=True,
        )
        return results
