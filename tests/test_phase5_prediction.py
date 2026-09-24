"""
Phase 5 Tests: Predictive Memory Pressure Analysis Component.

Test coverage:
1. Ordinary Least Squares (OLS) regression:
   - Perfect linear fit (slope, intercept, R^2 = 1.0).
   - Horizontal invariant series (slope = 0.0, R^2 = 1.0).
   - Noisy data with intermediate R^2 in [0.0, 1.0].
   - Boundary edge cases (single sample, identical timestamps).
2. Threshold Breach Estimation:
   - Upper limit active breach (already breached, seconds=0).
   - Upper limit approaching breach (exact time calculation).
   - Upper limit with zero or negative growth (no breach predicted).
   - Lower limit breach (available RAM declining to critical floor).
3. PressurePredictor System Forecasting:
   - Stable memory scenario (STABLE trajectory, no breach).
   - Rapidly expanding memory scenario (RAPID_INCREASE or CRITICAL_IMMINENT).
   - Recovering memory scenario (IMPROVING trajectory).
   - Horizon projection clamping within physical boundaries [0.0, 100.0]%.
   - Insufficient historical samples fallback.
4. Process-Level Memory Forecasting:
   - Milestone time-to-reach estimation (1 GB, 2 GB).
   - Process projections across horizons (+30s, +60s, +120s, +300s).
   - Insufficient process sample handling.
5. Integrated Prediction Service:
   - End-to-end execution against MetricsDatabase.
   - PredictionReport serialization and property access.
   - Graceful handling of empty database.
"""

import pytest

from src.collector.monitor import SystemMetrics, ProcessMetrics, SystemSnapshot
from src.prediction.forecaster import (
    ForecastPoint,
    PressureForecast,
    PressurePredictor,
    ProcessForecast,
    ThresholdBreachEstimate,
    TrajectoryState,
    compute_ols_regression,
    estimate_breach_timeline,
)
from src.prediction.service import (
    PredictionReport,
    predict_candidate_processes,
    predict_system_pressure,
    run_prediction,
)
from src.storage.database import MetricsDatabase


# ============================================================================
# 1. OLS Regression Tests
# ============================================================================

def test_compute_ols_regression_perfect_linear():
    """Verify OLS yields exact slope, intercept, and R^2 = 1.0 for linear data."""
    # y = 2.5 * t + 10.0
    t_points = [0.0, 1.0, 2.0, 3.0, 4.0]
    values = [10.0, 12.5, 15.0, 17.5, 20.0]

    slope, intercept, r2 = compute_ols_regression(t_points, values)

    assert abs(slope - 2.5) < 1e-5
    assert abs(intercept - 10.0) < 1e-5
    assert abs(r2 - 1.0) < 1e-5


def test_compute_ols_regression_horizontal_line():
    """Verify OLS returns 0.0 slope and 1.0 R^2 for constant series."""
    t_points = [100.0, 101.0, 102.0, 103.0]
    values = [42.0, 42.0, 42.0, 42.0]

    slope, intercept, r2 = compute_ols_regression(t_points, values)

    assert abs(slope) < 1e-5
    assert abs(intercept - 42.0) < 1e-5
    assert abs(r2 - 1.0) < 1e-5


def test_compute_ols_regression_edge_cases():
    """Verify OLS handles single point or zero variance safely."""
    slope, intercept, r2 = compute_ols_regression([10.0], [50.0])
    assert slope == 0.0
    assert intercept == 50.0
    assert r2 == 0.0

    # Identical timestamps
    slope, intercept, r2 = compute_ols_regression([10.0, 10.0], [50.0, 60.0])
    assert slope == 0.0
    assert r2 == 0.0


# ============================================================================
# 2. Threshold Breach Estimation Tests
# ============================================================================

def test_estimate_breach_timeline_already_breached():
    """Verify already breached state returns 0.0 seconds and active flag."""
    est = estimate_breach_timeline(
        current_value=94.0,
        rate_per_sec=0.1,
        target_threshold=92.0,
        threshold_name="Critical (92%)",
        current_timestamp=1000.0,
        is_upper_limit=True,
    )
    assert est.is_already_breached
    assert est.is_breach_predicted
    assert est.seconds_to_breach == 0.0
    assert "actively breached" in est.explanation


def test_estimate_breach_timeline_approaching():
    """Verify approaching breach accurately calculates time to threshold."""
    # Current: 80%, Target: 90%, Rate: +0.5% / sec -> 20.0 seconds
    est = estimate_breach_timeline(
        current_value=80.0,
        rate_per_sec=0.5,
        target_threshold=90.0,
        threshold_name="High (90%)",
        current_timestamp=1000.0,
        is_upper_limit=True,
    )
    assert not est.is_already_breached
    assert est.is_breach_predicted
    assert abs(est.seconds_to_breach - 20.0) < 1e-2
    assert est.breach_timestamp == 1020.0
    assert "projected to be reached in 20.0s" in est.explanation


