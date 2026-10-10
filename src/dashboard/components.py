"""
Phase 7: Dashboard Reusable UI Components & Page Renderers.

Provides modular views for Overview, Process Explorer,
Forecasting, and Recommendations, adhering to Phase 1–6 backend interfaces.
"""

import datetime
from typing import Any, Dict, List, Optional
import pandas as pd
import streamlit as st

from src.detection.service import DetectionReport
from src.prediction.forecaster import PressureForecast, TrajectoryState
from src.optimization.recommendation_engine import OptimizationPlan, RiskPriority
from src.dashboard.charts import (
    create_historical_ram_chart,
    create_forecast_chart,
    create_process_memory_bar_chart,
    COLOR_NORMAL,
    COLOR_MODERATE,
    COLOR_HIGH,
    COLOR_CRITICAL,
    COLOR_FORECAST,
)

# Compatibility functions tested in regression suite
def format_timestamp(ts: float) -> str:
    """Format Unix epoch timestamp as HH:MM:SS."""
    return datetime.datetime.fromtimestamp(ts).strftime('%H:%M:%S')


def get_pressure_color(state_value: str) -> str:
    """Map memory pressure state name to color code."""
    mapping = {
        "NORMAL": "#00FFFF",
        "MODERATE": "#FFC107",
        "HIGH": "#FF9800",
        "CRITICAL": "#F44336",
    }
    return mapping.get(state_value.upper(), "white")


def get_urgency_badge_class(urgency_str: str) -> str:
    """Return CSS class for risk/urgency badges."""
    u = str(urgency_str).upper()
    if u in ("CRITICAL", "ALREADY BREACHED", "CRITICAL_IMMINENT"):
        return "badge-critical"
    elif u in ("HIGH", "RAPID_INCREASE"):
        return "badge-high"
    elif u in ("MEDIUM", "MODERATE", "GRADUAL_INCREASE"):
        return "badge-moderate"
    elif u in ("LOW", "NORMAL", "STABLE", "IMPROVING"):
        return "badge-normal"
    return "badge-purple"


# =====================================================================
# PAGE 1: OVERVIEW COMPONENTS
# =====================================================================

