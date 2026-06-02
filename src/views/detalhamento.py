import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import date, timedelta

from src.data.api import fetch_leads_30dias, fetch_leads_criticos
from src.utils.formatters import fmt_brl
from src.utils.time import dias_uteis_lista
from src.ui.modals import modal_lead, modal_operador

CORES_DET = ["#4f8ef7", "#22c55e", "#f59e0b", "#8b5cf6", "#ef4444", "#f97316"]


def _hex_rgba(hex_color: str, alpha: float) -> str:
    h = hex_color.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return f"rgba({r},{g},{b},{alpha})"


def _spark_fig(y_values, x_labels, cor: str):
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=x_labels, y=y_values,
        mode="lines",
        line=dict(color=cor, width=2),
        fill="tozeroy",
        fillcolor=_hex_rgba(cor, 0.15),
        hovertemplate="%{x}: %{y} leads<extra></extra>",
    ))
    fig.update_layout(
        margin=dict(t=0, b=0, l=0, r=0),
        height=60,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(visible=False),
        yaxis=dict(visible=False),
        showlegend=False,
    )
    return fig


@st.fragment
def render_detalhamento(df_todos: pd.DataFrame):
    _default_de  = date.today().replace(day=1)
    _default_ate = date.today()
    ops_disp     = sorted(df_todos["origem"].dropna().unique().tolist())
    _de_val  = st.session_state.get("_fv_det_de",  _default_de)
    _ate_val = st.session_state.get("_fv_det_ate", _default_ate)
    _ops_val = [o for o in st.session_state.get("_fv_det_ops", ops_disp) if o in ops_disp] or ops_disp

    _ops_label   = ", ".join(_ops_val) if len(_ops_val) <= 3 else f"{len(_ops_val)} operadores"
    _exp_label   = f"🔎 Filtros · {_de_val.strftime('%d/%m')} – {_ate_val.strftime('%d/%m')} · {_ops_label}"

    with st.expander(_exp_label, expanded=False):
        fd1, fd2, fd3, fd4 = st.columns([1.5, 1.5, 3, 1])
        with fd1:
            det_de = st.date_input("📅 De",   value=_de_val,  format="DD/MM/YYYY", key="det_de")
        with fd2:
            det_ate = st.date_input("📅 Até", value=_ate_val, format="DD/MM/YYYY", key="det_ate")
        with fd3:
            det_ops = st.multiselect("👤 Origem", options=ops_disp, default=_ops_val, key="det_ops")
        with fd4:
            st.markdown("<div style='height:26px'></div>", unsafe_allow_html=True)
            if st.button("🔄 Atualizar", key="det_refresh", use_container_width=True):
                fetch_leads_30dias.clear()
                fetch_leads_criticos.clear()
                st.rerun(scope="fragment")

    det_de  = st.session_state.get("det_de",  _de_val)
    det_ate = st.session_state.get("det_ate", _ate_val)
    det_ops = st.session_state.get("det_ops", _ops_val)

    st.session_state["_fv_det_de"]  = det_de
    st.session_state["_fv_det_ate"] = det_ate
    st.session_state["_fv_det_ops"] = det_ops

    st.markdown("---")

    df_det = df_todos[df_todos["data_obj"].notna()].copy()
    df_det = df_det[df_det["data_obj"].apply(lambda d: det_de <= d <= det_ate)]
    if det_ops:
        df_det = df_det[df_det["origem"].isin(det_ops)]

    if df_det.empty or not det_ops:
        st.info("Nenhum dado encontrado para o período e operadores selecionados.")
        return

    operadores_det = sorted(df_det["origem"].dropna().unique().tolist())
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
    spark_x = [d.strftime("%d/%m") for d in pivot.index]

    # ── KPI FAIXA GLOBAL ──────────────────────────────────────────────────────
    total_leads  = len(df_det)
    total_vendas = int((df_det["status"] == "Venda Realizada").sum())
    conv_pct     = round(total_vendas / total_leads * 100, 1) if total_leads > 0 else 0
    volume_total = df_det["valor_proposta"].sum()

    kpi_items = [
        ("📥 Leads",      str(total_leads),      "#4f8ef7", "no período"),
        ("✅ Vendas",     str(total_vendas),      "#22c55e", "realizadas"),
        ("🎯 Conversão",  f"{conv_pct}%",         "#f59e0b", "leads → vendas"),
        ("💰 Volume",     fmt_brl(volume_total),  "#8b5cf6", "em propostas"),
    ]
    for col_k, (lbl, val, cor, sub) in zip(st.columns(4), kpi_items):
        with col_k:
            st.markdown(f"""
            <div style="background:#0e1f38;border-radius:12px;padding:24px 26px;
                        border-top:4px solid {cor};margin-bottom:6px;">
                <div style="color:#7a9cc7;font-size:13px;font-weight:600;
                            text-transform:uppercase;letter-spacing:.7px;margin-bottom:6px;">{lbl}</div>
                <div style="font-size:42px;font-weight:700;color:{cor};
                            line-height:1.1;margin:4px 0;">{val}</div>
                <div style="color:#7a9cc7;font-size:14px;margin-top:6px;">{sub}</div>
            </div>
            """, unsafe_allow_html=True)

    # ── CARDS POR OPERADOR ────────────────────────────────────────────────────
    st.markdown("---")
    st.markdown("#### 👤 Resumo por Operador")

    dias_uteis = len(dias_uteis_lista(det_de, det_ate))

    for chunk in [operadores_det[i:i+4] for i in range(0, len(operadores_det), 4)]:
        cols_cards = st.columns(4)
        for col_c, op in zip(cols_cards, chunk):
            cor_op      = cor_por_op[op]
            total_op    = int(pivot[op].sum())
            media_op    = round(total_op / dias_uteis, 1) if dias_uteis > 0 else 0
            df_op       = df_det[df_det["origem"] == op]
            valor_op    = df_op["valor_proposta"].sum()
            vendas_op   = int((df_op["status"] == "Venda Realizada").sum())
            conv_op     = round(vendas_op / total_op * 100, 1) if total_op > 0 else 0
            leads_c_val = int((df_op["valor_proposta"] > 0).sum())
            ticket_op   = valor_op / leads_c_val if leads_c_val > 0 else 0

            with col_c:
                st.markdown(f"""
                <div class="card-status" style="border-left:4px solid {cor_op};
                     display:flex;gap:16px;align-items:flex-start;">
                    <div style="min-width:110px;">
                        <span class="card-icone">👤</span>
                        <div class="card-valor" style="color:{cor_op};">{total_op}</div>
                        <div class="card-label">{op}</div>
                        <div style="margin-top:8px;font-size:13px;color:#7a9cc7;">
                            Média: <b style="color:{cor_op};">{media_op}/dia</b>
                        </div>
                        <div style="margin-top:4px;font-size:13px;color:#7a9cc7;">
                            Conversão: <b style="color:#22c55e;">{conv_op}%</b>
                        </div>
                    </div>
                    <div style="width:1px;background:#152a4a;align-self:stretch;
                                margin:4px 0;flex-shrink:0;"></div>
                    <div style="flex:1;min-width:0;padding-top:4px;">
                        <div style="color:#7a9cc7;font-size:13px;font-weight:600;
                                    text-transform:uppercase;letter-spacing:.6px;
                                    margin-bottom:6px;">Carteira (R$)</div>
                        <div style="font-size:26px;font-weight:700;color:#22c55e;line-height:1.1;">
                            {fmt_brl(valor_op)}
                        </div>
                        <div style="font-size:13px;color:#7a9cc7;margin-top:4px;">
                            em propostas enviadas
                        </div>
                        <div style="margin-top:10px;color:#7a9cc7;font-size:13px;font-weight:600;
                                    text-transform:uppercase;letter-spacing:.6px;
                                    margin-bottom:4px;">Ticket Médio</div>
                        <div style="font-size:22px;font-weight:700;color:#4f8ef7;">
                            {fmt_brl(ticket_op)}
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)

                if st.button("📊 Ver detalhes", key=f"btn_det_{op}", use_container_width=True):
                    modal_operador(op, df_op, cor_op, det_de, det_ate)

    # ── TABELA DE LEADS (colapsável) ──────────────────────────────────────────
    with st.expander("📋 Leads do Período", expanded=False):
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
        df_det_sorted["Atraso"] = df_det_sorted.get("em_atraso", pd.Series(False, index=df_det_sorted.index)).apply(
            lambda x: "🔴 Em atraso" if x else ""
        )

        col_labels = {
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
        df_display = df_det_sorted.copy()
        df_display["valor_proposta"] = df_display["valor_proposta"].apply(
            lambda v: fmt_brl(v) if v > 0 else "—"
        )
        cols_show = [c for c in col_labels if c in df_display.columns]
        df_display = df_display[cols_show].rename(columns={c: col_labels[c] for c in cols_show})

        term = st.text_input(
            "Pesquisar", placeholder="🔍 Nome, status, operador...",
            label_visibility="collapsed", key="search_leads_det"
        )
        if term:
            mask = df_display.apply(
                lambda c: c.astype(str).str.contains(term, case=False, na=False)
            ).any(axis=1)
            df_display    = df_display[mask].reset_index(drop=True)
            df_det_sorted = df_det_sorted[mask].reset_index(drop=True)

        evt = st.dataframe(
            df_display,
            use_container_width=True,
            hide_index=True,
            height=500,
            selection_mode="single-row",
            on_select="rerun",
            key="tabela_leads_det",
        )
        sel = evt.selection.rows
        if sel and st.session_state.get("modal_leads_det") != sel[0]:
            st.session_state["modal_leads_det"] = sel[0]
            modal_lead(df_det_sorted.iloc[sel[0]])
        if not sel:
            st.session_state.pop("modal_leads_det", None)
