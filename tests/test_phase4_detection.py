"""
Phase 4 Tests: Memory Pressure and Process Impact Scoring Component.

Test coverage:
1. MemoryPressureAnalyzer:
   - Normal pressure conditions.
   - Moderate pressure thresholds.
   - High pressure warnings.
   - Critical saturation (RAM %, low available RAM, swap exhaustion).
   - Upward velocity trajectory escalation.
   - Serialization to dict.
2. AbnormalGrowthDetector:
   - Stable processes (severity NONE, not abnormal).
   - Sustained growth processes (SUSTAINED_GROWTH flag).
   - Rapid expansion processes (RAPID_GROWTH flag).
   - Transient spikes (burst rate with low persistence).
   - Large footprint undergoing expansion (LARGE_FOOTPRINT_GROWING flag).
   - Negative growth (shrinking footprint).
3. ProcessImpactScorer:
   - Weight constraints validation (sum to 1.0, non-negative).
   - Component normalization guarantees (M_hat, G_hat, P in [0.0, 1.0]).
   - Single process evaluation.
   - Cohort scoring and relative ranking order.
   - Mathematical formulation verification (w1*M + w2*G + w3*P).
   - Custom weight configuration.
4. Integrated Detection Service:
   - End-to-end integration with MetricsDatabase historical data.
   - DetectionReport serialization and properties.
   - Graceful handling of empty or minimal historical data.
"""

import time
import pytest

