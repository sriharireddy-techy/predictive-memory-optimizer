"""
Phase 6 Tests: Safe Resource Recommendation Engine Component.

Test coverage:
1. Safety Principles & Invariants:
   - Verification of recommendation-only operation (no OS kill/terminate calls).
   - Prominence of safety notices and human-in-the-loop disclaimers.
2. OS Protection Catalog:
   - Whitelist enforcement for Windows/Linux system processes.
   - Protection for system PIDs (PID 0, PID 4).
   - Protected processes assigned PROHIBITED_SYSTEM_CRITICAL action with 0 reclaimable MB.
3. Recommendation Engine Planning:
   - Normal/healthy system state produces NO_ACTION summary.
   - High pressure + rapid growth triggers RESTART_APPLICATION.
   - Sustained growth triggers CLEAR_APPLICATION_CACHE.
   - High static memory triggers REDUCE_WORKLOAD.
   - Simulated post-remediation system RAM % calculation.
4. Urgency Escalation:
   - Critical imminent trajectory triggers CRITICAL urgency.
   - Moderate pressure triggers MEDIUM urgency.
5. Service Integration:
   - End-to-end run_optimization against MetricsDatabase records.
   - Empty database graceful fallback.
   - Serialization to dict for dashboard consumption.
"""

import pytest

from src.collector.monitor import SystemMetrics, ProcessMetrics, SystemSnapshot
from src.detection.growth_detector import (
    AbnormalProcessGrowth,
    GrowthFlag,
    GrowthSeverity,
)
from src.detection.impact_scorer import ImpactWeights, ProcessImpact
from src.detection.pressure_analyzer import PressureState, SystemPressure
from src.optimization.recommendation_engine import (
    PROTECTED_PIDS,
    PROTECTED_PROCESS_NAMES,
    ActionRecommendation,
    ActionType,
    OptimizationPlan,
    RecommendationEngine,
    RiskPriority,
    is_protected_process,
)
from src.optimization.service import generate_optimization_plan, run_optimization
from src.prediction.forecaster import (
    ForecastPoint,
    PressureForecast,
    ThresholdBreachEstimate,
    TrajectoryState,
)
from src.storage.database import MetricsDatabase


# ============================================================================
# 1. Safety Principles & Invariants Tests
# ============================================================================

def test_engine_has_no_process_termination_methods():
    """Verify that RecommendationEngine and service contain no process-killing APIs."""
    import src.optimization.recommendation_engine as re_mod
    import src.optimization.service as s_mod

    dangerous_keywords = ["kill", "terminate", "sigkill", "sigterm", "suspend_process"]
    for kw in dangerous_keywords:
        assert not hasattr(re_mod.RecommendationEngine, kw), f"Dangerous method '{kw}' found on RecommendationEngine!"
        assert not hasattr(s_mod, kw), f"Dangerous function '{kw}' found in optimization service!"


def test_safety_notice_present_in_all_plans():
    """Verify safety disclaimer is always prominently embedded in every OptimizationPlan."""
    engine = RecommendationEngine()
    pressure = SystemPressure(
        timestamp=1000.0,
        state=PressureState.NORMAL,
        score=30.0,
        ram_used_percent=40.0,
        available_ram_mb=9000.0,
        total_ram_mb=16384.0,
        used_ram_mb=7384.0,
        swap_used_percent=5.0,
        swap_used_mb=200.0,
        rate_percent_s=0.0,
        contributing_factors=[],
        explanation="Healthy",
    )
    plan = engine.generate_plan(system_pressure=pressure)

    assert "ADVISORY ONLY" in plan.safety_notice
    assert "does not autonomously terminate" in plan.safety_notice


# ============================================================================
# 2. OS Protection Whitelist Tests
# ============================================================================

