"""
Phase 3: Memory Behaviour and Growth Analysis Component.

Provides explainable, statistical time-series analysis of memory dynamics:
- Instantaneous and net growth rate (dM/dt in MB/s)
- Ordinary Least Squares (OLS) linear slope estimation
- Growth persistence factor across consecutive observation intervals
- Explainable classification: STABLE, FLUCTUATING, GRADUALLY_INCREASING,
  SUSTAINED_GROWTH, RAPID_GROWTH, or INSUFFICIENT_DATA.
- Comprehensive handling of irregular timestamps, noise, and invalid measurements.
"""

from dataclasses import dataclass, asdict
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


class TrendClassification(str, Enum):
    """Explainable behavioral categories for process and system memory dynamics."""
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"
    STABLE = "STABLE"
    FLUCTUATING = "FLUCTUATING"
    GRADUALLY_INCREASING = "GRADUALLY_INCREASING"
    SUSTAINED_GROWTH = "SUSTAINED_GROWTH"
    RAPID_GROWTH = "RAPID_GROWTH"


@dataclass(frozen=True)
class ProcessTrend:
    """Statistical summary of historical memory behavior for a single process."""
    pid: int
    name: str
    sample_count: int
    duration_seconds: float
    start_memory_mb: float
    end_memory_mb: float
    net_change_mb: float
    growth_rate_mb_s: float
    persistence_score: float
    classification: TrendClassification
    explanation: str

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["classification"] = self.classification.value
        return d


@dataclass(frozen=True)
class SystemTrend:
    """Statistical summary of host-wide memory utilization trends."""
    sample_count: int
    duration_seconds: float
    start_percent: float
    end_percent: float
    net_change_percent: float
    rate_percent_s: float
    classification: TrendClassification
    explanation: str

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["classification"] = self.classification.value
        return d


def compute_linear_slope(time_points: List[float], values: List[float]) -> float:
    """
    Calculate the slope of best fit using Ordinary Least Squares (OLS) regression:
    Slope = Cov(t, y) / Var(t) = sum((t_i - mean_t) * (y_i - mean_y)) / sum((t_i - mean_t)^2)

    Returns:
        float: Linear growth rate per second. Returns 0.0 if variance is zero.
    """
    n = len(time_points)
    if n < 2:
        return 0.0

    mean_t = sum(time_points) / n
    mean_y = sum(values) / n

    numerator = sum((t - mean_t) * (y - mean_y) for t, y in zip(time_points, values))
    denominator = sum((t - mean_t) ** 2 for t in time_points)

    if denominator <= 1e-9:
        return 0.0

    return numerator / denominator


def calculate_persistence(
    time_points: List[float],
    values: List[float],
    noise_threshold_mb: float = 0.1,
) -> Tuple[float, float, int, int, int]:
    """
    Calculate growth persistence and decrease ratios across consecutive valid time intervals:
    - Persistence (positive ratio) = positive_steps / total_valid_steps
    - Decrease ratio = negative_steps / total_valid_steps

    Args:
        time_points: Monotonically increasing timestamps in seconds.
        values: Memory values in MB.
        noise_threshold_mb: Minimum change in MB required to count as positive or negative step.

    Returns:
        Tuple of (persistence_ratio, decrease_ratio, positive_steps, flat_steps, total_valid_steps)
    """
    if len(values) < 2:
        return 0.0, 0.0, 0, 0, 0

    positive_steps = 0
    negative_steps = 0
    flat_steps = 0
    valid_steps = 0

    for i in range(1, len(values)):
        dt = time_points[i] - time_points[i - 1]
        if dt <= 0:
            continue

        dm = values[i] - values[i - 1]
        valid_steps += 1
        if dm > noise_threshold_mb:
            positive_steps += 1
        elif dm < -noise_threshold_mb:
            negative_steps += 1
        else:
            flat_steps += 1

    if valid_steps == 0:
        return 0.0, 0.0, 0, 0, 0

    pos_ratio = round(positive_steps / valid_steps, 4)
    neg_ratio = round(negative_steps / valid_steps, 4)
    return pos_ratio, neg_ratio, positive_steps, flat_steps, valid_steps


def sanitize_process_samples(
    history: List[Dict[str, Any]],
) -> Tuple[List[float], List[float], str, int]:
    """
    Validate, sanitize, and sort raw process history records:
    - Filters out None or negative values
    - Sorts strictly by timestamp
    - Drops consecutive duplicate timestamps
    """
    valid_samples: List[Tuple[float, float]] = []
    pid = 0
    name = "unknown"

    for r in history:
        t = r.get("timestamp")
        m = r.get("rss_mb")
        if t is None or m is None:
            continue
        try:
            t_val = float(t)
            m_val = float(m)
        except (ValueError, TypeError):
            continue

        if m_val < 0:
            continue

        valid_samples.append((t_val, m_val))
        if not pid and r.get("pid"):
            pid = int(r["pid"])
        if name == "unknown" and r.get("name"):
            name = str(r["name"])

    # Sort strictly by timestamp ascending
    valid_samples.sort(key=lambda x: x[0])

    # Deduplicate consecutive samples with identical timestamps
    deduped_t: List[float] = []
    deduped_m: List[float] = []
    last_t = -1.0

    for t_val, m_val in valid_samples:
        if t_val != last_t:
            deduped_t.append(t_val)
            deduped_m.append(m_val)
            last_t = t_val

    return deduped_t, deduped_m, name, pid


