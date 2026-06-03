import calendar
from datetime import date

import pandas as pd
import streamlit as st

from src.charts.rosca import grafico_rosca
from src.utils.formatters import fmt_brl
from src.utils.time import dias_uteis_lista


_SDR_NOMES = {
    "isaac", "julia", "leticia", "rodolfo", "o2 solution", "anny",
    "emilly", "emily", "maria eduarda", "clara", "kauany", "discadora", "gabrieli",
}


@st.fragment
def render_dashboard_home(df_todos: pd.DataFrame):
    df_todos = st.session_state.get("df_curto", df_todos)
    hoje = date.today()

    # ── Filtro SDR / Orgânico + Data ──────────────────────────────────────────
    _grupo  = st.session_state.get("_dash_grupo", "Todos")
    _de_val = st.session_state.get("_dash_de",  hoje.replace(day=1))
    _ate_val = st.session_state.get("_dash_ate", hoje)

    _grupo_label = "" if _grupo == "Todos" else f" · {_grupo}"
    _data_label  = f" · {_de_val.strftime('%d/%m')} – {_ate_val.strftime('%d/%m')}"
    with st.expander(f"🔎 Filtros{_grupo_label}{_data_label}", expanded=False):
        _col_g, _col_de, _col_ate, _col_btn = st.columns([3, 2, 2, 1])
        with _col_g:
            _novo_grupo = st.radio(
                "Grupo",
                options=["Todos", "SDR", "Orgânico"],
                index=["Todos", "SDR", "Orgânico"].index(_grupo),
                horizontal=True,
                label_visibility="collapsed",
                key="dash_grupo_radio",
            )
        with _col_de:
            _novo_de = st.date_input("De", value=_de_val, format="DD/MM/YYYY", key="dash_de")
        with _col_ate:
            _novo_ate = st.date_input("Até", value=_ate_val, format="DD/MM/YYYY", key="dash_ate")
        with _col_btn:
            st.markdown("<div style='margin-top:24px'>", unsafe_allow_html=True)
            if st.button("✔ Aplicar", key="dash_aplicar", use_container_width=True):
                st.session_state["_dash_grupo"] = _novo_grupo
                st.session_state["_dash_de"]    = _novo_de
                st.session_state["_dash_ate"]   = _novo_ate
                st.rerun(scope="fragment")
            st.markdown("</div>", unsafe_allow_html=True)

    if _grupo == "SDR":
        df_todos = df_todos[df_todos["origem"].apply(lambda o: str(o).lower() in _SDR_NOMES)]
    elif _grupo == "Orgânico":
        df_todos = df_todos[df_todos["origem"].apply(lambda o: str(o).lower() not in _SDR_NOMES)]

    df_todos = df_todos[
        df_todos["data_obj"].apply(lambda d: d is not None and _de_val <= d <= _ate_val)
    ]

    # ── Dados base ────────────────────────────────────────────────────────────
    df_hoje = df_todos[
        df_todos["data_obj"].apply(lambda d: d is not None and d == hoje)
    ]
    df_mes = df_todos

    _STATUS_ATIVOS = {"Pendente", "Agendado", "Proposta Enviada", "Aguardando Pagamento"}
    df_carteira = df_todos[df_todos["status"].isin(_STATUS_ATIVOS)]
    valor_carteira = df_carteira["valor_proposta"].sum()

    df_com_valor = df_todos[df_todos["valor_proposta"] > 0]
    ticket_medio = df_com_valor["valor_proposta"].mean() if len(df_com_valor) > 0 else 0.0

    # ── 4 KPI cards ───────────────────────────────────────────────────────────
    _periodo_label = f"{_de_val.strftime('%d/%m')} – {_ate_val.strftime('%d/%m')}"
    _kpis = [
        ("📥", str(len(df_hoje)),         "Leads Captados Hoje",              "#4f8ef7"),
        ("📅", str(len(df_mes)),           f"Leads no Período · {_periodo_label}", "#8b5cf6"),
        ("💰", fmt_brl(valor_carteira),    "Valor em Carteira",                "#22c55e"),
        ("🎯", fmt_brl(ticket_medio),      "Ticket Médio",                     "#f59e0b"),
    ]
    _kcols = st.columns(4)
    for _col, (icone, valor, label, cor) in zip(_kcols, _kpis):
        with _col:
            st.markdown(f"""
            <div class="card-status" style="border-top:4px solid {cor};border-left:none;
                        text-align:center;padding:16px 12px;">
                <div style="font-size:22px;margin-bottom:6px;">{icone}</div>
                <div style="font-size:32px;font-weight:700;color:{cor};line-height:1;">{valor}</div>
                <div style="font-size:12px;color:#7a9cc7;margin-top:8px;font-weight:500;">{label}</div>
            </div>
            """, unsafe_allow_html=True)

    st.markdown('<div style="height:28px"></div>', unsafe_allow_html=True)

    # ── Rosca + Meta / Projeção ───────────────────────────────────────────────
    col_rosca, col_meta = st.columns([6, 4])

    with col_rosca:
        st.markdown("#### 🍩 Distribuição por Status")
        _STATUS_ROSCA = {"Pendente", "Agendado", "Proposta Enviada"}
        df_rosca = df_todos[df_todos["status"].isin(_STATUS_ROSCA)]
        if not df_rosca.empty:
            st.plotly_chart(grafico_rosca(df_rosca), use_container_width=True, key="rosca_dash")
        else:
            st.info("Sem leads com esses status no período.")

    with col_meta:
        _meta = st.session_state.get("_meta_mensal", 100)
        with st.expander("⚙️ Meta mensal", expanded=False):
            _nova_meta = st.number_input(
                "Leads / mês", min_value=1, value=_meta, step=5, key="meta_input"
            )
            if st.button("💾 Salvar meta", key="btn_salvar_meta", use_container_width=True):
                st.session_state["_meta_mensal"] = int(_nova_meta)
                st.rerun(scope="fragment")

        _leads_mes = len(df_mes)
        _pct_meta = min(int(_leads_mes / max(_meta, 1) * 100), 100)
        _cor_prog = "#22c55e" if _leads_mes >= _meta else ("#f59e0b" if _pct_meta >= 70 else "#ef4444")

        st.markdown(f"""
        <div class="card-status" style="border-left:4px solid #4f8ef7;margin-bottom:12px;padding:14px 16px;">
            <div style="font-size:12px;font-weight:700;color:#e8eef8;
                        border-bottom:1px solid #152a4a;padding-bottom:6px;margin-bottom:10px;">🎯 Meta Mensal</div>
            <div style="display:flex;justify-content:space-between;align-items:baseline;margin-bottom:8px;">
                <div style="font-size:32px;font-weight:700;color:{_cor_prog};line-height:1;">{_leads_mes}</div>
                <div style="font-size:14px;color:#7a9cc7;">/ {_meta} leads</div>
            </div>
            <div style="background:#152a4a;border-radius:4px;height:7px;overflow:hidden;">
                <div style="background:{_cor_prog};width:{_pct_meta}%;height:100%;border-radius:4px;"></div>
            </div>
            <div style="font-size:11px;color:#7a9cc7;margin-top:6px;">{_pct_meta}% da meta atingida</div>
        </div>
        """, unsafe_allow_html=True)

        # Projeção — usa o período do filtro como janela
        _primeiro_dia = _de_val
        _ultimo_dia   = _ate_val
        _du_totais    = len(dias_uteis_lista(_primeiro_dia, _ultimo_dia))
        _du_passados  = max(len(dias_uteis_lista(_primeiro_dia, hoje)), 1)
        _projecao = int((_leads_mes / _du_passados) * _du_totais)
        _pct_proj = min(int(_projecao / max(_meta, 1) * 100), 999)
        _cor_proj = "#22c55e" if _projecao >= _meta else "#f59e0b"
        _proj_label = "✅ Acima da meta" if _projecao >= _meta else f"⚠️ {_pct_proj}% da meta projetada"

        st.markdown(f"""
        <div class="card-status" style="border-left:4px solid {_cor_proj};padding:14px 16px;">
            <div style="font-size:12px;font-weight:700;color:#e8eef8;
                        border-bottom:1px solid #152a4a;padding-bottom:6px;margin-bottom:10px;">📈 Projeção do Mês</div>
            <div style="font-size:32px;font-weight:700;color:{_cor_proj};line-height:1;margin-bottom:8px;">{_projecao}</div>
            <div style="font-size:11px;color:#7a9cc7;">Base: {_leads_mes} leads · {_du_passados}/{_du_totais} dias úteis</div>
            <div style="font-size:12px;color:{_cor_proj};margin-top:5px;font-weight:600;">{_proj_label}</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown('<div style="height:28px"></div>', unsafe_allow_html=True)

    # ── Ranking do mês ────────────────────────────────────────────────────────
    st.markdown("#### 🏆 Ranking de Captação — Mês Atual")

    if df_mes.empty:
        st.info("Sem leads captados no mês atual.")
        return

    _rank = (
        df_mes.groupby("origem")
        .agg(
            leads=("id", "count"),
            vendas=("status", lambda x: (x == "Venda Realizada").sum()),
            valor=("valor_proposta", "sum"),
        )
        .reset_index()
        .sort_values("leads", ascending=False)
        .reset_index(drop=True)
    )
    _rank["conversao"] = (_rank["vendas"] / _rank["leads"].clip(lower=1) * 100).round(1)

    _medals = ["🥇", "🥈", "🥉"]
    _rows = ""
    for i, row in _rank.iterrows():
        _pos = _medals[i] if i < 3 else f"#{i + 1}"
        _conv = row["conversao"]
        _conv_cor = "#22c55e" if _conv >= 30 else ("#f59e0b" if _conv >= 15 else "#ef4444")
        _rows += (
            '<tr style="border-bottom:1px solid #152a4a;">'
            f'<td style="padding:14px 16px;font-size:22px;text-align:center;">{_pos}</td>'
            f'<td style="padding:14px 16px;color:#e8eef8;font-weight:600;font-size:15px;">&#128100; {row["origem"]}</td>'
            f'<td style="padding:14px 16px;color:#4f8ef7;font-weight:700;font-size:22px;text-align:center;">{row["leads"]}</td>'
            f'<td style="padding:14px 16px;color:#22c55e;font-weight:700;font-size:18px;text-align:center;">{int(row["vendas"])}</td>'
            f'<td style="padding:14px 16px;color:{_conv_cor};font-weight:700;font-size:15px;text-align:center;">{_conv}%</td>'
            f'<td style="padding:14px 16px;color:#f59e0b;font-weight:600;font-size:14px;text-align:right;">{fmt_brl(row["valor"])}</td>'
            "</tr>"
        )

    _table_html = (
        '<div class="card-status" style="padding:0;overflow:hidden;">'
        '<table style="width:100%;border-collapse:collapse;">'
        "<thead>"
        '<tr style="background:#0d1f38;border-bottom:2px solid #152a4a;">'
        '<th style="padding:10px 16px;color:#7a9cc7;font-size:11px;text-transform:uppercase;letter-spacing:.7px;text-align:center;width:60px;">Pos</th>'
        '<th style="padding:10px 16px;color:#7a9cc7;font-size:11px;text-transform:uppercase;letter-spacing:.7px;text-align:left;">Operador</th>'
        '<th style="padding:10px 16px;color:#7a9cc7;font-size:11px;text-transform:uppercase;letter-spacing:.7px;text-align:center;">Leads</th>'
        '<th style="padding:10px 16px;color:#7a9cc7;font-size:11px;text-transform:uppercase;letter-spacing:.7px;text-align:center;">Vendas</th>'
        '<th style="padding:10px 16px;color:#7a9cc7;font-size:11px;text-transform:uppercase;letter-spacing:.7px;text-align:center;">Convers&#227;o</th>'
        '<th style="padding:10px 16px;color:#7a9cc7;font-size:11px;text-transform:uppercase;letter-spacing:.7px;text-align:right;">Carteira</th>'
        "</tr>"
        "</thead>"
        f"<tbody>{_rows}</tbody>"
        "</table></div>"
    )
    st.markdown(_table_html, unsafe_allow_html=True)
