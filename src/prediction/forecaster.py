"""
Phase 5: Short-Term Predictive Forecasting and Time-to-Exhaustion Engine.

Provides transparent mathematical and statistical forecasting:
1. Ordinary Least Squares (OLS) regression with R^2 confidence estimation.
2. Near-future state projections across multi-step horizons (+30s, +60s, +120s, +300s).
3. Explainable Time-to-Critical-Threshold (TTC) & Time-to-Exhaustion (TTE).
4. Trajectory state classification: STABLE, IMPROVING, GRADUAL_INCREASE,
   RAPID_INCREASE, or CRITICAL_IMMINENT.
"""

from dataclasses import dataclass, asdict
from enum import Enum
import math
import time
from typing import Any, Dict, List, Optional, Tuple


class TrajectoryState(str, Enum):
    """Explainable trajectory status of memory consumption."""
    STABLE = "STABLE"
    IMPROVING = "IMPROVING"
    GRADUAL_INCREASE = "GRADUAL_INCREASE"
    RAPID_INCREASE = "RAPID_INCREASE"
    CRITICAL_IMMINENT = "CRITICAL_IMMINENT"


@dataclass(frozen=True)
class ForecastPoint:
    """Projected system state at a specific future horizon."""
    timestamp: float
    horizon_seconds: float
    projected_ram_percent: float
    projected_available_mb: float
    projected_used_mb: float

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ThresholdBreachEstimate:
    """Estimated timeline to cross a critical memory threshold."""
    threshold_name: str
    target_value: float
    current_value: float
    is_already_breached: bool
    is_breach_predicted: bool
    seconds_to_breach: Optional[float]
    breach_timestamp: Optional[float]
    explanation: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class PressureForecast:
    """Consolidated short-term predictive forecast of system memory pressure."""
    timestamp: float
    current_percent: float
    current_available_mb: float
    current_used_mb: float
    total_ram_mb: float
    rate_percent_s: float
    rate_used_mb_s: float
    r_squared: float
    confidence_score: float
    trajectory: TrajectoryState
    projections: List[ForecastPoint]
    warning_breach: ThresholdBreachEstimate
    critical_breach: ThresholdBreachEstimate
    explanation: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "current_percent": self.current_percent,
            "current_available_mb": self.current_available_mb,
            "current_used_mb": self.current_used_mb,
            "total_ram_mb": self.total_ram_mb,
            "rate_percent_s": self.rate_percent_s,
            "rate_used_mb_s": self.rate_used_mb_s,
            "r_squared": self.r_squared,
            "confidence_score": self.confidence_score,
            "trajectory": self.trajectory.value,
            "projections": [p.to_dict() for p in self.projections],
            "warning_breach": self.warning_breach.to_dict(),
            "critical_breach": self.critical_breach.to_dict(),
            "explanation": self.explanation,
        }


@dataclass(frozen=True)
class ProcessForecastPoint:
    """Projected process RSS at a future horizon."""
    horizon_seconds: float
    projected_rss_mb: float

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ProcessForecast:
    """Individual process memory projection and threshold milestones."""
    pid: int
    name: str
    current_rss_mb: float
    growth_rate_mb_s: float
    r_squared: float
    projections: List[ProcessForecastPoint]
    time_to_1gb_s: Optional[float]
    time_to_2gb_s: Optional[float]
    explanation: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "pid": self.pid,
            "name": self.name,
            "current_rss_mb": self.current_rss_mb,
            "growth_rate_mb_s": self.growth_rate_mb_s,
            "r_squared": self.r_squared,
            "projections": [p.to_dict() for p in self.projections],
            "time_to_1gb_s": self.time_to_1gb_s,
            "time_to_2gb_s": self.time_to_2gb_s,
            "explanation": self.explanation,
        }


def compute_ols_regression(
    time_points: List[float],
    values: List[float],
) -> Tuple[float, float, float]:
    """
    Computes slope, intercept, and R^2 goodness-of-fit using Ordinary Least Squares:
        y = slope * t + intercept

    Returns:
        Tuple of (slope, intercept, r_squared)
    """
    n = len(time_points)
    if n < 2:
        return 0.0, values[0] if values else 0.0, 0.0

    mean_t = sum(time_points) / n
    mean_y = sum(values) / n

    denom = sum((t - mean_t) ** 2 for t in time_points)
    if denom <= 1e-9:
        return 0.0, mean_y, 0.0

    slope = sum((t - mean_t) * (y - mean_y) for t, y in zip(time_points, values)) / denom
    intercept = mean_y - slope * mean_t

    # Calculate Coefficient of Determination (R^2)
    ss_tot = sum((y - mean_y) ** 2 for y in values)
    ss_res = sum((y - (intercept + slope * t)) ** 2 for t, y in zip(time_points, values))

    if ss_tot <= 1e-9:
        # All y values identical -> perfect horizontal fit
        r_squared = 1.0 if ss_res <= 1e-9 else 0.0
    else:
        r_squared = max(0.0, min(1.0, 1.0 - (ss_res / ss_tot)))

    return slope, intercept, r_squared


