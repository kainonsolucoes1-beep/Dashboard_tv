import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import date, timedelta

from src.data.api import fetch_leads_30dias, fetch_leads_criticos
from src.data.transforms import merge_leads_curto
from src.utils.time import dias_uteis_lista
from src.charts.horarios import grafico_horarios_pico
from src.utils.formatters import fmt_brl
from src.ui.modals import modal_leads_status

_SDR_ORIGENS = {"isaac", "julia", "leticia", "rodolfo", "o2 solution", "anny", "emilly", "emily", "maria eduarda", "clara", "kauany", "discadora", "gabrieli"}

CORES_ORIGEM = ["#4f8ef7", "#22c55e", "#f59e0b", "#8b5cf6", "#ef4444", "#f97316", "#06b6d4", "#e879f9"]

_DDD_ESTADO = {
    "91": "Pará",       "93": "Pará",       "94": "Pará",
    "92": "Amazonas",   "97": "Amazonas",
    "95": "Roraima",    "96": "Amapá",
    "69": "Rondônia",   "68": "Acre",        "63": "Tocantins",
    "82": "Alagoas",
    "71": "Bahia",      "73": "Bahia",       "74": "Bahia",   "75": "Bahia",  "77": "Bahia",
    "85": "Ceará",      "88": "Ceará",
    "98": "Maranhão",   "99": "Maranhão",
    "83": "Paraíba",
    "81": "Pernambuco", "87": "Pernambuco",
    "86": "Piauí",      "89": "Piauí",
    "84": "Rio Grande do Norte",
    "79": "Sergipe",
    "61": "Distrito Federal",
    "62": "Goiás",      "64": "Goiás",
    "65": "Mato Grosso","66": "Mato Grosso",
    "67": "Mato Grosso do Sul",
    "27": "Espírito Santo", "28": "Espírito Santo",
    "31": "Minas Gerais","32": "Minas Gerais","33": "Minas Gerais",
    "34": "Minas Gerais","35": "Minas Gerais","37": "Minas Gerais","38": "Minas Gerais",
    "21": "Rio de Janeiro","22": "Rio de Janeiro","24": "Rio de Janeiro",
    "11": "São Paulo",  "12": "São Paulo",   "13": "São Paulo",
    "14": "São Paulo",  "15": "São Paulo",   "16": "São Paulo",
    "17": "São Paulo",  "18": "São Paulo",   "19": "São Paulo",
    "41": "Paraná",     "42": "Paraná",      "43": "Paraná",
    "44": "Paraná",     "45": "Paraná",      "46": "Paraná",
    "47": "Santa Catarina","48": "Santa Catarina","49": "Santa Catarina",
    "51": "Rio Grande do Sul","53": "Rio Grande do Sul",
    "54": "Rio Grande do Sul","55": "Rio Grande do Sul",
}

_ESTADO_REGIAO = {
    "Pará": "Norte", "Amazonas": "Norte", "Roraima": "Norte",
    "Amapá": "Norte", "Rondônia": "Norte", "Acre": "Norte", "Tocantins": "Norte",
    "Alagoas": "Nordeste", "Bahia": "Nordeste", "Ceará": "Nordeste",
    "Maranhão": "Nordeste", "Paraíba": "Nordeste", "Pernambuco": "Nordeste",
    "Piauí": "Nordeste", "Rio Grande do Norte": "Nordeste", "Sergipe": "Nordeste",
    "Distrito Federal": "Centro-Oeste", "Goiás": "Centro-Oeste",
    "Mato Grosso": "Centro-Oeste", "Mato Grosso do Sul": "Centro-Oeste",
    "Espírito Santo": "Sudeste", "Minas Gerais": "Sudeste",
    "Rio de Janeiro": "Sudeste", "São Paulo": "Sudeste",
    "Paraná": "Sul", "Santa Catarina": "Sul", "Rio Grande do Sul": "Sul",
}

_REGIAO_COR = {
    "Sudeste":      "#4f8ef7",
    "Nordeste":     "#f59e0b",
    "Sul":          "#22c55e",
    "Centro-Oeste": "#8b5cf6",
    "Norte":        "#06b6d4",
}

_ESTADO_UF = {
    "Acre": "AC", "Alagoas": "AL", "Amapá": "AP", "Amazonas": "AM",
    "Bahia": "BA", "Ceará": "CE", "Distrito Federal": "DF",
    "Espírito Santo": "ES", "Goiás": "GO", "Maranhão": "MA",
    "Mato Grosso": "MT", "Mato Grosso do Sul": "MS", "Minas Gerais": "MG",
    "Pará": "PA", "Paraíba": "PB", "Paraná": "PR", "Pernambuco": "PE",
    "Piauí": "PI", "Rio de Janeiro": "RJ", "Rio Grande do Norte": "RN",
    "Rio Grande do Sul": "RS", "Rondônia": "RO", "Roraima": "RR",
    "Santa Catarina": "SC", "São Paulo": "SP", "Sergipe": "SE",
    "Tocantins": "TO",
}


def _extrair_ddd(tel):
    digits = "".join(c for c in str(tel) if c.isdigit())
    if not digits:
        return None
    if digits.startswith("55") and len(digits) >= 12:
        return digits[2:4]
    if len(digits) >= 10:
        return digits[0:2]
    return None


