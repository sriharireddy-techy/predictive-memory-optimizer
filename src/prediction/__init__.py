"""
Phase 5: Predictive Memory Pressure Analysis Component.
"""

from src.prediction.forecaster import (
    ForecastPoint,
    PressureForecast,
    PressurePredictor,
    ProcessForecast,
    ProcessForecastPoint,
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

__all__ = [
    "ForecastPoint",
    "PressureForecast",
    "PressurePredictor",
    "ProcessForecast",
    "ProcessForecastPoint",
    "ThresholdBreachEstimate",
    "TrajectoryState",
    "PredictionReport",
    "compute_ols_regression",
    "estimate_breach_timeline",
    "predict_candidate_processes",
    "predict_system_pressure",
    "run_prediction",
]