def estimate_breach_timeline(
    current_value: float,
    rate_per_sec: float,
    target_threshold: float,
    threshold_name: str,
    current_timestamp: float,
    is_upper_limit: bool = True,
) -> ThresholdBreachEstimate:
    """
    Calculate explainable time remaining before crossing target threshold.

    Args:
        current_value: Current metric value (e.g. RAM % or available MB).
        rate_per_sec: Rate of change per second (positive = increasing).
        target_threshold: Threshold boundary.
        threshold_name: Descriptive name for reporting.
        current_timestamp: Reference epoch timestamp.
        is_upper_limit: True if threshold is breached by exceeding (e.g. 92% RAM),
                        False if breached by falling below (e.g. 500 MB available).
    """
    if is_upper_limit:
        already_breached = current_value >= target_threshold
        will_breach = not already_breached and rate_per_sec > 0.0001
        distance = target_threshold - current_value
        rate = rate_per_sec
    else:
        already_breached = current_value <= target_threshold
        will_breach = not already_breached and rate_per_sec < -0.0001
        distance = current_value - target_threshold
        rate = abs(rate_per_sec)

    if already_breached:
        return ThresholdBreachEstimate(
            threshold_name=threshold_name,
            target_value=round(target_threshold, 2),
            current_value=round(current_value, 2),
            is_already_breached=True,
            is_breach_predicted=True,
            seconds_to_breach=0.0,
            breach_timestamp=current_timestamp,
            explanation=f"{threshold_name} ({target_threshold:.1f}) is currently actively breached.",
        )

    if will_breach and rate > 0:
        seconds = distance / rate
        breach_ts = current_timestamp + seconds
        mins = seconds / 60.0
        return ThresholdBreachEstimate(
            threshold_name=threshold_name,
            target_value=round(target_threshold, 2),
            current_value=round(current_value, 2),
            is_already_breached=False,
            is_breach_predicted=True,
            seconds_to_breach=round(seconds, 1),
            breach_timestamp=round(breach_ts, 2),
            explanation=(
                f"{threshold_name} ({target_threshold:.1f}) projected to be reached in "
                f"{seconds:.1f}s (~{mins:.1f} min) at current trajectory."
            ),
        )

    return ThresholdBreachEstimate(
        threshold_name=threshold_name,
        target_value=round(target_threshold, 2),
        current_value=round(current_value, 2),
        is_already_breached=False,
        is_breach_predicted=False,
        seconds_to_breach=None,
        breach_timestamp=None,
        explanation=f"{threshold_name} ({target_threshold:.1f}) is not projected to be breached under current trend.",
    )