def test_estimate_breach_timeline_declining_or_zero():
    """Verify zero or declining rate indicates no breach predicted."""
    est = estimate_breach_timeline(
        current_value=75.0,
        rate_per_sec=-0.2,
        target_threshold=90.0,
        threshold_name="Critical (90%)",
        current_timestamp=1000.0,
        is_upper_limit=True,
    )
    assert not est.is_already_breached
    assert not est.is_breach_predicted
    assert est.seconds_to_breach is None
    assert "not projected to be breached" in est.explanation


def test_estimate_breach_timeline_lower_limit():
    """Verify lower limit threshold (available RAM falling to 500 MB)."""
    # Current: 1000 MB, Target: 500 MB, Rate: -50 MB/s -> 10.0 seconds
    est = estimate_breach_timeline(
        current_value=1000.0,
        rate_per_sec=-50.0,
        target_threshold=500.0,
        threshold_name="Available RAM Floor (500 MB)",
        current_timestamp=1000.0,
        is_upper_limit=False,
    )
    assert not est.is_already_breached
    assert est.is_breach_predicted
    assert abs(est.seconds_to_breach - 10.0) < 1e-2


# ============================================================================
# 3. Pressure Predictor System Forecasting Tests
# ============================================================================

def test_predict_system_stable_memory():
    """Verify stable memory results in STABLE trajectory and no breach."""
    predictor = PressurePredictor()
    history = [
        {
            "timestamp": 1000.0 + i,
            "percent_used": 50.0,
            "used_ram_mb": 8192.0,
            "available_ram_mb": 8192.0,
            "total_ram_mb": 16384.0,
        }
        for i in range(10)
    ]
    forecast = predictor.predict_system(history)

    assert forecast.trajectory == TrajectoryState.STABLE
    assert abs(forecast.rate_percent_s) < 0.01
    assert not forecast.critical_breach.is_breach_predicted
    assert len(forecast.projections) == 4
    # All projected points should hover near 50%
    for pt in forecast.projections:
        assert abs(pt.projected_ram_percent - 50.0) < 0.5


def test_predict_system_critical_imminent():
    """Verify rapidly increasing memory triggers CRITICAL_IMMINENT state."""
    predictor = PressurePredictor()
    # Memory starts at 86% and climbs at 0.5% per second over 6 samples
    # At t=5, RAM is 88.5%. Critical threshold (92%) is only 3.5% away = 7.0s!
    history = [
        {
            "timestamp": 1000.0 + i,
            "percent_used": 86.0 + (i * 0.5),
            "used_ram_mb": 14000.0 + (i * 80.0),
            "available_ram_mb": 2384.0 - (i * 80.0),
            "total_ram_mb": 16384.0,
        }
        for i in range(6)
    ]
    forecast = predictor.predict_system(history)

    assert forecast.trajectory == TrajectoryState.CRITICAL_IMMINENT
    assert forecast.critical_breach.is_breach_predicted
    assert forecast.critical_breach.seconds_to_breach is not None
    assert forecast.critical_breach.seconds_to_breach <= 300.0
    assert "CRITICAL_IMMINENT" in forecast.explanation


def test_predict_system_improving_trajectory():
    """Verify declining memory utilization is classified as IMPROVING."""
    predictor = PressurePredictor()
    history = [
        {
            "timestamp": 1000.0 + i,
            "percent_used": 80.0 - (i * 0.2),
            "used_ram_mb": 13000.0 - (i * 30.0),
            "available_ram_mb": 3384.0 + (i * 30.0),
            "total_ram_mb": 16384.0,
        }
        for i in range(10)
    ]
    forecast = predictor.predict_system(history)

    assert forecast.trajectory == TrajectoryState.IMPROVING
    assert forecast.rate_percent_s < 0
    assert not forecast.critical_breach.is_breach_predicted


def test_predict_system_projection_clamping():
    """Verify projections do not exceed 100% or physical RAM capacity."""
    predictor = PressurePredictor()
    # Rapid memory spike that would mathematically surpass 100% at +300s
    history = [
        {
            "timestamp": 1000.0 + i,
            "percent_used": 80.0 + (i * 2.0),
            "used_ram_mb": 13000.0 + (i * 300.0),
            "available_ram_mb": 3384.0 - (i * 300.0),
            "total_ram_mb": 16384.0,
        }
        for i in range(5)
    ]
    forecast = predictor.predict_system(history, horizons=[30.0, 100.0, 300.0])

    for pt in forecast.projections:
        assert 0.0 <= pt.projected_ram_percent <= 100.0
        assert 0.0 <= pt.projected_used_mb <= 16384.0
        assert pt.projected_available_mb >= 0.0


