import streamlit as st
import pandas as pd
from datetime import date

from src.data.api import fetch_leads_30dias, fetch_leads_criticos
from src.data.transforms import merge_leads_curto
from src.utils.time import dias_uteis_lista
from src.charts.horarios import grafico_horarios_pico
from src.utils.formatters import fmt_brl
from src.ui.modals import modal_leads_status

_SDR_ORIGENS = {"isaac", "julia", "leticia", "rodolfo", "o2 solution", "anny", "emilly"}

CORES_ORIGEM = ["#4f8ef7", "#22c55e", "#f59e0b", "#8b5cf6", "#ef4444", "#f97316", "#06b6d4", "#e879f9"]


def _cards_vendas_por_origem(df_vnd: pd.DataFrame, origens: list, tab_prefix: str = ""):
    if df_vnd.empty or not origens:
        st.info("Nenhuma venda realizada no período.")
        return

    total_geral = len(df_vnd)
    valor_geral = df_vnd["valor_proposta"].sum()
    g1, g2, g3 = st.columns(3)
    with g1:
        st.markdown(
            f"<div class='card-status' style='text-align:center;padding:16px 12px;'>"
            f"<div style='font-size:28px;font-weight:700;color:#22c55e;'>{total_geral}</div>"
            f"<div style='color:#7a9cc7;font-size:12px;text-transform:uppercase;letter-spacing:.6px;margin-top:4px;'>Vendas Realizadas</div>"
            f"</div>",
            unsafe_allow_html=True,
        )
        if st.button("🔍 Ver leads", key=f"{tab_prefix}_btn_vnd_total", use_container_width=True):
            modal_leads_status(df_vnd, "Vendas Realizadas", "#22c55e")
    with g2:
        st.markdown(
            f"<div class='card-status' style='text-align:center;padding:16px 12px;'>"
            f"<div style='font-size:24px;font-weight:700;color:#4f8ef7;'>{fmt_brl(valor_geral)}</div>"
            f"<div style='color:#7a9cc7;font-size:12px;text-transform:uppercase;letter-spacing:.6px;margin-top:4px;'>Valor Total</div>"
            f"</div>",
            unsafe_allow_html=True,
        )
    with g3:
        ticket = valor_geral / total_geral if total_geral else 0
        st.markdown(
            f"<div class='card-status' style='text-align:center;padding:16px 12px;'>"
            f"<div style='font-size:24px;font-weight:700;color:#f59e0b;'>{fmt_brl(ticket)}</div>"
            f"<div style='color:#7a9cc7;font-size:12px;text-transform:uppercase;letter-spacing:.6px;margin-top:4px;'>Ticket Médio</div>"
            f"</div>",
            unsafe_allow_html=True,
        )

    st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)

    chunks = [origens[i:i + 4] for i in range(0, len(origens), 4)]
    for chunk in chunks:
        cols = st.columns(len(chunk))
        for col, (i, op) in zip(cols, [(origens.index(o), o) for o in chunk]):
            cor = CORES_ORIGEM[i % len(CORES_ORIGEM)]
            df_op = df_vnd[df_vnd["origem"] == op]
            qtd = len(df_op)
            val = df_op["valor_proposta"].sum()
            tkt = val / qtd if qtd else 0
            with col:
                st.markdown(
                    f"<div class='card-status' style='border-left:4px solid {cor};'>"
                    f"<div style='font-size:13px;color:#7a9cc7;font-weight:600;text-transform:uppercase;"
                    f"letter-spacing:.6px;margin-bottom:8px;'>{op}</div>"
                    f"<div style='font-size:32px;font-weight:700;color:{cor};line-height:1;'>{qtd}</div>"
                    f"<div style='color:#7a9cc7;font-size:12px;margin-top:3px;'>vendas</div>"
                    f"<div style='margin-top:10px;border-top:1px solid #152a4a;padding-top:8px;'>"
                    f"<div style='color:#7a9cc7;font-size:11px;text-transform:uppercase;letter-spacing:.5px;'>Valor</div>"
                    f"<div style='font-size:18px;font-weight:700;color:#22c55e;'>{fmt_brl(val)}</div>"
                    f"<div style='color:#7a9cc7;font-size:11px;text-transform:uppercase;letter-spacing:.5px;margin-top:6px;'>Ticket Médio</div>"
                    f"<div style='font-size:16px;font-weight:700;color:#f59e0b;'>{fmt_brl(tkt)}</div>"
                    f"</div></div>",
                    unsafe_allow_html=True,
                )
                if st.button("🔍 Ver leads", key=f"{tab_prefix}_btn_vnd_{op}", use_container_width=True):
                    modal_leads_status(df_op, op, cor)


