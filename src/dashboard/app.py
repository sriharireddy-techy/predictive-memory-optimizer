"""
Phase 7: Memory Intelligence Dashboard Main Application.

Entrypoint for the 4-page Streamlit dashboard interface:
- Page 1: Overview (KPIs, historical memory trends, forecast summary, telemetry insights)
- Page 2: Process Explorer (searchable, filterable process table with composite impact scores)
- Page 3: Forecasting (multi-horizon OLS projection curves, breach estimates, statistical diagnostics)
- Page 4: Recommendations (risk-prioritized, explainable safe remediation plan with safety notice)
"""

import os
import time
from typing import Any, Dict, List, Optional
import streamlit as st

from src.storage.database import MetricsDatabase
from src.storage.service import record_current_snapshot
from src.optimization.service import run_optimization
from src.detection.service import run_detection
from src.prediction.service import run_prediction
from src.detection.pressure_analyzer import PressureThresholds

from src.dashboard.styles import inject_custom_css
from src.dashboard.components import (
    render_kpi_cards,
    render_historical_chart,
    render_forecast_summary_box,
    render_system_insights,
    render_process_table,
    render_forecasting_page,
    render_recommendations,
)
from src.dashboard.charts import create_process_memory_bar_chart

DB_PATH = "data/memory_monitor.db"