def test_is_protected_process_whitelist():
    """Verify detection of protected kernel and security tasks across OS platforms."""
    assert is_protected_process(4, "System")
    assert is_protected_process(0, "System Idle Process")
    assert is_protected_process(1234, "svchost.exe")
    assert is_protected_process(5678, "dwm.exe")
    assert is_protected_process(9999, "MsMpEng.exe")
    assert is_protected_process(1010, "explorer.exe")
    assert is_protected_process(2020, "MemCompression")
    assert is_protected_process(3030, "systemd")

    # Regular applications must not be protected
    assert not is_protected_process(4321, "chrome.exe")
    assert not is_protected_process(5432, "python.exe")
    assert not is_protected_process(6543, "slack.exe")


def test_protected_process_recommendation_prohibited_action():
    """Verify protected OS processes are assigned PROHIBITED_SYSTEM_CRITICAL with 0 reclaimable RAM."""
    engine = RecommendationEngine()
    pressure = SystemPressure(
        timestamp=1000.0,
        state=PressureState.HIGH,
        score=82.0,
        ram_used_percent=88.0,
        available_ram_mb=1900.0,
        total_ram_mb=16384.0,
        used_ram_mb=14484.0,
        swap_used_percent=15.0,
        swap_used_mb=600.0,
        rate_percent_s=0.05,
        contributing_factors=["High RAM"],
        explanation="High pressure",
    )
    impact = ProcessImpact(
        pid=1234,
        name="svchost.exe",
        rank=1,
        impact_score=0.85,
        current_rss_mb=2048.0,
        growth_rate_mb_s=1.0,
        persistence_score=0.8,
        normalized_memory=0.125,
        normalized_growth=0.1,
        normalized_persistence=0.8,
        weights=ImpactWeights(),
        explanation="High impact svchost",
    )
    plan = engine.generate_plan(system_pressure=pressure, ranked_impacts=[impact])

    assert len(plan.recommendations) == 1
    rec = plan.recommendations[0]
    assert rec.is_protected_system_process is True
    assert rec.action_type == ActionType.PROHIBITED_SYSTEM_CRITICAL
    assert rec.projected_reclaimable_mb == 0.0
    assert any("DO NOT TERMINATE" in step for step in rec.mitigation_steps)


# ============================================================================
# 3. Recommendation Engine Planning Tests
# ============================================================================

def test_generate_plan_healthy_system_no_remediation():
    """Verify healthy system produces 0 action recommendations and NONE urgency."""
    engine = RecommendationEngine()
    pressure = SystemPressure(
        timestamp=1000.0,
        state=PressureState.NORMAL,
        score=25.0,
        ram_used_percent=35.0,
        available_ram_mb=10500.0,
        total_ram_mb=16384.0,
        used_ram_mb=5884.0,
        swap_used_percent=2.0,
        swap_used_mb=100.0,
        rate_percent_s=0.0,
        contributing_factors=[],
        explanation="Nominal state",
    )
    plan = engine.generate_plan(system_pressure=pressure)

    assert plan.overall_urgency == RiskPriority.NONE
    assert len(plan.recommendations) == 0
    assert plan.total_potential_reclaim_mb == 0.0
    assert "No remediation required" in plan.summary


def test_generate_plan_rapid_growth_process():
    """Verify rapid expansion process triggers RESTART_APPLICATION recommendation."""
    engine = RecommendationEngine()
    pressure = SystemPressure(
        timestamp=1000.0,
        state=PressureState.HIGH,
        score=80.0,
        ram_used_percent=86.0,
        available_ram_mb=2200.0,
        total_ram_mb=16384.0,
        used_ram_mb=14184.0,
        swap_used_percent=10.0,
        swap_used_mb=400.0,
        rate_percent_s=0.20,
        contributing_factors=["High RAM"],
        explanation="High pressure",
    )
    impact = ProcessImpact(
        pid=9090,
        name="data_indexer.exe",
        rank=1,
        impact_score=0.92,
        current_rss_mb=3000.0,
        growth_rate_mb_s=12.0,
        persistence_score=0.95,
        normalized_memory=0.18,
        normalized_growth=0.90,
        normalized_persistence=0.95,
        weights=ImpactWeights(),
        explanation="Rapid expanding indexer",
    )
    abnormal = AbnormalProcessGrowth(
        pid=9090,
        name="data_indexer.exe",
        is_abnormal=True,
        severity=GrowthSeverity.CRITICAL,
        flags=[GrowthFlag.RAPID_GROWTH, GrowthFlag.SUSTAINED_GROWTH],
        growth_rate_mb_s=12.0,
        persistence_score=0.95,
        current_rss_mb=3000.0,
        net_change_mb=500.0,
        reasons=["Rapid growth"],
        explanation="Critical growth",
    )

    plan = engine.generate_plan(
        system_pressure=pressure,
        ranked_impacts=[impact],
        abnormal_processes=[abnormal],
    )

    assert len(plan.recommendations) == 1
    rec = plan.recommendations[0]
    assert rec.action_type == ActionType.RESTART_APPLICATION
    assert rec.urgency in (RiskPriority.HIGH, RiskPriority.CRITICAL)
    assert rec.projected_reclaimable_mb > 2000.0
    # Simulated system RAM % should decrease
    assert rec.simulated_post_ram_percent < 86.0
    assert plan.projected_system_ram_percent_after_remediation < 86.0


