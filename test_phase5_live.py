"""
Phase 5 Live Demonstration Script:
Evaluates real-time Short-Term Predictive Forecasting and Time-to-Exhaustion.
"""

from src.storage.database import MetricsDatabase
from src.prediction.service import run_prediction
from src.storage.service import record_current_snapshot


def main():
    db_path = "data/memory_monitor.db"
    db = MetricsDatabase(db_path)

    print("=" * 110)
    print("PHASE 5 - PREDICTIVE MEMORY PRESSURE FORECASTING & TIME-TO-EXHAUSTION")
    print("=" * 110)

    # 1. Capture current live snapshot into database
    print("\n[+] Capturing current live snapshot into database...")
    record_current_snapshot(db, top_n=25)

    # 2. Run prediction assessment over last 3 minutes of history
    print("[+] Running Phase 5 predictive forecasting engine...")
    report = run_prediction(db, window_seconds=180.0, horizons=[30.0, 60.0, 120.0, 300.0])

    forecast = report.system_forecast
    print("\nSYSTEM MEMORY PRESSURE TRAJECTORY FORECAST")
    print("-" * 110)
    print(f"Current Memory State    : {forecast.current_percent:.2f}% ({forecast.current_used_mb:.1f} MB / {forecast.total_ram_mb:.1f} MB)")
    print(f"Available Physical RAM  : {forecast.current_available_mb:.1f} MB")
    print(f"Trajectory Status       : {forecast.trajectory.value}")
    print(f"Growth Velocity         : {forecast.rate_percent_s:+.4f}%/s ({forecast.rate_used_mb_s:+.2f} MB/s)")
    print(f"Goodness of Fit (R^2)   : {forecast.r_squared:.4f}")
    print(f"Confidence Score        : {forecast.confidence_score * 100:.1f}%")
    print(f"Explanation             : {forecast.explanation}")

    # 3. Threshold Breach Timelines
    print("\nTHRESHOLD BREACH ESTIMATES")
    print("-" * 110)
    wb = forecast.warning_breach
    cb = forecast.critical_breach
    print(f"Warning Threshold (85%) : {'[ACTIVE]' if wb.is_already_breached else (f'{wb.seconds_to_breach:.1f}s' if wb.is_breach_predicted else 'Not Projected')}")
    print(f"Critical Threshold (92%): {'[ACTIVE]' if cb.is_already_breached else (f'{cb.seconds_to_breach:.1f}s' if cb.is_breach_predicted else 'Not Projected')}")
    print(f"Status Summary          : {'CRITICAL IMMINENT!' if report.is_critical_imminent else 'Stable operating envelope'}")

    # 4. Multi-Horizon Projections
    print("\nPROJECTED HORIZONS")
    print("-" * 110)
    print(f"{'Horizon':<12}{'Projected RAM %':<20}{'Projected Used MB':<22}{'Projected Available MB':<25}")
    print("-" * 110)
    for p in forecast.projections:
        print(f"+{int(p.horizon_seconds)}s{'':<8}{p.projected_ram_percent:.2f}%{'':<13}{p.projected_used_mb:.1f} MB{'':<12}{p.projected_available_mb:.1f} MB")

    # 5. Process Milestone Forecasts (Top Candidate Processes)
    if report.process_forecasts:
        print("\nTOP CANDIDATE PROCESS TRAJECTORIES & MILESTONES")
        print("-" * 110)
        print(f"{'PID':<8}{'Process Name':<25}{'Current RSS':<15}{'Growth MB/s':<15}{'R^2':<10}{'Time to 1GB':<15}{'Time to 2GB':<15}")
        print("-" * 110)
        for pf in report.process_forecasts[:8]:
            t1 = f"{pf.time_to_1gb_s:.1f}s" if pf.time_to_1gb_s else "--"
            t2 = f"{pf.time_to_2gb_s:.1f}s" if pf.time_to_2gb_s else "--"
            print(f"{pf.pid:<8}{pf.name[:24]:<25}{pf.current_rss_mb:<15.1f}{pf.growth_rate_mb_s:<15.2f}{pf.r_squared:<10.3f}{t1:<15}{t2:<15}")

    print("=" * 110)


if __name__ == "__main__":
    main()
