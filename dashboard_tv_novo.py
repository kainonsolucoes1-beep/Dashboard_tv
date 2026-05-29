import streamlit as st
import requests
import pandas as pd
import plotly.graph_objects as go
import base64
import os
from datetime import datetime, date, timedelta
from PIL import Image
from config import ACCESS_TOKEN
import re as _re
import streamlit_authenticator as stauth

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))


def _renovar_token_auto() -> str | None:
    env_path = os.path.join(SCRIPT_DIR, ".env")
    try:
        with open(env_path, "r") as f:
            conteudo = f.read()
        client_id     = _re.search(r'CLIENT_ID\s*=\s*["\']([^"\']+)["\']', conteudo).group(1)
        client_secret = _re.search(r'CLIENT_SECRET\s*=\s*["\']([^"\']+)["\']', conteudo).group(1)
        refresh_token = _re.search(r'REFRESH_TOKEN\s*=\s*["\']([^"\']+)["\']', conteudo).group(1)
        resp = requests.post(
            "https://api.followize.com.br/oauth/token",
            data={
                "grant_type":    "refresh_token",
                "refresh_token": refresh_token,
                "client_id":     client_id,
                "client_secret": client_secret,
            },
            timeout=15,
        )
        if resp.status_code != 200:
            return None
        data = resp.json()
        novo_access  = data["access_token"]
        novo_refresh = data["refresh_token"]
        conteudo = _re.sub(r'ACCESS_TOKEN\s*=\s*"[^"]*"',  f'ACCESS_TOKEN  = "{novo_access}"',  conteudo)
        conteudo = _re.sub(r'REFRESH_TOKEN\s*=\s*"[^"]*"', f'REFRESH_TOKEN = "{novo_refresh}"', conteudo)
        with open(env_path, "w") as f:
            f.write(conteudo)
        return novo_access
    except Exception:
        return None

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
    "Anny":  "O2 Solution",
}

# ── MAPEAMENTO DE STATUS ───────────────────────────────────────────────────────
STATUS_MAP = {
    "pending":            "Pendente",
    "scheduled":          "Agendado",
    "proposal_sent":      "Proposta Enviada",
    "waiting_billing":    "Venda Realizada",
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
    "Pendente":            "#4f8ef7",
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

# Mapeamentos de perfil de usuário (usados no funil personalizado)
USER_ATENDENTE = {
    "isaac": "Isaac", "julia": "Julia",
    "leticia": "Leticia", "rodolfo": "Rodolfo",
    "anny": "Anny",
}
USER_COR = {
    "isaac": "#4f8ef7", "julia": "#22c55e",
    "leticia": "#8b5cf6", "rodolfo": "#f59e0b",
    "anny": "#ef4444",
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


def dias_uteis_lista(de: date, ate: date) -> list:
    """Retorna lista de dias úteis (seg–sex, sem feriados BR) entre de e ate inclusive."""
    dias, cur = [], de
    while cur <= ate:
        if cur.weekday() < 5 and cur not in FERIADOS_BR:
            dias.append(cur)
        cur += timedelta(days=1)
    return dias


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


# ── BUSCA DE DADOS ─────────────────────────────────────────────────────────────
DIAS_CRITICOS = 4  # últimos N dias considerados tempo-real

# Caminhos dos arquivos de cache em disco gerados pelo updater.py
CACHE_30_PATH   = os.path.join(SCRIPT_DIR, "cache_30dias.pkl")
CACHE_80_PATH   = os.path.join(SCRIPT_DIR, "cache_80dias.pkl")
CACHE_HOJE_PATH     = os.path.join(SCRIPT_DIR, "cache_hoje.pkl")
CACHE_CRITICOS_PATH = os.path.join(SCRIPT_DIR, "cache_criticos.pkl")


def _ler_cache_disco(path: str):
    """
    Lê um arquivo de cache gerado pelo updater.py.
    Retorna (DataFrame, datetime_atualizacao) ou (DataFrame vazio, None) se não existir.
    """
    try:
        with open(path, "rb") as f:
            import pickle
            payload = pickle.load(f)
        return payload["df"], payload["atualizado"]
    except Exception:
        return pd.DataFrame(), None


def _cache_disco_disponivel(path: str, max_age: int = 0) -> bool:
    """Retorna True se o arquivo existe e não está vazio.
    max_age > 0: exige que o arquivo tenha menos de max_age segundos."""
    if not os.path.exists(path) or os.path.getsize(path) == 0:
        return False
    if max_age > 0:
        idade = (datetime.now() - datetime.fromtimestamp(os.path.getmtime(path))).total_seconds()
        return idade < max_age
    return True


@st.fragment(run_every=30)
def _watcher_pkl():
    """Detecta quando o updater.py salva novos pkl e recarrega o dashboard automaticamente."""
    _pkls = {
        CACHE_30_PATH:       "mtime_30",
        CACHE_80_PATH:       "mtime_80",
        CACHE_HOJE_PATH:     "mtime_hoje",
        CACHE_CRITICOS_PATH: "mtime_criticos",
    }
    for path, key in _pkls.items():
        if os.path.exists(path):
            mtime = os.path.getmtime(path)
            if st.session_state.get(key, 0) < mtime:
                st.session_state[key] = mtime
                fetch_leads_30dias.clear()
                fetch_leads_80dias.clear()
                fetch_leads_criticos.clear()
                fetch_leads_hoje.clear()
                st.session_state["_aba_pk"] = st.session_state.get("aba_ativa")
                st.rerun()


def _fetch_leads_from_api(days: int, date_of: str = "creation"):
    global ACCESS_TOKEN
    headers = {"Authorization": f"Bearer {ACCESS_TOKEN}", "Accept": "application/json"}
    todos_leads = []
    pagina = 1
    date_from = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    _token_renovado = False
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
                if response.status_code == 401 and not _token_renovado:
                    novo = _renovar_token_auto()
                    if novo:
                        ACCESS_TOKEN = novo
                        headers["Authorization"] = f"Bearer {novo}"
                        _token_renovado = True
                        continue
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
        finalization   = lead.get("finalization") or {}
        valor_proposta = (
            last_proposal.get("amount")
            or finalization.get("amount")
            or 0.0
        )
        def _parse_dt(s):
            for fmt in ("%Y-%m-%dT%H:%M:%S.%fZ", "%Y-%m-%dT%H:%M:%SZ",
                        "%Y-%m-%dT%H:%M:%S.%f+00:00", "%Y-%m-%dT%H:%M:%S+00:00"):
                try:
                    return datetime.strptime(s, fmt) - timedelta(hours=3)
                except ValueError:
                    continue
            return None

        data_obj = None
        if criado_em:
            dt = _parse_dt(criado_em)
            if dt:
                data_obj  = dt.date()
                criado_em = dt.strftime("%d/%m/%Y %H:%M")
        atualizado_obj = None
        if atualizado_em:
            dt = _parse_dt(atualizado_em)
            if dt:
                atualizado_obj = dt.date()
                atualizado_em  = dt.strftime("%d/%m/%Y %H:%M")

        email    = (lead.get("contact") or {}).get("email", "") or ""
        telefone = ((lead.get("contact") or {}).get("cellphone") or
                    (lead.get("contact") or {}).get("phone", "")) or ""
        int2     = ((lead.get("interests") or {}).get("interest_2") or {}).get("name", "") or ""
        int3     = ((lead.get("interests") or {}).get("interest_3") or {}).get("name", "") or ""

        msg_raw = lead.get("message", "") or ""
        base = ""
        if msg_raw:
            first_line = msg_raw.split("\n")[0]
            if first_line.startswith("Base:"):
                base = first_line[5:].strip().strip("|").strip()

        last_inter = lead.get("last_interaction_at", "") or ""
        last_inter_dt = None
        if last_inter:
            dt = _parse_dt(last_inter)
            if dt:
                last_inter_dt = dt
                last_inter = dt.strftime("%d/%m/%Y %H:%M")

        status_fechado = status_raw in ("sale_performed", "sale_not_performed", "waiting_billing")
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
            "atualizado_obj":      atualizado_obj,
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
            "base":                base,
            "em_atraso":           em_atraso,
        })
    return pd.DataFrame(registros), None


@st.cache_data(ttl=1800, show_spinner=False)
def fetch_leads_30dias():
    """
    60 dias por criação.
    Prioriza o cache em disco do updater.py (quase instantâneo).
    Só vai à API se o arquivo não existir ou estiver desatualizado.
    """
    if _cache_disco_disponivel(CACHE_30_PATH):
        df, _ = _ler_cache_disco(CACHE_30_PATH)
        if not df.empty:
            return df, None
    return _fetch_leads_from_api(days=60, date_of="creation")


@st.cache_data(ttl=1800, show_spinner=False)
def fetch_leads_80dias():
    """
    80 dias por criação.
    Prioriza o cache em disco do updater.py (quase instantâneo).
    Só vai à API se o arquivo não existir ou estiver desatualizado.
    """
    if _cache_disco_disponivel(CACHE_80_PATH):
        df, _ = _ler_cache_disco(CACHE_80_PATH)
        if not df.empty:
            return df, None
    return _fetch_leads_from_api(days=80, date_of="creation")


@st.cache_data(ttl=60, show_spinner=False)
def fetch_leads_criticos():
    """
    Últimos 4 dias por atualização.
    Prioriza o cache em disco do updater.py.
    Só vai à API se o arquivo não existir ou estiver desatualizado.
    """
    if _cache_disco_disponivel(CACHE_CRITICOS_PATH):
        df, _ = _ler_cache_disco(CACHE_CRITICOS_PATH)
        if not df.empty:
            return df, None
    return _fetch_leads_from_api(days=DIAS_CRITICOS, date_of="change")


@st.cache_data(ttl=55, show_spinner=False)
def fetch_leads_hoje():
    """
    Leads criados nos últimos 5 dias (garante que a sexta-feira aparece na segunda).
    Prioriza o cache em disco do updater.py, mas valida se o último dia útil está presente.
    """
    if _cache_disco_disponivel(CACHE_HOJE_PATH):
        df, _ = _ler_cache_disco(CACHE_HOJE_PATH)
        if not df.empty and "data_obj" in df.columns:
            # Calcula o último dia útil pulando fins de semana
            _ult = date.today() - timedelta(days=1)
            while _ult.weekday() >= 5:
                _ult -= timedelta(days=1)
            if (df["data_obj"] == _ult).any():
                return df, None
            # Cache não cobre o último dia útil — chama API diretamente
        elif not df.empty:
            return df, None
    return _fetch_leads_from_api(days=5, date_of="creation")


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


# ── BASE ALIASES ──────────────────────────────────────────────────────────────
_ALIASES_PATH = os.path.join(SCRIPT_DIR, "base_aliases.json")

def load_base_aliases() -> dict:
    if os.path.exists(_ALIASES_PATH):
        try:
            import json
            with open(_ALIASES_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}

def save_base_aliases(aliases: dict):
    import json
    with open(_ALIASES_PATH, "w", encoding="utf-8") as f:
        json.dump(aliases, f, ensure_ascii=False, indent=2)

def apply_base_aliases(df: pd.DataFrame, aliases: dict) -> pd.DataFrame:
    if aliases and "base" in df.columns:
        df = df.copy()
        # normaliza chaves para busca case-insensitive e sem espaços
        aliases_norm = {k.strip().lower(): v for k, v in aliases.items()}
        def _lookup(b):
            if not b:
                return b
            if b in aliases:
                return aliases[b]
            return aliases_norm.get(b.strip().lower(), b)
        # aplica em múltiplos passes para resolver encadeamentos
        # (ex: "SulAmerica"→"Base SulAmerica"→"Nome Final")
        for _ in range(5):
            antes = df["base"].copy()
            df["base"] = df["base"].apply(_lookup)
            if df["base"].equals(antes):
                break
    return df


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
            'padding:6px 0;border-bottom:1px solid var(--border);">'
            f'<span style="color:var(--text-main);font-size:14px;font-weight:500;">👤 {row["origem"]}</span>'
            f'<span style="color:{cor};font-weight:700;font-size:20px;line-height:1;">{row["qtd"]}</span>'
            '</div>'
        )
    return html


