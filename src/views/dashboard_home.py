import calendar
from datetime import date

import pandas as pd
import streamlit as st

from src.charts.rosca import grafico_rosca, grafico_rosca_bases
from src.data.aliases import load_base_aliases, apply_base_aliases
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

    # ── Filtro ────────────────────────────────────────────────────────────────
    _grupo   = st.session_state.get("_dash_grupo", "Todos")
    _de_val  = st.session_state.get("_dash_de",  hoje.replace(day=1))
    _ate_val = st.session_state.get("_dash_ate", hoje)

    _grupo_label = "" if _grupo == "Todos" else f" · {_grupo}"
    _data_label  = f" · {_de_val.strftime('%d/%m')} – {_ate_val.strftime('%d/%m')}"
    with st.expander(f"🔎 Filtros{_grupo_label}{_data_label}", expanded=False):
        _col_g, _col_de, _col_ate, _col_btn = st.columns([3, 2, 2, 1])
        with _col_g:
            _novo_grupo = st.radio(
                "Grupo", options=["Todos", "SDR", "Orgânico"],
                index=["Todos", "SDR", "Orgânico"].index(_grupo),
                horizontal=True, label_visibility="collapsed", key="dash_grupo_radio",
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

    # ── Métricas base ─────────────────────────────────────────────────────────
    df_hoje = df_todos[df_todos["data_obj"].apply(lambda d: d is not None and d == hoje)]
    _leads_mes = len(df_todos)

    _STATUS_ATIVOS = {"Pendente", "Agendado", "Proposta Enviada", "Aguardando Pagamento"}
    valor_carteira = df_todos[df_todos["status"].isin(_STATUS_ATIVOS)]["valor_proposta"].sum()

    df_com_valor = df_todos[df_todos["valor_proposta"] > 0]
    ticket_medio = df_com_valor["valor_proposta"].mean() if len(df_com_valor) > 0 else 0.0

    _meta = st.session_state.get("_meta_mensal", 100)
    _pct_meta = min(int(_leads_mes / max(_meta, 1) * 100), 100)
    _cor_prog = "#22c55e" if _leads_mes >= _meta else ("#f59e0b" if _pct_meta >= 70 else "#ef4444")

    # Projeção sempre sobre o mês corrente completo (independe do filtro de data)
    _primeiro_dia_mes = hoje.replace(day=1)
    _ultimo_dia_mes   = date(hoje.year, hoje.month, calendar.monthrange(hoje.year, hoje.month)[1])
    _du_totais   = len(dias_uteis_lista(_primeiro_dia_mes, _ultimo_dia_mes))
    _du_passados = max(len(dias_uteis_lista(_primeiro_dia_mes, hoje)), 1)
    _projecao    = int((_leads_mes / _du_passados) * _du_totais)
    _pct_proj    = min(int(_projecao / max(_meta, 1) * 100), 999)
    _cor_proj    = "#22c55e" if _projecao >= _meta else "#f59e0b"
    _proj_sub    = "Acima da meta" if _projecao >= _meta else f"{_pct_proj}% da meta"

    _periodo_label = f"{_de_val.strftime('%d/%m')} – {_ate_val.strftime('%d/%m')}"

    # ── Linha 1: 4 KPI cards ──────────────────────────────────────────────────
    _kpis = [
        ("Leads Captados Hoje",                 str(len(df_hoje)),      "📥", "#4f8ef7"),
        (f"Leads no Período · {_periodo_label}", str(_leads_mes),       "📅", "#8b5cf6"),
        ("Valor em Carteira",                    fmt_brl(valor_carteira),"💰", "#22c55e"),
        ("Ticket Médio",                         fmt_brl(ticket_medio),  "🎯", "#f59e0b"),
    ]
    _kcols = st.columns(4)
    for _col, (label, valor, icone, cor) in zip(_kcols, _kpis):
        with _col:
            st.markdown(f"""
            <div class="card-status" style="padding:12px 16px;">
                <div style="font-size:12px;color:#7a9cc7;font-weight:500;
                            text-transform:uppercase;letter-spacing:.5px;margin-bottom:10px;">{label}</div>
                <div style="font-size:36px;font-weight:700;color:{cor};line-height:1;">{valor}</div>
            </div>
            """, unsafe_allow_html=True)

    st.markdown('<div style="height:24px"></div>', unsafe_allow_html=True)

    # ── Linha 2: Rosca (esq) + Meta / Projeção (dir) ─────────────────────────
    col_rosca, col_cards = st.columns([6, 4])

    with col_rosca:
        _meta_diaria = max(round(_meta / max(_du_totais, 1)), 1)
        _leads_hoje  = len(df_hoje)
        _pct_hoje    = round(_leads_hoje / _meta_diaria * 100)
        _cor_hoje    = "#22c55e" if _leads_hoje >= _meta_diaria else ("#f59e0b" if _pct_hoje >= 70 else "#ef4444")

        if "origem" not in df_hoje.columns:
            df_hoje = df_hoje.copy()
            df_hoje["origem"] = "Sem origem"

        _rank_hoje = (
            df_hoje.groupby("origem")
            .size()
            .reset_index(name="n")
            .sort_values("n", ascending=False)
            .reset_index(drop=True)
        )

        _medalhas = ["🥇", "🥈", "🥉"]
        _rank_rows = ""
        for _ri, _rrow in _rank_hoje.iterrows():
            _med   = _medalhas[_ri] if _ri < 3 else ""
            _pct_op = round(_rrow["n"] / max(_leads_hoje, 1) * 100, 1)
            _lead_label = "lead" if _rrow["n"] == 1 else "leads"
            _rank_rows += (
                f"<div style='display:flex;justify-content:space-between;align-items:center;"
                f"padding:9px 0;border-bottom:1px solid #0d1320;'>"
                f"<div style='display:flex;align-items:center;gap:8px;'>"
                f"<span style='font-size:15px;min-width:20px;'>{_med}</span>"
                f"<span style='font-size:14px;font-weight:600;color:#c9d8f0;'>{_rrow['origem']}</span>"
                f"<span style='background:rgba(79,142,247,.15);border:1px solid rgba(79,142,247,.3);"
                f"border-radius:99px;padding:2px 9px;font-size:11px;color:#4f8ef7;font-weight:600;'>"
                f"{_rrow['n']} {_lead_label}</span>"
                f"</div>"
                f"<div style='font-size:13px;color:#7a9cc7;font-weight:500;'>{_pct_op}%</div>"
                f"</div>"
            )

        st.markdown(
            f"<div class='card-status' style='padding:20px 22px;'>"
            f"<div style='font-size:11px;color:#7a9cc7;font-weight:700;text-transform:uppercase;"
            f"letter-spacing:.7px;margin-bottom:14px;'>🏆 Performance do Dia</div>"
            f"<div style='display:flex;justify-content:space-between;align-items:flex-start;"
            f"margin-bottom:16px;'>"
            f"<div>"
            f"<div style='font-size:48px;font-weight:700;color:#c9d8f0;line-height:1;'>{_leads_hoje}</div>"
            f"</div>"
            f"<div style='text-align:right;'>"
            f"<div style='font-size:11px;color:#7a9cc7;margin-bottom:4px;'>Meta diária</div>"
            f"<div style='font-size:28px;font-weight:700;color:#c9d8f0;line-height:1;'>"
            f"{_leads_hoje} / {_meta_diaria}</div>"
            f"<div style='font-size:12px;color:{_cor_hoje};font-weight:600;margin-top:5px;'>"
            f"{_pct_hoje}% atingido</div>"
            f"</div></div>"
            f"{_rank_rows}"
            f"</div>",
            unsafe_allow_html=True,
        )

    with col_cards:
        with st.expander("⚙️ Meta mensal", expanded=False):
            _nova_meta = st.number_input(
                "Leads / mês", min_value=1, value=_meta, step=5, key="meta_input"
            )
            if st.button("💾 Salvar", key="btn_salvar_meta", use_container_width=True):
                st.session_state["_meta_mensal"] = int(_nova_meta)
                st.rerun(scope="fragment")

        st.markdown(f"""
        <div class="card-status" style="padding:20px 22px;margin-bottom:12px;">
            <div style="font-size:22px;margin-bottom:10px;">🎯</div>
            <div style="font-size:12px;color:#7a9cc7;font-weight:500;
                        text-transform:uppercase;letter-spacing:.5px;margin-bottom:8px;">Meta Mensal</div>
            <div style="display:flex;align-items:baseline;gap:6px;line-height:1;">
                <span style="font-size:38px;font-weight:700;color:{_cor_prog};">{_leads_mes}</span>
                <span style="font-size:18px;color:#7a9cc7;font-weight:400;">/ {_meta}</span>
            </div>
            <div style="background:#152a4a;border-radius:4px;height:5px;overflow:hidden;margin:10px 0 6px;">
                <div style="background:{_cor_prog};width:{_pct_meta}%;height:100%;border-radius:4px;"></div>
            </div>
            <div style="font-size:12px;color:#7a9cc7;">
                {_pct_meta}% atingido
                <span style="color:{_cor_prog};font-weight:600;margin-left:6px;">↑ {_leads_mes} de {_meta}</span>
            </div>
        </div>
        <div class="card-status" style="padding:20px 22px;">
            <div style="font-size:22px;margin-bottom:10px;">📈</div>
            <div style="font-size:12px;color:#7a9cc7;font-weight:500;
                        text-transform:uppercase;letter-spacing:.5px;margin-bottom:8px;">Projeção do Mês</div>
            <div style="font-size:38px;font-weight:700;color:{_cor_proj};line-height:1;">{_projecao}</div>
            <div style="font-size:12px;color:#7a9cc7;margin-top:10px;">
                Base: {_leads_mes} leads · {_du_passados}/{_du_totais} dias úteis
                <span style="color:{_cor_proj};font-weight:600;margin-left:6px;">↑ {_proj_sub}</span>
            </div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown('<div style="height:24px"></div>', unsafe_allow_html=True)

    # ── Linha 3: Ranking ──────────────────────────────────────────────────────
    st.markdown("#### 🏆 Ranking de Captação — Mês Atual")

    _df_rank_src = st.session_state.get("df_todos_all", df_todos).copy()
    if _grupo == "SDR":
        _df_rank_src = _df_rank_src[_df_rank_src["origem"].apply(lambda o: str(o).lower() in _SDR_NOMES)]
    elif _grupo == "Orgânico":
        _df_rank_src = _df_rank_src[_df_rank_src["origem"].apply(lambda o: str(o).lower() not in _SDR_NOMES)]
    _df_rank_src = _df_rank_src[
        _df_rank_src["data_obj"].apply(lambda d: d is not None and _de_val <= d <= _ate_val)
    ]

    if _df_rank_src.empty:
        st.info("Sem leads captados no período.")
        return

    _user_origem = st.session_state.get("_user_origem_filtro")

    _rank = (
        _df_rank_src.groupby("origem")
        .agg(
            leads=("id", "count"),
            tratados=("status", lambda x: (x != "Pendente").sum()),
            propostas=("status", lambda x: (x == "Proposta Enviada").sum()),
            valor=("valor_proposta", "sum"),
        )
        .reset_index()
        .sort_values("leads", ascending=False)
        .reset_index(drop=True)
    )

    _medals = ["🥇", "🥈", "🥉"]
    _rows = ""
    for i, row in _rank.iterrows():
        _pos = _medals[i] if i < 3 else f"#{i + 1}"
        _is_me = _user_origem and str(row["origem"]).strip().lower() == str(_user_origem).strip().lower()
        _row_bg = "background:rgba(79,142,247,0.08);border-left:3px solid #4f8ef7;" if _is_me else ""
        _trat_pct = round(row["tratados"] / row["leads"] * 100) if row["leads"] else 0
        _trat_cor = "#22c55e" if _trat_pct >= 70 else ("#f59e0b" if _trat_pct >= 40 else "#ef4444")
        _rows += (
            f'<tr style="border-bottom:1px solid #152a4a;{_row_bg}">'
            f'<td style="padding:14px 16px;font-size:22px;text-align:center;">{_pos}</td>'
            f'<td style="padding:14px 16px;color:#e8eef8;font-weight:600;font-size:15px;">&#128100; {row["origem"]}'
            + (" <span style='font-size:11px;color:#4f8ef7;font-weight:400;'>(você)</span>" if _is_me else "") +
            f'</td>'
            f'<td style="padding:14px 16px;color:#4f8ef7;font-weight:700;font-size:22px;text-align:center;">{row["leads"]}</td>'
            f'<td style="padding:14px 16px;color:{_trat_cor};font-weight:700;font-size:18px;text-align:center;">{int(row["tratados"])} <span style="font-size:11px;color:#4a5a6a;font-weight:400;">({_trat_pct}%)</span></td>'
            f'<td style="padding:14px 16px;color:#8b5cf6;font-weight:700;font-size:18px;text-align:center;">{int(row["propostas"])}</td>'
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
        '<th style="padding:10px 16px;color:#7a9cc7;font-size:11px;text-transform:uppercase;letter-spacing:.7px;text-align:center;">Tratados</th>'
        '<th style="padding:10px 16px;color:#7a9cc7;font-size:11px;text-transform:uppercase;letter-spacing:.7px;text-align:center;">Proposta</th>'
        '<th style="padding:10px 16px;color:#7a9cc7;font-size:11px;text-transform:uppercase;letter-spacing:.7px;text-align:right;">Carteira</th>'
        "</tr>"
        "</thead>"
        f"<tbody>{_rows}</tbody>"
        "</table></div>"
    )
    st.markdown(_table_html, unsafe_allow_html=True)
