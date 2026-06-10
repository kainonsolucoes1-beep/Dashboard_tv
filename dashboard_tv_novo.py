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
from src.utils.time import FERIADOS_BR, dias_uteis_lista, horas_uteis, _ultimo_dia_util
from src.utils.formatters import fmt_brl, foto_base64
from src.ui.styles import inject_css
from src.auth.token import _renovar_token_auto
from src.data.cache import (
    _ler_cache_disco, _cache_disco_disponivel, _watcher_pkl,
    CACHE_30_PATH, CACHE_80_PATH, CACHE_HOJE_PATH, CACHE_CRITICOS_PATH,
)
from src.data.api import (
    _fetch_leads_from_api,
    fetch_leads_30dias, fetch_leads_80dias, fetch_leads_criticos, fetch_leads_hoje,
    STATUS_MAP,
)
from src.data.transforms import merge_leads_curto, merge_leads_longo
from src.data.aliases import load_base_aliases, save_base_aliases, apply_base_aliases
from src.ui.cards import linhas_por_operador, render_card
from src.ui.modals import modal_lead, modal_leads_status, modal_operador
from src.charts.rosca import grafico_rosca
from src.charts.origens import grafico_origens
from src.charts.acumulado import grafico_acumulado
from src.charts.funil import grafico_funil_status
from src.charts.temperatura import grafico_temperatura_pizza
from src.charts.ranking import grafico_ranking_vendas, render_ranking_vendas
from src.views.visao_geral import render_visao_geral
from src.views.detalhamento import render_detalhamento
from src.views.crm import render_crm
from src.views.estagio import render_estagio_lead
from src.views.fragments import render_funil_rt, render_leads_rt
from src.views.kpis import render_kpis
from src.views.dashboard_home import render_dashboard_home

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))


# ── CONFIG ────────────────────────────────────────────────────────────────────
_logo = Image.open(os.path.join(SCRIPT_DIR, "logo o2 atualizada.png"))
st.set_page_config(
    page_title="Sales Hub - O2 Solution",
    page_icon=_logo,
    layout="wide",
    initial_sidebar_state="collapsed",
)

inject_css()

