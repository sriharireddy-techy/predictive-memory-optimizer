"""
Phase 7: Interactive Plotly Chart Generators.

Provides data visualization for historical time-series telemetry,
multi-horizon predictive forecasting, and process memory distributions.
"""

import datetime
from typing import Any, Dict, List, Optional
import pandas as pd
import plotly.graph_objects as go

# Theme Colors
COLOR_NORMAL = "#00FFFF"      # Cyan
COLOR_MODERATE = "#FFC107"    # Amber
COLOR_HIGH = "#FF9800"        # Orange
COLOR_CRITICAL = "#EF4444"    # Red / Rose
COLOR_FORECAST = "#A855F7"    # Purple
COLOR_MUTED = "#94A3B8"       # Slate
COLOR_GRID = "#1E293B"        # Dark Slate Grid


def create_historical_ram_chart(
    history_data: List[Dict[str, Any]],
    thresholds: Optional[Any] = None,
    warning_percent: float = 85.0,
    critical_percent: float = 92.0,
    auto_scale_y: bool = False,
) -> go.Figure:
    """
    Generate an interactive historical RAM utilization area chart with
    crisp datetime formatting, visible sample points, and threshold references.
    """
    fig = go.Figure()

    if not history_data:
        fig.add_annotation(
            text="No historical telemetry records found in the selected window.",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False,
            font=dict(size=14, color=COLOR_MUTED)
        )
        fig.update_layout(
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            xaxis=dict(showgrid=False, showticklabels=False),
            yaxis=dict(showgrid=False, showticklabels=False),
            height=320,
        )
        return fig

    # Sanitize and sort records chronologically
    df = pd.DataFrame(history_data)
    df = df.dropna(subset=['timestamp', 'percent_used']).sort_values('timestamp')
    df['datetime'] = pd.to_datetime(df['timestamp'], unit='s')

    # Extract threshold values from thresholds object if provided
    if thresholds is not None:
        if hasattr(thresholds, 'moderate_max_percent'):
            warning_percent = float(thresholds.moderate_max_percent)
        elif hasattr(thresholds, 'high_max_percent'):
            warning_percent = float(thresholds.high_max_percent)
        if hasattr(thresholds, 'critical_min_percent'):
            critical_percent = float(thresholds.critical_min_percent)
        elif hasattr(thresholds, 'high_max_percent') and not hasattr(thresholds, 'critical_min_percent'):
            critical_percent = float(thresholds.high_max_percent)

    # Build custom hover metadata
    customdata = []
    for _, row in df.iterrows():
        used_mb = row.get('used_ram_mb', 0.0)
        avail_mb = row.get('available_ram_mb', 0.0)
        tot_mb = row.get('total_ram_mb', 16384.0)
        customdata.append([used_mb, avail_mb, tot_mb])

    # System RAM Trace: lines+markers ensures single/few points are always visible!
    fig.add_trace(go.Scatter(
        x=df['datetime'],
        y=df['percent_used'],
        mode='lines+markers',
        name='Observed RAM (%)',
        line=dict(color=COLOR_NORMAL, width=2.5),
        marker=dict(size=6, color=COLOR_NORMAL, symbol='circle', line=dict(width=1, color='#FFFFFF')),
        fill='tozeroy',
        fillcolor='rgba(0, 240, 255, 0.12)',
        customdata=customdata,
        hovertemplate=(
            "<b>%{x|%Y-%m-%d %H:%M:%S}</b><br>"
            "RAM Utilized: <b>%{y:.1f}%</b><br>"
            "Used Memory: %{customdata[0]:,.0f} MB<br>"
            "Available Memory: %{customdata[1]:,.0f} MB<br>"
            "Total RAM: %{customdata[2]:,.0f} MB"
            "<extra></extra>"
        )
    ))

    # Add warning threshold reference line
    fig.add_hline(
        y=warning_percent,
        line_dash="dash",
        line_color=COLOR_MODERATE,
        line_width=1.5,
        annotation_text=f"Warning ({warning_percent:.0f}%)",
        annotation_position="top left",
        annotation_font=dict(color=COLOR_MODERATE, size=11),
    )

    # Add critical threshold reference line
    fig.add_hline(
        y=critical_percent,
        line_dash="dash",
        line_color=COLOR_CRITICAL,
        line_width=1.5,
        annotation_text=f"Critical ({critical_percent:.0f}%)",
        annotation_position="top left",
        annotation_font=dict(color=COLOR_CRITICAL, size=11),
    )

    # Y-axis bounds
    min_pct = max(0.0, df['percent_used'].min() - 8.0) if auto_scale_y else 0.0
    max_pct = min(100.0, max(100.0, df['percent_used'].max() + 5.0))

    fig.update_layout(
        title=dict(
            text=f"Historical RAM Utilization ({len(df)} Telemetry Snapshots)",
            font=dict(size=14, color="#FFFFFF", family="Inter, sans-serif"),
            x=0.01,
            y=0.96,
        ),
        margin=dict(l=40, r=20, t=40, b=30),
        height=320,
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        hovermode="x unified",
        xaxis=dict(
            title=dict(text="Timeline", font=dict(size=11, color=COLOR_MUTED)),
            showgrid=True,
            gridcolor=COLOR_GRID,
            color=COLOR_MUTED,
            tickformat="%H:%M:%S",
            hoverformat="%Y-%m-%d %H:%M:%S",
            nticks=8,
            zeroline=False,
        ),
        yaxis=dict(
            title=dict(text="RAM Used (%)", font=dict(size=11, color=COLOR_MUTED)),
            showgrid=True,
            gridcolor=COLOR_GRID,
            color=COLOR_MUTED,
            range=[min_pct, max_pct],
            ticksuffix="%",
            zeroline=False,
        ),
        font=dict(color="#E2E8F0", family="Inter, sans-serif"),
        showlegend=False,
    )

    return fig