class MemoryTrendAnalyzer:
    """
    Statistical analyzer that evaluates historical time-series memory data
    for processes and overall host systems.
    """

    def __init__(
        self,
        min_samples: int = 3,
        min_duration_s: float = 1.0,
        noise_threshold_mb: float = 0.5,
        sustained_persistence_threshold: float = 0.75,
        gradual_persistence_threshold: float = 0.50,
        rapid_growth_rate_threshold: float = 5.0,  # MB/s
    ):
        """
        Args:
            min_samples: Minimum historical points required for meaningful analysis.
            min_duration_s: Minimum duration required between first and last sample.
            noise_threshold_mb: Filter threshold to ignore negligible memory jitter.
            sustained_persistence_threshold: Persistence ratio threshold for SUSTAINED_GROWTH.
            gradual_persistence_threshold: Persistence ratio threshold for GRADUALLY_INCREASING.
            rapid_growth_rate_threshold: Growth velocity threshold for RAPID_GROWTH.
        """
        self.min_samples = min_samples
        self.min_duration_s = min_duration_s
        self.noise_threshold_mb = noise_threshold_mb
        self.sustained_persistence_threshold = sustained_persistence_threshold
        self.gradual_persistence_threshold = gradual_persistence_threshold
        self.rapid_growth_rate_threshold = rapid_growth_rate_threshold

    def analyze_process(
        self,
        history: List[Dict[str, Any]],
        pid: Optional[int] = None,
        name: Optional[str] = None,
    ) -> ProcessTrend:
        """
        Analyze the memory behavior of a specific process across its historical records.
        """
        t_points, m_points, extracted_name, extracted_pid = sanitize_process_samples(history)
        resolved_pid = pid or extracted_pid
        resolved_name = name or extracted_name

        sample_count = len(t_points)
        if sample_count < self.min_samples:
            return ProcessTrend(
                pid=resolved_pid,
                name=resolved_name,
                sample_count=sample_count,
                duration_seconds=0.0,
                start_memory_mb=m_points[0] if m_points else 0.0,
                end_memory_mb=m_points[-1] if m_points else 0.0,
                net_change_mb=0.0,
                growth_rate_mb_s=0.0,
                persistence_score=0.0,
                classification=TrendClassification.INSUFFICIENT_DATA,
                explanation=f"Insufficient samples ({sample_count} available, minimum {self.min_samples} required).",
            )

        duration = t_points[-1] - t_points[0]
        if duration < self.min_duration_s:
            return ProcessTrend(
                pid=resolved_pid,
                name=resolved_name,
                sample_count=sample_count,
                duration_seconds=duration,
                start_memory_mb=m_points[0],
                end_memory_mb=m_points[-1],
                net_change_mb=round(m_points[-1] - m_points[0], 2),
                growth_rate_mb_s=0.0,
                persistence_score=0.0,
                classification=TrendClassification.INSUFFICIENT_DATA,
                explanation=f"Sampling duration ({duration:.2f}s) is too short for reliable trend estimation.",
            )

        start_m = m_points[0]
        end_m = m_points[-1]
        net_change = round(end_m - start_m, 2)

        # 1. Linear slope estimation via OLS
        growth_rate = round(compute_linear_slope(t_points, m_points), 4)

        # 2. Persistence calculation
        pos_ratio, neg_ratio, pos_steps, flat_steps, total_steps = calculate_persistence(
            t_points, m_points, noise_threshold_mb=self.noise_threshold_mb
        )

        # 3. Rule-based classification
        # Check for stable state (net change is negligible and slope is near-zero)
        is_net_flat = abs(net_change) <= self.noise_threshold_mb
        is_slope_flat = abs(growth_rate) <= 0.05

        # Check if process is fluctuating (oscillating drops and rises)
        # If negative steps make up 25% or more of steps, memory is fluctuating/recovering
        is_oscillating = neg_ratio >= 0.25 and pos_ratio > 0.0

        if is_net_flat and is_slope_flat:
            classification = TrendClassification.STABLE
            explanation = (
                f"Memory is stable: net change of {net_change:+.2f} MB across {duration:.1f}s "
                f"with negligible slope ({growth_rate:+.4f} MB/s)."
            )
        elif is_oscillating:
            classification = TrendClassification.FLUCTUATING
            explanation = (
                f"Fluctuating memory: significant downward reversals ({neg_ratio:.0%} of intervals) "
                f"counteracting growth ({pos_ratio:.0%} intervals), net change {net_change:+.2f} MB."
            )
        elif growth_rate > 0 and net_change > self.noise_threshold_mb:
            if growth_rate >= self.rapid_growth_rate_threshold and pos_ratio >= self.sustained_persistence_threshold:
                classification = TrendClassification.RAPID_GROWTH
                explanation = (
                    f"Rapid memory growth detected: high velocity {growth_rate:+.2f} MB/s "
                    f"and strong persistence ({pos_ratio:.0%} of {total_steps} intervals)."
                )
            elif pos_ratio >= self.sustained_persistence_threshold:
                classification = TrendClassification.SUSTAINED_GROWTH
                explanation = (
                    f"Sustained memory growth observed: growth rate {growth_rate:+.4f} MB/s, "
                    f"increasing in {pos_steps}/{total_steps} intervals ({pos_ratio:.0%})."
                )
            elif pos_ratio >= self.gradual_persistence_threshold:
                classification = TrendClassification.GRADUALLY_INCREASING
                explanation = (
                    f"Gradually increasing memory: rate {growth_rate:+.4f} MB/s "
                    f"with moderate persistence ({pos_ratio:.0%})."
                )
            else:
                classification = TrendClassification.FLUCTUATING
                explanation = (
                    f"Fluctuating memory: overall positive change ({net_change:+.2f} MB) but "
                    f"low persistence ({pos_ratio:.0%}), indicating non-sustained spikes."
                )
        else:
            classification = TrendClassification.FLUCTUATING
            explanation = (
                f"Fluctuating or decreasing memory: net change {net_change:+.2f} MB, "
                f"slope {growth_rate:+.4f} MB/s, persistence {pos_ratio:.0%}."
            )

        return ProcessTrend(
            pid=resolved_pid,
            name=resolved_name,
            sample_count=sample_count,
            duration_seconds=round(duration, 2),
            start_memory_mb=round(start_m, 2),
            end_memory_mb=round(end_m, 2),
            net_change_mb=net_change,
            growth_rate_mb_s=growth_rate,
            persistence_score=pos_ratio,
            classification=classification,
            explanation=explanation,
        )

    def analyze_system(
        self,
        history: List[Dict[str, Any]],
    ) -> SystemTrend:
        """
        Analyze the host system's memory pressure trajectory across historical snapshots.
        """
        valid_points: List[Tuple[float, float]] = []
        for r in history:
            t = r.get("timestamp")
            p = r.get("percent_used")
            if t is not None and p is not None:
                try:
                    valid_points.append((float(t), float(p)))
                except (ValueError, TypeError):
                    continue

        valid_points.sort(key=lambda x: x[0])
        sample_count = len(valid_points)

        if sample_count < self.min_samples:
            return SystemTrend(
                sample_count=sample_count,
                duration_seconds=0.0,
                start_percent=valid_points[0][1] if valid_points else 0.0,
                end_percent=valid_points[-1][1] if valid_points else 0.0,
                net_change_percent=0.0,
                rate_percent_s=0.0,
                classification=TrendClassification.INSUFFICIENT_DATA,
                explanation=f"Insufficient system history ({sample_count} points, minimum {self.min_samples} required).",
            )

        t_points = [p[0] for p in valid_points]
        pct_points = [p[1] for p in valid_points]

        duration = t_points[-1] - t_points[0]
        if duration < self.min_duration_s:
            return SystemTrend(
                sample_count=sample_count,
                duration_seconds=duration,
                start_percent=pct_points[0],
                end_percent=pct_points[-1],
                net_change_percent=round(pct_points[-1] - pct_points[0], 2),
                rate_percent_s=0.0,
                classification=TrendClassification.INSUFFICIENT_DATA,
                explanation=f"System observation window ({duration:.2f}s) is too short.",
            )

        start_pct = pct_points[0]
        end_pct = pct_points[-1]
        net_pct = round(end_pct - start_pct, 2)
        slope = round(compute_linear_slope(t_points, pct_points), 4)

        pos_ratio, neg_ratio, pos_steps, flat_steps, total_steps = calculate_persistence(
            t_points, pct_points, noise_threshold_mb=0.1
        )

        if abs(net_pct) < 1.0 and abs(slope) < 0.05:
            classification = TrendClassification.STABLE
            explanation = f"System RAM utilization is stable around {end_pct:.1f}% (net change {net_pct:+.1f}%)."
        elif slope > 0 and net_pct > 1.0:
            if pos_ratio >= self.sustained_persistence_threshold:
                classification = TrendClassification.SUSTAINED_GROWTH
                explanation = (
                    f"System RAM pressure is steadily increasing: {slope:+.3f}%/s "
                    f"over {duration:.1f}s (persistence {pos_ratio:.0%})."
                )
            else:
                classification = TrendClassification.GRADUALLY_INCREASING
                explanation = (
                    f"System RAM pressure shows gradual increase: net {net_pct:+.1f}% "
                    f"with moderate persistence {pos_ratio:.0%}."
                )
        else:
            classification = TrendClassification.FLUCTUATING
            explanation = f"System RAM utilization fluctuating: net change {net_pct:+.1f}%, slope {slope:+.3f}%/s."

        return SystemTrend(
            sample_count=sample_count,
            duration_seconds=round(duration, 2),
            start_percent=round(start_pct, 2),
            end_percent=round(end_pct, 2),
            net_change_percent=net_pct,
            rate_percent_s=slope,
            classification=classification,
            explanation=explanation,
        )