def render_card(icone, valor, label, cor, df=None, status_filtro=None):
    """Renderiza card de métrica com breakdown opcional por operador."""
    if df is not None:
        linhas = linhas_por_operador(df, status_filtro, cor)
        st.markdown(f"""
        <div class="card-status" style="border-left:4px solid {cor};display:flex;gap:20px;align-items:flex-start;">
            <div style="min-width:100px;">
                <span class="card-icone">{icone}</span>
                <div class="card-valor" style="color:{cor};">{valor}</div>
                <div class="card-label">{label}</div>
            </div>
            <div style="width:1px;background:var(--border);align-self:stretch;margin:4px 0;"></div>
            <div style="flex:1;min-width:0;padding-top:4px;">
                <div style="color:var(--text-sub);font-size:12px;font-weight:600;text-transform:uppercase;
                            letter-spacing:.7px;margin-bottom:8px;">Por Operador</div>
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


@st.dialog("Detalhamento de Leads", width="large")
def modal_leads_status(df_modal, label, cor, atendentes=None, operadores=None, show_perception=False):
    """
    atendentes: lista de nomes para filtro por atendente (ex: ["Giovanna", "Rayanna"]).
    operadores: lista de nomes para filtro por origem/operador (ex: SDR).
    show_perception: exibe coluna Temperatura (morno/frio) e filtro correspondente.
    """
    if df_modal.empty:
        st.info("Nenhum lead encontrado.")
        return

    df_filtrado = df_modal.copy()

    if show_perception:
        _fcol1, _fcol2, _fcol3 = st.columns([3, 2, 2])
    else:
        _fcol1, _fcol2 = st.columns([3, 2])

    with _fcol1:
        if atendentes:
            opcoes = ["Todas"] + atendentes
            escolha = st.radio(
                "👤 Atendente",
                opcoes,
                horizontal=True,
                key="modal_filtro_atendente",
            )
            if escolha != "Todas":
                df_filtrado = df_filtrado[
                    df_filtrado["atendente"].str.contains(escolha, case=False, na=False)
                ]
        elif operadores:
            opcoes = ["Todos"] + operadores
            escolha = st.radio(
                "👤 Operador",
                opcoes,
                horizontal=True,
                key="modal_filtro_operador",
            )
            if escolha != "Todos":
                df_filtrado = df_filtrado[df_filtrado["origem"] == escolha]

    with _fcol2:
        _status_opts = ["Todos"] + sorted(df_modal["status"].dropna().unique().tolist())
        _status_sel = st.selectbox("📊 Status", options=_status_opts, key="modal_filtro_status")
        if _status_sel != "Todos":
            df_filtrado = df_filtrado[df_filtrado["status"] == _status_sel]

    if show_perception:
        with _fcol3:
            _temp_opts = ["Todos", "🌡️ Morno", "🧊 Frio"]
            _temp_sel = st.selectbox("🌡️ Temperatura", options=_temp_opts, key="modal_filtro_temp")
            if _temp_sel != "Todos":
                df_filtrado = df_filtrado[df_filtrado["perception"] == _temp_sel]

    total       = len(df_filtrado)
    valor_total = df_filtrado["valor_proposta"].sum()

    st.markdown(
        f"<div style='margin-bottom:4px;'>"
        f"<span style='color:{cor};font-size:18px;font-weight:700;'>{label}</span>"
        f"&nbsp;&nbsp;<span style='color:#7a9cc7;font-size:13px;'>"
        f"{total} lead{'s' if total != 1 else ''}</span>"
        f"&nbsp;·&nbsp;<span style='color:#7a9cc7;font-size:13px;'>"
        f"Carteira: <strong style='color:{cor};'>{fmt_brl(valor_total)}</strong></span>"
        f"</div>",
        unsafe_allow_html=True,
    )

    if show_perception:
        _cols = ["nome", "status", "origem", "atendente", "perception", "valor_proposta", "criado_em", "atualizado_em"]
        _rename = {
            "nome": "Nome", "status": "Status", "origem": "Operador",
            "atendente": "Atendente", "perception": "Temperatura",
            "valor_proposta": "Valor (R$)", "criado_em": "Cadastrado em",
            "atualizado_em": "Última Atualização",
        }
    else:
        _cols = ["nome", "status", "origem", "atendente", "valor_proposta", "criado_em", "atualizado_em"]
        _rename = {
            "nome": "Nome", "status": "Status", "origem": "Operador",
            "atendente": "Atendente", "valor_proposta": "Valor (R$)",
            "criado_em": "Cadastrado em", "atualizado_em": "Última Atualização",
        }

    df_show = df_filtrado[_cols].copy()
    df_show["_sort"] = pd.to_datetime(df_show["atualizado_em"], format="%d/%m/%Y %H:%M", errors="coerce")
    df_show = df_show.sort_values("_sort", ascending=False).drop(columns="_sort").reset_index(drop=True)
    df_show = df_show.rename(columns=_rename)
    df_show["Valor (R$)"] = df_show["Valor (R$)"].apply(
        lambda v: fmt_brl(v) if v > 0 else "—"
    )

    st.dataframe(df_show, use_container_width=True, hide_index=True, height=400)


# ── GRÁFICOS ──────────────────────────────────────────────────────────────────
def grafico_rosca(df):
    counts = df["status"].value_counts()
    labels = counts.index.tolist()
    values = counts.values.tolist()
    colors = [CORES_STATUS.get(l, "#aaa") for l in labels]
    fig = go.Figure(go.Pie(
        labels=labels, values=values, hole=0.68,
        domain=dict(x=[0, 0.58]),
        marker=dict(colors=colors, line=dict(color="rgba(0,0,0,0)", width=0)),
        textinfo="percent",
        textfont=dict(size=11, color="#e8eef8"),
        hovertemplate="<b>%{label}</b><br>%{value} leads (%{percent})<extra></extra>",
    ))
    fig.update_layout(
        margin=dict(t=10, b=10, l=10, r=10),
        showlegend=True,
        legend=dict(
            orientation="v", x=0.61, y=0.5,
            xanchor="left", yanchor="middle",
            font=dict(color="#e8eef8", size=11),
            bgcolor="rgba(0,0,0,0)",
        ),
        height=280,
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
        cor = CORES_OP[i % len(CORES_OP)]
        fig.add_trace(go.Scatter(
            x=por_dia["data_obj"].tolist(), y=por_dia["acumulado"].tolist(),
            name=operador, mode="lines+markers",
            line=dict(color=cor, width=3),
            marker=dict(color=cor, size=8, symbol="circle"),
            hovertemplate=f"<b>{operador}</b><br>%{{x|%d/%m}}<br>%{{y}} leads acumulados<extra></extra>",
        ))
    fig.update_layout(
        margin=dict(t=20, b=20, l=10, r=20), height=320,
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        legend=dict(orientation="h", y=1.1, x=0, font=dict(color="#e8eef8", size=13)),
        xaxis=dict(showgrid=True, gridcolor="#152a4a", color="#7a9cc7",
                   tickformat="%d/%m", tickfont=dict(color="#e8eef8", size=12)),
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
        "Pendente",
        "Agendado",
        "Proposta Enviada",
        "Aguardando Pagamento",
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
        height=max(160, len(labels) * 56),
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
        labels=labels, values=values, hole=0.65,
        marker=dict(colors=cores, line=dict(color="rgba(0,0,0,0)", width=0)),
        textinfo="percent",
        textfont=dict(size=11, color="#e8eef8"),
        hovertemplate="<b>%{label}</b><br>%{value} leads (%{percent})<extra></extra>",
    ))
    fig.update_layout(
        margin=dict(t=10, b=10, l=10, r=10),
        showlegend=True,
        legend=dict(
            orientation="v", x=1.02, y=0.5,
            font=dict(color="#e8eef8", size=11),
            bgcolor="rgba(0,0,0,0)",
        ),
        height=280,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
    )
    return fig


def grafico_ranking_vendas(dados: dict):
    """Barras verticais de ranking de vendas — top performer em verde, demais em azul."""
    if not dados:
        return None
    operadores = list(dados.keys())
    valores    = list(dados.values())
    max_val    = max(valores)
    cores      = ["#1D9E75" if v == max_val else "#378ADD" for v in valores]

    fig = go.Figure(go.Bar(
        x=operadores,
        y=valores,
        marker=dict(
            color=cores,
            line=dict(color="rgba(0,0,0,0)", width=0),
        ),
        text=valores,
        textposition="outside",
        textfont=dict(color="#e8eef8", size=14, family="DM Sans"),
        hovertemplate="<b>%{x}</b><br>%{y} venda(s)<extra></extra>",
    ))
    fig.update_layout(
        margin=dict(t=30, b=10, l=10, r=10),
        height=300,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(
            color="#e8eef8",
            tickfont=dict(size=13, family="DM Sans", color="#e8eef8"),
            showgrid=False,
            zeroline=False,
        ),
        yaxis=dict(
            showgrid=True,
            gridcolor="#152a4a",
            color="#7a9cc7",
            tickfont=dict(size=11),
            zeroline=False,
            dtick=1,
        ),
        bargap=0.45,
    )
    return fig


def render_ranking_vendas(dados: dict | None = None):
    """
    Cards de métrica + gráfico de barras de ranking de vendas por operador.
    `dados`: dict {operador: qtd_vendas}. Usa exemplo se None.
    """
    if dados is None:
        dados = {"Indicação": 2, "Isaac": 1, "Orgânico": 1}

    total_vendas      = sum(dados.values())
    top_operador      = max(dados, key=dados.get) if dados else "—"
    operadores_ativos = len(dados)

    st.markdown("#### 🏆 Ranking de Vendas")

    c1, c2, c3 = st.columns(3)
    with c1:
        render_card("🏆", total_vendas,       "Total de Vendas",   "#1D9E75")
    with c2:
        render_card("⭐", top_operador,        "Top Operador",      "#378ADD")
    with c3:
        render_card("👥", operadores_ativos,   "Operadores Ativos", "#f59e0b")

    fig = grafico_ranking_vendas(dados)
    if fig:
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})


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

    _status_fechados = {"Venda Realizada", "Venda não Realizada"}
    leads_abertos = int((~df_atendente["status"].isin(_status_fechados)).sum())
    leads_com_val = int((df_atendente["valor_proposta"] > 0).sum())
    ticket_medio  = total_valor / leads_com_val if leads_com_val > 0 else 0
    em_atraso_qt  = int(df_atendente["em_atraso"].sum()) if "em_atraso" in df_atendente.columns else 0

    # ── Avatar: foto circular ou boneco como fallback ─────────────────────────
    foto_uri = foto_base64(foto_path) if foto_path else None
    if foto_uri:
        avatar_html = (
            f'<img src="{foto_uri}" style="'
            f'width:96px;height:96px;border-radius:50%;'
            f'border:3px solid {cor_atendente};object-fit:cover;flex-shrink:0;">'
        )
    else:
        avatar_html = (
            f'<div style="width:96px;height:96px;border-radius:50%;'
            f'border:3px solid {cor_atendente};background:{cor_atendente}18;'
            f'display:flex;align-items:center;justify-content:center;'
            f'font-size:48px;flex-shrink:0;">'
            f'👤</div>'
        )

    _cor_atr   = "#ef4444" if em_atraso_qt > 0 else "var(--text-sub)"

    _html_carteira = f'<span style="font-size:20px;font-weight:700;">R$</span><span style="font-size:20px;font-weight:700;">{fmt_brl(total_valor).split(" ",1)[1]}</span>'
    _html_ticket   = f'<span style="font-size:20px;font-weight:700;">R$</span><span style="font-size:20px;font-weight:700;">{fmt_brl(ticket_medio).split(" ",1)[1]}</span>'
    _div_style_brl = "display:flex;align-items:baseline;justify-content:center;gap:4px;"

    # ── Cabeçalho ────────────────────────────────────────────────────────────
    st.markdown(f"""
    <div style="
        background: linear-gradient(135deg, var(--bg-card) 0%, {cor_atendente}12 100%);
        border: 2px solid {cor_atendente};
        border-radius: 20px;
        padding: 20px 28px;
        margin-bottom: 20px;
        display: flex;
        align-items: center;
        gap: 20px;
        box-shadow: 0 4px 32px {cor_atendente}22;
    ">
        <div style="display:flex;align-items:center;gap:16px;flex-shrink:0;">
            {avatar_html}
            <div>
                <span style="font-size:26px;font-weight:700;color:{cor_atendente};line-height:1.1;">{nome_atendente}</span>
            </div>
        </div>
        <div style="flex:1;display:flex;justify-content:center;align-items:center;">
            <div style="display:flex;align-items:center;gap:0;">
                <div style="text-align:center;padding:0 32px;">
                    <div style="font-size:10px;color:var(--text-sub);text-transform:uppercase;letter-spacing:.7px;margin-bottom:5px;">Leads no Período</div>
                    <div style="font-size:30px;font-weight:700;color:{cor_atendente};">{total_at}</div>
                </div>
                <div style="width:1px;height:36px;background:var(--border);"></div>
                <div style="text-align:center;padding:0 32px;">
                    <div style="font-size:10px;color:var(--text-sub);text-transform:uppercase;letter-spacing:.7px;margin-bottom:5px;">Carteira Total</div>
                    <div style="font-size:30px;font-weight:700;color:var(--green);{_div_style_brl}">{_html_carteira}</div>
                </div>
                <div style="width:1px;height:36px;background:var(--border);"></div>
                <div style="text-align:center;padding:0 32px;">
                    <div style="font-size:10px;color:var(--text-sub);text-transform:uppercase;letter-spacing:.7px;margin-bottom:5px;">Ticket Médio</div>
                    <div style="font-size:30px;font-weight:700;color:#4f8ef7;{_div_style_brl}">{_html_ticket}</div>
                </div>
                <div style="width:1px;height:36px;background:var(--border);"></div>
                <div style="text-align:center;padding:0 32px;">
                    <div style="font-size:10px;color:var(--text-sub);text-transform:uppercase;letter-spacing:.7px;margin-bottom:5px;">Em Atraso</div>
                    <div style="font-size:30px;font-weight:700;color:{_cor_atr};">{em_atraso_qt}</div>
                </div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ── Cards de temperatura com barra de progresso ───────────────────────────
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
        nome_temp = temp_label.split(' ', 1)[1]
        pct       = (qtd / total_at * 100) if total_at > 0 else 0
        with col:
            st.markdown(f"""
            <div class="card-status" style="border-left:4px solid {cfg['cor']};">
                <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:12px;">
                    <div style="display:flex;align-items:center;gap:8px;">
                        <span style="font-size:18px;">{cfg['icone']}</span>
                        <span class="card-label" style="color:{cfg['cor']};">{nome_temp.upper()}</span>
                    </div>
                    <span style="font-size:13px;font-weight:700;color:{cfg['cor']};opacity:.85;">{pct:.0f}%</span>
                </div>
                <div class="card-valor" style="color:{cfg['cor']};font-size:44px;line-height:1;">{qtd}</div>
                <div style="margin-top:12px;height:4px;background:{cfg['cor']}22;border-radius:2px;">
                    <div style="height:4px;width:{min(pct,100):.1f}%;background:{cfg['cor']};border-radius:2px;"></div>
                </div>
                <div style="margin-top:8px;font-size:12px;color:var(--text-sub);">{fmt_brl(valor_sum)}</div>
            </div>
            """, unsafe_allow_html=True)

    sem_perc = int(
        (
            (df_atendente["perception"] == "Sem percepção") &
            (~df_atendente["status"].isin(_status_fechados))
        ).sum()
    )
    pct_sp = (sem_perc / total_at * 100) if total_at > 0 else 0
    with ct4:
        st.markdown(f"""
        <div class="card-status" style="border-left:4px solid var(--text-sub);">
            <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:12px;">
                <div style="display:flex;align-items:center;gap:8px;">
                    <span style="font-size:18px;">❓</span>
                    <span class="card-label" style="color:var(--text-sub);">SEM PERCEPÇÃO</span>
                </div>
                <span style="font-size:13px;font-weight:700;color:var(--text-sub);">{pct_sp:.0f}%</span>
            </div>
            <div class="card-valor" style="color:var(--text-sub);font-size:44px;line-height:1;">{sem_perc}</div>
            <div style="margin-top:12px;height:4px;background:#ffffff12;border-radius:2px;">
                <div style="height:4px;width:{min(pct_sp,100):.1f}%;background:var(--text-sub);border-radius:2px;"></div>
            </div>
            <div style="margin-top:8px;font-size:12px;color:var(--text-sub);">não classificados</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown('<div style="height:20px"></div>', unsafe_allow_html=True)

    # ── Funil (2/3) + Pizza (1/3) ────────────────────────────────────────────
    cg1, cg2 = st.columns([1, 1])
    with cg1:
        st.markdown("#### 🔽 Funil de Status")
        st.plotly_chart(
            grafico_funil_status(df_atendente),
            use_container_width=True,
            key=f"funil_{nome_atendente}"
        )
    with cg2:
        st.markdown("#### 🌡️ Temperatura")
        fig_pizza = grafico_temperatura_pizza(df_atendente)
        if fig_pizza:
            st.plotly_chart(
                fig_pizza,
                use_container_width=True,
                key=f"pizza_{nome_atendente}"
            )
        else:
            st.info("Sem percepção classificada ainda.")

    st.markdown('<div style="height:20px"></div>', unsafe_allow_html=True)

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
    data_de      = st.session_state.get("_fv_de",      date.today() - timedelta(days=30))
    data_ate     = st.session_state.get("_fv_ate",     date.today())
    selecionados = st.session_state.get("_fv_origem",  [])
    f_status     = st.session_state.get("_fv_status",  "Todos")
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
                    _orig_f = st.session_state.get("_user_origem_filtro")
                    if _orig_f:
                        df = df[df["origem"].str.strip() == _orig_f]
                    st.session_state["df_funil"] = df
                st.rerun()
        return

    df_todos_rt = st.session_state["df_funil"]

    # ── Filtros independentes desta aba ────────────────────────────────────────
    ops_funil = sorted(df_todos_rt["origem"].dropna().unique().tolist()) if not df_todos_rt.empty else []

    _default_funil_de  = date.today() - timedelta(days=30)
    _default_funil_ate = date.today()
    funil_de     = st.session_state.get("_fv_funil_de",     _default_funil_de)
    funil_ate    = st.session_state.get("_fv_funil_ate",    _default_funil_ate)
    funil_origem = st.session_state.get("_fv_funil_origem", ops_funil)
    funil_status = st.session_state.get("_fv_funil_status", "Todos")
    filtro_temp  = st.session_state.get("_fv_funil_temp",   "Todas")
    funil_origem = [o for o in funil_origem if o in ops_funil] or ops_funil

    with st.expander("🔎 Filtros da Aba", expanded=False):
        _fb_col, _ = st.columns([1, 5])
        with _fb_col:
            _funil_atualizar = st.button("🔄 Atualizar", key="funil_refresh", use_container_width=True)
        if _funil_atualizar:
            fetch_leads_80dias.clear()
            fetch_leads_criticos.clear()
            df, _ = merge_leads_longo()
            st.session_state["df_funil"] = df
            st.rerun(scope="fragment")
        with st.form("filtros_funil", border=False):
            ff1, ff2, ff3, ff4, ff5, ff6 = st.columns([1.5, 1.5, 2.5, 2, 1.5, 1])
            with ff1:
                funil_de = st.date_input(
                    "📅 De", value=funil_de, format="DD/MM/YYYY", key="funil_de"
                )
            with ff2:
                funil_ate = st.date_input(
                    "📅 Até", value=funil_ate, format="DD/MM/YYYY", key="funil_ate"
                )
            with ff3:
                funil_origem = st.multiselect(
                    "👤 Origem", options=ops_funil, default=funil_origem, key="funil_origem"
                )
            with ff4:
                funil_status = st.selectbox(
                    "📌 Status", ["Todos"] + list(dict.fromkeys(STATUS_MAP.values())),
                    key="funil_status"
                )
            with ff5:
                filtro_temp = st.selectbox(
                    "🌡️ Temperatura",
                    ["Todas", "🔥 Quente", "🌡️ Morno", "🧊 Frio", "Sem percepção"],
                    key="filtro_temperatura"
                )
            with ff6:
                st.markdown("<div style='margin-top:24px'>", unsafe_allow_html=True)
                submitted_funil = st.form_submit_button("✔ Aplicar", use_container_width=True)
                st.markdown("</div>", unsafe_allow_html=True)
            if submitted_funil:
                funil_de     = st.session_state.get("funil_de",           _default_funil_de)
                funil_ate    = st.session_state.get("funil_ate",          _default_funil_ate)
                funil_origem = st.session_state.get("funil_origem",       ops_funil)
                funil_status = st.session_state.get("funil_status",       "Todos")
                filtro_temp  = st.session_state.get("filtro_temperatura", "Todas")
                st.session_state["_fv_funil_de"]     = funil_de
                st.session_state["_fv_funil_ate"]    = funil_ate
                st.session_state["_fv_funil_origem"] = funil_origem
                st.session_state["_fv_funil_status"] = funil_status
                st.session_state["_fv_funil_temp"]   = filtro_temp

    # ── Aplica filtros ────────────────────────────────────────────────────────
    df_funil = df_todos_rt.copy() if not df_todos_rt.empty else df_todos_rt
    if not df_funil.empty:
        df_funil = df_funil[df_funil["data_obj"].apply(
            lambda d: d is not None and funil_de <= d <= funil_ate
        )]
        if funil_origem:
            df_funil = df_funil[df_funil["origem"].isin(funil_origem)]
        _STATUS_ENCERRADOS = {"Venda Realizada", "Venda não Realizada"}
        if funil_status == "Todos":
            df_funil = df_funil[~df_funil["status"].isin(_STATUS_ENCERRADOS)]
        else:
            df_funil = df_funil[df_funil["status"] == funil_status]
        if filtro_temp != "Todas":
            df_funil = df_funil[df_funil["perception"] == filtro_temp]

    st.markdown("---")

    # Sempre derivado do username atual — evita valor stale de sessão anterior
    _funil_user     = st.session_state.get("username", "")
    _funil_is_admin = (_funil_user == "lucas")

    if not _funil_is_admin:
        # Operador logado: df_funil já está filtrado pela sua origem — usa direto
        _nome_at = USER_ATENDENTE.get(_funil_user, _funil_user.capitalize())
        _cor_at  = USER_COR.get(_funil_user, "#4f8ef7")
        render_painel_atendente(df_funil, _nome_at, _cor_at, foto_path=None)
    else:
        # Admin: painéis lado a lado de Giovanna e Rayanna
        df_giovanna = df_funil[df_funil["atendente"].str.contains("Giovanna", case=False, na=False)]
        df_rayanna  = df_funil[df_funil["atendente"].str.contains("Rayanna",  case=False, na=False)]
        col_gio, col_sep, col_ray = st.columns([1, 0.04, 1])
        with col_gio:
            render_painel_atendente(df_giovanna, "Giovanna", "#8b5cf6", foto_path="fotos/giovanna.jpg")
        with col_ray:
            render_painel_atendente(df_rayanna,  "Rayanna",  "#f59e0b", foto_path="fotos/rayanna.jpg")

    st.markdown("---")
    _titulo_cons = "#### 📊 Meu Consolidado" if not _funil_is_admin else "#### 📊 Consolidado das Atendentes"
    st.markdown(_titulo_cons)

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


def _ultimo_dia_util(referencia: date) -> date:
    """
    Retorna o último dia útil anterior à data de referência,
    pulando finais de semana e feriados nacionais do Brasil.
    """
    feriados_fixos = {
        (1,  1),   # Confraternização Universal
        (4,  21),  # Tiradentes
        (5,  1),   # Dia do Trabalho
        (9,  7),   # Independência
        (10, 12),  # Nossa Senhora Aparecida
        (11, 2),   # Finados
        (11, 15),  # Proclamação da República
        (12, 25),  # Natal
    }

    def _is_util(d: date) -> bool:
        if d.weekday() >= 5:          # sábado=5, domingo=6
            return False
        if (d.month, d.day) in feriados_fixos:
            return False
        return True

    candidato = referencia - timedelta(days=1)
    while not _is_util(candidato):
        candidato -= timedelta(days=1)
    return candidato


def render_hoje_rt():
    st.markdown("#### 📅 Hoje")
    df_base, _ = fetch_leads_hoje()
    if df_base.empty:
        return

    selecionados = st.session_state.get("visao_origem", [])
    hoje            = date.today()
    ultimo_util     = _ultimo_dia_util(hoje)

    # Nome amigável para exibir na seta (ex: "sexta-feira" na segunda)
    nomes_dia = {0:"segunda",1:"terça",2:"quarta",3:"quinta",4:"sexta"}
    nome_util = nomes_dia.get(ultimo_util.weekday(), str(ultimo_util))

    _ORIGENS_SDR_HOJE = {"julia", "isaac", "leticia", "rodolfo"}
    df_base_hoje = df_base[
        df_base["origem"].str.lower().str.strip().isin(_ORIGENS_SDR_HOJE)
    ].copy()
    if selecionados:
        df_base_hoje = df_base_hoje[df_base_hoje["origem"].isin(selecionados)]

    df_ontem_v = df_base_hoje[df_base_hoje["data_obj"].apply(lambda d: d == ultimo_util)]
    df_hoje_v  = df_base_hoje[df_base_hoje["data_obj"].apply(lambda d: d == hoje)]

    leads_hoje  = len(df_hoje_v)
    leads_ontem = len(df_ontem_v)
    diferenca   = leads_hoje - leads_ontem

    if diferenca > 0:
        seta, cor_seta = f"↑ +{diferenca} que {nome_util}", "#22c55e"
    elif diferenca < 0:
        seta, cor_seta = f"↓ {diferenca} que {nome_util}", "#ef4444"
    else:
        seta, cor_seta = f"= igual a {nome_util}", "#7a9cc7"

    if df_hoje_v.empty or "origem" not in df_hoje_v.columns:
        operadores_hoje = pd.DataFrame(columns=["origem", "qtd"])
    else:
        operadores_hoje = (
            df_hoje_v.groupby("origem").size()
            .reset_index(name="qtd").sort_values("qtd", ascending=False)
        )

    META_DIARIA = 10
    progresso = min(leads_hoje / META_DIARIA, 1.0)
    pct_meta  = int(progresso * 100)
    cor_meta  = "#22c55e" if progresso >= 1.0 else "#f59e0b" if progresso >= 0.5 else "#ef4444"
    h1, h2 = st.columns(2)

    with h1:
        linhas_op = ""
        for _, row in operadores_hoje.iterrows():
            linhas_op += (
                '<div style="display:flex;justify-content:space-between;align-items:center;'
                'padding:8px 0;border-bottom:1px solid var(--border);">'
                f'<span style="color:var(--text-main);font-size:18px;font-weight:500;">👤 {row["origem"]}</span>'
                f'<span style="color:#4f8ef7;font-weight:700;font-size:26px;line-height:1;">{row["qtd"]}</span>'
                '</div>'
            )
        if not linhas_op:
            linhas_op = '<span style="color:var(--text-sub);font-size:15px;">Nenhum lead hoje</span>'

        st.markdown(
            '<div class="card-total" style="display:flex;gap:28px;align-items:flex-start;">'
            '<div style="min-width:130px;">'
            '<span class="card-icone">🌅</span>'
            f'<div class="card-valor" style="color:#4f8ef7;">{leads_hoje}</div>'
            '<div class="card-label">Leads Captados Hoje</div>'
            f'<div style="margin-top:10px;font-size:15px;font-weight:600;color:{cor_seta};">{seta}</div>'
            f'<div style="font-size:13px;color:var(--text-sub);margin-top:4px;">{nome_util.capitalize()}: {leads_ontem} leads</div>'
            '</div>'
            '<div style="width:1px;background:var(--border);align-self:stretch;margin:4px 0;"></div>'
            '<div style="flex:1;min-width:0;padding-top:4px;">'
            '<div style="color:var(--text-sub);font-size:12px;font-weight:600;text-transform:uppercase;'
            'letter-spacing:.7px;margin-bottom:10px;">Por Operador</div>'
            + linhas_op +
            '</div></div>',
            unsafe_allow_html=True
        )

    with h2:
        _circ    = 213.63
        _offset  = _circ * (1 - progresso)
        _rest    = max(0, META_DIARIA - leads_hoje)
        _meta_txt = "Meta atingida!" if progresso >= 1.0 else f"{_rest} lead{'s' if _rest != 1 else ''} restante{'s' if _rest != 1 else ''}"
        st.markdown(f"""
        <div class="card-status" style="border-left:4px solid {cor_meta};">
            <div style="display:flex;align-items:center;gap:20px;">
                <svg width="84" height="84" viewBox="0 0 84 84" style="flex-shrink:0;">
                    <circle cx="42" cy="42" r="34" fill="none" stroke="#1c2a3d" stroke-width="7"/>
                    <circle cx="42" cy="42" r="34" fill="none" stroke="{cor_meta}" stroke-width="7"
                        stroke-dasharray="{_circ:.2f}" stroke-dashoffset="{_offset:.2f}"
                        stroke-linecap="round" transform="rotate(-90 42 42)"/>
                    <text x="42" y="47" text-anchor="middle" fill="{cor_meta}"
                        font-size="15" font-weight="700" font-family="DM Sans,sans-serif">{pct_meta}%</text>
                </svg>
                <div>
                    <div class="card-valor" style="color:{cor_meta};font-size:38px;">{leads_hoje} / {META_DIARIA}</div>
                    <div class="card-label">Meta Diária de Leads</div>
                    <div style="color:{cor_meta};font-size:12px;margin-top:8px;font-weight:600;">{_meta_txt}</div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    if progresso >= 1.0:
        _today_str = str(date.today())
        if st.session_state.get("meta_rocket_date") != _today_str:
            st.session_state["meta_rocket_date"] = _today_str
            st.markdown("""
            <style>
            @keyframes foguete-voo {
                0%   { transform: translate(0, 0) rotate(-45deg);           opacity: 1; }
                70%  { transform: translate(-65vw, -38vh) rotate(-45deg);   opacity: 1; }
                100% { transform: translate(-130vw, -60vh) rotate(-45deg);  opacity: 0; }
            }
            #foguete-meta {
                position: fixed;
                right: -140px;
                bottom: 18vh;
                font-size: 110px;
                pointer-events: none;
                z-index: 99999;
                animation: foguete-voo 3.8s cubic-bezier(0.2, 0.6, 0.3, 1) forwards;
                filter: drop-shadow(0 0 30px rgba(245, 158, 11, 0.9))
                        drop-shadow(0 0 60px rgba(245, 158, 11, 0.4));
            }
            </style>
            <span id="foguete-meta">🚀</span>
            """, unsafe_allow_html=True)


@st.fragment
def render_leads_rt():
    df_todos_rt, _ = merge_leads_curto()
    df_rt = _df_com_filtros_globais(df_todos_rt) if not df_todos_rt.empty else df_todos_rt

    _hd_leads, _btn_leads = st.columns([5, 1])
    with _hd_leads:
        st.markdown("#### 📋 Leads Recentes")
        st.markdown(
            "<p style='color:#7a9cc7;font-size:13px;margin-top:-4px;'>"
            f"Exibindo os 100 leads mais recentes do período filtrado ({len(df_rt)} no total)."
            "</p>",
            unsafe_allow_html=True
        )
    with _btn_leads:
        st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)
        _leads_atualizar = st.button("🔄 Atualizar", key="leads_refresh", use_container_width=True)
    if _leads_atualizar:
        fetch_leads_30dias.clear()
        fetch_leads_80dias.clear()
        fetch_leads_criticos.clear()
        fetch_leads_hoje.clear()
        st.rerun(scope="fragment")

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

# ── AUTENTICAÇÃO ──────────────────────────────────────────────────────────────
_CREDENTIALS = {
    "usernames": {
        "isaac":   {"email": "isaac@equipe.com",    "first_name": "Isaac",   "last_name": "", "password": "$2b$12$nNCX6xqvp1CPBWT2VmQQxeRymHfesflUbRrRt5CTo5Je0TKnKnOTS"},
        "leticia": {"email": "leticia@silva.com",   "first_name": "Leticia", "last_name": "Matos Silva", "password": "$2b$12$FLmNwpf6y2Q3zMGlJ9hATOoctEFYfmZgAevAYn.9avAqttvLM36lm"},
        "julia":   {"email": "julia@equipe.com",    "first_name": "Julia",   "last_name": "", "password": "$2b$12$Le12fc4FL64kbMcjk2Z58ejTvI4HBma46QlMGyqV3YBp81bplgz66"},
        "anny":    {"email": "anny@equipe.com.br",  "first_name": "Anny",    "last_name": "", "password": "$2b$12$8WE445z2aNYQGmD4tfkomOEWE5QtIPcVp4av9J9.al3Cam64Zce7a"},
        "lucas":   {"email": "lucas@admin.com",     "first_name": "Lucas",   "last_name": "", "password": "$2b$12$dg98BTCmfkqLqRJ1sCWpZ.KL/mYWqB5f00KgiFrPBphdXZ6.xXKWO"},
        "rodolfo": {"email": "rodolfo@equipe.com",  "first_name": "Rodolfo", "last_name": "", "password": "$2b$12$dfT5JVsAyg.ajCERMIACHuBT0G67PvFDKrsYg6mPkg7JBvNpXCYha"},
    }
}
_authenticator = stauth.Authenticate(
    _CREDENTIALS,
    cookie_name="dashboard_o2",
    cookie_key="chave_secreta_dashboard_2024",
    cookie_expiry_days=1,
)
# ── Tela de login ──────────────────────────────────────────────────────────────
if st.session_state.get("authentication_status") is not True:
    st.markdown("""
    <style>
    [data-testid="stMainBlockContainer"] { padding-top: 2rem !important; }
    [data-testid="stForm"] {
        background: var(--bg-card) !important;
        border: 1px solid var(--border) !important;
        border-radius: 20px !important;
        padding: 32px 36px !important;
        box-shadow: 0 8px 40px rgba(0,0,0,.5) !important;
    }
    </style>
    <div style="text-align:center;padding:48px 0 28px;">
        <div style="font-size:52px;line-height:1;">📺</div>
        <div style="font-size:28px;font-weight:700;color:#e8eef8;margin:14px 0 6px;letter-spacing:-.5px;">O2 Solution</div>
        <div style="font-size:13px;color:#7a9cc7;letter-spacing:.4px;">Dashboard de Acompanhamento de Leads</div>
    </div>
    """, unsafe_allow_html=True)
    _, col_login, _ = st.columns([1, 1.2, 1])
    with col_login:
        _authenticator.login(location="main")
    if st.session_state.get("authentication_status") is False:
        st.error("Usuário ou senha incorretos.")
    st.stop()

_auth_status = st.session_state.get("authentication_status")
_auth_name   = st.session_state.get("name", "")
_auth_user   = st.session_state.get("username", "")

_is_admin = (_auth_user == "lucas")
# Mapeia username → valor do campo 'origem' no dataframe
_USER_ORIGEM = {
    "isaac": "Isaac", "julia": "Julia",
    "leticia": "Leticia", "rodolfo": "Rodolfo",
    "anny": "O2 Solution",
}
st.session_state["_is_admin"]          = _is_admin
st.session_state["_auth_user"]         = _auth_user
st.session_state["_user_origem_filtro"] = _USER_ORIGEM.get(_auth_user) if not _is_admin else None

# Limpa df_funil ao trocar de usuário para evitar contaminação cross-sessão
if st.session_state.get("_prev_auth_user") != _auth_user:
    st.session_state.pop("df_funil", None)
    st.session_state["_prev_auth_user"] = _auth_user

# ── Cabeçalho ─────────────────────────────────────────────────────────────────
col_titulo, col_hora, col_btn, col_user = st.columns([3, 2, 1, 1])
with col_titulo:
    st.title("📺 Dashboard · O2 Solution")
with col_hora:
    st.markdown(
        f"<div class='update-time' style='margin-top:16px'>🕐 Atualizado: "
        f"{datetime.now().strftime('%d/%m/%Y %H:%M')}</div>",
        unsafe_allow_html=True
    )
with col_btn:
    if st.button("🚀", key="refresh"):
        # Limpa cache e reroda o script inteiro — recarrega tudo do disco
        fetch_leads_30dias.clear()
        fetch_leads_80dias.clear()
        fetch_leads_criticos.clear()
        fetch_leads_hoje.clear()
        st.rerun()  # rerun global: reroda o script completo
with col_user:
    with st.popover(f"👤 {_auth_name}", use_container_width=True):
        st.markdown(
            f"<div style='font-size:13px;color:#7a9cc7;padding:4px 0 10px;'>"
            f"Logado como <strong style='color:#e8eef8;'>{_auth_name}</strong></div>",
            unsafe_allow_html=True,
        )
        _authenticator.logout(location="main")

_watcher_pkl()

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

# Filtra por origem se não for admin
if not _is_admin and _auth_user in _USER_ORIGEM:
    _orig = _USER_ORIGEM[_auth_user]
    df_todos = df_todos[df_todos["origem"].str.strip() == _orig]

# Mantém df_curto atualizado no session_state para o render_visao_geral usar
# na seção mensal — garante consistência entre seção Hoje e seção Mensal
st.session_state["df_curto"] = df_todos

# ── NAV BAR ───────────────────────────────────────────────────────────────────
_abas = (
    ["📊 Visão Geral", "🔥 Funil de Vendas", "👤 Por Operador", "📆 Detalhamento por Dia", "📋 Leads Recentes", "🗂️ CRM"]
    if _is_admin else
    ["📊 Visão Geral", "🔥 Funil de Vendas", "👤 Por Operador", "📆 Detalhamento por Dia"]
)
_aba_restore = st.session_state.pop("_aba_pk", None)
if _aba_restore in _abas:
    st.session_state.pop("aba_ativa", None)
    _nav_idx = _abas.index(_aba_restore)
else:
    _nav_idx = 0
aba_ativa = st.radio(
    "nav",
    options=_abas,
    index=_nav_idx,
    horizontal=True,
    label_visibility="collapsed",
    key="aba_ativa",
)


@st.fragment
def render_visao_geral(df_todos: pd.DataFrame):
    # Sempre relê do disco via session_state atualizado pelo script principal
    df_todos = st.session_state.get("df_curto", df_todos)

    origens_disp = sorted(df_todos["origem"].dropna().unique().tolist())

    _default_de  = date.today() - timedelta(days=30)
    _default_ate = date.today()

    # Chaves persistentes — não são apagadas quando a aba some da tela
    selecionados  = [o for o in st.session_state.get("_fv_origem", origens_disp) if o in origens_disp] or origens_disp
    filtro_status = st.session_state.get("_fv_status",  "Todos")
    data_de       = st.session_state.get("_fv_de",      _default_de)
    data_ate      = st.session_state.get("_fv_ate",     _default_ate)

    with st.expander("🔎 Filtros da Aba", expanded=False):
        with st.form("filtros_visao", border=False):
            col_op, col_st, col_de, col_ate, col_btn_f = st.columns([3, 2, 1.5, 1.5, 1])
            with col_op:
                _w_orig = st.multiselect(
                    "👤 Origem", options=origens_disp, default=selecionados, key="visao_origem"
                )
            with col_st:
                _status_opts = ["Todos"] + list(dict.fromkeys(STATUS_MAP.values()))
                _st_idx = _status_opts.index(filtro_status) if filtro_status in _status_opts else 0
                _w_status = st.selectbox(
                    "📌 Status", _status_opts, index=_st_idx, key="visao_status"
                )
            with col_de:
                _w_de = st.date_input(
                    "📅 De", value=data_de, format="DD/MM/YYYY", key="visao_de"
                )
            with col_ate:
                _w_ate = st.date_input(
                    "📅 Até", value=data_ate, format="DD/MM/YYYY", key="visao_ate"
                )
            with col_btn_f:
                st.markdown("<div style='margin-top:24px'>", unsafe_allow_html=True)
                submitted = st.form_submit_button("✔ Aplicar", use_container_width=True)
                st.markdown("</div>", unsafe_allow_html=True)
            if submitted:
                selecionados  = _w_orig
                filtro_status = _w_status
                data_de       = _w_de
                data_ate      = _w_ate
                st.session_state["_fv_origem"] = selecionados
                st.session_state["_fv_status"] = filtro_status
                st.session_state["_fv_de"]     = data_de
                st.session_state["_fv_ate"]    = data_ate
        st.markdown("<div style='margin-top:8px'></div>", unsafe_allow_html=True)
        if st.button("🔄 Atualizar", key="visao_refresh", use_container_width=True):
            fetch_leads_30dias.clear()
            fetch_leads_hoje.clear()
            fetch_leads_criticos.clear()
            df_novo, _ = merge_leads_curto()
            st.session_state["df_curto"] = df_novo
            st.rerun(scope="fragment")

    df = df_todos.copy()
    df = df[df["data_obj"].apply(lambda d: d is not None and data_de <= d <= data_ate)]
    if selecionados:
        df = df[df["origem"].isin(selecionados)]
    if filtro_status != "Todos":
        df = df[df["status"] == filtro_status]

    st.markdown('<div style="height:20px"></div>', unsafe_allow_html=True)

    total     = len(df)
    vendas    = int((df["status"] == "Venda Realizada").sum())
    proposta  = int((df["status"] == "Proposta Enviada").sum())
    nao_venda = int((df["status"] == "Venda não Realizada").sum())
    agendado  = int((df["status"] == "Agendado").sum())
    primeiro  = int((df["status"] == "Pendente").sum())

    render_hoje_rt()

    st.markdown('<div style="height:28px"></div>', unsafe_allow_html=True)
    st.markdown("#### 📊 Pipeline · SDR")
    st.markdown("<div style='color:#7a9cc7;font-size:12px;margin-top:-10px;margin-bottom:16px;'>Leads contados pela <strong>data de criação</strong> no período selecionado</div>", unsafe_allow_html=True)

    df_sdr = df.copy()

    _ops_sdr = sorted(df_sdr["origem"].dropna().unique().tolist())

    _sdr_cols = st.columns(5)

    # Card 1 – Total de Leads
    with _sdr_cols[0]:
        _linhas = linhas_por_operador(df_sdr, None, "#4f8ef7")
        st.markdown(f"""
        <div class="card-total" style="display:flex;gap:16px;align-items:flex-start;">
            <div style="min-width:90px;">
                <span class="card-icone">📋</span>
                <div class="card-valor" style="color:#4f8ef7;">{len(df_sdr)}</div>
                <div class="card-label">Total de Leads</div>
            </div>
            <div style="width:1px;background:#152a4a;align-self:stretch;margin:4px 0;"></div>
            <div style="flex:1;min-width:0;padding-top:4px;">
                <div style="color:#7a9cc7;font-size:11px;font-weight:600;text-transform:uppercase;
                            letter-spacing:.6px;margin-bottom:6px;">Por Operador</div>
                {_linhas}
            </div>
        </div>
        """, unsafe_allow_html=True)
        if st.button("🔍 Ver leads", key="btn_total", use_container_width=True):
            modal_leads_status(df_sdr, "Total de Leads", "#4f8ef7", operadores=_ops_sdr)

    # Cards 2-5 – status fixos
    _sdr_static = [
        ("btn_prim",     "Pendente",         "👋", "#4f8ef7"),
        ("btn_agend",    "Agendado",          "📅", "#f59e0b"),
        ("btn_proposta", "Proposta Enviada",  "📄", "#8b5cf6"),
    ]
    for _i, (_btn_key, _status, _icone, _cor) in enumerate(_sdr_static):
        _df_card = df_sdr[df_sdr["status"] == _status]
        with _sdr_cols[_i + 1]:
            render_card(_icone, len(_df_card), _status, _cor, df=_df_card, status_filtro=None)
            if st.button("🔍 Ver leads", key=_btn_key, use_container_width=True):
                modal_leads_status(_df_card, _status, _cor, operadores=_ops_sdr)

    # Card 5 – 💰 Potencial em Carteira (substitui "Venda Realizada")
    _df_proposta    = df_sdr[df_sdr["status"] == "Proposta Enviada"]
    _valor_carteira = _df_proposta["valor_proposta"].sum()
    _qtd_proposta   = len(_df_proposta)

    with _sdr_cols[4]:
        st.markdown(f"""
        <div class="card-status" style="border-left:4px solid #22c55e;text-align:center;">
            <span class="card-icone">💰</span>
            <div class="card-valor" style="color:#22c55e;font-size:38px;">{fmt_brl(_valor_carteira)}</div>
            <div class="card-label">Potencial em Carteira</div>
            <div style="margin-top:10px;color:#7a9cc7;font-size:13px;">
                📄 {_qtd_proposta} lead{"s" if _qtd_proposta != 1 else ""} com proposta
            </div>
        </div>
        """, unsafe_allow_html=True)

        if st.button("🔍 Ver leads", key="btn_carteira", use_container_width=True):
            modal_leads_status(_df_proposta, "Potencial em Carteira", "#22c55e", operadores=_ops_sdr)

    st.markdown('<div style="height:28px"></div>', unsafe_allow_html=True)
    st.markdown("#### 💰 Pipeline · Equipe Comercial")
    st.markdown("<div style='color:#7a9cc7;font-size:12px;margin-top:-10px;margin-bottom:16px;'>Leads contados pela <strong>última atualização</strong> — inclui leads antigos ainda em negociação</div>", unsafe_allow_html=True)

    _ATENDENTES = ["Giovanna", "Rayanna"]
    # Usa os 80 dias do Funil (session_state["df_funil"]) quando disponível,
    # garantindo a mesma base de dados que o Funil de Vendas usa.
    _base_at = st.session_state.get("df_funil", df_todos)

    # Janela padrão: 80 dias se df_funil carregado, 30 se não (cobre pipeline histórico)
    _ec_default_days = 80 if "df_funil" in st.session_state else 30
    _ec_default_de   = date.today() - timedelta(days=_ec_default_days)
    _ec_default_ate  = date.today()
    ec_de      = st.session_state.get("ec_de",     _ec_default_de)
    ec_ate     = st.session_state.get("ec_ate",    _ec_default_ate)

    # Origens derivadas de df_todos (dados limpos da sessão atual) para garantir
    # que o admin sempre veja todas as origens, independente do df_funil em cache
    _origens_disp_ec = sorted(df_todos["origem"].dropna().unique().tolist())
    ec_origens = st.session_state.get("ec_origens", _origens_disp_ec)
    # Garante que valores salvos no session_state ainda válidos na base atual
    ec_origens = [o for o in ec_origens if o in _origens_disp_ec] or _origens_disp_ec

    with st.expander("📅 Período · Origem", expanded=False):
        with st.form("filtros_ec", border=False):
            _ec1, _ec2, _ec3, _ec4 = st.columns([2, 2, 3, 1])
            with _ec1:
                ec_de = st.date_input("De", value=ec_de, format="DD/MM/YYYY", key="ec_de")
            with _ec2:
                ec_ate = st.date_input("Até", value=ec_ate, format="DD/MM/YYYY", key="ec_ate")
            with _ec3:
                ec_origens = st.multiselect(
                    "🎯 Origem", options=_origens_disp_ec, default=ec_origens, key="ec_origens"
                )
            with _ec4:
                st.markdown("<div style='margin-top:24px'>", unsafe_allow_html=True)
                _ec_sub = st.form_submit_button("✔ Aplicar", use_container_width=True)
                st.markdown("</div>", unsafe_allow_html=True)
            if _ec_sub:
                ec_de      = st.session_state.get("ec_de",     _ec_default_de)
                ec_ate     = st.session_state.get("ec_ate",    _ec_default_ate)
                ec_origens = st.session_state.get("ec_origens", _origens_disp_ec)
    df_at = _base_at.copy()
    # Filtra por última atualização (atualizado_obj) com fallback para data de criação —
    # captura leads antigos ainda ativos na carteira da equipe comercial
    df_at = df_at[df_at.apply(
        lambda r: (r["atualizado_obj"] or r["data_obj"]) is not None
                  and ec_de <= (r["atualizado_obj"] or r["data_obj"]) <= ec_ate,
        axis=1
    )]
    if ec_origens:
        df_at = df_at[df_at["origem"].isin(ec_origens)]
    df_at = df_at[df_at["atendente"].apply(
        lambda x: any(n.lower() in str(x).lower() for n in _ATENDENTES) if pd.notna(x) else False
    )]

    _STATUS_ENCERRADOS = {"Venda Realizada", "Venda não Realizada"}

    a1, a2, a3, a4 = st.columns([1, 2, 2, 2])

    with a1:
        total_at = len(df_at[~df_at["status"].isin(_STATUS_ENCERRADOS)])
        st.markdown(f"""
        <div class="card-status" style="text-align:center;padding:24px 12px;height:100%;">
            <div style="font-size:32px;margin-bottom:4px;">🤝</div>
            <div style="font-size:40px;font-weight:700;color:#4f8ef7;line-height:1;">{total_at}</div>
            <div style="color:#7a9cc7;font-size:12px;font-weight:600;text-transform:uppercase;
                        letter-spacing:.7px;margin-top:6px;">Total de Leads</div>
            <div style="color:#7a9cc7;font-size:11px;margin-top:4px;">Giovanna + Rayanna</div>
        </div>
        """, unsafe_allow_html=True)

    # Dataframes combinados (Giovanna + Rayanna) para cada card
    df_pote_all    = df_at[
        (df_at["perception"] != "🔥 Quente") &
        (~df_at["status"].isin(_STATUS_ENCERRADOS))
    ]
    df_esteira_all = df_at[
        (df_at["perception"] == "🔥 Quente") &
        (~df_at["status"].isin(_STATUS_ENCERRADOS))
    ]
    df_vendas_all  = df_at[df_at["status"] == "Venda Realizada"]

    def _bloco_atendente(df_sub, nome, qtd_cor, qtd_label, dir_label, dir_cor, separador=True):
        borda_sep = "border-bottom:1px solid #152a4a;margin-bottom:16px;padding-bottom:16px;" if separador else ""
        return (
            f'<div style="{borda_sep}padding-top:2px;">'
            f'<div style="font-size:12px;color:#7a9cc7;font-weight:600;text-transform:uppercase;'
            f'letter-spacing:.6px;margin-bottom:10px;">{nome}</div>'
            '<div style="display:flex;gap:16px;align-items:flex-start;">'
            f'<div style="min-width:72px;">'
            f'<div style="font-size:40px;font-weight:700;color:{qtd_cor};line-height:1;">{len(df_sub)}</div>'
            f'<div style="font-size:12px;color:#7a9cc7;text-transform:uppercase;letter-spacing:.5px;margin-top:3px;">{qtd_label}</div>'
            '</div>'
            '<div style="width:1px;background:var(--border);align-self:stretch;margin:4px 0;"></div>'
            '<div style="flex:1;min-width:0;padding-top:4px;padding-left:12px;">'
            f'<div style="font-size:12px;color:#7a9cc7;font-weight:600;text-transform:uppercase;letter-spacing:.6px;margin-bottom:6px;">{dir_label}</div>'
            f'<div style="font-size:22px;font-weight:700;color:{dir_cor};line-height:1;">{fmt_brl(df_sub["valor_proposta"].sum())}</div>'
            '</div>'
            '</div></div>'
        )

    with a2:
        linhas_pote = "".join(
            _bloco_atendente(
                df_pote_all[df_pote_all["atendente"].str.contains(n, case=False, na=False)],
                n, "#8b5cf6", "leads", "Carteira", "#f59e0b",
                separador=(i < len(_ATENDENTES) - 1),
            )
            for i, n in enumerate(_ATENDENTES)
        )
        st.markdown(
            '<div class="card-status">'
            '<div style="display:flex;align-items:center;gap:8px;margin-bottom:14px;">'
            '<span style="font-size:20px;">💰</span>'
            '<span style="color:#8b5cf6;font-size:14px;font-weight:700;text-transform:uppercase;letter-spacing:.7px;">Pote da Ganância</span>'
            '</div>'
            f'{linhas_pote}</div>',
            unsafe_allow_html=True,
        )
        if st.button("🔍 Ver leads", key="btn_acomp_pote", use_container_width=True):
            modal_leads_status(df_pote_all, "Pote da Ganância", "#8b5cf6", atendentes=_ATENDENTES, show_perception=True)

    with a3:
        linhas_esteira = "".join(
            _bloco_atendente(
                df_esteira_all[df_esteira_all["atendente"].str.contains(n, case=False, na=False)],
                n, "#ef4444", "leads", "Carteira", "#f59e0b",
                separador=(i < len(_ATENDENTES) - 1),
            )
            for i, n in enumerate(_ATENDENTES)
        )
        st.markdown(
            '<div class="card-status">'
            '<div style="display:flex;align-items:center;gap:8px;margin-bottom:14px;">'
            '<span style="font-size:20px;">🔥</span>'
            '<span style="color:#ef4444;font-size:14px;font-weight:700;text-transform:uppercase;letter-spacing:.7px;">Propostas em Esteira</span>'
            '</div>'
            f'{linhas_esteira}</div>',
            unsafe_allow_html=True,
        )
        if st.button("🔍 Ver leads", key="btn_acomp_esteira", use_container_width=True):
            modal_leads_status(df_esteira_all, "Propostas em Esteira", "#ef4444", atendentes=_ATENDENTES)

    with a4:
        linhas_vendas = "".join(
            _bloco_atendente(
                df_vendas_all[df_vendas_all["atendente"].str.contains(n, case=False, na=False)],
                n, "#22c55e", "vendas", "Valor", "#22c55e",
                separador=(i < len(_ATENDENTES) - 1),
            )
            for i, n in enumerate(_ATENDENTES)
        )
        st.markdown(
            '<div class="card-status">'
            '<div style="display:flex;align-items:center;gap:8px;margin-bottom:14px;">'
            '<span style="font-size:20px;">✅</span>'
            '<span style="color:#22c55e;font-size:14px;font-weight:700;text-transform:uppercase;letter-spacing:.7px;">Vendas Realizadas</span>'
            '</div>'
            f'{linhas_vendas}</div>',
            unsafe_allow_html=True,
        )
        if st.button("🔍 Ver leads", key="btn_acomp_vendas", use_container_width=True):
            modal_leads_status(df_vendas_all, "Vendas Realizadas", "#22c55e", atendentes=_ATENDENTES)

    st.markdown('<div style="height:28px"></div>', unsafe_allow_html=True)
    col_g1, col_g2 = st.columns(2)
    with col_g1:
        st.markdown("#### 🍩 Distribuição por Status")
        st.plotly_chart(grafico_rosca(df), use_container_width=True, key="rosca_visao")
    with col_g2:
        st.markdown("#### 🏆 Ranking por Operador (Vendas)")
        st.plotly_chart(grafico_origens(df), use_container_width=True, key="origens_visao")


@st.fragment
def render_operadores(df_todos: pd.DataFrame):
    _hd_op, _btn_op = st.columns([5, 1])
    with _hd_op:
        st.markdown("#### 🔎 Filtros da Aba")
    with _btn_op:
        st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)
        _op_atualizar = st.button("🔄 Atualizar", key="op_refresh", use_container_width=True)
    if _op_atualizar:
        fetch_leads_30dias.clear()
        fetch_leads_criticos.clear()
        st.rerun(scope="fragment")
    _default_op_de  = date.today() - timedelta(days=30)
    _default_op_ate = date.today()
    op_de  = st.session_state.get("_fv_op_de",  _default_op_de)
    op_ate = st.session_state.get("_fv_op_ate", _default_op_ate)

    origens_op_disp = sorted(df_todos["origem"].dropna().unique().tolist())
    _op_orig_def    = [o for o in st.session_state.get("_fv_op_orig", origens_op_disp) if o in origens_op_disp] or origens_op_disp
    _op_status_opts = ["Todos"] + list(dict.fromkeys(STATUS_MAP.values()))
    _op_status_def  = st.session_state.get("_fv_op_status", "Todos")
    _op_status_idx  = _op_status_opts.index(_op_status_def) if _op_status_def in _op_status_opts else 0

    op_de_col, op_ate_col, op1, op2, _ = st.columns([1.5, 1.5, 2.5, 2, 1])
    with op_de_col:
        op_de = st.date_input("📅 De", value=op_de, format="DD/MM/YYYY", key="op_de")
    with op_ate_col:
        op_ate = st.date_input("📅 Até", value=op_ate, format="DD/MM/YYYY", key="op_ate")
    with op1:
        op_selecionados = st.multiselect(
            "👤 Origem", options=origens_op_disp, default=_op_orig_def, key="op_origem"
        )
    with op2:
        op_status = st.selectbox(
            "📌 Status", _op_status_opts, index=_op_status_idx, key="op_status"
        )

    # Persiste valores para sobreviver à troca de aba
    st.session_state["_fv_op_de"]     = op_de
    st.session_state["_fv_op_ate"]    = op_ate
    st.session_state["_fv_op_orig"]   = op_selecionados
    st.session_state["_fv_op_status"] = op_status

    df_todos = df_todos[df_todos["data_obj"].apply(lambda d: d is not None and op_de <= d <= op_ate)]

    df_filtrado = df_todos.copy()
    if op_selecionados:
        df_filtrado = df_filtrado[df_filtrado["origem"].isin(op_selecionados)]
    if op_status != "Todos":
        df_filtrado = df_filtrado[df_filtrado["status"] == op_status]

    _VENDEDORES = {"isaac", "leticia", "julia", "rodolfo"}
    _is_admin   = st.session_state.get("_auth_user", "") not in _VENDEDORES

    st.markdown('<div style="height:20px"></div>', unsafe_allow_html=True)

    if _is_admin:
        dados_ranking     = df_filtrado[df_filtrado["status"] == "Venda Realizada"]["origem"].value_counts().to_dict()
        total_vendas      = sum(dados_ranking.values())
        top_operador      = max(dados_ranking, key=dados_ranking.get) if dados_ranking else "—"
        operadores_ativos = len(dados_ranking)

        mc1, mc2, mc3 = st.columns(3)
        with mc1:
            render_card("🏆", total_vendas,      "Total de Vendas",   "#1D9E75")
        with mc2:
            render_card("⭐", top_operador,       "Top Operador",      "#378ADD")
        with mc3:
            render_card("👥", operadores_ativos,  "Operadores Ativos", "#f59e0b")

        st.markdown('<div style="height:16px"></div>', unsafe_allow_html=True)

        col_linha, col_rank = st.columns([6, 4])
        with col_linha:
            st.markdown("#### 📈 Acumulado de Leads")
            if op_selecionados:
                st.plotly_chart(
                    grafico_acumulado(df_filtrado, op_selecionados),
                    use_container_width=True, key="acumulado_op",
                )
            else:
                st.info("Selecione ao menos um operador.")
        with col_rank:
            st.markdown("#### 🏆 Ranking de Vendas")
            if dados_ranking:
                st.plotly_chart(
                    grafico_ranking_vendas(dados_ranking),
                    use_container_width=True,
                    config={"displayModeBar": False},
                    key="ranking_op",
                )
            else:
                st.info("Sem vendas no período.")
    else:
        st.markdown("#### 📈 Acumulado de Leads por Operador no Mês")
        if op_selecionados:
            st.plotly_chart(
                grafico_acumulado(df_filtrado, op_selecionados),
                use_container_width=True, key="acumulado_op",
            )
        else:
            st.info("Selecione ao menos um operador para ver o acumulado.")


