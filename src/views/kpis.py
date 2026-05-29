import streamlit as st
import pandas as pd
from datetime import date

from src.data.api import fetch_leads_30dias, fetch_leads_criticos
from src.data.transforms import merge_leads_curto
from src.utils.time import dias_uteis_lista
from src.charts.horarios import grafico_horarios_pico


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

        st.session_state["kpi_pico_de"]  = kpi_de
        st.session_state["kpi_pico_ate"] = kpi_ate

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