class PressurePredictor:
    """
    Predictive engine that forecasts system memory trajectories and time-to-threshold.
    """

    DEFAULT_HORIZONS = [30.0, 60.0, 120.0, 300.0]

    def __init__(
        self,
        warning_percent_threshold: float = 85.0,
        critical_percent_threshold: float = 92.0,
        critical_available_mb: float = 500.0,
        rapid_rate_percent_s: float = 0.15,
        min_samples: int = 3,
    ):
        self.warning_threshold = warning_percent_threshold
        self.critical_threshold = critical_percent_threshold
        self.critical_available_mb = critical_available_mb
        self.rapid_rate_percent_s = rapid_rate_percent_s
        self.min_samples = min_samples

    def predict_system(
        self,
        history: List[Dict[str, Any]],
        horizons: Optional[List[float]] = None,
    ) -> PressureForecast:
        """
        Forecast short-term system pressure based on historical telemetry.

        Args:
            history: List of system metrics dictionaries with timestamp, percent_used,
                     used_ram_mb, available_ram_mb, total_ram_mb.
            horizons: Future projection intervals in seconds (e.g. [30, 60, 120, 300]).

        Returns:
            PressureForecast: Detailed projections, breach estimates, and trajectory state.
        """
        horizons = horizons or self.DEFAULT_HORIZONS

        # Sanitize and extract time-series
        clean_pts: List[Tuple[float, float, float, float, float]] = []
        for r in history:
            t = r.get("timestamp")
            pct = r.get("percent_used")
            used = r.get("used_ram_mb")
            avail = r.get("available_ram_mb")
            tot = r.get("total_ram_mb")
            if None in (t, pct, used, avail, tot):
                continue
            try:
                clean_pts.append((float(t), float(pct), float(used), float(avail), float(tot)))
            except (ValueError, TypeError):
                continue

        clean_pts.sort(key=lambda x: x[0])

        if len(clean_pts) < self.min_samples:
            # Fallback for insufficient telemetry
            now = clean_pts[-1][0] if clean_pts else time.time()
            cur_pct = clean_pts[-1][1] if clean_pts else 0.0
            cur_used = clean_pts[-1][2] if clean_pts else 0.0
            cur_avail = clean_pts[-1][3] if clean_pts else 16384.0
            total_ram = clean_pts[-1][4] if clean_pts else 16384.0

            return PressureForecast(
                timestamp=now,
                current_percent=round(cur_pct, 2),
                current_available_mb=round(cur_avail, 2),
                current_used_mb=round(cur_used, 2),
                total_ram_mb=round(total_ram, 2),
                rate_percent_s=0.0,
                rate_used_mb_s=0.0,
                r_squared=0.0,
                confidence_score=0.0,
                trajectory=TrajectoryState.STABLE,
                projections=[],
                warning_breach=ThresholdBreachEstimate(
                    threshold_name="Warning Threshold (85%)",
                    target_value=self.warning_threshold,
                    current_value=round(cur_pct, 2),
                    is_already_breached=cur_pct >= self.warning_threshold,
                    is_breach_predicted=False,
                    seconds_to_breach=None,
                    breach_timestamp=None,
                    explanation="Insufficient historical samples for regression.",
                ),
                critical_breach=ThresholdBreachEstimate(
                    threshold_name="Critical Threshold (92%)",
                    target_value=self.critical_threshold,
                    current_value=round(cur_pct, 2),
                    is_already_breached=cur_pct >= self.critical_threshold,
                    is_breach_predicted=False,
                    seconds_to_breach=None,
                    breach_timestamp=None,
                    explanation="Insufficient historical samples for regression.",
                ),
                explanation=f"Insufficient history ({len(clean_pts)} samples, minimum {self.min_samples} required).",
            )

        t_series = [p[0] for p in clean_pts]
        pct_series = [p[1] for p in clean_pts]
        used_series = [p[2] for p in clean_pts]

        cur_t = t_series[-1]
        cur_pct = pct_series[-1]
        cur_used = used_series[-1]
        cur_avail = clean_pts[-1][3]
        total_ram = clean_pts[-1][4]

        # 1. Linear OLS Regression on RAM Percent and Used MB
        slope_pct, _, r2_pct = compute_ols_regression(t_series, pct_series)
        slope_used, _, r2_used = compute_ols_regression(t_series, used_series)

        # Confidence: combine sample count scale with R^2 fit
        sample_factor = min(1.0, len(clean_pts) / 10.0)
        confidence = round(r2_pct * sample_factor, 3)

        # 2. Estimate Threshold Breaches
        warn_est = estimate_breach_timeline(
            current_value=cur_pct,
            rate_per_sec=slope_pct,
            target_threshold=self.warning_threshold,
            threshold_name=f"Warning Threshold ({self.warning_threshold:.1f}%)",
            current_timestamp=cur_t,
            is_upper_limit=True,
        )

        crit_est = estimate_breach_timeline(
            current_value=cur_pct,
            rate_per_sec=slope_pct,
            target_threshold=self.critical_threshold,
            threshold_name=f"Critical Threshold ({self.critical_threshold:.1f}%)",
            current_timestamp=cur_t,
            is_upper_limit=True,
        )

        # 3. Horizon Projections
        projections: List[ForecastPoint] = []
        for h in horizons:
            proj_pct = max(0.0, min(100.0, cur_pct + (slope_pct * h)))
            proj_used = max(0.0, min(total_ram, cur_used + (slope_used * h)))
            proj_avail = max(0.0, total_ram - proj_used)

            projections.append(
                ForecastPoint(
                    timestamp=round(cur_t + h, 2),
                    horizon_seconds=h,
                    projected_ram_percent=round(proj_pct, 2),
                    projected_available_mb=round(proj_avail, 2),
                    projected_used_mb=round(proj_used, 2),
                )
            )

        # 4. Trajectory State Classification
        is_crit_imminent = (
            crit_est.is_already_breached
            or (crit_est.is_breach_predicted and crit_est.seconds_to_breach is not None and crit_est.seconds_to_breach <= 300.0)
            or cur_avail <= self.critical_available_mb
        )

        if is_crit_imminent:
            trajectory = TrajectoryState.CRITICAL_IMMINENT
        elif slope_pct >= self.rapid_rate_percent_s:
            trajectory = TrajectoryState.RAPID_INCREASE
        elif slope_pct > 0.02:
            trajectory = TrajectoryState.GRADUAL_INCREASE
        elif slope_pct < -0.02:
            trajectory = TrajectoryState.IMPROVING
        else:
            trajectory = TrajectoryState.STABLE

        # 5. Explainable Justification String
        explanation_parts = [
            f"Trajectory is {trajectory.value} (Rate: {slope_pct:+.4f}%/s [{slope_used:+.2f} MB/s], R^2={r2_pct:.3f}, Confidence={confidence:.2f})."
        ]
        if crit_est.is_already_breached:
            explanation_parts.append("Critical memory saturation is actively present.")
        elif crit_est.is_breach_predicted and crit_est.seconds_to_breach is not None:
            explanation_parts.append(
                f"Critical saturation predicted in {crit_est.seconds_to_breach:.1f}s (~{crit_est.seconds_to_breach/60:.1f} min)."
            )
        elif warn_est.is_breach_predicted and warn_est.seconds_to_breach is not None:
            explanation_parts.append(
                f"Warning threshold predicted in {warn_est.seconds_to_breach:.1f}s."
            )
        elif trajectory == TrajectoryState.IMPROVING:
            explanation_parts.append("Memory utilization is steadily declining.")
        else:
            explanation_parts.append("Memory consumption remains in steady state.")

        return PressureForecast(
            timestamp=cur_t,
            current_percent=round(cur_pct, 2),
            current_available_mb=round(cur_avail, 2),
            current_used_mb=round(cur_used, 2),
            total_ram_mb=round(total_ram, 2),
            rate_percent_s=round(slope_pct, 4),
            rate_used_mb_s=round(slope_used, 3),
            r_squared=round(r2_pct, 4),
            confidence_score=confidence,
            trajectory=trajectory,
            projections=projections,
            warning_breach=warn_est,
            critical_breach=crit_est,
            explanation=" ".join(explanation_parts),
        )

    def predict_process(
        self,
        history: List[Dict[str, Any]],
        horizons: Optional[List[float]] = None,
        pid: Optional[int] = None,
        name: Optional[str] = None,
    ) -> ProcessForecast:
        """
        Forecast future memory consumption for an individual process.
        """
        horizons = horizons or self.DEFAULT_HORIZONS
        valid: List[Tuple[float, float]] = []
        resolved_pid = pid or 0
        resolved_name = name or "unknown"

        for r in history:
            t = r.get("timestamp")
            m = r.get("rss_mb")
            if t is None or m is None:
                continue
            try:
                valid.append((float(t), float(m)))
                if not resolved_pid and r.get("pid"):
                    resolved_pid = int(r["pid"])
                if resolved_name == "unknown" and r.get("name"):
                    resolved_name = str(r["name"])
            except (ValueError, TypeError):
                continue

        valid.sort(key=lambda x: x[0])

        if len(valid) < 2:
            cur_m = valid[0][1] if valid else 0.0
            return ProcessForecast(
                pid=resolved_pid,
                name=resolved_name,
                current_rss_mb=round(cur_m, 2),
                growth_rate_mb_s=0.0,
                r_squared=0.0,
                projections=[],
                time_to_1gb_s=None,
                time_to_2gb_s=None,
                explanation="Insufficient samples for process forecasting.",
            )

        t_pts = [v[0] for v in valid]
        m_pts = [v[1] for v in valid]
        cur_m = m_pts[-1]

        slope, _, r2 = compute_ols_regression(t_pts, m_pts)

        # Milestone estimations (1 GB = 1024 MB, 2 GB = 2048 MB)
        t_1gb = None
        t_2gb = None
        if slope > 0.01:
            if cur_m < 1024.0:
                t_1gb = round((1024.0 - cur_m) / slope, 1)
            if cur_m < 2048.0:
                t_2gb = round((2048.0 - cur_m) / slope, 1)

        projections = [
            ProcessForecastPoint(
                horizon_seconds=h,
                projected_rss_mb=round(max(0.0, cur_m + (slope * h)), 2),
            )
            for h in horizons
        ]

        explanation = (
            f"Process {resolved_name} (PID {resolved_pid}) growth velocity: {slope:+.2f} MB/s (R^2={r2:.3f}). "
            f"Current RSS: {cur_m:.1f} MB. "
        )
        if t_1gb is not None:
            explanation += f"Expected to reach 1 GB in {t_1gb:.1f}s. "
        if t_2gb is not None:
            explanation += f"Expected to reach 2 GB in {t_2gb:.1f}s. "

        return ProcessForecast(
            pid=resolved_pid,
            name=resolved_name,
            current_rss_mb=round(cur_m, 2),
            growth_rate_mb_s=round(slope, 4),
            r_squared=round(r2, 4),
            projections=projections,
            time_to_1gb_s=t_1gb,
            time_to_2gb_s=t_2gb,
            explanation=explanation.strip(),
        )
