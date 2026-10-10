"""
Phase 7: Dashboard Styling & Visual Design System.

Provides high-contrast dark theme styles, glassmorphism card layouts,
status badges, and responsive typography for the Predictive Memory Optimizer UI.
"""

import streamlit as st

def get_custom_css() -> str:
    """Return the CSS style definitions for the dark theme dashboard."""
    return """
    <style>
    /* Google Fonts Import */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap');

    /* Global CSS Variables */
    :root {
        --bg-primary: #0A0D14;
        --bg-card: #131824;
        --bg-card-hover: #1A2130;
        --bg-surface: #1E2638;
        --border-subtle: rgba(255, 255, 255, 0.08);
        --border-accent: rgba(0, 240, 255, 0.3);
        --text-primary: #F8FAFC;
        --text-secondary: #94A3B8;
        --text-muted: #64748B;
        --color-cyan: #00F0FF;
        --color-blue: #3B82F6;
        --color-purple: #A855F7;
        --color-emerald: #10B981;
        --color-amber: #F59E0B;
        --color-orange: #F97316;
        --color-rose: #EF4444;
        --color-indigo: #6366F1;
    }

    /* Main Container & Background */
    .stApp {
        background-color: var(--bg-primary) !important;
        color: var(--text-primary) !important;
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif !important;
    }

    /* Streamlit Defaults Override */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    .block-container {
        padding-top: 1.5rem !important;
        padding-bottom: 2rem !important;
        padding-left: 2rem !important;
        padding-right: 2rem !important;
        max-width: 100% !important;
    }

    /* Typography */
    h1, h2, h3, h4, h5, h6 {
        color: var(--text-primary) !important;
        font-family: 'Inter', sans-serif !important;
        font-weight: 700 !important;
        letter-spacing: -0.02em !important;
    }

    /* Header Accent */
    .dashboard-header {
        margin-bottom: 1.5rem;
        padding-bottom: 1rem;
        border-bottom: 1px solid var(--border-subtle);
    }
    .dashboard-title {
        font-size: 1.85rem;
        font-weight: 800;
        color: #FFFFFF;
        display: flex;
        align-items: center;
        gap: 0.75rem;
    }
    .dashboard-subtitle {
        font-size: 0.95rem;
        color: var(--text-secondary);
        margin-top: 0.25rem;
    }

    /* Custom Metric Cards */
    .metric-card {
        background: linear-gradient(135deg, rgba(19, 24, 36, 0.9) 0%, rgba(26, 33, 48, 0.7) 100%);
        border: 1px solid var(--border-subtle);
        border-radius: 12px;
        padding: 1.25rem;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.25);
        backdrop-filter: blur(10px);
        transition: transform 0.2s ease, border-color 0.2s ease, box-shadow 0.2s ease;
        position: relative;
        overflow: hidden;
    }
    .metric-card:hover {
        transform: translateY(-2px);
        border-color: rgba(255, 255, 255, 0.16);
        box-shadow: 0 8px 24px rgba(0, 0, 0, 0.35);
    }
    .metric-card::before {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        height: 2px;
        background: linear-gradient(90deg, transparent, var(--border-accent), transparent);
    }
    .metric-card.cyan::before { background: linear-gradient(90deg, transparent, #00F0FF, transparent); }
    .metric-card.emerald::before { background: linear-gradient(90deg, transparent, #10B981, transparent); }
    .metric-card.amber::before { background: linear-gradient(90deg, transparent, #F59E0B, transparent); }
    .metric-card.rose::before { background: linear-gradient(90deg, transparent, #EF4444, transparent); }
    .metric-card.purple::before { background: linear-gradient(90deg, transparent, #A855F7, transparent); }

    .metric-title {
        font-size: 0.8rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        color: var(--text-secondary);
        margin-bottom: 0.5rem;
        display: flex;
        justify-content: space-between;
        align-items: center;
    }
    .metric-value {
        font-size: 1.85rem;
        font-weight: 800;
        color: #FFFFFF;
        font-family: 'JetBrains Mono', monospace;
        letter-spacing: -0.03em;
        line-height: 1.2;
    }
    .metric-subtitle {
        font-size: 0.78rem;
        color: var(--text-muted);
        margin-top: 0.5rem;
        display: flex;
        align-items: center;
        gap: 0.35rem;
    }

    /* Badges */
    .badge {
        display: inline-flex;
        align-items: center;
        gap: 0.35rem;
        padding: 0.25rem 0.65rem;
        border-radius: 9999px;
        font-size: 0.75rem;
        font-weight: 600;
        letter-spacing: 0.02em;
        line-height: 1;
    }
    .badge-normal {
        background: rgba(16, 185, 129, 0.15);
        color: #10B981;
        border: 1px solid rgba(16, 185, 129, 0.3);
    }
    .badge-moderate {
        background: rgba(245, 158, 11, 0.15);
        color: #F59E0B;
        border: 1px solid rgba(245, 158, 11, 0.3);
    }
    .badge-high {
        background: rgba(249, 115, 22, 0.15);
        color: #F97316;
        border: 1px solid rgba(249, 115, 22, 0.3);
    }
    .badge-critical {
        background: rgba(239, 68, 68, 0.15);
        color: #EF4444;
        border: 1px solid rgba(239, 68, 68, 0.3);
    }
    .badge-purple {
        background: rgba(168, 85, 247, 0.15);
        color: #C084FC;
        border: 1px solid rgba(168, 85, 247, 0.3);
    }
    .badge-cyan {
        background: rgba(0, 240, 255, 0.15);
        color: #00F0FF;
        border: 1px solid rgba(0, 240, 255, 0.3);
    }
    .badge-protected {
        background: rgba(99, 102, 241, 0.15);
        color: #818CF8;
        border: 1px solid rgba(99, 102, 241, 0.35);
    }

    /* Content Cards */
    .content-box {
        background-color: var(--bg-card);
        border: 1px solid var(--border-subtle);
        border-radius: 12px;
        padding: 1.5rem;
        margin-bottom: 1.5rem;
    }
    .content-box-header {
        font-size: 1.1rem;
        font-weight: 700;
        color: #FFFFFF;
        margin-bottom: 1rem;
        display: flex;
        justify-content: space-between;
        align-items: center;
    }

    /* Recommendation Cards */
    .rec-card {
        background: var(--bg-card);
        border: 1px solid var(--border-subtle);
        border-radius: 12px;
        padding: 1.25rem;
        margin-bottom: 1rem;
        transition: all 0.2s ease;
    }
    .rec-card:hover {
        border-color: rgba(255, 255, 255, 0.15);
        background: var(--bg-card-hover);
    }
    .rec-card.critical {
        border-left: 4px solid var(--color-rose);
    }
    .rec-card.high {
        border-left: 4px solid var(--color-orange);
    }
    .rec-card.medium {
        border-left: 4px solid var(--color-amber);
    }
    .rec-card.low {
        border-left: 4px solid var(--color-blue);
    }
    .rec-card.protected {
        border-left: 4px solid var(--color-indigo);
    }

    /* Safety Notice Banner */
    .safety-banner {
        background: linear-gradient(90deg, rgba(30, 41, 59, 0.9) 0%, rgba(15, 23, 42, 0.9) 100%);
        border: 1px solid rgba(99, 102, 241, 0.3);
        border-radius: 10px;
        padding: 0.85rem 1.25rem;
        margin-bottom: 1.5rem;
        display: flex;
        align-items: center;
        gap: 0.75rem;
        color: #CBD5E1;
        font-size: 0.88rem;
    }
    .safety-banner strong {
        color: #A5B4FC;
    }

    /* Streamlit Native Elements Customization */
    div[data-testid="stMetricValue"] {
        font-family: 'JetBrains Mono', monospace !important;
        color: #FFFFFF !important;
        font-size: 1.75rem !important;
    }
    
    div[data-testid="stMetricLabel"] {
        color: var(--text-secondary) !important;
        font-size: 0.85rem !important;
        font-weight: 500 !important;
    }

    /* Sidebar Styling */
    section[data-testid="stSidebar"] {
        background-color: #0c1018 !important;
        border-right: 1px solid var(--border-subtle) !important;
    }
    
    section[data-testid="stSidebar"] .block-container {
        padding-top: 2rem !important;
        padding-left: 1.25rem !important;
        padding-right: 1.25rem !important;
    }

    /* Buttons */
    .stButton > button {
        background: linear-gradient(135deg, #2563EB 0%, #1D4ED8 100%) !important;
        color: #FFFFFF !important;
        border: 1px solid rgba(255, 255, 255, 0.1) !important;
        border-radius: 8px !important;
        padding: 0.5rem 1.25rem !important;
        font-weight: 600 !important;
        font-size: 0.88rem !important;
        transition: all 0.2s ease !important;
    }
    .stButton > button:hover {
        background: linear-gradient(135deg, #3B82F6 0%, #2563EB 100%) !important;
        border-color: rgba(255, 255, 255, 0.25) !important;
        box-shadow: 0 4px 12px rgba(37, 99, 235, 0.35) !important;
        transform: translateY(-1px) !important;
    }

    /* Radio navigation styling */
    div[data-testid="stRadio"] > div {
        background-color: rgba(255, 255, 255, 0.03);
        padding: 0.5rem;
        border-radius: 10px;
        border: 1px solid var(--border-subtle);
    }
    div[data-testid="stRadio"] label {
        color: var(--text-secondary) !important;
        font-weight: 500 !important;
        padding: 0.35rem 0.5rem !important;
        border-radius: 6px !important;
    }

    /* Sliders and Selects */
    div[data-baseweb="slider"] {
        padding-top: 0.5rem;
        padding-bottom: 0.5rem;
    }

    /* Dataframe table dark theme */
    div[data-testid="stDataFrame"] {
        border-radius: 10px;
        overflow: hidden;
        border: 1px solid var(--border-subtle);
    }

    /* Progress bar */
    .stProgress > div > div > div > div {
        background: linear-gradient(90deg, #00F0FF, #3B82F6) !important;
    }
    </style>
    """

def inject_custom_css():
    """Inject custom styles into the Streamlit app."""
    st.markdown(get_custom_css(), unsafe_allow_html=True)