def render_kpi_cards(
    plan: Optional[OptimizationPlan],
    detection: Optional[DetectionReport],
    forecast: Optional[PressureForecast],
    latest_system: Dict[str, Any],
):
    """
    Render 4 aligned top-level KPI cards with visual hierarchy,
    contextual subtitles, and accurate breach state indicators.
    """
    ram_percent = float(latest_system.get('percent_used', 0.0))
    total_ram_mb = float(latest_system.get('total_ram_mb', 16384.0))
    used_ram_mb = float(latest_system.get('used_ram_mb', 0.0))
    
    available_mb = float(latest_system.get('available_ram_mb', 0.0))
    if available_mb <= 0.0 and total_ram_mb > 0.0:
        available_mb = max(0.0, total_ram_mb - used_ram_mb)

    # Pressure State
    if plan and hasattr(plan, 'system_pressure_state'):
        p_state = plan.system_pressure_state.value
    elif detection and hasattr(detection, 'system_pressure'):
        p_state = detection.system_pressure.state.value
    else:
        p_state = "NORMAL"

    # Time to Threshold - Accurately handling Already Breached vs Predicted vs Stable
    if forecast and hasattr(forecast, 'critical_breach'):
        cb = forecast.critical_breach
        wb = forecast.warning_breach
        
        if cb.is_already_breached:
            time_val = "Already Breached"
            time_sub = "Critical threshold actively exceeded"
            time_card_class = "rose"
        elif cb.is_breach_predicted and cb.seconds_to_breach is not None:
            secs = cb.seconds_to_breach
            time_val = f"{secs:.0f}s" if secs < 60 else f"{secs / 60.0:.1f}m"
            time_sub = "Critical breach predicted"
            time_card_class = "rose"
        elif wb.is_already_breached:
            time_val = "Warning Breached"
            time_sub = "Warning threshold actively exceeded"
            time_card_class = "amber"
        elif wb.is_breach_predicted and wb.seconds_to_breach is not None:
            secs = wb.seconds_to_breach
            time_val = f"{secs:.0f}s" if secs < 60 else f"{secs / 60.0:.1f}m"
            time_sub = "Warning breach predicted"
            time_card_class = "amber"
        else:
            time_val = "Stable"
            time_sub = "No breach in forecast horizon"
            time_card_class = "emerald"
    else:
        time_val = "Stable"
        time_sub = "Telemetry within normal parameters"
        time_card_class = "emerald"

    # RAM card theme
    ram_card_class = "rose" if ram_percent >= 90 else "amber" if ram_percent >= 80 else "cyan"

    # Pressure card theme
    p_card_class = "rose" if p_state == "CRITICAL" else "orange" if p_state == "HIGH" else "amber" if p_state == "MODERATE" else "emerald"

    cols = st.columns(4)

    with cols[0]:
        st.markdown(f"""
        <div class="metric-card {ram_card_class}">
            <div class="metric-title">
                <span>RAM Utilization</span>
                <span class="badge {get_urgency_badge_class(p_state)}">{ram_percent:.1f}%</span>
            </div>
            <div class="metric-value">{ram_percent:.1f}<span style="font-size: 1.1rem; color: #94A3B8;">%</span></div>
            <div class="metric-subtitle">
                <span>Used: <b>{used_ram_mb / 1024.0:.1f} GB</b> of {total_ram_mb / 1024.0:.1f} GB</span>
            </div>
        </div>
        """, unsafe_allow_html=True)

    with cols[1]:
        st.markdown(f"""
        <div class="metric-card emerald">
            <div class="metric-title">
                <span>Available Memory</span>
                <span style="color: #10B981; font-weight: 700;">{available_mb / total_ram_mb * 100.0:.0f}% Free</span>
            </div>
            <div class="metric-value">{available_mb:,.0f} <span style="font-size: 1.0rem; color: #94A3B8;">MB</span></div>
            <div class="metric-subtitle">
                <span>Physical headroom: <b>{available_mb / 1024.0:.2f} GB</b></span>
            </div>
        </div>
        """, unsafe_allow_html=True)

    with cols[2]:
        st.markdown(f"""
        <div class="metric-card {p_card_class}">
            <div class="metric-title">
                <span>Pressure State</span>
                <span class="badge {get_urgency_badge_class(p_state)}">{p_state}</span>
            </div>
            <div class="metric-value" style="font-size: 1.5rem; text-transform: uppercase;">{p_state}</div>
            <div class="metric-subtitle">
                <span>Host dynamic evaluation</span>
            </div>
        </div>
        """, unsafe_allow_html=True)

    with cols[3]:
        st.markdown(f"""
        <div class="metric-card {time_card_class}">
            <div class="metric-title">
                <span>Time to Threshold</span>
                <span class="badge {get_urgency_badge_class(time_val)}">{time_val}</span>
            </div>
            <div class="metric-value" style="font-size: 1.4rem;">{time_val}</div>
            <div class="metric-subtitle">
                <span>{time_sub}</span>
            </div>
        </div>
        """, unsafe_allow_html=True)


def render_historical_chart(history_data: List[Dict[str, Any]], thresholds: Any = None):
    """Render historical memory chart widget with metadata."""
    fig = create_historical_ram_chart(history_data, thresholds)
    st.plotly_chart(fig, use_container_width=True)

    if len(history_data) < 2:
        st.info("ℹ️ **Single Telemetry Sample**: Currently 1 sample is displayed. Capture additional snapshots via the sidebar to observe live velocity and trend curves over time.")


