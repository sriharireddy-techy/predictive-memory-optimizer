"""
Phase 6: Safe Resource Recommendation Engine Component.
"""

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
from src.optimization.service import (
    generate_optimization_plan,
    run_optimization,
)

__all__ = [
    "PROTECTED_PIDS",
    "PROTECTED_PROCESS_NAMES",
    "ActionRecommendation",
    "ActionType",
    "OptimizationPlan",
    "RecommendationEngine",
    "RiskPriority",
    "generate_optimization_plan",
    "is_protected_process",
    "run_optimization",
]
