import streamlit as st
import pandas as pd
from datetime import date, timedelta

from src.data.api import fetch_leads_30dias, fetch_leads_criticos, STATUS_MAP
from src.utils.formatters import fmt_brl, foto_base64
from src.ui.cards import render_card
from src.ui.modals import modal_lead
from src.charts.funil import grafico_funil_status
from src.charts.temperatura import grafico_temperatura_pizza
from src.charts.acumulado import grafico_acumulado
from src.charts.ranking import grafico_ranking_vendas


def render_painel_atendente(df_atendente, nome_atendente, cor_atendente, foto_path=None, show_table=True):
    total_at    = len(df_atendente)
    total_valor = df_atendente["valor_proposta"].sum()
    vendas_at   = int((df_atendente["status"] == "Venda Realizada").sum())
    taxa_at     = f"{(vendas_at / total_at * 100):.1f}%" if total_at > 0 else "0%"

    _status_fechados = {"Venda Realizada", "Venda não Realizada"}
    leads_abertos = int((~df_atendente["status"].isin(_status_fechados)).sum())
    leads_com_val = int((df_atendente["valor_proposta"] > 0).sum())
    ticket_medio  = total_valor / leads_com_val if leads_com_val > 0 else 0
    em_atraso_qt  = int(df_atendente["em_atraso"].sum()) if "em_atraso" in df_atendente.columns else 0

    foto_uri = foto_base64(foto_path) if foto_path else None
    if foto_uri:
        avatar_html = (
            f'<img src="{foto_uri}" style="'
            f'width:96px;height:96px;border-radius:50%;'
            f'border:3px solid {cor_atendente};object-fit:cover;flex-shrink:0;">'
        )
    else:
        avatar_html = (
            f'<div style="width:96px;height:96px;border-radius:50%;'
            f'border:3px solid {cor_atendente};background:{cor_atendente}18;'
            f'display:flex;align-items:center;justify-content:center;'
            f'font-size:48px;flex-shrink:0;">'
            f'👤</div>'
        )

    _cor_atr   = "#ef4444" if em_atraso_qt > 0 else "var(--text-sub)"

    _html_carteira = f'<span style="font-size:20px;font-weight:700;">R$</span><span style="font-size:20px;font-weight:700;">{fmt_brl(total_valor).split(" ",1)[1]}</span>'
    _html_ticket   = f'<span style="font-size:20px;font-weight:700;">R$</span><span style="font-size:20px;font-weight:700;">{fmt_brl(ticket_medio).split(" ",1)[1]}</span>'
    _div_style_brl = "display:flex;align-items:baseline;justify-content:center;gap:4px;"

    st.markdown(f"""
    <div style="
        background: linear-gradient(135deg, var(--bg-card) 0%, {cor_atendente}12 100%);
        border: 2px solid {cor_atendente};
        border-radius: 20px;
        padding: 20px 28px;
        margin-bottom: 20px;
        display: flex;
        align-items: center;
        gap: 20px;
        box-shadow: 0 4px 32px {cor_atendente}22;
    ">
        <div style="display:flex;align-items:center;gap:16px;flex-shrink:0;">
            {avatar_html}
            <div>
                <span style="font-size:26px;font-weight:700;color:{cor_atendente};line-height:1.1;">{nome_atendente}</span>
            </div>
        </div>
        <div style="flex:1;display:flex;justify-content:center;align-items:center;">
            <div style="display:flex;align-items:center;gap:0;">
                <div style="text-align:center;padding:0 32px;">
                    <div style="font-size:10px;color:var(--text-sub);text-transform:uppercase;letter-spacing:.7px;margin-bottom:5px;">Leads no Período</div>
                    <div style="font-size:30px;font-weight:700;color:{cor_atendente};">{total_at}</div>
                </div>
                <div style="width:1px;height:36px;background:var(--border);"></div>
                <div style="text-align:center;padding:0 32px;">
                    <div style="font-size:10px;color:var(--text-sub);text-transform:uppercase;letter-spacing:.7px;margin-bottom:5px;">Carteira Total</div>
                    <div style="font-size:30px;font-weight:700;color:var(--green);{_div_style_brl}">{_html_carteira}</div>
                </div>
                <div style="width:1px;height:36px;background:var(--border);"></div>
                <div style="text-align:center;padding:0 32px;">
                    <div style="font-size:10px;color:var(--text-sub);text-transform:uppercase;letter-spacing:.7px;margin-bottom:5px;">Ticket Médio</div>
                    <div style="font-size:30px;font-weight:700;color:#4f8ef7;{_div_style_brl}">{_html_ticket}</div>
                </div>
                <div style="width:1px;height:36px;background:var(--border);"></div>
                <div style="text-align:center;padding:0 32px;">
                    <div style="font-size:10px;color:var(--text-sub);text-transform:uppercase;letter-spacing:.7px;margin-bottom:5px;">Em Atraso</div>
                    <div style="font-size:30px;font-weight:700;color:{_cor_atr};">{em_atraso_qt}</div>
                </div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    temps = {
        "🔥 Quente": {"cor": "#ef4444", "icone": "🔥"},
        "🌡️ Morno":  {"cor": "#f59e0b", "icone": "🌡️"},
        "🧊 Frio":   {"cor": "#4f8ef7", "icone": "🧊"},
    }

    ct1, ct2, ct3, ct4 = st.columns(4)
    cols_temp = [ct1, ct2, ct3]

    for col, (temp_label, cfg) in zip(cols_temp, temps.items()):
        df_temp   = df_atendente[df_atendente["perception"] == temp_label]
        qtd       = len(df_temp)
        valor_sum = df_temp["valor_proposta"].sum()
        nome_temp = temp_label.split(' ', 1)[1]
        pct       = (qtd / total_at * 100) if total_at > 0 else 0
        with col:
            st.markdown(f"""
            <div class="card-status" style="border-left:4px solid {cfg['cor']};">
                <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:12px;">
                    <div style="display:flex;align-items:center;gap:8px;">
                        <span style="font-size:18px;">{cfg['icone']}</span>
                        <span class="card-label" style="color:{cfg['cor']};">{nome_temp.upper()}</span>
                    </div>
                    <span style="font-size:13px;font-weight:700;color:{cfg['cor']};opacity:.85;">{pct:.0f}%</span>
                </div>
                <div class="card-valor" style="color:{cfg['cor']};font-size:44px;line-height:1;">{qtd}</div>
                <div style="margin-top:12px;height:4px;background:{cfg['cor']}22;border-radius:2px;">
                    <div style="height:4px;width:{min(pct,100):.1f}%;background:{cfg['cor']};border-radius:2px;"></div>
                </div>
                <div style="margin-top:8px;font-size:12px;color:var(--text-sub);">{fmt_brl(valor_sum)}</div>
            </div>
            """, unsafe_allow_html=True)

    sem_perc = int(
        (
            (df_atendente["perception"] == "Sem percepção") &
            (~df_atendente["status"].isin(_status_fechados))
        ).sum()
    )
    pct_sp = (sem_perc / total_at * 100) if total_at > 0 else 0
    with ct4:
        st.markdown(f"""
        <div class="card-status" style="border-left:4px solid var(--text-sub);">
            <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:12px;">
                <div style="display:flex;align-items:center;gap:8px;">
                    <span style="font-size:18px;">❓</span>
                    <span class="card-label" style="color:var(--text-sub);">SEM PERCEPÇÃO</span>
                </div>
                <span style="font-size:13px;font-weight:700;color:var(--text-sub);">{pct_sp:.0f}%</span>
            </div>
            <div class="card-valor" style="color:var(--text-sub);font-size:44px;line-height:1;">{sem_perc}</div>
            <div style="margin-top:12px;height:4px;background:#ffffff12;border-radius:2px;">
                <div style="height:4px;width:{min(pct_sp,100):.1f}%;background:var(--text-sub);border-radius:2px;"></div>
            </div>
            <div style="margin-top:8px;font-size:12px;color:var(--text-sub);">não classificados</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown('<div style="height:20px"></div>', unsafe_allow_html=True)

    cg1, cg2 = st.columns([1, 1])
    with cg1:
        st.markdown("#### 🔽 Funil de Status")
        st.plotly_chart(
            grafico_funil_status(df_atendente),
            use_container_width=True,
            key=f"funil_{nome_atendente}"
        )
    with cg2:
        st.markdown("#### 🌡️ Temperatura")
        fig_pizza = grafico_temperatura_pizza(df_atendente)
        if fig_pizza:
            st.plotly_chart(
                fig_pizza,
                use_container_width=True,
                key=f"pizza_{nome_atendente}"
            )
        else:
            st.info("Sem percepção classificada ainda.")

    st.markdown('<div style="height:20px"></div>', unsafe_allow_html=True)

    if not show_table:
        return

    st.markdown("#### 📋 Leads em Carteira")

    df_tabela = df_atendente.copy()
    df_tabela["Valor"] = df_tabela["valor_proposta"].apply(
        lambda v: fmt_brl(v) if v > 0 else "—"
    )
    if "em_atraso" in df_tabela.columns:
        df_tabela["Atraso"] = df_tabela["em_atraso"].apply(lambda x: "🔴 Em atraso" if x else "")
    else:
        df_tabela["Atraso"] = ""

    col_map = {
        "Atraso":        "Situação",
        "nome":          "Nome",
        "status":        "Status",
        "perception":    "Temperatura",
        "Valor":         "Valor da Proposta",
        "origem":        "Canal",
        "interesse":     "Interesse",
        "criado_em":     "Cadastrado em",
        "atualizado_em": "Última Atualização",
    }

    df_sorted_orig = df_tabela.copy()
    df_sorted_orig["_sort"] = pd.to_datetime(
        df_sorted_orig["atualizado_em"], format="%d/%m/%Y %H:%M", errors="coerce"
    )
    df_sorted_orig = (
        df_sorted_orig.sort_values("_sort", ascending=False)
        .drop(columns=["_sort"])
        .reset_index(drop=True)
    )
    df_show = df_sorted_orig[list(col_map.keys())].rename(columns=col_map)

    _sc_at, _ = st.columns([1, 2])
    with _sc_at:
        _term_at = st.text_input(
            "Pesquisar", placeholder="🔍 Busque seus leads aqui...",
            label_visibility="collapsed", key=f"search_{nome_atendente}"
        )
    if _term_at:
        _mask_at = df_show.apply(lambda c: c.astype(str).str.contains(_term_at, case=False, na=False)).any(axis=1)
        df_show        = df_show[_mask_at].reset_index(drop=True)
        df_sorted_orig = df_sorted_orig[_mask_at].reset_index(drop=True)

    st.caption("💡 Clique em uma linha para ver os detalhes completos do lead.")
    modal_key = f"modal_shown_{nome_atendente}"
    evt = st.dataframe(
        df_show,
        use_container_width=True,
        hide_index=True,
        height=300,
        selection_mode="single-row",
        on_select="rerun",
        key=f"tabela_{nome_atendente}",
    )
    sel = evt.selection.rows
    if sel and st.session_state.get(modal_key) != sel[0]:
        st.session_state[modal_key] = sel[0]
        modal_lead(df_sorted_orig.iloc[sel[0]])
    if not sel:
        st.session_state.pop(modal_key, None)


@st.fragment
def render_operadores(df_todos: pd.DataFrame):
    _hd_op, _btn_op = st.columns([5, 1])
    with _hd_op:
        st.markdown("#### 🔎 Filtros da Aba")
    with _btn_op:
        st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)
        _op_atualizar = st.button("🔄 Atualizar", key="op_refresh", use_container_width=True)
    if _op_atualizar:
        fetch_leads_30dias.clear()
        fetch_leads_criticos.clear()
        st.rerun(scope="fragment")
    _default_op_de  = date.today() - timedelta(days=30)
    _default_op_ate = date.today()
    op_de  = st.session_state.get("_fv_op_de",  _default_op_de)
    op_ate = st.session_state.get("_fv_op_ate", _default_op_ate)

    origens_op_disp = sorted(df_todos["origem"].dropna().unique().tolist())
    _op_orig_def    = [o for o in st.session_state.get("_fv_op_orig", origens_op_disp) if o in origens_op_disp] or origens_op_disp
    _op_status_opts = ["Todos"] + list(dict.fromkeys(STATUS_MAP.values()))
    _op_status_def  = st.session_state.get("_fv_op_status", "Todos")
    _op_status_idx  = _op_status_opts.index(_op_status_def) if _op_status_def in _op_status_opts else 0

    op_de_col, op_ate_col, op1, op2, _ = st.columns([1.5, 1.5, 2.5, 2, 1])
    with op_de_col:
        op_de = st.date_input("📅 De", value=op_de, format="DD/MM/YYYY", key="op_de")
    with op_ate_col:
        op_ate = st.date_input("📅 Até", value=op_ate, format="DD/MM/YYYY", key="op_ate")
    with op1:
        op_selecionados = st.multiselect(
            "👤 Origem", options=origens_op_disp, default=_op_orig_def, key="op_origem"
        )
    with op2:
        op_status = st.selectbox(
            "📌 Status", _op_status_opts, index=_op_status_idx, key="op_status"
        )

    st.session_state["_fv_op_de"]     = op_de
    st.session_state["_fv_op_ate"]    = op_ate
    st.session_state["_fv_op_orig"]   = op_selecionados
    st.session_state["_fv_op_status"] = op_status

    df_todos = df_todos[df_todos["data_obj"].apply(lambda d: d is not None and op_de <= d <= op_ate)]

    df_filtrado = df_todos.copy()
    if op_selecionados:
        df_filtrado = df_filtrado[df_filtrado["origem"].isin(op_selecionados)]
    if op_status != "Todos":
        df_filtrado = df_filtrado[df_filtrado["status"] == op_status]

    _VENDEDORES = {"isaac", "leticia", "julia", "rodolfo"}
    _is_admin   = st.session_state.get("_auth_user", "") not in _VENDEDORES

    st.markdown('<div style="height:20px"></div>', unsafe_allow_html=True)

    if _is_admin:
        dados_ranking     = df_filtrado[df_filtrado["status"] == "Venda Realizada"]["origem"].value_counts().to_dict()
        total_vendas      = sum(dados_ranking.values())
        top_operador      = max(dados_ranking, key=dados_ranking.get) if dados_ranking else "—"
        operadores_ativos = len(dados_ranking)

        mc1, mc2, mc3 = st.columns(3)
        with mc1:
            render_card("🏆", total_vendas,      "Total de Vendas",   "#1D9E75")
        with mc2:
            render_card("⭐", top_operador,       "Top Operador",      "#378ADD")
        with mc3:
            render_card("👥", operadores_ativos,  "Operadores Ativos", "#f59e0b")

        st.markdown('<div style="height:16px"></div>', unsafe_allow_html=True)

        col_linha, col_rank = st.columns([6, 4])
        with col_linha:
            st.markdown("#### 📈 Acumulado de Leads")
            if op_selecionados:
                st.plotly_chart(
                    grafico_acumulado(df_filtrado, op_selecionados),
                    use_container_width=True, key="acumulado_op",
                )
            else:
                st.info("Selecione ao menos um operador.")
        with col_rank:
            st.markdown("#### 🏆 Ranking de Vendas")
            if dados_ranking:
                st.plotly_chart(
                    grafico_ranking_vendas(dados_ranking),
                    use_container_width=True,
                    config={"displayModeBar": False},
                    key="ranking_op",
                )
            else:
                st.info("Sem vendas no período.")
    else:
        st.markdown("#### 📈 Acumulado de Leads por Operador no Mês")
        if op_selecionados:
            st.plotly_chart(
                grafico_acumulado(df_filtrado, op_selecionados),
                use_container_width=True, key="acumulado_op",
            )
        else:
            st.info("Selecione ao menos um operador para ver o acumulado.")
