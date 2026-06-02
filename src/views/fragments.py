import streamlit as st
import pandas as pd
from datetime import date, timedelta

from src.data.api import (
    fetch_leads_30dias, fetch_leads_80dias, fetch_leads_criticos, fetch_leads_hoje,
    STATUS_MAP,
)
from src.data.transforms import merge_leads_curto, merge_leads_longo
from src.utils.formatters import fmt_brl
from src.utils.time import _ultimo_dia_util
from src.ui.cards import render_card
from src.ui.modals import modal_lead
from src.views.operadores import render_painel_atendente

USER_ATENDENTE = {
    "isaac": "Isaac", "julia": "Julia",
    "leticia": "Leticia", "rodolfo": "Rodolfo",
    "anny": "Anny",
}
USER_COR = {
    "isaac": "#4f8ef7", "julia": "#22c55e",
    "leticia": "#8b5cf6", "rodolfo": "#f59e0b",
    "anny": "#ef4444",
}


def _df_com_filtros_globais(df_base: pd.DataFrame) -> pd.DataFrame:
    data_de      = st.session_state.get("_fv_de",      date.today() - timedelta(days=30))
    data_ate     = st.session_state.get("_fv_ate",     date.today())
    selecionados = st.session_state.get("_fv_origem",  [])
    f_status     = st.session_state.get("_fv_status",  "Todos")
    df = df_base[df_base["data_obj"].apply(lambda d: d is not None and data_de <= d <= data_ate)]
    if selecionados:
        df = df[df["origem"].isin(selecionados)]
    if f_status != "Todos":
        df = df[df["status"] == f_status]
    return df