@st.dialog("👤 Detalhes do Operador", width="large")
def modal_operador(op: str, df_op: pd.DataFrame, cor: str, de: date, ate: date):
    st.markdown(
        f"<h3 style='color:{cor};margin-bottom:4px;'>👤 {op}</h3>",
        unsafe_allow_html=True,
    )
    st.markdown("---")

    total   = len(df_op)
    vendas  = int((df_op["status"] == "Venda Realizada").sum())
    conv    = round(vendas / total * 100, 1) if total > 0 else 0
    valor   = df_op["valor_proposta"].sum()
    lc_val  = int((df_op["valor_proposta"] > 0).sum())
    ticket  = valor / lc_val if lc_val > 0 else 0
    du_lista      = dias_uteis_lista(de, ate)
    leads_por_dia = df_op[df_op["data_obj"].notna()].groupby("data_obj").size()
    du            = len(du_lista)
    media         = round(total / du, 1) if du > 0 else 0

    # Tendência: média leads/dia útil — semana atual vs semana anterior (calendário real)
    if du_lista:
        _last_du     = max(du_lista)
        _curr_mon    = _last_du - timedelta(days=_last_du.weekday())
        _prev_mon    = _curr_mon - timedelta(weeks=1)
        _curr_days   = [d for d in du_lista if d >= _curr_mon]
        _prev_days   = [d for d in du_lista if _prev_mon <= d < _curr_mon]
        _curr_leads  = sum(int(leads_por_dia.get(d, 0)) for d in _curr_days)
        _prev_leads  = sum(int(leads_por_dia.get(d, 0)) for d in _prev_days)
        _curr_avg    = round(_curr_leads / len(_curr_days), 1) if _curr_days else 0
        _prev_avg    = round(_prev_leads / len(_prev_days), 1) if _prev_days else 0
        if not _prev_days:
            tend_label, tend_cor, tend_sub = "—", "#7a9cc7", "sem semana anterior"
        elif _curr_avg > _prev_avg:
            tend_label, tend_cor = "↑ Subindo", "#22c55e"
            tend_sub = f"{_prev_avg} → {_curr_avg} leads/dia"
        elif _curr_avg < _prev_avg:
            tend_label, tend_cor = "↓ Caindo", "#ef4444"
            tend_sub = f"{_prev_avg} → {_curr_avg} leads/dia"
        else:
            tend_label, tend_cor = "→ Estável", "#7a9cc7"
            tend_sub = f"{_curr_avg} leads/dia"
    else:
        tend_label, tend_cor, tend_sub = "—", "#7a9cc7", ""

    st.markdown(f"""
    <div style="display:flex;gap:0;flex-wrap:wrap;background:#0a1628;border-radius:10px;
                border:1px solid #152a4a;overflow:hidden;margin-bottom:8px;">
      <div style="flex:1;min-width:90px;padding:14px 18px;border-right:1px solid #152a4a;">
        <div style="font-size:11px;color:#7a9cc7;text-transform:uppercase;letter-spacing:.7px;font-weight:600;">Leads</div>
        <div style="font-size:26px;font-weight:700;color:#e8eef8;margin-top:2px;">{total}</div>
      </div>
      <div style="flex:1;min-width:90px;padding:14px 18px;border-right:1px solid #152a4a;">
        <div style="font-size:11px;color:#7a9cc7;text-transform:uppercase;letter-spacing:.7px;font-weight:600;">Dias úteis</div>
        <div style="font-size:26px;font-weight:700;color:#e8eef8;margin-top:2px;">{du}</div>
      </div>
      <div style="flex:1;min-width:90px;padding:14px 18px;border-right:1px solid #152a4a;">
        <div style="font-size:11px;color:#7a9cc7;text-transform:uppercase;letter-spacing:.7px;font-weight:600;">Média/dia</div>
        <div style="font-size:26px;font-weight:700;color:{cor};margin-top:2px;">{media}</div>
      </div>
      <div style="flex:1;min-width:110px;padding:14px 18px;border-right:1px solid #152a4a;">
        <div style="font-size:11px;color:#7a9cc7;text-transform:uppercase;letter-spacing:.7px;font-weight:600;">Carteira</div>
        <div style="font-size:22px;font-weight:700;color:#f59e0b;margin-top:2px;">{fmt_brl(valor)}</div>
      </div>
      <div style="flex:1;min-width:110px;padding:14px 18px;border-right:1px solid #152a4a;">
        <div style="font-size:11px;color:#7a9cc7;text-transform:uppercase;letter-spacing:.7px;font-weight:600;">Ticket Médio</div>
        <div style="font-size:22px;font-weight:700;color:#4f8ef7;margin-top:2px;">{fmt_brl(ticket)}</div>
      </div>
      <div style="flex:1;min-width:110px;padding:14px 18px;">
        <div style="font-size:11px;color:#7a9cc7;text-transform:uppercase;letter-spacing:.7px;font-weight:600;">Tendência</div>
        <div style="font-size:20px;font-weight:700;color:{tend_cor};margin-top:4px;">{tend_label}</div>
        <div style="font-size:11px;color:#7a9cc7;margin-top:4px;">{tend_sub}</div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("#### 📈 Leads por Semana (dias úteis)")

    # Base: todos os dias úteis do período, com 0 onde não houve leads
    # du_lista e leads_por_dia já calculados acima
    registros = [{"data_obj": d, "leads": int(leads_por_dia.get(d, 0))} for d in du_lista]
    df_dia = pd.DataFrame(registros)

    # Numerar semanas sequencialmente
    semanas_ord = sorted(df_dia["data_obj"].apply(lambda d: d.isocalendar()[1]).unique())
    semana_map  = {w: f"Semana {i+1}" for i, w in enumerate(semanas_ord)}
    df_dia["semana"] = df_dia["data_obj"].apply(lambda d: semana_map[d.isocalendar()[1]])

    por_semana = df_dia.groupby("semana", sort=False)["leads"].sum().reset_index()
    por_semana["_ord"] = por_semana["semana"].map({v: k for k, v in enumerate(semana_map.values())})
    por_semana = por_semana.sort_values("_ord").drop(columns="_ord")

    fig_sem = go.Figure()
    fig_sem.add_trace(go.Scatter(
        x=por_semana["semana"].tolist(),
        y=por_semana["leads"].tolist(),
        mode="lines+markers+text",
        text=por_semana["leads"].tolist(),
        textposition="top center",
        textfont=dict(color="#e8eef8", size=13, family="DM Sans"),
        line=dict(color=cor, width=3),
        marker=dict(color=cor, size=10),
        hovertemplate="<b>%{x}</b><br>%{y} leads<extra></extra>",
    ))
    _max_sem = max(int(por_semana["leads"].max()), 1)
    fig_sem.update_layout(
        height=280,
        margin=dict(t=70, b=20, l=10, r=10),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(showgrid=False, color="#7a9cc7", tickfont=dict(color="#e8eef8", size=13)),
        yaxis=dict(showgrid=True, gridcolor="#152a4a", color="#7a9cc7",
                   tickfont=dict(color="#e8eef8", size=12), zeroline=False,
                   range=[0, _max_sem * 1.35]),
    )
    st.plotly_chart(fig_sem, use_container_width=True, key=f"modal_sem_{op}")

    st.markdown("---")
    st.markdown("#### 📅 Leads por Dia")

    # Todos os dias do período: dias úteis (com 0 se sem leads) + fins de semana + feriados
    _all_days_data = []
    _cur = de
    while _cur <= ate:
        if _cur in FERIADOS_BR:
            _tipo = "feriado"
        elif _cur.weekday() >= 5:
            _tipo = "fds"
        else:
            _tipo = "util"
        _leads_d = int(leads_por_dia.get(_cur, 0)) if _tipo == "util" else 0
        _all_days_data.append({"data_obj": _cur, "leads": _leads_d, "tipo": _tipo})
        _cur += timedelta(days=1)
    df_all_dias = pd.DataFrame(_all_days_data)

    # Cor dimmed do operador (para dias úteis sem leads)
    _HEX_RGB = {
        "#4f8ef7": (79, 142, 247), "#22c55e": (34, 197, 94),
        "#f59e0b": (245, 158, 11), "#8b5cf6": (139, 92, 246),
        "#ef4444": (239, 68, 68),  "#f97316": (249, 115, 22),
    }
    _rgb    = _HEX_RGB.get(cor, (79, 142, 247))
    _cor_dim = f"rgba({_rgb[0]},{_rgb[1]},{_rgb[2]},0.3)"
    _COR_FDS = "rgba(100,120,160,0.35)"
    _COR_FER = "rgba(245,158,11,0.45)"

    _colors, _texts, _hovers = [], [], []
    for _, _r in df_all_dias.iterrows():
        _d = _r["data_obj"]
        if _r["tipo"] == "util":
            _colors.append(cor if _r["leads"] > 0 else _cor_dim)
            _texts.append(str(int(_r["leads"])))
            _hovers.append(f"{_d.strftime('%d/%m')}: {int(_r['leads'])} lead(s)")
        elif _r["tipo"] == "fds":
            _colors.append(_COR_FDS)
            _texts.append("FDS")
            _hovers.append(f"{_d.strftime('%d/%m')}: Final de Semana")
        else:
            _colors.append(_COR_FER)
            _texts.append("Feriado")
            _hovers.append(f"{_d.strftime('%d/%m')}: Feriado")

    fig_dia = go.Figure()
    fig_dia.add_trace(go.Bar(
        x=df_all_dias["data_obj"].tolist(),
        y=df_all_dias["leads"].tolist(),
        text=_texts,
        textposition="outside",
        constraintext="none",
        textfont=dict(color="#e8eef8", size=11),
        marker_color=_colors,
        customdata=_hovers,
        hovertemplate="%{customdata}<extra></extra>",
    ))
    _tickvals = df_all_dias["data_obj"].tolist()
    _ticktext = [d.strftime("%d/%m") for d in _tickvals]
    _max_dia = max(int(df_all_dias["leads"].max()), 1)
    fig_dia.update_layout(
        height=260,
        margin=dict(t=35, b=20, l=10, r=10),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(
            showgrid=False, color="#7a9cc7",
            tickmode="array", tickvals=_tickvals, ticktext=_ticktext,
            tickfont=dict(color="#e8eef8", size=11),
        ),
        yaxis=dict(showgrid=True, gridcolor="#152a4a", color="#7a9cc7",
                   tickfont=dict(color="#e8eef8", size=11), zeroline=False,
                   range=[0, _max_dia * 1.30]),
    )
    st.plotly_chart(fig_dia, use_container_width=True, key=f"modal_dia_{op}")


@st.fragment
def render_detalhamento(df_todos: pd.DataFrame):
    _hd_det, _btn_det = st.columns([5, 1])
    with _hd_det:
        st.markdown("#### 📆 Detalhamento de Leads por Dia e Operador")
        st.markdown(
            "<p style='color:#7a9cc7;font-size:13px;margin-top:-4px;'>"
            "Análise detalhada dia a dia — filtre o período abaixo de forma independente das outras abas."
            "</p>",
            unsafe_allow_html=True
        )
    with _btn_det:
        st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)
        _det_atualizar = st.button("🔄 Atualizar", key="det_refresh", use_container_width=True)
    if _det_atualizar:
        fetch_leads_30dias.clear()
        fetch_leads_criticos.clear()
        st.rerun(scope="fragment")

    st.markdown("---")
    st.markdown("#### 🔎 Filtros da Aba")
    _default_det_de  = date.today().replace(day=1)
    _default_det_ate = date.today()
    ops_disp_det     = sorted(df_todos["origem"].dropna().unique().tolist())
    _det_de_val  = st.session_state.get("_fv_det_de",  _default_det_de)
    _det_ate_val = st.session_state.get("_fv_det_ate", _default_det_ate)
    _det_ops_val = [o for o in st.session_state.get("_fv_det_ops", ops_disp_det) if o in ops_disp_det] or ops_disp_det

    fd1, fd2, fd3 = st.columns([1.5, 1.5, 3])
    with fd1:
        det_de = st.date_input(
            "📅 De", value=_det_de_val,
            format="DD/MM/YYYY", key="det_de"
        )
    with fd2:
        det_ate = st.date_input(
            "📅 Até", value=_det_ate_val,
            format="DD/MM/YYYY", key="det_ate"
        )
    with fd3:
        det_ops = st.multiselect(
            "👤 Origem", options=ops_disp_det, default=_det_ops_val, key="det_ops"
        )

    # Persiste valores para sobreviver à troca de aba
    st.session_state["_fv_det_de"]  = det_de
    st.session_state["_fv_det_ate"] = det_ate
    st.session_state["_fv_det_ops"] = det_ops

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
            total_op   = int(pivot[op].sum())
            dias_uteis = len(dias_uteis_lista(det_de, det_ate))
            media_op   = round(total_op / dias_uteis, 1) if dias_uteis > 0 else 0

            df_op_det = df_det[df_det["origem"] == op]
            valor_op  = df_op_det["valor_proposta"].sum()
            leads_com_valor = int((df_op_det["valor_proposta"] > 0).sum())
            ticket_op = valor_op / leads_com_valor if leads_com_valor > 0 else 0

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
                if st.button("📊 Ver detalhes", key=f"btn_det_{op}", use_container_width=True):
                    modal_operador(op, df_op_det, cor_op, det_de, det_ate)

    st.markdown("---")
    st.markdown("#### 📋 Leads do Período")
    st.caption("💡 Clique em uma linha para ver os detalhes completos do lead.")

    df_det_sorted = df_det.copy()
    df_det_sorted["_sort"] = pd.to_datetime(
        df_det_sorted["atualizado_em"], format="%d/%m/%Y %H:%M", errors="coerce"
    )
    df_det_sorted = (
        df_det_sorted.sort_values("_sort", ascending=False)
        .drop(columns=["_sort"])
        .reset_index(drop=True)
    )
    if "em_atraso" in df_det_sorted.columns:
        df_det_sorted["Atraso"] = df_det_sorted["em_atraso"].apply(lambda x: "🔴 Em atraso" if x else "")
    else:
        df_det_sorted["Atraso"] = ""

    col_labels_det = {
        "Atraso":         "Situação",
        "nome":           "Nome",
        "status":         "Status",
        "perception":     "Temperatura",
        "valor_proposta": "Valor (R$)",
        "atendente":      "Atendente",
        "origem":         "Operador",
        "base":           "Base",
        "interesse":      "Interesse",
        "criado_em":      "Cadastrado em",
        "atualizado_em":  "Última Atualização",
    }
    df_det_display = df_det_sorted.copy()
    df_det_display["valor_proposta"] = df_det_display["valor_proposta"].apply(
        lambda v: fmt_brl(v) if v > 0 else "—"
    )
    cols_to_show = [c for c in col_labels_det if c in df_det_display.columns]
    df_det_display = df_det_display[cols_to_show].rename(
        columns={c: col_labels_det[c] for c in cols_to_show}
    )

    evt_det = st.dataframe(
        df_det_display,
        use_container_width=True,
        hide_index=True,
        height=500,
        selection_mode="single-row",
        on_select="rerun",
        key="tabela_leads_det",
    )
    sel_det = evt_det.selection.rows
    if sel_det and st.session_state.get("modal_leads_det") != sel_det[0]:
        st.session_state["modal_leads_det"] = sel_det[0]
        modal_lead(df_det_sorted.iloc[sel_det[0]])

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
    if not sel_det:
        st.session_state.pop("modal_leads_det", None)

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


# ══════════════════════════════════════════════════════════════════════════════
# ABA 6 — CRM · BASES DE CLIENTES
# ══════════════════════════════════════════════════════════════════════════════
@st.fragment
def render_crm():
    df_todos, _ = merge_leads_curto()

    CORES_CRM = ["#4f8ef7", "#22c55e", "#f59e0b", "#8b5cf6", "#ef4444", "#f97316"]
    SEMANA_PT = {
        "Monday": "Segunda-feira", "Tuesday": "Terça-feira", "Wednesday": "Quarta-feira",
        "Thursday": "Quinta-feira", "Friday": "Sexta-feira",
        "Saturday": "Sábado", "Sunday": "Domingo",
    }

    _, crm_btn_col = st.columns([5, 1])
    with crm_btn_col:
        _crm_atualizar = st.button("🔄 Atualizar", key="crm_refresh", use_container_width=True)
    if _crm_atualizar:
        fetch_leads_30dias.clear()
        fetch_leads_criticos.clear()
        st.rerun(scope="fragment")

    aliases = load_base_aliases()
    df_todos_raw = df_todos.copy()  # nomes brutos da API, antes dos aliases
    df_todos = apply_base_aliases(df_todos, aliases)

    has_base = "base" in df_todos.columns
    df_base_all = (
        df_todos[df_todos["base"].notna() & (df_todos["base"] != "")].copy()
        if has_base else pd.DataFrame()
    )

    sub_dia, sub_ranking, sub_historico, sub_aliases = st.tabs([
        "📅 Por Data",
        "🏆 Ranking de Conversão",
        "🕐 Histórico de Bases",
        "✏️ Gerenciar Nomes",
    ])

    # ── SUB-ABA 1: POR DATA ───────────────────────────────────────────────────
    with sub_dia:
        data_crm = st.date_input(
            "📅 Selecione a data",
            value=date.today(),
            format="DD/MM/YYYY",
            key="crm_data",
        )

        df_crm = df_todos[df_todos["data_obj"].notna()].copy()
        df_crm = df_crm[df_crm["data_obj"] == data_crm]

        data_fmt  = data_crm.strftime("%d/%m/%Y")
        dia_semana = SEMANA_PT.get(data_crm.strftime("%A"), data_crm.strftime("%A"))
        st.markdown(
            f"<h3 style='color:#e8eef8;margin-bottom:2px;'>{data_fmt}"
            f"<span style='color:#7a9cc7;font-size:16px;font-weight:400;margin-left:12px;'>"
            f"{dia_semana}</span></h3>",
            unsafe_allow_html=True
        )

        if df_crm.empty:
            st.info("Nenhum lead registrado nesta data.")
        else:
            df_com_base_dia = df_crm[df_crm["base"].notna() & (df_crm["base"] != "")] if has_base else pd.DataFrame()
            m1, m2, m3, m4 = st.columns(4)
            with m1:
                st.metric("Total de Leads", len(df_crm))
            with m2:
                st.metric("Bases Identificadas", df_com_base_dia["base"].nunique() if not df_com_base_dia.empty else 0)
            with m3:
                st.metric("Operadores Ativos", df_crm["origem"].nunique())
            with m4:
                st.metric("Vendas no Dia", int((df_crm["status"] == "Venda Realizada").sum()))

            st.markdown("---")

            if df_com_base_dia.empty:
                st.warning(
                    "Nenhum lead desta data possui base registrada. "
                    "O campo **Base de Clientes** no formulário ainda não foi utilizado — "
                    "os próximos leads cadastrados já aparecerão aqui automaticamente."
                )
            else:
                st.markdown("#### 🗂️ Bases Utilizadas")
                for i, base in enumerate(sorted(df_com_base_dia["base"].unique())):
                    cor       = CORES_CRM[i % len(CORES_CRM)]
                    df_b      = df_com_base_dia[df_com_base_dia["base"] == base]
                    leads_b   = len(df_b)
                    vendas_b  = int((df_b["status"] == "Venda Realizada").sum())
                    valor_b   = df_b["valor_proposta"].sum()
                    ops_b     = ", ".join(sorted(df_b["origem"].dropna().unique()))
                    conv_b    = round(vendas_b / leads_b * 100, 1) if leads_b > 0 else 0
                    st.markdown(f"""
                    <div class="card-status" style="border-left:4px solid {cor};margin-bottom:16px;">
                      <div style="display:flex;align-items:flex-start;gap:24px;flex-wrap:wrap;">
                        <div style="min-width:220px;">
                          <div style="font-size:11px;color:#7a9cc7;text-transform:uppercase;
                                      letter-spacing:.8px;font-weight:600;margin-bottom:4px;">Base de Clientes</div>
                          <div style="font-size:20px;font-weight:700;color:{cor};word-break:break-all;">{base}</div>
                          <div style="margin-top:10px;font-size:13px;color:#7a9cc7;">
                            <b style="color:#e8eef8;">Operadores:</b> {ops_b}</div>
                        </div>
                        <div style="width:1px;background:#152a4a;align-self:stretch;flex-shrink:0;"></div>
                        <div style="display:flex;gap:28px;flex-wrap:wrap;padding-top:2px;">
                          <div>
                            <div style="font-size:11px;color:#7a9cc7;text-transform:uppercase;letter-spacing:.8px;font-weight:600;">Leads</div>
                            <div style="font-size:32px;font-weight:700;color:#e8eef8;line-height:1.1;">{leads_b}</div>
                          </div>
                          <div>
                            <div style="font-size:11px;color:#7a9cc7;text-transform:uppercase;letter-spacing:.8px;font-weight:600;">Vendas</div>
                            <div style="font-size:32px;font-weight:700;color:#22c55e;line-height:1.1;">{vendas_b}</div>
                            <div style="font-size:12px;color:#22c55e;">{conv_b}% conversão</div>
                          </div>
                          <div>
                            <div style="font-size:11px;color:#7a9cc7;text-transform:uppercase;letter-spacing:.8px;font-weight:600;">Carteira (R$)</div>
                            <div style="font-size:26px;font-weight:700;color:#f59e0b;line-height:1.1;">{fmt_brl(valor_b)}</div>
                            <div style="font-size:12px;color:#7a9cc7;">em propostas</div>
                          </div>
                        </div>
                      </div>
                    </div>
                    """, unsafe_allow_html=True)

            st.markdown("---")
            st.markdown("#### 📋 Leads do Dia")
            st.caption("💡 Clique em uma linha para ver os detalhes completos do lead.")

            df_crm_sorted = df_crm.copy()
            df_crm_sorted["_sort"] = pd.to_datetime(
                df_crm_sorted["atualizado_em"], format="%d/%m/%Y %H:%M", errors="coerce"
            )
            df_crm_sorted = (
                df_crm_sorted.sort_values("_sort", ascending=False)
                .drop(columns=["_sort"])
                .reset_index(drop=True)
            )
            if "em_atraso" in df_crm_sorted.columns:
                df_crm_sorted["Atraso"] = df_crm_sorted["em_atraso"].apply(lambda x: "🔴 Em atraso" if x else "")
            else:
                df_crm_sorted["Atraso"] = ""

            col_labels_crm = {
                "Atraso": "Situação", "nome": "Nome", "status": "Status",
                "perception": "Temperatura", "valor_proposta": "Valor (R$)",
                "atendente": "Atendente", "origem": "Operador", "base": "Base",
                "interesse": "Interesse", "atualizado_em": "Última Atualização",
            }
            df_crm_disp = df_crm_sorted.copy()
            df_crm_disp["valor_proposta"] = df_crm_disp["valor_proposta"].apply(
                lambda v: fmt_brl(v) if v > 0 else "—"
            )
            cols_crm = [c for c in col_labels_crm if c in df_crm_disp.columns]
            df_crm_disp = df_crm_disp[cols_crm].rename(columns={c: col_labels_crm[c] for c in cols_crm})

            evt_crm = st.dataframe(
                df_crm_disp, use_container_width=True, hide_index=True, height=480,
                selection_mode="single-row", on_select="rerun", key="tabela_leads_crm",
            )
            sel_crm = evt_crm.selection.rows
            if sel_crm and st.session_state.get("modal_leads_crm") != sel_crm[0]:
                st.session_state["modal_leads_crm"] = sel_crm[0]
                modal_lead(df_crm_sorted.iloc[sel_crm[0]])
            if not sel_crm:
                st.session_state.pop("modal_leads_crm", None)

    # ── SUB-ABA 2: RANKING DE CONVERSÃO ──────────────────────────────────────
    with sub_ranking:
        if df_base_all.empty:
            st.info("Nenhuma base registrada ainda. Preencha o campo **Base de Clientes** no formulário para os dados aparecerem aqui.")
        else:
            MEDALHAS = {0: "🥇", 1: "🥈", 2: "🥉"}

            ranking = (
                df_base_all.groupby("base")
                .agg(
                    leads     =("id",           "count"),
                    vendas    =("status",        lambda x: (x == "Venda Realizada").sum()),
                    carteira  =("valor_proposta","sum"),
                    dias      =("data_obj",      "nunique"),
                )
                .reset_index()
            )
            ranking["conv_pct"]    = (ranking["vendas"] / ranking["leads"].replace(0, float("nan")) * 100).fillna(0).round(1)
            ranking["ticket_medio"]= (ranking["carteira"] / ranking["vendas"].replace(0, float("nan"))).fillna(0)
            ranking = ranking.sort_values(["conv_pct", "leads"], ascending=[False, False]).reset_index(drop=True)

            r1, r2, r3 = st.columns(3)
            with r1:
                st.metric("Bases no período", len(ranking))
            with r2:
                ranking_com_venda = ranking[ranking["vendas"] > 0]
                melhor = ranking_com_venda.iloc[0]["base"] if not ranking_com_venda.empty else "—"
                st.metric("Maior conversão", melhor)
            with r3:
                media_conv = round(ranking["conv_pct"].mean(), 1) if not ranking.empty else 0
                st.metric("Conversão média", f"{media_conv}%")

            st.markdown("---")
            st.markdown("#### 🏆 Bases por Taxa de Conversão")

            for idx, row in ranking.iterrows():
                medalha   = MEDALHAS.get(idx, f"#{idx + 1}")
                cor       = CORES_CRM[idx % len(CORES_CRM)]
                conv_cor  = "#22c55e" if row["conv_pct"] >= media_conv else "#f59e0b"
                bar_w     = min(int(row["conv_pct"] * 4), 100)

                st.markdown(f"""
                <div class="card-status" style="border-left:4px solid {cor};margin-bottom:14px;">
                  <div style="display:flex;align-items:flex-start;gap:20px;flex-wrap:wrap;">
                    <div style="font-size:34px;line-height:1;min-width:48px;text-align:center;padding-top:4px;">{medalha}</div>
                    <div style="width:1px;background:#152a4a;align-self:stretch;flex-shrink:0;"></div>
                    <div style="min-width:200px;flex:1;">
                      <div style="font-size:11px;color:#7a9cc7;text-transform:uppercase;letter-spacing:.8px;font-weight:600;margin-bottom:2px;">Base</div>
                      <div style="font-size:18px;font-weight:700;color:{cor};word-break:break-all;">{row['base']}</div>
                      <div style="margin-top:8px;background:#152a4a;border-radius:99px;height:6px;width:100%;">
                        <div style="background:{conv_cor};border-radius:99px;height:6px;width:{bar_w}%;"></div>
                      </div>
                      <div style="font-size:12px;color:{conv_cor};margin-top:3px;font-weight:600;">{row['conv_pct']}% conversão</div>
                    </div>
                    <div style="width:1px;background:#152a4a;align-self:stretch;flex-shrink:0;"></div>
                    <div style="display:flex;gap:24px;flex-wrap:wrap;padding-top:4px;">
                      <div>
                        <div style="font-size:11px;color:#7a9cc7;text-transform:uppercase;letter-spacing:.8px;font-weight:600;">Leads</div>
                        <div style="font-size:26px;font-weight:700;color:#e8eef8;">{int(row['leads'])}</div>
                      </div>
                      <div>
                        <div style="font-size:11px;color:#7a9cc7;text-transform:uppercase;letter-spacing:.8px;font-weight:600;">Vendas</div>
                        <div style="font-size:26px;font-weight:700;color:#22c55e;">{int(row['vendas'])}</div>
                      </div>
                      <div>
                        <div style="font-size:11px;color:#7a9cc7;text-transform:uppercase;letter-spacing:.8px;font-weight:600;">Carteira</div>
                        <div style="font-size:22px;font-weight:700;color:#f59e0b;">{fmt_brl(row['carteira'])}</div>
                      </div>
                      <div>
                        <div style="font-size:11px;color:#7a9cc7;text-transform:uppercase;letter-spacing:.8px;font-weight:600;">Ticket Médio</div>
                        <div style="font-size:22px;font-weight:700;color:#4f8ef7;">{fmt_brl(row['ticket_medio'])}</div>
                      </div>
                      <div>
                        <div style="font-size:11px;color:#7a9cc7;text-transform:uppercase;letter-spacing:.8px;font-weight:600;">Dias Usada</div>
                        <div style="font-size:26px;font-weight:700;color:#e8eef8;">{int(row['dias'])}</div>
                      </div>
                    </div>
                  </div>
                </div>
                """, unsafe_allow_html=True)

            st.markdown("---")
            st.markdown("#### 📊 Comparativo Visual")
            fig_rank = go.Figure()
            bases_rank = ranking["base"].tolist()
            fig_rank.add_trace(go.Bar(
                name="Leads", x=bases_rank, y=ranking["leads"].tolist(),
                marker_color="#4f8ef7",
                hovertemplate="<b>%{x}</b><br>Leads: %{y}<extra></extra>",
            ))
            fig_rank.add_trace(go.Bar(
                name="Vendas", x=bases_rank, y=ranking["vendas"].tolist(),
                marker_color="#22c55e",
                hovertemplate="<b>%{x}</b><br>Vendas: %{y}<extra></extra>",
            ))
            fig_rank.update_layout(
                barmode="group", height=320,
                margin=dict(t=10, b=20, l=10, r=10),
                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                legend=dict(orientation="h", y=1.1, x=0, font=dict(color="#e8eef8", size=13)),
                xaxis=dict(showgrid=False, color="#7a9cc7", tickfont=dict(color="#e8eef8", size=11)),
                yaxis=dict(showgrid=True, gridcolor="#152a4a", color="#7a9cc7",
                           tickfont=dict(color="#e8eef8", size=12), zeroline=False),
            )
            st.plotly_chart(fig_rank, use_container_width=True, key="crm_rank_chart")

    # ── SUB-ABA 3: HISTÓRICO DE BASES ────────────────────────────────────────
    with sub_historico:
        if df_base_all.empty:
            st.info("Nenhuma base registrada ainda. Preencha o campo **Base de Clientes** no formulário para o histórico aparecer aqui.")
        else:
            _default_hist_ini = df_base_all["data_obj"].min()
            _default_hist_fim = date.today()
            hist_data_ini = st.session_state.get("hist_data_ini", _default_hist_ini)
            hist_data_fim = st.session_state.get("hist_data_fim", _default_hist_fim)

            with st.form("filtros_historico", border=False):
                col_f1, col_f2, col_f3 = st.columns([2, 2, 1])
                with col_f1:
                    hist_data_ini = st.date_input(
                        "📅 Data inicial",
                        value=hist_data_ini,
                        format="DD/MM/YYYY",
                        key="hist_data_ini",
                    )
                with col_f2:
                    hist_data_fim = st.date_input(
                        "📅 Data final",
                        value=hist_data_fim,
                        format="DD/MM/YYYY",
                        key="hist_data_fim",
                    )
                with col_f3:
                    st.markdown("<div style='margin-top:24px'>", unsafe_allow_html=True)
                    submitted_hist = st.form_submit_button("✔ Aplicar", use_container_width=True)
                    st.markdown("</div>", unsafe_allow_html=True)
                if submitted_hist:
                    hist_data_ini = st.session_state.get("hist_data_ini", _default_hist_ini)
                    hist_data_fim = st.session_state.get("hist_data_fim", _default_hist_fim)

            df_hist_filtrado = df_base_all[
                df_base_all["data_obj"].notna() &
                (df_base_all["data_obj"] >= hist_data_ini) &
                (df_base_all["data_obj"] <= hist_data_fim)
            ].copy()

            periodo_label = (
                f"{hist_data_ini.strftime('%d/%m/%Y')} → {hist_data_fim.strftime('%d/%m/%Y')}"
            )
            st.markdown(
                f"<div style='color:#7a9cc7;font-size:13px;margin-bottom:4px;'>"
                f"Exibindo: <strong style='color:#e8eef8;'>{periodo_label}</strong></div>",
                unsafe_allow_html=True,
            )
            st.markdown("---")

            if df_hist_filtrado.empty:
                st.info("Nenhuma base registrada no período selecionado.")
            else:
                historico = (
                    df_hist_filtrado.groupby("base")
                    .agg(
                        leads_total   =("id",            "count"),
                        vendas_total  =("status",        lambda x: (x == "Venda Realizada").sum()),
                        carteira_total=("valor_proposta","sum"),
                        primeira_data =("data_obj",      "min"),
                        ultima_data   =("data_obj",      "max"),
                        dias_usada    =("data_obj",      "nunique"),
                    )
                    .reset_index()
                )
                historico["conv_pct"] = (
                    historico["vendas_total"] / historico["leads_total"] * 100
                ).round(1)
                historico["ticket_medio"] = historico.apply(
                    lambda r: r["carteira_total"] / r["leads_total"] if r["leads_total"] > 0 else 0, axis=1
                )
                historico = historico.sort_values("ultima_data", ascending=False).reset_index(drop=True)

                _tot_leads    = int(historico["leads_total"].sum())
                _tot_carteira = historico["carteira_total"].sum()
                _ticket_geral = fmt_brl(_tot_carteira / _tot_leads) if _tot_leads > 0 else "R$ 0"

                h1, h2, h3, h4 = st.columns(4)
                with h1:
                    st.metric("Total de bases", len(historico))
                with h2:
                    st.metric("Leads totais", _tot_leads)
                with h3:
                    st.metric("Carteira total", fmt_brl(_tot_carteira))
                with h4:
                    st.metric("Ticket médio", _ticket_geral)

                st.markdown("---")
                st.markdown("#### 🕐 Todas as Bases Utilizadas")

                total_leads_geral = int(historico["leads_total"].sum())

                for idx, row in historico.iterrows():
                    cor          = CORES_CRM[idx % len(CORES_CRM)]
                    p_data       = row["primeira_data"].strftime("%d/%m/%Y") if pd.notna(row["primeira_data"]) else "—"
                    u_data       = row["ultima_data"].strftime("%d/%m/%Y")   if pd.notna(row["ultima_data"])   else "—"
                    captacao_pct = round(row["leads_total"] / total_leads_geral * 100, 1) if total_leads_geral > 0 else 0
                    bar_cap      = min(int(captacao_pct * 2), 100)
                    _carteira_f  = fmt_brl(float(row["carteira_total"] or 0))
                    _ticket_f    = fmt_brl(float(row["ticket_medio"]  or 0))
                    _base_nome   = str(row["base"])
                    _leads_int   = int(row["leads_total"])
                    _dias_int    = int(row["dias_usada"])

                    _esc = r'\$'
                    exp_label = (
                        f"📦 {_base_nome}  ·  "
                        f"{_leads_int} leads  ·  "
                        f"{_carteira_f.replace('$', _esc)}  ·  "
                        f"ticket: {_ticket_f.replace('$', _esc)}"
                    )
                    with st.expander(exp_label, expanded=False):
                        # percepção desta base
                        _df_b_exp = df_hist_filtrado[df_hist_filtrado["base"] == row["base"]]
                        _perc_cfg = [
                            ("🔥", "Quente",        "#ef4444", "🔥 Quente"),
                            ("🌡️", "Morno",         "#f97316", "🌡️ Morno"),
                            ("🧊", "Frio",          "#4f8ef7", "🧊 Frio"),
                            ("❓", "Sem percepção", "#475569", None),
                        ]
                        _perc_counts = _df_b_exp["perception"].value_counts()
                        _badges = ""
                        for _emoji, _label_p, _cor_p, _key_p in _perc_cfg:
                            if _key_p:
                                _cnt = int(_perc_counts.get(_key_p, 0))
                            else:
                                _cnt = int(len(_df_b_exp) - sum(
                                    _perc_counts.get(k, 0)
                                    for k in ["🔥 Quente", "🌡️ Morno", "🧊 Frio"]
                                ))
                            _badges += (
                                f'<div style="background:#0d1f38;border:1px solid {_cor_p}44;'
                                f'border-radius:10px;padding:10px 18px;text-align:center;min-width:90px;">'
                                f'<div style="font-size:20px;line-height:1;">{_emoji}</div>'
                                f'<div style="font-size:26px;font-weight:700;color:{_cor_p};line-height:1.2;">{_cnt}</div>'
                                f'<div style="font-size:11px;color:#7a9cc7;text-transform:uppercase;'
                                f'letter-spacing:.6px;margin-top:3px;">{_label_p}</div>'
                                f'</div>'
                            )

                        st.markdown(f"""
                        <div class="card-status" style="border-left:4px solid {cor};margin-bottom:14px;">
                          <div style="display:flex;align-items:flex-start;gap:20px;flex-wrap:wrap;">
                            <div style="min-width:220px;">
                              <div style="font-size:13px;color:#7a9cc7;text-transform:uppercase;letter-spacing:.8px;font-weight:600;margin-bottom:4px;">Base</div>
                              <div style="font-size:20px;font-weight:700;color:{cor};word-break:break-all;">{_base_nome}</div>
                              <div style="margin-top:10px;display:flex;gap:20px;">
                                <div>
                                  <div style="font-size:13px;color:#7a9cc7;font-weight:500;">Primeiro uso</div>
                                  <div style="font-size:15px;font-weight:700;color:#e8eef8;">{p_data}</div>
                                </div>
                                <div>
                                  <div style="font-size:13px;color:#7a9cc7;font-weight:500;">Último uso</div>
                                  <div style="font-size:15px;font-weight:700;color:#e8eef8;">{u_data}</div>
                                </div>
                                <div>
                                  <div style="font-size:13px;color:#7a9cc7;font-weight:500;">Dias usada</div>
                                  <div style="font-size:15px;font-weight:700;color:#e8eef8;">{_dias_int}</div>
                                </div>
                              </div>
                            </div>
                            <div style="width:1px;background:#152a4a;align-self:stretch;flex-shrink:0;"></div>
                            <div style="display:flex;gap:36px;flex-wrap:wrap;padding-top:4px;">
                              <div>
                                <div style="font-size:12px;color:#7a9cc7;text-transform:uppercase;letter-spacing:.8px;font-weight:600;margin-bottom:4px;">Leads</div>
                                <div style="font-size:28px;font-weight:700;color:#e8eef8;">{_leads_int}</div>
                              </div>
                              <div>
                                <div style="font-size:12px;color:#7a9cc7;text-transform:uppercase;letter-spacing:.8px;font-weight:600;margin-bottom:4px;">Carteira</div>
                                <div style="font-size:24px;font-weight:700;color:#f59e0b;">{_carteira_f}</div>
                              </div>
                              <div>
                                <div style="font-size:12px;color:#7a9cc7;text-transform:uppercase;letter-spacing:.8px;font-weight:600;margin-bottom:4px;">Ticket M&#233;dio</div>
                                <div style="font-size:24px;font-weight:700;color:#4f8ef7;">{_ticket_f}</div>
                              </div>
                              <div style="min-width:100px;">
                                <div style="font-size:12px;color:#7a9cc7;text-transform:uppercase;letter-spacing:.8px;font-weight:600;margin-bottom:4px;">% Capta&#231;&#227;o</div>
                                <div style="font-size:28px;font-weight:700;color:{cor};">{captacao_pct}%</div>
                                <div style="margin-top:4px;background:#152a4a;border-radius:99px;height:5px;width:100%;">
                                  <div style="background:{cor};border-radius:99px;height:5px;width:{bar_cap}%;"></div>
                                </div>
                                <div style="font-size:11px;color:#7a9cc7;margin-top:3px;">do total do per&#237;odo</div>
                              </div>
                            </div>
                          </div>
                        </div>
                        """, unsafe_allow_html=True)

                        st.markdown(
                            f'<div style="display:flex;gap:10px;flex-wrap:wrap;margin-bottom:16px;">'
                            f'{_badges}'
                            f'</div>',
                            unsafe_allow_html=True,
                        )

                        # ── Breakdown de origens ─────────────────────────────
                        _orig_counts = _df_b_exp["origem"].value_counts()
                        if not _orig_counts.empty:
                            st.markdown("##### 👤 Origens desta base")
                            _orig_html = '<div style="display:flex;gap:8px;flex-wrap:wrap;margin-bottom:16px;">'
                            for _orig_nome, _orig_qtd in _orig_counts.items():
                                _orig_pct = round(_orig_qtd / len(_df_b_exp) * 100, 1)
                                _orig_html += (
                                    f'<div style="background:#0d1f38;border:1px solid #1c2a3d;'
                                    f'border-radius:10px;padding:8px 16px;min-width:100px;text-align:center;">'
                                    f'<div style="font-size:13px;color:#7a9cc7;font-weight:600;'
                                    f'text-transform:uppercase;letter-spacing:.5px;margin-bottom:4px;">'
                                    f'{_orig_nome}</div>'
                                    f'<div style="font-size:26px;font-weight:700;color:{cor};line-height:1;">'
                                    f'{_orig_qtd}</div>'
                                    f'<div style="font-size:11px;color:#7a9cc7;margin-top:2px;">'
                                    f'{_orig_pct}%</div>'
                                    f'</div>'
                                )
                            _orig_html += '</div>'
                            st.markdown(_orig_html, unsafe_allow_html=True)

                        st.markdown("##### 📋 Leads desta base")
                        df_leads_base = _df_b_exp.copy()
                        df_leads_base = df_leads_base.sort_values("data_obj", ascending=False).reset_index(drop=True)
                        _cols_base = {
                            "criado_em":      "Data Captação",
                            "nome":           "Nome",
                            "origem":         "Origem",
                            "atendente":      "Atendente",
                            "status":         "Status",
                            "perception":     "Temperatura",
                            "valor_proposta": "Valor (R$)",
                            "interesse":      "Interesse",
                        }
                        df_leads_disp = df_leads_base[[c for c in _cols_base if c in df_leads_base.columns]].copy()
                        df_leads_disp.rename(columns=_cols_base, inplace=True)
                        if "Valor (R$)" in df_leads_disp.columns:
                            df_leads_disp["Valor (R$)"] = df_leads_base["valor_proposta"].apply(
                                lambda v: fmt_brl(v) if v > 0 else "—"
                            )
                        altura = min(500, 40 + len(df_leads_disp) * 35)
                        st.dataframe(df_leads_disp, use_container_width=True, hide_index=True, height=altura)

                st.markdown("---")
                st.markdown("#### 📈 Evolução de Leads por Base ao Longo do Tempo")
                por_dia_base = (
                    df_hist_filtrado.groupby(["data_obj", "base"])
                    .size()
                    .reset_index(name="leads")
                )
                fig_hist = go.Figure()
                for i, base in enumerate(historico["base"].tolist()):
                    df_b = por_dia_base[por_dia_base["base"] == base].sort_values("data_obj")
                    fig_hist.add_trace(go.Scatter(
                        name=base,
                        x=[d.strftime("%d/%m") for d in df_b["data_obj"]],
                        y=df_b["leads"].tolist(),
                        mode="lines+markers",
                        line=dict(color=CORES_CRM[i % len(CORES_CRM)], width=2),
                        marker=dict(size=6),
                        hovertemplate=f"<b>{base}</b><br>%{{x}}<br>%{{y}} leads<extra></extra>",
                    ))
                fig_hist.update_layout(
                    height=340, margin=dict(t=10, b=20, l=10, r=10),
                    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                    legend=dict(orientation="h", y=1.1, x=0, font=dict(color="#e8eef8", size=12)),
                    xaxis=dict(showgrid=False, color="#7a9cc7", tickfont=dict(color="#e8eef8", size=11)),
                    yaxis=dict(showgrid=True, gridcolor="#152a4a", color="#7a9cc7",
                               tickfont=dict(color="#e8eef8", size=12), zeroline=False),
                )
                st.plotly_chart(fig_hist, use_container_width=True, key="crm_hist_chart")

    # ── SUB-ABA 4: GERENCIAR NOMES ────────────────────────────────────────────
    with sub_aliases:
        st.markdown("#### ✏️ Corrigir Nomes de Bases")
        st.markdown(
            "<p style='color:#7a9cc7;font-size:13px;margin-top:-4px;'>"
            "Unifique variações de nomes escritos de forma diferente pelos operadores."
            "</p>",
            unsafe_allow_html=True
        )
        st.markdown("---")

        aliases_atuais = load_base_aliases()

        # ── Adicionar novo alias ───────────────────────────────────────────────
        st.markdown("#### ➕ Agrupar Variações sob um Nome Único")
        st.markdown(
            "<p style='color:#7a9cc7;font-size:13px;margin-top:-4px;'>"
            "Selecione <strong>todas</strong> as variações do mesmo nome e defina o nome final. "
            "Isso garante que datas antigas também exibam o nome correto."
            "</p>",
            unsafe_allow_html=True
        )
        # nomes brutos da API (antes dos aliases) para cobrir variações antigas
        bases_existentes = sorted(
            df_todos_raw[df_todos_raw["base"].notna() & (df_todos_raw["base"] != "")]["base"].unique().tolist()
        ) if has_base else []

        with st.form("form_add_alias", border=False):
            bases_de = st.multiselect(
                "Variações a unificar (selecione uma ou mais)",
                options=bases_existentes,
                key="alias_de"
            )
            col_para, col_btn_a = st.columns([4, 1])
            with col_para:
                base_para = st.text_input(
                    "Nome final (como deve aparecer em todo o histórico)",
                    placeholder="Ex: Base SulAmérica",
                    key="alias_para"
                )
            with col_btn_a:
                st.markdown("<div style='margin-top:24px'>", unsafe_allow_html=True)
                salvar = st.form_submit_button("✔ Salvar", use_container_width=True)
                st.markdown("</div>", unsafe_allow_html=True)

            if salvar:
                if not bases_de:
                    st.warning("Selecione ao menos uma variação.")
                elif not base_para.strip():
                    st.warning("Preencha o nome final.")
                elif bases_de == [base_para.strip()]:
                    st.warning("O nome selecionado e o nome final são iguais.")
                else:
                    nome_final = base_para.strip()
                    for variacao in bases_de:
                        if variacao != nome_final:
                            aliases_atuais[variacao] = nome_final
                    save_base_aliases(aliases_atuais)
                    nomes_str = ", ".join(f'"{v}"' for v in bases_de)
                    st.success(f'{nomes_str} → "{nome_final}" salvo(s).')
                    st.rerun(scope="fragment")

        st.markdown("---")

        # ── Lista de aliases existentes ────────────────────────────────────────
        st.markdown("#### 📋 Correções Ativas")
        if not aliases_atuais:
            st.info("Nenhuma correção cadastrada ainda.")
        else:
            for nome_original, nome_correto in list(aliases_atuais.items()):
                col_orig, col_arr, col_corr, col_del = st.columns([3, 0.5, 3, 1])
                with col_orig:
                    st.markdown(
                        f"<div style='background:#0d1f36;border:1px solid #152a4a;border-radius:8px;"
                        f"padding:8px 12px;color:#ef4444;font-size:13px;font-weight:600;'>"
                        f"{nome_original}</div>",
                        unsafe_allow_html=True
                    )
                with col_arr:
                    st.markdown(
                        "<div style='text-align:center;padding-top:8px;color:#7a9cc7;font-size:18px;'>→</div>",
                        unsafe_allow_html=True
                    )
                with col_corr:
                    st.markdown(
                        f"<div style='background:#0d1f36;border:1px solid #152a4a;border-radius:8px;"
                        f"padding:8px 12px;color:#22c55e;font-size:13px;font-weight:600;'>"
                        f"{nome_correto}</div>",
                        unsafe_allow_html=True
                    )
                with col_del:
                    if st.button("🗑️", key=f"del_alias_{nome_original}", use_container_width=True):
                        del aliases_atuais[nome_original]
                        save_base_aliases(aliases_atuais)
                        st.rerun(scope="fragment")

        # ── Nomes sem mapeamento ───────────────────────────────────────────────
        st.markdown("---")
        st.markdown("#### ⚠️ Nomes Sem Mapeamento")
        st.markdown(
            "<p style='color:#7a9cc7;font-size:13px;margin-top:-4px;'>"
            "Variações encontradas nos dados que ainda não têm correção definida. "
            "Estes nomes podem aparecer no histórico quando você recua o filtro de data."
            "</p>",
            unsafe_allow_html=True
        )
        if has_base:
            nomes_brutos = set(
                df_todos_raw[df_todos_raw["base"].notna() & (df_todos_raw["base"] != "")]["base"].unique()
            )
            sem_mapa = sorted(nomes_brutos - set(aliases_atuais.keys()))
            if sem_mapa:
                for nome in sem_mapa:
                    st.markdown(
                        f"<div style='background:#1a1a2e;border:1px solid #3a2a0a;border-radius:8px;"
                        f"padding:8px 12px;color:#f59e0b;font-size:13px;font-weight:600;margin-bottom:6px;'>"
                        f"{nome}</div>",
                        unsafe_allow_html=True
                    )
            else:
                st.success("Todos os nomes encontrados nos dados têm mapeamento.")
        else:
            st.info("Nenhum dado de base disponível.")


# ══════════════════════════════════════════════════════════════════════════════
# ABA — ESTÁGIO DO LEAD
# ══════════════════════════════════════════════════════════════════════════════
@st.fragment
def render_estagio_lead():
    # ── Botão Atualizar da aba ────────────────────────────────────────────────
    _est_h, _est_btn = st.columns([5, 1])
    with _est_btn:
        _est_atualizar = st.button("🔄 Atualizar", key="estagio_refresh", use_container_width=True)
    if _est_atualizar:
        fetch_leads_30dias.clear()
        fetch_leads_criticos.clear()
        st.rerun(scope="fragment")

    df_todos, _ = merge_leads_curto()
    if df_todos.empty:
        st.info("Nenhum dado disponível.")
        return

    # ── Filtros ───────────────────────────────────────────────────────────────
    origens_disp    = sorted(df_todos["origem"].dropna().unique().tolist())
    atendentes_disp = sorted(df_todos["atendente"].dropna().unique().tolist())

    # Lê valores atuais do session_state (persistem mesmo com expander fechado)
    _default_de = date.today() - timedelta(days=30)
    _default_ate = date.today()
    sel_origem = st.session_state.get("est_origem", [])
    sel_atend  = st.session_state.get("est_atend", [])
    est_de     = st.session_state.get("est_de", _default_de)
    est_ate    = st.session_state.get("est_ate", _default_ate)

    with st.expander("🔍 Filtros — Origem/SDR · Atendente · Período", expanded=False):
        with st.form("filtros_estagio", border=False):
            fc1, fc2, fc3, fc4, fc5 = st.columns([2, 2, 1.5, 1.5, 1])
            with fc1:
                sel_origem = st.multiselect(
                    "🎯 Origem/SDR", options=origens_disp, default=sel_origem, key="est_origem"
                )
            with fc2:
                sel_atend = st.multiselect(
                    "🎧 Atendente", options=atendentes_disp, default=sel_atend, key="est_atend"
                )
            with fc3:
                est_de = st.date_input(
                    "📅 De", value=est_de, format="DD/MM/YYYY", key="est_de"
                )
            with fc4:
                est_ate = st.date_input(
                    "📅 Até", value=est_ate, format="DD/MM/YYYY", key="est_ate"
                )
            with fc5:
                st.markdown("<div style='margin-top:24px'>", unsafe_allow_html=True)
                submitted = st.form_submit_button("✔ Aplicar", use_container_width=True)
                st.markdown("</div>", unsafe_allow_html=True)
            if submitted:
                sel_origem = st.session_state.get("est_origem", [])
                sel_atend  = st.session_state.get("est_atend", [])
                est_de     = st.session_state.get("est_de", _default_de)
                est_ate    = st.session_state.get("est_ate", _default_ate)

    df = df_todos.copy()
    df = df[df["data_obj"].apply(lambda d: d is not None and est_de <= d <= est_ate)]
    if sel_origem:
        df = df[df["origem"].isin(sel_origem)]
    if sel_atend:
        df = df[df["atendente"].isin(sel_atend)]

    if df.empty:
        st.info("Nenhum lead no período/filtro selecionado.")
        return

    # ── Dias no status (criação → atualização) ────────────────────────────────
    def _dias_entre(criado, atualizado):
        try:
            fmt = "%d/%m/%Y %H:%M"
            diff = (datetime.strptime(atualizado, fmt) - datetime.strptime(criado, fmt)).total_seconds() / 86400
            return max(round(diff, 1), 0)
        except Exception:
            return None

    df = df.copy()
    df["dias_no_status"] = df.apply(
        lambda r: _dias_entre(r["criado_em"], r["atualizado_em"])
        if r["criado_em"] and r["atualizado_em"] else None, axis=1,
    )

    # pipeline: (label, cor_hex, bg_escuro)
    PIPELINE = [
        ("Pendente",         "#4f8ef7", "#0c1c30"),
        ("Agendado",         "#f59e0b", "#1c1400"),
        ("Proposta Enviada", "#8b5cf6", "#130c25"),
        ("Venda Realizada",  "#22c55e", "#0a1c10"),
    ]
    LOST = ("Venda não Realizada", "#ef4444", "#1c0a0a")
    TODOS_STAGES = PIPELINE + [LOST]
    STATUS_COR   = {s: c for s, c, _ in TODOS_STAGES}

    total     = len(df)
    vendas    = int((df["status"] == "Venda Realizada").sum())
    conv_pct  = round(vendas / total * 100, 1) if total else 0
    ciclo_med = df["dias_no_status"].dropna().mean()
    ciclo_str = f"{ciclo_med:.1f}" if not pd.isna(ciclo_med) else "—"

    # ── Métricas ──────────────────────────────────────────────────────────────
    m1, m2, m3, m4 = st.columns(4)
    for col, val, label in [
        (m1, total,          "Total de leads"),
        (m2, vendas,         "Vendas realizadas"),
        (m3, f"{conv_pct}%", "Taxa de conversão"),
        (m4, ciclo_str,      "Ciclo médio (dias)"),
    ]:
        with col:
            st.markdown(
                f"<div style='background:var(--bg-card);border:1px solid var(--border);"
                f"border-radius:12px;padding:22px 18px;text-align:center;'>"
                f"<div style='color:#7a9cc7;font-size:11px;font-weight:600;"
                f"text-transform:uppercase;letter-spacing:.7px;margin-bottom:10px;'>{label}</div>"
                f"<div style='color:#e8eef8;font-size:38px;font-weight:700;line-height:1;'>{val}</div>"
                f"</div>",
                unsafe_allow_html=True,
            )

    st.markdown("<div style='height:28px'></div>", unsafe_allow_html=True)

    # ── Pipeline cards ────────────────────────────────────────────────────────
    def _pipe_card(status, cor, bg, dashed=False):
        sub     = df[df["status"] == status]
        qtd     = len(sub)
        med_val = sub["dias_no_status"].dropna().mean()
        med_str = f"{med_val:.1f}d" if qtd and not pd.isna(med_val) else "—"
        bar_pct = min(int(qtd / total * 100), 100) if total else 0
        border  = f"1.5px dashed {cor}55" if dashed else f"1px solid {cor}44"
        return (
            f"<div style='background:{bg};border:{border};border-radius:14px;"
            f"padding:26px 16px 22px;text-align:center;height:100%;box-sizing:border-box;'>"
            f"<div style='width:30px;height:30px;border:2px solid {cor}88;border-radius:7px;"
            f"margin:0 auto 14px;display:flex;align-items:center;justify-content:center;'>"
            f"<div style='width:12px;height:12px;background:{cor};border-radius:3px;'></div></div>"
            f"<div style='color:{cor};font-size:16px;font-weight:700;margin-bottom:14px;"
            f"white-space:nowrap;overflow:hidden;text-overflow:ellipsis;'>{status}</div>"
            f"<div style='color:#e8eef8;font-size:46px;font-weight:800;line-height:1;"
            f"margin-bottom:8px;'>{qtd}</div>"
            f"<div style='color:#7a9cc7;font-size:13px;margin-bottom:16px;'>média {med_str}</div>"
            f"<div style='background:#152a4a;border-radius:99px;height:5px;overflow:hidden;'>"
            f"<div style='background:{cor};width:{bar_pct}%;height:100%;border-radius:99px;'></div></div>"
            f"</div>"
        )

    # ── Contagens e % de passagem ─────────────────────────────────────────────
    n_pend    = int((df["status"] == "Pendente").sum())
    n_agend   = int((df["status"] == "Agendado").sum())
    n_prop    = int((df["status"] == "Proposta Enviada").sum())
    n_perdido = int((df["status"] == "Venda não Realizada").sum())

    atingiram_agend = n_agend + n_prop + vendas + n_perdido
    atingiram_prop  = n_prop + vendas + n_perdido

    pct_pend_agend   = round(atingiram_agend  / total           * 100, 1) if total           else 0
    pct_agend_prop   = round(atingiram_prop   / atingiram_agend * 100, 1) if atingiram_agend else 0
    pct_prop_venda   = round(vendas           / atingiram_prop  * 100, 1) if atingiram_prop  else 0
    pct_prop_perdido = round(n_perdido        / atingiram_prop  * 100, 1) if atingiram_prop  else 0

    def _arrow_pct(pct, cor, label="passaram"):
        return (
            f"<div style='display:flex;flex-direction:column;align-items:center;"
            f"justify-content:center;padding:0 10px;flex-shrink:0;min-width:80px;gap:5px;'>"
            f"<div style='color:{cor};font-size:15px;font-weight:800;line-height:1;'>{pct}%</div>"
            f"<div style='color:#7a9cc7;font-size:10px;text-transform:uppercase;"
            f"letter-spacing:.5px;'>{label}</div>"
            f"<svg width='42' height='14' viewBox='0 0 42 14'>"
            f"<line x1='0' y1='7' x2='33' y2='7' stroke='{cor}' stroke-width='2'/>"
            f"<polygon points='29,2 40,7 29,12' fill='{cor}'/>"
            f"</svg>"
            f"</div>"
        )

    _h_pend  = _pipe_card("Pendente",            "#4f8ef7", "#0c1c30")
    _h_agend = _pipe_card("Agendado",            "#f59e0b", "#1c1400")
    _h_prop  = _pipe_card("Proposta Enviada",    "#8b5cf6", "#130c25")
    _h_venda = _pipe_card("Venda Realizada",     "#22c55e", "#0a1c10")
    _h_perd  = _pipe_card("Venda não Realizada", "#ef4444", "#1c0a0a", dashed=True)

    _fork_col = (
        f"<div style='display:flex;flex-direction:column;align-items:center;"
        f"justify-content:center;padding:0 10px;flex-shrink:0;min-width:86px;gap:4px;'>"
        f"<div style='color:#22c55e;font-size:15px;font-weight:800;line-height:1;'>{pct_prop_venda}%</div>"
        f"<div style='color:#7a9cc7;font-size:10px;text-transform:uppercase;letter-spacing:.5px;'>vendas</div>"
        f"<svg width='42' height='14' viewBox='0 0 42 14'>"
        f"<line x1='0' y1='7' x2='33' y2='7' stroke='#22c55e' stroke-width='2'/>"
        f"<polygon points='29,2 40,7 29,12' fill='#22c55e'/>"
        f"</svg>"
        f"<div style='height:22px;border-left:1.5px dashed #7a9cc755;margin:2px 0;'></div>"
        f"<svg width='42' height='14' viewBox='0 0 42 14'>"
        f"<line x1='0' y1='7' x2='33' y2='7' stroke='#ef4444' stroke-width='1.5' stroke-dasharray='5,3'/>"
        f"<polygon points='29,2 40,7 29,12' fill='#ef4444'/>"
        f"</svg>"
        f"<div style='color:#7a9cc7;font-size:10px;text-transform:uppercase;letter-spacing:.5px;'>perdidos</div>"
        f"<div style='color:#ef4444;font-size:15px;font-weight:800;line-height:1;'>{pct_prop_perdido}%</div>"
        f"</div>"
    )

    st.markdown(
        f"<div style='display:flex;align-items:stretch;gap:0;'>"
        f"  <div style='flex:1;'>{_h_pend}</div>"
        f"  {_arrow_pct(pct_pend_agend, '#4f8ef7')}"
        f"  <div style='flex:1;'>{_h_agend}</div>"
        f"  {_arrow_pct(pct_agend_prop, '#8b5cf6')}"
        f"  <div style='flex:1;'>{_h_prop}</div>"
        f"  {_fork_col}"
        f"  <div style='flex:1;display:flex;flex-direction:column;gap:10px;'>"
        f"    <div style='flex:1;'>{_h_venda}</div>"
        f"    <div style='flex:1;'>{_h_perd}</div>"
        f"  </div>"
        f"</div>",
        unsafe_allow_html=True,
    )

    st.markdown("<div style='height:36px'></div>", unsafe_allow_html=True)

    # ── Leads por estágio (menus suspensos) ───────────────────────────────────
    AVATAR_BG  = ["#0e2040","#0c2818","#28100e","#180e28","#281e0e","#0e2828"]
    AVATAR_COR = ["#4f8ef7","#22c55e","#ef4444","#8b5cf6","#f59e0b","#22c5c5"]
    STAGE_EMOJI = {
        "Pendente":            "🔵",
        "Agendado":            "🟡",
        "Proposta Enviada":    "🟣",
        "Venda Realizada":     "🟢",
        "Venda não Realizada": "🔴",
    }

    st.markdown(
        "<div style='color:#7a9cc7;font-size:13px;font-weight:600;"
        "text-transform:uppercase;letter-spacing:.6px;margin-bottom:10px;'>"
        "Leads por estágio</div>",
        unsafe_allow_html=True,
    )

    df_sorted = df.sort_values("data_obj", ascending=False).reset_index(drop=True)

    for status, cor, bg in TODOS_STAGES:
        df_stage = df_sorted[df_sorted["status"] == status].reset_index(drop=True)
        qtd  = len(df_stage)
        icon = STAGE_EMOJI.get(status, "●")
        with st.expander(f"{icon}  {status}  —  {qtd} lead{'s' if qtd != 1 else ''}", expanded=False):
            if qtd == 0:
                st.info("Nenhum lead neste estágio.")
            else:
                cards_html = ""
                for i, row in df_stage.iterrows():
                    nome      = str(row.get("nome", "") or "").strip() or "—"
                    palavras  = [p for p in nome.split() if p]
                    initials  = (palavras[0][0] + (palavras[1][0] if len(palavras) > 1 else "")).upper()
                    av_bg     = AVATAR_BG[i % len(AVATAR_BG)]
                    av_cor    = AVATAR_COR[i % len(AVATAR_COR)]
                    status_v  = str(row.get("status", "") or "—")
                    badge_cor = STATUS_COR.get(status_v, "#7a9cc7")
                    interesse = str(row.get("interesse", "") or row.get("base", "") or "").strip()
                    if not interesse or interesse == "nan":
                        interesse = str(row.get("atendente", "") or "").strip() or "—"
                    dias     = row.get("dias_no_status")
                    dias_str = f"{int(dias)}d total" if dias is not None and not pd.isna(dias) else "—"
                    cards_html += (
                        f"<div style='background:var(--bg-card);border:1px solid var(--border);"
                        f"border-radius:12px;padding:14px 18px;display:flex;align-items:center;"
                        f"gap:14px;margin-bottom:8px;'>"
                        f"<div style='width:44px;height:44px;border-radius:50%;background:{av_bg};"
                        f"border:1.5px solid {av_cor}55;display:flex;align-items:center;"
                        f"justify-content:center;flex-shrink:0;'>"
                        f"<span style='color:{av_cor};font-weight:700;font-size:13px;'>{initials}</span></div>"
                        f"<div style='flex:1;min-width:0;'>"
                        f"<div style='color:#e8eef8;font-weight:600;font-size:14px;"
                        f"white-space:nowrap;overflow:hidden;text-overflow:ellipsis;'>{nome}</div>"
                        f"<div style='color:#7a9cc7;font-size:12px;margin-top:2px;"
                        f"white-space:nowrap;overflow:hidden;text-overflow:ellipsis;'>{interesse}</div>"
                        f"</div>"
                        f"<div style='background:{badge_cor}1a;border:1px solid {badge_cor}44;"
                        f"border-radius:99px;padding:5px 14px;flex-shrink:0;'>"
                        f"<span style='color:{badge_cor};font-size:12px;font-weight:600;"
                        f"white-space:nowrap;'>{status_v}</span></div>"
                        f"<div style='color:#7a9cc7;font-size:13px;min-width:58px;"
                        f"text-align:right;flex-shrink:0;'>{dias_str}</div>"
                        f"</div>"
                    )
                st.markdown(cards_html, unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# ABAS
# ══════════════════════════════════════════════════════════════════════════════
if "Visão Geral" in aba_ativa:
    render_visao_geral(df_todos)
elif "Funil" in aba_ativa:
    render_funil_rt()
elif "Por Operador" in aba_ativa:
    render_operadores(df_todos)
elif "Detalhamento" in aba_ativa:
    render_detalhamento(df_todos)
elif "Leads Recentes" in aba_ativa:
    render_leads_rt()
elif "CRM" in aba_ativa:
    render_crm()


# ── RODAPÉ ────────────────────────────────────────────────────────────────────
st.markdown("---")
st.markdown(
    "<div style='text-align:center;color:#7a9cc7;font-size:12px;'>"
    "Hoje · atualização manual via botão · demais seções via botão Atualizar · O2 Solution"
    "</div>",
    unsafe_allow_html=True
)

