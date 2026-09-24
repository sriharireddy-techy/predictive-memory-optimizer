"""
Phase 6 Live Demonstration Script:
Evaluates real-time Safe Advisory Recommendations & Simulated Remediation.
"""

from src.storage.database import MetricsDatabase
from src.optimization.service import run_optimization
from src.storage.service import record_current_snapshot


def main():
    db_path = "data/memory_monitor.db"
    db = MetricsDatabase(db_path)

    print("=" * 110)
    print("PHASE 6 - SAFE RESOURCE RECOMMENDATION ENGINE (ADVISORY-ONLY)")
    print("=" * 110)

    # 1. Capture current live snapshot into database
    print("\n[+] Capturing current live snapshot into database...")
    record_current_snapshot(db, top_n=25)

    # 2. Run full optimization pipeline
    print("[+] Synthesizing Phase 4 Detection & Phase 5 Prediction into Advisory Plan...")
    plan = run_optimization(db, window_seconds=180.0, top_candidates_limit=6)

    # 3. Print Overall System Plan
    print("\nOPTIMIZATION PLAN SUMMARY")
    print("-" * 110)
    print(f"System Pressure State   : {plan.system_pressure_state.value}")
    print(f"Predicted Trajectory    : {plan.trajectory_state.value}")
    print(f"Overall Plan Urgency    : {plan.overall_urgency.value}")
    print(f"Total Potential Reclaim : {plan.total_potential_reclaim_mb:.1f} MB (non-critical candidates)")
    print(f"Projected Post-Action % : {plan.projected_system_ram_percent_after_remediation:.2f}% RAM")
    print(f"Executive Summary       : {plan.summary}")
    print(f"\nSAFETY NOTICE           :\n{plan.safety_notice}")

    # 4. Action Recommendations
    print("\nORDERED ADVISORY RECOMMENDATIONS")
    print("-" * 110)
    if not plan.recommendations:
        print("No immediate actions required. System memory envelope is healthy and stable.")
    else:
        for idx, rec in enumerate(plan.recommendations, start=1):
            protected_tag = "[OS PROTECTED]" if rec.is_protected_system_process else "[USER APP]"
            print(f"\n{idx}. {protected_tag} {rec.title}")
            print(f"   PID: {rec.pid:<6} | Action: {rec.action_type.value:<25} | Urgency: {rec.urgency.value}")
            print(f"   Current RSS: {rec.current_rss_mb:.1f} MB | Reclaimable: {rec.projected_reclaimable_mb:.1f} MB | Simulated Post RAM: {rec.simulated_post_ram_percent:.1f}%")
            print(f"   Reasoning: {rec.reasoning}")
            print("   Recommended Mitigation Steps:")
            for step in rec.mitigation_steps:
                print(f"     -> {step}")

    print("\n" + "=" * 110)


if __name__ == "__main__":
    main()
