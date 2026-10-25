"""
Phase 7: Dashboard Styling & Visual Design System.

Provides professional light theme styling, subtle card layouts,
status badges, and responsive typography for the Predictive Memory Optimizer UI.
"""

import streamlit as st

def get_custom_css() -> str:
    """Return the CSS style definitions for the professional light theme dashboard."""
    return """
    <style>
    /* Google Fonts Import */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap');

    /* Global CSS Variables - Professional Light Theme */
    :root {
        --bg-primary: #F8FAFC;
        --bg-card: #FFFFFF;
        --bg-card-hover: #F1F5F9;
        --bg-surface: #FFFFFF;
        --border-subtle: #E2E8F0;
        --border-accent: #CBD5E1;
        --text-primary: #0F172A;
        --text-secondary: #475569;
        --text-muted: #64748B;
        --color-blue: #2563EB;
        --color-cyan: #0284C7;
        --color-purple: #7C3AED;
        --color-emerald: #16A34A;
        --color-amber: #D97706;
        --color-orange: #EA580C;
        --color-rose: #DC2626;
        --color-indigo: #4F46E5;
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
        color: var(--text-primary);
        display: flex;
        align-items: center;
        gap: 0.75rem;
    }
    .dashboard-subtitle {
        font-size: 0.95rem;
        color: var(--text-muted);
        margin-top: 0.25rem;
    }

    /* Custom Metric Cards - Light Theme */
    .metric-card {
        background: #FFFFFF;
        border: 1px solid var(--border-subtle);
        border-radius: 10px;
        padding: 1.25rem;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05), 0 1px 2px rgba(0, 0, 0, 0.03);
        transition: transform 0.2s ease, border-color 0.2s ease, box-shadow 0.2s ease;
        position: relative;
        overflow: hidden;
    }
    .metric-card:hover {
        transform: translateY(-2px);
        border-color: #CBD5E1;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
    }
    .metric-card::before {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        height: 3px;
        background: var(--color-blue);
    }
    .metric-card.cyan::before, .metric-card.blue::before { background: #2563EB; }
    .metric-card.emerald::before { background: #16A34A; }
    .metric-card.amber::before { background: #D97706; }
    .metric-card.orange::before { background: #EA580C; }
    .metric-card.rose::before { background: #DC2626; }
    .metric-card.purple::before { background: #7C3AED; }

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
        color: var(--text-primary);
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

    /* Badges - Light Theme High Contrast */
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
        background: #DCFCE7;
        color: #15803D;
        border: 1px solid #86EFAC;
    }
    .badge-moderate {
        background: #FEF3C7;
        color: #B45309;
        border: 1px solid #FCD34D;
    }
    .badge-high {
        background: #FFEDD5;
        color: #C2410C;
        border: 1px solid #FDBA74;
    }
    .badge-critical {
        background: #FEE2E2;
        color: #B91C1C;
        border: 1px solid #FCA5A5;
    }
    .badge-purple {
        background: #F3E8FF;
        color: #7E22CE;
        border: 1px solid #D8B4FE;
    }
    .badge-cyan, .badge-blue {
        background: #DBEAFE;
        color: #1D4ED8;
        border: 1px solid #93C5FD;
    }
    .badge-protected {
        background: #EEF2FF;
        color: #4338CA;
        border: 1px solid #C7D2FE;
    }

    /* Content Cards */
    .content-box {
        background-color: var(--bg-card);
        border: 1px solid var(--border-subtle);
        border-radius: 10px;
        padding: 1.5rem;
        margin-bottom: 1.5rem;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.04);
    }
    .content-box-header {
        font-size: 1.1rem;
        font-weight: 700;
        color: var(--text-primary);
        margin-bottom: 1rem;
        display: flex;
        justify-content: space-between;
        align-items: center;
    }

    /* Recommendation Cards */
    .rec-card {
        background: var(--bg-card);
        border: 1px solid var(--border-subtle);
        border-radius: 10px;
        padding: 1.25rem;
        margin-bottom: 1rem;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.04);
        transition: all 0.2s ease;
    }
    .rec-card:hover {
        border-color: #CBD5E1;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.06);
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
        background: #F8FAFC;
        border: 1px solid #CBD5E1;
        border-radius: 8px;
        padding: 0.85rem 1.25rem;
        margin-bottom: 1.5rem;
        display: flex;
        align-items: center;
        gap: 0.75rem;
        color: #334155;
        font-size: 0.88rem;
    }
    .safety-banner strong {
        color: #1E293B;
    }

    /* Streamlit Native Elements Customization */
    div[data-testid="stMetricValue"] {
        font-family: 'JetBrains Mono', monospace !important;
        color: var(--text-primary) !important;
        font-size: 1.75rem !important;
    }
    
    div[data-testid="stMetricLabel"] {
        color: var(--text-secondary) !important;
        font-size: 0.85rem !important;
        font-weight: 600 !important;
    }

    /* Sidebar Styling - Light Theme */
    section[data-testid="stSidebar"] {
        background-color: #F8FAFC !important;
        border-right: 1px solid var(--border-subtle) !important;
    }
    
    section[data-testid="stSidebar"] .block-container {
        padding-top: 2rem !important;
        padding-left: 1.25rem !important;
        padding-right: 1.25rem !important;
    }

    /* Buttons */
    .stButton > button {
        background: #2563EB !important;
        color: #FFFFFF !important;
        border: 1px solid #1D4ED8 !important;
        border-radius: 8px !important;
        padding: 0.5rem 1.25rem !important;
        font-weight: 600 !important;
        font-size: 0.88rem !important;
        transition: all 0.2s ease !important;
    }
    .stButton > button:hover {
        background: #1D4ED8 !important;
        border-color: #1E40AF !important;
        box-shadow: 0 2px 6px rgba(37, 99, 235, 0.25) !important;
        transform: translateY(-1px) !important;
    }

    /* Radio navigation styling */
    div[data-testid="stRadio"] > div {
        background-color: #FFFFFF !important;
        padding: 0.5rem;
        border-radius: 8px;
        border: 1px solid var(--border-subtle);
    }
    div[data-testid="stRadio"] label {
        color: var(--text-primary) !important;
        font-weight: 500 !important;
        padding: 0.35rem 0.5rem !important;
        border-radius: 6px !important;
    }

    /* Sliders and Selects */
    div[data-baseweb="slider"] {
        padding-top: 0.5rem;
        padding-bottom: 0.5rem;
    }

    /* Dataframe table light theme */
    div[data-testid="stDataFrame"] {
        border-radius: 8px;
        overflow: hidden;
        border: 1px solid var(--border-subtle);
        background: #FFFFFF;
    }

    /* Progress bar */
    .stProgress > div > div > div > div {
        background: #2563EB !important;
    }

    /* Investigation highlight box */
    .investigation-panel {
        background: #FFFFFF;
        border: 1px solid #CBD5E1;
        border-left: 4px solid #2563EB;
        border-radius: 8px;
        padding: 1.25rem;
        margin-top: 1rem;
        margin-bottom: 1.5rem;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
    }
    </style>
    """

def inject_custom_css():
    """Inject custom styles into the Streamlit app."""
    st.markdown(get_custom_css(), unsafe_allow_html=True)

