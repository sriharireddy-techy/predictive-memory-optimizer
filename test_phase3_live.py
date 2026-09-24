from src.storage.database import MetricsDatabase
from src.analysis.service import analyze_active_processes, analyze_system_trend


def main():
    db = MetricsDatabase("data/memory_monitor.db")

    print("=" * 100)
    print("PHASE 3 - LIVE MEMORY TREND ANALYSIS")
    print("=" * 100)

    # --------------------------------------------------
    # SYSTEM TREND
    # --------------------------------------------------
    system_trend = analyze_system_trend(db)

    print("\nSYSTEM MEMORY TREND")
    print("-" * 100)

    print(f"Samples          : {system_trend.sample_count}")
    print(f"Duration         : {system_trend.duration_seconds:.2f} seconds")
    print(f"Start RAM        : {system_trend.start_percent:.2f}%")
    print(f"End RAM          : {system_trend.end_percent:.2f}%")
    print(f"Net Change       : {system_trend.net_change_percent:+.2f}%")
    print(f"Rate             : {system_trend.rate_percent_s:+.4f}%/sec")
    print(f"Classification   : {system_trend.classification.value}")
    print(f"Explanation      : {system_trend.explanation}")

    # --------------------------------------------------
    # PROCESS TRENDS
    # --------------------------------------------------
    results = analyze_active_processes(
        db,
        window_seconds=60
    )

    print("\nPROCESS MEMORY TRENDS")
    print("-" * 100)

    print(
        f"{'PID':<8}"
        f"{'Process':<25}"
        f"{'Samples':<9}"
        f"{'Start MB':<12}"
        f"{'End MB':<12}"
        f"{'Change MB':<12}"
        f"{'Growth MB/s':<14}"
        f"{'Classification':<22}"
    )

    print("-" * 100)

    for trend in results[:15]:
        print(
            f"{trend.pid:<8}"
            f"{trend.name[:24]:<25}"
            f"{trend.sample_count:<9}"
            f"{trend.start_memory_mb:<12.2f}"
            f"{trend.end_memory_mb:<12.2f}"
            f"{trend.net_change_mb:<12.2f}"
            f"{trend.growth_rate_mb_s:<14.4f}"
            f"{trend.classification.value:<22}"
        )

    print("-" * 100)

    # --------------------------------------------------
    # DETAILED EXPLANATIONS
    # --------------------------------------------------
    print("\nDETAILED ANALYSIS")
    print("-" * 100)

    for trend in results[:5]:
        print(f"\nPID: {trend.pid}")
        print(f"Process: {trend.name}")
        print(f"Classification: {trend.classification.value}")
        print(f"Growth rate: {trend.growth_rate_mb_s:.4f} MB/s")
        print(f"Persistence: {trend.persistence_score:.2%}")
        print(f"Explanation: {trend.explanation}")

    db.close()


if __name__ == "__main__":
    main()