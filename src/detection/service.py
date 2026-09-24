"""
Phase 4 Service: Comprehensive Memory Pressure and Process Impact Assessment.

Integrates:
- System Memory Pressure Analyzer
- Abnormal Growth Pattern Detector
- Composite Process Impact Scorer
With historical storage (MetricsDatabase) and time-series trend analysis (Phase 3).
"""

from dataclasses import dataclass, asdict
import time
from typing import Any, Dict, List, Optional

from src.analysis.service import analyze_active_processes, analyze_system_trend
from src.analysis.trend_analyzer import ProcessTrend, SystemTrend, MemoryTrendAnalyzer
from src.collector.monitor import SystemMetrics
from src.detection.growth_detector import (
    AbnormalGrowthDetector,
    AbnormalProcessGrowth,
    GrowthDetectionConfig,
)
from src.detection.impact_scorer import (
    ImpactWeights,
    ProcessImpact,
    ProcessImpactScorer,
)
from src.detection.pressure_analyzer import (
    MemoryPressureAnalyzer,
    PressureState,
    PressureThresholds,
    SystemPressure,
)
from src.storage.database import MetricsDatabase


@dataclass(frozen=True)
class DetectionReport:
    """Consolidated memory pressure and process impact evaluation report."""
    timestamp: float
    system_pressure: SystemPressure
    system_trend: Optional[SystemTrend]
    abnormal_processes: List[AbnormalProcessGrowth]
    ranked_impact_scores: List[ProcessImpact]

    @property
    def highest_impact_process(self) -> Optional[ProcessImpact]:
        """Return the #1 ranked contributor to memory pressure, if any."""
        return self.ranked_impact_scores[0] if self.ranked_impact_scores else None

    @property
    def critical_growth_processes(self) -> List[AbnormalProcessGrowth]:
        """Return processes marked with abnormal growth behavior."""
        return [p for p in self.abnormal_processes if p.is_abnormal]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "system_pressure": self.system_pressure.to_dict(),
            "system_trend": self.system_trend.to_dict() if self.system_trend else None,
            "abnormal_processes": [p.to_dict() for p in self.abnormal_processes],
            "ranked_impact_scores": [i.to_dict() for i in self.ranked_impact_scores],
            "highest_impact_process": (
                self.highest_impact_process.to_dict() if self.highest_impact_process else None
            ),
        }


def assess_system_pressure(
    system_metrics: SystemMetrics,
    system_trend: Optional[SystemTrend] = None,
    thresholds: Optional[PressureThresholds] = None,
) -> SystemPressure:
    """Convenience helper to evaluate system memory pressure."""
    analyzer = MemoryPressureAnalyzer(thresholds=thresholds)
    return analyzer.evaluate(system_metrics, system_trend=system_trend)


def detect_abnormal_processes(
    trends: List[ProcessTrend],
    config: Optional[GrowthDetectionConfig] = None,
) -> List[AbnormalProcessGrowth]:
    """Convenience helper to detect abnormal process growth patterns."""
    detector = AbnormalGrowthDetector(config=config)
    return detector.evaluate_processes(trends)


def score_process_impacts(
    trends: List[ProcessTrend],
    total_ram_mb: Optional[float] = None,
    weights: Optional[ImpactWeights] = None,
    reference_growth_rate_mb_s: float = 10.0,
) -> List[ProcessImpact]:
    """Convenience helper to score and rank process memory impact."""
    scorer = ProcessImpactScorer(
        weights=weights,
        reference_growth_rate_mb_s=reference_growth_rate_mb_s,
    )
    return scorer.score_cohort(trends, total_ram_mb=total_ram_mb)


def run_detection(
    db: MetricsDatabase,
    window_seconds: float = 60.0,
    pressure_thresholds: Optional[PressureThresholds] = None,
    growth_config: Optional[GrowthDetectionConfig] = None,
    impact_weights: Optional[ImpactWeights] = None,
    trend_analyzer: Optional[MemoryTrendAnalyzer] = None,
) -> DetectionReport:
    """
    Execute full Phase 4 assessment against historical database records:
    1. Query and analyze system-wide memory trends.
    2. Query and analyze individual process memory trends.
    3. Evaluate system memory pressure state.
    4. Detect abnormal growth behaviors across all active processes.
    5. Score and rank processes by composite impact.

    Args:
        db: Active MetricsDatabase instance.
        window_seconds: Historical window in seconds to analyze.
        pressure_thresholds: Custom pressure classification thresholds.
        growth_config: Custom abnormal growth criteria.
        impact_weights: Custom weights for composite impact scoring.
        trend_analyzer: Custom MemoryTrendAnalyzer instance.

    Returns:
        DetectionReport: Complete, serialized assessment summary.
    """
    current_time = time.time()

    # 1. Analyze historical trends
    process_trends = analyze_active_processes(
        db=db,
        window_seconds=window_seconds,
        analyzer=trend_analyzer,
    )
    sys_trend = analyze_system_trend(
        db=db,
        window_seconds=window_seconds,
        analyzer=trend_analyzer,
    )

    # 2. Retrieve latest instantaneous system telemetry from DB
    latest_sys_records = db.get_system_history(limit=1)
    if latest_sys_records:
        r = latest_sys_records[0]
        latest_sys_metrics = SystemMetrics(
            timestamp=float(r["timestamp"]),
            total_ram_mb=float(r["total_ram_mb"]),
            available_ram_mb=float(r["available_ram_mb"]),
            used_ram_mb=float(r["used_ram_mb"]),
            percent_used=float(r["percent_used"]),
            swap_total_mb=float(r.get("swap_total_mb", 0.0) or 0.0),
            swap_used_mb=float(r.get("swap_used_mb", 0.0) or 0.0),
            swap_percent=float(r.get("swap_percent", 0.0) or 0.0),
        )
    else:
        # Fallback empty metrics if no historical record is found
        latest_sys_metrics = SystemMetrics(
            timestamp=current_time,
            total_ram_mb=16384.0,
            available_ram_mb=16384.0,
            used_ram_mb=0.0,
            percent_used=0.0,
            swap_total_mb=0.0,
            swap_used_mb=0.0,
            swap_percent=0.0,
        )

    # 3. Evaluate System Memory Pressure
    pressure = assess_system_pressure(
        system_metrics=latest_sys_metrics,
        system_trend=sys_trend,
        thresholds=pressure_thresholds,
    )

    # 4. Detect Abnormal Process Growth Patterns
    abnormal = detect_abnormal_processes(
        trends=process_trends,
        config=growth_config,
    )

    # 5. Calculate Composite Process Impact Scores
    ranked_impacts = score_process_impacts(
        trends=process_trends,
        total_ram_mb=latest_sys_metrics.total_ram_mb,
        weights=impact_weights,
    )

    return DetectionReport(
        timestamp=current_time,
        system_pressure=pressure,
        system_trend=sys_trend,
        abnormal_processes=abnormal,
        ranked_impact_scores=ranked_impacts,
    )