# ── AUTENTICAÇÃO ──────────────────────────────────────────────────────────────
_CREDENTIALS = {
    "usernames": {
        "isaac":   {"name": "Isaac",   "email": "isaac@equipe.com",    "first_name": "Isaac",   "last_name": "", "password": "$2b$12$nNCX6xqvp1CPBWT2VmQQxeRymHfesflUbRrRt5CTo5Je0TKnKnOTS"},
        "leticia": {"name": "Leticia Matos Silva", "email": "leticia@silva.com",   "first_name": "Leticia", "last_name": "Matos Silva", "password": "$2b$12$FLmNwpf6y2Q3zMGlJ9hATOoctEFYfmZgAevAYn.9avAqttvLM36lm"},
        "julia":   {"name": "Julia",   "email": "julia@equipe.com",    "first_name": "Julia",   "last_name": "", "password": "$2b$12$Le12fc4FL64kbMcjk2Z58ejTvI4HBma46QlMGyqV3YBp81bplgz66"},
        "anny":    {"name": "Anny",    "email": "anny@equipe.com.br",  "first_name": "Anny",    "last_name": "", "password": "$2b$12$8WE445z2aNYQGmD4tfkomOEWE5QtIPcVp4av9J9.al3Cam64Zce7a"},
        "lucas":   {"name": "Lucas",   "email": "lucas@admin.com",     "first_name": "Lucas",   "last_name": "", "password": "$2b$12$dg98BTCmfkqLqRJ1sCWpZ.KL/mYWqB5f00KgiFrPBphdXZ6.xXKWO"},
        "rodolfo": {"name": "Rodolfo", "email": "rodolfo@equipe.com",  "first_name": "Rodolfo", "last_name": "", "password": "$2b$12$dfT5JVsAyg.ajCERMIACHuBT0G67PvFDKrsYg6mPkg7JBvNpXCYha"},
    }
}
_authenticator = stauth.Authenticate(
    _CREDENTIALS,
    cookie_name="dashboard_o2",
    cookie_key="chave_secreta_dashboard_2024",
    cookie_expiry_days=1,
    auto_hash=False,
)
# ── Tela de login ──────────────────────────────────────────────────────────────
if st.session_state.get("authentication_status") is not True:
    st.markdown("""
    <style>
    [data-testid="stAppViewContainer"] {
        background: radial-gradient(ellipse at 50% 0%, #0d1f38 0%, #060d18 70%) !important;
    }
    [data-testid="stMainBlockContainer"] {
        padding-top: 0 !important;
        max-width: 540px !important;
        margin: 0 auto !important;
    }
    [data-testid="stForm"] {
        background: #111c2d !important;
        border: 1px solid #1e3a5f !important;
        border-radius: 24px !important;
        padding: 56px 64px !important;
        box-shadow: 0 20px 60px rgba(0,0,0,.7), 0 0 0 1px rgba(79,142,247,.08) !important;
    }
    [data-testid="stForm"] h2 {
        color: #e8eef8 !important;
        font-size: 20px !important;
        font-weight: 700 !important;
        margin-top: -28px !important;
        margin-bottom: 28px !important;
        letter-spacing: -.3px !important;
    }
    [data-testid="stForm"] > div > div > div > p {
        display: none !important;
    }
    [data-testid="stForm"] input {
        background: #0a1525 !important;
        color: #e8eef8 !important;
        border: 1px solid #1e3a5f !important;
        border-radius: 10px !important;
        padding: 12px 16px !important;
        font-size: 15px !important;
    }
    [data-testid="stForm"] input::placeholder,
    [data-testid="stForm"] input::-webkit-input-placeholder,
    [data-testid="stForm"] input::-moz-placeholder,
    [data-testid="stForm"] input:-ms-input-placeholder {
        color: transparent !important;
        opacity: 0 !important;
    }
    [data-testid="stForm"] input:focus {
        border-color: #4f8ef7 !important;
        box-shadow: 0 0 0 3px rgba(79,142,247,.15) !important;
    }
    [data-testid="stForm"] label {
        color: #7a9cc7 !important;
        font-size: 13px !important;
        font-weight: 600 !important;
        letter-spacing: .4px !important;
        text-transform: uppercase !important;
    }
    [data-testid="stFormSubmitButton"] button {
        background: linear-gradient(135deg, #1e4080, #4f8ef7) !important;
        color: #fff !important;
        border: none !important;
        border-radius: 10px !important;
        padding: 14px 48px !important;
        font-size: 15px !important;
        font-weight: 700 !important;
        letter-spacing: .5px !important;
        width: 100% !important;
        margin-top: 12px !important;
        transition: opacity .2s !important;
    }
    [data-testid="stFormSubmitButton"] button:hover {
        opacity: .88 !important;
    }
    [data-testid="stForm"] [data-testid="stBaseButton-minimal"] {
        background: transparent !important;
        border: none !important;
        padding: 6px !important;
        width: auto !important;
        color: #7a9cc7 !important;
    }
    </style>
    <div style="text-align:center;padding:64px 0 36px;">
        <div style="font-size:58px;line-height:1;filter:drop-shadow(0 4px 16px rgba(79,142,247,.4));">🚀</div>
        <div style="font-size:32px;font-weight:800;color:#e8eef8;margin:18px 0 8px;
                    letter-spacing:-.8px;">O2 Solution</div>
        <div style="font-size:13px;color:#4f8ef7;letter-spacing:1.2px;text-transform:uppercase;
                    font-weight:600;">Sales Hub</div>
    </div>
    """, unsafe_allow_html=True)
    try:
        _authenticator.login(
            location="main",
            fields={
                "Form name": "Acesso",
                "Username": "Usuário",
                "Password": "Senha",
                "Login": "Entrar",
            },
        )
    except Exception as _login_err:
        st.error(f"Erro ao renderizar login: {_login_err}")
    st.html("""<script>
(function(){
    function clear(){
        var els=window.parent.document.querySelectorAll('input[placeholder]');
        els.forEach(function(e){e.placeholder='';});
    }
    clear();
    new MutationObserver(clear).observe(window.parent.document.body,{childList:true,subtree:true});
})();
</script>""")
    if st.session_state.get("authentication_status") is False:
        st.error("Usuario ou senha incorretos.")
    st.stop()

_auth_status = st.session_state.get("authentication_status")
_auth_name   = st.session_state.get("name", "")
_auth_user   = st.session_state.get("username", "")

