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
    st.markdown("#### 💰 Pipeline · Equipe Comercial")
    st.markdown("<div style='color:#7a9cc7;font-size:12px;margin-top:-10px;margin-bottom:16px;'>Leads contados pela <strong>última atualização</strong> — inclui leads antigos ainda em negociação</div>", unsafe_allow_html=True)

    _ATENDENTES = ["Giovanna", "Rayanna"]
    _base_at = st.session_state.get("df_funil", df_todos)

    _ec_default_days = 80 if "df_funil" in st.session_state else 30
    _ec_default_de   = date.today() - timedelta(days=_ec_default_days)
    _ec_default_ate  = date.today()
    ec_de      = st.session_state.get("ec_de",     _ec_default_de)
    ec_ate     = st.session_state.get("ec_ate",    _ec_default_ate)

    _origens_disp_ec = sorted(df_todos["origem"].dropna().unique().tolist())
    ec_origens = st.session_state.get("ec_origens", _origens_disp_ec)
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
