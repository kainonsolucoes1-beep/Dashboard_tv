import streamlit as st
import requests
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, date, timedelta
from config import ACCESS_TOKEN

# ── CONFIG ────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Dashboard · O2 Saúde",
    page_icon="📺",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── MAPEAMENTO DE STATUS ───────────────────────────────────────────────────────
STATUS_MAP = {
    "pending":            "Primeiro Contato",
    "scheduled":          "Agendado",
    "proposal_sent":      "Proposta Enviada",
    "waiting_billing":    "Aguardando Pagamento",
    "sale_performed":     "Venda Realizada",
    "sale_not_performed": "Venda não Realizada",
}

CORES_STATUS = {
    "Primeiro Contato":    "#4f8ef7",
    "Agendado":            "#f59e0b",
    "Proposta Enviada":    "#8b5cf6",
    "Aguardando Pagamento":"#f97316",
    "Venda Realizada":     "#22c55e",
    "Venda não Realizada": "#ef4444",
}

ICONES_STATUS = {
    "Primeiro Contato":    "👋",
    "Agendado":            "📅",
    "Proposta Enviada":    "📄",
    "Aguardando Pagamento":"💳",
    "Venda Realizada":     "✅",
    "Venda não Realizada": "❌",

}
# ── RENOMEAÇÃO DOS OPERADORES ───────────────────────────────────────────────────────────────────────

NOMES_OPERADORES = {

    "Livia": "o2 Solution",
    
    }