@st.cache_data(ttl=86400 * 7, show_spinner=False)
def _fetch_br_states_geojson():
    try:
        import requests as _req
        r = _req.get(
            "https://raw.githubusercontent.com/giuliano-macedo/geodata-br-states/main/geojson/br_states.json",
            timeout=15,
        )
        if r.status_code == 200:
            return r.json()
    except Exception:
        pass
    return None



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

        _fc1, _fc2, _fc3 = st.columns([2, 2, 2])
        with _fc1:
            kpi_de = st.date_input("📅 De", value=_kpi_de, format="DD/MM/YYYY", key="kpi_pico_de")
        with _fc2:
            kpi_ate = st.date_input("📅 Até", value=_kpi_ate, format="DD/MM/YYYY", key="kpi_pico_ate")
        with _fc3:
            kpi_pico_tipo = st.radio("Tipo", options=["Todos", "SDR", "Orgânico"],
                                     horizontal=True, key="kpi_pico_tipo")

        _dias_uteis = set(dias_uteis_lista(kpi_de, kpi_ate))
        df_pico = df_todos[df_todos["data_obj"].apply(
            lambda d: d is not None and d in _dias_uteis
        )]
        if kpi_pico_tipo == "SDR":
            df_pico = df_pico[df_pico["origem"].apply(lambda o: str(o).lower() in _SDR_ORIGENS)]
        elif kpi_pico_tipo == "Orgânico":
            df_pico = df_pico[df_pico["origem"].apply(lambda o: str(o).lower() not in _SDR_ORIGENS)]

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

            _HORAS_LIST = list(range(9, 19))
            _DIAS_PT    = ["Seg", "Ter", "Qua", "Qui", "Sex"]
            _matrix     = [[0] * len(_HORAS_LIST) for _ in range(5)]
            for _, _pr in df_pico.iterrows():
                try:
                    _ph = int(str(_pr.get("criado_em", "")).split(" ")[1].split(":")[0])
                except (IndexError, ValueError, AttributeError):
                    _ph = None
                _pd = _pr["data_obj"].weekday() if _pr["data_obj"] else None
                if _ph is not None and _pd is not None and 0 <= _pd <= 4 and _ph in _HORAS_LIST:
                    _matrix[_pd][_ph - 9] += 1

            fig_heat = go.Figure(go.Heatmap(
                z=_matrix,
                x=[f"{h:02d}h" for h in _HORAS_LIST],
                y=_DIAS_PT,
                colorscale=[[0, "#0d2137"], [0.5, "#1e4d8c"], [1, "#f59e0b"]],
                hovertemplate="<b>%{y} · %{x}</b><br>%{z} leads<extra></extra>",
                colorbar=dict(
                    title=dict(text="Leads", font=dict(color="#7a9cc7", size=11)),
                    tickfont=dict(color="#7a9cc7", size=10),
                    bgcolor="rgba(0,0,0,0)",
                    len=0.8,
                ),
            ))
            fig_heat.update_layout(
                height=220,
                margin=dict(t=30, b=10, l=10, r=60),
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                xaxis=dict(tickfont=dict(color="#e8eef8", size=11), side="top"),
                yaxis=dict(tickfont=dict(color="#e8eef8", size=11), autorange="reversed"),
            )
            st.markdown(
                "<div style='font-size:12px;color:#7a9cc7;font-weight:600;text-transform:uppercase;"
                "letter-spacing:.6px;margin-top:8px;margin-bottom:4px;'>🔥 Concentração por Dia × Hora</div>",
                unsafe_allow_html=True,
            )
            st.plotly_chart(fig_heat, use_container_width=True, key="kpis_heatmap_pico")

    with st.expander("💰 Vendas Realizadas", expanded=False):
        st.markdown(
            "<div style='color:#7a9cc7;font-size:12px;margin-bottom:14px;'>"
            "Ranking de vendas por operador · delta vs período anterior · acompanhamento de meta"
            "</div>",
            unsafe_allow_html=True,
        )

        _vc1, _vc2, _vc3 = st.columns([2, 2, 2])
        with _vc1:
            venda_de  = st.date_input("📅 De",  value=date.today().replace(day=1),
                                      format="DD/MM/YYYY", key="kpi_venda_de")
        with _vc2:
            venda_ate = st.date_input("📅 Até", value=date.today(),
                                      format="DD/MM/YYYY", key="kpi_venda_ate")
        with _vc3:
            venda_tipo = st.radio("Tipo", options=["Todos", "SDR", "Orgânico"],
                                  horizontal=True, key="kpi_venda_tipo")

        _vm1, _ = st.columns([1, 3])
        with _vm1:
            meta_vendas = st.number_input("🎯 Meta de vendas", min_value=0, value=30, step=1,
                                          key="kpi_meta_vendas")

        df_vnd = df_todos[
            (df_todos["status"] == "Venda Realizada") &
            (df_todos["data_obj"].apply(lambda d: d is not None and venda_de <= d <= venda_ate))
        ].copy()
        if venda_tipo == "SDR":
            df_vnd = df_vnd[df_vnd["origem"].apply(lambda o: str(o).lower() in _SDR_ORIGENS)]
        elif venda_tipo == "Orgânico":
            df_vnd = df_vnd[df_vnd["origem"].apply(lambda o: str(o).lower() not in _SDR_ORIGENS)]

        _periodo_dias = (venda_ate - venda_de).days + 1
        _ant_ate = venda_de - timedelta(days=1)
        _ant_de  = _ant_ate - timedelta(days=_periodo_dias - 1)
        df_vnd_ant = df_todos[
            (df_todos["status"] == "Venda Realizada") &
            (df_todos["data_obj"].apply(lambda d: d is not None and _ant_de <= d <= _ant_ate))
        ].copy()
        if venda_tipo == "SDR":
            df_vnd_ant = df_vnd_ant[df_vnd_ant["origem"].apply(lambda o: str(o).lower() in _SDR_ORIGENS)]
        elif venda_tipo == "Orgânico":
            df_vnd_ant = df_vnd_ant[df_vnd_ant["origem"].apply(lambda o: str(o).lower() not in _SDR_ORIGENS)]

        _total_vnd  = len(df_vnd)
        _total_ant  = len(df_vnd_ant)
        _delta_qtd  = _total_vnd - _total_ant
        _valor_vnd  = df_vnd["valor_proposta"].sum()
        _valor_ant  = df_vnd_ant["valor_proposta"].sum()
        _delta_val  = _valor_vnd - _valor_ant
        _ticket_vnd = _valor_vnd / _total_vnd if _total_vnd else 0
        _meta_pct   = min(100, round(_total_vnd / meta_vendas * 100)) if meta_vendas > 0 else 0
        _meta_cor   = "#22c55e" if _meta_pct >= 100 else "#f59e0b" if _meta_pct >= 70 else "#ef4444"

        def _delta_badge(v, is_money=False):
            if v == 0:
                return "<span style='background:#152a4a;color:#7a9cc7;font-size:10px;padding:2px 7px;border-radius:99px;font-weight:600;'>= ant.</span>"
            _bc  = "#22c55e" if v > 0 else "#ef4444"
            _bbg = "#22c55e22" if v > 0 else "#ef444422"
            _bs  = "▲" if v > 0 else "▼"
            _bt  = fmt_brl(abs(v)) if is_money else str(abs(int(v)))
            return (
                f"<span style='background:{_bbg};color:{_bc};font-size:10px;"
                f"padding:2px 7px;border-radius:99px;font-weight:600;"
                f"border:1px solid {_bc};'>{_bs} {_bt}</span>"
            )

        _g1, _g2, _g3 = st.columns(3)
        with _g1:
            st.markdown(
                f"<div class='card-status' style='text-align:center;padding:14px 10px;'>"
                f"<div style='font-size:28px;font-weight:700;color:#22c55e;'>{_total_vnd}</div>"
                f"<div style='margin-top:5px;'>{_delta_badge(_delta_qtd)}</div>"
                f"<div style='color:#7a9cc7;font-size:11px;text-transform:uppercase;letter-spacing:.6px;margin-top:6px;'>Vendas Realizadas</div>"
                f"</div>", unsafe_allow_html=True,
            )
            if st.button("🔍 Ver leads", key="vnd_btn_total", use_container_width=True):
                modal_leads_status(df_vnd, "Vendas Realizadas", "#22c55e")
        with _g2:
            st.markdown(
                f"<div class='card-status' style='text-align:center;padding:14px 10px;'>"
                f"<div style='font-size:22px;font-weight:700;color:#4f8ef7;'>{fmt_brl(_valor_vnd)}</div>"
                f"<div style='margin-top:5px;'>{_delta_badge(_delta_val, is_money=True)}</div>"
                f"<div style='color:#7a9cc7;font-size:11px;text-transform:uppercase;letter-spacing:.6px;margin-top:6px;'>Valor Total</div>"
                f"</div>", unsafe_allow_html=True,
            )
        with _g3:
            st.markdown(
                f"<div class='card-status' style='text-align:center;padding:14px 10px;'>"
                f"<div style='font-size:22px;font-weight:700;color:#f59e0b;'>{fmt_brl(_ticket_vnd)}</div>"
                f"<div style='color:#7a9cc7;font-size:11px;text-transform:uppercase;letter-spacing:.6px;margin-top:12px;'>Ticket Médio</div>"
                f"</div>", unsafe_allow_html=True,
            )

        st.markdown(
            f"<div style='margin-top:12px;background:#0a1628;border:1px solid #152a4a;"
            f"border-radius:10px;padding:14px 18px;'>"
            f"<div style='display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;'>"
            f"<span style='color:#7a9cc7;font-size:12px;font-weight:600;text-transform:uppercase;"
            f"letter-spacing:.6px;'>🎯 Meta Mensal</span>"
            f"<span style='font-size:20px;font-weight:700;color:{_meta_cor};'>{_meta_pct}%"
            f"<span style='font-size:13px;color:#7a9cc7;font-weight:400;margin-left:6px;'>"
            f"({_total_vnd} / {meta_vendas})</span></span>"
            f"</div>"
            f"<div style='background:#152a4a;border-radius:99px;height:14px;'>"
            f"<div style='background:{_meta_cor};border-radius:99px;height:14px;"
            f"width:{_meta_pct}%;transition:width .4s;'></div>"
            f"</div></div>",
            unsafe_allow_html=True,
        )

        if df_vnd.empty:
            st.info("Nenhuma venda realizada no período selecionado.")
        else:
            st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)
            _ops_vnd = (
                df_vnd.groupby("origem")
                .agg(vendas=("id", "count"), valor=("valor_proposta", "sum"))
                .reset_index()
            )
            _ops_vnd["ticket"] = _ops_vnd.apply(
                lambda r: r["valor"] / r["vendas"] if r["vendas"] > 0 else 0, axis=1
            )
            _ops_vnd = _ops_vnd.sort_values("vendas", ascending=False).reset_index(drop=True)
            _max_vnd = int(_ops_vnd["vendas"].max()) or 1

            for _oi, _vrow in _ops_vnd.iterrows():
                _cor_v = CORES_ORIGEM[_oi % len(CORES_ORIGEM)]
                _bar_v = int(_vrow["vendas"] / _max_vnd * 100)
                _exp_v = (
                    f"👤 {_vrow['origem']}  ·  "
                    f"{int(_vrow['vendas'])} vendas  ·  "
                    f"{fmt_brl(_vrow['valor'])}"
                )
                with st.expander(_exp_v, expanded=False):
                    st.markdown(f"""
                    <div style="background:#0a1628;border:1px solid #152a4a;border-left:4px solid {_cor_v};
                                border-radius:10px;padding:14px 18px;margin-bottom:12px;">
                      <div style="display:flex;align-items:center;gap:24px;flex-wrap:wrap;">
                        <div style="flex:1;min-width:80px;text-align:center;">
                          <div style="font-size:11px;color:#7a9cc7;text-transform:uppercase;letter-spacing:.6px;font-weight:600;">Vendas</div>
                          <div style="font-size:26px;font-weight:700;color:{_cor_v};">{int(_vrow['vendas'])}</div>
                          <div style="margin-top:4px;background:#152a4a;border-radius:99px;height:5px;">
                            <div style="background:{_cor_v};border-radius:99px;height:5px;width:{_bar_v}%;"></div>
                          </div>
                        </div>
                        <div style="flex:1;min-width:100px;text-align:center;">
                          <div style="font-size:11px;color:#7a9cc7;text-transform:uppercase;letter-spacing:.6px;font-weight:600;">Valor Total</div>
                          <div style="font-size:18px;font-weight:700;color:#22c55e;">{fmt_brl(_vrow['valor'])}</div>
                        </div>
                        <div style="flex:1;min-width:100px;text-align:center;">
                          <div style="font-size:11px;color:#7a9cc7;text-transform:uppercase;letter-spacing:.6px;font-weight:600;">Ticket Médio</div>
                          <div style="font-size:18px;font-weight:700;color:#f59e0b;">{fmt_brl(_vrow['ticket'])}</div>
                        </div>
                      </div>
                    </div>
                    """, unsafe_allow_html=True)

                    _df_op_vnd = df_vnd[df_vnd["origem"] == _vrow["origem"]].copy()
                    _df_op_vnd = _df_op_vnd.sort_values("data_obj", ascending=False).reset_index(drop=True)
                    if st.button("🔍 Ver leads", key=f"vnd_btn_{_vrow['origem']}", use_container_width=True):
                        modal_leads_status(_df_op_vnd, _vrow["origem"], _cor_v)
                    _COLS_VND = {
                        "criado_em":      "Data",
                        "nome":           "Cliente",
                        "status":         "Status",
                        "atendente":      "Atendente",
                        "valor_proposta": "Valor (R$)",
                    }
                    _df_vnd_disp = _df_op_vnd[[c for c in _COLS_VND if c in _df_op_vnd.columns]].copy()
                    if "valor_proposta" in _df_vnd_disp.columns:
                        _df_vnd_disp["valor_proposta"] = _df_vnd_disp["valor_proposta"].apply(
                            lambda v: fmt_brl(v) if v > 0 else "—"
                        )
                    _df_vnd_disp = _df_vnd_disp.rename(columns=_COLS_VND)
                    _alt_v = min(400, 40 + len(_df_vnd_disp) * 35)
                    st.dataframe(_df_vnd_disp, use_container_width=True, hide_index=True, height=_alt_v)

    with st.expander("📊 Distribuição por Etapa", expanded=False):
        st.markdown(
            "<div style='color:#7a9cc7;font-size:12px;margin-bottom:14px;'>"
            "Distribuição dos leads por etapa do processo comercial no período selecionado"
            "</div>",
            unsafe_allow_html=True,
        )
        _fn1, _fn2, _ = st.columns([2, 2, 4])
        with _fn1:
            funil_de = st.date_input("📅 De", value=date.today().replace(day=1),
                                     format="DD/MM/YYYY", key="kpi_funil_de")
        with _fn2:
            funil_ate = st.date_input("📅 Até", value=date.today(),
                                      format="DD/MM/YYYY", key="kpi_funil_ate")

        df_fn = df_todos[
            df_todos["data_obj"].apply(lambda d: d is not None and funil_de <= d <= funil_ate)
        ].copy()

        if df_fn.empty:
            st.info("Nenhum lead no período selecionado.")
        else:
            _ETAPAS = [
                ("Total Captados",     None,                    "#4f8ef7"),
                ("Agendado",           "Agendado",              "#8b5cf6"),
                ("Proposta Enviada",   "Proposta Enviada",      "#f59e0b"),
                ("Venda Realizada",    "Venda Realizada",       "#22c55e"),
                ("Venda não Realizada","Venda não Realizada",   "#ef4444"),
            ]

            _labels, _values, _colors = [], [], []
            _total = len(df_fn)
            for _lbl, _st, _cor in _ETAPAS:
                _n = _total if _st is None else int((df_fn["status"] == _st).sum())
                _labels.append(_lbl)
                _values.append(_n)
                _colors.append(_cor)

            _pcts = [round(_v / _total * 100, 1) if _total else 0 for _v in _values]

            _max_v = max(_values) or 1
            for _i, (_lbl, _val, _cor, _pct) in enumerate(zip(_labels, _values, _colors, _pcts)):
                _bar_w = int(_val / _max_v * 100)
                _pct_str = f"({_pct}%)" if _i > 0 else ""
                st.markdown(f"""
                <div style="display:flex;align-items:center;gap:14px;margin-bottom:10px;">
                  <div style="min-width:160px;font-size:13px;color:#7a9cc7;font-weight:600;
                              text-align:right;text-transform:uppercase;letter-spacing:.5px;">{_lbl}</div>
                  <div style="flex:1;background:#152a4a;border-radius:99px;height:14px;">
                    <div style="background:{_cor};border-radius:99px;height:14px;width:{_bar_w}%;
                                transition:width .4s;"></div>
                  </div>
                  <div style="min-width:90px;font-size:18px;font-weight:700;color:{_cor};">
                    {_val} <span style="font-size:13px;color:#7a9cc7;font-weight:400;">{_pct_str}</span>
                  </div>
                </div>
                """, unsafe_allow_html=True)

            _fc1, _fc2, _fc3, _fc4, _fc5 = st.columns(5)
            _tx_ag     = round(_values[1] / _values[0] * 100, 1) if _values[0] else 0
            _tx_prop   = round(_values[2] / _values[0] * 100, 1) if _values[0] else 0
            _tx_vnd    = round(_values[3] / _values[0] * 100, 1) if _values[0] else 0
            _tx_cancel = round(_values[4] / _values[0] * 100, 1) if _values[0] else 0
            with _fc1:
                st.metric("Leads Captados", _values[0])
            with _fc2:
                st.metric("Taxa de Agendamento", f"{_tx_ag}%")
            with _fc3:
                st.metric("Taxa de Proposta", f"{_tx_prop}%")
            with _fc4:
                st.metric("Taxa de Conversão", f"{_tx_vnd}%")
            with _fc5:
                st.metric("Cancelamentos", f"{_values[4]} ({_tx_cancel}%)")

    with st.expander("📡 Origem dos Leads", expanded=False):
        st.markdown(
            "<div style='color:#7a9cc7;font-size:12px;margin-bottom:14px;'>"
            "Volume e conversão por canal de captação — SDR vs Orgânico"
            "</div>",
            unsafe_allow_html=True,
        )

        _og1, _og2 = st.columns([2, 2])
        with _og1:
            orig_de = st.date_input("📅 De", value=date.today().replace(day=1),
                                    format="DD/MM/YYYY", key="kpi_orig_de")
        with _og2:
            orig_ate = st.date_input("📅 Até", value=date.today(),
                                     format="DD/MM/YYYY", key="kpi_orig_ate")

        df_orig = df_todos[
            df_todos["data_obj"].apply(lambda d: d is not None and orig_de <= d <= orig_ate)
        ].copy()

        if df_orig.empty:
            st.info("Nenhum lead no período selecionado.")
        else:
            df_orig["canal"] = df_orig["origem"].apply(
                lambda o: "SDR" if str(o).lower() in _SDR_ORIGENS else "Orgânico"
            )

            _total_orig = len(df_orig)
            _df_sdr = df_orig[df_orig["canal"] == "SDR"]
            _df_org = df_orig[df_orig["canal"] == "Orgânico"]

            _n_sdr   = len(_df_sdr)
            _n_org   = len(_df_org)
            _pct_sdr = round(_n_sdr / _total_orig * 100, 1) if _total_orig else 0
            _pct_org = round(_n_org / _total_orig * 100, 1) if _total_orig else 0

            _vnd_sdr  = int((_df_sdr["status"] == "Venda Realizada").sum())
            _vnd_org  = int((_df_org["status"] == "Venda Realizada").sum())
            _conv_sdr = round(_vnd_sdr / _n_sdr * 100, 1) if _n_sdr else 0
            _conv_org = round(_vnd_org / _n_org * 100, 1) if _n_org else 0

            _cor_conv_sdr = "#22c55e" if _conv_sdr >= 20 else "#f59e0b" if _conv_sdr >= 10 else "#ef4444"
            _cor_conv_org = "#22c55e" if _conv_org >= 20 else "#f59e0b" if _conv_org >= 10 else "#ef4444"

            _oc1, _oc2 = st.columns(2)
            with _oc1:
                st.markdown(
                    f"<div class='card-status' style='border-left:4px solid #4f8ef7;padding:18px;'>"
                    f"<div style='font-size:12px;color:#7a9cc7;font-weight:600;text-transform:uppercase;"
                    f"letter-spacing:.6px;margin-bottom:10px;'>📞 SDR</div>"
                    f"<div style='display:flex;align-items:flex-end;gap:10px;'>"
                    f"<div style='font-size:36px;font-weight:700;color:#4f8ef7;line-height:1;'>{_n_sdr}</div>"
                    f"<div style='font-size:15px;color:#7a9cc7;margin-bottom:4px;'>{_pct_sdr}% do total</div>"
                    f"</div>"
                    f"<div style='margin-top:12px;display:flex;gap:24px;'>"
                    f"<div><div style='font-size:11px;color:#7a9cc7;text-transform:uppercase;letter-spacing:.5px;'>Vendas</div>"
                    f"<div style='font-size:20px;font-weight:700;color:#22c55e;'>{_vnd_sdr}</div></div>"
                    f"<div><div style='font-size:11px;color:#7a9cc7;text-transform:uppercase;letter-spacing:.5px;'>Conversão</div>"
                    f"<div style='font-size:20px;font-weight:700;color:{_cor_conv_sdr};'>{_conv_sdr}%</div></div>"
                    f"</div></div>",
                    unsafe_allow_html=True,
                )
            with _oc2:
                st.markdown(
                    f"<div class='card-status' style='border-left:4px solid #22c55e;padding:18px;'>"
                    f"<div style='font-size:12px;color:#7a9cc7;font-weight:600;text-transform:uppercase;"
                    f"letter-spacing:.6px;margin-bottom:10px;'>🌿 Orgânico</div>"
                    f"<div style='display:flex;align-items:flex-end;gap:10px;'>"
                    f"<div style='font-size:36px;font-weight:700;color:#22c55e;line-height:1;'>{_n_org}</div>"
                    f"<div style='font-size:15px;color:#7a9cc7;margin-bottom:4px;'>{_pct_org}% do total</div>"
                    f"</div>"
                    f"<div style='margin-top:12px;display:flex;gap:24px;'>"
                    f"<div><div style='font-size:11px;color:#7a9cc7;text-transform:uppercase;letter-spacing:.5px;'>Vendas</div>"
                    f"<div style='font-size:20px;font-weight:700;color:#22c55e;'>{_vnd_org}</div></div>"
                    f"<div><div style='font-size:11px;color:#7a9cc7;text-transform:uppercase;letter-spacing:.5px;'>Conversão</div>"
                    f"<div style='font-size:20px;font-weight:700;color:{_cor_conv_org};'>{_conv_org}%</div></div>"
                    f"</div></div>",
                    unsafe_allow_html=True,
                )

            st.markdown(
                f"<div style='margin-top:20px;margin-bottom:8px;'>"
                f"<div style='font-size:11px;color:#7a9cc7;text-transform:uppercase;letter-spacing:.6px;"
                f"font-weight:600;margin-bottom:8px;'>Distribuição do volume</div>"
                f"<div style='display:flex;border-radius:99px;overflow:hidden;height:22px;'>"
                f"<div style='background:#4f8ef7;width:{_pct_sdr}%;display:flex;align-items:center;"
                f"justify-content:center;font-size:11px;font-weight:700;color:#fff;white-space:nowrap;"
                f"overflow:hidden;'>{'SDR ' + str(_pct_sdr) + '%' if _pct_sdr > 8 else ''}</div>"
                f"<div style='background:#22c55e;width:{_pct_org}%;display:flex;align-items:center;"
                f"justify-content:center;font-size:11px;font-weight:700;color:#fff;white-space:nowrap;"
                f"overflow:hidden;'>{'Orgânico ' + str(_pct_org) + '%' if _pct_org > 8 else ''}</div>"
                f"</div></div>",
                unsafe_allow_html=True,
            )


    with st.expander("📅 Leads Tratados por Dia", expanded=False):
        st.markdown(
            "<style>"
            ".kpi-tooltip{position:relative;display:inline-flex;align-items:center;justify-content:center;"
            "width:15px;height:15px;background:#1e3a5f;border:1px solid #4f8ef7;border-radius:50%;"
            "color:#4f8ef7;font-size:10px;font-weight:700;cursor:default;margin-left:6px;vertical-align:middle;}"
            ".kpi-tooltip .kpi-tip{visibility:hidden;opacity:0;width:280px;background:#0d1f35;"
            "color:#c9d8f0;font-size:12px;line-height:1.5;border:1px solid #1e3a5f;border-radius:8px;"
            "padding:10px 12px;position:absolute;left:22px;top:-4px;z-index:999;"
            "transition:opacity .2s;pointer-events:none;}"
            ".kpi-tooltip:hover .kpi-tip{visibility:visible;opacity:1;}"
            "</style>"
            "<div style='color:#7a9cc7;font-size:12px;margin-bottom:14px;display:flex;align-items:center;'>"
            "Leads ativos trabalhados no dia (status ≠ Pendente) — contados pela data de última atualização"
            "<span class='kpi-tooltip'>?"
            "<span class='kpi-tip'>"
            "<strong style='color:#4f8ef7;'>Como ler este indicador</strong><br><br>"
            "Cada barra do gráfico diário mostra quantos leads foram <em>movimentados</em> naquele dia "
            "(ou seja, saíram do status Pendente ou receberam alguma atualização).<br><br>"
            "A seção <strong>Agilidade de Tratamento</strong> mede o tempo entre o lead "
            "<em>entrar no sistema</em> e ser <em>tocado pela equipe</em>:<br>"
            "• <strong style='color:#22c55e;'>Mesmo dia</strong> — tratado no dia em que chegou<br>"
            "• <strong style='color:#f59e0b;'>Até 1 dia</strong> — tratado no dia seguinte<br>"
            "• <strong style='color:#ef4444;'>2+ dias</strong> — ficou parado antes de ser trabalhado"
            "</span></span></div>",
            unsafe_allow_html=True,
        )

        _trat1, _trat2 = st.columns([2, 2])
        with _trat1:
            trat_de = st.date_input("📅 De", value=date.today() - timedelta(days=29),
                                    format="DD/MM/YYYY", key="kpi_trat_de")
        with _trat2:
            trat_ate = st.date_input("📅 Até", value=date.today(),
                                     format="DD/MM/YYYY", key="kpi_trat_ate")

        df_trat = df_todos[
            df_todos["atualizado_obj"].apply(lambda d: d is not None and trat_de <= d <= trat_ate)
            & (df_todos["status"] != "Pendente")
        ].copy()

        if df_trat.empty:
            st.info("Nenhum lead tratado no período selecionado.")
        else:
            contagem = (
                df_trat.groupby("atualizado_obj").size()
                .reset_index(name="qtd")
                .sort_values("atualizado_obj")
            )
            contagem["data_fmt"] = contagem["atualizado_obj"].apply(lambda d: d.strftime("%d/%m"))

            _hoje  = date.today()
            _ontem = _hoje - timedelta(days=1)
            _qtd_hoje  = int(contagem.loc[contagem["atualizado_obj"] == _hoje,  "qtd"].sum())
            _qtd_ontem = int(contagem.loc[contagem["atualizado_obj"] == _ontem, "qtd"].sum())
            _ult7      = contagem[contagem["atualizado_obj"] >= _hoje - timedelta(days=6)]
            _media7    = round(_ult7["qtd"].mean(), 1) if not _ult7.empty else 0.0

            _cor_hoje = "#22c55e" if _qtd_hoje >= _media7 else "#f59e0b" if _qtd_hoje > 0 else "#ef4444"

            _df_pendente = df_todos[df_todos["status"] == "Pendente"]
            _qtd_pend    = len(_df_pendente)

            _tm1, _tm2, _tm3, _tm4 = st.columns(4)
            with _tm1:
                st.markdown(
                    f"<div class='card-status' style='text-align:center;padding:16px 8px;'>"
                    f"<div style='font-size:11px;color:#7a9cc7;text-transform:uppercase;letter-spacing:.6px;'>Hoje</div>"
                    f"<div style='font-size:36px;font-weight:700;color:{_cor_hoje};line-height:1.1;'>{_qtd_hoje}</div>"
                    f"<div style='font-size:12px;color:#7a9cc7;'>leads tratados</div>"
                    f"</div>",
                    unsafe_allow_html=True,
                )
                _df_hoje_trat = df_trat[df_trat["atualizado_obj"] == _hoje]
                if st.button("Ver leads", key="trat_btn_hoje", use_container_width=True):
                    modal_leads_status(_df_hoje_trat, "Tratados Hoje", _cor_hoje)
            with _tm2:
                st.markdown(
                    f"<div class='card-status' style='text-align:center;padding:16px 8px;'>"
                    f"<div style='font-size:11px;color:#7a9cc7;text-transform:uppercase;letter-spacing:.6px;'>Ontem</div>"
                    f"<div style='font-size:36px;font-weight:700;color:#4f8ef7;line-height:1.1;'>{_qtd_ontem}</div>"
                    f"<div style='font-size:12px;color:#7a9cc7;'>leads tratados</div>"
                    f"</div>",
                    unsafe_allow_html=True,
                )
                _df_ontem_trat = df_trat[df_trat["atualizado_obj"] == _ontem]
                if st.button("Ver leads", key="trat_btn_ontem", use_container_width=True):
                    modal_leads_status(_df_ontem_trat, "Tratados Ontem", "#4f8ef7")
            with _tm3:
                st.markdown(
                    f"<div class='card-status' style='text-align:center;padding:16px 8px;border-left:4px solid #ef4444;'>"
                    f"<div style='font-size:11px;color:#7a9cc7;text-transform:uppercase;letter-spacing:.6px;'>Faltam tratar</div>"
                    f"<div style='font-size:36px;font-weight:700;color:#ef4444;line-height:1.1;'>{_qtd_pend}</div>"
                    f"<div style='font-size:12px;color:#7a9cc7;'>em Pendente agora</div>"
                    f"</div>",
                    unsafe_allow_html=True,
                )
                if st.button("Ver leads", key="trat_btn_pend", use_container_width=True):
                    modal_leads_status(_df_pendente, "Faltam Tratar", "#ef4444")
            with _tm4:
                st.markdown(
                    f"<div class='card-status' style='text-align:center;padding:16px 8px;'>"
                    f"<div style='font-size:11px;color:#7a9cc7;text-transform:uppercase;letter-spacing:.6px;'>Média 7 dias</div>"
                    f"<div style='font-size:36px;font-weight:700;color:#8b5cf6;line-height:1.1;'>{_media7}</div>"
                    f"<div style='font-size:12px;color:#7a9cc7;'>por dia</div>"
                    f"</div>",
                    unsafe_allow_html=True,
                )

            _fig_trat = go.Figure()
            _fig_trat.add_trace(go.Bar(
                x=contagem["qtd"],
                y=contagem["data_fmt"],
                orientation="h",
                marker_color="#4f8ef7",
                text=contagem["qtd"],
                textposition="outside",
                hovertemplate="<b>%{y}</b><br>%{x} leads<extra></extra>",
            ))
            _fig_trat.update_layout(
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                font=dict(color="#c9d8f0", family="DM Sans"),
                margin=dict(t=10, b=10, l=0, r=40),
                height=max(220, len(contagem) * 28),
                xaxis=dict(showgrid=True, gridcolor="#152a4a", tickfont=dict(size=11)),
                yaxis=dict(showgrid=False, tickfont=dict(size=11), autorange="reversed"),
                bargap=0.3,
            )
            st.plotly_chart(_fig_trat, use_container_width=True, key="chart_tratados_dia")

            _periodo_dias = (trat_ate - trat_de).days
            _modo_curto   = _periodo_dias <= 3

            if _modo_curto:
                # Modo curto: âncora em data_obj (leads criados no período)
                _df_criados = df_todos[
                    df_todos["data_obj"].apply(lambda d: d is not None and trat_de <= d <= trat_ate)
                ].copy()
                _df_trat_ag    = _df_criados[_df_criados["status"] != "Pendente"].copy()
                _df_pend_curto = _df_criados[_df_criados["status"] == "Pendente"]
                _n_criados     = len(_df_criados)
                _n_trat_curto  = len(_df_trat_ag)
                _n_pend_curto  = len(_df_pend_curto)
                _pct_trat = round(_n_trat_curto / _n_criados * 100) if _n_criados else 0
                _ctx_label = "⚡ Agilidade · leads criados no período"
            else:
                _df_trat_ag   = df_trat.copy()
                _ctx_label    = "⚡ Agilidade de Tratamento"

            st.markdown(
                f"<div style='margin-top:8px;margin-bottom:6px;font-size:11px;color:#7a9cc7;"
                f"text-transform:uppercase;letter-spacing:.6px;font-weight:600;'>"
                f"{_ctx_label}</div>",
                unsafe_allow_html=True,
            )

            if _modo_curto:
                st.markdown(
                    f"<div style='margin-bottom:10px;background:#0a1628;"
                    f"border:1px solid #152a4a;border-radius:10px;padding:12px 16px;"
                    f"display:flex;align-items:center;gap:24px;'>"
                    f"<div style='text-align:center;'>"
                    f"<div style='font-size:11px;color:#7a9cc7;text-transform:uppercase;letter-spacing:.5px;'>Criados</div>"
                    f"<div style='font-size:28px;font-weight:700;color:#c9d8f0;line-height:1.1;'>{_n_criados}</div>"
                    f"</div>"
                    f"<div style='width:1px;background:#152a4a;align-self:stretch;'></div>"
                    f"<div style='text-align:center;'>"
                    f"<div style='font-size:11px;color:#7a9cc7;text-transform:uppercase;letter-spacing:.5px;'>Já tratados</div>"
                    f"<div style='font-size:28px;font-weight:700;color:#22c55e;line-height:1.1;'>{_n_trat_curto} <span style='font-size:14px;color:#22c55e;'>({_pct_trat}%)</span></div>"
                    f"</div>"
                    f"<div style='width:1px;background:#152a4a;align-self:stretch;'></div>"
                    f"<div style='text-align:center;'>"
                    f"<div style='font-size:11px;color:#7a9cc7;text-transform:uppercase;letter-spacing:.5px;'>Ainda pendentes</div>"
                    f"<div style='font-size:28px;font-weight:700;color:#ef4444;line-height:1.1;'>{_n_pend_curto}</div>"
                    f"</div>"
                    f"</div>",
                    unsafe_allow_html=True,
                )

            _df_trat_ag["_dias"] = (
                pd.to_datetime(_df_trat_ag["atualizado_obj"]) -
                pd.to_datetime(_df_trat_ag["data_obj"])
            ).dt.days.fillna(999).astype(int)

            _ag_mesmo  = _df_trat_ag[_df_trat_ag["_dias"] == 0]
            _ag_um     = _df_trat_ag[_df_trat_ag["_dias"] == 1]
            _ag_atraso = _df_trat_ag[_df_trat_ag["_dias"] >= 2]
            _ag_total  = len(_df_trat_ag)

            def _pct(n): return round(n / _ag_total * 100, 1) if _ag_total else 0

            _ag_labels = ["Mesmo dia", "Até 1 dia", "2+ dias"]
            _ag_vals   = [len(_ag_mesmo), len(_ag_um), len(_ag_atraso)]
            _ag_cores  = ["#22c55e", "#f59e0b", "#ef4444"]
            _ag_pcts   = [_pct(v) for v in _ag_vals]
            _ag_texts  = [f"{v}  ({p}%)" for v, p in zip(_ag_vals, _ag_pcts)]

            _fig_ag = go.Figure()
            _fig_ag.add_trace(go.Bar(
                x=_ag_vals,
                y=_ag_labels,
                orientation="h",
                marker_color=_ag_cores,
                text=_ag_texts,
                textposition="outside",
                hovertemplate="<b>%{y}</b><br>%{x} leads<extra></extra>",
            ))
            _fig_ag.update_layout(
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                font=dict(color="#c9d8f0", family="DM Sans"),
                margin=dict(t=8, b=8, l=0, r=80),
                height=160,
                xaxis=dict(showgrid=True, gridcolor="#152a4a", tickfont=dict(size=11)),
                yaxis=dict(showgrid=False, tickfont=dict(size=12, color="#c9d8f0")),
                bargap=0.35,
            )
            st.plotly_chart(_fig_ag, use_container_width=True, key="chart_agilidade")

    with st.expander("🔄 Jornada do Lead", expanded=False):
        st.markdown(
            "<div style='color:#7a9cc7;font-size:12px;margin-bottom:14px;'>"
            "Progressão e tempo médio por estágio — baseado nos leads criados no período"
            "</div>",
            unsafe_allow_html=True,
        )

        _jd1, _jd2 = st.columns([2, 2])
        with _jd1:
            jorn_de = st.date_input("📅 De", value=date.today().replace(day=1),
                                    format="DD/MM/YYYY", key="kpi_jorn_de")
        with _jd2:
            jorn_ate = st.date_input("📅 Até", value=date.today(),
                                     format="DD/MM/YYYY", key="kpi_jorn_ate")

        df_jorn = df_todos[
            df_todos["data_obj"].apply(lambda d: d is not None and jorn_de <= d <= jorn_ate)
        ].copy()

        if df_jorn.empty:
            st.info("Nenhum lead criado no período selecionado.")
        else:
            df_jorn["_dias"] = (
                pd.to_datetime(df_jorn["atualizado_obj"]) -
                pd.to_datetime(df_jorn["data_obj"])
            ).dt.days.fillna(0).astype(int)

            _JORNADA = [
                ("Captados",         None,                   "#4f8ef7"),
                ("Agendado",         "Agendado",             "#8b5cf6"),
                ("Proposta Enviada", "Proposta Enviada",     "#f59e0b"),
                ("Venda Realizada",  "Venda Realizada",      "#22c55e"),
            ]

            _total_jorn = len(df_jorn)
            _jcols = st.columns(len(_JORNADA))
            _prev_n = _total_jorn

            for _ji, (_jlabel, _jstatus, _jcor) in enumerate(_JORNADA):
                _df_e = df_jorn if _jstatus is None else df_jorn[df_jorn["status"] == _jstatus]
                _jn   = len(_df_e)
                _jpct_total = round(_jn / _total_jorn * 100, 1) if _total_jorn else 0
                _jpct_prev  = round(_jn / _prev_n  * 100, 1) if _prev_n else 0
                _javg = round(_df_e["_dias"].mean(), 1) if _jstatus and not _df_e.empty else None

                _dias_html = (
                    f"<div style='margin-top:10px;font-size:14px;color:#7a9cc7;'>⏱ {_javg} dias em média</div>"
                    if _javg is not None else ""
                )
                _prev_html = (
                    f"<div style='font-size:14px;color:{_jcor};margin-top:6px;font-weight:700;'>"
                    f"↓ {_jpct_prev}% do anterior</div>"
                    if _ji > 0 else ""
                )

                with _jcols[_ji]:
                    st.markdown(
                        f"<div class='card-status' style='border-left:4px solid {_jcor};"
                        f"text-align:center;padding:20px 12px;min-height:180px;"
                        f"display:flex;flex-direction:column;justify-content:space-between;'>"
                        f"<div style='font-size:12px;color:#7a9cc7;text-transform:uppercase;"
                        f"letter-spacing:.7px;margin-bottom:8px;font-weight:600;'>{_jlabel}</div>"
                        f"<div style='font-size:44px;font-weight:700;color:{_jcor};line-height:1.1;'>{_jn}</div>"
                        f"<div style='font-size:14px;color:#c9d8f0;margin-top:4px;'>{_jpct_total}% do total</div>"
                        f"{_prev_html}{_dias_html}"
                        f"</div>",
                        unsafe_allow_html=True,
                    )
                if _jstatus is not None:
                    _prev_n = _jn

            # Venda não Realizada — saída do funil
            _df_vnr  = df_jorn[df_jorn["status"] == "Venda não Realizada"]
            _jn_vnr  = len(_df_vnr)
            _pct_vnr = round(_jn_vnr / _total_jorn * 100, 1) if _total_jorn else 0
            _avg_vnr = round(_df_vnr["_dias"].mean(), 1) if not _df_vnr.empty else None
            _tempo_vnr_html = (
                "<div style='display:flex;gap:24px;justify-content:center;margin-top:10px;'>"
                "<div><div style='font-size:12px;color:#7a9cc7;'>% do total</div>"
                "<div style='font-size:22px;font-weight:700;color:#ef4444;'>" + str(_pct_vnr) + "%</div></div>"
                "<div style='width:1px;background:#1e3a5f;align-self:stretch;'></div>"
                "<div><div style='font-size:12px;color:#7a9cc7;'>Tempo médio</div>"
                "<div style='font-size:22px;font-weight:700;color:#ef4444;'>" + str(_avg_vnr) + " dias</div></div>"
                "</div>"
            ) if _avg_vnr is not None else (
                "<div style='margin-top:10px;'>"
                "<div style='font-size:12px;color:#7a9cc7;'>% do total</div>"
                "<div style='font-size:22px;font-weight:700;color:#ef4444;'>" + str(_pct_vnr) + "%</div>"
                "</div>"
            )
            st.markdown(
                f"<div style='margin-top:14px;border-top:1px dashed #1e3a5f;padding-top:14px;'>"
                f"<div style='font-size:11px;color:#7a9cc7;text-transform:uppercase;"
                f"letter-spacing:.7px;font-weight:600;margin-bottom:8px;'>↳ Saída do funil</div>"
                f"<div class='card-status' style='border-left:4px solid #ef4444;"
                f"text-align:center;padding:20px 12px;min-height:180px;"
                f"display:flex;flex-direction:column;justify-content:space-between;'>"
                f"<div style='font-size:12px;color:#7a9cc7;text-transform:uppercase;"
                f"letter-spacing:.7px;font-weight:600;'>Venda não Realizada</div>"
                f"<div style='font-size:44px;font-weight:700;color:#ef4444;line-height:1.1;'>{_jn_vnr}</div>"
                f"{_tempo_vnr_html}"
                f"</div></div>",
                unsafe_allow_html=True,
            )

            st.markdown(
                "<div style='margin-top:16px;margin-bottom:4px;font-size:11px;color:#7a9cc7;"
                "text-transform:uppercase;letter-spacing:.6px;font-weight:600;'>"
                "⏱ Tempo médio até cada estágio</div>",
                unsafe_allow_html=True,
            )

            _jbar_labels, _jbar_vals, _jbar_cores = [], [], []
            for _jlabel, _jstatus, _jcor in _JORNADA:
                if _jstatus is None:
                    continue
                _df_e = df_jorn[df_jorn["status"] == _jstatus]
                _jbar_labels.append(_jlabel)
                _jbar_cores.append(_jcor)
                _jbar_vals.append(round(_df_e["_dias"].mean(), 1) if not _df_e.empty else 0)
            # Adiciona Venda não Realizada ao gráfico de tempo
            _jbar_labels.append("Venda não Realizada")
            _jbar_cores.append("#ef4444")
            _jbar_vals.append(round(_df_vnr["_dias"].mean(), 1) if not _df_vnr.empty else 0)

            _fig_jorn = go.Figure()
            _fig_jorn.add_trace(go.Bar(
                x=_jbar_vals,
                y=_jbar_labels,
                orientation="h",
                marker_color=_jbar_cores,
                text=[f"{v} dias" for v in _jbar_vals],
                textposition="outside",
                hovertemplate="<b>%{y}</b><br>%{x} dias em média<extra></extra>",
            ))
            _fig_jorn.update_layout(
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                font=dict(color="#c9d8f0", family="DM Sans"),
                margin=dict(t=8, b=8, l=0, r=80),
                height=190,
                xaxis=dict(showgrid=True, gridcolor="#152a4a", tickfont=dict(size=11),
                           ticksuffix=" d", title=None),
                yaxis=dict(showgrid=False, tickfont=dict(size=12, color="#c9d8f0")),
                bargap=0.35,
            )
            st.plotly_chart(_fig_jorn, use_container_width=True, key="chart_jornada")

    with st.expander("📊 Taxa de Conversão por Operador", expanded=False):
        st.markdown(
            "<div style='color:#7a9cc7;font-size:12px;margin-bottom:14px;'>"
            "Eficiência individual — leads captados vs vendas realizadas por operador"
            "</div>",
            unsafe_allow_html=True,
        )
        _op1, _op2, _op3 = st.columns([2, 2, 2])
        with _op1:
            conv_de = st.date_input("📅 De", value=date.today().replace(day=1),
                                    format="DD/MM/YYYY", key="kpi_conv_de")
        with _op2:
            conv_ate = st.date_input("📅 Até", value=date.today(),
                                     format="DD/MM/YYYY", key="kpi_conv_ate")
        with _op3:
            conv_tipo = st.radio(
                "Tipo", options=["Todos", "SDR", "Orgânico"],
                horizontal=True, key="kpi_conv_tipo",
            )

        df_cv = df_todos[
            df_todos["data_obj"].apply(lambda d: d is not None and conv_de <= d <= conv_ate)
        ].copy()
        if conv_tipo == "SDR":
            df_cv = df_cv[df_cv["origem"].apply(lambda o: str(o).lower() in _SDR_ORIGENS)]
        elif conv_tipo == "Orgânico":
            df_cv = df_cv[df_cv["origem"].apply(lambda o: str(o).lower() not in _SDR_ORIGENS)]

        if df_cv.empty:
            st.info("Nenhum lead no período selecionado.")
        else:
            _ops_cv = (
                df_cv.groupby("origem")
                .agg(
                    leads   =("id",            "count"),
                    vendas  =("status",        lambda x: (x == "Venda Realizada").sum()),
                    valor   =("valor_proposta", "sum"),
                )
                .reset_index()
            )
            _ops_cv["taxa"]   = (_ops_cv["vendas"] / _ops_cv["leads"] * 100).round(2)
            _ops_cv["ticket"] = _ops_cv.apply(
                lambda r: r["valor"] / r["vendas"] if r["vendas"] > 0 else 0, axis=1
            )
            _ops_cv = _ops_cv.sort_values("taxa", ascending=False).reset_index(drop=True)

            _total_leads_cv = int(_ops_cv["leads"].sum()) or 1
            _max_leads_cv   = int(_ops_cv["leads"].max()) or 1
            _ops_cv["pct_leads"] = (_ops_cv["leads"] / _total_leads_cv * 100).round(1)
            _max_taxa = float(_ops_cv["taxa"].max()) or 1.0

            for _oi, _orow in _ops_cv.iterrows():
                _cor_op   = CORES_ORIGEM[_oi % len(CORES_ORIGEM)]
                _bar_w    = int(_orow["taxa"] / _max_taxa * 100)
                _bar_vol  = int(_orow["leads"] / _max_leads_cv * 100)
                _taxa_cor = (
                    "#22c55e" if _orow["taxa"] >= 20 else
                    "#f59e0b" if _orow["taxa"] >= 10 else
                    "#ef4444"
                )
                _exp_op = (
                    f"👤 {_orow['origem']}  ·  "
                    f"{int(_orow['leads'])} leads  ·  "
                    f"{int(_orow['vendas'])} vendas  ·  "
                    f"{_orow['taxa']}% conversão"
                )
                with st.expander(_exp_op, expanded=False):
                    st.markdown(f"""
                    <div style="background:#0a1628;border:1px solid #152a4a;border-left:4px solid {_cor_op};
                                border-radius:10px;padding:14px 18px;margin-bottom:12px;">
                      <div style="display:flex;align-items:center;gap:24px;flex-wrap:wrap;">
                        <div style="flex:1;min-width:80px;text-align:center;">
                          <div style="font-size:11px;color:#7a9cc7;text-transform:uppercase;letter-spacing:.6px;font-weight:600;">Leads</div>
                          <div style="font-size:22px;font-weight:700;color:#e8eef8;">{int(_orow['leads'])}</div>
                          <div style="font-size:11px;color:#7a9cc7;margin-top:2px;">{_orow['pct_leads']}% do total</div>
                          <div style="margin-top:4px;background:#152a4a;border-radius:99px;height:5px;">
                            <div style="background:{_cor_op};border-radius:99px;height:5px;width:{_bar_vol}%;"></div>
                          </div>
                        </div>
                        <div style="flex:1;min-width:80px;text-align:center;">
                          <div style="font-size:11px;color:#7a9cc7;text-transform:uppercase;letter-spacing:.6px;font-weight:600;">Vendas</div>
                          <div style="font-size:22px;font-weight:700;color:#22c55e;">{int(_orow['vendas'])}</div>
                        </div>
                        <div style="flex:1;min-width:100px;text-align:center;">
                          <div style="font-size:11px;color:#7a9cc7;text-transform:uppercase;letter-spacing:.6px;font-weight:600;">Conversão</div>
                          <div style="font-size:26px;font-weight:700;color:{_taxa_cor};">{_orow['taxa']}%</div>
                          <div style="margin-top:4px;background:#152a4a;border-radius:99px;height:5px;">
                            <div style="background:{_taxa_cor};border-radius:99px;height:5px;width:{_bar_w}%;"></div>
                          </div>
                        </div>
                        <div style="flex:1;min-width:100px;text-align:center;">
                          <div style="font-size:11px;color:#7a9cc7;text-transform:uppercase;letter-spacing:.6px;font-weight:600;">Valor Total</div>
                          <div style="font-size:16px;font-weight:700;color:#f59e0b;">{fmt_brl(_orow['valor'])}</div>
                        </div>
                        <div style="flex:1;min-width:100px;text-align:center;">
                          <div style="font-size:11px;color:#7a9cc7;text-transform:uppercase;letter-spacing:.6px;font-weight:600;">Ticket Médio</div>
                          <div style="font-size:16px;font-weight:700;color:#4f8ef7;">{fmt_brl(_orow['ticket'])}</div>
                        </div>
                      </div>
                    </div>
                    """, unsafe_allow_html=True)

                    _df_op_leads = df_cv[df_cv["origem"] == _orow["origem"]].copy()
                    _df_op_leads = _df_op_leads.sort_values("data_obj", ascending=False).reset_index(drop=True)

                    st.markdown("##### 📋 Leads do período")
                    _COLS_OP = {
                        "criado_em":      "Data",
                        "nome":           "Cliente",
                        "status":         "Status",
                        "atendente":      "Atendente",
                        "valor_proposta": "Valor (R$)",
                        "perception":     "Temperatura",
                    }
                    _df_op_disp = _df_op_leads[[c for c in _COLS_OP if c in _df_op_leads.columns]].copy()
                    _df_op_disp["valor_proposta"] = _df_op_leads["valor_proposta"].apply(
                        lambda v: fmt_brl(v) if v > 0 else "—"
                    )
                    _df_op_disp = _df_op_disp.rename(columns=_COLS_OP)
                    _alt = min(500, 40 + len(_df_op_disp) * 35)
                    st.dataframe(_df_op_disp, use_container_width=True, hide_index=True, height=_alt)

    with st.expander("🚨 Leads em Atraso por Operador", expanded=False):
        st.markdown(
            "<div style='color:#7a9cc7;font-size:12px;margin-bottom:14px;'>"
            "Leads sem resposta em tempo útil — distribuição por operador"
            "</div>",
            unsafe_allow_html=True,
        )

        if "em_atraso" not in df_todos.columns:
            st.info("Campo 'em_atraso' não disponível nos dados.")
        else:
            df_at = df_todos[df_todos["em_atraso"] == True].copy()

            if df_at.empty:
                st.success("✅ Nenhum lead em atraso no momento.")
            else:
                _total_op  = df_todos.groupby("origem")["id"].count().rename("total")
                _atraso_op = df_at.groupby("origem")["id"].count().rename("em_atraso")
                _grp_at = pd.concat([_total_op, _atraso_op], axis=1).fillna(0)
                _grp_at = _grp_at[_grp_at["em_atraso"] > 0].reset_index()
                _grp_at["em_atraso"] = _grp_at["em_atraso"].astype(int)
                _grp_at["total"]     = _grp_at["total"].astype(int)
                _grp_at["pct"]       = (_grp_at["em_atraso"] / _grp_at["total"] * 100).round(1)
                _grp_at = _grp_at.sort_values("em_atraso", ascending=False).reset_index(drop=True)

                _at_max = int(_grp_at["em_atraso"].max()) or 1

                st.markdown(
                    f"<div style='font-size:26px;font-weight:700;color:#ef4444;text-align:center;"
                    f"margin-bottom:16px;'>🚨 {len(df_at)} leads em atraso</div>",
                    unsafe_allow_html=True,
                )

                for _ai, _ar in _grp_at.iterrows():
                    _bar_w_at = int(_ar["em_atraso"] / _at_max * 100)
                    with st.expander(
                        f"👤 {_ar['origem']}  ·  {_ar['em_atraso']} em atraso  ·  {_ar['pct']}% da carteira",
                        expanded=False,
                    ):
                        st.markdown(f"""
                        <div style="display:flex;align-items:center;gap:14px;margin-bottom:12px;">
                          <div style="flex:1;background:#152a4a;border-radius:99px;height:10px;">
                            <div style="background:#ef4444;border-radius:99px;height:10px;width:{_bar_w_at}%;"></div>
                          </div>
                          <div style="font-size:18px;font-weight:700;color:#ef4444;">{_ar['em_atraso']}</div>
                          <div style="font-size:13px;color:#7a9cc7;">/ {_ar['total']} leads ({_ar['pct']}%)</div>
                        </div>
                        """, unsafe_allow_html=True)

                        _df_at_op = df_at[df_at["origem"] == _ar["origem"]].copy()
                        _df_at_op = _df_at_op.sort_values("data_obj", ascending=False).reset_index(drop=True)
                        _COLS_AT = {
                            "nome":          "Cliente",
                            "status":        "Status",
                            "atualizado_em": "Última Atualização",
                            "atendente":     "Atendente",
                            "base":          "Base",
                        }
                        _df_at_disp = _df_at_op[[c for c in _COLS_AT if c in _df_at_op.columns]].copy()
                        _df_at_disp = _df_at_disp.rename(columns=_COLS_AT)
                        _alt_at = min(400, 40 + len(_df_at_disp) * 35)
                        st.dataframe(_df_at_disp, use_container_width=True, hide_index=True, height=_alt_at)

    with st.expander("⏱️ Tempo Médio de Fechamento", expanded=False):
        st.markdown(
            "<div style='color:#7a9cc7;font-size:12px;margin-bottom:14px;'>"
            "Dias médios entre captação e venda realizada — por operador"
            "</div>",
            unsafe_allow_html=True,
        )

        _fc1_tm, _fc2_tm, _fc3_tm = st.columns([2, 2, 2])
        with _fc1_tm:
            tempo_de  = st.date_input("📅 De",  value=date.today().replace(day=1),
                                      format="DD/MM/YYYY", key="kpi_tempo_de")
        with _fc2_tm:
            tempo_ate = st.date_input("📅 Até", value=date.today(),
                                      format="DD/MM/YYYY", key="kpi_tempo_ate")
        with _fc3_tm:
            tempo_tipo = st.radio("Tipo", options=["Todos", "SDR", "Orgânico"],
                                  horizontal=True, key="kpi_tempo_tipo")

        df_fc = df_todos[
            (df_todos["status"] == "Venda Realizada") &
            (df_todos["data_obj"].apply(lambda d: d is not None and tempo_de <= d <= tempo_ate))
        ].copy()
        if tempo_tipo == "SDR":
            df_fc = df_fc[df_fc["origem"].apply(lambda o: str(o).lower() in _SDR_ORIGENS)]
        elif tempo_tipo == "Orgânico":
            df_fc = df_fc[df_fc["origem"].apply(lambda o: str(o).lower() not in _SDR_ORIGENS)]

        if df_fc.empty:
            st.info("Nenhuma venda realizada no período selecionado.")
        else:
            df_fc["_upd"] = pd.to_datetime(df_fc["atualizado_em"], format="%d/%m/%Y %H:%M", errors="coerce")
            df_fc["dias"] = df_fc.apply(
                lambda r: (r["_upd"].date() - r["data_obj"]).days
                if pd.notna(r["_upd"]) and r["data_obj"] is not None else None,
                axis=1,
            )
            df_fc = df_fc.dropna(subset=["dias"])
            df_fc["dias"] = df_fc["dias"].astype(int).clip(lower=0)

            if df_fc.empty:
                st.info("Dados insuficientes para calcular tempo médio.")
            else:
                _media_geral = round(float(df_fc["dias"].mean()), 1)
                st.markdown(
                    f"<div style='font-size:22px;font-weight:700;color:#4f8ef7;text-align:center;"
                    f"margin-bottom:16px;'>⏱️ Média geral: "
                    f"<span style='color:#f59e0b;'>{_media_geral} dias</span></div>",
                    unsafe_allow_html=True,
                )

                _grp_tm = (
                    df_fc.groupby("origem")["dias"]
                    .agg(["mean", "min", "max", "count"])
                    .reset_index()
                    .rename(columns={"mean": "media", "min": "minimo", "max": "maximo", "count": "vendas"})
                )
                _grp_tm["media"] = _grp_tm["media"].round(1)
                _grp_tm = _grp_tm.sort_values("media").reset_index(drop=True)
                _max_med = float(_grp_tm["media"].max()) or 1.0

                for _ti, _tr in _grp_tm.iterrows():
                    _cor_tm = (
                        "#22c55e" if _tr["media"] <= 3 else
                        "#f59e0b" if _tr["media"] <= 7 else
                        "#ef4444"
                    )
                    _bar_w_tm = int(_tr["media"] / _max_med * 100)
                    st.markdown(f"""
                    <div style="display:flex;align-items:center;gap:14px;margin-bottom:10px;">
                      <div style="min-width:140px;font-size:13px;color:#7a9cc7;font-weight:600;text-align:right;">
                        {_tr['origem']}</div>
                      <div style="flex:1;background:#152a4a;border-radius:99px;height:12px;">
                        <div style="background:{_cor_tm};border-radius:99px;height:12px;width:{_bar_w_tm}%;"></div>
                      </div>
                      <div style="min-width:60px;font-size:17px;font-weight:700;color:{_cor_tm};">{_tr['media']}d</div>
                      <div style="min-width:150px;font-size:12px;color:#7a9cc7;">
                        {int(_tr['vendas'])} vendas · {int(_tr['minimo'])}–{int(_tr['maximo'])} dias
                      </div>
                    </div>
                    """, unsafe_allow_html=True)

    with st.expander("📈 Evolução Semanal de Conversão", expanded=False):
        st.markdown(
            "<div style='color:#7a9cc7;font-size:12px;margin-bottom:14px;'>"
            "Taxa de conversão semana a semana — leads captados vs vendas realizadas"
            "</div>",
            unsafe_allow_html=True,
        )

        _ec1, _ec2, _ec3 = st.columns([2, 2, 2])
        with _ec1:
            ev_de = st.date_input("📅 De",  value=date.today().replace(day=1),
                                   format="DD/MM/YYYY", key="kpi_ev_de")
        with _ec2:
            ev_ate = st.date_input("📅 Até", value=date.today(),
                                    format="DD/MM/YYYY", key="kpi_ev_ate")
        with _ec3:
            ev_tipo = st.radio("Tipo", options=["Todos", "SDR", "Orgânico"],
                               horizontal=True, key="kpi_ev_tipo")

        df_ev = df_todos[
            df_todos["data_obj"].apply(lambda d: d is not None and ev_de <= d <= ev_ate)
        ].copy()
        if ev_tipo == "SDR":
            df_ev = df_ev[df_ev["origem"].apply(lambda o: str(o).lower() in _SDR_ORIGENS)]
        elif ev_tipo == "Orgânico":
            df_ev = df_ev[df_ev["origem"].apply(lambda o: str(o).lower() not in _SDR_ORIGENS)]

        if df_ev.empty:
            st.info("Nenhum lead no período selecionado.")
        else:
            df_ev["semana_inicio"] = df_ev["data_obj"].apply(
                lambda d: d - timedelta(days=d.weekday())
            )
            _grp_ev = (
                df_ev.groupby("semana_inicio")
                .agg(
                    leads =("id",     "count"),
                    vendas=("status", lambda x: (x == "Venda Realizada").sum()),
                )
                .reset_index()
                .sort_values("semana_inicio")
            )
            _grp_ev["taxa"]  = (_grp_ev["vendas"] / _grp_ev["leads"] * 100).round(2)
            _grp_ev["label"] = _grp_ev["semana_inicio"].apply(lambda d: f"Sem {d.strftime('%d/%m')}")

            fig_ev = go.Figure()
            fig_ev.add_trace(go.Bar(
                name="Leads captados",
                x=_grp_ev["label"],
                y=_grp_ev["leads"],
                marker_color="#4f8ef7",
                opacity=0.55,
                yaxis="y",
                hovertemplate="<b>%{x}</b><br>%{y} leads<extra></extra>",
            ))
            fig_ev.add_trace(go.Scatter(
                name="Conversão (%)",
                x=_grp_ev["label"],
                y=_grp_ev["taxa"],
                mode="lines+markers+text",
                line=dict(color="#22c55e", width=2),
                marker=dict(size=8, color="#22c55e"),
                text=[f"{v}%" for v in _grp_ev["taxa"]],
                textposition="top center",
                textfont=dict(color="#22c55e", size=11),
                yaxis="y2",
                hovertemplate="<b>%{x}</b><br>%{y:.2f}% conversão<extra></extra>",
            ))
            fig_ev.update_layout(
                height=320,
                margin=dict(t=30, b=20, l=10, r=60),
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                legend=dict(orientation="h", y=1.14, x=0, font=dict(color="#e8eef8", size=12)),
                xaxis=dict(showgrid=False, color="#7a9cc7", tickfont=dict(color="#e8eef8", size=11)),
                yaxis=dict(
                    title="Leads", showgrid=True, gridcolor="#152a4a",
                    tickfont=dict(color="#4f8ef7", size=11), zeroline=False,
                ),
                yaxis2=dict(
                    title="Conversão (%)", overlaying="y", side="right",
                    showgrid=False, tickfont=dict(color="#22c55e", size=11), zeroline=False,
                ),
                hovermode="x unified",
            )
            st.plotly_chart(fig_ev, use_container_width=True, key="kpis_evolucao_semanal")

            _grp_ev_disp = _grp_ev[["label", "leads", "vendas", "taxa"]].rename(columns={
                "label": "Semana", "leads": "Leads", "vendas": "Vendas", "taxa": "Conversão (%)",
            })
            st.dataframe(_grp_ev_disp, use_container_width=True, hide_index=True)

    with st.expander("🗺️ Região dos Leads", expanded=False):
        st.markdown(
            "<div style='color:#7a9cc7;font-size:12px;margin-bottom:14px;'>"
            "Distribuição geográfica por DDD — captações e vendas por estado e região"
            "</div>",
            unsafe_allow_html=True,
        )

        _rg1, _rg2, _rg3, _rg4 = st.columns([2, 2, 2, 2])
        with _rg1:
            reg_de = st.date_input("📅 De",  value=date.today().replace(day=1),
                                   format="DD/MM/YYYY", key="kpi_reg_de")
        with _rg2:
            reg_ate = st.date_input("📅 Até", value=date.today(),
                                    format="DD/MM/YYYY", key="kpi_reg_ate")
        with _rg3:
            reg_tipo = st.radio("Tipo", options=["Todos", "SDR", "Orgânico"],
                                horizontal=True, key="kpi_reg_tipo")
        with _rg4:
            reg_metrica = st.radio("Exibir", options=["Captações", "Vendas"],
                                   horizontal=True, key="kpi_reg_metrica")

        df_rg = df_todos[
            df_todos["data_obj"].apply(lambda d: d is not None and reg_de <= d <= reg_ate)
        ].copy()
        if reg_tipo == "SDR":
            df_rg = df_rg[df_rg["origem"].apply(lambda o: str(o).lower() in _SDR_ORIGENS)]
        elif reg_tipo == "Orgânico":
            df_rg = df_rg[df_rg["origem"].apply(lambda o: str(o).lower() not in _SDR_ORIGENS)]
        if reg_metrica == "Vendas":
            df_rg = df_rg[df_rg["status"] == "Venda Realizada"]

        if df_rg.empty:
            st.info("Nenhum lead no período selecionado.")
        else:
            df_rg["ddd"]    = df_rg["telefone"].apply(_extrair_ddd)
            df_rg["estado"] = df_rg["ddd"].apply(lambda d: _DDD_ESTADO.get(d))
            df_rg["regiao"] = df_rg["estado"].apply(lambda e: _ESTADO_REGIAO.get(e, "Não identificado") if e else "Não identificado")
            df_rg["uf"]     = df_rg["estado"].apply(lambda e: _ESTADO_UF.get(e) if e else None)

            _identificados = df_rg[df_rg["regiao"] != "Não identificado"]
            _nao_id        = int((df_rg["regiao"] == "Não identificado").sum())
            _total_rg      = len(df_rg)

            if _identificados.empty:
                st.warning("Nenhum DDD identificado nos telefones do período.")
            else:
                _grp_reg = (
                    _identificados.groupby("regiao")
                    .agg(qtd=("id", "count"))
                    .reset_index()
                    .sort_values("qtd", ascending=False)
                    .reset_index(drop=True)
                )
                _max_reg = int(_grp_reg["qtd"].max()) or 1

                _top_reg = _grp_reg.iloc[0]["regiao"]
                _m1r, _m2r, _m3r = st.columns(3)
                with _m1r:
                    st.markdown(
                        f"<div class='card-status' style='text-align:center;padding:14px 10px;'>"
                        f"<div style='font-size:26px;font-weight:700;color:#4f8ef7;'>{len(_identificados)}</div>"
                        f"<div style='color:#7a9cc7;font-size:11px;text-transform:uppercase;letter-spacing:.6px;margin-top:4px;'>"
                        f"{'Leads' if reg_metrica == 'Captações' else 'Vendas'} identificados</div>"
                        f"</div>", unsafe_allow_html=True,
                    )
                with _m2r:
                    _cor_top = _REGIAO_COR.get(_top_reg, "#7a9cc7")
                    st.markdown(
                        f"<div class='card-status' style='text-align:center;padding:14px 10px;'>"
                        f"<div style='font-size:16px;font-weight:700;color:{_cor_top};'>{_top_reg}</div>"
                        f"<div style='color:#7a9cc7;font-size:11px;text-transform:uppercase;letter-spacing:.6px;margin-top:4px;'>Região líder</div>"
                        f"</div>", unsafe_allow_html=True,
                    )
                with _m3r:
                    st.markdown(
                        f"<div class='card-status' style='text-align:center;padding:14px 10px;'>"
                        f"<div style='font-size:26px;font-weight:700;color:#7a9cc7;'>{_nao_id}</div>"
                        f"<div style='color:#7a9cc7;font-size:11px;text-transform:uppercase;letter-spacing:.6px;margin-top:4px;'>Sem DDD identificado</div>"
                        f"</div>", unsafe_allow_html=True,
                    )

                st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)

                _geo = _fetch_br_states_geojson()
                if _geo:
                    _grp_uf = (
                        _identificados[_identificados["uf"].notna()]
                        .groupby(["estado", "uf"])
                        .agg(qtd=("id", "count"))
                        .reset_index()
                    )
                    if not _grp_uf.empty:
                        _label_mapa = "leads" if reg_metrica == "Captações" else "vendas"
                        fig_mapa = go.Figure(go.Choropleth(
                            geojson=_geo,
                            locations=_grp_uf["uf"].tolist(),
                            z=_grp_uf["qtd"].tolist(),
                            featureidkey="id",
                            colorscale=[[0, "#0d2137"], [0.5, "#1e4d8c"], [1, "#4f8ef7"]],
                            text=_grp_uf.apply(
                                lambda r: f"{r['estado']} ({r['uf']})", axis=1
                            ).tolist(),
                            hovertemplate="<b>%{text}</b><br>%{z} " + _label_mapa + "<extra></extra>",
                            marker_line_color="#0a1628",
                            marker_line_width=0.8,
                            colorbar=dict(
                                title=dict(text=_label_mapa.capitalize(), font=dict(color="#7a9cc7", size=11)),
                                tickfont=dict(color="#7a9cc7", size=10),
                                bgcolor="rgba(0,0,0,0)",
                                len=0.6,
                            ),
                        ))
                        fig_mapa.update_geos(
                            fitbounds="locations",
                            visible=False,
                            bgcolor="rgba(0,0,0,0)",
                        )
                        fig_mapa.update_layout(
                            height=420,
                            margin=dict(t=0, b=0, l=0, r=0),
                            paper_bgcolor="rgba(0,0,0,0)",
                            geo=dict(bgcolor="rgba(0,0,0,0)"),
                        )
                        st.plotly_chart(fig_mapa, use_container_width=True, key="kpis_mapa_regiao")

                for _, _rrow in _grp_reg.iterrows():
                    _reg     = _rrow["regiao"]
                    _qtd_reg = int(_rrow["qtd"])
                    _pct_reg = round(_qtd_reg / len(_identificados) * 100, 1)
                    _cor_reg = _REGIAO_COR.get(_reg, "#7a9cc7")
                    _bar_reg = int(_qtd_reg / _max_reg * 100)

                    _df_estados = (
                        _identificados[_identificados["regiao"] == _reg]
                        .groupby("estado")
                        .agg(qtd=("id", "count"))
                        .reset_index()
                        .sort_values("qtd", ascending=False)
                    )

                    with st.expander(
                        f"📍 {_reg}  ·  {_qtd_reg} {'leads' if reg_metrica == 'Captações' else 'vendas'}  ·  {_pct_reg}% do total",
                        expanded=False,
                    ):
                        st.markdown(f"""
                        <div style="display:flex;align-items:center;gap:14px;margin-bottom:14px;">
                          <div style="flex:1;background:#152a4a;border-radius:99px;height:10px;">
                            <div style="background:{_cor_reg};border-radius:99px;height:10px;width:{_bar_reg}%;"></div>
                          </div>
                          <div style="font-size:18px;font-weight:700;color:{_cor_reg};">{_qtd_reg}</div>
                          <div style="font-size:13px;color:#7a9cc7;">({_pct_reg}%)</div>
                        </div>
                        """, unsafe_allow_html=True)

                        _max_est = int(_df_estados["qtd"].max()) or 1
                        for _, _erow in _df_estados.iterrows():
                            _bar_est = int(_erow["qtd"] / _max_est * 100)
                            _pct_est = round(_erow["qtd"] / _qtd_reg * 100, 1)
                            st.markdown(f"""
                            <div style="display:flex;align-items:center;gap:12px;margin-bottom:8px;">
                              <div style="min-width:160px;font-size:13px;color:#7a9cc7;text-align:right;">{_erow['estado']}</div>
                              <div style="flex:1;background:#152a4a;border-radius:99px;height:8px;">
                                <div style="background:{_cor_reg};opacity:.7;border-radius:99px;height:8px;width:{_bar_est}%;"></div>
                              </div>
                              <div style="min-width:40px;font-size:14px;font-weight:700;color:#e8eef8;">{int(_erow['qtd'])}</div>
                              <div style="min-width:50px;font-size:12px;color:#7a9cc7;">{_pct_est}%</div>
                            </div>
                            """, unsafe_allow_html=True)

