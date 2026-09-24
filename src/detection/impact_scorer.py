"""
Phase 4: Composite Process Impact Scorer.

Calculates the explainable Composite Process Impact Score:
    Impact_i = w1 * M_hat_i + w2 * G_hat_i + w3 * P_i

Where:
- M_hat_i in [0, 1] is normalized current physical memory usage (RSS).
- G_hat_i in [0, 1] is normalized positive growth velocity.
- P_i in [0, 1] is growth persistence factor.
- w1, w2, w3 are configurable weights satisfying w1 + w2 + w3 = 1.0.
"""

from dataclasses import dataclass, asdict
from typing import Any, Dict, List, Optional

from src.analysis.trend_analyzer import ProcessTrend


@dataclass(frozen=True)
class ImpactWeights:
    """Configurable weights for the Composite Process Impact Score."""
    w_memory: float = 0.40
    w_growth: float = 0.35
    w_persistence: float = 0.25

    def __post_init__(self) -> None:
        if self.w_memory < 0 or self.w_growth < 0 or self.w_persistence < 0:
            raise ValueError(
                f"Impact weights must be non-negative. Given: "
                f"w_memory={self.w_memory}, w_growth={self.w_growth}, w_persistence={self.w_persistence}"
            )
        total = self.w_memory + self.w_growth + self.w_persistence
        if abs(total - 1.0) > 1e-4:
            raise ValueError(f"Impact weights must sum to 1.0 (current sum: {total:.4f}).")

    def to_dict(self) -> Dict[str, float]:
        return asdict(self)


@dataclass(frozen=True)
class ProcessImpact:
    """Comprehensive impact score assessment for an individual process."""
    pid: int
    name: str
    rank: int
    impact_score: float
    current_rss_mb: float
    growth_rate_mb_s: float
    persistence_score: float
    normalized_memory: float
    normalized_growth: float
    normalized_persistence: float
    weights: ImpactWeights
    explanation: str

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["weights"] = self.weights.to_dict()
        return d