def main():
    st.set_page_config(
        page_title="Memory Intelligence Dashboard",
        page_icon="🧠",
        layout="wide",
        initial_sidebar_state="expanded"
    )

    # Apply styling system
    inject_custom_css()

    # Ensure data directory exists and initialize SQLite connection
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    db = MetricsDatabase(DB_PATH)

    # --- SIDEBAR NAVIGATION & CONFIGURATION ---
    st.sidebar.markdown("""
    <div style="display: flex; align-items: center; gap: 0.6rem; margin-bottom: 1.25rem;">
        <span style="font-size: 1.6rem;">🧠</span>
        <div>
            <div style="font-weight: 800; font-size: 1.05rem; color: #FFFFFF; letter-spacing: -0.01em;">Memory Optimizer</div>
            <div style="font-size: 0.75rem; color: #94A3B8;">Predictive Pressure Intelligence</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Page Selector
    selected_page = st.sidebar.radio(
        "Navigation",
        [
            "📊 Overview",
            "🔍 Process Explorer",
            "📈 Forecasting",
            "💡 Recommendations"
        ],
        index=0,
        label_visibility="collapsed"
    )

    st.sidebar.markdown("---")
    st.sidebar.markdown("<div style='font-size: 0.8rem; font-weight: 700; color: #94A3B8; text-transform: uppercase; margin-bottom: 0.5rem;'>Analysis Window</div>", unsafe_allow_html=True)

    window_minutes = st.sidebar.slider(
        "Historical Window (Minutes)",
        min_value=1,
        max_value=30,
        value=5,
        help="Time window in minutes to analyze system memory and process trajectories."
    )
    window_seconds = window_minutes * 60.0

    top_n = st.sidebar.slider(
        "Top Candidates Analyzed",
        min_value=1,
        max_value=20,
        value=5,
        help="Maximum candidate processes evaluated for prioritized optimization recommendations."
    )

    st.sidebar.markdown("---")
    st.sidebar.markdown("<div style='font-size: 0.8rem; font-weight: 700; color: #94A3B8; text-transform: uppercase; margin-bottom: 0.5rem;'>Telemetry Controls</div>", unsafe_allow_html=True)

    if st.sidebar.button("⚡ Capture Snapshot & Refresh", use_container_width=True):
        with st.spinner("Recording host telemetry snapshot..."):
            record_current_snapshot(db, top_n=25)
            st.toast("Telemetry snapshot recorded successfully!", icon="✅")

    st.sidebar.caption("💡 Telemetry is read from SQLite. Page navigation does not capture duplicate samples.")

    # Retrieve historical data intelligently anchored to available snapshots
    all_recent_records = db.get_system_history(limit=5000)
    if all_recent_records:
        max_db_ts = float(all_recent_records[-1]["timestamp"])
        # If latest snapshot in DB was recorded recently (< 10 min ago), anchor to current wall clock time
        # Otherwise anchor to max_db_ts so past recorded sessions can be explored!
        if time.time() - max_db_ts <= 600:
            anchor_ts = time.time()
        else:
            anchor_ts = max_db_ts

        start_time = anchor_ts - window_seconds
        history_data = [r for r in all_recent_records if float(r["timestamp"]) >= start_time]

        # If fewer than 2 snapshots in window, but DB has snapshots, retrieve recent snapshots
        if len(history_data) < 2:
            history_data = all_recent_records[-50:]
    else:
        history_data = []

    # Total database stats
    total_db_samples = len(all_recent_records)

    st.sidebar.markdown("---")
    st.sidebar.markdown(f"""
    <div style="font-size: 0.75rem; color: #64748B;">
        Database: <code>{DB_PATH}</code><br>
        Total Records: <b>{total_db_samples}</b> snapshots<br>
        Active Window: <b>{len(history_data)}</b> snapshots
    </div>
    """, unsafe_allow_html=True)

    # --- TOP HEADER ---
    st.markdown("""
    <div class="dashboard-header">
        <div class="dashboard-title">
            <span>🧠 Predictive Memory Pressure & Abnormal Growth Detection</span>
        </div>
        <div class="dashboard-subtitle">
            Continuous Telemetry Analysis • OLS Predictive Forecasting • Safe Non-Destructive Remediation
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Handle Empty Database State
    if not history_data:
        st.info("ℹ️ SQLite database is currently empty. Click 'Capture Snapshot & Refresh' in the sidebar or use the button below to record the first telemetry snapshot.")
        if st.button("🚀 Capture Initial Telemetry Snapshot", use_container_width=False):
            with st.spinner("Capturing live host telemetry..."):
                record_current_snapshot(db, top_n=25)
                st.rerun()
        return

    latest_system = history_data[-1]

    # --- EXECUTE CORE PIPELINES ---
    with st.spinner("Analyzing memory dynamics and trajectories..."):
        detection_report = run_detection(db, window_seconds=window_seconds)
        prediction_report = run_prediction(db, window_seconds=window_seconds)
        plan = run_optimization(db, window_seconds=window_seconds, top_candidates_limit=top_n)

    # --- ROUTE PAGES ---
    if selected_page == "📊 Overview":
        # 1. Aligned 4 KPI Cards
        render_kpi_cards(
            plan=plan,
            detection=detection_report,
            forecast=prediction_report.system_forecast if prediction_report else None,
            latest_system=latest_system
        )

        st.markdown("<div style='height: 15px;'></div>", unsafe_allow_html=True)

        # 2. Charts & Insights in 2 balanced columns
        col_main, col_side = st.columns([3, 2])

        with col_main:
            render_historical_chart(history_data, PressureThresholds())
            
            # Mini Process Footprint distribution
            if detection_report and detection_report.ranked_impact_scores:
                fig_proc = create_process_memory_bar_chart(detection_report.ranked_impact_scores, top_n=6)
                st.plotly_chart(fig_proc, use_container_width=True)

        with col_side:
            render_forecast_summary_box(prediction_report.system_forecast if prediction_report else None)
            render_system_insights(detection_report, latest_system, len(history_data))

    elif selected_page == "🔍 Process Explorer":
        render_process_table(detection_report)

    elif selected_page == "📈 Forecasting":
        render_forecasting_page(
            history_data=history_data,
            forecast=prediction_report.system_forecast if prediction_report else None,
            thresholds=PressureThresholds(),
        )

    elif selected_page == "💡 Recommendations":
        render_recommendations(plan)


if __name__ == "__main__":
    main()
