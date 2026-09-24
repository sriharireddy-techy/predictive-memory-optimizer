"""
Phase 4: Memory Pressure & Process Impact Scoring Component.
"""

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

__all__ = [
    "AbnormalGrowthDetector",
    "AbnormalProcessGrowth",
    "GrowthDetectionConfig",
    "GrowthFlag",
    "GrowthSeverity",
    "ImpactWeights",
    "ProcessImpact",
    "ProcessImpactScorer",
    "MemoryPressureAnalyzer",
    "PressureState",
    "PressureThresholds",
    "SystemPressure",
    "DetectionReport",
    "assess_system_pressure",
    "detect_abnormal_processes",
    "run_detection",
    "score_process_impacts",
]