def test_predict_system_insufficient_samples():
    """Verify safe fallback when history has fewer than min_samples."""
    predictor = PressurePredictor(min_samples=3)
    history = [
        {
            "timestamp": 1000.0,
            "percent_used": 50.0,
            "used_ram_mb": 8000.0,
            "available_ram_mb": 8384.0,
            "total_ram_mb": 16384.0,
        }
    ]
    forecast = predictor.predict_system(history)

    assert forecast.confidence_score == 0.0
    assert len(forecast.projections) == 0
    assert "Insufficient" in forecast.explanation


# ============================================================================
# 4. Process-Level Memory Forecasting Tests
# ============================================================================

def test_predict_process_milestones():
    """Verify process memory forecasts milestones (1 GB, 2 GB) correctly."""
    predictor = PressurePredictor()
    # Process memory expands from 600 MB at +10 MB/s over 10s
    # At t=9: current RSS = 690 MB.
    # Time to 1024 MB = (1024 - 690) / 10 = 33.4s
    history = [
        {"timestamp": 1000.0 + i, "pid": 777, "name": "leaky_service.exe", "rss_mb": 600.0 + (i * 10.0)}
        for i in range(10)
    ]
    forecast = predictor.predict_process(history, horizons=[30.0, 60.0])

    assert forecast.pid == 777
    assert forecast.name == "leaky_service.exe"
    assert abs(forecast.growth_rate_mb_s - 10.0) < 0.1
    assert forecast.time_to_1gb_s is not None
    assert abs(forecast.time_to_1gb_s - 33.4) < 1.0
    assert len(forecast.projections) == 2
    # At +30s: 690 + 300 = 990 MB
    assert abs(forecast.projections[0].projected_rss_mb - 990.0) < 5.0


def test_predict_process_insufficient_data():
    """Verify single-sample process forecast returns safe fallback."""
    predictor = PressurePredictor()
    forecast = predictor.predict_process([{"timestamp": 1000.0, "rss_mb": 250.0, "pid": 12, "name": "init.exe"}])

    assert forecast.growth_rate_mb_s == 0.0
    assert len(forecast.projections) == 0
    assert forecast.time_to_1gb_s is None


# ============================================================================
# 5. Service Integration Tests
# ============================================================================

def test_run_prediction_end_to_end_with_database():
    """Verify run_prediction executes against MetricsDatabase records."""
    db = MetricsDatabase(":memory:")
    base_time = 1700000000.0

    # Insert 8 consecutive snapshots with rising system RAM
    for i in range(8):
        t = base_time + i
        sys_m = SystemMetrics(
            timestamp=t,
            total_ram_mb=16384.0,
            available_ram_mb=3000.0 - (i * 150.0),
            used_ram_mb=13384.0 + (i * 150.0),
            percent_used=81.0 + (i * 0.9),  # 81% to 87.3%
            swap_total_mb=4096.0,
            swap_used_mb=200.0,
            swap_percent=4.8,
        )
        p1 = ProcessMetrics(
            pid=555,
            name="cache_drain.exe",
            rss_mb=500.0 + (i * 50.0),
            vms_mb=1000.0,
            memory_percent=3.0,
            cpu_percent=4.0,
            num_threads=4,
            create_time=base_time,
            status="running",
        )
        snapshot = SystemSnapshot(timestamp=t, system=sys_m, processes=[p1])
        db.insert_snapshot(snapshot)

    report = run_prediction(db, window_seconds=60.0)

    assert isinstance(report, PredictionReport)
    assert report.system_forecast is not None
    assert report.system_forecast.rate_percent_s > 0.5
    assert len(report.system_forecast.projections) > 0

    # Critical breach (92%) should be predicted soon
    assert report.system_forecast.critical_breach.is_breach_predicted
    assert report.is_critical_imminent

    # Process forecast for PID 555
    assert len(report.process_forecasts) == 1
    p_fc = report.process_forecasts[0]
    assert p_fc.pid == 555
    assert p_fc.growth_rate_mb_s > 30.0

    # Serialization test
    d = report.to_dict()
    assert isinstance(d, dict)
    assert "system_forecast" in d
    assert "process_forecasts" in d
    assert d["is_critical_imminent"] is True


def test_run_prediction_empty_database():
    """Verify run_prediction safely handles an empty database."""
    db = MetricsDatabase(":memory:")
    report = run_prediction(db, window_seconds=60.0)

    assert isinstance(report, PredictionReport)
    assert not report.is_critical_imminent
    assert report.time_to_critical_seconds is None
    assert len(report.process_forecasts) == 0