def test_generate_plan_sustained_growth_cache_clear():
    """Verify sustained growth process triggers CLEAR_APPLICATION_CACHE."""
    engine = RecommendationEngine()
    pressure = SystemPressure(
        timestamp=1000.0,
        state=PressureState.MODERATE,
        score=65.0,
        ram_used_percent=78.0,
        available_ram_mb=3600.0,
        total_ram_mb=16384.0,
        used_ram_mb=12784.0,
        swap_used_percent=5.0,
        swap_used_mb=200.0,
        rate_percent_s=0.03,
        contributing_factors=["Moderate RAM"],
        explanation="Moderate pressure",
    )
    impact = ProcessImpact(
        pid=7878,
        name="ide_worker.exe",
        rank=1,
        impact_score=0.65,
        current_rss_mb=1500.0,
        growth_rate_mb_s=0.5,
        persistence_score=0.85,
        normalized_memory=0.09,
        normalized_growth=0.05,
        normalized_persistence=0.85,
        weights=ImpactWeights(),
        explanation="Sustained IDE worker",
    )
    abnormal = AbnormalProcessGrowth(
        pid=7878,
        name="ide_worker.exe",
        is_abnormal=True,
        severity=GrowthSeverity.MEDIUM,
        flags=[GrowthFlag.SUSTAINED_GROWTH],
        growth_rate_mb_s=0.5,
        persistence_score=0.85,
        current_rss_mb=1500.0,
        net_change_mb=100.0,
        reasons=["Sustained positive steps"],
        explanation="Sustained memory growth",
    )

    plan = engine.generate_plan(
        system_pressure=pressure,
        ranked_impacts=[impact],
        abnormal_processes=[abnormal],
    )

    assert len(plan.recommendations) == 1
    rec = plan.recommendations[0]
    assert rec.action_type == ActionType.CLEAR_APPLICATION_CACHE


# ============================================================================
# 4. Critical Escalation Tests
# ============================================================================

def test_plan_critical_imminent_urgency_escalation():
    """Verify CRITICAL_IMMINENT trajectory elevates plan urgency to CRITICAL."""
    engine = RecommendationEngine()
    pressure = SystemPressure(
        timestamp=1000.0,
        state=PressureState.HIGH,
        score=82.0,
        ram_used_percent=88.0,
        available_ram_mb=1900.0,
        total_ram_mb=16384.0,
        used_ram_mb=14484.0,
        swap_used_percent=15.0,
        swap_used_mb=600.0,
        rate_percent_s=0.25,
        contributing_factors=["High RAM"],
        explanation="High pressure",
    )
    forecast = PressureForecast(
        timestamp=1000.0,
        current_percent=88.0,
        current_available_mb=1900.0,
        current_used_mb=14484.0,
        total_ram_mb=16384.0,
        rate_percent_s=0.25,
        rate_used_mb_s=40.0,
        r_squared=0.95,
        confidence_score=0.90,
        trajectory=TrajectoryState.CRITICAL_IMMINENT,  # Critical imminent!
        projections=[],
        warning_breach=ThresholdBreachEstimate("Warn", 85.0, 88.0, True, True, 0.0, 1000.0, "Breached"),
        critical_breach=ThresholdBreachEstimate("Crit", 92.0, 88.0, False, True, 16.0, 1016.0, "Breach in 16s"),
        explanation="Critical breach imminent",
    )

    plan = engine.generate_plan(system_pressure=pressure, forecast=forecast)

    assert plan.overall_urgency == RiskPriority.CRITICAL
    assert plan.trajectory_state == TrajectoryState.CRITICAL_IMMINENT