@st.fragment
def render_funil_rt():
    if "df_funil" not in st.session_state:
        st.markdown(
            "<div style='text-align:center;padding:48px 0 16px;color:#7a9cc7;font-size:14px;'>"
            "Os dados do Funil cobrem 80 dias e são carregados sob demanda."
            "</div>",
            unsafe_allow_html=True
        )
        _, col_c, _ = st.columns([1, 2, 1])
        with col_c:
            if st.button("📊 Carregar Funil de Vendas", use_container_width=True):
                with st.spinner("Buscando 80 dias de dados..."):
                    df, _ = merge_leads_longo()
                    _orig_f = st.session_state.get("_user_origem_filtro")
                    if _orig_f:
                        df = df[df["origem"].str.strip() == _orig_f]
                    st.session_state["df_funil"] = df
                st.rerun()
        return

    df_todos_rt = st.session_state["df_funil"]

    ops_funil = sorted(df_todos_rt["origem"].dropna().unique().tolist()) if not df_todos_rt.empty else []

    _default_funil_de  = date.today() - timedelta(days=30)
    _default_funil_ate = date.today()
    funil_de     = st.session_state.get("_fv_funil_de",     _default_funil_de)
    funil_ate    = st.session_state.get("_fv_funil_ate",    _default_funil_ate)
    funil_origem = st.session_state.get("_fv_funil_origem", ops_funil)
    funil_status = st.session_state.get("_fv_funil_status", "Todos")
    filtro_temp  = st.session_state.get("_fv_funil_temp",   "Todas")
    funil_origem = [o for o in funil_origem if o in ops_funil] or ops_funil

    with st.expander("🔎 Filtros da Aba", expanded=False):
        _fb_col, _ = st.columns([1, 5])
        with _fb_col:
            _funil_atualizar = st.button("🔄 Atualizar", key="funil_refresh", use_container_width=True)
        if _funil_atualizar:
            fetch_leads_80dias.clear()
            fetch_leads_criticos.clear()
            df, _ = merge_leads_longo()
            st.session_state["df_funil"] = df
            st.rerun(scope="fragment")
        with st.form("filtros_funil", border=False):
            ff1, ff2, ff3, ff4, ff5, ff6 = st.columns([1.5, 1.5, 2.5, 2, 1.5, 1])
            with ff1:
                funil_de = st.date_input(
                    "📅 De", value=funil_de, format="DD/MM/YYYY", key="funil_de"
                )
            with ff2:
                funil_ate = st.date_input(
                    "📅 Até", value=funil_ate, format="DD/MM/YYYY", key="funil_ate"
                )
            with ff3:
                funil_origem = st.multiselect(
                    "👤 Origem", options=ops_funil, default=funil_origem, key="funil_origem"
                )
            with ff4:
                funil_status = st.selectbox(
                    "📌 Status", ["Todos"] + list(dict.fromkeys(STATUS_MAP.values())),
                    key="funil_status"
                )
            with ff5:
                filtro_temp = st.selectbox(
                    "🌡️ Temperatura",
                    ["Todas", "🔥 Quente", "🌡️ Morno", "🧊 Frio", "Sem percepção"],
                    key="filtro_temperatura"
                )
            with ff6:
                st.markdown("<div style='margin-top:24px'>", unsafe_allow_html=True)
                submitted_funil = st.form_submit_button("✔ Aplicar", use_container_width=True)
                st.markdown("</div>", unsafe_allow_html=True)
            if submitted_funil:
                funil_de     = st.session_state.get("funil_de",           _default_funil_de)
                funil_ate    = st.session_state.get("funil_ate",          _default_funil_ate)
                funil_origem = st.session_state.get("funil_origem",       ops_funil)
                funil_status = st.session_state.get("funil_status",       "Todos")
                filtro_temp  = st.session_state.get("filtro_temperatura", "Todas")
                st.session_state["_fv_funil_de"]     = funil_de
                st.session_state["_fv_funil_ate"]    = funil_ate
                st.session_state["_fv_funil_origem"] = funil_origem
                st.session_state["_fv_funil_status"] = funil_status
                st.session_state["_fv_funil_temp"]   = filtro_temp

    df_funil = df_todos_rt.copy() if not df_todos_rt.empty else df_todos_rt
    if not df_funil.empty:
        df_funil = df_funil[df_funil["data_obj"].apply(
            lambda d: d is not None and funil_de <= d <= funil_ate
        )]
        if funil_origem:
            df_funil = df_funil[df_funil["origem"].isin(funil_origem)]
        _STATUS_ENCERRADOS = {"Venda Realizada", "Venda não Realizada"}
        if funil_status == "Todos":
            df_funil = df_funil[~df_funil["status"].isin(_STATUS_ENCERRADOS)]
        else:
            df_funil = df_funil[df_funil["status"] == funil_status]
        if filtro_temp != "Todas":
            df_funil = df_funil[df_funil["perception"] == filtro_temp]

    st.markdown("---")

    _funil_user     = st.session_state.get("username", "")
    _funil_is_admin = (_funil_user == "lucas")

    if not _funil_is_admin:
        _nome_at = USER_ATENDENTE.get(_funil_user, _funil_user.capitalize())
        _cor_at  = USER_COR.get(_funil_user, "#4f8ef7")
        render_painel_atendente(df_funil, _nome_at, _cor_at, foto_path=None)
    else:
        df_giovanna = df_funil[df_funil["atendente"].str.contains("Giovanna", case=False, na=False)]
        df_rayanna  = df_funil[df_funil["atendente"].str.contains("Rayanna",  case=False, na=False)]
        col_gio, col_sep, col_ray = st.columns([1, 0.04, 1])
        with col_gio:
            render_painel_atendente(df_giovanna, "Giovanna", "#8b5cf6", foto_path="fotos/giovanna.jpg")
        with col_ray:
            render_painel_atendente(df_rayanna,  "Rayanna",  "#f59e0b", foto_path="fotos/rayanna.jpg")

    st.markdown("---")
    _titulo_cons = "#### 📊 Meu Consolidado" if not _funil_is_admin else "#### 📊 Consolidado das Atendentes"
    st.markdown(_titulo_cons)

    total_carteira = df_funil["valor_proposta"].sum()
    leads_com_val  = int((df_funil["valor_proposta"] > 0).sum())
    ticket_medio   = total_carteira / leads_com_val if leads_com_val > 0 else 0

    rc1, rc2, rc3, rc4 = st.columns(4)
    with rc1:
        render_card("💰", fmt_brl(total_carteira), "Total em Carteira", "#22c55e", small=True)
    with rc2:
        render_card("🎟️", fmt_brl(ticket_medio), "Ticket Médio", "#4f8ef7", small=True)
    with rc3:
        render_card("🔥", int((df_funil["perception"] == "🔥 Quente").sum()), "Leads Quentes", "#ef4444", small=True)
    with rc4:
        render_card("🌡️", int((df_funil["perception"] == "🌡️ Morno").sum()), "Leads Mornos", "#f59e0b", small=True)