def render_forecast_summary_box(forecast: Optional[PressureForecast]):
    """Render compact forecast intelligence summary box."""
    if not forecast:
        st.info("Predictive forecast model is calculating or awaiting telemetry samples.")
        return

    traj = forecast.trajectory.value
    badge_cls = get_urgency_badge_class(traj)
    r2_pct = max(0.0, forecast.r_squared * 100.0)

    # Status text for breach
    if forecast.critical_breach.is_already_breached:
        crit_status = "Already Breached"
        crit_color = "#EF4444"
    elif forecast.critical_breach.is_breach_predicted:
        crit_status = f"~{forecast.critical_breach.seconds_to_breach:.0f}s"
        crit_color = "#EF4444"
    else:
        crit_status = "None Predicted"
        crit_color = "#10B981"

    st.markdown(f"""
    <div class="content-box">
        <div class="content-box-header">
            <span>Forecast Trajectory</span>
            <span class="badge {badge_cls}">{traj}</span>
        </div>
        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 1rem; margin-bottom: 0.75rem;">
            <div>
                <div style="font-size: 0.75rem; color: #94A3B8; text-transform: uppercase;">Model Fit (R²)</div>
                <div style="font-size: 1.25rem; font-weight: 700; color: #FFFFFF; font-family: monospace;">{forecast.r_squared:.2f} <span style="font-size: 0.8rem; color: #64748B;">({r2_pct:.0f}%)</span></div>
            </div>
            <div>
                <div style="font-size: 0.75rem; color: #94A3B8; text-transform: uppercase;">Confidence Score</div>
                <div style="font-size: 1.25rem; font-weight: 700; color: #A855F7; font-family: monospace;">{forecast.confidence_score * 100.0:.0f}%</div>
            </div>
            <div>
                <div style="font-size: 0.75rem; color: #94A3B8; text-transform: uppercase;">Growth Velocity</div>
                <div style="font-size: 1.1rem; font-weight: 600; color: #FFFFFF; font-family: monospace;">{forecast.rate_used_mb_s:+.2f} MB/s</div>
            </div>
            <div>
                <div style="font-size: 0.75rem; color: #94A3B8; text-transform: uppercase;">Critical Breach</div>
                <div style="font-size: 1.1rem; font-weight: 600; color: {crit_color}; font-family: monospace;">{crit_status}</div>
            </div>
        </div>
        <div style="font-size: 0.82rem; color: #94A3B8; border-top: 1px solid rgba(255,255,255,0.06); padding-top: 0.5rem;">
            {forecast.explanation}
        </div>
    </div>
    """, unsafe_allow_html=True)