from src.analysis.trend_analyzer import ProcessTrend, SystemTrend, TrendClassification
from src.collector.monitor import SystemMetrics, ProcessMetrics, SystemSnapshot
from src.detection.growth_detector import (
    AbnormalGrowthDetector,
    AbnormalProcessGrowth,
    GrowthDetectionConfig,
    GrowthFlag,
    GrowthSeverity,
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
from src.detection.service import (
    DetectionReport,
    assess_system_pressure,
    detect_abnormal_processes,
    run_detection,
    score_process_impacts,
)
from src.storage.database import MetricsDatabase


# ============================================================================
# 1. Memory Pressure Analyzer Tests
# ============================================================================

def test_pressure_normal_state():
    """Verify normal pressure when RAM and swap usage are comfortably low."""
    analyzer = MemoryPressureAnalyzer()
    sys_metrics = SystemMetrics(
        timestamp=1000.0,
        total_ram_mb=16384.0,
        available_ram_mb=10000.0,
        used_ram_mb=6384.0,
        percent_used=39.0,
        swap_total_mb=4096.0,
        swap_used_mb=200.0,
        swap_percent=4.8,
    )
    pressure = analyzer.evaluate(sys_metrics)

    assert pressure.state == PressureState.NORMAL
    assert pressure.score < 55.0
    assert pressure.ram_used_percent == 39.0
    assert "NORMAL" in pressure.explanation


def test_pressure_moderate_state():
    """Verify moderate pressure when RAM is in the 70%-85% bracket."""
    analyzer = MemoryPressureAnalyzer()
    sys_metrics = SystemMetrics(
        timestamp=1000.0,
        total_ram_mb=16384.0,
        available_ram_mb=4000.0,
        used_ram_mb=12384.0,
        percent_used=75.5,
        swap_total_mb=4096.0,
        swap_used_mb=400.0,
        swap_percent=9.7,
    )
    pressure = analyzer.evaluate(sys_metrics)

    assert pressure.state == PressureState.MODERATE
    assert 50.0 <= pressure.score < 80.0


def test_pressure_high_state():
    """Verify high pressure when RAM exceeds 85%."""
    analyzer = MemoryPressureAnalyzer()
    sys_metrics = SystemMetrics(
        timestamp=1000.0,
        total_ram_mb=16384.0,
        available_ram_mb=1800.0,
        used_ram_mb=14584.0,
        percent_used=89.0,
        swap_total_mb=4096.0,
        swap_used_mb=1500.0,
        swap_percent=36.6,
    )
    pressure = analyzer.evaluate(sys_metrics)

    assert pressure.state == PressureState.HIGH
    assert pressure.score >= 70.0


def test_pressure_critical_on_ram_saturation():
    """Verify critical pressure when RAM exceeds 92%."""
    analyzer = MemoryPressureAnalyzer()
    sys_metrics = SystemMetrics(
        timestamp=1000.0,
        total_ram_mb=16384.0,
        available_ram_mb=800.0,
        used_ram_mb=15584.0,
        percent_used=95.1,
        swap_total_mb=4096.0,
        swap_used_mb=2000.0,
        swap_percent=48.8,
    )
    pressure = analyzer.evaluate(sys_metrics)

    assert pressure.state == PressureState.CRITICAL
    assert pressure.score >= 70.0


def test_pressure_critical_on_critically_low_available_ram():
    """Verify critical state triggers if remaining RAM is < 500 MB even if % is below 92%."""
    analyzer = MemoryPressureAnalyzer()
    sys_metrics = SystemMetrics(
        timestamp=1000.0,
        total_ram_mb=4096.0,
        available_ram_mb=350.0,  # Below 500 MB threshold
        used_ram_mb=3746.0,
        percent_used=91.4,
        swap_total_mb=2048.0,
        swap_used_mb=500.0,
        swap_percent=24.4,
    )
    pressure = analyzer.evaluate(sys_metrics)

    assert pressure.state == PressureState.CRITICAL
    assert any("Critically low available physical RAM" in factor for factor in pressure.contributing_factors)


def test_pressure_critical_on_swap_exhaustion():
    """Verify critical state triggers if swap usage reaches severe paging threshold (80%+)."""
    analyzer = MemoryPressureAnalyzer()
    sys_metrics = SystemMetrics(
        timestamp=1000.0,
        total_ram_mb=16384.0,
        available_ram_mb=2500.0,
        used_ram_mb=13884.0,
        percent_used=84.7,
        swap_total_mb=8192.0,
        swap_used_mb=7000.0,
        swap_percent=85.4,  # > 80% swap exhaustion
    )
    pressure = analyzer.evaluate(sys_metrics)

    assert pressure.state == PressureState.CRITICAL
    assert any("Critical swap exhaustion" in factor for factor in pressure.contributing_factors)


def test_pressure_velocity_escalation():
    """Verify rapid upward trajectory escalates moderate baseline memory to high pressure."""
    analyzer = MemoryPressureAnalyzer()
    sys_metrics = SystemMetrics(
        timestamp=1000.0,
        total_ram_mb=16384.0,
        available_ram_mb=4000.0,
        used_ram_mb=12384.0,
        percent_used=75.0,  # baseline moderate
        swap_total_mb=4096.0,
        swap_used_mb=400.0,
        swap_percent=9.7,
    )
    sys_trend = SystemTrend(
        sample_count=10,
        duration_seconds=10.0,
        start_percent=72.0,
        end_percent=75.0,
        net_change_percent=3.0,
        rate_percent_s=0.30,  # Rapid rate (+0.30% / s)
        classification=TrendClassification.RAPID_GROWTH,
        explanation="Rapid increase",
    )
    pressure = analyzer.evaluate(sys_metrics, system_trend=sys_trend)

    # Escalated from MODERATE to HIGH due to rapid growth trajectory
    assert pressure.state == PressureState.HIGH
    assert any("Rapid upward memory trajectory" in f for f in pressure.contributing_factors)


def test_pressure_serialization():
    """Verify SystemPressure correctly serializes to dictionary."""
    analyzer = MemoryPressureAnalyzer()
    sys_metrics = SystemMetrics(
        timestamp=1000.0,
        total_ram_mb=16384.0,
        available_ram_mb=8000.0,
        used_ram_mb=8384.0,
        percent_used=51.1,
        swap_total_mb=4096.0,
        swap_used_mb=100.0,
        swap_percent=2.4,
    )
    pressure = analyzer.evaluate(sys_metrics)
    d = pressure.to_dict()

    assert isinstance(d, dict)
    assert d["state"] == "NORMAL"
    assert "score" in d
    assert "ram_used_percent" in d


# ============================================================================
# 2. Abnormal Growth Detector Tests
# ============================================================================

def test_detector_stable_process():
    """Verify stable process is classified as normal with NONE severity."""
    detector = AbnormalGrowthDetector()
    trend = ProcessTrend(
        pid=101,
        name="stable_srv.exe",
        sample_count=10,
        duration_seconds=10.0,
        start_memory_mb=500.0,
        end_memory_mb=500.2,
        net_change_mb=0.2,
        growth_rate_mb_s=0.01,
        persistence_score=0.20,
        classification=TrendClassification.STABLE,
        explanation="Memory is stable",
    )
    result = detector.evaluate_process(trend)

    assert not result.is_abnormal
    assert result.severity == GrowthSeverity.NONE
    assert GrowthFlag.STABLE in result.flags


def test_detector_sustained_growth_process():
    """Verify process exhibiting high persistence is flagged with SUSTAINED_GROWTH."""
    detector = AbnormalGrowthDetector()
    trend = ProcessTrend(
        pid=202,
        name="growing_worker.exe",
        sample_count=10,
        duration_seconds=10.0,
        start_memory_mb=200.0,
        end_memory_mb=350.0,
        net_change_mb=150.0,
        growth_rate_mb_s=15.0,
        persistence_score=0.90,
        classification=TrendClassification.SUSTAINED_GROWTH,
        explanation="Memory shows strong sustained growth",
    )
    result = detector.evaluate_process(trend)

    assert result.is_abnormal
    assert result.severity in (GrowthSeverity.HIGH, GrowthSeverity.CRITICAL)
    assert GrowthFlag.SUSTAINED_GROWTH in result.flags


def test_detector_rapid_growth_process():
    """Verify process expanding above rapid threshold is flagged with RAPID_GROWTH."""
    detector = AbnormalGrowthDetector()
    trend = ProcessTrend(
        pid=303,
        name="rapid_allocator.exe",
        sample_count=10,
        duration_seconds=10.0,
        start_memory_mb=100.0,
        end_memory_mb=250.0,
        net_change_mb=150.0,
        growth_rate_mb_s=15.0,  # Exceeds rapid threshold of 5 MB/s
        persistence_score=0.85,
        classification=TrendClassification.RAPID_GROWTH,
        explanation="Rapid memory expansion",
    )
    result = detector.evaluate_process(trend)

    assert result.is_abnormal
    assert GrowthFlag.RAPID_GROWTH in result.flags
    assert result.severity == GrowthSeverity.CRITICAL


def test_detector_transient_spike():
    """Verify short burst with low persistence is flagged as TRANSIENT_SPIKE."""
    detector = AbnormalGrowthDetector()
    trend = ProcessTrend(
        pid=404,
        name="bursty_app.exe",
        sample_count=10,
        duration_seconds=10.0,
        start_memory_mb=100.0,
        end_memory_mb=160.0,
        net_change_mb=60.0,
        growth_rate_mb_s=6.0,  # Rapid rate
        persistence_score=0.30,  # Low persistence
        classification=TrendClassification.RAPID_GROWTH,
        explanation="Bursty spike",
    )
    result = detector.evaluate_process(trend)

    assert GrowthFlag.TRANSIENT_SPIKE in result.flags
    assert result.severity == GrowthSeverity.LOW  # Downgraded because it is transient


def test_detector_large_footprint_growing():
    """Verify large footprint process (> 1024 MB) that is growing is flagged."""
    detector = AbnormalGrowthDetector()
    trend = ProcessTrend(
        pid=505,
        name="large_database.exe",
        sample_count=10,
        duration_seconds=10.0,
        start_memory_mb=2000.0,
        end_memory_mb=2200.0,
        net_change_mb=200.0,
        growth_rate_mb_s=20.0,
        persistence_score=0.80,
        classification=TrendClassification.SUSTAINED_GROWTH,
        explanation="Expanding large memory footprint",
    )
    result = detector.evaluate_process(trend)

    assert result.is_abnormal
    assert GrowthFlag.LARGE_FOOTPRINT_GROWING in result.flags
    assert result.severity in (GrowthSeverity.HIGH, GrowthSeverity.CRITICAL)


def test_detector_negative_growth():
    """Verify shrinking memory footprint is not flagged as abnormal."""
    detector = AbnormalGrowthDetector()
    trend = ProcessTrend(
        pid=606,
        name="cleanup_agent.exe",
        sample_count=10,
        duration_seconds=10.0,
        start_memory_mb=500.0,
        end_memory_mb=300.0,
        net_change_mb=-200.0,
        growth_rate_mb_s=-20.0,
        persistence_score=0.0,
        classification=TrendClassification.FLUCTUATING,
        explanation="Memory decreasing",
    )
    result = detector.evaluate_process(trend)

    assert not result.is_abnormal
    assert result.severity == GrowthSeverity.NONE


# ============================================================================
# 3. Process Impact Scorer Tests
# ============================================================================

def test_impact_weights_validation():
    """Verify ImpactWeights enforces non-negative terms and exact sum of 1.0."""
    # Valid default weights
    valid_weights = ImpactWeights(w_memory=0.40, w_growth=0.35, w_persistence=0.25)
    assert valid_weights.w_memory == 0.40

    # Negative weight raises ValueError
    with pytest.raises(ValueError, match="non-negative"):
        ImpactWeights(w_memory=-0.1, w_growth=0.7, w_persistence=0.4)

    # Weights not summing to 1.0 raises ValueError
    with pytest.raises(ValueError, match="must sum to 1.0"):
        ImpactWeights(w_memory=0.5, w_growth=0.5, w_persistence=0.5)


def test_impact_score_single_process():
    """Verify single process impact score calculation and component normalization."""
    scorer = ProcessImpactScorer(
        weights=ImpactWeights(w_memory=0.40, w_growth=0.35, w_persistence=0.25),
        reference_growth_rate_mb_s=10.0,
    )
    trend = ProcessTrend(
        pid=1001,
        name="heavy_worker.exe",
        sample_count=10,
        duration_seconds=10.0,
        start_memory_mb=4000.0,
        end_memory_mb=4096.0,  # 4096 MB out of 16384 MB = 0.25
        net_change_mb=96.0,
        growth_rate_mb_s=5.0,  # 5.0 MB/s out of 10.0 reference = 0.50
        persistence_score=0.80,  # 0.80
        classification=TrendClassification.SUSTAINED_GROWTH,
        explanation="Growing worker",
    )
    impact = scorer.score_single(trend, total_ram_mb=16384.0)

    # Expected:
    # M_hat = 4096 / 16384 = 0.25
    # G_hat = 5.0 / 10.0 = 0.50
    # P_hat = 0.80
    # Score = 0.40 * 0.25 + 0.35 * 0.50 + 0.25 * 0.80 = 0.10 + 0.175 + 0.20 = 0.475
    assert impact.normalized_memory == 0.25
    assert impact.normalized_growth == 0.50
    assert impact.normalized_persistence == 0.80
    assert abs(impact.impact_score - 0.475) < 1e-3
    assert "Impact Score: 0.4750" in impact.explanation


def test_impact_score_cohort_ranking():
    """Verify cohort scoring properly sorts processes by impact descending and assigns ranks."""
    scorer = ProcessImpactScorer()

    trend_high = ProcessTrend(
        pid=1,
        name="high_impact.exe",
        sample_count=10,
        duration_seconds=10.0,
        start_memory_mb=7000.0,
        end_memory_mb=8000.0,
        net_change_mb=1000.0,
        growth_rate_mb_s=10.0,
        persistence_score=0.95,
        classification=TrendClassification.SUSTAINED_GROWTH,
        explanation="High impact",
    )
    trend_mid = ProcessTrend(
        pid=2,
        name="mid_impact.exe",
        sample_count=10,
        duration_seconds=10.0,
        start_memory_mb=1000.0,
        end_memory_mb=1500.0,
        net_change_mb=500.0,
        growth_rate_mb_s=2.0,
        persistence_score=0.60,
        classification=TrendClassification.GRADUALLY_INCREASING,
        explanation="Mid impact",
    )
    trend_low = ProcessTrend(
        pid=3,
        name="low_stable.exe",
        sample_count=10,
        duration_seconds=10.0,
        start_memory_mb=200.0,
        end_memory_mb=200.0,
        net_change_mb=0.0,
        growth_rate_mb_s=0.0,
        persistence_score=0.0,
        classification=TrendClassification.STABLE,
        explanation="Low stable",
    )

    ranked = scorer.score_cohort(
        [trend_mid, trend_low, trend_high],
        total_ram_mb=16384.0,
    )

    assert len(ranked) == 3
    assert ranked[0].pid == 1
    assert ranked[0].rank == 1
    assert ranked[1].pid == 2
    assert ranked[1].rank == 2
    assert ranked[2].pid == 3
    assert ranked[2].rank == 3
    assert ranked[0].impact_score > ranked[1].impact_score > ranked[2].impact_score


def test_impact_negative_growth_zeroed():
    """Verify process with negative growth gets zeroed growth and persistence impact."""
    scorer = ProcessImpactScorer()
    trend = ProcessTrend(
        pid=99,
        name="shrinking.exe",
        sample_count=10,
        duration_seconds=10.0,
        start_memory_mb=2000.0,
        end_memory_mb=1000.0,
        net_change_mb=-1000.0,
        growth_rate_mb_s=-10.0,
        persistence_score=0.0,
        classification=TrendClassification.FLUCTUATING,
        explanation="Shrinking",
    )
    impact = scorer.score_single(trend, total_ram_mb=16384.0)

    assert impact.normalized_growth == 0.0
    assert impact.normalized_persistence == 0.0
    # Score is purely based on remaining memory footprint
    expected_score = round(0.40 * (1000.0 / 16384.0), 4)
    assert abs(impact.impact_score - expected_score) < 1e-4


# ============================================================================
# 4. Service Integration Tests
# ============================================================================

def test_run_detection_end_to_end_with_database():
    """Verify run_detection executes end-to-end against an active MetricsDatabase."""
    db = MetricsDatabase(":memory:")
    base_time = 1700000000.0

    # Insert 6 consecutive snapshots at 1-second intervals
    for i in range(6):
        t = base_time + i
        sys_m = SystemMetrics(
            timestamp=t,
            total_ram_mb=16384.0,
            available_ram_mb=4000.0 - (i * 200.0),
            used_ram_mb=12384.0 + (i * 200.0),
            percent_used=75.0 + (i * 1.2),
            swap_total_mb=4096.0,
            swap_used_mb=500.0,
            swap_percent=12.2,
        )
        # Process 101: Accumulating memory rapidly
        p1 = ProcessMetrics(
            pid=101,
            name="memory_hog.exe",
            rss_mb=1000.0 + (i * 100.0),
            vms_mb=2000.0,
            memory_percent=6.1 + (i * 0.6),
            cpu_percent=5.0,
            num_threads=8,
            create_time=base_time,
            status="running",
        )
        # Process 202: Stable background service
        p2 = ProcessMetrics(
            pid=202,
            name="system_daemon.exe",
            rss_mb=200.0 + (0.1 * (i % 2)),
            vms_mb=400.0,
            memory_percent=1.2,
            cpu_percent=1.0,
            num_threads=2,
            create_time=base_time,
            status="running",
        )
        snapshot = SystemSnapshot(timestamp=t, system=sys_m, processes=[p1, p2])
        db.insert_snapshot(snapshot)

    report = run_detection(db, window_seconds=60.0)

    assert isinstance(report, DetectionReport)
    assert report.system_pressure is not None
    # 75% + rising rate should result in Moderate or High pressure
    assert report.system_pressure.state in (PressureState.MODERATE, PressureState.HIGH)

    # memory_hog.exe should be flagged as abnormal with sustained/rapid growth
    assert len(report.abnormal_processes) == 2
    hog_abnormal = next(p for p in report.abnormal_processes if p.pid == 101)
    assert hog_abnormal.is_abnormal
    assert GrowthFlag.SUSTAINED_GROWTH in hog_abnormal.flags

    # memory_hog.exe should rank #1 in impact score
    assert report.highest_impact_process is not None
    assert report.highest_impact_process.pid == 101
    assert report.highest_impact_process.rank == 1

    # Report serializes cleanly to dict
    d = report.to_dict()
    assert isinstance(d, dict)
    assert "system_pressure" in d
    assert "ranked_impact_scores" in d
    assert len(d["ranked_impact_scores"]) == 2


def test_run_detection_empty_database():
    """Verify run_detection handles an empty database safely without crashing."""
    db = MetricsDatabase(":memory:")
    report = run_detection(db, window_seconds=60.0)

    assert isinstance(report, DetectionReport)
    assert report.system_pressure.state == PressureState.NORMAL
    assert len(report.abnormal_processes) == 0
    assert len(report.ranked_impact_scores) == 0
    assert report.highest_impact_process is None