def render_hoje_rt():
    st.markdown("#### 📅 Hoje")
    df_base, _ = fetch_leads_hoje()
    if df_base.empty:
        return

    selecionados = st.session_state.get("visao_origem", [])
    hoje            = date.today()
    ultimo_util     = _ultimo_dia_util(hoje)

    nomes_dia = {0:"segunda",1:"terça",2:"quarta",3:"quinta",4:"sexta"}
    nome_util = nomes_dia.get(ultimo_util.weekday(), str(ultimo_util))

    _ORIGENS_SDR_HOJE = {"julia", "isaac", "leticia", "rodolfo", "maria eduarda", "clara", "kauany", "o2 solution", "gabrieli"}
    df_base_hoje = df_base[
        df_base["origem"].str.lower().str.strip().isin(_ORIGENS_SDR_HOJE)
    ].copy()
    if selecionados:
        df_base_hoje = df_base_hoje[df_base_hoje["origem"].isin(selecionados)]

    df_ontem_v = df_base_hoje[df_base_hoje["data_obj"].apply(lambda d: d == ultimo_util)]
    df_hoje_v  = df_base_hoje[df_base_hoje["data_obj"].apply(lambda d: d == hoje)]

    leads_hoje  = len(df_hoje_v)
    leads_ontem = len(df_ontem_v)
    diferenca   = leads_hoje - leads_ontem

    if diferenca > 0:
        seta, cor_seta = f"↑ +{diferenca} que {nome_util}", "#22c55e"
    elif diferenca < 0:
        seta, cor_seta = f"↓ {diferenca} que {nome_util}", "#ef4444"
    else:
        seta, cor_seta = f"= igual a {nome_util}", "#7a9cc7"

    if df_hoje_v.empty or "origem" not in df_hoje_v.columns:
        operadores_hoje = pd.DataFrame(columns=["origem", "qtd"])
    else:
        operadores_hoje = (
            df_hoje_v.groupby("origem").size()
            .reset_index(name="qtd").sort_values("qtd", ascending=False)
        )

    META_DIARIA = 10
    progresso = min(leads_hoje / META_DIARIA, 1.0)
    pct_meta  = int(progresso * 100)
    cor_meta  = "#22c55e" if progresso >= 1.0 else "#f59e0b" if progresso >= 0.5 else "#ef4444"
    h1, h2 = st.columns(2)

    with h1:
        linhas_op = ""
        for _, row in operadores_hoje.iterrows():
            linhas_op += (
                '<div style="display:flex;justify-content:space-between;align-items:center;'
                'padding:8px 0;border-bottom:1px solid var(--border);">'
                f'<span style="color:var(--text-main);font-size:18px;font-weight:500;">👤 {row["origem"]}</span>'
                f'<span style="color:#4f8ef7;font-weight:700;font-size:26px;line-height:1;">{row["qtd"]}</span>'
                '</div>'
            )
        if not linhas_op:
            linhas_op = '<span style="color:var(--text-sub);font-size:15px;">Nenhum lead hoje</span>'

        st.markdown(
            '<div class="card-total" style="display:flex;gap:28px;align-items:flex-start;">'
            '<div style="min-width:130px;">'
            '<span class="card-icone">🌅</span>'
            f'<div class="card-valor" style="color:#4f8ef7;">{leads_hoje}</div>'
            '<div class="card-label">Leads Captados Hoje</div>'
            f'<div style="margin-top:10px;font-size:15px;font-weight:600;color:{cor_seta};">{seta}</div>'
            f'<div style="font-size:13px;color:var(--text-sub);margin-top:4px;">{nome_util.capitalize()}: {leads_ontem} leads</div>'
            '</div>'
            '<div style="width:1px;background:var(--border);align-self:stretch;margin:4px 0;"></div>'
            '<div style="flex:1;min-width:0;padding-top:4px;">'
            '<div style="color:var(--text-sub);font-size:12px;font-weight:600;text-transform:uppercase;'
            'letter-spacing:.7px;margin-bottom:10px;">Por Operador</div>'
            + linhas_op +
            '</div></div>',
            unsafe_allow_html=True
        )

    with h2:
        _circ    = 213.63
        _offset  = _circ * (1 - progresso)
        _rest    = max(0, META_DIARIA - leads_hoje)
        _meta_txt = "Meta atingida!" if progresso >= 1.0 else f"{_rest} lead{'s' if _rest != 1 else ''} restante{'s' if _rest != 1 else ''}"
        st.markdown(f"""
        <div class="card-status" style="border-left:4px solid {cor_meta};">
            <div style="display:flex;align-items:center;gap:20px;">
                <svg width="84" height="84" viewBox="0 0 84 84" style="flex-shrink:0;">
                    <circle cx="42" cy="42" r="34" fill="none" stroke="#1c2a3d" stroke-width="7"/>
                    <circle cx="42" cy="42" r="34" fill="none" stroke="{cor_meta}" stroke-width="7"
                        stroke-dasharray="{_circ:.2f}" stroke-dashoffset="{_offset:.2f}"
                        stroke-linecap="round" transform="rotate(-90 42 42)"/>
                    <text x="42" y="47" text-anchor="middle" fill="{cor_meta}"
                        font-size="15" font-weight="700" font-family="DM Sans,sans-serif">{pct_meta}%</text>
                </svg>
                <div>
                    <div class="card-valor" style="color:{cor_meta};font-size:38px;">{leads_hoje} / {META_DIARIA}</div>
                    <div class="card-label">Meta Diária de Leads</div>
                    <div style="color:{cor_meta};font-size:12px;margin-top:8px;font-weight:600;">{_meta_txt}</div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    if progresso >= 1.0:
        _today_str = str(date.today())
        if st.session_state.get("meta_rocket_date") != _today_str:
            st.session_state["meta_rocket_date"] = _today_str
            st.markdown("""
            <style>
            @keyframes foguete-voo {
                0%   { transform: translate(0, 0) rotate(-45deg);           opacity: 1; }
                70%  { transform: translate(-65vw, -38vh) rotate(-45deg);   opacity: 1; }
                100% { transform: translate(-130vw, -60vh) rotate(-45deg);  opacity: 0; }
            }
            #foguete-meta {
                position: fixed;
                right: -140px;
                bottom: 18vh;
                font-size: 110px;
                pointer-events: none;
                z-index: 99999;
                animation: foguete-voo 3.8s cubic-bezier(0.2, 0.6, 0.3, 1) forwards;
                filter: drop-shadow(0 0 30px rgba(245, 158, 11, 0.9))
                        drop-shadow(0 0 60px rgba(245, 158, 11, 0.4));
            }
            </style>
            <span id="foguete-meta">🚀</span>
            """, unsafe_allow_html=True)


@st.fragment
def render_leads_rt():
    df_todos_rt, _ = merge_leads_curto()
    df_rt = _df_com_filtros_globais(df_todos_rt) if not df_todos_rt.empty else df_todos_rt

    _hd_leads, _btn_leads = st.columns([5, 1])
    with _hd_leads:
        st.markdown("#### 📋 Leads Recentes")
        st.markdown(
            "<p style='color:#7a9cc7;font-size:13px;margin-top:-4px;'>"
            f"Exibindo os 100 leads mais recentes do período filtrado ({len(df_rt)} no total)."
            "</p>",
            unsafe_allow_html=True
        )
    with _btn_leads:
        st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)
        _leads_atualizar = st.button("🔄 Atualizar", key="leads_refresh", use_container_width=True)
    if _leads_atualizar:
        fetch_leads_30dias.clear()
        fetch_leads_80dias.clear()
        fetch_leads_criticos.clear()
        fetch_leads_hoje.clear()
        st.rerun(scope="fragment")

    df_sorted_orig = df_rt.copy()
    df_sorted_orig["_sort"] = pd.to_datetime(
        df_sorted_orig["atualizado_em"], format="%d/%m/%Y %H:%M", errors="coerce"
    )
    df_sorted_orig = (
        df_sorted_orig.sort_values("_sort", ascending=False)
        .drop(columns=["_sort"])
        .reset_index(drop=True)
        .head(100)
    )
    if "em_atraso" in df_sorted_orig.columns:
        df_sorted_orig["Atraso"] = df_sorted_orig["em_atraso"].apply(lambda x: "🔴 Em atraso" if x else "")
    else:
        df_sorted_orig["Atraso"] = ""

    col_labels = {
        "Atraso":         "Situação",
        "nome":           "Nome",
        "status":         "Status",
        "perception":     "Temperatura",
        "valor_proposta": "Valor (R$)",
        "atendente":      "Atendente",
        "origem":         "Operador",
        "interesse":      "Interesse",
        "criado_em":      "Cadastrado em",
        "atualizado_em":  "Última Atualização",
    }
    df_display = df_sorted_orig.copy()
    df_display["valor_proposta"] = df_display["valor_proposta"].apply(
        lambda v: fmt_brl(v) if v > 0 else "—"
    )
    df_display = df_display[list(col_labels.keys())].rename(columns=col_labels)

    _sc_rt, _ = st.columns([1, 2])
    with _sc_rt:
        _term_rt = st.text_input(
            "Pesquisar", placeholder="🔍 Busque seus leads aqui...",
            label_visibility="collapsed", key="search_leads_rt"
        )
    if _term_rt:
        _mask_rt = df_display.apply(lambda c: c.astype(str).str.contains(_term_rt, case=False, na=False)).any(axis=1)
        df_display     = df_display[_mask_rt].reset_index(drop=True)
        df_sorted_orig = df_sorted_orig[_mask_rt].reset_index(drop=True)

    st.caption("💡 Clique em uma linha para ver os detalhes completos do lead.")
    evt = st.dataframe(
        df_display,
        use_container_width=True,
        hide_index=True,
        height=500,
        selection_mode="single-row",
        on_select="rerun",
        key="tabela_leads_rt",
    )
    sel = evt.selection.rows
    if sel and st.session_state.get("modal_leads_rt") != sel[0]:
        st.session_state["modal_leads_rt"] = sel[0]
        modal_lead(df_sorted_orig.iloc[sel[0]])
    if not sel:
        st.session_state.pop("modal_leads_rt", None)