def create_forecast_chart(
    history_data: List[Dict[str, Any]],
    forecast: Optional[Any],
    warning_percent: float = 85.0,
    critical_percent: float = 92.0,
) -> go.Figure:
    """
    Generate an interactive forecasting chart clearly separating observed historical
    telemetry from forward-looking multi-step OLS linear projections.
    """
    fig = go.Figure()

    if not history_data and not forecast:
        fig.add_annotation(
            text="No telemetry records or forecast model available.",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False,
            font=dict(size=14, color=COLOR_MUTED)
        )
        fig.update_layout(
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            xaxis=dict(showgrid=False, showticklabels=False),
            yaxis=dict(showgrid=False, showticklabels=False),
            height=340,
        )
        return fig

    # 1. Historical Observed Segment
    if history_data:
        df_hist = pd.DataFrame(history_data)
        df_hist = df_hist.dropna(subset=['timestamp', 'percent_used']).sort_values('timestamp')
        df_hist['datetime'] = pd.to_datetime(df_hist['timestamp'], unit='s')

        fig.add_trace(go.Scatter(
            x=df_hist['datetime'],
            y=df_hist['percent_used'],
            mode='lines+markers',
            name='Observed Telemetry',
            line=dict(color=COLOR_NORMAL, width=2.5),
            marker=dict(size=5, color=COLOR_NORMAL),
            fill='tozeroy',
            fillcolor='rgba(0, 240, 255, 0.10)',
            hovertemplate="<b>Observed Telemetry</b>: %{y:.1f}% at %{x|%H:%M:%S}<extra></extra>",
        ))

    # 2. Forecast Projected Segment
    if forecast and hasattr(forecast, 'projections') and forecast.projections:
        current_dt = pd.to_datetime(forecast.timestamp, unit='s')
        proj_dts = [current_dt]
        proj_vals = [forecast.current_percent]
        proj_labels = ["Current Reference (T₀)"]

        for p in forecast.projections:
            proj_dts.append(pd.to_datetime(p.timestamp, unit='s'))
            proj_vals.append(p.projected_ram_percent)
            proj_labels.append(f"Forecast Horizon (+{p.horizon_seconds:.0f}s)")

        fig.add_trace(go.Scatter(
            x=proj_dts,
            y=proj_vals,
            mode='lines+markers',
            name='OLS Linear Projections',
            line=dict(color=COLOR_FORECAST, width=2.5, dash='dash'),
            marker=dict(size=7, color=COLOR_FORECAST, symbol='diamond'),
            hovertemplate="<b>%{text}</b><br>Projected RAM: <b>%{y:.1f}%</b> at %{x|%H:%M:%S}<extra></extra>",
            text=proj_labels,
        ))

    # 3. Add Threshold Lines
    fig.add_hline(
        y=warning_percent,
        line_dash="dot",
        line_color=COLOR_MODERATE,
        line_width=1.5,
        annotation_text=f"Warning ({warning_percent:.0f}%)",
        annotation_position="top left",
        annotation_font=dict(color=COLOR_MODERATE, size=11),
    )

    fig.add_hline(
        y=critical_percent,
        line_dash="dot",
        line_color=COLOR_CRITICAL,
        line_width=1.5,
        annotation_text=f"Critical ({critical_percent:.0f}%)",
        annotation_position="top left",
        annotation_font=dict(color=COLOR_CRITICAL, size=11),
    )

    # 4. Breach Markers
    if forecast and hasattr(forecast, 'critical_breach'):
        cb = forecast.critical_breach
        if cb.is_already_breached:
            fig.add_annotation(
                text="🚨 CRITICAL THRESHOLD ACTIVELY BREACHED",
                xref="paper", yref="paper",
                x=0.98, y=0.95, showarrow=False,
                align="right",
                font=dict(size=11, color=COLOR_CRITICAL, weight="bold"),
                bgcolor="rgba(239, 68, 68, 0.15)",
                bordercolor=COLOR_CRITICAL,
                borderwidth=1,
                borderpad=4,
            )
        elif cb.is_breach_predicted and cb.breach_timestamp is not None:
            breach_dt = pd.to_datetime(cb.breach_timestamp, unit='s')
            fig.add_vline(
                x=breach_dt.timestamp() * 1000,
                line_dash="dashdot",
                line_color=COLOR_CRITICAL,
                line_width=2,
                annotation_text=f"Projected Critical Breach (~{cb.seconds_to_breach:.0f}s)",
                annotation_position="top right",
                annotation_font=dict(color=COLOR_CRITICAL, size=11),
            )

    traj_text = forecast.trajectory.value if forecast and hasattr(forecast, 'trajectory') else "N/A"
    r2_text = f"R² = {forecast.r_squared:.2f}" if forecast and hasattr(forecast, 'r_squared') else ""
    title_suffix = f" — Trajectory: {traj_text} ({r2_text})" if traj_text != "N/A" else ""

    fig.update_layout(
        title=dict(
            text=f"Predictive RAM Trajectory & Future Horizon Extrapolations{title_suffix}",
            font=dict(size=14, color="#FFFFFF", family="Inter, sans-serif"),
            x=0.01,
            y=0.96,
        ),
        margin=dict(l=40, r=20, t=40, b=30),
        height=340,
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        hovermode="x unified",
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1.0,
            font=dict(size=11, color=COLOR_MUTED),
        ),
        xaxis=dict(
            title=dict(text="Observation & Forecast Timeline", font=dict(size=11, color=COLOR_MUTED)),
            showgrid=True,
            gridcolor=COLOR_GRID,
            color=COLOR_MUTED,
            tickformat="%H:%M:%S",
            hoverformat="%Y-%m-%d %H:%M:%S",
            nticks=8,
            zeroline=False,
        ),
        yaxis=dict(
            title=dict(text="RAM Utilization (%)", font=dict(size=11, color=COLOR_MUTED)),
            showgrid=True,
            gridcolor=COLOR_GRID,
            color=COLOR_MUTED,
            range=[0, 100],
            ticksuffix="%",
            zeroline=False,
        ),
        font=dict(color="#E2E8F0", family="Inter, sans-serif"),
    )

    return fig