# ── CSS ───────────────────────────────────────────────────────────────────────
def inject_css():
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@300;400;500;600;700&display=swap');

    :root {
        --bg-main:   #0f1117;
        --bg-card:   #1a1d27;
        --bg-input:  #23273a;
        --border:    #2e3347;
        --text-main: #e8eaf0;
        --text-sub:  #8b90a7;
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

    /* Cards de status customizados */
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
    .card-icone {
        font-size: 28px;
        margin-bottom: 8px;
        display: block;
    }
    .card-valor {
        font-size: 38px;
        font-weight: 700;
        line-height: 1;
        margin-bottom: 6px;
    }
    .card-label {
        font-size: 12px;
        font-weight: 500;
        text-transform: uppercase;
        letter-spacing: .6px;
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

    /* Flags de operador */
    .flag-container {
        background: var(--bg-card);
        border: 1px solid var(--border);
        border-radius: 12px;
        padding: 16px 20px;
        margin-bottom: 12px;
    }
    .flag-label {
        font-size: 12px;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: .6px;
        color: var(--text-sub);
        margin-bottom: 10px;
    }

    /* Checkbox customizado */
    [data-testid="stCheckbox"] {
        background: var(--bg-input);
        border: 1px solid var(--border);
        border-radius: 8px;
        padding: 6px 12px;
        margin: 2px;
    }
    [data-testid="stCheckbox"]:hover {
        border-color: var(--accent) !important;
    }
    [data-testid="stCheckbox"] label {
        color: var(--text-main) !important;
        font-size: 14px !important;
        font-weight: 500 !important;
    }

    /* Selectbox */
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

    hr { border-color: var(--border) !important; }

    .update-time {
        color: var(--text-sub);
        font-size: 12px;
        text-align: right;
    }

    /* Barra superior do Streamlit (deploy, menu) */
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

    /* Calendário do date input */
    [data-baseweb="calendar"] {
        background: var(--bg-card) !important;
        border: 1px solid var(--border) !important;
    }
    [data-baseweb="calendar"] * { color: var(--text-main) !important; }

    /* Tabela — cabeçalho e células */
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

    /* Multiselect tags */
    [data-baseweb="tag"] {
        background: var(--bg-input) !important;
        border: 1px solid var(--border) !important;
    }
    [data-baseweb="tag"] span { color: var(--text-main) !important; }
    </style>
    """, unsafe_allow_html=True)

# ── BUSCA DE DADOS ─────────────────────────────────────────────────────────────
@st.cache_data(ttl=60)
def fetch_leads():
    headers = {
        "Authorization": f"Bearer {ACCESS_TOKEN}",
        "Accept": "application/json"
    }

    todos_leads = []
    pagina = 1
    date_from = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")

    while True:
        params = {
            "date_from": date_from,
            "per_page": 200,
            "page": pagina
        }
        try:
            response = requests.get(
                "https://api.followize.com.br/v3/leads",
                headers=headers,
                params=params,
                timeout=30
            )
            if response.status_code != 200:
                return pd.DataFrame(), f"Erro na API: {response.status_code}"

            data = response.json()
            leads = data.get("data", [])
            if not leads:
                break

            todos_leads.extend(leads)

            meta = data.get("meta", {})
            if pagina >= meta.get("last_page", 1):
                break
            pagina += 1

        except Exception as e:
            return pd.DataFrame(), f"Erro ao buscar leads: {e}"

    registros = []
    for lead in todos_leads:
        atendente  = (lead.get("attendant") or {}).get("name", "Sem atendente")
        status_raw = lead.get("status", "")
        status_pt  = STATUS_MAP.get(status_raw, status_raw)
        origem     = (lead.get("tracking") or {}).get("source", "") or "Sem origem"
        origem     = NOMES_OPERADORES.get(origem, origem)
        equipe     = ((lead.get("contact") or {}).get("team") or {}).get("name", "")
        interesse  = ((lead.get("interests") or {}).get("interest_1") or {}).get("name", "")
        criado_em  = lead.get("created_at", "")

        data_obj = None
        if criado_em:
            try:
                dt       = datetime.fromisoformat(criado_em.replace("Z", "+00:00"))
                data_obj = dt.date()
                criado_em = dt.strftime("%d/%m/%Y %H:%M")
            except:
                pass

        registros.append({
            "nome":      lead.get("name", ""),
            "status":    status_pt,
            "atendente": atendente,
            "origem":    origem,
            "equipe":    equipe,
            "interesse": interesse,
            "criado_em": criado_em,
            "data_obj":  data_obj,
        })

    return pd.DataFrame(registros), None

# ── HELPER: Gera linhas de operadores para um status específico ───────────────
def linhas_por_operador(df, status_filtro, cor):
    if status_filtro:
        df_filtrado = df[df["status"] == status_filtro]
    else:
        df_filtrado = df

    ranking = (
        df_filtrado.groupby("origem")
        .size()
        .reset_index(name="qtd")
        .sort_values("qtd", ascending=False)
    )

    if ranking.empty:
        return '<span style="color:#8b90a7;font-size:12px;">Sem registros</span>'

    html = ""
    for _, row in ranking.iterrows():
        html += (
            '<div style="display:flex;justify-content:space-between;align-items:center;'
            'gap:8px;padding:3px 0;border-bottom:1px solid #2e3347;">'
            f'<span style="color:#e8eaf0;font-size:12px;overflow:hidden;'
            f'text-overflow:ellipsis;white-space:nowrap;min-width:0;flex:1;">👤 {row["origem"]}</span>'
            f'<span style="color:{cor};font-weight:700;font-size:13px;'
            f'white-space:nowrap;flex-shrink:0;">{row["qtd"]}</span>'
            '</div>'
        )
    return html

# ── CARD DE MÉTRICA CUSTOMIZADO ───────────────────────────────────────────────
def render_card(icone, valor, label, cor, df=None, status_filtro=None):
    if df is not None:
        linhas = linhas_por_operador(df, status_filtro, cor)
        st.markdown(f"""
        <div class="card-status" style="border-left: 4px solid {cor}; display:flex; gap:16px; align-items:flex-start; overflow:hidden;">
            <div style="min-width:90px;flex-shrink:0;">
                <span class="card-icone">{icone}</span>
                <div class="card-valor" style="color: {cor};">{valor}</div>
                <div class="card-label" style="white-space:nowrap;">{label}</div>
            </div>
            <div style="width:1px;background:#2e3347;align-self:stretch;margin:4px 0;flex-shrink:0;"></div>
            <div style="flex:1;overflow:hidden;padding-top:4px;">
                <div style="color:#8b90a7;font-size:11px;font-weight:600;text-transform:uppercase;
                            letter-spacing:.6px;margin-bottom:6px;white-space:nowrap;">Por Operador</div>
                {linhas}
            </div>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown(f"""
        <div class="card-status" style="border-left: 4px solid {cor};">
            <span class="card-icone">{icone}</span>
            <div class="card-valor" style="color: {cor};">{valor}</div>
            <div class="card-label">{label}</div>
        </div>
        """, unsafe_allow_html=True)

# ── GRÁFICO DE ROSCA ──────────────────────────────────────────────────────────
def grafico_rosca(df):
    counts = df["status"].value_counts()
    labels = counts.index.tolist()
    values = counts.values.tolist()
    colors = [CORES_STATUS.get(l, "#aaa") for l in labels]

    fig = go.Figure(go.Pie(
        labels=labels,
        values=values,
        hole=0.55,
        marker=dict(colors=colors, line=dict(color="#1a1d27", width=2)),
        textinfo="label+percent",
        textfont=dict(size=12, color="#e8eaf0"),
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

# ── GRÁFICO DE BARRAS POR ORIGEM ──────────────────────────────────────────────
def grafico_origens(df):
    vendas  = df[df["status"] == "Venda Realizada"]
    ranking = vendas["origem"].value_counts().head(10)

    fig = go.Figure(go.Bar(
        x=ranking.values.tolist(),
        y=ranking.index.tolist(),
        orientation="h",
        marker=dict(
            color=ranking.values.tolist(),
            colorscale=[[0, "#1a1d27"], [1, "#22c55e"]],
            line=dict(color="#2e3347", width=1)
        ),
        text=ranking.values.tolist(),
        textposition="outside",
        textfont=dict(color="#e8eaf0", size=12),
        hovertemplate="<b>%{y}</b><br>%{x} vendas<extra></extra>",
    ))
    fig.update_layout(
        margin=dict(t=10, b=10, l=10, r=40),
        height=280,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(showgrid=True, gridcolor="#2e3347", color="#8b90a7", zeroline=False),
        yaxis=dict(color="#e8eaf0", autorange="reversed"),
    )
    return fig

# ── GRÁFICO DE LINHAS ACUMULADO POR OPERADOR ─────────────────────────────────
def grafico_acumulado(df, operadores):
    CORES_OPERADORES = [
        "#4f8ef7", "#22c55e", "#f59e0b",
        "#8b5cf6", "#ef4444", "#f97316",
    ]

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

        cor = CORES_OPERADORES[i % len(CORES_OPERADORES)]

        fig.add_trace(go.Scatter(
            x=por_dia["data_fmt"].tolist(),
            y=por_dia["acumulado"].tolist(),
            name=operador,
            mode="lines+markers",
            line=dict(color=cor, width=3),
            marker=dict(color=cor, size=8, symbol="circle"),
            hovertemplate=f"<b>{operador}</b><br>%{{x}}<br>%{{y}} leads acumulados<extra></extra>",
        ))

    fig.update_layout(
        margin=dict(t=20, b=20, l=10, r=20),
        height=320,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        legend=dict(
            orientation="h",
            y=1.1,
            x=0,
            font=dict(color="#e8eaf0", size=13),
        ),
        xaxis=dict(
            showgrid=True,
            gridcolor="#2e3347",
            color="#8b90a7",
            tickfont=dict(color="#e8eaf0", size=12),
        ),
        yaxis=dict(
            showgrid=True,
            gridcolor="#2e3347",
            color="#8b90a7",
            tickfont=dict(color="#e8eaf0", size=12),
            zeroline=False,
        ),
        hovermode="x unified",
    )
    return fig

# ── MAIN ──────────────────────────────────────────────────────────────────────
inject_css()
# As proporções [4, 2, 1] significam: título | hora | botão
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
        fetch_leads.clear()
        st.rerun()

st.markdown("---")

# ── LOADING ELEGANTE ──────────────────────────────────────────────────────────
loading_placeholder = st.empty()
loading_placeholder.markdown("""
<div class="loading-box">
    ⏳ Carregando leads, aguarde...
</div>
""", unsafe_allow_html=True)

df_todos, erro = fetch_leads()

loading_placeholder.empty()

if erro:
    st.error(erro)
    st.stop()

if df_todos.empty:
    st.warning("Nenhum lead encontrado. Verifique o token de acesso.")
    st.stop()

# ── FILTROS ───────────────────────────────────────────────────────────────────
col_op, col_st, col_de, col_ate = st.columns([3, 2, 1.5, 1.5])

with col_op:
    origens_disponiveis = sorted(df_todos["origem"].dropna().unique().tolist())
    selecionados = st.multiselect(
        "👤 Operadores",
        options=origens_disponiveis,
        default=origens_disponiveis,
        key="filtro_origem"
    )

with col_st:
    filtro_status = st.selectbox(
        "📌 Status",
        ["Todos"] + list(STATUS_MAP.values()),
        key="filtro_status"
    )

with col_de:
    data_de = st.date_input(
        "📅 De",
        value=date.today() - timedelta(days=30),
        format="DD/MM/YYYY",
        key="filtro_de"
    )

with col_ate:
    data_ate = st.date_input(
        "📅 Até",
        value=date.today(),
        format="DD/MM/YYYY",
        key="filtro_ate"
    )

# Aplica filtros encadeados
df = df_todos.copy()
df = df[df["data_obj"].apply(lambda d: d is not None and data_de <= d <= data_ate)]
if selecionados:
    df = df[df["origem"].isin(selecionados)]
if filtro_status != "Todos":
    df = df[df["status"] == filtro_status]

st.markdown("---")

# ── CARDS DE MÉTRICAS ─────────────────────────────────────────────────────────
total      = len(df)
vendas     = int((df["status"] == "Venda Realizada").sum())
aguardando = int((df["status"] == "Aguardando Pagamento").sum())
proposta   = int((df["status"] == "Proposta Enviada").sum())
nao_venda  = int((df["status"] == "Venda não Realizada").sum())
agendado   = int((df["status"] == "Agendado").sum())
primeiro   = int((df["status"] == "Primeiro Contato").sum())
taxa_conv  = f"{(vendas / total * 100):.1f}%" if total > 0 else "0%"

# ── Comparativo com ontem ─────────────────────────────────────────────────────
hoje   = date.today()
ontem  = hoje - timedelta(days=1)

df_hoje = df_todos.copy()
if selecionados:
    df_hoje = df_hoje[df_hoje["origem"].isin(selecionados)]

df_ontem = df_hoje[df_hoje["data_obj"].apply(lambda d: d == ontem)]
df_hoje  = df_hoje[df_hoje["data_obj"].apply(lambda d: d == hoje)]

leads_hoje  = len(df_hoje)
leads_ontem = len(df_ontem)

diferenca = leads_hoje - leads_ontem
if diferenca > 0:
    seta      = f"↑ +{diferenca} que ontem"
    cor_seta  = "#22c55e"
elif diferenca < 0:
    seta      = f"↓ {diferenca} que ontem"
    cor_seta  = "#ef4444"
else:
    seta      = "= igual a ontem"
    cor_seta  = "#8b90a7"

operadores_hoje = (
    df_hoje.groupby("origem")
    .size()
    .reset_index(name="qtd")
    .sort_values("qtd", ascending=False)
)

META_DIARIA = 10
progresso = min(leads_hoje / META_DIARIA, 1.0)
pct_meta  = int(progresso * 100)
cor_meta  = "#22c55e" if progresso >= 1.0 else "#f59e0b" if progresso >= 0.5 else "#ef4444"

# ── Seção: Hoje ───────────────────────────────────────────────────────────────
st.markdown("#### 📅 Hoje")
h1, h2 = st.columns(2)

with h1:
    linhas_operadores = ""
    for _, row in operadores_hoje.iterrows():
        nome = row["origem"]
        qtd  = row["qtd"]
        linhas_operadores += (
            '<div style="display:flex;justify-content:space-between;align-items:center;'
            'gap:8px;padding:4px 0;border-bottom:1px solid #2e3347;">'
            f'<span style="color:#e8eaf0;font-size:14px;overflow:hidden;'
            f'text-overflow:ellipsis;white-space:nowrap;min-width:0;flex:1;">👤 {nome}</span>'
            f'<span style="color:#4f8ef7;font-weight:700;font-size:14px;'
            f'white-space:nowrap;flex-shrink:0;">{qtd}</span>'
            '</div>'
        )

    if not linhas_operadores:
        linhas_operadores = '<span style="color:#8b90a7;font-size:13px;">Nenhum lead hoje</span>'

    card_html = (
        '<div class="card-total" style="display:flex;gap:24px;align-items:flex-start;overflow:hidden;">'
            '<div style="min-width:120px;flex-shrink:0;">'
                '<span class="card-icone">🌅</span>'
                f'<div class="card-valor" style="color:#4f8ef7;">{leads_hoje}</div>'
                '<div class="card-label" style="white-space:nowrap;">Leads Captados Hoje</div>'
                f'<div style="margin-top:10px;font-size:13px;font-weight:600;color:{cor_seta};white-space:nowrap;">'
                f'  {seta}'
                f'</div>'
                f'<div style="font-size:11px;color:#8b90a7;margin-top:2px;white-space:nowrap;">Ontem: {leads_ontem} leads</div>'
            '</div>'
            '<div style="width:1px;background:#2e3347;align-self:stretch;margin:4px 0;flex-shrink:0;"></div>'
            '<div style="flex:1;overflow:hidden;">'
                '<div style="color:#8b90a7;font-size:14px;font-weight:600;'
                'text-transform:uppercase;letter-spacing:.6px;margin-bottom:8px;white-space:nowrap;">Por Operador</div>'
                + linhas_operadores +
            '</div>'
        '</div>'
    )

    st.markdown(card_html, unsafe_allow_html=True)

with h2:
    st.markdown(f"""
    <div class="card-status" style="border-left: 4px solid {cor_meta};">
        <span class="card-icone">🎯</span>
        <div class="card-valor" style="color:{cor_meta};">{leads_hoje} / {META_DIARIA}</div>
        <div class="card-label">Meta Diária de Leads</div>
        <div style="
            background:#2e3347;
            border-radius:99px;
            height:8px;
            margin-top:10px;
            overflow:hidden;
        ">
            <div style="
                background:{cor_meta};
                width:{pct_meta}%;
                height:100%;
                border-radius:99px;
                transition: width .5s ease;
            "></div>
        </div>
        <div style="color:{cor_meta}; font-size:11px; margin-top:4px;">{pct_meta}% da meta</div>
    </div>
    """, unsafe_allow_html=True)

st.markdown("---")

# ── Seção: Visão Geral (período filtrado) ─────────────────────────────────────
st.markdown("#### 📊 Visão Geral do Período")

c1, c2, c3, c4 = st.columns(4)
with c1:
    linhas_total = linhas_por_operador(df, None, "#4f8ef7")
    st.markdown(f"""
    <div class="card-total" style="display:flex;gap:16px;align-items:flex-start;overflow:hidden;">
        <div style="min-width:90px;flex-shrink:0;">
            <span class="card-icone">📋</span>
            <div class="card-valor" style="color:#4f8ef7;">{total}</div>
            <div class="card-label" style="white-space:nowrap;">Total de Leads</div>
        </div>
        <div style="width:1px;background:#2e3347;align-self:stretch;margin:4px 0;flex-shrink:0;"></div>
        <div style="flex:1;overflow:hidden;padding-top:4px;">
            <div style="color:#8b90a7;font-size:11px;font-weight:600;text-transform:uppercase;
                        letter-spacing:.6px;margin-bottom:6px;white-space:nowrap;">Por Operador</div>
            {linhas_total}
        </div>
    </div>
    """, unsafe_allow_html=True)
with c2:
    linhas_taxa = linhas_por_operador(df, "Venda Realizada", "#22c55e")
    st.markdown(f"""
    <div class="card-taxa" style="display:flex;gap:16px;align-items:flex-start;overflow:hidden;">
        <div style="min-width:90px;flex-shrink:0;">
            <span class="card-icone">📈</span>
            <div class="card-valor" style="color:#22c55e;">{taxa_conv}</div>
            <div class="card-label" style="white-space:nowrap;">Taxa de Conversão</div>
        </div>
        <div style="width:1px;background:#2e3347;align-self:stretch;margin:4px 0;flex-shrink:0;"></div>
        <div style="flex:1;overflow:hidden;padding-top:4px;">
            <div style="color:#8b90a7;font-size:11px;font-weight:600;text-transform:uppercase;
                        letter-spacing:.6px;margin-bottom:6px;white-space:nowrap;">Vendas / Op.</div>
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

# ── GRÁFICOS ──────────────────────────────────────────────────────────────────
st.markdown("#### 📈 Acumulado de Leads por Operador no Mês")
if selecionados:
    df_acum = df_todos.copy()
    df_acum = df_acum[df_acum["origem"].isin(selecionados)]
    if filtro_status != "Todos":
        df_acum = df_acum[df_acum["status"] == filtro_status]
    st.plotly_chart(grafico_acumulado(df_acum, selecionados), use_container_width=True)
else:
    st.info("Selecione ao menos um operador para ver o acumulado.")

st.markdown("---")

col_g1, col_g2 = st.columns(2)
with col_g1:
    st.markdown("#### 🍩 Distribuição por Status")
    st.plotly_chart(grafico_rosca(df), use_container_width=True)

with col_g2:
    st.markdown("#### 🏆 Ranking por Operador")
    st.plotly_chart(grafico_origens(df), use_container_width=True)

st.markdown("---")

# ── TABELA ────────────────────────────────────────────────────────────────────
st.markdown("#### 📋 Leads Recentes")

col_labels = {
    "nome":      "Nome",
    "status":    "Status",
    "origem":    "Operador",
    "atendente": "Atendente",
    "interesse": "Interesse",
    "criado_em": "Cadastrado em",
}

df_show = df[list(col_labels.keys())].rename(columns=col_labels).head(100)
st.dataframe(df_show, use_container_width=True, hide_index=True, height=320)

# ── RODAPÉ ────────────────────────────────────────────────────────────────────
st.markdown("---")
st.markdown(
    "<div style='text-align:center; color:#8b90a7; font-size:12px'>"
    "Dados atualizados automaticamente a cada 1 minuto · O2 Solution"
    "</div>",
    unsafe_allow_html=True
)

# Auto-refresh a cada 1 minuto
st.markdown("""
    <script>
        setTimeout(function() { window.location.reload(); }, 60000);
    </script>
""", unsafe_allow_html=True)
