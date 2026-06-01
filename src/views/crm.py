import json
import os
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import date, datetime

from src.data.api import fetch_leads_30dias, fetch_leads_criticos, fetch_leads_80dias
from src.data.transforms import merge_leads_curto, merge_leads_longo
from src.utils.formatters import fmt_brl
from src.data.aliases import load_base_aliases, save_base_aliases, apply_base_aliases, load_base_manual, apply_base_manual, load_valor_manual, apply_valor_manual
from src.ui.modals import modal_lead


@st.fragment
def render_crm():
    df_todos, _ = merge_leads_curto()

    CORES_CRM = ["#4f8ef7", "#22c55e", "#f59e0b", "#8b5cf6", "#ef4444", "#f97316"]
    SEMANA_PT = {
        "Monday": "Segunda-feira", "Tuesday": "Terça-feira", "Wednesday": "Quarta-feira",
        "Thursday": "Quinta-feira", "Friday": "Sexta-feira",
        "Saturday": "Sábado", "Sunday": "Domingo",
    }

    _, crm_btn_col = st.columns([5, 1])
    with crm_btn_col:
        _crm_atualizar = st.button("🔄 Atualizar", key="crm_refresh", use_container_width=True)
    if _crm_atualizar:
        fetch_leads_30dias.clear()
        fetch_leads_criticos.clear()
        st.rerun(scope="fragment")

    aliases = load_base_aliases()
    df_todos_raw = df_todos.copy()
    df_todos = apply_base_aliases(df_todos, aliases)

    has_base = "base" in df_todos.columns
    df_base_all = (
        df_todos[df_todos["base"].notna() & (df_todos["base"] != "")].copy()
        if has_base else pd.DataFrame()
    )

    sub_dia, sub_ranking, sub_historico, sub_aliases = st.tabs([
        "📅 Por Data",
        "🏆 Ranking de Conversão",
        "🕐 Histórico de Bases",
        "✏️ Gerenciar Nomes",
    ])

    with sub_dia:
        data_crm = st.date_input(
            "📅 Selecione a data",
            value=date.today(),
            format="DD/MM/YYYY",
            key="crm_data",
        )

        df_crm = df_todos[df_todos["data_obj"].notna()].copy()
        df_crm = df_crm[df_crm["data_obj"] == data_crm]

        data_fmt  = data_crm.strftime("%d/%m/%Y")
        dia_semana = SEMANA_PT.get(data_crm.strftime("%A"), data_crm.strftime("%A"))
        st.markdown(
            f"<h3 style='color:#e8eef8;margin-bottom:2px;'>{data_fmt}"
            f"<span style='color:#7a9cc7;font-size:16px;font-weight:400;margin-left:12px;'>"
            f"{dia_semana}</span></h3>",
            unsafe_allow_html=True
        )

        if df_crm.empty:
            st.info("Nenhum lead registrado nesta data.")
        else:
            df_com_base_dia = df_crm[df_crm["base"].notna() & (df_crm["base"] != "")] if has_base else pd.DataFrame()
            m1, m2, m3, m4 = st.columns(4)
            with m1:
                st.metric("Total de Leads", len(df_crm))
            with m2:
                st.metric("Bases Identificadas", df_com_base_dia["base"].nunique() if not df_com_base_dia.empty else 0)
            with m3:
                st.metric("Operadores Ativos", df_crm["origem"].nunique())
            with m4:
                st.metric("Vendas no Dia", int((df_crm["status"] == "Venda Realizada").sum()))

            st.markdown("---")

            if df_com_base_dia.empty:
                st.warning(
                    "Nenhum lead desta data possui base registrada. "
                    "O campo **Base de Clientes** no formulário ainda não foi utilizado — "
                    "os próximos leads cadastrados já aparecerão aqui automaticamente."
                )
            else:
                st.markdown("#### 🗂️ Bases Utilizadas")
                for i, base in enumerate(sorted(df_com_base_dia["base"].unique())):
                    cor       = CORES_CRM[i % len(CORES_CRM)]
                    df_b      = df_com_base_dia[df_com_base_dia["base"] == base]
                    leads_b   = len(df_b)
                    vendas_b  = int((df_b["status"] == "Venda Realizada").sum())
                    valor_b   = df_b["valor_proposta"].sum()
                    ops_b     = ", ".join(sorted(df_b["origem"].dropna().unique()))
                    conv_b    = round(vendas_b / leads_b * 100, 1) if leads_b > 0 else 0
                    st.markdown(f"""
                    <div class="card-status" style="border-left:4px solid {cor};margin-bottom:16px;">
                      <div style="display:flex;align-items:flex-start;gap:24px;flex-wrap:wrap;">
                        <div style="min-width:220px;">
                          <div style="font-size:11px;color:#7a9cc7;text-transform:uppercase;
                                      letter-spacing:.8px;font-weight:600;margin-bottom:4px;">Base de Clientes</div>
                          <div style="font-size:20px;font-weight:700;color:{cor};word-break:break-all;">{base}</div>
                          <div style="margin-top:10px;font-size:13px;color:#7a9cc7;">
                            <b style="color:#e8eef8;">Operadores:</b> {ops_b}</div>
                        </div>
                        <div style="width:1px;background:#152a4a;align-self:stretch;flex-shrink:0;"></div>
                        <div style="display:flex;gap:28px;flex-wrap:wrap;padding-top:2px;">
                          <div>
                            <div style="font-size:11px;color:#7a9cc7;text-transform:uppercase;letter-spacing:.8px;font-weight:600;">Leads</div>
                            <div style="font-size:32px;font-weight:700;color:#e8eef8;line-height:1.1;">{leads_b}</div>
                          </div>
                          <div>
                            <div style="font-size:11px;color:#7a9cc7;text-transform:uppercase;letter-spacing:.8px;font-weight:600;">Vendas</div>
                            <div style="font-size:32px;font-weight:700;color:#22c55e;line-height:1.1;">{vendas_b}</div>
                            <div style="font-size:12px;color:#22c55e;">{conv_b}% conversão</div>
                          </div>
                          <div>
                            <div style="font-size:11px;color:#7a9cc7;text-transform:uppercase;letter-spacing:.8px;font-weight:600;">Carteira (R$)</div>
                            <div style="font-size:26px;font-weight:700;color:#f59e0b;line-height:1.1;">{fmt_brl(valor_b)}</div>
                            <div style="font-size:12px;color:#7a9cc7;">em propostas</div>
                          </div>
                        </div>
                      </div>
                    </div>
                    """, unsafe_allow_html=True)

            st.markdown("---")
            st.markdown("#### 📋 Leads do Dia")
            st.caption("💡 Clique em uma linha para ver os detalhes completos do lead.")

            df_crm_sorted = df_crm.copy()
            df_crm_sorted["_sort"] = pd.to_datetime(
                df_crm_sorted["atualizado_em"], format="%d/%m/%Y %H:%M", errors="coerce"
            )
            df_crm_sorted = (
                df_crm_sorted.sort_values("_sort", ascending=False)
                .drop(columns=["_sort"])
                .reset_index(drop=True)
            )
            if "em_atraso" in df_crm_sorted.columns:
                df_crm_sorted["Atraso"] = df_crm_sorted["em_atraso"].apply(lambda x: "🔴 Em atraso" if x else "")
            else:
                df_crm_sorted["Atraso"] = ""

            col_labels_crm = {
                "Atraso": "Situação", "nome": "Nome", "status": "Status",
                "perception": "Temperatura", "valor_proposta": "Valor (R$)",
                "atendente": "Atendente", "origem": "Operador", "base": "Base",
                "interesse": "Interesse", "atualizado_em": "Última Atualização",
            }
            df_crm_disp = df_crm_sorted.copy()
            df_crm_disp["valor_proposta"] = df_crm_disp["valor_proposta"].apply(
                lambda v: fmt_brl(v) if v > 0 else "—"
            )
            cols_crm = [c for c in col_labels_crm if c in df_crm_disp.columns]
            df_crm_disp = df_crm_disp[cols_crm].rename(columns={c: col_labels_crm[c] for c in cols_crm})

            _term_crm = st.text_input(
                "Pesquisar", placeholder="🔍 Nome, status, operador...",
                label_visibility="collapsed", key="search_leads_crm"
            )
            if _term_crm:
                _mask_crm   = df_crm_disp.apply(lambda c: c.astype(str).str.contains(_term_crm, case=False, na=False)).any(axis=1)
                df_crm_disp    = df_crm_disp[_mask_crm].reset_index(drop=True)
                df_crm_sorted  = df_crm_sorted[_mask_crm].reset_index(drop=True)

            evt_crm = st.dataframe(
                df_crm_disp, use_container_width=True, hide_index=True, height=480,
                selection_mode="single-row", on_select="rerun", key="tabela_leads_crm",
            )
            sel_crm = evt_crm.selection.rows
            if sel_crm and st.session_state.get("modal_leads_crm") != sel_crm[0]:
                st.session_state["modal_leads_crm"] = sel_crm[0]
                modal_lead(df_crm_sorted.iloc[sel_crm[0]])
            if not sel_crm:
                st.session_state.pop("modal_leads_crm", None)

    _SDR_NOMES_CRM = {"isaac", "julia", "leticia", "rodolfo", "o2 solution", "anny", "emilly", "maria eduarda", "clara", "kauany"}

    with sub_ranking:
        df_longo, _ = merge_leads_longo()
        if "conversion_goal" not in df_longo.columns:
            fetch_leads_80dias.clear()
            df_longo, _ = merge_leads_longo()
        df_longo = apply_base_manual(df_longo, load_base_manual())
        df_longo = apply_valor_manual(df_longo, load_valor_manual())
        df_longo = apply_base_aliases(df_longo, aliases)
        df_vnd_all = df_longo[df_longo["status"] == "Venda Realizada"].copy()

        _default_vr_de  = date.today().replace(day=1)
        _default_vr_ate = date.today()
        _vc1, _vc2, _ = st.columns([2, 2, 4])
        with _vc1:
            vr_de = st.date_input("📅 De", value=st.session_state.get("crm_vr_de", _default_vr_de), format="DD/MM/YYYY", key="crm_vr_de")
        with _vc2:
            vr_ate = st.date_input("📅 Até", value=st.session_state.get("crm_vr_ate", _default_vr_ate), format="DD/MM/YYYY", key="crm_vr_ate")

        df_vr = df_vnd_all[
            df_vnd_all["atualizado_obj"].apply(lambda d: d is not None and vr_de <= d <= vr_ate)
        ].copy()

        def _calc_origem_base(r):
            base   = str(r.get("base") or "").strip()
            origem = str(r.get("origem") or "").strip()
            conv   = str(r.get("conversion_goal") or "").strip()
            if origem.lower() in _SDR_NOMES_CRM:
                return pd.Series({"origem_display": origem, "base_display": base or "Sem base"})
            return pd.Series({"origem_display": origem or "Sem origem", "base_display": base or conv or "—"})

        if not df_vr.empty:
            df_vr[["origem_display", "base_display"]] = df_vr.apply(_calc_origem_base, axis=1)

        _extras_path = os.path.join(os.path.dirname(__file__), "..", "..", "leads_extras.json")
        try:
            with open(_extras_path, "r", encoding="utf-8") as _f:
                _extras_raw = json.load(_f)
            _extras_rows = []
            for _e in _extras_raw:
                _d = datetime.strptime(_e["atualizado_obj"], "%Y-%m-%d").date()
                if vr_de <= _d <= vr_ate:
                    _extras_rows.append({
                        "id":              _e["id"],
                        "nome":            _e["nome"],
                        "atualizado_em":   _e["atualizado_em"],
                        "atualizado_obj":  _d,
                        "atendente":       _e.get("atendente", ""),
                        "valor_proposta":  float(_e.get("valor_proposta", 0)),
                        "origem_display":  _e.get("origem_display", "—"),
                        "base_display":    _e.get("base_display", "—"),
                    })
            if _extras_rows:
                df_vr = pd.concat([df_vr, pd.DataFrame(_extras_rows)], ignore_index=True)
        except Exception:
            pass

        if df_vr.empty:
            st.info("Nenhuma venda realizada no período.")
        else:
            total_vr    = len(df_vr)
            valor_total = df_vr["valor_proposta"].sum()
            ticket      = valor_total / total_vr if total_vr else 0

            grp = (
                df_vr.groupby("base_display")
                .agg(vendas=("id", "count"), valor=("valor_proposta", "sum"))
                .reset_index()
                .sort_values("vendas", ascending=False)
                .reset_index(drop=True)
            )
            grp["ticket"] = grp.apply(
                lambda r: r["valor"] / r["vendas"] if r["vendas"] > 0 else 0, axis=1
            )
            _top_base = grp.loc[grp["valor"].idxmax(), "base_display"] if not grp.empty else "—"

            st.markdown("<div style='margin-top:24px'></div>", unsafe_allow_html=True)
            _m1, _m2, _m3, _m4 = st.columns(4)
            with _m1:
                st.metric("Vendas Realizadas", total_vr)
            with _m2:
                st.metric("Valor Total", fmt_brl(valor_total))
            with _m3:
                st.metric("Ticket Médio", fmt_brl(ticket))
            with _m4:
                st.metric("🏆 Maior Base (R$)", _top_base)

            st.markdown("---")
            st.markdown("#### 🗂️ Por Origem")

            for _gi, (_, _row) in enumerate(grp.iterrows()):
                _cor      = CORES_CRM[_gi % len(CORES_CRM)]
                _base_lbl = str(_row["base_display"])
                _vendas_i = int(_row["vendas"])
                _valor_f  = fmt_brl(_row["valor"])
                _ticket_f = fmt_brl(_row["ticket"])
                with st.expander(f"📦  {_base_lbl}", expanded=False):
                    st.markdown(f"""
                    <div class="card-status" style="border-left:4px solid {_cor};margin-bottom:14px;">
                      <div style="display:flex;align-items:flex-start;gap:24px;flex-wrap:wrap;">
                        <div style="min-width:200px;">
                          <div style="font-size:11px;color:#7a9cc7;text-transform:uppercase;
                                      letter-spacing:.8px;font-weight:600;margin-bottom:4px;">Base / Site</div>
                          <div style="font-size:20px;font-weight:700;color:{_cor};word-break:break-all;">{_base_lbl}</div>
                        </div>
                        <div style="width:1px;background:#152a4a;align-self:stretch;flex-shrink:0;"></div>
                        <div style="display:flex;gap:32px;flex-wrap:wrap;padding-top:2px;">
                          <div>
                            <div style="font-size:11px;color:#7a9cc7;text-transform:uppercase;letter-spacing:.8px;font-weight:600;">Vendas</div>
                            <div style="font-size:32px;font-weight:700;color:{_cor};line-height:1.1;">{_vendas_i}</div>
                          </div>
                          <div>
                            <div style="font-size:11px;color:#7a9cc7;text-transform:uppercase;letter-spacing:.8px;font-weight:600;">Valor Total</div>
                            <div style="font-size:26px;font-weight:700;color:#22c55e;line-height:1.1;">{_valor_f}</div>
                          </div>
                          <div>
                            <div style="font-size:11px;color:#7a9cc7;text-transform:uppercase;letter-spacing:.8px;font-weight:600;">Ticket Médio</div>
                            <div style="font-size:26px;font-weight:700;color:#f59e0b;line-height:1.1;">{_ticket_f}</div>
                          </div>
                        </div>
                      </div>
                    </div>
                    """, unsafe_allow_html=True)

                    _df_grp = df_vr[df_vr["base_display"] == _row["base_display"]].copy()

                    _orig_counts = _df_grp["origem_display"].value_counts()
                    if not _orig_counts.empty and len(_orig_counts) > 1:
                        st.markdown("##### 👤 Origens")
                        _orig_html = '<div style="display:flex;gap:8px;flex-wrap:wrap;margin-bottom:16px;">'
                        for _orig_nome, _orig_qtd in _orig_counts.items():
                            _orig_pct = round(_orig_qtd / len(_df_grp) * 100, 1)
                            _orig_html += (
                                f'<div style="background:#0d1f38;border:1px solid #1c2a3d;'
                                f'border-radius:10px;padding:8px 16px;min-width:100px;text-align:center;">'
                                f'<div style="font-size:13px;color:#7a9cc7;font-weight:600;'
                                f'text-transform:uppercase;letter-spacing:.5px;margin-bottom:4px;">'
                                f'{_orig_nome}</div>'
                                f'<div style="font-size:26px;font-weight:700;color:{_cor};line-height:1;">'
                                f'{_orig_qtd}</div>'
                                f'<div style="font-size:11px;color:#7a9cc7;margin-top:2px;">'
                                f'{_orig_pct}%</div>'
                                f'</div>'
                            )
                        _orig_html += '</div>'
                        st.markdown(_orig_html, unsafe_allow_html=True)

                    st.markdown("##### 📋 Vendas desta origem")
                    _df_grp_s = _df_grp.sort_values("atualizado_obj", ascending=False).reset_index(drop=True)
                    _COLS_GRP = {
                        "atualizado_em":  "Data da Venda",
                        "nome":           "Cliente",
                        "origem_display": "Origem",
                        "atendente":      "Atendente",
                        "valor_proposta": "Valor Final (R$)",
                    }
                    _df_grp_disp = _df_grp_s[[c for c in _COLS_GRP if c in _df_grp_s.columns]].copy()
                    _df_grp_disp["valor_proposta"] = _df_grp_s["valor_proposta"].apply(
                        lambda v: fmt_brl(v) if v > 0 else "—"
                    )
                    _df_grp_disp = _df_grp_disp.rename(columns=_COLS_GRP)
                    _alt_grp = min(500, 40 + len(_df_grp_disp) * 35)
                    st.dataframe(_df_grp_disp, use_container_width=True, hide_index=True, height=_alt_grp)

    with sub_historico:
        if df_base_all.empty:
            st.info("Nenhuma base registrada ainda. Preencha o campo **Base de Clientes** no formulário para o histórico aparecer aqui.")
        else:
            _default_hist_ini = df_base_all["data_obj"].min()
            _default_hist_fim = date.today()
            hist_data_ini = st.session_state.get("hist_data_ini", _default_hist_ini)
            hist_data_fim = st.session_state.get("hist_data_fim", _default_hist_fim)

            with st.form("filtros_historico", border=False):
                col_f1, col_f2, col_f3 = st.columns([2, 2, 1])
                with col_f1:
                    hist_data_ini = st.date_input(
                        "📅 Data inicial",
                        value=hist_data_ini,
                        format="DD/MM/YYYY",
                        key="hist_data_ini",
                    )
                with col_f2:
                    hist_data_fim = st.date_input(
                        "📅 Data final",
                        value=hist_data_fim,
                        format="DD/MM/YYYY",
                        key="hist_data_fim",
                    )
                with col_f3:
                    st.markdown("<div style='margin-top:24px'>", unsafe_allow_html=True)
                    submitted_hist = st.form_submit_button("✔ Aplicar", use_container_width=True)
                    st.markdown("</div>", unsafe_allow_html=True)
                if submitted_hist:
                    hist_data_ini = st.session_state.get("hist_data_ini", _default_hist_ini)
                    hist_data_fim = st.session_state.get("hist_data_fim", _default_hist_fim)

            df_hist_filtrado = df_base_all[
                df_base_all["data_obj"].notna() &
                (df_base_all["data_obj"] >= hist_data_ini) &
                (df_base_all["data_obj"] <= hist_data_fim)
            ].copy()

            periodo_label = (
                f"{hist_data_ini.strftime('%d/%m/%Y')} → {hist_data_fim.strftime('%d/%m/%Y')}"
            )
            st.markdown(
                f"<div style='color:#7a9cc7;font-size:13px;margin-bottom:4px;'>"
                f"Exibindo: <strong style='color:#e8eef8;'>{periodo_label}</strong></div>",
                unsafe_allow_html=True,
            )
            st.markdown("---")

            if df_hist_filtrado.empty:
                st.info("Nenhuma base registrada no período selecionado.")
            else:
                historico = (
                    df_hist_filtrado.groupby("base")
                    .agg(
                        leads_total   =("id",            "count"),
                        vendas_total  =("status",        lambda x: (x == "Venda Realizada").sum()),
                        carteira_total=("valor_proposta","sum"),
                        primeira_data =("data_obj",      "min"),
                        ultima_data   =("data_obj",      "max"),
                        dias_usada    =("data_obj",      "nunique"),
                    )
                    .reset_index()
                )
                historico["conv_pct"] = (
                    historico["vendas_total"] / historico["leads_total"] * 100
                ).round(1)
                historico["ticket_medio"] = historico.apply(
                    lambda r: r["carteira_total"] / r["leads_total"] if r["leads_total"] > 0 else 0, axis=1
                )
                historico = historico.sort_values("ultima_data", ascending=False).reset_index(drop=True)

                _tot_leads    = int(historico["leads_total"].sum())
                _tot_carteira = historico["carteira_total"].sum()
                _ticket_geral = fmt_brl(_tot_carteira / _tot_leads) if _tot_leads > 0 else "R$ 0"

                h1, h2, h3, h4 = st.columns(4)
                with h1:
                    st.metric("Total de bases", len(historico))
                with h2:
                    st.metric("Leads totais", _tot_leads)
                with h3:
                    st.metric("Carteira total", fmt_brl(_tot_carteira))
                with h4:
                    st.metric("Ticket médio", _ticket_geral)

                st.markdown("---")
                st.markdown("#### 🕐 Todas as Bases Utilizadas")

                total_leads_geral = int(historico["leads_total"].sum())

                for idx, row in historico.iterrows():
                    cor          = CORES_CRM[idx % len(CORES_CRM)]
                    p_data       = row["primeira_data"].strftime("%d/%m/%Y") if pd.notna(row["primeira_data"]) else "—"
                    u_data       = row["ultima_data"].strftime("%d/%m/%Y")   if pd.notna(row["ultima_data"])   else "—"
                    captacao_pct = round(row["leads_total"] / total_leads_geral * 100, 1) if total_leads_geral > 0 else 0
                    bar_cap      = min(int(captacao_pct * 2), 100)
                    _carteira_f  = fmt_brl(float(row["carteira_total"] or 0))
                    _ticket_f    = fmt_brl(float(row["ticket_medio"]  or 0))
                    _base_nome   = str(row["base"])
                    _leads_int   = int(row["leads_total"])
                    _dias_int    = int(row["dias_usada"])

                    _esc = r'\$'
                    exp_label = (
                        f"📦 {_base_nome}  ·  "
                        f"{_leads_int} leads  ·  "
                        f"{_carteira_f.replace('$', _esc)}  ·  "
                        f"ticket: {_ticket_f.replace('$', _esc)}"
                    )
                    with st.expander(exp_label, expanded=False):
                        _df_b_exp = df_hist_filtrado[df_hist_filtrado["base"] == row["base"]]
                        _perc_cfg = [
                            ("🔥", "Quente",        "#ef4444", "🔥 Quente"),
                            ("🌡️", "Morno",         "#f97316", "🌡️ Morno"),
                            ("🧊", "Frio",          "#4f8ef7", "🧊 Frio"),
                            ("❓", "Sem percepção", "#475569", None),
                        ]
                        _perc_counts = _df_b_exp["perception"].value_counts()
                        _badges = ""
                        for _emoji, _label_p, _cor_p, _key_p in _perc_cfg:
                            if _key_p:
                                _cnt = int(_perc_counts.get(_key_p, 0))
                            else:
                                _cnt = int(len(_df_b_exp) - sum(
                                    _perc_counts.get(k, 0)
                                    for k in ["🔥 Quente", "🌡️ Morno", "🧊 Frio"]
                                ))
                            _badges += (
                                f'<div style="background:#0d1f38;border:1px solid {_cor_p}44;'
                                f'border-radius:10px;padding:10px 18px;text-align:center;min-width:90px;">'
                                f'<div style="font-size:20px;line-height:1;">{_emoji}</div>'
                                f'<div style="font-size:26px;font-weight:700;color:{_cor_p};line-height:1.2;">{_cnt}</div>'
                                f'<div style="font-size:11px;color:#7a9cc7;text-transform:uppercase;'
                                f'letter-spacing:.6px;margin-top:3px;">{_label_p}</div>'
                                f'</div>'
                            )

                        st.markdown(f"""
                        <div class="card-status" style="border-left:4px solid {cor};margin-bottom:14px;">
                          <div style="display:flex;align-items:flex-start;gap:20px;flex-wrap:wrap;">
                            <div style="min-width:220px;">
                              <div style="font-size:13px;color:#7a9cc7;text-transform:uppercase;letter-spacing:.8px;font-weight:600;margin-bottom:4px;">Base</div>
                              <div style="font-size:20px;font-weight:700;color:{cor};word-break:break-all;">{_base_nome}</div>
                              <div style="margin-top:10px;display:flex;gap:20px;">
                                <div>
                                  <div style="font-size:13px;color:#7a9cc7;font-weight:500;">Primeiro uso</div>
                                  <div style="font-size:15px;font-weight:700;color:#e8eef8;">{p_data}</div>
                                </div>
                                <div>
                                  <div style="font-size:13px;color:#7a9cc7;font-weight:500;">Último uso</div>
                                  <div style="font-size:15px;font-weight:700;color:#e8eef8;">{u_data}</div>
                                </div>
                                <div>
                                  <div style="font-size:13px;color:#7a9cc7;font-weight:500;">Dias usada</div>
                                  <div style="font-size:15px;font-weight:700;color:#e8eef8;">{_dias_int}</div>
                                </div>
                              </div>
                            </div>
                            <div style="width:1px;background:#152a4a;align-self:stretch;flex-shrink:0;"></div>
                            <div style="display:flex;gap:36px;flex-wrap:wrap;padding-top:4px;">
                              <div>
                                <div style="font-size:12px;color:#7a9cc7;text-transform:uppercase;letter-spacing:.8px;font-weight:600;margin-bottom:4px;">Leads</div>
                                <div style="font-size:28px;font-weight:700;color:#e8eef8;">{_leads_int}</div>
                              </div>
                              <div>
                                <div style="font-size:12px;color:#7a9cc7;text-transform:uppercase;letter-spacing:.8px;font-weight:600;margin-bottom:4px;">Carteira</div>
                                <div style="font-size:24px;font-weight:700;color:#f59e0b;">{_carteira_f}</div>
                              </div>
                              <div>
                                <div style="font-size:12px;color:#7a9cc7;text-transform:uppercase;letter-spacing:.8px;font-weight:600;margin-bottom:4px;">Ticket M&#233;dio</div>
                                <div style="font-size:24px;font-weight:700;color:#4f8ef7;">{_ticket_f}</div>
                              </div>
                              <div style="min-width:100px;">
                                <div style="font-size:12px;color:#7a9cc7;text-transform:uppercase;letter-spacing:.8px;font-weight:600;margin-bottom:4px;">% Capta&#231;&#227;o</div>
                                <div style="font-size:28px;font-weight:700;color:{cor};">{captacao_pct}%</div>
                                <div style="margin-top:4px;background:#152a4a;border-radius:99px;height:5px;width:100%;">
                                  <div style="background:{cor};border-radius:99px;height:5px;width:{bar_cap}%;"></div>
                                </div>
                                <div style="font-size:11px;color:#7a9cc7;margin-top:3px;">do total do per&#237;odo</div>
                              </div>
                            </div>
                          </div>
                        </div>
                        """, unsafe_allow_html=True)

                        st.markdown(
                            f'<div style="display:flex;gap:10px;flex-wrap:wrap;margin-bottom:16px;">'
                            f'{_badges}'
                            f'</div>',
                            unsafe_allow_html=True,
                        )

                        _orig_counts = _df_b_exp["origem"].value_counts()
                        if not _orig_counts.empty:
                            st.markdown("##### 👤 Origens desta base")
                            _orig_html = '<div style="display:flex;gap:8px;flex-wrap:wrap;margin-bottom:16px;">'
                            for _orig_nome, _orig_qtd in _orig_counts.items():
                                _orig_pct = round(_orig_qtd / len(_df_b_exp) * 100, 1)
                                _orig_html += (
                                    f'<div style="background:#0d1f38;border:1px solid #1c2a3d;'
                                    f'border-radius:10px;padding:8px 16px;min-width:100px;text-align:center;">'
                                    f'<div style="font-size:13px;color:#7a9cc7;font-weight:600;'
                                    f'text-transform:uppercase;letter-spacing:.5px;margin-bottom:4px;">'
                                    f'{_orig_nome}</div>'
                                    f'<div style="font-size:26px;font-weight:700;color:{cor};line-height:1;">'
                                    f'{_orig_qtd}</div>'
                                    f'<div style="font-size:11px;color:#7a9cc7;margin-top:2px;">'
                                    f'{_orig_pct}%</div>'
                                    f'</div>'
                                )
                            _orig_html += '</div>'
                            st.markdown(_orig_html, unsafe_allow_html=True)

                        st.markdown("##### 📋 Leads desta base")
                        df_leads_base = _df_b_exp.copy()
                        df_leads_base = df_leads_base.sort_values("data_obj", ascending=False).reset_index(drop=True)
                        _cols_base = {
                            "criado_em":      "Data Captação",
                            "nome":           "Nome",
                            "origem":         "Origem",
                            "atendente":      "Atendente",
                            "status":         "Status",
                            "perception":     "Temperatura",
                            "valor_proposta": "Valor (R$)",
                            "interesse":      "Interesse",
                        }
                        df_leads_disp = df_leads_base[[c for c in _cols_base if c in df_leads_base.columns]].copy()
                        df_leads_disp.rename(columns=_cols_base, inplace=True)
                        if "Valor (R$)" in df_leads_disp.columns:
                            df_leads_disp["Valor (R$)"] = df_leads_base["valor_proposta"].apply(
                                lambda v: fmt_brl(v) if v > 0 else "—"
                            )
                        altura = min(500, 40 + len(df_leads_disp) * 35)
                        st.dataframe(df_leads_disp, use_container_width=True, hide_index=True, height=altura)

                st.markdown("---")
                st.markdown("#### 📈 Evolução de Leads por Base ao Longo do Tempo")
                por_dia_base = (
                    df_hist_filtrado.groupby(["data_obj", "base"])
                    .size()
                    .reset_index(name="leads")
                )
                fig_hist = go.Figure()
                for i, base in enumerate(historico["base"].tolist()):
                    df_b = por_dia_base[por_dia_base["base"] == base].sort_values("data_obj")
                    fig_hist.add_trace(go.Scatter(
                        name=base,
                        x=[d.strftime("%d/%m") for d in df_b["data_obj"]],
                        y=df_b["leads"].tolist(),
                        mode="lines+markers",
                        line=dict(color=CORES_CRM[i % len(CORES_CRM)], width=2),
                        marker=dict(size=6),
                        hovertemplate=f"<b>{base}</b><br>%{{x}}<br>%{{y}} leads<extra></extra>",
                    ))
                fig_hist.update_layout(
                    height=340, margin=dict(t=10, b=20, l=10, r=10),
                    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                    legend=dict(orientation="h", y=1.1, x=0, font=dict(color="#e8eef8", size=12)),
                    xaxis=dict(showgrid=False, color="#7a9cc7", tickfont=dict(color="#e8eef8", size=11)),
                    yaxis=dict(showgrid=True, gridcolor="#152a4a", color="#7a9cc7",
                               tickfont=dict(color="#e8eef8", size=12), zeroline=False),
                )
                st.plotly_chart(fig_hist, use_container_width=True, key="crm_hist_chart")

    with sub_aliases:
        st.markdown("#### ✏️ Corrigir Nomes de Bases")
        st.markdown(
            "<p style='color:#7a9cc7;font-size:13px;margin-top:-4px;'>"
            "Unifique variações de nomes escritos de forma diferente pelos operadores."
            "</p>",
            unsafe_allow_html=True
        )
        st.markdown("---")

        aliases_atuais = load_base_aliases()

        st.markdown("#### ➕ Agrupar Variações sob um Nome Único")
        st.markdown(
            "<p style='color:#7a9cc7;font-size:13px;margin-top:-4px;'>"
            "Selecione <strong>todas</strong> as variações do mesmo nome e defina o nome final. "
            "Isso garante que datas antigas também exibam o nome correto."
            "</p>",
            unsafe_allow_html=True
        )
        bases_existentes = sorted(
            df_todos_raw[df_todos_raw["base"].notna() & (df_todos_raw["base"] != "")]["base"].unique().tolist()
        ) if has_base else []

        with st.form("form_add_alias", border=False):
            bases_de = st.multiselect(
                "Variações a unificar (selecione uma ou mais)",
                options=bases_existentes,
                key="alias_de"
            )
            col_para, col_btn_a = st.columns([4, 1])
            with col_para:
                base_para = st.text_input(
                    "Nome final (como deve aparecer em todo o histórico)",
                    placeholder="Ex: Base SulAmérica",
                    key="alias_para"
                )
            with col_btn_a:
                st.markdown("<div style='margin-top:24px'>", unsafe_allow_html=True)
                salvar = st.form_submit_button("✔ Salvar", use_container_width=True)
                st.markdown("</div>", unsafe_allow_html=True)

            if salvar:
                if not bases_de:
                    st.warning("Selecione ao menos uma variação.")
                elif not base_para.strip():
                    st.warning("Preencha o nome final.")
                elif bases_de == [base_para.strip()]:
                    st.warning("O nome selecionado e o nome final são iguais.")
                else:
                    nome_final = base_para.strip()
                    for variacao in bases_de:
                        if variacao != nome_final:
                            aliases_atuais[variacao] = nome_final
                    save_base_aliases(aliases_atuais)
                    nomes_str = ", ".join(f'"{v}"' for v in bases_de)
                    st.success(f'{nomes_str} → "{nome_final}" salvo(s).')
                    st.rerun(scope="fragment")

        st.markdown("---")

        st.markdown("#### 📋 Correções Ativas")
        if not aliases_atuais:
            st.info("Nenhuma correção cadastrada ainda.")
        else:
            for nome_original, nome_correto in list(aliases_atuais.items()):
                col_orig, col_arr, col_corr, col_del = st.columns([3, 0.5, 3, 1])
                with col_orig:
                    st.markdown(
                        f"<div style='background:#0d1f36;border:1px solid #152a4a;border-radius:8px;"
                        f"padding:8px 12px;color:#ef4444;font-size:13px;font-weight:600;'>"
                        f"{nome_original}</div>",
                        unsafe_allow_html=True
                    )
                with col_arr:
                    st.markdown(
                        "<div style='text-align:center;padding-top:8px;color:#7a9cc7;font-size:18px;'>→</div>",
                        unsafe_allow_html=True
                    )
                with col_corr:
                    st.markdown(
                        f"<div style='background:#0d1f36;border:1px solid #152a4a;border-radius:8px;"
                        f"padding:8px 12px;color:#22c55e;font-size:13px;font-weight:600;'>"
                        f"{nome_correto}</div>",
                        unsafe_allow_html=True
                    )
                with col_del:
                    if st.button("🗑️", key=f"del_alias_{nome_original}", use_container_width=True):
                        del aliases_atuais[nome_original]
                        save_base_aliases(aliases_atuais)
                        st.rerun(scope="fragment")

        st.markdown("---")
        st.markdown("#### ⚠️ Nomes Sem Mapeamento")
        st.markdown(
            "<p style='color:#7a9cc7;font-size:13px;margin-top:-4px;'>"
            "Variações encontradas nos dados que ainda não têm correção definida. "
            "Estes nomes podem aparecer no histórico quando você recua o filtro de data."
            "</p>",
            unsafe_allow_html=True
        )
        if has_base:
            nomes_brutos = set(
                df_todos_raw[df_todos_raw["base"].notna() & (df_todos_raw["base"] != "")]["base"].unique()
            )
            sem_mapa = sorted(nomes_brutos - set(aliases_atuais.keys()))
            if sem_mapa:
                for nome in sem_mapa:
                    st.markdown(
                        f"<div style='background:#1a1a2e;border:1px solid #3a2a0a;border-radius:8px;"
                        f"padding:8px 12px;color:#f59e0b;font-size:13px;font-weight:600;margin-bottom:6px;'>"
                        f"{nome}</div>",
                        unsafe_allow_html=True
                    )
            else:
                st.success("Todos os nomes encontrados nos dados têm mapeamento.")
        else:
            st.info("Nenhum dado de base disponível.")
