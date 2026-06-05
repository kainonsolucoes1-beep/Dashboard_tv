import streamlit as st
import pandas as pd
from datetime import date, timedelta

from src.data.api import fetch_leads_30dias, fetch_leads_hoje, fetch_leads_criticos, STATUS_MAP
from src.data.transforms import merge_leads_curto
from src.utils.formatters import fmt_brl
from src.ui.cards import linhas_por_operador, render_card
from src.ui.modals import modal_leads_status
from src.charts.rosca import grafico_rosca
from src.charts.origens import grafico_origens
from src.views.fragments import render_hoje_rt


@st.fragment
def render_visao_geral(df_todos: pd.DataFrame):
    df_todos = st.session_state.get("df_curto", df_todos)

    _SDR_NOMES_VG = {"isaac", "julia", "leticia", "rodolfo", "o2 solution", "anny", "emilly", "emily", "maria eduarda", "clara", "kauany", "discadora", "gabrieli"}

    origens_disp = sorted(df_todos["origem"].dropna().unique().tolist())

    _default_de  = date.today() - timedelta(days=30)
    _default_ate = date.today()

    selecionados  = [o for o in st.session_state.get("_fv_origem", origens_disp) if o in origens_disp] or origens_disp
    filtro_status = st.session_state.get("_fv_status",  "Todos")
    filtro_grupo  = st.session_state.get("_fv_grupo",   "Todos")
    data_de       = st.session_state.get("_fv_de",      _default_de)
    data_ate      = st.session_state.get("_fv_ate",     _default_ate)

    with st.expander("🔎 Filtros da Aba", expanded=False):
        with st.form("filtros_visao", border=False):
            _grupo_idx = ["Todos", "SDR", "Orgânico"].index(filtro_grupo) if filtro_grupo in ["Todos", "SDR", "Orgânico"] else 0
            _w_grupo = st.radio(
                "👥 Grupo de Origem", options=["Todos", "SDR", "Orgânico"],
                index=_grupo_idx, horizontal=True, key="visao_grupo",
            )
            st.markdown("<div style='margin-bottom:4px'></div>", unsafe_allow_html=True)
            col_op, col_st, col_de, col_ate, col_btn_f = st.columns([3, 2, 1.5, 1.5, 1])
            with col_op:
                _w_orig = st.multiselect(
                    "👤 Origem individual", options=origens_disp, default=selecionados, key="visao_origem"
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
                filtro_grupo  = _w_grupo
                data_de       = _w_de
                data_ate      = _w_ate
                st.session_state["_fv_origem"] = selecionados
                st.session_state["_fv_status"] = filtro_status
                st.session_state["_fv_grupo"]  = filtro_grupo
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
    if filtro_grupo == "SDR":
        df = df[df["origem"].apply(lambda o: str(o).lower() in _SDR_NOMES_VG)]
    elif filtro_grupo == "Orgânico":
        df = df[df["origem"].apply(lambda o: str(o).lower() not in _SDR_NOMES_VG)]
    elif selecionados:
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
    col_g1, col_g2 = st.columns(2)
    with col_g1:
        st.markdown("#### 🍩 Distribuição por Status")
        st.plotly_chart(grafico_rosca(df), use_container_width=True, key="rosca_visao")
    with col_g2:
        st.markdown("#### 🏆 Ranking por Operador (Vendas)")
        st.plotly_chart(grafico_origens(df), use_container_width=True, key="origens_visao")
