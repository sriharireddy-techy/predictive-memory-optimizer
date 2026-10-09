"""
Phase 5 Service: Short-Term Predictive Forecasting Service.

Coordinates:
- System pressure time-series regression and horizon projections
- Process memory milestone projections
- High-level prediction report generation against historical storage (MetricsDatabase)
"""

from dataclasses import dataclass, asdict
import time
from typing import Any, Dict, List, Optional

from src.prediction.forecaster import (
    ForecastPoint,
    PressureForecast,
    PressurePredictor,
    ProcessForecast,
    ThresholdBreachEstimate,
    TrajectoryState,
)
from src.storage.database import MetricsDatabase


@dataclass(frozen=True)
class PredictionReport:
    """Consolidated predictive forecast report for system and top processes."""
    timestamp: float
    system_forecast: PressureForecast
    process_forecasts: List[ProcessForecast]

    @property
    def is_critical_imminent(self) -> bool:
        """Indicates if system is in CRITICAL_IMMINENT state."""
        return self.system_forecast.trajectory == TrajectoryState.CRITICAL_IMMINENT

    @property
    def time_to_critical_seconds(self) -> Optional[float]:
        """Estimated seconds remaining until critical threshold breach."""
        return self.system_forecast.critical_breach.seconds_to_breach

    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "system_forecast": self.system_forecast.to_dict(),
            "process_forecasts": [p.to_dict() for p in self.process_forecasts],
            "is_critical_imminent": self.is_critical_imminent,
            "time_to_critical_seconds": self.time_to_critical_seconds,
        }


def predict_system_pressure(
    db: MetricsDatabase,
    window_seconds: float = 120.0,
    horizons: Optional[List[float]] = None,
    predictor: Optional[PressurePredictor] = None,
) -> PressureForecast:
    """
    Query system memory history and forecast pressure trajectory over specified horizons.
    """
    predictor = predictor or PressurePredictor()
    history = db.get_system_history()

    # Filter to window_seconds if available
    if history and window_seconds > 0:
        latest_t = float(history[0]["timestamp"])
        cutoff_t = latest_t - window_seconds
        history = [r for r in history if float(r["timestamp"]) >= cutoff_t]

    return predictor.predict_system(history, horizons=horizons)


def predict_candidate_processes(
    db: MetricsDatabase,
    candidate_pids: Optional[List[int]] = None,
    window_seconds: float = 120.0,
    top_n: int = 5,
    predictor: Optional[PressurePredictor] = None,
) -> List[ProcessForecast]:
    """
    Generate memory milestone forecasts for candidate active processes.
    """
    predictor = predictor or PressurePredictor()

    if candidate_pids is None:
        candidate_pids = db.get_active_pids_in_window(window_seconds=window_seconds)

    forecasts: List[ProcessForecast] = []
    for pid in candidate_pids[:top_n]:
        history = db.get_process_history(pid=pid)
        if not history:
            continue
        p_forecast = predictor.predict_process(history, pid=pid)
        forecasts.append(p_forecast)

    # Sort so processes expanding fastest appear first
    forecasts.sort(key=lambda p: p.growth_rate_mb_s, reverse=True)
    return forecasts


def run_prediction(
    db: MetricsDatabase,
    window_seconds: float = 120.0,
    candidate_pids: Optional[List[int]] = None,
    horizons: Optional[List[float]] = None,
    predictor: Optional[PressurePredictor] = None,
) -> PredictionReport:
    """
    Execute full Phase 5 predictive forecasting pipeline:
    1. Forecast system pressure trajectory and critical breach timelines.
    2. Forecast trajectory and milestone timelines for key candidate processes.
    3. Generate consolidated PredictionReport.
    """
    current_time = time.time()
    predictor = predictor or PressurePredictor()

    sys_forecast = predict_system_pressure(
        db=db,
        window_seconds=window_seconds,
        horizons=horizons,
        predictor=predictor,
    )

    proc_forecasts = predict_candidate_processes(
        db=db,
        candidate_pids=candidate_pids,
        window_seconds=window_seconds,
        predictor=predictor,
    )

    return PredictionReport(
        timestamp=current_time,
        system_forecast=sys_forecast,
        process_forecasts=proc_forecasts,
    )
if __name__ == "__main__":
    db = MetricsDatabase("data/memory_monitor.db")
    p = run_optimization(db)

    print("\n" + "=" * 70)
    print("PHASE 6 - SAFE RESOURCE RECOMMENDATION ENGINE")
    print("=" * 70)

    print(f"System Pressure State     : {p.system_pressure.state.value}")

    trajectory = p.forecast.trajectory.value if p.forecast else "N/A"
    print(f"Predicted Trajectory      : {trajectory}")

    print(f"Overall Plan Urgency      : {p.overall_urgency.value}")
    print(f"Simulated Reclaimable RSS : "
          f"{p.simulated_reclaimable_rss_mb:.1f} MB")
    print(f"Projected RAM After       : "
          f"{p.projected_system_ram_percent_after:.2f}%")

    print("\nEXECUTIVE SUMMARY")
    print("-" * 70)
    print(p.summary)

    print("\nSAFETY NOTICE")
    print("-" * 70)
    print(p.safety_notice)

    print("\nRECOMMENDATIONS")
    print("-" * 70)

    for i, r in enumerate(p.recommendations, 1):
        print(f"\n{i}. {r.process_name} (PID {r.pid})")
        print(f"   Action        : {r.action_type.value}")
        print(f"   Urgency       : {r.urgency.value}")
        print(f"   Current RSS   : {r.current_rss_mb:.1f} MB")
        print(f"   Simulated RSS : {r.projected_reclaimable_mb:.1f} MB")
        print(f"   Reason        : {r.reasoning}")

    print("\n" + "=" * 70)
