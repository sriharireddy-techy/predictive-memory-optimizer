"""
Phase 3 Tests: Memory Behaviour and Growth Analysis Component.

Test coverage:
1. Stable memory data.
2. Fluctuating memory data.
3. Controlled increasing memory data.
4. Strong sustained growth.
5. Rapid growth scenario.
6. Insufficient historical samples (< 3 samples or < 1.0s duration).
7. Irregular timestamps (varying delta_t, duplicate timestamps).
8. Missing, null, or invalid measurements.
9. System trend analysis (stable vs. increasing).
10. Batch active process analysis via MetricsDatabase integration.
"""

import pytest

from src.analysis.trend_analyzer import (
    TrendClassification,
    ProcessTrend,
    SystemTrend,
    MemoryTrendAnalyzer,
    compute_linear_slope,
    calculate_persistence,
)
from src.analysis.service import analyze_active_processes, analyze_system_trend
from src.collector.monitor import SystemMetrics, ProcessMetrics, SystemSnapshot
from src.storage.database import MetricsDatabase


@pytest.fixture
def analyzer():
    return MemoryTrendAnalyzer(
        min_samples=3,
        min_duration_s=1.0,
        noise_threshold_mb=0.5,
        sustained_persistence_threshold=0.75,
        gradual_persistence_threshold=0.50,
        rapid_growth_rate_threshold=5.0,
    )


def test_stable_memory_data(analyzer):
    """
    Scenario 1: Stable memory data.
    Process memory hovers tightly around 500 MB across 10 seconds.
    """
    history = [
        {"timestamp": 1000.0 + i, "pid": 101, "name": "stable_srv.exe", "rss_mb": 500.0 + (0.05 * (i % 2))}
        for i in range(10)
    ]
    trend = analyzer.analyze_process(history)

    assert trend.classification == TrendClassification.STABLE
    assert abs(trend.net_change_mb) <= 0.5
    assert abs(trend.growth_rate_mb_s) <= 0.05
    assert "Memory is stable" in trend.explanation


def test_fluctuating_memory_data(analyzer):
    """
    Scenario 2: Fluctuating memory data.
    Process memory bounces up and down without sustained direction.
    """
    history = [
        {"timestamp": 1000.0, "pid": 102, "name": "fluct_app.exe", "rss_mb": 100.0},
        {"timestamp": 1001.0, "pid": 102, "name": "fluct_app.exe", "rss_mb": 140.0},
        {"timestamp": 1002.0, "pid": 102, "name": "fluct_app.exe", "rss_mb": 105.0},
        {"timestamp": 1003.0, "pid": 102, "name": "fluct_app.exe", "rss_mb": 145.0},
        {"timestamp": 1004.0, "pid": 102, "name": "fluct_app.exe", "rss_mb": 102.0},
        {"timestamp": 1005.0, "pid": 102, "name": "fluct_app.exe", "rss_mb": 138.0},
    ]
    trend = analyzer.analyze_process(history)

    assert trend.classification == TrendClassification.FLUCTUATING
    assert trend.persistence_score < 0.75
    assert "Fluctuating" in trend.explanation


def test_controlled_increasing_memory_data(analyzer):
    """
    Scenario 3: Controlled increasing memory data.
    Process memory grows moderately with intermittent plateaus.
    """
    history = [
        {"timestamp": 1000.0, "pid": 103, "name": "gradual_app.exe", "rss_mb": 200.0},
        {"timestamp": 1002.0, "pid": 103, "name": "gradual_app.exe", "rss_mb": 203.0},
        {"timestamp": 1004.0, "pid": 103, "name": "gradual_app.exe", "rss_mb": 203.1},  # plateau
        {"timestamp": 1006.0, "pid": 103, "name": "gradual_app.exe", "rss_mb": 206.5},
        {"timestamp": 1008.0, "pid": 103, "name": "gradual_app.exe", "rss_mb": 206.6},  # plateau
        {"timestamp": 1010.0, "pid": 103, "name": "gradual_app.exe", "rss_mb": 210.0},
    ]
    trend = analyzer.analyze_process(history)

    assert trend.classification == TrendClassification.GRADUALLY_INCREASING
    assert trend.growth_rate_mb_s > 0.0
    assert 0.50 <= trend.persistence_score < 0.75
    assert trend.net_change_mb == 10.0


