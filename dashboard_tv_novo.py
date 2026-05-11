import streamlit as st
import requests
import pandas as pd
import plotly.graph_objects as go
import base64
import os
from datetime import datetime, date, timedelta
from PIL import Image
from config import ACCESS_TOKEN

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# ── CONFIG ────────────────────────────────────────────────────────────────────
_logo = Image.open(os.path.join(SCRIPT_DIR, "logo o2 atualizada.png"))
st.set_page_config(
    page_title="Dashboard · O2 Solution",
    page_icon=_logo,
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── RENOMEAÇÃO DE ORIGENS ─────────────────────────────────────────────────────
ORIGEM_MAP = {
    "Livia": "O2 Solution",
}

# ── MAPEAMENTO DE STATUS ───────────────────────────────────────────────────────
STATUS_MAP = {
    "pending":            "Primeiro Contato",
    "scheduled":          "Agendado",
    "proposal_sent":      "Proposta Enviada",
    "waiting_billing":    "Aguardando Pagamento",
    "sale_performed":     "Venda Realizada",
    "sale_not_performed": "Venda não Realizada",
}

# Mapeamento da temperatura vinda da API para exibição em português
PERCEPTION_MAP = {
    "hot":  "🔥 Quente",
    "warm": "🌡️ Morno",
    "cold": "🧊 Frio",
    # fallback: se vier em português ou outro valor, mantém como veio
}

CORES_STATUS = {
    "Primeiro Contato":    "#4f8ef7",
    "Agendado":            "#f59e0b",
    "Proposta Enviada":    "#8b5cf6",
    "Aguardando Pagamento":"#f97316",
    "Venda Realizada":     "#22c55e",
    "Venda não Realizada": "#ef4444",
}

CORES_PERCEPTION = {
    "🔥 Quente": "#ef4444",   # vermelho quente
    "🌡️ Morno":  "#f59e0b",   # âmbar
    "🧊 Frio":   "#4f8ef7",   # azul frio
}

# ── HORAS ÚTEIS (sem fins de semana e feriados BR) ────────────────────────────
FERIADOS_BR = {
    date(2025, 1, 1), date(2025, 4, 18), date(2025, 4, 21),
    date(2025, 5, 1), date(2025, 6, 19), date(2025, 9, 7),
    date(2025, 10, 12), date(2025, 11, 2), date(2025, 11, 15),
    date(2025, 11, 20), date(2025, 12, 25),
    date(2026, 1, 1), date(2026, 4, 3), date(2026, 4, 21),
    date(2026, 5, 1), date(2026, 6, 4), date(2026, 9, 7),
    date(2026, 10, 12), date(2026, 11, 2), date(2026, 11, 15),
    date(2026, 11, 20), date(2026, 12, 25),
}


def horas_uteis(dt_inicio: datetime, dt_fim: datetime) -> float:
    """Horas corridas entre dois datetimes, pulando fins de semana e feriados BR."""
    if dt_fim <= dt_inicio:
        return 0.0
    total = 0.0
    current = dt_inicio
    while current < dt_fim:
        next_day = (current + timedelta(days=1)).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        if current.weekday() < 5 and current.date() not in FERIADOS_BR:
            total += (min(next_day, dt_fim) - current).total_seconds()
        current = next_day
    return total / 3600


# ── CSS ───────────────────────────────────────────────────────────────────────
def inject_css():
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@300;400;500;600;700&display=swap');

    :root {
        --bg-main:   #060e1a;
        --bg-card:   #050b14;
        --bg-input:  #060e1a;
        --border:    #152a4a;
        --text-main: #e8eef8;
        --text-sub:  #7a9cc7;
        --accent:    #4f8ef7;
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
        color: var(--accent) !important;
        font-size: 13px !important;
        font-weight: 700 !important;
        text-transform: uppercase;
        letter-spacing: .7px;
        border-left: 3px solid var(--accent);
        padding-left: 8px;
        margin-top: 8px !important;
        margin-bottom: 4px !important;
    }

    /* Cards de status */
    .card-status {
        background: var(--bg-card);
        border: 1px solid var(--border);
        border-radius: 16px;
        padding: 20px 24px;
        margin-bottom: 8px;
        position: relative;
        overflow: hidden;
    }
    .card-status::before {
        content: '';
        position: absolute;
        top: 0; left: 0;
        width: 4px;
        height: 100%;
        border-radius: 16px 0 0 16px;
    }
    .card-icone  { font-size: 30px; margin-bottom: 8px; display: block; }
    .card-valor  { font-size: 42px; font-weight: 700; line-height: 1; margin-bottom: 6px; }
    .card-label  {
        font-size: 13px; font-weight: 600;
        text-transform: uppercase; letter-spacing: .6px;
        color: var(--text-sub);
    }
    .card-total {
        background: var(--bg-card);
        border: 1px solid var(--accent);
        border-radius: 16px;
        padding: 20px 24px;
        margin-bottom: 8px;
    }
    .card-taxa {
        background: var(--bg-card);
        border: 1px solid #22c55e;
        border-radius: 16px;
        padding: 20px 24px;
        margin-bottom: 8px;
    }

    /* Card de atendente no funil */
    .card-atendente {
        background: var(--bg-card);
        border: 1px solid var(--border);
        border-radius: 16px;
        padding: 20px 24px;
        margin-bottom: 12px;
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
        border-radius: 10px !important;
    }
    [data-testid="stDataFrame"] thead tr th {
        background: var(--bg-input) !important;
        color: var(--text-main) !important;
    }
    [data-testid="stDataFrame"] tbody tr td {
        background: var(--bg-card) !important;
        color: var(--text-main) !important;
    }
    [data-testid="stDataFrame"] tbody tr:hover td {
        background: var(--bg-input) !important;
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
        padding: 8px 16px !important;
    }
    [data-testid="stTabs"] [role="tab"][aria-selected="true"] {
        background: var(--bg-input) !important;
        color: var(--text-main) !important;
        font-weight: 700 !important;
    }
    [data-testid="stTabs"] [role="tab"]:hover {
        color: var(--text-main) !important;
    }

    hr { border-color: var(--border) !important; }

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

    /* Multiselect tags */
    [data-baseweb="tag"] {
        background: var(--bg-input) !important;
        border: 1px solid var(--border) !important;
    }
    [data-baseweb="tag"] span { color: var(--text-main) !important; }
    </style>
    """, unsafe_allow_html=True)


# ── BUSCA DE DADOS ─────────────────────────────────────────────────────────────
DIAS_CRITICOS = 4  # últimos N dias considerados tempo-real


def _fetch_leads_from_api(days: int, date_of: str = "creation"):
    headers = {"Authorization": f"Bearer {ACCESS_TOKEN}", "Accept": "application/json"}
    todos_leads = []
    pagina = 1
    date_from = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    while True:
        params = {"date_from": date_from, "date_of": date_of, "per_page": 200, "page": pagina}
        ultimo_erro = None
        data = None
        for _ in range(3):
            try:
                response = requests.get(
                    "https://api.followize.com.br/v3/leads",
                    headers=headers, params=params, timeout=60
                )
                if response.status_code != 200:
                    return pd.DataFrame(), f"Erro na API: {response.status_code}"
                data = response.json()
                ultimo_erro = None
                break
            except Exception as e:
                ultimo_erro = e
        if ultimo_erro is not None:
            return pd.DataFrame(), f"Erro ao buscar leads: {ultimo_erro}"
        leads = data.get("data", [])
        if not leads:
            break
        todos_leads.extend(leads)
        meta = data.get("meta", {})
        if pagina >= meta.get("last_page", 1):
            break
        pagina += 1

    registros = []
    for lead in todos_leads:
        atendente = (
            ((lead.get("contact") or {}).get("attendant") or {}).get("name")
            or (lead.get("attendant") or {}).get("name", "Sem atendente")
        )
        status_raw     = lead.get("status", "")
        status_pt      = STATUS_MAP.get(status_raw, status_raw)
        origem_raw     = (lead.get("tracking") or {}).get("source", "") or "Sem origem"
        origem         = ORIGEM_MAP.get(origem_raw, origem_raw)
        equipe         = ((lead.get("contact") or {}).get("team") or {}).get("name", "")
        interesse      = ((lead.get("interests") or {}).get("interest_1") or {}).get("name", "")
        criado_em      = lead.get("created_at", "")
        atualizado_em  = lead.get("updated_at", "")
        perception_raw = lead.get("perception") or ""
        perception_pt  = PERCEPTION_MAP.get(perception_raw, perception_raw or "Sem percepção")
        last_proposal  = lead.get("last_proposal") or {}
        valor_proposta = last_proposal.get("amount") or 0.0
        def _parse_dt(s):
            for fmt in ("%Y-%m-%dT%H:%M:%S.%fZ", "%Y-%m-%dT%H:%M:%SZ",
                        "%Y-%m-%dT%H:%M:%S.%f+00:00", "%Y-%m-%dT%H:%M:%S+00:00"):
                try:
                    return datetime.strptime(s, fmt)
                except ValueError:
                    continue
            return None

        data_obj = None
        if criado_em:
            dt = _parse_dt(criado_em)
            if dt:
                data_obj  = dt.date()
                criado_em = dt.strftime("%d/%m/%Y %H:%M")
        if atualizado_em:
            dt = _parse_dt(atualizado_em)
            if dt:
                atualizado_em = dt.strftime("%d/%m/%Y %H:%M")

        email    = (lead.get("contact") or {}).get("email", "") or ""
        telefone = ((lead.get("contact") or {}).get("cellphone") or
                    (lead.get("contact") or {}).get("phone", "")) or ""
        int2     = ((lead.get("interests") or {}).get("interest_2") or {}).get("name", "") or ""
        int3     = ((lead.get("interests") or {}).get("interest_3") or {}).get("name", "") or ""

        last_inter = lead.get("last_interaction_at", "") or ""
        last_inter_dt = None
        if last_inter:
            dt = _parse_dt(last_inter)
            if dt:
                last_inter_dt = dt
                last_inter = dt.strftime("%d/%m/%Y %H:%M")

        status_fechado = status_raw in ("sale_performed", "sale_not_performed")
        em_atraso = False
        if last_inter_dt and not status_fechado:
            em_atraso = horas_uteis(last_inter_dt, datetime.now()) > 24

        last_sched = lead.get("last_schedule") or {}
        sched_data, sched_tipo, sched_status = "", "", ""
        if isinstance(last_sched, dict) and last_sched:
            _v = last_sched.get("date", "")
            if _v:
                _dt2 = _parse_dt(str(_v))
                sched_data = _dt2.strftime("%d/%m/%Y %H:%M") if _dt2 else str(_v)
            sched_tipo   = ((last_sched.get("reason") or {}).get("name", "")) or ""
            sched_status = last_sched.get("status", "") or ""

        registros.append({
            "id":                  lead.get("id"),
            "nome":                lead.get("name", ""),
            "status":              status_pt,
            "atendente":           atendente,
            "origem":              origem,
            "equipe":              equipe,
            "interesse":           interesse,
            "criado_em":           criado_em,
            "data_obj":            data_obj,
            "perception":          perception_pt,
            "valor_proposta":      float(valor_proposta),
            "atualizado_em":       atualizado_em,
            "email":               email,
            "telefone":            telefone,
            "interest_2":          int2,
            "interest_3":          int3,
            "last_interaction_at": last_inter,
            "agendamento_data":    sched_data,
            "agendamento_tipo":    sched_tipo,
            "agendamento_status":  sched_status,
            "first_interaction_at": last_inter,
            "message_lead":        lead.get("message", "") or "",
            "em_atraso":           em_atraso,
        })
    return pd.DataFrame(registros), None


@st.cache_data(ttl=1800, show_spinner=False)
def fetch_leads_30dias():
    """30 dias por criação · cache 30 min · abas de visão geral."""
    return _fetch_leads_from_api(days=30, date_of="creation")


@st.cache_data(ttl=1800, show_spinner=False)
def fetch_leads_80dias():
    """80 dias por criação · cache 30 min · funil de atendentes."""
    return _fetch_leads_from_api(days=80, date_of="creation")


@st.cache_data(ttl=60, show_spinner=False)
def fetch_leads_criticos():
    """Últimos 4 dias por atualização · cache 60s · captura qualquer lead modificado."""
    return _fetch_leads_from_api(days=DIAS_CRITICOS, date_of="change")


@st.cache_data(ttl=55, show_spinner=False)
def fetch_leads_hoje():
    """Leads criados nos últimos 2 dias por criação · cache 55s · para o painel Hoje."""
    return _fetch_leads_from_api(days=2, date_of="creation")


def _merge(df_hist, err1):
    df_crit, err2 = fetch_leads_criticos()
    if df_hist.empty and df_crit.empty:
        return pd.DataFrame(), err1 or err2
    partes = [p for p in [df_crit, df_hist] if not p.empty]
    merged = pd.concat(partes, ignore_index=True)
    if "id" in merged.columns:
        merged = merged.drop_duplicates(subset=["id"], keep="first")
    return merged, err1 or err2


def merge_leads_curto():
    """30 dias + críticos · usado em Visão Geral, Operador, Detalhamento e Leads."""
    df_hist, err1 = fetch_leads_30dias()
    return _merge(df_hist, err1)


def merge_leads_longo():
    """80 dias + críticos · usado no Funil de Vendas."""
    df_hist, err1 = fetch_leads_80dias()
    return _merge(df_hist, err1)


# ── HELPERS ───────────────────────────────────────────────────────────────────
def fmt_brl(valor: float) -> str:
    """Formata um número como moeda brasileira: R$ 1.234,56"""
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


@st.cache_data(show_spinner=False)
def foto_base64(path: str) -> str | None:
    try:
        abs_path = os.path.join(SCRIPT_DIR, path)
        with open(abs_path, "rb") as f:
            ext = path.rsplit(".", 1)[-1].lower()
            mime = "image/jpeg" if ext in ("jpg", "jpeg") else f"image/{ext}"
            return f"data:{mime};base64,{base64.b64encode(f.read()).decode()}"
    except Exception:
        return None


def linhas_por_operador(df, status_filtro, cor):
    """Gera linhas HTML de contagem por origem (operador) para um dado status."""
    df_f = df[df["status"] == status_filtro] if status_filtro else df
    ranking = (
        df_f.groupby("origem").size()
        .reset_index(name="qtd")
        .sort_values("qtd", ascending=False)
    )
    if ranking.empty:
        return '<span style="color:#7a9cc7;font-size:12px;">Sem registros</span>'
    html = ""
    for _, row in ranking.iterrows():
        html += (
            '<div style="display:flex;justify-content:space-between;align-items:center;'
            'padding:3px 0;border-bottom:1px solid #152a4a;">'
            f'<span style="color:#e8eef8;font-size:12px;">👤 {row["origem"]}</span>'
            f'<span style="color:{cor};font-weight:700;font-size:13px;">{row["qtd"]}</span>'
            '</div>'
        )
    return html


def render_card(icone, valor, label, cor, df=None, status_filtro=None):
    """Renderiza card de métrica com breakdown opcional por operador."""
    if df is not None:
        linhas = linhas_por_operador(df, status_filtro, cor)
        st.markdown(f"""
        <div class="card-status" style="border-left:4px solid {cor};display:flex;gap:16px;align-items:flex-start;">
            <div style="min-width:90px;">
                <span class="card-icone">{icone}</span>
                <div class="card-valor" style="color:{cor};">{valor}</div>
                <div class="card-label">{label}</div>
            </div>
            <div style="width:1px;background:#152a4a;align-self:stretch;margin:4px 0;"></div>
            <div style="flex:1;min-width:0;padding-top:4px;">
                <div style="color:#7a9cc7;font-size:11px;font-weight:600;text-transform:uppercase;
                            letter-spacing:.6px;margin-bottom:6px;">Por Operador</div>
                {linhas}
            </div>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown(f"""
        <div class="card-status" style="border-left:4px solid {cor};">
            <span class="card-icone">{icone}</span>
            <div class="card-valor" style="color:{cor};">{valor}</div>
            <div class="card-label">{label}</div>
        </div>
        """, unsafe_allow_html=True)


# ── GRÁFICOS ──────────────────────────────────────────────────────────────────
def grafico_rosca(df):
    counts = df["status"].value_counts()
    labels = counts.index.tolist()
    values = counts.values.tolist()
    colors = [CORES_STATUS.get(l, "#aaa") for l in labels]
    fig = go.Figure(go.Pie(
        labels=labels, values=values, hole=0.55,
        marker=dict(colors=colors, line=dict(color="#050b14", width=2)),
        textinfo="label+percent",
        textfont=dict(size=12, color="#e8eef8"),
        hovertemplate="<b>%{label}</b><br>%{value} leads (%{percent})<extra></extra>",
    ))
    fig.update_layout(
        margin=dict(t=10, b=10, l=10, r=10), showlegend=False, height=280,
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
    )
    return fig


def grafico_origens(df):
    vendas  = df[df["status"] == "Venda Realizada"]
    ranking = vendas["origem"].value_counts().head(10)
    fig = go.Figure(go.Bar(
        x=ranking.values.tolist(), y=ranking.index.tolist(), orientation="h",
        marker=dict(
            color=ranking.values.tolist(),
            colorscale=[[0, "#050b14"], [1, "#22c55e"]],
            line=dict(color="#152a4a", width=1)
        ),
        text=ranking.values.tolist(), textposition="outside",
        textfont=dict(color="#e8eef8", size=12),
        hovertemplate="<b>%{y}</b><br>%{x} vendas<extra></extra>",
    ))
    fig.update_layout(
        margin=dict(t=10, b=10, l=10, r=40), height=280,
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(showgrid=True, gridcolor="#152a4a", color="#7a9cc7", zeroline=False),
        yaxis=dict(color="#e8eef8", autorange="reversed"),
    )
    return fig


def grafico_acumulado(df, operadores):
    CORES_OP = ["#4f8ef7", "#22c55e", "#f59e0b", "#8b5cf6", "#ef4444", "#f97316"]
    fig = go.Figure()
    for i, operador in enumerate(operadores):
        df_op = df[df["origem"] == operador].copy()
        df_op = df_op[df_op["data_obj"].notna()]
        if df_op.empty:
            continue
        por_dia = df_op.groupby("data_obj").size().reset_index(name="leads")
        por_dia = por_dia.sort_values("data_obj")
        por_dia["acumulado"] = por_dia["leads"].cumsum()
        por_dia["data_fmt"]  = por_dia["data_obj"].apply(lambda d: d.strftime("%d/%m"))
        cor = CORES_OP[i % len(CORES_OP)]
        fig.add_trace(go.Scatter(
            x=por_dia["data_fmt"].tolist(), y=por_dia["acumulado"].tolist(),
            name=operador, mode="lines+markers",
            line=dict(color=cor, width=3),
            marker=dict(color=cor, size=8, symbol="circle"),
            hovertemplate=f"<b>{operador}</b><br>%{{x}}<br>%{{y}} leads acumulados<extra></extra>",
        ))
    fig.update_layout(
        margin=dict(t=20, b=20, l=10, r=20), height=320,
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        legend=dict(orientation="h", y=1.1, x=0, font=dict(color="#e8eef8", size=13)),
        xaxis=dict(showgrid=True, gridcolor="#152a4a", color="#7a9cc7",
                   tickfont=dict(color="#e8eef8", size=12)),
        yaxis=dict(showgrid=True, gridcolor="#152a4a", color="#7a9cc7",
                   tickfont=dict(color="#e8eef8", size=12), zeroline=False),
        hovermode="x unified",
    )
    return fig


def grafico_funil_status(df_atendente):
    """
    Gráfico de funil mostrando a quantidade de leads em cada etapa do status.
    O % exibido é individual de cada status em relação ao total de leads,
    e não acumulado em relação ao topo do funil.
    """
    ordem = [
        "Primeiro Contato",
        "Agendado",
        "Proposta Enviada",
        "Aguardando Pagamento",
        "Venda Realizada",
        "Venda não Realizada",
    ]
    contagens = df_atendente["status"].value_counts()
    labels = [s for s in ordem if s in contagens.index]
    values = [contagens[s] for s in labels]
    cores  = [CORES_STATUS[s] for s in labels]

    total = len(df_atendente)

    # Monta o texto de cada barra: quantidade + % individual do total
    # Ex: "12  (18,5%)" — cada status mostra sua própria fatia
    textos = [
        f"{v}  ({v / total * 100:.1f}%)" if total > 0 else str(v)
        for v in values
    ]

    fig = go.Figure(go.Funnel(
        y=labels,
        x=values,
        # "none" desliga o texto automático do Plotly para usarmos o nosso
        textinfo="none",
        text=textos,
        textposition="inside",
        textfont=dict(color="#e8eef8", size=13, family="DM Sans"),
        marker=dict(color=cores, line=dict(color="#050b14", width=1)),
        connector=dict(line=dict(color="#152a4a", width=1)),
        hovertemplate="<b>%{y}</b><br>%{x} leads<br>%{text}<extra></extra>",
    ))
    fig.update_layout(
        margin=dict(t=10, b=10, l=10, r=10),
        height=320,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        yaxis=dict(color="#e8eef8"),
    )
    return fig


def grafico_temperatura_pizza(df_atendente):
    """
    Gráfico de pizza com a distribuição de temperatura (quente/morno/frio)
    para os leads com percepção preenchida.
    """
    df_com_temp = df_atendente[df_atendente["perception"] != "Sem percepção"]
    if df_com_temp.empty:
        return None

    contagens = df_com_temp["perception"].value_counts()
    labels = contagens.index.tolist()
    values = contagens.values.tolist()
    cores  = [CORES_PERCEPTION.get(l, "#7a9cc7") for l in labels]

    fig = go.Figure(go.Pie(
        labels=labels, values=values, hole=0.5,
        marker=dict(colors=cores, line=dict(color="#050b14", width=2)),
        textinfo="label+value+percent",
        textfont=dict(size=12, color="#e8eef8"),
        hovertemplate="<b>%{label}</b><br>%{value} leads (%{percent})<extra></extra>",
    ))
    fig.update_layout(
        margin=dict(t=10, b=10, l=10, r=10),
        showlegend=False,
        height=280,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
    )
    return fig


def render_painel_atendente(df_atendente, nome_atendente, cor_atendente, foto_path=None):
    """
    Renderiza o painel completo de um atendente na aba de Funil:
    - Cards de temperatura com valores
    - Funil de status
    - Gráfico de temperatura
    - Tabela de leads
    """
    total_at    = len(df_atendente)
    total_valor = df_atendente["valor_proposta"].sum()
    vendas_at   = int((df_atendente["status"] == "Venda Realizada").sum())
    taxa_at     = f"{(vendas_at / total_at * 100):.1f}%" if total_at > 0 else "0%"

    # ── Avatar: foto circular ou iniciais como fallback ───────────────────────
    foto_uri = foto_base64(foto_path) if foto_path else None
    iniciais = "".join(p[0].upper() for p in nome_atendente.split()[:2])
    if foto_uri:
        avatar_html = (
            f'<img src="{foto_uri}" style="'
            f'width:64px;height:64px;border-radius:50%;'
            f'border:3px solid {cor_atendente};object-fit:cover;flex-shrink:0;">'
        )
    else:
        avatar_html = (
            f'<div style="width:64px;height:64px;border-radius:50%;'
            f'border:3px solid {cor_atendente};background:{cor_atendente}22;'
            f'display:flex;align-items:center;justify-content:center;'
            f'font-size:22px;font-weight:700;color:{cor_atendente};flex-shrink:0;">'
            f'{iniciais}</div>'
        )

    # ── Cabeçalho do atendente ────────────────────────────────────────────────
    st.markdown(f"""
    <div style="
        background: var(--bg-card);
        border: 2px solid {cor_atendente};
        border-radius: 16px;
        padding: 16px 24px;
        margin-bottom: 16px;
        display: flex;
        align-items: center;
        gap: 16px;
    ">
        {avatar_html}
        <div>
            <div style="font-size:20px;font-weight:700;color:{cor_atendente};">{nome_atendente}</div>
            <div style="font-size:13px;color:#7a9cc7;margin-top:2px;">
                <b>{total_at} leads no período · {vendas_at} vendas · {taxa_at} conversão</b>
            </div>
        </div>
        <div style="margin-left:auto;text-align:right;">
            <div style="font-size:11px;color:#7a9cc7;text-transform:uppercase;letter-spacing:.6px;">
                <b>Valor total em carteira</b>
            </div>
            <div style="font-size:24px;font-weight:700;color:#22c55e;">{fmt_brl(total_valor)}</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ── Cards de temperatura ──────────────────────────────────────────────────
    temps = {
        "🔥 Quente": {"cor": "#ef4444", "icone": "🔥"},
        "🌡️ Morno":  {"cor": "#f59e0b", "icone": "🌡️"},
        "🧊 Frio":   {"cor": "#4f8ef7", "icone": "🧊"},
    }

    ct1, ct2, ct3, ct4 = st.columns(4)
    cols_temp = [ct1, ct2, ct3]

    for col, (temp_label, cfg) in zip(cols_temp, temps.items()):
        df_temp   = df_atendente[df_atendente["perception"] == temp_label]
        qtd       = len(df_temp)
        valor_sum = df_temp["valor_proposta"].sum()
        with col:
            st.markdown(f"""
            <div class="card-status" style="border-left:4px solid {cfg['cor']};">
                <span class="card-icone">{cfg['icone']}</span>
                <div class="card-valor" style="color:{cfg['cor']};">{qtd}</div>
                <div class="card-label">{temp_label.split(' ', 1)[1]}</div>
                <div style="margin-top:8px;font-size:13px;font-weight:600;color:#22c55e;">
                    {fmt_brl(valor_sum)}
                </div>
                <div style="font-size:11px;color:#7a9cc7;">em propostas</div>
            </div>
            """, unsafe_allow_html=True)

    # Card de leads sem percepção preenchida
    sem_perc = int((df_atendente["perception"] == "Sem percepção").sum())
    with ct4:
        st.markdown(f"""
        <div class="card-status" style="border-left:4px solid #7a9cc7;">
            <span class="card-icone">❓</span>
            <div class="card-valor" style="color:#7a9cc7;">{sem_perc}</div>
            <div class="card-label">Sem percepção</div>
            <div style="margin-top:8px;font-size:11px;color:#7a9cc7;">não classificados</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Funil + Pizza lado a lado ─────────────────────────────────────────────
    cg1, cg2 = st.columns(2)
    with cg1:
        st.markdown("#### 🔽 Funil de Status")
        st.plotly_chart(
            grafico_funil_status(df_atendente),
            use_container_width=True,
            key=f"funil_{nome_atendente}"
        )
    with cg2:
        st.markdown("#### 🌡️ Distribuição de Temperatura")
        fig_pizza = grafico_temperatura_pizza(df_atendente)
        if fig_pizza:
            st.plotly_chart(
                fig_pizza,
                use_container_width=True,
                key=f"pizza_{nome_atendente}"
            )
        else:
            st.info("Nenhum lead com percepção classificada ainda.")

    # ── Tabela de leads do atendente ──────────────────────────────────────────
    st.markdown("#### 📋 Leads em Carteira")

    df_tabela = df_atendente.copy()
    df_tabela["Valor"] = df_tabela["valor_proposta"].apply(
        lambda v: fmt_brl(v) if v > 0 else "—"
    )
    if "em_atraso" in df_tabela.columns:
        df_tabela["Atraso"] = df_tabela["em_atraso"].apply(lambda x: "🔴 Em atraso" if x else "")
    else:
        df_tabela["Atraso"] = ""

    col_map = {
        "Atraso":        "Situação",
        "nome":          "Nome",
        "status":        "Status",
        "perception":    "Temperatura",
        "Valor":         "Valor da Proposta",
        "origem":        "Canal",
        "interesse":     "Interesse",
        "criado_em":     "Cadastrado em",
        "atualizado_em": "Última Atualização",
    }

    df_sorted_orig = df_tabela.copy()
    df_sorted_orig["_sort"] = pd.to_datetime(
        df_sorted_orig["atualizado_em"], format="%d/%m/%Y %H:%M", errors="coerce"
    )
    df_sorted_orig = (
        df_sorted_orig.sort_values("_sort", ascending=False)
        .drop(columns=["_sort"])
        .reset_index(drop=True)
    )
    df_show = df_sorted_orig[list(col_map.keys())].rename(columns=col_map)

    st.caption("💡 Clique em uma linha para ver os detalhes completos do lead.")
    modal_key = f"modal_shown_{nome_atendente}"
    evt = st.dataframe(
        df_show,
        use_container_width=True,
        hide_index=True,
        height=300,
        selection_mode="single-row",
        on_select="rerun",
        key=f"tabela_{nome_atendente}",
    )
    sel = evt.selection.rows
    if sel and st.session_state.get(modal_key) != sel[0]:
        st.session_state[modal_key] = sel[0]
        modal_lead(df_sorted_orig.iloc[sel[0]])
    if not sel:
        st.session_state.pop(modal_key, None)


# ── MODAL DE DETALHES DO LEAD ─────────────────────────────────────────────────
@st.dialog("📋 Detalhes do Lead", width="large")
def modal_lead(lead: pd.Series):
    nome    = lead.get("nome", "")    or ""
    status  = lead.get("status", "")  or ""
    temp    = lead.get("perception", "") or "Sem percepção"
    canal   = lead.get("origem", "")  or ""
    atend   = lead.get("atendente", "") or ""
    intere  = lead.get("interesse", "") or ""
    int2    = lead.get("interest_2", "") or ""
    int3    = lead.get("interest_3", "") or ""
    criado  = lead.get("criado_em", "")   or ""
    atualiz = lead.get("atualizado_em", "") or ""
    last_int= lead.get("last_interaction_at", "") or ""
    email   = lead.get("email", "")   or ""
    tel     = lead.get("telefone", "") or ""
    valor   = float(lead.get("valor_proposta", 0) or 0)
    ag_data   = lead.get("agendamento_data", "")   or ""
    ag_tipo   = lead.get("agendamento_tipo", "")   or ""
    ag_status = lead.get("agendamento_status", "") or ""
    msg_lead  = lead.get("message_lead", "")       or ""
    first_int = lead.get("first_interaction_at", "") or last_int

    em_atraso_flag = bool(lead.get("em_atraso", False))
    cor_s = CORES_STATUS.get(status, "#7a9cc7")
    cor_t = CORES_PERCEPTION.get(temp, "#7a9cc7")

    st.markdown(f"<h2 style='margin:0 0 8px;'>{nome}</h2>", unsafe_allow_html=True)
    badges = (
        f"<span style='background:{cor_s}22;color:{cor_s};border:1px solid {cor_s};"
        f"border-radius:99px;padding:3px 14px;font-size:13px;font-weight:600;margin-right:8px;'>"
        f"{status}</span>"
        f"<span style='background:{cor_t}22;color:{cor_t};border:1px solid {cor_t};"
        f"border-radius:99px;padding:3px 14px;font-size:13px;font-weight:600;margin-right:8px;'>"
        f"{temp}</span>"
        f"<span style='background:#152a4a;color:#7a9cc7;border:1px solid #152a4a;"
        f"border-radius:99px;padding:3px 14px;font-size:13px;font-weight:600;margin-right:8px;'>"
        f"📡 {canal}</span>"
    )
    if em_atraso_flag:
        badges += (
            "<span style='background:#ef444422;color:#ef4444;border:1px solid #ef4444;"
            "border-radius:99px;padding:3px 14px;font-size:13px;font-weight:600;'>"
            "🔴 Em atraso</span>"
        )
    st.markdown(badges, unsafe_allow_html=True)
    st.markdown("---")

    col_a, col_b = st.columns(2)

    with col_a:
        st.markdown(
            "<div style='color:#7a9cc7;font-size:11px;font-weight:600;"
            "text-transform:uppercase;letter-spacing:.7px;margin-bottom:8px;'>👤 Contato</div>",
            unsafe_allow_html=True,
        )
        st.markdown(f"**Atendente:** {atend}")
        if email:
            st.markdown(f"**E-mail:** {email}")
        if tel:
            st.markdown(f"**Telefone:** {tel}")

        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown(
            "<div style='color:#7a9cc7;font-size:11px;font-weight:600;"
            "text-transform:uppercase;letter-spacing:.7px;margin-bottom:8px;'>🎯 Interesse</div>",
            unsafe_allow_html=True,
        )
        interesses = [i for i in [intere, int2, int3] if i]
        if interesses:
            for i in interesses:
                st.markdown(f"• {i}")
        else:
            st.markdown(
                "<span style='color:#7a9cc7;font-size:13px;'>Não informado</span>",
                unsafe_allow_html=True,
            )

    with col_b:
        st.markdown(
            "<div style='color:#7a9cc7;font-size:11px;font-weight:600;"
            "text-transform:uppercase;letter-spacing:.7px;margin-bottom:8px;'>📅 Histórico</div>",
            unsafe_allow_html=True,
        )
        for label, val in [
            ("Cadastrado em",      criado),
            ("Última atualização", atualiz),
            ("Primeira interação", first_int),
            ("Última interação",   last_int),
        ]:
            if val:
                st.markdown(f"**{label}:** {val}")

        if valor > 0:
            st.markdown("<br>", unsafe_allow_html=True)
            st.markdown(
                "<div style='color:#7a9cc7;font-size:11px;font-weight:600;"
                "text-transform:uppercase;letter-spacing:.7px;margin-bottom:8px;'>💰 Proposta</div>",
                unsafe_allow_html=True,
            )
            st.markdown(
                f"<div style='font-size:26px;font-weight:700;color:#22c55e;'>{fmt_brl(valor)}</div>",
                unsafe_allow_html=True,
            )

    if ag_data or ag_tipo:
        st.markdown("---")
        st.markdown(
            "<div style='color:#7a9cc7;font-size:11px;font-weight:600;"
            "text-transform:uppercase;letter-spacing:.7px;margin-bottom:8px;'>📆 Último Agendamento</div>",
            unsafe_allow_html=True,
        )
        ag1, ag2 = st.columns(2)
        with ag1:
            if ag_data:
                st.markdown(f"**Data:** {ag_data}")
            if ag_tipo:
                st.markdown(f"**Motivo:** {ag_tipo}")
        with ag2:
            if ag_status:
                status_ag_map = {"pending": "⏳ Pendente", "done": "✅ Realizado", "canceled": "❌ Cancelado"}
                st.markdown(f"**Situação:** {status_ag_map.get(ag_status, ag_status)}")

    if msg_lead:
        st.markdown("---")
        st.markdown(
            "<div style='color:#7a9cc7;font-size:11px;font-weight:600;"
            "text-transform:uppercase;letter-spacing:.7px;margin-bottom:8px;'>📝 Campos do Lead</div>",
            unsafe_allow_html=True,
        )
        st.markdown(
            f"<div style='background:#060e1a;border:1px solid #152a4a;border-radius:8px;"
            f"padding:10px 14px;font-size:13px;color:#e8eef8;'>{msg_lead}</div>",
            unsafe_allow_html=True,
        )


# ── FRAGMENTS (abas de tempo real) ────────────────────────────────────────────
def _df_com_filtros_globais(df_base: pd.DataFrame) -> pd.DataFrame:
    """Aplica os filtros globais (período, origem, status) a qualquer dataframe."""
    data_de      = st.session_state.get("visao_de",     date.today() - timedelta(days=30))
    data_ate     = st.session_state.get("visao_ate",    date.today())
    selecionados = st.session_state.get("visao_origem", [])
    f_status     = st.session_state.get("visao_status", "Todos")
    df = df_base[df_base["data_obj"].apply(lambda d: d is not None and data_de <= d <= data_ate)]
    if selecionados:
        df = df[df["origem"].isin(selecionados)]
    if f_status != "Todos":
        df = df[df["status"] == f_status]
    return df


@st.fragment
def render_funil_rt():
    # ── Lazy load: só busca 80 dias quando o usuário solicitar ────────────────
    if "df_funil" not in st.session_state:
        st.markdown(
            "<div style='text-align:center;padding:48px 0 16px;color:#7a9cc7;font-size:14px;'>"
            "Os dados do Funil cobrem 80 dias e são carregados sob demanda."
            "</div>",
            unsafe_allow_html=True
        )
        _, col_c, _ = st.columns([1, 2, 1])
        with col_c:
            if st.button("📊 Carregar Funil de Vendas", use_container_width=True):
                with st.spinner("Buscando 80 dias de dados..."):
                    df, _ = merge_leads_longo()
                    st.session_state["df_funil"] = df
                st.rerun()
        return

    df_todos_rt = st.session_state["df_funil"]

    # ── Filtros independentes desta aba ────────────────────────────────────────
    st.markdown("#### 🔎 Filtros da Aba")
    ff1, ff2, ff3, ff4, ff5, ff6 = st.columns([1.5, 1.5, 2.5, 2, 1.5, 1.2])
    with ff1:
        funil_de = st.date_input(
            "📅 De",
            value=date.today() - timedelta(days=30),
            format="DD/MM/YYYY",
            key="funil_de"
        )
    with ff2:
        funil_ate = st.date_input(
            "📅 Até",
            value=date.today(),
            format="DD/MM/YYYY",
            key="funil_ate"
        )
    with ff3:
        ops_funil = sorted(df_todos_rt["origem"].dropna().unique().tolist()) if not df_todos_rt.empty else []
        funil_origem = st.multiselect(
            "👤 Origem",
            options=ops_funil,
            default=ops_funil,
            key="funil_origem"
        )
    with ff4:
        funil_status = st.selectbox(
            "📌 Status", ["Todos"] + list(STATUS_MAP.values()), key="funil_status"
        )
    with ff5:
        filtro_temp = st.selectbox(
            "🌡️ Temperatura",
            ["Todas", "🔥 Quente", "🌡️ Morno", "🧊 Frio", "Sem percepção"],
            key="filtro_temperatura"
        )
    with ff6:
        st.markdown("<div style='height:28px'></div>", unsafe_allow_html=True)
        if st.button("🔄 Atualizar", key="funil_refresh", use_container_width=True):
            fetch_leads_80dias.clear()
            with st.spinner("Atualizando..."):
                df, _ = merge_leads_longo()
                st.session_state["df_funil"] = df

    # ── Aplica filtros ────────────────────────────────────────────────────────
    df_funil = df_todos_rt.copy() if not df_todos_rt.empty else df_todos_rt
    if not df_funil.empty:
        df_funil = df_funil[df_funil["data_obj"].apply(
            lambda d: d is not None and funil_de <= d <= funil_ate
        )]
        if funil_origem:
            df_funil = df_funil[df_funil["origem"].isin(funil_origem)]
        if funil_status != "Todos":
            df_funil = df_funil[df_funil["status"] == funil_status]
        if filtro_temp != "Todas":
            df_funil = df_funil[df_funil["perception"] == filtro_temp]

    st.markdown("---")

    df_giovanna = df_funil[df_funil["atendente"].str.contains("Giovanna", case=False, na=False)]
    df_rayanna  = df_funil[df_funil["atendente"].str.contains("Rayanna",  case=False, na=False)]

    col_gio, col_sep, col_ray = st.columns([1, 0.04, 1])
    with col_gio:
        render_painel_atendente(df_giovanna, "Giovanna", "#8b5cf6", foto_path="fotos/giovanna.jpg")
    with col_ray:
        render_painel_atendente(df_rayanna,  "Rayanna",  "#f59e0b", foto_path="fotos/rayanna.jpg")

    st.markdown("---")
    st.markdown("#### 📊 Consolidado das Atendentes")

    total_carteira = df_funil["valor_proposta"].sum()
    leads_com_val  = int((df_funil["valor_proposta"] > 0).sum())
    ticket_medio   = total_carteira / leads_com_val if leads_com_val > 0 else 0

    rc1, rc2, rc3, rc4 = st.columns(4)
    with rc1:
        render_card("💰", fmt_brl(total_carteira), "Total em Carteira", "#22c55e")
    with rc2:
        render_card("🎟️", fmt_brl(ticket_medio), "Ticket Médio", "#4f8ef7")
    with rc3:
        render_card("🔥", int((df_funil["perception"] == "🔥 Quente").sum()), "Leads Quentes", "#ef4444")
    with rc4:
        render_card("🌡️", int((df_funil["perception"] == "🌡️ Morno").sum()), "Leads Mornos", "#f59e0b")


@st.fragment
def render_hoje_rt():
    df_base, _ = fetch_leads_hoje()
    if df_base.empty:
        return

    selecionados = st.session_state.get("visao_origem", [])
    hoje  = date.today()
    ontem = hoje - timedelta(days=1)

    df_base_hoje = df_base.copy()
    if selecionados:
        df_base_hoje = df_base_hoje[df_base_hoje["origem"].isin(selecionados)]

    df_ontem_v = df_base_hoje[df_base_hoje["data_obj"].apply(lambda d: d == ontem)]
    df_hoje_v  = df_base_hoje[df_base_hoje["data_obj"].apply(lambda d: d == hoje)]

    leads_hoje  = len(df_hoje_v)
    leads_ontem = len(df_ontem_v)
    diferenca   = leads_hoje - leads_ontem

    if diferenca > 0:
        seta, cor_seta = f"↑ +{diferenca} que ontem", "#22c55e"
    elif diferenca < 0:
        seta, cor_seta = f"↓ {diferenca} que ontem", "#ef4444"
    else:
        seta, cor_seta = "= igual a ontem", "#7a9cc7"

    operadores_hoje = (
        df_hoje_v.groupby("origem").size()
        .reset_index(name="qtd").sort_values("qtd", ascending=False)
    )

    META_DIARIA = 10
    progresso = min(leads_hoje / META_DIARIA, 1.0)
    pct_meta  = int(progresso * 100)
    cor_meta  = "#22c55e" if progresso >= 1.0 else "#f59e0b" if progresso >= 0.5 else "#ef4444"

    hd_col, hd_btn = st.columns([5, 1])
    with hd_col:
        st.markdown("#### 📅 Hoje")
    with hd_btn:
        if st.button("🔄 Atualizar Hoje", key="hoje_refresh", use_container_width=True):
            fetch_leads_hoje.clear()
    h1, h2 = st.columns(2)

    with h1:
        linhas_op = ""
        for _, row in operadores_hoje.iterrows():
            linhas_op += (
                '<div style="display:flex;justify-content:space-between;align-items:center;'
                'padding:4px 0;border-bottom:1px solid #152a4a;">'
                f'<span style="color:#e8eef8;font-size:16px;">👤 {row["origem"]}</span>'
                f'<span style="color:#4f8ef7;font-weight:700;font-size:14px;">{row["qtd"]}</span>'
                '</div>'
            )
        if not linhas_op:
            linhas_op = '<span style="color:#7a9cc7;font-size:13px;">Nenhum lead hoje</span>'

        st.markdown(
            '<div class="card-total" style="display:flex;gap:24px;align-items:flex-start;">'
            '<div style="min-width:120px;">'
            '<span class="card-icone">🌅</span>'
            f'<div class="card-valor" style="color:#4f8ef7;">{leads_hoje}</div>'
            '<div class="card-label">Leads Captados Hoje</div>'
            f'<div style="margin-top:10px;font-size:13px;font-weight:600;color:{cor_seta};">{seta}</div>'
            f'<div style="font-size:11px;color:#7a9cc7;margin-top:2px;">Ontem: {leads_ontem} leads</div>'
            '</div>'
            '<div style="width:1px;background:#152a4a;align-self:stretch;margin:4px 0;"></div>'
            '<div style="flex:1;min-width:0;">'
            '<div style="color:#7a9cc7;font-size:14px;font-weight:600;text-transform:uppercase;'
            'letter-spacing:.6px;margin-bottom:8px;">Por Operador</div>'
            + linhas_op +
            '</div></div>',
            unsafe_allow_html=True
        )

    with h2:
        st.markdown(f"""
        <div class="card-status" style="border-left:4px solid {cor_meta};">
            <span class="card-icone">🎯</span>
            <div class="card-valor" style="color:{cor_meta};">{leads_hoje} / {META_DIARIA}</div>
            <div class="card-label">Meta Diária de Leads</div>
            <div style="background:#152a4a;border-radius:99px;height:8px;margin-top:10px;overflow:hidden;">
                <div style="background:{cor_meta};width:{pct_meta}%;height:100%;border-radius:99px;"></div>
            </div>
            <div style="color:{cor_meta};font-size:11px;margin-top:4px;">{pct_meta}% da meta</div>
        </div>
        """, unsafe_allow_html=True)


@st.fragment
def render_leads_rt():
    df_todos_rt, _ = merge_leads_curto()
    df_rt = _df_com_filtros_globais(df_todos_rt) if not df_todos_rt.empty else df_todos_rt

    st.markdown("#### 📋 Leads Recentes")
    st.markdown(
        "<p style='color:#7a9cc7;font-size:13px;margin-top:-4px;'>"
        f"Exibindo os 100 leads mais recentes do período filtrado ({len(df_rt)} no total)."
        "</p>",
        unsafe_allow_html=True
    )

    df_sorted_orig = df_rt.copy()
    df_sorted_orig["_sort"] = pd.to_datetime(
        df_sorted_orig["atualizado_em"], format="%d/%m/%Y %H:%M", errors="coerce"
    )
    df_sorted_orig = (
        df_sorted_orig.sort_values("_sort", ascending=False)
        .drop(columns=["_sort"])
        .reset_index(drop=True)
        .head(100)
    )
    if "em_atraso" in df_sorted_orig.columns:
        df_sorted_orig["Atraso"] = df_sorted_orig["em_atraso"].apply(lambda x: "🔴 Em atraso" if x else "")
    else:
        df_sorted_orig["Atraso"] = ""

    col_labels = {
        "Atraso":         "Situação",
        "nome":           "Nome",
        "status":         "Status",
        "perception":     "Temperatura",
        "valor_proposta": "Valor (R$)",
        "atendente":      "Atendente",
        "origem":         "Operador",
        "interesse":      "Interesse",
        "criado_em":      "Cadastrado em",
        "atualizado_em":  "Última Atualização",
    }
    df_display = df_sorted_orig.copy()
    df_display["valor_proposta"] = df_display["valor_proposta"].apply(
        lambda v: fmt_brl(v) if v > 0 else "—"
    )
    df_display = df_display[list(col_labels.keys())].rename(columns=col_labels)

    st.caption("💡 Clique em uma linha para ver os detalhes completos do lead.")
    evt = st.dataframe(
        df_display,
        use_container_width=True,
        hide_index=True,
        height=500,
        selection_mode="single-row",
        on_select="rerun",
        key="tabela_leads_rt",
    )
    sel = evt.selection.rows
    if sel and st.session_state.get("modal_leads_rt") != sel[0]:
        st.session_state["modal_leads_rt"] = sel[0]
        modal_lead(df_sorted_orig.iloc[sel[0]])
    if not sel:
        st.session_state.pop("modal_leads_rt", None)


# ═══════════════════════════════════════════════════════════════════════════════
# ── MAIN ──────────────────────────────────────────────────────────────────────
# ═══════════════════════════════════════════════════════════════════════════════
inject_css()

# ── Cabeçalho ─────────────────────────────────────────────────────────────────
col_titulo, col_hora, col_btn = st.columns([4, 2, 1])
with col_titulo:
    st.title("📺 Dashboard · O2 Solution")
with col_hora:
    st.markdown(
        f"<div class='update-time' style='margin-top:16px'>🕐 Atualizado: "
        f"{datetime.now().strftime('%d/%m/%Y %H:%M')}</div>",
        unsafe_allow_html=True
    )
with col_btn:
    if st.button("🔄 Atualizar", key="refresh"):
        fetch_leads_30dias.clear()
        fetch_leads_80dias.clear()
        fetch_leads_criticos.clear()
        st.session_state.pop("df_funil", None)
        st.rerun()

st.markdown("---")

# ── Loading ────────────────────────────────────────────────────────────────────
loading_ph = st.empty()
loading_ph.markdown(
    '<div class="loading-box">⏳ Carregando leads, aguarde...</div>',
    unsafe_allow_html=True
)
df_todos, erro = merge_leads_curto()
loading_ph.empty()

if erro:
    st.error(erro)
    st.stop()

if df_todos.empty:
    st.warning("Nenhum lead encontrado. Verifique o token de acesso.")
    st.stop()

# ── ABAS ──────────────────────────────────────────────────────────────────────
aba_visao, aba_funil, aba_operadores, aba_detalhamento, aba_leads = st.tabs([
    "📊 Visão Geral",
    "🔥 Funil de Vendas",
    "👤 Por Operador",
    "📆 Detalhamento por Dia",
    "📋 Leads Recentes",
])


@st.fragment
def render_visao_geral(df_todos: pd.DataFrame):
    st.markdown("#### 🔎 Filtros da Aba")
    origens_disp = sorted(df_todos["origem"].dropna().unique().tolist())
    with st.form("filtros_visao", border=False):
        col_op, col_st, col_de, col_ate, col_btn_f = st.columns([3, 2, 1.5, 1.5, 1])
        with col_op:
            selecionados = st.multiselect(
                "👤 Origem", options=origens_disp, default=origens_disp, key="visao_origem"
            )
        with col_st:
            filtro_status = st.selectbox(
                "📌 Status", ["Todos"] + list(STATUS_MAP.values()), key="visao_status"
            )
        with col_de:
            data_de = st.date_input(
                "📅 De", value=date.today() - timedelta(days=30),
                format="DD/MM/YYYY", key="visao_de"
            )
        with col_ate:
            data_ate = st.date_input(
                "📅 Até", value=date.today(), format="DD/MM/YYYY", key="visao_ate"
            )
        with col_btn_f:
            st.markdown("<div style='margin-top:24px'>", unsafe_allow_html=True)
            st.form_submit_button("✔ Aplicar", use_container_width=True)
            st.markdown("</div>", unsafe_allow_html=True)

    df = df_todos.copy()
    df = df[df["data_obj"].apply(lambda d: d is not None and data_de <= d <= data_ate)]
    if selecionados:
        df = df[df["origem"].isin(selecionados)]
    if filtro_status != "Todos":
        df = df[df["status"] == filtro_status]

    st.markdown("---")

    total      = len(df)
    vendas     = int((df["status"] == "Venda Realizada").sum())
    aguardando = int((df["status"] == "Aguardando Pagamento").sum())
    proposta   = int((df["status"] == "Proposta Enviada").sum())
    nao_venda  = int((df["status"] == "Venda não Realizada").sum())
    agendado   = int((df["status"] == "Agendado").sum())
    primeiro   = int((df["status"] == "Primeiro Contato").sum())
    taxa_conv  = f"{(vendas / total * 100):.1f}%" if total > 0 else "0%"

    render_hoje_rt()

    st.markdown("---")
    st.markdown("#### 📊 Visão Geral do Período")

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        linhas_total = linhas_por_operador(df, None, "#4f8ef7")
        st.markdown(f"""
        <div class="card-total" style="display:flex;gap:16px;align-items:flex-start;">
            <div style="min-width:90px;">
                <span class="card-icone">📋</span>
                <div class="card-valor" style="color:#4f8ef7;">{total}</div>
                <div class="card-label">Total de Leads</div>
            </div>
            <div style="width:1px;background:#152a4a;align-self:stretch;margin:4px 0;"></div>
            <div style="flex:1;min-width:0;padding-top:4px;">
                <div style="color:#7a9cc7;font-size:11px;font-weight:600;text-transform:uppercase;
                            letter-spacing:.6px;margin-bottom:6px;">Por Operador</div>
                {linhas_total}
            </div>
        </div>
        """, unsafe_allow_html=True)
    with c2:
        linhas_taxa = linhas_por_operador(df, "Venda Realizada", "#22c55e")
        st.markdown(f"""
        <div class="card-taxa" style="display:flex;gap:16px;align-items:flex-start;">
            <div style="min-width:90px;">
                <span class="card-icone">📈</span>
                <div class="card-valor" style="color:#22c55e;">{taxa_conv}</div>
                <div class="card-label">Taxa de Conversão</div>
            </div>
            <div style="width:1px;background:#152a4a;align-self:stretch;margin:4px 0;"></div>
            <div style="flex:1;min-width:0;padding-top:4px;">
                <div style="color:#7a9cc7;font-size:11px;font-weight:600;text-transform:uppercase;
                            letter-spacing:.6px;margin-bottom:6px;">Vendas / Op.</div>
                {linhas_taxa}
            </div>
        </div>
        """, unsafe_allow_html=True)
    with c3:
        render_card("✅", vendas, "Venda Realizada", "#22c55e", df=df, status_filtro="Venda Realizada")
    with c4:
        render_card("💳", aguardando, "Aguardando Pagamento", "#f97316", df=df, status_filtro="Aguardando Pagamento")

    c5, c6, c7, c8 = st.columns(4)
    with c5:
        render_card("📄", proposta, "Proposta Enviada", "#8b5cf6", df=df, status_filtro="Proposta Enviada")
    with c6:
        render_card("📅", agendado, "Agendado", "#f59e0b", df=df, status_filtro="Agendado")
    with c7:
        render_card("👋", primeiro, "Primeiro Contato", "#4f8ef7", df=df, status_filtro="Primeiro Contato")
    with c8:
        render_card("❌", nao_venda, "Venda não Realizada", "#ef4444", df=df, status_filtro="Venda não Realizada")

    st.markdown("---")
    col_g1, col_g2 = st.columns(2)
    with col_g1:
        st.markdown("#### 🍩 Distribuição por Status")
        st.plotly_chart(grafico_rosca(df), use_container_width=True, key="rosca_visao")
    with col_g2:
        st.markdown("#### 🏆 Ranking por Operador (Vendas)")
        st.plotly_chart(grafico_origens(df), use_container_width=True, key="origens_visao")


@st.fragment
def render_operadores(df_todos: pd.DataFrame):
    st.markdown("#### 🔎 Filtros da Aba")
    origens_op_disp = sorted(df_todos["origem"].dropna().unique().tolist())
    op1, op2, _ = st.columns([3, 2, 3])
    with op1:
        op_selecionados = st.multiselect(
            "👤 Origem", options=origens_op_disp, default=origens_op_disp, key="op_origem"
        )
    with op2:
        op_status = st.selectbox(
            "📌 Status", ["Todos"] + list(STATUS_MAP.values()), key="op_status"
        )

    st.markdown("---")
    st.markdown("#### 📈 Acumulado de Leads por Operador no Mês")

    if op_selecionados:
        df_acum = df_todos.copy()
        df_acum = df_acum[df_acum["origem"].isin(op_selecionados)]
        if op_status != "Todos":
            df_acum = df_acum[df_acum["status"] == op_status]
        st.plotly_chart(grafico_acumulado(df_acum, op_selecionados), use_container_width=True, key="acumulado_op")
    else:
        st.info("Selecione ao menos um operador para ver o acumulado.")

    st.markdown("---")
    st.markdown("#### 🏆 Ranking de Vendas por Operador")
    df_op_rank = df_todos.copy()
    if op_selecionados:
        df_op_rank = df_op_rank[df_op_rank["origem"].isin(op_selecionados)]
    if op_status != "Todos":
        df_op_rank = df_op_rank[df_op_rank["status"] == op_status]
    st.plotly_chart(grafico_origens(df_op_rank), use_container_width=True, key="origens_op")


@st.fragment
def render_detalhamento(df_todos: pd.DataFrame):
    st.markdown("#### 📆 Detalhamento de Leads por Dia e Operador")
    st.markdown(
        "<p style='color:#7a9cc7;font-size:13px;margin-top:-4px;'>"
        "Análise detalhada dia a dia — filtre o período abaixo de forma independente das outras abas."
        "</p>",
        unsafe_allow_html=True
    )

    st.markdown("---")
    st.markdown("#### 🔎 Filtros da Aba")
    fd1, fd2, fd3 = st.columns([1.5, 1.5, 3])
    with fd1:
        det_de = st.date_input(
            "📅 De", value=date.today().replace(day=1),
            format="DD/MM/YYYY", key="det_de"
        )
    with fd2:
        det_ate = st.date_input(
            "📅 Até", value=date.today(),
            format="DD/MM/YYYY", key="det_ate"
        )
    with fd3:
        ops_disp_det = sorted(df_todos["origem"].dropna().unique().tolist())
        det_ops = st.multiselect(
            "👤 Origem", options=ops_disp_det, default=ops_disp_det, key="det_ops"
        )

    st.markdown("---")

    df_det = df_todos.copy()
    df_det = df_det[df_det["data_obj"].notna()]
    df_det = df_det[df_det["data_obj"].apply(lambda d: det_de <= d <= det_ate)]
    if det_ops:
        df_det = df_det[df_det["origem"].isin(det_ops)]

    if df_det.empty or not det_ops:
        st.info("Nenhum dado encontrado para o período e operadores selecionados.")
        return

    operadores_det = sorted(df_det["origem"].dropna().unique().tolist())
    CORES_DET = ["#4f8ef7", "#22c55e", "#f59e0b", "#8b5cf6", "#ef4444", "#f97316"]
    cor_por_op = {op: CORES_DET[i % len(CORES_DET)] for i, op in enumerate(operadores_det)}

    pivot = (
        df_det.groupby(["data_obj", "origem"])
        .size()
        .reset_index(name="leads")
        .pivot(index="data_obj", columns="origem", values="leads")
        .fillna(0)
        .astype(int)
        .sort_index()
    )
    pivot["Total"] = pivot[operadores_det].sum(axis=1)

    st.markdown("#### 👤 Resumo do Período por Operador")

    chunks = [operadores_det[i:i+4] for i in range(0, len(operadores_det), 4)]
    for chunk in chunks:
        cols_cards = st.columns(len(chunk))
        for col_c, op in zip(cols_cards, chunk):
            cor_op = cor_por_op[op]
            total_op = int(pivot[op].sum())
            dias_uteis = len(pivot)
            media_op = round(total_op / dias_uteis, 1) if dias_uteis > 0 else 0

            df_op_det = df_det[df_det["origem"] == op]
            valor_op  = df_op_det["valor_proposta"].sum()
            leads_com_valor = int((df_op_det["valor_proposta"] > 0).sum())
            ticket_op = valor_op / leads_com_valor if leads_com_valor > 0 else 0

            vals = pivot[op].tolist()
            metade = len(vals) // 2
            if metade > 0:
                media_ini = sum(vals[:metade]) / metade
                media_fim = sum(vals[metade:]) / max(len(vals[metade:]), 1)
                if media_fim > media_ini:
                    tendencia, cor_tend = "↑ Subindo", "#22c55e"
                elif media_fim < media_ini:
                    tendencia, cor_tend = "↓ Caindo", "#ef4444"
                else:
                    tendencia, cor_tend = "→ Estável", "#7a9cc7"
            else:
                tendencia, cor_tend = "→ Estável", "#7a9cc7"

            with col_c:
                st.markdown(f"""
                <div class="card-status" style="border-left:4px solid {cor_op};display:flex;gap:16px;align-items:flex-start;">
                    <div style="min-width:110px;">
                        <span class="card-icone">👤</span>
                        <div class="card-valor" style="color:{cor_op};">{total_op}</div>
                        <div class="card-label">{op}</div>
                        <div style="margin-top:10px;font-size:14px;color:#7a9cc7;">
                            Média: <b style="color:{cor_op};">{media_op}/dia</b>
                        </div>
                        <div style="margin-top:6px;font-size:15px;font-weight:700;color:{cor_tend};">
                            {tendencia}
                        </div>
                    </div>
                    <div style="width:1px;background:#152a4a;align-self:stretch;margin:4px 0;flex-shrink:0;"></div>
                    <div style="flex:1;min-width:0;padding-top:4px;">
                        <div style="color:#7a9cc7;font-size:13px;font-weight:600;text-transform:uppercase;
                                    letter-spacing:.6px;margin-bottom:6px;">Carteira (R$)</div>
                        <div style="font-size:26px;font-weight:700;color:#22c55e;line-height:1.1;">
                            {fmt_brl(valor_op)}
                        </div>
                        <div style="font-size:13px;color:#7a9cc7;margin-top:4px;">em propostas enviadas</div>
                        <div style="margin-top:10px;color:#7a9cc7;font-size:13px;font-weight:600;
                                    text-transform:uppercase;letter-spacing:.6px;margin-bottom:4px;">Ticket Médio</div>
                        <div style="font-size:22px;font-weight:700;color:#4f8ef7;">
                            {fmt_brl(ticket_op)}
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("#### 📊 Leads por Dia (todos os operadores)")

    fig_barras = go.Figure()
    for op in operadores_det:
        cor_op = cor_por_op[op]
        datas_fmt = [d.strftime("%d/%m") for d in pivot.index]
        fig_barras.add_trace(go.Bar(
            name=op,
            x=datas_fmt,
            y=pivot[op].tolist(),
            marker_color=cor_op,
            hovertemplate=f"<b>{op}</b><br>%{{x}}<br>%{{y}} leads<extra></extra>",
        ))

    fig_barras.update_layout(
        barmode="group",
        margin=dict(t=20, b=20, l=10, r=20),
        height=340,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        legend=dict(orientation="h", y=1.12, x=0, font=dict(color="#e8eef8", size=13)),
        xaxis=dict(showgrid=False, color="#7a9cc7", tickfont=dict(color="#e8eef8", size=11)),
        yaxis=dict(showgrid=True, gridcolor="#152a4a", color="#7a9cc7",
                   tickfont=dict(color="#e8eef8", size=12), zeroline=False),
        hovermode="x unified",
    )
    st.plotly_chart(fig_barras, use_container_width=True, key="det_barras")

    st.markdown("---")
    st.markdown("#### 📋 Tabela de Leads por Data e Operador")

    tabela_display = pivot.copy()
    tabela_display.index = [d.strftime("%d/%m/%Y (%a)").replace(
        "Mon", "Seg").replace("Tue", "Ter").replace("Wed", "Qua")
        .replace("Thu", "Qui").replace("Fri", "Sex")
        .replace("Sat", "Sáb").replace("Sun", "Dom")
        for d in tabela_display.index
    ]
    tabela_display.index.name = "Data"
    tabela_display = tabela_display.reset_index()

    linha_total = {"Data": "📊 TOTAL"}
    for op in operadores_det:
        linha_total[op] = int(pivot[op].sum())
    linha_total["Total"] = int(pivot["Total"].sum())
    tabela_display = pd.concat(
        [tabela_display, pd.DataFrame([linha_total])], ignore_index=True
    )
    st.dataframe(tabela_display, use_container_width=True, hide_index=True, height=420)

    st.markdown("---")
    st.markdown("#### 📈 Evolução Diária por Operador (Δ vs dia anterior)")
    st.markdown(
        "<p style='color:#7a9cc7;font-size:12px;margin-top:-8px;'>"
        "↑ verde = captou mais que o dia anterior · ↓ vermelho = captou menos · = cinza = igual"
        "</p>",
        unsafe_allow_html=True
    )

    datas_sorted = sorted(pivot.index.tolist())
    if len(datas_sorted) >= 2:
        evolucao_html = (
            '<div style="overflow-x:auto;">'
            '<table style="width:100%;border-collapse:collapse;font-size:13px;">'
            '<thead><tr>'
            '<th style="text-align:left;padding:8px 12px;color:#7a9cc7;'
            'border-bottom:1px solid #152a4a;white-space:nowrap;">Operador</th>'
        )
        for d in datas_sorted:
            evolucao_html += (
                f'<th style="text-align:center;padding:8px 10px;color:#7a9cc7;'
                f'border-bottom:1px solid #152a4a;white-space:nowrap;">'
                f'{d.strftime("%d/%m")}</th>'
            )
        evolucao_html += '</tr></thead><tbody>'

        for op in operadores_det:
            cor_op = cor_por_op[op]
            evolucao_html += (
                f'<tr>'
                f'<td style="padding:8px 12px;font-weight:600;color:{cor_op};'
                f'border-bottom:1px solid #152a4a;white-space:nowrap;">👤 {op}</td>'
            )
            for idx, d in enumerate(datas_sorted):
                val_hoje = int(pivot.loc[d, op]) if d in pivot.index else 0
                if idx == 0:
                    evolucao_html += (
                        f'<td style="text-align:center;padding:8px 10px;'
                        f'border-bottom:1px solid #152a4a;">'
                        f'<span style="color:#e8eef8;font-weight:700;">{val_hoje}</span>'
                        f'</td>'
                    )
                else:
                    d_ant = datas_sorted[idx - 1]
                    val_ant = int(pivot.loc[d_ant, op]) if d_ant in pivot.index else 0
                    diff = val_hoje - val_ant
                    if diff > 0:
                        cor_cell, seta_cell = "#22c55e", f"↑ +{diff}"
                    elif diff < 0:
                        cor_cell, seta_cell = "#ef4444", f"↓ {diff}"
                    else:
                        cor_cell, seta_cell = "#7a9cc7", "="
                    evolucao_html += (
                        f'<td style="text-align:center;padding:8px 10px;'
                        f'border-bottom:1px solid #152a4a;">'
                        f'<span style="color:#e8eef8;font-weight:700;">{val_hoje}</span>'
                        f'<br><span style="color:{cor_cell};font-size:11px;">{seta_cell}</span>'
                        f'</td>'
                    )
            evolucao_html += '</tr>'

        evolucao_html += '</tbody></table></div>'
        st.markdown(evolucao_html, unsafe_allow_html=True)
    else:
        st.info("Selecione ao menos 2 dias para ver a evolução diária.")


# ══════════════════════════════════════════════════════════════════════════════
# ABAS
# ══════════════════════════════════════════════════════════════════════════════
with aba_visao:
    render_visao_geral(df_todos)

with aba_funil:
    render_funil_rt()

with aba_operadores:
    render_operadores(df_todos)

with aba_detalhamento:
    render_detalhamento(df_todos)

# ══════════════════════════════════════════════════════════════════════════════
# ABA 5 — LEADS RECENTES (tempo real via fragment)
# ══════════════════════════════════════════════════════════════════════════════
with aba_leads:

    render_leads_rt()


# ── RODAPÉ ────────────────────────────────────────────────────────────────────
st.markdown("---")
st.markdown(
    "<div style='text-align:center;color:#7a9cc7;font-size:12px;'>"
    "Hoje · atualização manual via botão · demais seções via botão Atualizar · O2 Solution"
    "</div>",
    unsafe_allow_html=True
)