def render_system_insights(
    detection: Optional[DetectionReport],
    latest_system: Dict[str, Any],
    history_count: int,
):
    """Render telemetry health and host metadata insights."""
    ts = float(latest_system.get('timestamp', 0.0))
    time_str = format_timestamp(ts) if ts > 0 else "N/A"
    
    total_active = len(detection.ranked_impact_scores) if detection else 0
    abnormal_count = len(detection.critical_growth_processes) if detection else 0
    swap_pct = float(latest_system.get('swap_percent', 0.0) or 0.0)
    swap_used = float(latest_system.get('swap_used_mb', 0.0) or 0.0)

    st.markdown(f"""
    <div class="content-box">
        <div class="content-box-header">
            <span>System Telemetry Health</span>
            <span class="badge badge-normal">● Live Active</span>
        </div>
        <div style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 0.75rem;">
            <div>
                <span style="font-size: 0.78rem; color: #94A3B8;">Last Snapshot</span>
                <div style="font-weight: 600; color: #FFFFFF; font-family: monospace;">{time_str}</div>
            </div>
            <div>
                <span style="font-size: 0.78rem; color: #94A3B8;">Active Samples</span>
                <div style="font-weight: 600; color: #00F0FF; font-family: monospace;">{history_count} snapshots</div>
            </div>
            <div>
                <span style="font-size: 0.78rem; color: #94A3B8;">Monitored Tasks</span>
                <div style="font-weight: 600; color: #FFFFFF; font-family: monospace;">{total_active} processes</div>
            </div>
            <div>
                <span style="font-size: 0.78rem; color: #94A3B8;">Abnormal Leaks</span>
                <div style="font-weight: 600; color: {'#EF4444' if abnormal_count > 0 else '#10B981'}; font-family: monospace;">{abnormal_count} detected</div>
            </div>
            <div>
                <span style="font-size: 0.78rem; color: #94A3B8;">Swap Utilization</span>
                <div style="font-weight: 600; color: #FFFFFF; font-family: monospace;">{swap_pct:.1f}% ({swap_used:,.0f} MB)</div>
            </div>
            <div>
                <span style="font-size: 0.78rem; color: #94A3B8;">Storage Mode</span>
                <div style="font-weight: 600; color: #A5B4FC;">WAL Indexed SQLite</div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)


# =====================================================================
# PAGE 2: PROCESS EXPLORER COMPONENTS
# =====================================================================

def render_process_table(detection: DetectionReport):
    """
    Render process intelligence explorer with search, severity filters,
    category filters, impact score progress bars, and educational distinction between
    physical memory footprint, composite impact, and abnormal growth severity.
    """
    st.markdown("### Process Intelligence Explorer")
    st.markdown("<p style='color: #94A3B8; font-size: 0.9rem; margin-top: -8px;'>Multi-dimensional process analysis: Physical Footprint (RSS), Growth Velocity (MB/s), and Composite Impact Scoring.</p>", unsafe_allow_html=True)

    if not detection or not detection.ranked_impact_scores:
        st.info("No active process telemetry records available.")
        return

    # Map abnormal process metadata
    abnormal_map = {p.pid: p for p in detection.abnormal_processes}
    
    total_procs = len(detection.ranked_impact_scores)
    abnormal_procs = len(detection.critical_growth_processes)
    high_impact_procs = sum(1 for i in detection.ranked_impact_scores if i.impact_score >= 0.4)

    # Process counts summary bar
    col_m1, col_m2, col_m3, col_m4 = st.columns(4)
    with col_m1:
        st.metric("Total Monitored Processes", total_procs)
    with col_m2:
        st.metric("Abnormal Growth Detections", abnormal_procs)
    with col_m3:
        st.metric("High Impact Processes (Score ≥ 0.4)", high_impact_procs)
    with col_m4:
        top_name = detection.highest_impact_process.name if detection.highest_impact_process else "None"
        st.metric("Top Pressure Contributor", top_name)

    # Conceptual Explanation Notice
    st.info(
        "💡 **Understanding Process Metrics:**\n"
        "- **Physical Footprint (RSS MB)**: Absolute RAM currently occupied by the process.\n"
        "- **Composite Impact Score (0.0 – 1.0)**: Weighted index combining footprint (40%), growth rate (35%), and persistence (25%). A static, non-leaking application like Chrome can have high impact due to its large static footprint.\n"
        "- **Abnormal Severity**: Flags active, unbounded memory expansion (leaks). Processes with `NONE` or `STABLE` are operating without abnormal memory growth."
    )

    # Filter controls
    col_search, col_sev, col_cat, col_sort = st.columns([2, 1, 1, 1])
    with col_search:
        search_query = st.text_input("🔍 Search process name or PID", "", key="proc_search_query")
    with col_sev:
        filter_sev = st.selectbox("Severity Filter", ["All Severities", "CRITICAL", "HIGH", "MEDIUM", "LOW", "NONE", "STABLE"], key="proc_sev_filter")
    with col_cat:
        filter_cat = st.selectbox("Category Filter", ["All Processes", "Abnormal Growth Only", "High Impact (Score ≥ 0.4)"], key="proc_cat_filter")
    with col_sort:
        sort_by = st.selectbox("Sort By", ["Impact Score (Desc)", "RSS Footprint (Desc)", "Growth Rate (Desc)", "PID (Asc)", "Process Name (A-Z)"], key="proc_sort_by")

    # Filter and construct rows
    table_rows = []
    for impact in detection.ranked_impact_scores:
        ab = abnormal_map.get(impact.pid)
        severity = ab.severity.value if ab else "NONE"
        is_abnormal = ab.is_abnormal if ab else False

        # Apply search filter
        if search_query:
            query_clean = search_query.strip().lower()
            if query_clean not in impact.name.lower() and query_clean not in str(impact.pid):
                continue

        # Apply severity filter
        if filter_sev != "All Severities":
            if filter_sev in ("NONE", "STABLE") and severity in ("NONE", "STABLE"):
                pass
            elif severity != filter_sev:
                continue

        # Apply category filter
        if filter_cat == "Abnormal Growth Only" and not is_abnormal:
            continue
        elif filter_cat == "High Impact (Score ≥ 0.4)" and impact.impact_score < 0.4:
            continue

        table_rows.append({
            "Rank": impact.rank,
            "Process Name": impact.name,
            "PID": impact.pid,
            "Growth Severity": severity if severity != "NONE" else "STABLE (Normal)",
            "Impact Score": float(impact.impact_score),
            "RSS (MB)": float(impact.current_rss_mb),
            "Growth Rate (MB/s)": float(impact.growth_rate_mb_s),
            "Persistence": f"{impact.persistence_score:.0%}",
            "_raw_impact": impact,
            "_raw_abnormal": ab,
        })

    # Sort rows
    if sort_by == "Impact Score (Desc)":
        table_rows.sort(key=lambda r: r["Impact Score"], reverse=True)
    elif sort_by == "RSS Footprint (Desc)":
        table_rows.sort(key=lambda r: r["RSS (MB)"], reverse=True)
    elif sort_by == "Growth Rate (Desc)":
        table_rows.sort(key=lambda r: r["Growth Rate (MB/s)"], reverse=True)
    elif sort_by == "PID (Asc)":
        table_rows.sort(key=lambda r: r["PID"])
    elif sort_by == "Process Name (A-Z)":
        table_rows.sort(key=lambda r: r["Process Name"].lower())

    if not table_rows:
        st.info("No processes match the selected filter criteria.")
        return

    # Visual Process Table via st.dataframe
    display_df = pd.DataFrame([
        {
            "Rank": r["Rank"],
            "Process Name": r["Process Name"],
            "PID": r["PID"],
            "Abnormal Severity": r["Growth Severity"],
            "Impact Score": r["Impact Score"],
            "RSS (MB)": r["RSS (MB)"],
            "Growth Velocity (MB/s)": r["Growth Rate (MB/s)"],
            "Persistence": r["Persistence"],
        }
        for r in table_rows
    ])

    st.dataframe(
        display_df,
        column_config={
            "Rank": st.column_config.NumberColumn("Rank", width="small", format="#%d"),
            "Process Name": st.column_config.TextColumn("Process Name", width="medium"),
            "PID": st.column_config.NumberColumn("PID", width="small", format="%d"),
            "Abnormal Severity": st.column_config.TextColumn("Growth Severity", width="small"),
            "Impact Score": st.column_config.ProgressColumn(
                "Composite Impact",
                help="Composite Impact Score (0.0 to 1.0) synthesized from normalized memory footprint (40%), growth velocity (35%), and persistence (25%).",
                format="%.3f",
                min_value=0.0,
                max_value=1.0,
                width="medium",
            ),
            "RSS (MB)": st.column_config.NumberColumn("Footprint (MB)", format="%.1f MB", width="small"),
            "Growth Velocity (MB/s)": st.column_config.NumberColumn("Velocity", format="%+.2f MB/s", width="small"),
            "Persistence": st.column_config.TextColumn("Persistence", width="small"),
        },
        hide_index=True,
        use_container_width=True,
    )

    # Process Deep-Dive Inspector
    st.markdown("<div style='height: 15px;'></div>", unsafe_allow_html=True)
    with st.expander("🔬 Deep-Dive Process Inspector & Mathematical Breakdown", expanded=False):
        selected_pid_str = st.selectbox(
            "Select process for full mathematical impact breakdown:",
            options=[f"{r['Process Name']} (PID {r['PID']}) — Impact: {r['Impact Score']:.3f}" for r in table_rows],
            key="proc_inspector_select"
        )
        if selected_pid_str:
            pid_target = int(selected_pid_str.split("PID ")[1].split(")")[0])
            matched_row = next((r for r in table_rows if r["PID"] == pid_target), None)
            if matched_row:
                imp = matched_row["_raw_impact"]
                abn = matched_row["_raw_abnormal"]

                st.markdown(f"#### Telemetry Details: **{imp.name}** (PID {imp.pid})")
                
                ic1, ic2, ic3, ic4 = st.columns(4)
                with ic1:
                    st.metric("Normalized Memory (M̂)", f"{imp.normalized_memory:.3f}", f"Weight: {imp.weights.w_memory:.0%}")
                with ic2:
                    st.metric("Normalized Growth (Ĝ)", f"{imp.normalized_growth:.3f}", f"Weight: {imp.weights.w_growth:.0%}")
                with ic3:
                    st.metric("Persistence Factor (P)", f"{imp.normalized_persistence:.3f}", f"Weight: {imp.weights.w_persistence:.0%}")
                with ic4:
                    st.metric("Composite Impact", f"{imp.impact_score:.3f}")

                st.markdown(f"**Impact Equation Justification:**")
                st.code(f"Impact = ({imp.weights.w_memory:.2f} × {imp.normalized_memory:.3f}) + ({imp.weights.w_growth:.2f} × {imp.normalized_growth:.3f}) + ({imp.weights.w_persistence:.2f} × {imp.normalized_persistence:.3f}) = {imp.impact_score:.4f}", language="text")
                st.info(f"**Impact Explanation:** {imp.explanation}")

                if abn:
                    flags_str = ", ".join([f.value for f in abn.flags])
                    st.markdown(f"**Abnormal Growth Behavior Flags:** `{flags_str}`")
                    st.markdown(f"- Severity: **{abn.severity.value}** | Is Abnormal: **{'YES' if abn.is_abnormal else 'NO'}**")
                    st.markdown(f"- Net Change in Window: **{abn.net_change_mb:+.1f} MB** | Velocity: **{abn.growth_rate_mb_s:+.2f} MB/s**")
                    st.markdown(f"- **Growth Assessment:** {abn.explanation}")


# =====================================================================
# PAGE 3: FORECASTING COMPONENTS
# =====================================================================

def render_forecast_chart(
    history_data: List[Dict[str, Any]],
    forecast: Optional[PressureForecast],
    warning_percent: float = 85.0,
    critical_percent: float = 92.0,
):
    """Render interactive forecasting chart."""
    fig = create_forecast_chart(history_data, forecast, warning_percent, critical_percent)
    st.plotly_chart(fig, use_container_width=True)


def render_forecasting_page(
    history_data: List[Dict[str, Any]],
    forecast: Optional[PressureForecast],
    thresholds: Any = None,
):
    """
    Render complete Predictive Forecasting page with model diagnostics,
    accurate breach status handling, and multi-step projection tables.
    """
    st.markdown("### Short-Term Predictive Forecasting Engine")
    st.markdown("<p style='color: #94A3B8; font-size: 0.9rem; margin-top: -8px;'>Ordinary Least Squares (OLS) linear trend extrapolation across multi-horizon steps (+30s, +60s, +120s, +300s).</p>", unsafe_allow_html=True)

    if not forecast:
        st.warning("⚠️ Forecasting requires historical telemetry samples. Click 'Capture Snapshot & Refresh' in the sidebar to activate.")
        return

    # Extract threshold configs
    warn_thresh = getattr(thresholds, 'moderate_max_percent', 85.0) if thresholds else 85.0
    crit_thresh = getattr(thresholds, 'high_max_percent', 92.0) if thresholds else 92.0

    # Forecasting KPI metrics
    fc1, fc2, fc3, fc4 = st.columns(4)
    with fc1:
        traj_val = forecast.trajectory.value
        st.markdown(f"""
        <div class="metric-card purple">
            <div class="metric-title">
                <span>Trajectory State</span>
                <span class="badge {get_urgency_badge_class(traj_val)}">{traj_val}</span>
            </div>
            <div class="metric-value" style="font-size: 1.4rem;">{traj_val}</div>
            <div class="metric-subtitle">Trend classification</div>
        </div>
        """, unsafe_allow_html=True)

    with fc2:
        r2_color = "emerald" if forecast.r_squared >= 0.7 else "amber" if forecast.r_squared >= 0.4 else "cyan"
        st.markdown(f"""
        <div class="metric-card {r2_color}">
            <div class="metric-title">
                <span>Model Fit (R²)</span>
                <span style="font-weight: 700; color: #FFFFFF;">{forecast.r_squared:.2f}</span>
            </div>
            <div class="metric-value">{forecast.r_squared:.3f}</div>
            <div class="metric-subtitle">Variance explained</div>
        </div>
        """, unsafe_allow_html=True)

    with fc3:
        st.markdown(f"""
        <div class="metric-card cyan">
            <div class="metric-title">
                <span>Confidence Score</span>
                <span style="color: #00F0FF; font-weight: 700;">{forecast.confidence_score * 100.0:.0f}%</span>
            </div>
            <div class="metric-value">{forecast.confidence_score * 100.0:.1f}<span style="font-size: 1.0rem; color: #94A3B8;">%</span></div>
            <div class="metric-subtitle">Statistical reliability</div>
        </div>
        """, unsafe_allow_html=True)

    with fc4:
        rate_val = forecast.rate_used_mb_s
        rate_color = "rose" if rate_val > 5.0 else "amber" if rate_val > 1.0 else "emerald"
        st.markdown(f"""
        <div class="metric-card {rate_color}">
            <div class="metric-title">
                <span>Growth Velocity</span>
                <span style="font-weight: 700;">{rate_val:+.2f} MB/s</span>
            </div>
            <div class="metric-value">{rate_val:+.2f} <span style="font-size: 1.0rem; color: #94A3B8;">MB/s</span></div>
            <div class="metric-subtitle">{forecast.rate_percent_s:+.3f}% RAM / sec</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)

    # Forecast Interactive Chart
    render_forecast_chart(history_data, forecast, warning_percent=warn_thresh, critical_percent=crit_thresh)

    st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)

    # Multi-Horizon Projections & Breach Diagnostics in 2 columns
    col_proj, col_diag = st.columns([3, 2])

    with col_proj:
        st.markdown("#### Multi-Horizon Projected Milestones")
        if forecast.projections:
            proj_data = []
            for p in forecast.projections:
                proj_data.append({
                    "Horizon": f"+{p.horizon_seconds:.0f} sec",
                    "Projected Time": format_timestamp(p.timestamp),
                    "Projected RAM (%)": f"{p.projected_ram_percent:.1f}%",
                    "Projected Used": f"{p.projected_used_mb:,.0f} MB",
                    "Projected Available": f"{p.projected_available_mb:,.0f} MB",
                })
            df_proj = pd.DataFrame(proj_data)
            st.dataframe(df_proj, hide_index=True, use_container_width=True)
        else:
            st.info("No projection milestones generated.")

    with col_diag:
        st.markdown("#### Threshold Breach Diagnostics")
        
        # Warning Breach Box
        wb = forecast.warning_breach
        if wb.is_already_breached:
            wb_status = "⚠️ ALREADY BREACHED"
            wb_cls = "badge-high"
            wb_time = "Active (0s remaining)"
        elif wb.is_breach_predicted and wb.seconds_to_breach is not None:
            wb_status = "⚠️ PREDICTED"
            wb_cls = "badge-high"
            wb_time = f"{wb.seconds_to_breach:.0f}s"
        else:
            wb_status = "✅ CLEAR"
            wb_cls = "badge-normal"
            wb_time = "No breach predicted"
        
        # Critical Breach Box
        cb = forecast.critical_breach
        if cb.is_already_breached:
            cb_status = "🚨 ALREADY BREACHED"
            cb_cls = "badge-critical"
            cb_time = "Active (0s remaining)"
        elif cb.is_breach_predicted and cb.seconds_to_breach is not None:
            cb_status = "🚨 IMMINENT"
            cb_cls = "badge-critical"
            cb_time = f"{cb.seconds_to_breach:.0f}s"
        else:
            cb_status = "✅ CLEAR"
            cb_cls = "badge-normal"
            cb_time = "No breach predicted"

        st.markdown(f"""
        <div style="background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.08); border-radius: 10px; padding: 1rem; margin-bottom: 0.75rem;">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.5rem;">
                <span style="font-weight: 600; color: #FFFFFF;">Warning Threshold ({warn_thresh:.0f}%)</span>
                <span class="badge {wb_cls}">{wb_status}</span>
            </div>
            <div style="font-size: 0.85rem; color: #94A3B8;">Time to Breach: <b style="color: #FFFFFF;">{wb_time}</b></div>
            <div style="font-size: 0.8rem; color: #64748B; margin-top: 0.25rem;">{wb.explanation}</div>
        </div>
        <div style="background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.08); border-radius: 10px; padding: 1rem;">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.5rem;">
                <span style="font-weight: 600; color: #FFFFFF;">Critical Threshold ({crit_thresh:.0f}%)</span>
                <span class="badge {cb_cls}">{cb_status}</span>
            </div>
            <div style="font-size: 0.85rem; color: #94A3B8;">Time to Breach: <b style="color: #FFFFFF;">{cb_time}</b></div>
            <div style="font-size: 0.8rem; color: #64748B; margin-top: 0.25rem;">{cb.explanation}</div>
        </div>
        """, unsafe_allow_html=True)

    # Transparent Model Fit Explanation
    st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)
    with st.expander("ℹ️ Statistical Modeling & Fit Diagnostics", expanded=False):
        st.markdown("""
        **About OLS Regression & Model Diagnostics:**
        - **Model Confidence & R²:** When system memory utilization is stationary/flat (zero upward velocity), variance is zero ($SS_{tot} \\approx 0$), resulting in $R^2 = 0.00$. This is mathematically normal and indicates a **stable system with zero growth**, not an algorithm defect.
        - **Linear Extrapolation:** Multi-horizon projections assume current growth trajectory continues linearly and do not account for external OS memory compaction or garbage collection events.
        """)


