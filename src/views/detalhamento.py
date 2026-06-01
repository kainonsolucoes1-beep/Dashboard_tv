import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import date, timedelta

from src.data.api import fetch_leads_30dias, fetch_leads_criticos
from src.utils.formatters import fmt_brl
from src.utils.time import dias_uteis_lista
from src.ui.modals import modal_lead, modal_operador


@st.fragment
def render_detalhamento(df_todos: pd.DataFrame):
    _hd_det, _btn_det = st.columns([5, 1])
    with _hd_det:
        st.markdown("#### 📆 Detalhamento de Leads por Dia e Operador")
        st.markdown(
            "<p style='color:#7a9cc7;font-size:13px;margin-top:-4px;'>"
            "Análise detalhada dia a dia — filtre o período abaixo de forma independente das outras abas."
            "</p>",
            unsafe_allow_html=True
        )
    with _btn_det:
        st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)
        _det_atualizar = st.button("🔄 Atualizar", key="det_refresh", use_container_width=True)
    if _det_atualizar:
        fetch_leads_30dias.clear()
        fetch_leads_criticos.clear()
        st.rerun(scope="fragment")

    st.markdown("---")
    st.markdown("#### 🔎 Filtros da Aba")
    _default_det_de  = date.today().replace(day=1)
    _default_det_ate = date.today()
    ops_disp_det     = sorted(df_todos["origem"].dropna().unique().tolist())
    _det_de_val  = st.session_state.get("_fv_det_de",  _default_det_de)
    _det_ate_val = st.session_state.get("_fv_det_ate", _default_det_ate)
    _det_ops_val = [o for o in st.session_state.get("_fv_det_ops", ops_disp_det) if o in ops_disp_det] or ops_disp_det

    fd1, fd2, fd3 = st.columns([1.5, 1.5, 3])
    with fd1:
        det_de = st.date_input(
            "📅 De", value=_det_de_val,
            format="DD/MM/YYYY", key="det_de"
        )
    with fd2:
        det_ate = st.date_input(
            "📅 Até", value=_det_ate_val,
            format="DD/MM/YYYY", key="det_ate"
        )
    with fd3:
        det_ops = st.multiselect(
            "👤 Origem", options=ops_disp_det, default=_det_ops_val, key="det_ops"
        )

    st.session_state["_fv_det_de"]  = det_de
    st.session_state["_fv_det_ate"] = det_ate
    st.session_state["_fv_det_ops"] = det_ops

    st.markdown("---")

    df_det = df_todos.copy()
    df_det = df_det[df_det["data_obj"].notna()]
    df_det = df_det[df_det["data_obj"].apply(lambda d: det_de <= d <= det_ate)]
    if det_ops:
        df_det = df_det[df_det["origem"].isin(det_ops)]

    if df_det.empty or not det_ops:
        st.info("Nenhum dado encontrado para o período e operadores selecionados.")
        return

    operadores_det = sorted(df_det["origem"].dropna().unique().tolist())
    CORES_DET = ["#4f8ef7", "#22c55e", "#f59e0b", "#8b5cf6", "#ef4444", "#f97316"]
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

    st.markdown("#### 👤 Resumo do Período por Operador")

    chunks = [operadores_det[i:i+4] for i in range(0, len(operadores_det), 4)]
    for chunk in chunks:
        cols_cards = st.columns(4)
        for col_c, op in zip(cols_cards, chunk):
            cor_op = cor_por_op[op]
            total_op   = int(pivot[op].sum())
            dias_uteis = len(dias_uteis_lista(det_de, det_ate))
            media_op   = round(total_op / dias_uteis, 1) if dias_uteis > 0 else 0

            df_op_det = df_det[df_det["origem"] == op]
            valor_op  = df_op_det["valor_proposta"].sum()
            leads_com_valor = int((df_op_det["valor_proposta"] > 0).sum())
            ticket_op = valor_op / leads_com_valor if leads_com_valor > 0 else 0

            with col_c:
                st.markdown(f"""
                <div class="card-status" style="border-left:4px solid {cor_op};display:flex;gap:16px;align-items:flex-start;">
                    <div style="min-width:110px;">
                        <span class="card-icone">👤</span>
                        <div class="card-valor" style="color:{cor_op};">{total_op}</div>
                        <div class="card-label">{op}</div>
                        <div style="margin-top:10px;font-size:14px;color:#7a9cc7;">
                            Média: <b style="color:{cor_op};">{media_op}/dia</b>
                        </div>
                    </div>
                    <div style="width:1px;background:#152a4a;align-self:stretch;margin:4px 0;flex-shrink:0;"></div>
                    <div style="flex:1;min-width:0;padding-top:4px;">
                        <div style="color:#7a9cc7;font-size:13px;font-weight:600;text-transform:uppercase;
                                    letter-spacing:.6px;margin-bottom:6px;">Carteira (R$)</div>
                        <div style="font-size:26px;font-weight:700;color:#22c55e;line-height:1.1;">
                            {fmt_brl(valor_op)}
                        </div>
                        <div style="font-size:13px;color:#7a9cc7;margin-top:4px;">em propostas enviadas</div>
                        <div style="margin-top:10px;color:#7a9cc7;font-size:13px;font-weight:600;
                                    text-transform:uppercase;letter-spacing:.6px;margin-bottom:4px;">Ticket Médio</div>
                        <div style="font-size:22px;font-weight:700;color:#4f8ef7;">
                            {fmt_brl(ticket_op)}
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
                if st.button("📊 Ver detalhes", key=f"btn_det_{op}", use_container_width=True):
                    modal_operador(op, df_op_det, cor_op, det_de, det_ate)

    st.markdown("---")
    st.markdown("#### 📋 Leads do Período")
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
    if "em_atraso" in df_det_sorted.columns:
        df_det_sorted["Atraso"] = df_det_sorted["em_atraso"].apply(lambda x: "🔴 Em atraso" if x else "")
    else:
        df_det_sorted["Atraso"] = ""

    col_labels_det = {
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
    df_det_display = df_det_sorted.copy()
    df_det_display["valor_proposta"] = df_det_display["valor_proposta"].apply(
        lambda v: fmt_brl(v) if v > 0 else "—"
    )
    cols_to_show = [c for c in col_labels_det if c in df_det_display.columns]
    df_det_display = df_det_display[cols_to_show].rename(
        columns={c: col_labels_det[c] for c in cols_to_show}
    )

    _term_det = st.text_input(
        "Pesquisar", placeholder="🔍 Nome, status, operador...",
        label_visibility="collapsed", key="search_leads_det"
    )
    if _term_det:
        _mask_det  = df_det_display.apply(lambda c: c.astype(str).str.contains(_term_det, case=False, na=False)).any(axis=1)
        df_det_display = df_det_display[_mask_det].reset_index(drop=True)
        df_det_sorted  = df_det_sorted[_mask_det].reset_index(drop=True)

    evt_det = st.dataframe(
        df_det_display,
        use_container_width=True,
        hide_index=True,
        height=500,
        selection_mode="single-row",
        on_select="rerun",
        key="tabela_leads_det",
    )
    sel_det = evt_det.selection.rows
    if sel_det and st.session_state.get("modal_leads_det") != sel_det[0]:
        st.session_state["modal_leads_det"] = sel_det[0]
        modal_lead(df_det_sorted.iloc[sel_det[0]])

    st.markdown("---")
    st.markdown("#### 📋 Tabela de Leads por Data e Operador")

    tabela_display = pivot.copy()
    tabela_display.index = [d.strftime("%d/%m/%Y (%a)").replace(
        "Mon", "Seg").replace("Tue", "Ter").replace("Wed", "Qua")
        .replace("Thu", "Qui").replace("Fri", "Sex")
        .replace("Sat", "Sáb").replace("Sun", "Dom")
        for d in tabela_display.index
    ]
    tabela_display.index.name = "Data"
    tabela_display = tabela_display.reset_index()

    linha_total = {"Data": "📊 TOTAL"}
    for op in operadores_det:
        linha_total[op] = int(pivot[op].sum())
    linha_total["Total"] = int(pivot["Total"].sum())
    tabela_display = pd.concat(
        [tabela_display, pd.DataFrame([linha_total])], ignore_index=True
    )
    st.dataframe(tabela_display, use_container_width=True, hide_index=True, height=420)
    if not sel_det:
        st.session_state.pop("modal_leads_det", None)

    st.markdown("---")
    st.markdown("#### 📊 Leads por Dia (todos os operadores)")

    fig_barras = go.Figure()
    for op in operadores_det:
        cor_op = cor_por_op[op]
        datas_fmt = [d.strftime("%d/%m") for d in pivot.index]
        fig_barras.add_trace(go.Bar(
            name=op,
            x=datas_fmt,
            y=pivot[op].tolist(),
            marker_color=cor_op,
            hovertemplate=f"<b>{op}</b><br>%{{x}}<br>%{{y}} leads<extra></extra>",
        ))

    fig_barras.update_layout(
        barmode="group",
        margin=dict(t=20, b=20, l=10, r=20),
        height=340,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        legend=dict(orientation="h", y=1.12, x=0, font=dict(color="#e8eef8", size=13)),
        xaxis=dict(showgrid=False, color="#7a9cc7", tickfont=dict(color="#e8eef8", size=11)),
        yaxis=dict(showgrid=True, gridcolor="#152a4a", color="#7a9cc7",
                   tickfont=dict(color="#e8eef8", size=12), zeroline=False),
        hovermode="x unified",
    )
    st.plotly_chart(fig_barras, use_container_width=True, key="det_barras")
