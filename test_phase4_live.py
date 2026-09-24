"""
Phase 4 Live Demonstration Script:
Evaluates real-time Memory Pressure, Abnormal Growth, and Ranked Impact Scores.
"""

from src.storage.database import MetricsDatabase
from src.detection.service import run_detection
from src.collector.monitor import collect_snapshot
from src.storage.service import record_current_snapshot


def main():
    db_path = "data/memory_monitor.db"
    db = MetricsDatabase(db_path)

    print("=" * 110)
    print("PHASE 4 - MEMORY PRESSURE & PROCESS IMPACT SCORING")
    print("=" * 110)

    # 1. Ensure at least one fresh live snapshot is recorded into the database
    print("\n[+] Capturing current live snapshot into database...")
    record_current_snapshot(db, top_n=25)

    # 2. Run detection assessment
    print("[+] Running Phase 4 detection and impact scoring analysis...")
    report = run_detection(db, window_seconds=120.0)

    # 3. System Memory Pressure Evaluation
    pressure = report.system_pressure
    print("\nSYSTEM MEMORY PRESSURE EVALUATION")
    print("-" * 110)
    print(f"State                   : {pressure.state.value}")
    print(f"Composite Pressure Score: {pressure.score:.2f} / 100.0")
    print(f"Physical RAM Used       : {pressure.ram_used_percent:.2f}% ({pressure.used_ram_mb:.1f} MB / {pressure.total_ram_mb:.1f} MB)")
    print(f"Available Physical RAM  : {pressure.available_ram_mb:.1f} MB")
    print(f"Swap Space Used         : {pressure.swap_used_percent:.2f}% ({pressure.swap_used_mb:.1f} MB)")
    print(f"Rate of RAM Change      : {pressure.rate_percent_s:+.4f}%/s")
    print(f"Explanation             : {pressure.explanation}")
    if pressure.contributing_factors:
        print("Contributing Factors    :")
        for factor in pressure.contributing_factors:
            print(f"  * {factor}")

    # 4. Abnormal Process Growth Detection
    print("\nABNORMAL PROCESS GROWTH DETECTIONS")
    print("-" * 110)
    abnormal = [p for p in report.abnormal_processes if p.is_abnormal]
    if abnormal:
        for p in abnormal:
            flags_str = ", ".join(f.value for f in p.flags)
            print(f"PID {p.pid:<6} | {p.name:<25} | Severity: {p.severity.value:<8} | Flags: {flags_str}")
            print(f"   Rate: +{p.growth_rate_mb_s:.2f} MB/s | Persistence: {p.persistence_score*100:.1f}% | RSS: {p.current_rss_mb:.1f} MB")
            for r in p.reasons:
                print(f"   - {r}")
    else:
        print("No processes currently exhibiting abnormal or sustained growth patterns.")

    # 5. Composite Process Impact Scores (Top 10)
    print("\nTOP PROCESSES BY COMPOSITE IMPACT SCORE")
    print("Formulation: Impact = (0.40 * M_hat) + (0.35 * G_hat) + (0.25 * P_hat)")
    print("-" * 110)
    print(
        f"{'Rank':<6}"
        f"{'PID':<8}"
        f"{'Process Name':<25}"
        f"{'RSS (MB)':<12}"
        f"{'Growth MB/s':<14}"
        f"{'Persistence':<14}"
        f"{'Impact Score':<14}"
    )
    print("-" * 110)

    for impact in report.ranked_impact_scores[:10]:
        pct_str = f"{impact.persistence_score * 100:.1f}%"
        print(
            f"{impact.rank:<6}"
            f"{impact.pid:<8}"
            f"{impact.name[:24]:<25}"
            f"{impact.current_rss_mb:<12.1f}"
            f"{impact.growth_rate_mb_s:<14.2f}"
            f"{pct_str:<14}"
            f"{impact.impact_score:<14.4f}"
        )

    print("=" * 110)


if __name__ == "__main__":
    main()
