import streamlit as st


def inject_css():
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@300;400;500;600;700&display=swap');

    :root {
        --bg-main:   #0a0a0a;
        --bg-card:   #141414;
        --bg-input:  #0a0a0a;
        --border:    #1c2a3d;
        --text-main: #e8eef8;
        --text-sub:  #7a9cc7;
        --accent:    #3b82f6;
        --green:     #22c55e;
        --red:       #ef4444;
    }

    html, body, [class*="css"] {
        font-family: 'DM Sans', sans-serif;
        color: var(--text-main);
    }

    .stApp { background: var(--bg-main); }
    p, span, div, li { color: var(--text-main); }

    h1 {
        font-size: 24px !important;
        font-weight: 700 !important;
        color: var(--text-main) !important;
    }

    h4 {
        color: var(--text-main) !important;
        font-size: 13px !important;
        font-weight: 600 !important;
        text-transform: uppercase;
        letter-spacing: .7px;
        border-left: 2px solid var(--accent);
        padding-left: 8px;
        margin-top: 8px !important;
        margin-bottom: 4px !important;
    }

    /* Cards de status */
    .card-status {
        background: var(--bg-card);
        border: 1px solid var(--border);
        border-radius: 16px;
        padding: 24px 28px;
        margin-bottom: 8px;
        position: relative;
        overflow: hidden;
        box-shadow: 0 4px 20px rgba(0,0,0,.25);
        transition: transform .2s ease, box-shadow .2s ease;
    }
    .card-status:hover {
        transform: translateY(-2px);
        box-shadow: 0 8px 32px rgba(0,0,0,.4);
    }
    .card-status::before {
        content: '';
        position: absolute;
        top: 0; left: 0;
        width: 4px;
        height: 100%;
        border-radius: 16px 0 0 16px;
    }
    .card-icone  { font-size: 26px; margin-bottom: 8px; display: block; }
    .card-valor  { font-size: 48px; font-weight: 700; line-height: 1; margin-bottom: 6px; }
    .card-label  {
        font-size: 11px; font-weight: 600;
        text-transform: uppercase; letter-spacing: .7px;
        color: var(--text-sub);
    }
    .card-total {
        background: var(--bg-card);
        border: 1px solid var(--border);
        border-radius: 16px;
        padding: 28px 32px;
        margin-bottom: 12px;
        box-shadow: 0 4px 20px rgba(0,0,0,.25);
        transition: transform .2s ease, box-shadow .2s ease;
    }
    .card-total:hover {
        transform: translateY(-2px);
        box-shadow: 0 8px 32px rgba(0,0,0,.4);
    }
    .card-taxa {
        background: var(--bg-card);
        border: 1px solid var(--border);
        border-radius: 16px;
        padding: 24px 28px;
        margin-bottom: 8px;
        box-shadow: 0 4px 20px rgba(0,0,0,.25);
        transition: transform .2s ease, box-shadow .2s ease;
    }
    .card-taxa:hover {
        transform: translateY(-2px);
        box-shadow: 0 8px 32px rgba(0,0,0,.4);
    }

    /* Card de atendente no funil */
    .card-atendente {
        background: var(--bg-card);
        border: 1px solid var(--border);
        border-radius: 16px;
        padding: 24px 28px;
        margin-bottom: 12px;
        box-shadow: 0 4px 20px rgba(0,0,0,.25);
        transition: transform .2s ease, box-shadow .2s ease;
    }
    .card-atendente:hover {
        transform: translateY(-2px);
        box-shadow: 0 8px 32px rgba(0,0,0,.4);
    }
    .atendente-nome {
        font-size: 18px;
        font-weight: 700;
        color: var(--text-main);
        margin-bottom: 16px;
        padding-bottom: 10px;
        border-bottom: 1px solid var(--border);
    }
    .temp-badge {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        border-radius: 99px;
        padding: 4px 14px;
        font-size: 13px;
        font-weight: 600;
        margin-bottom: 4px;
    }

    /* Loading skeleton */
    .loading-box {
        background: var(--bg-card);
        border: 1px solid var(--border);
        border-radius: 16px;
        padding: 40px 24px;
        margin-bottom: 8px;
        text-align: center;
        color: var(--text-sub);
        font-size: 14px;
        animation: pulse 1.5s ease-in-out infinite;
    }
    @keyframes pulse {
        0%, 100% { opacity: 1; }
        50%       { opacity: 0.4; }
    }

    /* Selectbox / multiselect */
    [data-baseweb="select"] > div {
        background: var(--bg-input) !important;
        border: 1px solid var(--border) !important;
        color: var(--text-main) !important;
        border-radius: 8px !important;
    }
    [data-baseweb="select"] span { color: var(--text-main) !important; }
    [data-baseweb="popover"] {
        background: var(--bg-card) !important;
        border: 1px solid var(--border) !important;
    }
    [role="option"] { color: var(--text-main) !important; }
    [role="option"]:hover { background: var(--bg-input) !important; }

    /* Labels */
    label, [data-testid="stWidgetLabel"] {
        color: var(--text-sub) !important;
        font-size: 13px !important;
    }

    /* Tabela */
    [data-testid="stDataFrame"] {
        background: var(--bg-card) !important;
        border: 1px solid var(--border) !important;
        border-radius: 12px !important;
        overflow: hidden !important;
    }
    [data-testid="stDataFrame"] thead tr th {
        background: var(--bg-input) !important;
        color: var(--text-sub) !important;
        font-size: 11px !important;
        font-weight: 600 !important;
        text-transform: uppercase !important;
        letter-spacing: .6px !important;
    }
    [data-testid="stDataFrame"] tbody tr td {
        background: var(--bg-card) !important;
        color: var(--text-main) !important;
        font-size: 13px !important;
    }
    [data-testid="stDataFrame"] tbody tr:hover td {
        background: rgba(59,130,246,.04) !important;
        transition: background .15s !important;
    }

    /* Botão */
    .stButton > button {
        background: var(--bg-input) !important;
        color: var(--text-main) !important;
        border: 1px solid var(--border) !important;
        border-radius: 8px !important;
        font-weight: 500 !important;
    }
    .stButton > button:hover {
        border-color: var(--accent) !important;
        color: var(--accent) !important;
    }

    /* Tabs */
    [data-testid="stTabs"] [role="tablist"] {
        background: var(--bg-card) !important;
        border-radius: 12px !important;
        padding: 4px !important;
        border: 1px solid var(--border) !important;
        gap: 4px !important;
    }
    [data-testid="stTabs"] [role="tab"] {
        color: var(--text-sub) !important;
        font-weight: 500 !important;
        border-radius: 8px !important;
        padding: 6px 12px !important;
        font-size: 13px !important;
        transition: background .15s, color .15s !important;
    }
    [data-testid="stTabs"] [role="tab"][aria-selected="true"] {
        background: var(--bg-input) !important;
        color: var(--text-main) !important;
        font-weight: 700 !important;
    }
    [data-testid="stTabs"] [role="tab"]:hover {
        background: rgba(255,255,255,.05) !important;
        color: var(--text-main) !important;
    }

    hr {
        border: none !important;
        border-top: 1px solid var(--border) !important;
        opacity: 0.5 !important;
        margin: 20px 0 !important;
    }

    /* Micro-animação de entrada nos cards */
    @keyframes fadeInUp {
        from { opacity: 0; transform: translateY(8px); }
        to   { opacity: 1; transform: translateY(0); }
    }
    .card-status { animation: fadeInUp .25s ease both; }
    .card-total  { animation: fadeInUp .25s ease both; }
    .card-taxa   { animation: fadeInUp .25s ease both; }

    .update-time {
        color: var(--text-sub);
        font-size: 12px;
        text-align: right;
    }

    header[data-testid="stHeader"] {
        background: var(--bg-main) !important;
        border-bottom: 1px solid var(--border) !important;
    }
    #MainMenu, footer { visibility: hidden; }
    [data-testid="stToolbar"] { display: none; }

    /* Campo de data */
    [data-testid="stDateInput"] input {
        background: var(--bg-input) !important;
        color: var(--text-main) !important;
        border: 1px solid var(--border) !important;
        border-radius: 8px !important;
    }
    [data-testid="stDateInput"] > div {
        background: var(--bg-input) !important;
        border: 1px solid var(--border) !important;
        border-radius: 8px !important;
    }
    [data-baseweb="calendar"] {
        background: var(--bg-card) !important;
        border: 1px solid var(--border) !important;
    }
    [data-baseweb="calendar"] * { color: var(--text-main) !important; }

    /* Gap entre colunas */
    [data-testid="stHorizontalBlock"] {
        gap: 1.25rem !important;
    }

    /* Multiselect tags */
    [data-baseweb="tag"] {
        background: rgba(59,130,246,.12) !important;
        border: 1px solid rgba(59,130,246,.3) !important;
        border-radius: 6px !important;
    }
    [data-baseweb="tag"] span { color: var(--text-main) !important; }

    /* ── Nav bar horizontal (st.radio) ─────────────────────────────── */
    div[data-testid="stRadio"] > div { gap: 0 !important; }
    div[data-testid="stRadio"] [role="radiogroup"] {
        display: flex !important; flex-wrap: wrap !important; gap: 6px !important;
        background: var(--bg-card) !important; padding: 8px 10px !important;
        border-radius: 12px !important; border: 1px solid var(--border) !important;
    }
    div[data-testid="stRadio"] [role="radiogroup"] label {
        padding: 7px 15px !important; border-radius: 8px !important;
        color: var(--text-sub) !important; font-size: 13px !important;
        font-weight: 500 !important; cursor: pointer !important;
        border: 1px solid transparent !important; white-space: nowrap !important;
        transition: background .15s, color .15s, border-color .15s !important;
    }
    div[data-testid="stRadio"] [role="radiogroup"] label:hover {
        background: rgba(79,142,247,.1) !important; color: var(--text-main) !important;
        border-color: rgba(79,142,247,.35) !important;
    }
    div[data-testid="stRadio"] [role="radiogroup"] label:has(input:checked) {
        background: rgba(79,142,247,.18) !important; color: #4f8ef7 !important;
        border-color: rgba(79,142,247,.55) !important; font-weight: 600 !important;
    }
    div[data-testid="stRadio"] [role="radiogroup"] label > div:first-child { display: none !important; }
    </style>
    """, unsafe_allow_html=True)