class ProcessImpactScorer:
    """
    Computes transparent, normalized impact scores across active processes
    to rank contributors to system memory pressure.
    """

    def __init__(
        self,
        weights: Optional[ImpactWeights] = None,
        reference_growth_rate_mb_s: float = 10.0,
    ):
        """
        Args:
            weights: Configurable weighting terms (defaults to w1=0.40, w2=0.35, w3=0.25).
            reference_growth_rate_mb_s: Reference growth velocity in MB/s for normalization
                when absolute velocity scaling is preferred or cohort max is small.
        """
        self.weights = weights or ImpactWeights()
        self.reference_growth_rate_mb_s = max(0.1, reference_growth_rate_mb_s)

    def score_single(
        self,
        trend: ProcessTrend,
        total_ram_mb: Optional[float] = None,
        max_cohort_growth: Optional[float] = None,
        current_rss_mb: Optional[float] = None,
    ) -> ProcessImpact:
        """
        Score a single process trend without ranking against a wider cohort.
        """
        rss = current_rss_mb if current_rss_mb is not None else trend.end_memory_mb
        rate = trend.growth_rate_mb_s
        persistence = trend.persistence_score

        # 1. Normalize Memory (M_hat in [0, 1])
        if total_ram_mb and total_ram_mb > 0:
            m_hat = min(1.0, max(0.0, rss / total_ram_mb))
        else:
            # Fallback heuristic: 16 GB typical maximum baseline
            m_hat = min(1.0, max(0.0, rss / 16384.0))

        # 2. Normalize Growth Velocity (G_hat in [0, 1])
        # Non-positive growth contributes 0 to expansion pressure
        if rate <= 0:
            g_hat = 0.0
        else:
            growth_scale = max_cohort_growth if (max_cohort_growth and max_cohort_growth > 0) else self.reference_growth_rate_mb_s
            g_hat = min(1.0, max(0.0, rate / growth_scale))

        # 3. Normalize Persistence (P in [0, 1])
        # If the process is not growing, persistence of positive growth is effectively zero
        if rate <= 0:
            p_hat = 0.0
        else:
            p_hat = min(1.0, max(0.0, persistence))

        # 4. Composite Impact Score
        score = (
            self.weights.w_memory * m_hat
            + self.weights.w_growth * g_hat
            + self.weights.w_persistence * p_hat
        )
        score = round(min(1.0, max(0.0, score)), 4)

        explanation = (
            f"Impact Score: {score:.4f} = "
            f"({self.weights.w_memory:.2f} * {m_hat:.4f} [RSS: {rss:.1f} MB]) + "
            f"({self.weights.w_growth:.2f} * {g_hat:.4f} [Growth: +{max(0.0, rate):.2f} MB/s]) + "
            f"({self.weights.w_persistence:.2f} * {p_hat:.4f} [Persistence: {p_hat * 100:.1f}%])"
        )

        return ProcessImpact(
            pid=trend.pid,
            name=trend.name,
            rank=1,
            impact_score=score,
            current_rss_mb=round(rss, 2),
            growth_rate_mb_s=round(rate, 4),
            persistence_score=round(persistence, 4),
            normalized_memory=round(m_hat, 4),
            normalized_growth=round(g_hat, 4),
            normalized_persistence=round(p_hat, 4),
            weights=self.weights,
            explanation=explanation,
        )

    def score_cohort(
        self,
        trends: List[ProcessTrend],
        total_ram_mb: Optional[float] = None,
        use_cohort_max_growth: bool = True,
    ) -> List[ProcessImpact]:
        """
        Score a cohort of active processes and assign rankings (1 = highest impact).

        Args:
            trends: ProcessTrend objects for active processes.
            total_ram_mb: Total host RAM in MB for memory normalization.
            use_cohort_max_growth: If True, scales positive growth relative to the
                highest observed growth rate in the cohort (or reference if larger).

        Returns:
            List[ProcessImpact]: Ranked processes ordered from highest to lowest impact.
        """
        if not trends:
            return []

        # Find max observed RSS if total_ram_mb is not available
        max_rss = max((t.end_memory_mb for t in trends), default=1.0)
        norm_ram_denom = total_ram_mb if (total_ram_mb and total_ram_mb > 0) else max(max_rss, 1.0)

        # Find max positive growth rate in cohort
        positive_rates = [t.growth_rate_mb_s for t in trends if t.growth_rate_mb_s > 0]
        max_cohort_growth = max(positive_rates) if positive_rates else 0.0

        if use_cohort_max_growth and max_cohort_growth > 0:
            growth_scale = max_cohort_growth
        else:
            growth_scale = self.reference_growth_rate_mb_s

        preliminary: List[ProcessImpact] = []
        for t in trends:
            rss = t.end_memory_mb
            rate = t.growth_rate_mb_s
            persistence = t.persistence_score

            m_hat = min(1.0, max(0.0, rss / norm_ram_denom))

            if rate <= 0:
                g_hat = 0.0
                p_hat = 0.0
            else:
                g_hat = min(1.0, max(0.0, rate / growth_scale))
                p_hat = min(1.0, max(0.0, persistence))

            score = (
                self.weights.w_memory * m_hat
                + self.weights.w_growth * g_hat
                + self.weights.w_persistence * p_hat
            )
            score = round(min(1.0, max(0.0, score)), 4)

            explanation = (
                f"Impact Score: {score:.4f} = "
                f"({self.weights.w_memory:.2f} * {m_hat:.4f} [RSS: {rss:.1f} MB]) + "
                f"({self.weights.w_growth:.2f} * {g_hat:.4f} [Growth: +{max(0.0, rate):.2f} MB/s]) + "
                f"({self.weights.w_persistence:.2f} * {p_hat:.4f} [Persistence: {p_hat * 100:.1f}%])"
            )

            preliminary.append(
                ProcessImpact(
                    pid=t.pid,
                    name=t.name,
                    rank=0,
                    impact_score=score,
                    current_rss_mb=round(rss, 2),
                    growth_rate_mb_s=round(rate, 4),
                    persistence_score=round(persistence, 4),
                    normalized_memory=round(m_hat, 4),
                    normalized_growth=round(g_hat, 4),
                    normalized_persistence=round(p_hat, 4),
                    weights=self.weights,
                    explanation=explanation,
                )
            )

        # Sort descending by impact_score, break ties with growth_rate then current_rss
        preliminary.sort(
            key=lambda item: (item.impact_score, item.growth_rate_mb_s, item.current_rss_mb),
            reverse=True,
        )

        # Assign 1-indexed ranks and format explanation with rank
        ranked_results: List[ProcessImpact] = []
        for idx, item in enumerate(preliminary, start=1):
            ranked_item = ProcessImpact(
                pid=item.pid,
                name=item.name,
                rank=idx,
                impact_score=item.impact_score,
                current_rss_mb=item.current_rss_mb,
                growth_rate_mb_s=item.growth_rate_mb_s,
                persistence_score=item.persistence_score,
                normalized_memory=item.normalized_memory,
                normalized_growth=item.normalized_growth,
                normalized_persistence=item.normalized_persistence,
                weights=item.weights,
                explanation=f"[Rank {idx}] {item.explanation}",
            )
            ranked_results.append(ranked_item)

        return ranked_results