def create_process_memory_bar_chart(
    ranked_impacts: List[Any],
    top_n: int = 8
) -> go.Figure:
    """
    Generate a horizontal bar chart displaying top memory consumers ranked by impact.
    """
    if not ranked_impacts:
        fig = go.Figure()
        fig.add_annotation(
            text="No active process telemetry available.",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False,
            font=dict(size=12, color=COLOR_MUTED)
        )
        fig.update_layout(
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            height=260,
        )
        return fig

    items = ranked_impacts[:top_n]
    names = [f"{i.name} ({i.pid})" for i in reversed(items)]
    rss_vals = [i.current_rss_mb for i in reversed(items)]
    scores = [i.impact_score for i in reversed(items)]

    colors = []
    for score in scores:
        if score >= 0.7:
            colors.append(COLOR_CRITICAL)
        elif score >= 0.4:
            colors.append(COLOR_HIGH)
        elif score >= 0.2:
            colors.append(COLOR_MODERATE)
        else:
            colors.append(COLOR_NORMAL)

    fig = go.Figure(go.Bar(
        x=rss_vals,
        y=names,
        orientation='h',
        marker=dict(color=colors, line=dict(width=0)),
        hovertemplate="<b>%{y}</b><br>Physical Footprint: <b>%{x:,.1f} MB</b><extra></extra>",
    ))

    fig.update_layout(
        title=dict(
            text="Top Process Memory Footprints (RSS MB)",
            font=dict(size=13, color="#FFFFFF", family="Inter, sans-serif"),
            x=0.01,
        ),
        margin=dict(l=10, r=20, t=35, b=25),
        height=260,
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(
            showgrid=True,
            gridcolor=COLOR_GRID,
            color=COLOR_MUTED,
            ticksuffix=" MB",
        ),
        yaxis=dict(
            showgrid=False,
            color=COLOR_MUTED,
            tickfont=dict(size=11),
        ),
        font=dict(color="#E2E8F0", family="Inter, sans-serif"),
    )

    return fig