_is_admin = (_auth_user == "lucas")
_USER_ORIGEM = {
    "isaac": "Isaac", "julia": "Julia",
    "leticia": "Leticia", "rodolfo": "Rodolfo",
    "anny": "O2 Solution",
}
st.session_state["_is_admin"]          = _is_admin
st.session_state["_auth_user"]         = _auth_user
st.session_state["_user_origem_filtro"] = _USER_ORIGEM.get(_auth_user) if not _is_admin else None

if st.session_state.get("_prev_auth_user") != _auth_user:
    st.session_state.pop("df_funil", None)
    st.session_state.pop("df_curto", None)
    st.session_state.pop("df_todos_all", None)
    st.session_state["_df_curto_stale"] = True
    st.session_state["_prev_auth_user"] = _auth_user

# ── Cabeçalho ─────────────────────────────────────────────────────────────────
col_titulo, col_hora, col_btn, col_user = st.columns([3, 2, 1, 1])
with col_titulo:
    st.title("🚀 Sales Hub · O2 Solution")
with col_hora:
    st.markdown(
        f"<div class='update-time' style='margin-top:16px'>🕐 Atualizado: "
        f"{datetime.now().strftime('%d/%m/%Y %H:%M')}</div>",
        unsafe_allow_html=True
    )
with col_btn:
    if st.button("🚀", key="refresh"):
        fetch_leads_30dias.clear()
        fetch_leads_80dias.clear()
        fetch_leads_criticos.clear()
        fetch_leads_hoje.clear()
        st.rerun()
with col_user:
    with st.popover(f"👤 {_auth_name}", use_container_width=True):
        st.markdown(
            f"<div style='font-size:13px;color:#7a9cc7;padding:4px 0 10px;'>"
            f"Logado como <strong style='color:#e8eef8;'>{_auth_name}</strong></div>",
            unsafe_allow_html=True,
        )
        _authenticator.logout(location="main")

_watcher_pkl(fetch_leads_30dias, fetch_leads_80dias, fetch_leads_criticos, fetch_leads_hoje)

st.markdown("---")

# ── Loading ────────────────────────────────────────────────────────────────────
loading_ph = st.empty()
_stale = st.session_state.get("_df_curto_stale", True)

if "df_curto" not in st.session_state or _stale:
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

    st.session_state["df_todos_all"] = df_todos.copy()

    if not _is_admin and _auth_user in _USER_ORIGEM:
        _orig = _USER_ORIGEM[_auth_user]
        df_todos = df_todos[df_todos["origem"].str.strip() == _orig]

    st.session_state["df_curto"] = df_todos
    st.session_state["_df_curto_stale"] = False
else:
    loading_ph.empty()
    df_todos = st.session_state["df_curto"]

# ── NAV BAR ───────────────────────────────────────────────────────────────────
_abas = (
    ["🏠 Dashboard", "📊 SDR", "🔥 Comercial", "👤 Por Operador", "📋 Leads Recentes", "🗂️ CRM", "📈 KPIs"]
    if _is_admin else
    ["🏠 Dashboard", "📊 SDR", "🔥 Comercial", "👤 Por Operador", "📈 KPIs"]
)
if "aba_ativa" not in st.session_state and st.session_state.get("_tab_sel") in _abas:
    st.session_state["aba_ativa"] = st.session_state["_tab_sel"]
aba_ativa = st.radio(
    "nav",
    options=_abas,
    horizontal=True,
    label_visibility="collapsed",
    key="aba_ativa",
)
st.session_state["_tab_sel"] = aba_ativa

# ── ABAS ──────────────────────────────────────────────────────────────────────
if "Dashboard" in aba_ativa:
    render_dashboard_home(df_todos)
elif "SDR" in aba_ativa:
    render_visao_geral(df_todos)
elif "Comercial" in aba_ativa:
    render_funil_rt()
elif "Por Operador" in aba_ativa:
    render_detalhamento(df_todos)
elif "Leads Recentes" in aba_ativa:
    render_leads_rt()
elif "CRM" in aba_ativa:
    render_crm()
elif "KPIs" in aba_ativa:
    render_kpis(df_todos)

# ── RODAPÉ ────────────────────────────────────────────────────────────────────
st.markdown("---")
st.markdown(
    "<div style='text-align:center;color:#7a9cc7;font-size:12px;'>"
    "Hoje · atualização manual via botão · demais seções via botão Atualizar · O2 Solution"
    "</div>",
    unsafe_allow_html=True
)
