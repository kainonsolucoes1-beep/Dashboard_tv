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

_SDR_ORIGENS = {"isaac", "julia", "leticia", "rodolfo", "o2 solution", "anny", "emilly", "maria eduarda", "clara", "kauany"}

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
                ("Total Captados",    None,                  "#4f8ef7"),
                ("Agendado",          "Agendado",            "#8b5cf6"),
                ("Proposta Enviada",  "Proposta Enviada",    "#f59e0b"),
                ("Venda Realizada",   "Venda Realizada",     "#22c55e"),
            ]
            _perdidos = int((df_fn["status"] == "Venda não Realizada").sum())

            _labels, _values, _colors = [], [], []
            _total = len(df_fn)
            for _lbl, _st, _cor in _ETAPAS:
                _n = _total if _st is None else int((df_fn["status"] == _st).sum())
                _labels.append(_lbl)
                _values.append(_n)
                _colors.append(_cor)

            _pcts = [round(_v / _total * 100, 1) if _total else 0 for _v in _values]
            _bar_texts = [
                f"{_v}  ({_p}%)" if _i > 0 else str(_v)
                for _i, (_v, _p) in enumerate(zip(_values, _pcts))
            ]

            _max_v = max(_values) or 1
            for _i, (_lbl, _val, _cor, _pct) in enumerate(zip(_labels, _values, _colors, _pcts)):
                _bar_w = int(_val / _max_v * 100)
                _pct_str = f"({_pct}%)" if _i > 0 else ""
                st.markdown(f"""
                <div style="display:flex;align-items:center;gap:14px;margin-bottom:10px;">
                  <div style="min-width:140px;font-size:13px;color:#7a9cc7;font-weight:600;
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

            _fc1, _fc2, _fc3, _fc4 = st.columns(4)
            _tx_ag  = round(_values[1] / _values[0] * 100, 1) if _values[0] else 0
            _tx_prop = round(_values[2] / _values[0] * 100, 1) if _values[0] else 0
            _tx_vnd  = round(_values[3] / _values[0] * 100, 1) if _values[0] else 0
            with _fc1:
                st.metric("Leads Captados", _values[0])
            with _fc2:
                st.metric("Taxa de Agendamento", f"{_tx_ag}%")
            with _fc3:
                st.metric("Taxa de Proposta", f"{_tx_prop}%")
            with _fc4:
                st.metric("Taxa de Conversão", f"{_tx_vnd}%")

            if _perdidos:
                st.markdown(
                    f"<div style='margin-top:10px;font-size:13px;color:#ef4444;'>"
                    f"⚠️ {_perdidos} lead(s) marcado(s) como <b>Venda não Realizada</b> no período."
                    f"</div>",
                    unsafe_allow_html=True,
                )

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
                "Tipo", options=["SDR", "Orgânico"],
                horizontal=True, key="kpi_conv_tipo",
            )

        df_cv = df_todos[
            df_todos["data_obj"].apply(lambda d: d is not None and conv_de <= d <= conv_ate)
        ].copy()
        if conv_tipo == "SDR":
            df_cv = df_cv[df_cv["origem"].apply(lambda o: str(o).lower() in _SDR_ORIGENS)]
        else:
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

            _max_taxa = float(_ops_cv["taxa"].max()) or 1.0

            for _oi, _orow in _ops_cv.iterrows():
                _cor_op = CORES_ORIGEM[_oi % len(CORES_ORIGEM)]
                _bar_w  = int(_orow["taxa"] / _max_taxa * 100)
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

        _fc1_tm, _fc2_tm, _ = st.columns([2, 2, 4])
        with _fc1_tm:
            tempo_de  = st.date_input("📅 De",  value=date.today().replace(day=1),
                                      format="DD/MM/YYYY", key="kpi_tempo_de")
        with _fc2_tm:
            tempo_ate = st.date_input("📅 Até", value=date.today(),
                                      format="DD/MM/YYYY", key="kpi_tempo_ate")

        df_fc = df_todos[
            (df_todos["status"] == "Venda Realizada") &
            (df_todos["data_obj"].apply(lambda d: d is not None and tempo_de <= d <= tempo_ate))
        ].copy()

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

    with st.expander("🗺️ Origem do Lead", expanded=False):
        st.markdown(
            "<div style='color:#7a9cc7;font-size:12px;margin-bottom:14px;'>"
            "Distribuição de todos os leads por operador/origem — volume e eficiência"
            "</div>",
            unsafe_allow_html=True,
        )

        _or1, _or2, _or3 = st.columns([2, 2, 2])
        with _or1:
            orig_de = st.date_input("📅 De",  value=date.today().replace(day=1),
                                    format="DD/MM/YYYY", key="kpi_orig_de")
        with _or2:
            orig_ate = st.date_input("📅 Até", value=date.today(),
                                     format="DD/MM/YYYY", key="kpi_orig_ate")
        with _or3:
            orig_tipo = st.radio("Tipo", options=["Todos", "SDR", "Orgânico"],
                                 horizontal=True, key="kpi_orig_tipo")

        df_or = df_todos[
            df_todos["data_obj"].apply(lambda d: d is not None and orig_de <= d <= orig_ate)
        ].copy()
        if orig_tipo == "SDR":
            df_or = df_or[df_or["origem"].apply(lambda o: str(o).lower() in _SDR_ORIGENS)]
        elif orig_tipo == "Orgânico":
            df_or = df_or[df_or["origem"].apply(lambda o: str(o).lower() not in _SDR_ORIGENS)]

        if df_or.empty:
            st.info("Nenhum lead no período selecionado.")
        else:
            _grp_or = (
                df_or.groupby("origem")
                .agg(
                    leads =("id",     "count"),
                    vendas=("status", lambda x: (x == "Venda Realizada").sum()),
                )
                .reset_index()
            )
            _grp_or["taxa"] = (_grp_or["vendas"] / _grp_or["leads"] * 100).round(2)
            _grp_or["pct_leads"] = (_grp_or["leads"] / _grp_or["leads"].sum() * 100).round(1)
            _grp_or = _grp_or.sort_values("leads", ascending=False).reset_index(drop=True)

            _total_or   = int(_grp_or["leads"].sum())
            _lider_or   = _grp_or.iloc[0]["origem"]
            _maior_conv = _grp_or.loc[_grp_or["taxa"].idxmax(), "origem"]
            _menor_conv = _grp_or.loc[_grp_or["taxa"].idxmin(), "origem"]

            _m1, _m2, _m3, _m4 = st.columns(4)
            with _m1:
                st.markdown(
                    f"<div class='card-status' style='text-align:center;padding:14px 10px;'>"
                    f"<div style='font-size:26px;font-weight:700;color:#4f8ef7;'>{_total_or}</div>"
                    f"<div style='color:#7a9cc7;font-size:11px;text-transform:uppercase;letter-spacing:.6px;margin-top:4px;'>Total de Leads</div>"
                    f"</div>", unsafe_allow_html=True,
                )
            with _m2:
                st.markdown(
                    f"<div class='card-status' style='text-align:center;padding:14px 10px;'>"
                    f"<div style='font-size:16px;font-weight:700;color:#f59e0b;'>{_lider_or}</div>"
                    f"<div style='color:#7a9cc7;font-size:11px;text-transform:uppercase;letter-spacing:.6px;margin-top:4px;'>Maior Volume</div>"
                    f"</div>", unsafe_allow_html=True,
                )
            with _m3:
                st.markdown(
                    f"<div class='card-status' style='text-align:center;padding:14px 10px;'>"
                    f"<div style='font-size:16px;font-weight:700;color:#22c55e;'>{_maior_conv}</div>"
                    f"<div style='color:#7a9cc7;font-size:11px;text-transform:uppercase;letter-spacing:.6px;margin-top:4px;'>Maior Conversão</div>"
                    f"</div>", unsafe_allow_html=True,
                )
            with _m4:
                st.markdown(
                    f"<div class='card-status' style='text-align:center;padding:14px 10px;'>"
                    f"<div style='font-size:16px;font-weight:700;color:#ef4444;'>{_menor_conv}</div>"
                    f"<div style='color:#7a9cc7;font-size:11px;text-transform:uppercase;letter-spacing:.6px;margin-top:4px;'>Menor Conversão</div>"
                    f"</div>", unsafe_allow_html=True,
                )

            st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)

            _max_leads = int(_grp_or["leads"].max()) or 1
            for _oi, _or_row in _grp_or.iterrows():
                _cor_or  = CORES_ORIGEM[_oi % len(CORES_ORIGEM)]
                _bar_vol = int(_or_row["leads"] / _max_leads * 100)
                _taxa_or = _or_row["taxa"]
                _cor_tx  = (
                    "#22c55e" if _taxa_or >= 20 else
                    "#f59e0b" if _taxa_or >= 10 else
                    "#ef4444"
                )
                st.markdown(f"""
                <div style="display:flex;align-items:center;gap:12px;margin-bottom:10px;">
                  <div style="min-width:130px;font-size:13px;font-weight:600;color:{_cor_or};
                              text-align:right;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">
                    {_or_row['origem']}</div>
                  <div style="flex:1;background:#152a4a;border-radius:99px;height:12px;">
                    <div style="background:{_cor_or};border-radius:99px;height:12px;width:{_bar_vol}%;"></div>
                  </div>
                  <div style="min-width:50px;font-size:16px;font-weight:700;color:{_cor_or};">
                    {int(_or_row['leads'])}</div>
                  <div style="min-width:55px;font-size:12px;color:#7a9cc7;">{_or_row['pct_leads']}%</div>
                  <div style="min-width:80px;font-size:13px;font-weight:700;color:{_cor_tx};text-align:right;">
                    {_taxa_or}% conv.</div>
                </div>
                """, unsafe_allow_html=True)
