from src.storage.database import MetricsDatabase
from src.detection.service import run_detection


def main():
    db = MetricsDatabase("data/memory_monitor.db")

    print("=" * 100)
    print("PHASE 4 - LIVE MEMORY DETECTION")
    print("=" * 100)

    report = run_detection(
        db,
        window_seconds=60.0
    )

    # --------------------------------------------------
    # SYSTEM MEMORY PRESSURE
    # --------------------------------------------------

    pressure = report.system_pressure

    print("\nSYSTEM MEMORY PRESSURE")
    print("-" * 100)

    print(f"RAM Usage       : {pressure.ram_used_percent:.2f}%")
    print(f"Available RAM   : {pressure.available_ram_mb:.2f} MB")
    print(f"Swap Usage      : {pressure.swap_used_percent:.2f}%")
    print(f"Pressure State  : {pressure.state.value}")
    print(f"Pressure Score  : {pressure.score:.2f}")

    print("\nContributing Factors:")

    if pressure.contributing_factors:
        for factor in pressure.contributing_factors:
            print(f"  - {factor}")
    else:
        print("  None")

    print(f"\nExplanation:")
    print(pressure.explanation)

    # --------------------------------------------------
    # ABNORMAL PROCESSES
    # --------------------------------------------------

    print("\n\nABNORMAL PROCESSES")
    print("-" * 100)

    if not report.abnormal_processes:
        print("No abnormal processes detected.")
    else:
        for process in report.abnormal_processes:
            print(f"\nPID          : {process.pid}")
            print(f"Process      : {process.name}")
            print(f"Abnormal     : {process.is_abnormal}")
            print(f"Severity     : {process.severity.value}")

            print("Flags        :")
            for flag in process.flags:
                print(f"  - {flag.value}")

            print(f"Explanation  : {process.explanation}")

    # --------------------------------------------------
    # PROCESS IMPACT SCORES
    # --------------------------------------------------

    print("\n\nPROCESS IMPACT SCORES")
    print("-" * 100)

    if not report.ranked_impact_scores:
        print("No process impact scores available.")
    else:
        print(
            f"{'Rank':<8}"
            f"{'PID':<8}"
            f"{'Process':<25}"
            f"{'Score':<10}"
        )

        print("-" * 100)

        for impact in report.ranked_impact_scores[:15]:
            print(
                f"{impact.rank:<8}"
                f"{impact.pid:<8}"
                f"{impact.name[:24]:<25}"
                f"{impact.impact_score:<10.4f}"
            )

    # --------------------------------------------------
    # HIGHEST IMPACT PROCESS
    # --------------------------------------------------

    print("\n\nHIGHEST IMPACT PROCESS")
    print("-" * 100)

    highest = report.highest_impact_process

    if highest:
        print(f"PID          : {highest.pid}")
        print(f"Process      : {highest.name}")
        print(f"Impact Score : {highest.impact_score:.4f}")
        print(f"Rank         : {highest.rank}")
    else:
        print("No high-impact process identified.")

    print("\n" + "=" * 100)

    db.close()


if __name__ == "__main__":
    main()