@st.fragment
def render_kpis(df_todos: pd.DataFrame):
    df_todos = st.session_state.get("df_curto", df_todos)

    _hd, _btn = st.columns([5, 1])
    with _hd:
        st.markdown("#### 📈 KPIs")
        st.markdown(
            "<p style='color:#7a9cc7;font-size:13px;margin-top:-4px;'>"
            "Indicadores de performance operacional."
            "</p>",
            unsafe_allow_html=True,
        )
    with _btn:
        st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)
        if st.button("🔄 Atualizar", key="kpis_refresh", use_container_width=True):
            fetch_leads_30dias.clear()
            fetch_leads_criticos.clear()
            df_novo, _ = merge_leads_curto()
            st.session_state["df_curto"] = df_novo
            st.rerun(scope="fragment")

    st.markdown("---")

    with st.expander("⏰ Horário de Pico", expanded=False):
        st.markdown(
            "<div style='color:#7a9cc7;font-size:12px;margin-bottom:14px;'>"
            "Seg–Sex · sem feriados · 09h–18h · top 3 horários destacados"
            "</div>",
            unsafe_allow_html=True,
        )

        _default_de  = date.today().replace(day=1)
        _default_ate = date.today()
        _kpi_de  = st.session_state.get("kpi_pico_de",  _default_de)
        _kpi_ate = st.session_state.get("kpi_pico_ate", _default_ate)

        _fc1, _fc2, _ = st.columns([2, 2, 4])
        with _fc1:
            kpi_de = st.date_input("📅 De", value=_kpi_de, format="DD/MM/YYYY", key="kpi_pico_de")
        with _fc2:
            kpi_ate = st.date_input("📅 Até", value=_kpi_ate, format="DD/MM/YYYY", key="kpi_pico_ate")

        _dias_uteis = set(dias_uteis_lista(kpi_de, kpi_ate))
        df_pico = df_todos[df_todos["data_obj"].apply(
            lambda d: d is not None and d in _dias_uteis
        )]

        if df_pico.empty:
            st.info("Nenhum lead em dias úteis no período selecionado.")
        else:
            _fig_h, _top3_cap, _top3_vnd, _cap_c, _vnd_c = grafico_horarios_pico(df_pico)

            _h1, _h2 = st.columns(2)
            with _h1:
                _pico_cap = sorted(_top3_cap, key=lambda h: _cap_c[h - 9], reverse=True)
                st.markdown(
                    "<div style='font-size:12px;color:#7a9cc7;font-weight:600;text-transform:uppercase;"
                    "letter-spacing:.6px;margin-bottom:8px;'>📌 Top 3 · Capturas</div>"
                    "<div style='display:flex;gap:8px;flex-wrap:wrap;'>"
                    + (
                        "".join(
                            f"<span style='background:#f59e0b22;border:1px solid #f59e0b;border-radius:8px;"
                            f"padding:4px 12px;font-size:14px;color:#f59e0b;font-weight:700;'>"
                            f"{h:02d}h "
                            f"<span style='color:#e8eef8;font-weight:400;font-size:12px;'>({_cap_c[h - 9]} leads)</span>"
                            f"</span>"
                            for h in _pico_cap
                        ) if _pico_cap else "<span style='color:#7a9cc7;font-size:13px;'>—</span>"
                    )
                    + "</div>",
                    unsafe_allow_html=True,
                )
            with _h2:
                _pico_vnd = sorted(_top3_vnd, key=lambda h: _vnd_c[h - 9], reverse=True)
                st.markdown(
                    "<div style='font-size:12px;color:#7a9cc7;font-weight:600;text-transform:uppercase;"
                    "letter-spacing:.6px;margin-bottom:8px;'>💰 Top 3 · Vendas</div>"
                    "<div style='display:flex;gap:8px;flex-wrap:wrap;'>"
                    + (
                        "".join(
                            f"<span style='background:#16a34a22;border:1px solid #16a34a;border-radius:8px;"
                            f"padding:4px 12px;font-size:14px;color:#22c55e;font-weight:700;'>"
                            f"{h:02d}h "
                            f"<span style='color:#e8eef8;font-weight:400;font-size:12px;'>({_vnd_c[h - 9]} vendas)</span>"
                            f"</span>"
                            for h in _pico_vnd
                        ) if _pico_vnd else "<span style='color:#7a9cc7;font-size:13px;'>—</span>"
                    )
                    + "</div>",
                    unsafe_allow_html=True,
                )

            st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)
            st.plotly_chart(_fig_h, use_container_width=True, key="kpis_horarios_pico")

    with st.expander("💰 Vendas Realizadas", expanded=False):
        st.markdown(
            "<div style='color:#7a9cc7;font-size:12px;margin-bottom:14px;'>"
            "Detalhamento de vendas por origem · SDR e demais"
            "</div>",
            unsafe_allow_html=True,
        )

        _vd_de  = st.session_state.get("kpi_venda_de",  date.today().replace(day=1))
        _vd_ate = st.session_state.get("kpi_venda_ate", date.today())

        _vc1, _vc2, _ = st.columns([2, 2, 4])
        with _vc1:
            venda_de = st.date_input("📅 De", value=_vd_de, format="DD/MM/YYYY", key="kpi_venda_de")
        with _vc2:
            venda_ate = st.date_input("📅 Até", value=_vd_ate, format="DD/MM/YYYY", key="kpi_venda_ate")

        df_vnd = df_todos[
            (df_todos["status"] == "Venda Realizada") &
            (df_todos["data_obj"].apply(lambda d: d is not None and venda_de <= d <= venda_ate))
        ].copy()

        todas_origens = sorted(df_vnd["origem"].dropna().unique().tolist())
        sdr_presentes    = [o for o in todas_origens if o.lower() in _SDR_ORIGENS]
        demais_presentes = [o for o in todas_origens if o.lower() not in _SDR_ORIGENS]

        tab_sdr, tab_demais = st.tabs(["👥 SDR", "📋 Demais"])

        with tab_sdr:
            df_sdr = df_vnd[df_vnd["origem"].apply(lambda o: str(o).lower() in _SDR_ORIGENS)]
            _cards_vendas_por_origem(df_sdr, sdr_presentes, tab_prefix="sdr")

        with tab_demais:
            df_demais = df_vnd[df_vnd["origem"].apply(lambda o: str(o).lower() not in _SDR_ORIGENS)]
            _cards_vendas_por_origem(df_demais, demais_presentes, tab_prefix="demais")
