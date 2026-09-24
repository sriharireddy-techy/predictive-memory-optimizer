"""
Phase 6: Safe Resource Recommendation Engine.

Generates risk-prioritized, explainable, safe recommendations without taking
unverified or disruptive termination actions.

Key Guarantees:
1. Advisory Only: No autonomous SIGKILL, TerminateProcess, or disruptive OS commands.
2. Protection of Core OS Processes: Whitelisted kernel, subsystem, and security processes
   are strictly guarded with PROHIBITED_SYSTEM_CRITICAL status.
3. Transparent Explanations: Every recommendation provides mathematical justification,
   projected reclaimable memory, and simulated post-remediation system RAM %.
"""

from dataclasses import dataclass, asdict
from enum import Enum
import time
from typing import Any, Dict, List, Optional, Set

from src.detection.growth_detector import AbnormalProcessGrowth, GrowthFlag, GrowthSeverity
from src.detection.impact_scorer import ProcessImpact
from src.detection.pressure_analyzer import PressureState, SystemPressure
from src.prediction.forecaster import PressureForecast, TrajectoryState


class ActionType(str, Enum):
    """Safe, human-in-the-loop recommendation categories."""
    NO_ACTION = "NO_ACTION"
    MONITOR_CLOSELY = "MONITOR_CLOSELY"
    CLEAR_APPLICATION_CACHE = "CLEAR_APPLICATION_CACHE"
    REDUCE_WORKLOAD = "REDUCE_WORKLOAD"
    RESTART_APPLICATION = "RESTART_APPLICATION"
    CLOSE_BACKGROUND_APPLICATION = "CLOSE_BACKGROUND_APPLICATION"
    INVESTIGATE_ACCUMULATION = "INVESTIGATE_ACCUMULATION"
    PROHIBITED_SYSTEM_CRITICAL = "PROHIBITED_SYSTEM_CRITICAL"


class RiskPriority(str, Enum):
    """Urgency level of a recommendation."""
    NONE = "NONE"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


# Protected operating system and security processes that must never be terminated
PROTECTED_PROCESS_NAMES: Set[str] = {
    # Core Windows Kernel & Session Managers
    "system",
    "system idle process",
    "registry",
    "smss.exe",
    "csrss.exe",
    "wininit.exe",
    "services.exe",
    "lsass.exe",
    "svchost.exe",
    "dwm.exe",
    "winlogon.exe",
    "explorer.exe",
    "explorer",
    "fontdrvhost.exe",
    "sihost.exe",
    "taskhostw.exe",
    "runtimebroker.exe",
    "shellexperiencehost.exe",
    "searchhost.exe",
    "startmenuexperiencehost.exe",
    "spoolsv.exe",
    # Windows Security & Anti-Malware
    "msmpeng.exe",
    "nissrv.exe",
    "securityhealthservice.exe",
    "securityhealthsystray.exe",
    # Memory Management Subsystem
    "memcompression",
    # Core Linux/Unix Essentials (cross-platform safety)
    "systemd",
    "init",
    "kthreadd",
    "sshd",
    "dbus-daemon",
    "cron",
}

# Protected system PIDs
PROTECTED_PIDS: Set[int] = {0, 4}


def is_protected_process(pid: int, name: str) -> bool:
    """
    Determine if a process is a protected OS or security-critical task.
    """
    if pid in PROTECTED_PIDS:
        return True
    clean_name = name.strip().lower()
    base_name = clean_name[:-4] if clean_name.endswith(".exe") else clean_name
    return clean_name in PROTECTED_PROCESS_NAMES or base_name in PROTECTED_PROCESS_NAMES


@dataclass(frozen=True)
class ActionRecommendation:
    """An explainable, safe advisory recommendation for an individual process."""
    recommendation_id: str
    timestamp: float
    pid: int
    process_name: str
    is_protected_system_process: bool
    action_type: ActionType
    urgency: RiskPriority
    current_rss_mb: float
    projected_reclaimable_mb: float
    simulated_post_ram_percent: float
    confidence_score: float
    title: str
    reasoning: str
    mitigation_steps: List[str]

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["action_type"] = self.action_type.value
        d["urgency"] = self.urgency.value
        return d


