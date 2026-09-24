"""
Phase 6 Service: End-to-End Resource Optimization and Safe Advisory Coordination.

Synthesizes:
- DetectionReport from Phase 4 (Memory Pressure, Abnormal Growth, Impact Scores)
- PredictionReport from Phase 5 (Trajectory Forecasting, Threshold Milestones)
To produce an actionable, ordered, non-destructive OptimizationPlan.
"""

from typing import Optional

from src.detection.service import DetectionReport, run_detection
from src.optimization.recommendation_engine import (
    ActionRecommendation,
    ActionType,
    OptimizationPlan,
    RecommendationEngine,
    RiskPriority,
    is_protected_process,
)
from src.prediction.service import PredictionReport, run_prediction
from src.storage.database import MetricsDatabase


def generate_optimization_plan(
    detection_report: DetectionReport,
    prediction_report: Optional[PredictionReport] = None,
    top_candidates_limit: int = 5,
    engine: Optional[RecommendationEngine] = None,
) -> OptimizationPlan:
    """
    Generate an advisory optimization plan from pre-computed detection and prediction reports.
    """
    engine = engine or RecommendationEngine(top_candidates_limit=top_candidates_limit)

    forecast = prediction_report.system_forecast if prediction_report else None

    return engine.generate_plan(
        system_pressure=detection_report.system_pressure,
        forecast=forecast,
        ranked_impacts=detection_report.ranked_impact_scores,
        abnormal_processes=detection_report.abnormal_processes,
    )


def run_optimization(
    db: MetricsDatabase,
    window_seconds: float = 120.0,
    top_candidates_limit: int = 5,
    engine: Optional[RecommendationEngine] = None,
) -> OptimizationPlan:
    """
    Execute full Phase 6 advisory recommendation pipeline against historical database records:
    1. Runs Phase 4 detection (pressure, abnormal growth, impact scores).
    2. Runs Phase 5 prediction (trajectories, time-to-threshold).
    3. Synthesizes inputs into a safe, ordered OptimizationPlan with simulated memory savings.

    Args:
        db: Active MetricsDatabase instance.
        window_seconds: Historical window in seconds to analyze.
        top_candidates_limit: Number of top candidate processes to evaluate.
        engine: Optional custom RecommendationEngine instance.

    Returns:
        OptimizationPlan: Prioritized advisory plan with simulation metrics.
    """
    detection = run_detection(db=db, window_seconds=window_seconds)
    prediction = run_prediction(db=db, window_seconds=window_seconds)

    return generate_optimization_plan(
        detection_report=detection,
        prediction_report=prediction,
        top_candidates_limit=top_candidates_limit,
        engine=engine,
    )