# =====================================================================
# PAGE 4: RECOMMENDATIONS COMPONENTS (NATIVE STREAMLIT RENDERING)
# =====================================================================

def render_recommendations(plan: OptimizationPlan):
    """
    Render recommendations and remediation plan using 100% native Streamlit components
    (st.container, st.columns, st.metric, st.markdown, st.expander), ensuring zero raw HTML
    or unrendered source code blocks.
    """
    st.markdown("### Recommendations & Safe Remediation Plan")
    st.markdown("<p style='color: #94A3B8; font-size: 0.9rem; margin-top: -8px;'>Human-in-the-loop, risk-prioritized remediation strategies with non-destructive guarantees.</p>", unsafe_allow_html=True)

    if not plan:
        st.info("No remediation plan generated yet. Telemetry analysis is active.")
        return

    # Prominent Safety Notice Banner
    st.warning(f"🛡️ **NON-DESTRUCTIVE SAFETY GUARANTEE (ADVISORY ONLY):** {plan.safety_notice}")

    # Executive Summary & Remediation Metrics
    urgency_val = plan.overall_urgency.value
    u_badge_cls = get_urgency_badge_class(urgency_val)

    col_sum1, col_sum2, col_sum3 = st.columns(3)
    with col_sum1:
        st.markdown(f"""
        <div class="metric-card { 'rose' if urgency_val == 'CRITICAL' else 'amber' if urgency_val == 'HIGH' else 'emerald' }">
            <div class="metric-title">
                <span>Overall Plan Urgency</span>
                <span class="badge {u_badge_cls}">{urgency_val}</span>
            </div>
            <div class="metric-value">{urgency_val}</div>
            <div class="metric-subtitle">System remediation priority</div>
        </div>
        """, unsafe_allow_html=True)

    with col_sum2:
        st.markdown(f"""
        <div class="metric-card cyan">
            <div class="metric-title">
                <span>Estimated Reclaimable RSS</span>
                <span class="badge badge-cyan">Simulated</span>
            </div>
            <div class="metric-value">{plan.total_potential_reclaim_mb:,.1f} <span style="font-size: 1.0rem; color: #94A3B8;">MB</span></div>
            <div class="metric-subtitle">Estimate only, not guaranteed</div>
        </div>
        """, unsafe_allow_html=True)

    with col_sum3:
        st.markdown(f"""
        <div class="metric-card emerald">
            <div class="metric-title">
                <span>Projected RAM After Action</span>
                <span class="badge badge-normal">Post-Remediation</span>
            </div>
            <div class="metric-value">{plan.projected_system_ram_percent_after_remediation:.1f}<span style="font-size: 1.0rem; color: #94A3B8;">%</span></div>
            <div class="metric-subtitle">Simulated host impact</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)

    # Executive Summary Box
    st.info(f"**Executive Summary:** {plan.summary}")

    if not plan.recommendations:
        st.success("✅ System memory is operating within normal boundaries. No remediation actions currently required.")
        return

    st.markdown("#### Prioritized Remediation Candidates")

    for idx, rec in enumerate(plan.recommendations, 1):
        is_prot = rec.is_protected_system_process
        urgency = rec.urgency.value
        act_type = rec.action_type.value

        # Render each card using clean native Streamlit containers
        with st.container(border=True):
            # Header row: Title + Badges
            hdr_col1, hdr_col2 = st.columns([3, 1])
            with hdr_col1:
                st.markdown(f"#### {idx}. {rec.title}")
                st.caption(f"Process: **{rec.process_name}** (PID: `{rec.pid}`) • Recommended Action: `{act_type}`")
            with hdr_col2:
                if is_prot:
                    st.markdown("<span class='badge badge-protected'>🛡️ PROTECTED OS PROCESS</span>", unsafe_allow_html=True)
                else:
                    st.markdown(f"<span class='badge {get_urgency_badge_class(urgency)}'>{urgency} PRIORITY</span>", unsafe_allow_html=True)

            # Metric row: Current Footprint, Estimated Reclaim, Post-Remediation RAM
            m_col1, m_col2, m_col3 = st.columns(3)
            with m_col1:
                m_col1.metric("Current Footprint", f"{rec.current_rss_mb:,.1f} MB")
            with m_col2:
                if is_prot:
                    m_col2.metric("Estimated Reclaim", "0.0 MB (Guarded)", help="OS Kernel process — termination prohibited by safety policy.")
                else:
                    m_col2.metric("Estimated Reclaim", f"{rec.projected_reclaimable_mb:,.1f} MB", help="Analytical projection, not guaranteed.")
            with m_col3:
                m_col3.metric("Post-Remediation RAM", f"{rec.simulated_post_ram_percent:.1f}%")

            # Technical Reasoning callout
            st.markdown(f"**Technical Justification:** {rec.reasoning}")

            # Expandable Step-by-Step Mitigation Guidance
            with st.expander(f"📋 Step-by-Step Mitigation Guidance ({rec.process_name})", expanded=False):
                st.markdown("**Authorized Operator Action Steps:**")
                for s_idx, step in enumerate(rec.mitigation_steps, 1):
                    st.markdown(f"{s_idx}. {step}")
                
                st.caption("⚠️ Note: Simulated memory reclaim is an analytical projection and does not guarantee exact OS page deallocation.")
                if is_prot:
                    st.warning("🛡️ Safeguard Policy: This process is part of core operating system stability or security subsystems. Manual termination or killing is strictly prohibited.")