@dataclass(frozen=True)
class OptimizationPlan:
    """Consolidated, prioritized remediation plan for system memory optimization."""
    timestamp: float
    system_pressure_state: PressureState
    trajectory_state: TrajectoryState
    overall_urgency: RiskPriority
    recommendations: List[ActionRecommendation]
    total_potential_reclaim_mb: float
    projected_system_ram_percent_after_remediation: float
    summary: str
    safety_notice: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "system_pressure_state": self.system_pressure_state.value,
            "trajectory_state": self.trajectory_state.value,
            "overall_urgency": self.overall_urgency.value,
            "recommendations": [r.to_dict() for r in self.recommendations],
            "total_potential_reclaim_mb": self.total_potential_reclaim_mb,
            "projected_system_ram_percent_after_remediation": self.projected_system_ram_percent_after_remediation,
            "summary": self.summary,
            "safety_notice": self.safety_notice,
        }


class RecommendationEngine:
    """
    Synthesizes Phase 4 (Detection) and Phase 5 (Prediction) telemetry to construct
    an ordered, non-destructive advisory optimization plan.
    """

    SAFETY_DISCLAIMER = (
        "ADVISORY ONLY: The Predictive Memory Optimizer does not autonomously terminate, "
        "kill, or modify processes. All recommendations require human review and authorization."
    )

    def __init__(self, top_candidates_limit: int = 5):
        self.top_candidates_limit = top_candidates_limit

    def generate_plan(
        self,
        system_pressure: SystemPressure,
        forecast: Optional[PressureForecast] = None,
        ranked_impacts: Optional[List[ProcessImpact]] = None,
        abnormal_processes: Optional[List[AbnormalProcessGrowth]] = None,
    ) -> OptimizationPlan:
        """
        Generate a comprehensive, safe recommendation plan.

        Args:
            system_pressure: Instantaneous & evaluated system pressure from Phase 4.
            forecast: Short-term predictive forecast from Phase 5.
            ranked_impacts: Ranked process impacts from Phase 4.
            abnormal_processes: Detected abnormal growth patterns from Phase 4.

        Returns:
            OptimizationPlan: Ordered advisory actions with simulated memory savings.
        """
        now = time.time()
        traj = forecast.trajectory if forecast else TrajectoryState.STABLE
        p_state = system_pressure.state

        # 1. Determine Overall Plan Urgency
        if p_state == PressureState.CRITICAL or traj == TrajectoryState.CRITICAL_IMMINENT:
            overall_urgency = RiskPriority.CRITICAL
        elif p_state == PressureState.HIGH or traj == TrajectoryState.RAPID_INCREASE:
            overall_urgency = RiskPriority.HIGH
        elif p_state == PressureState.MODERATE or traj == TrajectoryState.GRADUAL_INCREASE:
            overall_urgency = RiskPriority.MEDIUM
        else:
            overall_urgency = RiskPriority.LOW if traj == TrajectoryState.IMPROVING else RiskPriority.NONE

        # Index abnormal processes by PID for quick lookup
        abnormal_map: Dict[int, AbnormalProcessGrowth] = {}
        if abnormal_processes:
            for ab in abnormal_processes:
                abnormal_map[ab.pid] = ab

        recommendations: List[ActionRecommendation] = []
        cur_used_mb = system_pressure.used_ram_mb
        total_ram_mb = max(1.0, system_pressure.total_ram_mb)

        candidate_impacts = (ranked_impacts or [])[: self.top_candidates_limit]

        # If system is completely healthy and no candidate is severely expanding
        if overall_urgency == RiskPriority.NONE and not any(ab.is_abnormal for ab in abnormal_map.values()):
            return OptimizationPlan(
                timestamp=now,
                system_pressure_state=p_state,
                trajectory_state=traj,
                overall_urgency=RiskPriority.NONE,
                recommendations=[],
                total_potential_reclaim_mb=0.0,
                projected_system_ram_percent_after_remediation=system_pressure.ram_used_percent,
                summary="System memory utilization is healthy and within nominal thresholds. No remediation required.",
                safety_notice=self.SAFETY_DISCLAIMER,
            )

        simulated_used_mb = cur_used_mb

        for idx, impact in enumerate(candidate_impacts, start=1):
            pid = impact.pid
            name = impact.name
            rss = impact.current_rss_mb
            growth = impact.growth_rate_mb_s
            ab = abnormal_map.get(pid)

            is_protected = is_protected_process(pid, name)

            # Reclaimable estimation heuristic:
            # For non-protected processes: graceful close reclaims full RSS,
            # restart/cache clear reclaims ~60% of elevated footprint.
            if is_protected:
                reclaimable_mb = 0.0  # Cannot be reclaimed via termination
                simulated_pct = round((simulated_used_mb / total_ram_mb) * 100.0, 2)
            else:
                reclaimable_mb = round(rss * 0.85, 1)  # Expected realistic memory recovery
                simulated_used_mb = max(0.0, simulated_used_mb - reclaimable_mb)
                simulated_pct = round((simulated_used_mb / total_ram_mb) * 100.0, 2)

            # Formulate specific action and steps
            rec = self._formulate_process_recommendation(
                rec_id=f"REC-{int(now)}-{idx}",
                timestamp=now,
                impact=impact,
                abnormal_info=ab,
                is_protected=is_protected,
                overall_urgency=overall_urgency,
                reclaimable_mb=reclaimable_mb,
                simulated_pct=simulated_pct,
            )
            recommendations.append(rec)

        # Calculate total potential savings
        total_reclaim = sum(r.projected_reclaimable_mb for r in recommendations if not r.is_protected_system_process)
        post_rem_pct = round(max(0.0, (cur_used_mb - total_reclaim) / total_ram_mb) * 100.0, 2)

        summary = (
            f"Evaluated {len(recommendations)} candidate processes under {p_state.value} pressure "
            f"and {traj.value} trajectory. Overall Urgency: {overall_urgency.value}. "
            f"Total potential recoverable memory from non-critical tasks: {total_reclaim:.1f} MB "
            f"(simulated system RAM: {system_pressure.ram_used_percent:.1f}% -> {post_rem_pct:.1f}%)."
        )

        return OptimizationPlan(
            timestamp=now,
            system_pressure_state=p_state,
            trajectory_state=traj,
            overall_urgency=overall_urgency,
            recommendations=recommendations,
            total_potential_reclaim_mb=round(total_reclaim, 1),
            projected_system_ram_percent_after_remediation=post_rem_pct,
            summary=summary,
            safety_notice=self.SAFETY_DISCLAIMER,
        )

    def _formulate_process_recommendation(
        self,
        rec_id: str,
        timestamp: float,
        impact: ProcessImpact,
        abnormal_info: Optional[AbnormalProcessGrowth],
        is_protected: bool,
        overall_urgency: RiskPriority,
        reclaimable_mb: float,
        simulated_pct: float,
    ) -> ActionRecommendation:
        """Build an individual ActionRecommendation based on safety and metrics."""
        pid = impact.pid
        name = impact.name
        rss = impact.current_rss_mb
        rate = impact.growth_rate_mb_s
        score = impact.impact_score

        # Case 1: Protected OS/System process
        if is_protected:
            return ActionRecommendation(
                recommendation_id=rec_id,
                timestamp=timestamp,
                pid=pid,
                process_name=name,
                is_protected_system_process=True,
                action_type=ActionType.PROHIBITED_SYSTEM_CRITICAL,
                urgency=RiskPriority.LOW,
                current_rss_mb=rss,
                projected_reclaimable_mb=0.0,
                simulated_post_ram_percent=simulated_pct,
                confidence_score=0.99,
                title=f"Protected System Process: {name} (PID {pid})",
                reasoning=(
                    f"{name} is an essential operating system component (PID {pid}, RSS: {rss:.1f} MB). "
                    "Termination or suspension is strictly prohibited to maintain OS stability."
                ),
                mitigation_steps=[
                    "DO NOT TERMINATE: Termination will cause OS instability or blue screen.",
                    "If memory continues growing, inspect host background services or restart non-essential user software.",
                    "Allow Windows memory manager (Working Set trimming / Paging) to manage working set naturally.",
                ],
            )

        # Case 2: Abnormal sustained or rapid growth detected
        has_abnormal_growth = abnormal_info and abnormal_info.is_abnormal

        if has_abnormal_growth and abnormal_info is not None:
            if GrowthFlag.RAPID_GROWTH in abnormal_info.flags or rate >= 5.0:
                action = ActionType.RESTART_APPLICATION
                urgency = RiskPriority.CRITICAL if overall_urgency in (RiskPriority.CRITICAL, RiskPriority.HIGH) else RiskPriority.HIGH
                title = f"Restart Rapidly Expanding Application: {name}"
                reasoning = (
                    f"{name} (PID {pid}) is expanding rapidly (+{rate:.2f} MB/s) with impact score {score:.4f}. "
                    f"Consuming {rss:.1f} MB. A controlled restart will safely release accumulated buffers."
                )
                steps = [
                    f"Save ongoing work in {name} immediately.",
                    f"Perform a clean, graceful application restart of {name}.",
                    "If expansion recurs after restart, inspect application logs or report an unbounded buffer growth issue.",
                ]
            elif GrowthFlag.SUSTAINED_GROWTH in abnormal_info.flags:
                action = ActionType.CLEAR_APPLICATION_CACHE
                urgency = RiskPriority.HIGH if overall_urgency in (RiskPriority.CRITICAL, RiskPriority.HIGH) else RiskPriority.MEDIUM
                title = f"Clear Application Cache / Purge Buffers: {name}"
                reasoning = (
                    f"{name} (PID {pid}) exhibits sustained accumulation over observation period "
                    f"({abnormal_info.persistence_score * 100:.1f}% positive intervals, RSS: {rss:.1f} MB). "
                    f"Potential reclaimable memory: {reclaimable_mb:.1f} MB."
                )
                steps = [
                    f"Trigger internal cache cleanup or close unused project workspaces / tabs inside {name}.",
                    f"If the application is an IDE or browser, close unneeded background tabs or idle extensions.",
                    "Monitor subsequent memory rate to verify stabilization.",
                ]
            else:
                action = ActionType.INVESTIGATE_ACCUMULATION
                urgency = RiskPriority.MEDIUM
                title = f"Investigate Memory Growth: {name}"
                reasoning = (
                    f"{name} (PID {pid}) shows gradual memory accumulation (Net change: +{impact.growth_rate_mb_s:.2f} MB/s). "
                    f"Current RSS: {rss:.1f} MB."
                )
                steps = [
                    f"Check application activity logs for pending background tasks in {name}.",
                    "Observe memory footprint over the next 5 minutes.",
                ]

        # Case 3: Large static memory footprint without rapid growth
        elif rss >= 1024.0:
            action = ActionType.REDUCE_WORKLOAD
            urgency = RiskPriority.MEDIUM if overall_urgency != RiskPriority.LOW else RiskPriority.LOW
            title = f"Reduce Workload Footprint: {name}"
            reasoning = (
                f"{name} (PID {pid}) holds a substantial static memory footprint ({rss:.1f} MB) "
                f"accounting for a significant portion of physical RAM."
            )
            steps = [
                f"Close idle documents, heavy datasets, or inactive browser windows in {name}.",
                "Consider delegating heavy computing workloads to background batches.",
            ]

        # Case 4: Moderate footprint or stable
        else:
            action = ActionType.MONITOR_CLOSELY
            urgency = RiskPriority.LOW
            title = f"Monitor Resource Usage: {name}"
            reasoning = (
                f"{name} (PID {pid}) is operating within expected parameters (RSS: {rss:.1f} MB, "
                f"Growth: {rate:+.2f} MB/s). Observation recommended."
            )
            steps = [
                "No immediate intervention required.",
                "Continue automated background monitoring.",
            ]

        confidence = round(min(1.0, max(0.5, impact.impact_score + 0.3)), 2)

        return ActionRecommendation(
            recommendation_id=rec_id,
            timestamp=timestamp,
            pid=pid,
            process_name=name,
            is_protected_system_process=False,
            action_type=action,
            urgency=urgency,
            current_rss_mb=rss,
            projected_reclaimable_mb=reclaimable_mb,
            simulated_post_ram_percent=simulated_pct,
            confidence_score=confidence,
            title=title,
            reasoning=reasoning,
            mitigation_steps=steps,
        )