def test_strong_sustained_growth(analyzer):
    """
    Scenario 4: Strong sustained growth.
    Process memory increases strictly in every single sampling interval.
    """
    history = [
        {"timestamp": 1000.0 + i, "pid": 104, "name": "leaking_worker.exe", "rss_mb": 100.0 + (i * 2.0)}
        for i in range(8)
    ]
    trend = analyzer.analyze_process(history)

    assert trend.classification == TrendClassification.SUSTAINED_GROWTH
    assert trend.persistence_score == 1.0  # 7 out of 7 intervals increased
    assert trend.growth_rate_mb_s == pytest.approx(2.0, rel=1e-2)
    assert trend.net_change_mb == 14.0
    assert "Sustained memory growth" in trend.explanation


def test_rapid_growth(analyzer):
    """
    Scenario 4b: Rapid growth exceeding rapid_growth_rate_threshold (> 5.0 MB/s).
    """
    history = [
        {"timestamp": 1000.0 + i, "pid": 105, "name": "allocator.exe", "rss_mb": 100.0 + (i * 10.0)}
        for i in range(6)
    ]
    trend = analyzer.analyze_process(history)

    assert trend.classification == TrendClassification.RAPID_GROWTH
    assert trend.growth_rate_mb_s >= 5.0
    assert trend.persistence_score >= 0.75
    assert "Rapid memory growth" in trend.explanation


def test_insufficient_historical_samples(analyzer):
    """
    Scenario 5: Insufficient historical samples.
    Tests 0, 1, 2 samples, and duration < min_duration_s.
    """
    # Empty
    t0 = analyzer.analyze_process([])
    assert t0.classification == TrendClassification.INSUFFICIENT_DATA
    assert t0.sample_count == 0

    # 1 sample
    t1 = analyzer.analyze_process([{"timestamp": 1000.0, "rss_mb": 100.0, "pid": 1}])
    assert t1.classification == TrendClassification.INSUFFICIENT_DATA
    assert t1.sample_count == 1

    # 2 samples
    t2 = analyzer.analyze_process([
        {"timestamp": 1000.0, "rss_mb": 100.0, "pid": 1},
        {"timestamp": 1001.0, "rss_mb": 105.0, "pid": 1},
    ])
    assert t2.classification == TrendClassification.INSUFFICIENT_DATA
    assert t2.sample_count == 2

    # 3 samples but zero elapsed duration
    t_zero_dur = analyzer.analyze_process([
        {"timestamp": 1000.0, "rss_mb": 100.0, "pid": 1},
        {"timestamp": 1000.0, "rss_mb": 101.0, "pid": 1},
        {"timestamp": 1000.0, "rss_mb": 102.0, "pid": 1},
    ])
    assert t_zero_dur.classification == TrendClassification.INSUFFICIENT_DATA


def test_irregular_and_duplicate_timestamps(analyzer):
    """
    Scenario 6: Irregular timestamps.
    Non-uniform time intervals (0.5s, 4.0s, duplicate timestamps).
    """
    history = [
        {"timestamp": 1000.0, "rss_mb": 50.0, "pid": 106, "name": "irregular.exe"},
        {"timestamp": 1000.0, "rss_mb": 50.0, "pid": 106, "name": "irregular.exe"},  # duplicate timestamp
        {"timestamp": 1000.5, "rss_mb": 52.0, "pid": 106, "name": "irregular.exe"},
        {"timestamp": 1004.5, "rss_mb": 60.0, "pid": 106, "name": "irregular.exe"},
        {"timestamp": 1005.0, "rss_mb": 62.0, "pid": 106, "name": "irregular.exe"},
    ]
    trend = analyzer.analyze_process(history)

    # Should deduplicate timestamp 1000.0 and compute valid rate across the 5.0 seconds
    assert trend.sample_count == 4
    assert trend.duration_seconds == 5.0
    assert trend.classification in (TrendClassification.SUSTAINED_GROWTH, TrendClassification.RAPID_GROWTH)
    assert trend.net_change_mb == 12.0