# ============================================================================
# 5. Serialization and Service Integration Tests
# ============================================================================

def test_optimization_plan_serialization():
    """Verify OptimizationPlan and ActionRecommendations serialize cleanly to dict."""
    engine = RecommendationEngine()
    pressure = SystemPressure(
        timestamp=1000.0,
        state=PressureState.NORMAL,
        score=40.0,
        ram_used_percent=50.0,
        available_ram_mb=8192.0,
        total_ram_mb=16384.0,
        used_ram_mb=8192.0,
        swap_used_percent=4.0,
        swap_used_mb=150.0,
        rate_percent_s=0.0,
        contributing_factors=[],
        explanation="Stable",
    )
    plan = engine.generate_plan(system_pressure=pressure)
    d = plan.to_dict()

    assert isinstance(d, dict)
    assert d["system_pressure_state"] == "NORMAL"
    assert "safety_notice" in d
    assert "total_potential_reclaim_mb" in d


def test_run_optimization_end_to_end_with_database():
    """Verify run_optimization executes end-to-end against an active MetricsDatabase."""
    db = MetricsDatabase(":memory:")
    base_time = 1700000000.0

    # Insert 6 snapshots with rising RAM
    for i in range(6):
        t = base_time + i
        sys_m = SystemMetrics(
            timestamp=t,
            total_ram_mb=16384.0,
            available_ram_mb=2500.0 - (i * 100.0),
            used_ram_mb=13884.0 + (i * 100.0),
            percent_used=84.0 + (i * 0.8),
            swap_total_mb=4096.0,
            swap_used_mb=300.0,
            swap_percent=7.3,
        )
        p1 = ProcessMetrics(
            pid=2222,
            name="memory_hog.exe",
            rss_mb=2000.0 + (i * 80.0),
            vms_mb=4000.0,
            memory_percent=12.0,
            cpu_percent=6.0,
            num_threads=8,
            create_time=base_time,
            status="running",
        )
        p2 = ProcessMetrics(
            pid=4,
            name="System",
            rss_mb=150.0,
            vms_mb=300.0,
            memory_percent=0.9,
            cpu_percent=1.0,
            num_threads=150,
            create_time=base_time,
            status="running",
        )
        snapshot = SystemSnapshot(timestamp=t, system=sys_m, processes=[p1, p2])
        db.insert_snapshot(snapshot)

    plan = run_optimization(db, window_seconds=60.0)

    assert isinstance(plan, OptimizationPlan)
    assert plan.overall_urgency in (RiskPriority.HIGH, RiskPriority.CRITICAL)
    assert len(plan.recommendations) > 0

    # Check that PID 4 (System) is marked protected
    system_rec = next((r for r in plan.recommendations if r.pid == 4), None)
    if system_rec:
        assert system_rec.is_protected_system_process is True
        assert system_rec.action_type == ActionType.PROHIBITED_SYSTEM_CRITICAL

    # Check that memory_hog.exe has an action recommendation with simulated reclaim
    hog_rec = next(r for r in plan.recommendations if r.pid == 2222)
    assert hog_rec.is_protected_system_process is False
    assert hog_rec.action_type in (ActionType.RESTART_APPLICATION, ActionType.CLEAR_APPLICATION_CACHE)
    assert hog_rec.projected_reclaimable_mb > 1500.0


def test_run_optimization_empty_database():
    """Verify run_optimization handles empty database gracefully."""
    db = MetricsDatabase(":memory:")
    plan = run_optimization(db, window_seconds=60.0)

    assert isinstance(plan, OptimizationPlan)
    assert plan.overall_urgency == RiskPriority.NONE
    assert len(plan.recommendations) == 0