def test_missing_and_invalid_measurements(analyzer):
    """
    Scenario 7: Missing, null, or negative measurements.
    Sanitizer must drop invalid rows without raising exceptions.
    """
    history = [
        {"timestamp": 1000.0, "rss_mb": 100.0, "pid": 107, "name": "messy.exe"},
        {"timestamp": 1001.0, "rss_mb": None, "pid": 107, "name": "messy.exe"},     # Null memory
        {"timestamp": None, "rss_mb": 105.0, "pid": 107, "name": "messy.exe"},      # Null timestamp
        {"timestamp": 1002.0, "rss_mb": -50.0, "pid": 107, "name": "messy.exe"},     # Negative memory
        {"timestamp": "corrupt", "rss_mb": 105.0, "pid": 107, "name": "messy.exe"}, # String timestamp
        {"timestamp": 1003.0, "rss_mb": 106.0, "pid": 107, "name": "messy.exe"},    # Valid
        {"timestamp": 1004.0, "rss_mb": 109.0, "pid": 107, "name": "messy.exe"},    # Valid
    ]
    trend = analyzer.analyze_process(history)

    # Exactly 3 valid samples should survive: 1000.0 (100MB), 1003.0 (106MB), 1004.0 (109MB)
    assert trend.sample_count == 3
    assert trend.duration_seconds == 4.0
    assert trend.net_change_mb == 9.0
    assert trend.classification != TrendClassification.INSUFFICIENT_DATA


def test_system_trend_analysis(analyzer):
    """Verify system RAM utilization trend analysis."""
    # Stable system RAM
    stable_sys = [
        {"timestamp": 1000.0 + i, "percent_used": 60.0 + (0.1 * (i % 2))}
        for i in range(5)
    ]
    s_trend = analyzer.analyze_system(stable_sys)
    assert s_trend.classification == TrendClassification.STABLE

    # Increasing system RAM
    increasing_sys = [
        {"timestamp": 1000.0 + i, "percent_used": 50.0 + (i * 2.0)}
        for i in range(6)
    ]
    inc_trend = analyzer.analyze_system(increasing_sys)
    assert inc_trend.classification in (TrendClassification.SUSTAINED_GROWTH, TrendClassification.GRADUALLY_INCREASING)
    assert inc_trend.rate_percent_s > 0.0


def test_batch_active_process_analysis_integration():
    """
    Test end-to-end integration:
    Store synthetic processes into MetricsDatabase and run analyze_active_processes.
    """
    with MetricsDatabase(":memory:") as db:
        # Insert 4 consecutive snapshots with 2 processes:
        # Process 10: Constant 200 MB (Stable)
        # Process 20: Growing 100 -> 130 MB (Sustained Growth)
        for i in range(4):
            t = 1000.0 + i
            snap = SystemSnapshot(
                timestamp=t,
                system=SystemMetrics(
                    timestamp=t,
                    total_ram_mb=16000.0,
                    available_ram_mb=8000.0,
                    used_ram_mb=8000.0,
                    percent_used=50.0,
                    swap_total_mb=4000.0,
                    swap_used_mb=0.0,
                    swap_percent=0.0,
                ),
                processes=[
                    ProcessMetrics(
                        pid=10,
                        name="stable_daemon.exe",
                        rss_mb=200.0,
                        vms_mb=300.0,
                        memory_percent=1.25,
                        cpu_percent=0.5,
                        num_threads=2,
                        create_time=500.0,
                        status="running",
                    ),
                    ProcessMetrics(
                        pid=20,
                        name="leaking_worker.exe",
                        rss_mb=100.0 + (i * 10.0),
                        vms_mb=400.0,
                        memory_percent=1.0,
                        cpu_percent=3.0,
                        num_threads=4,
                        create_time=600.0,
                        status="running",
                    ),
                ],
            )
            db.insert_snapshot(snap)

        results = analyze_active_processes(db, window_seconds=60.0)
        assert len(results) == 2

        # The growing process should be ranked FIRST because results are sorted by growth rate descending
        top_growth = results[0]
        assert top_growth.pid == 20
        assert top_growth.name == "leaking_worker.exe"
        assert top_growth.classification in (TrendClassification.SUSTAINED_GROWTH, TrendClassification.RAPID_GROWTH)
        assert top_growth.growth_rate_mb_s > 0

        stable_proc = results[1]
        assert stable_proc.pid == 10
        assert stable_proc.name == "stable_daemon.exe"
        assert stable_proc.classification == TrendClassification.STABLE
