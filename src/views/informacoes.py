import streamlit as st

from src.data.transforms import merge_leads_longo
from src.data.api import fetch_leads_30dias, fetch_leads_80dias, fetch_leads_criticos, fetch_leads_hoje


@st.fragment
def render_informacoes():
    df, _ = merge_leads_longo()
    if df.empty:
        st.warning("Nenhum dado disponível.")
        return

    _hd, _btn = st.columns([5, 1])
    with _hd:
        st.markdown("#### ℹ️ Informações dos Leads")
        st.markdown(
            "<p style='color:#7a9cc7;font-size:13px;margin-top:-4px;'>"
            f"Exibindo leads com CNPJ, cidade ou idade preenchidos ({len(df)} leads no total)."
            "</p>",
            unsafe_allow_html=True,
        )
    with _btn:
        st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)
        if st.button("🔄 Atualizar", key="info_refresh", use_container_width=True):
            fetch_leads_30dias.clear()
            fetch_leads_80dias.clear()
            fetch_leads_criticos.clear()
            fetch_leads_hoje.clear()
            st.rerun(scope="fragment")

    _sc, _ = st.columns([1, 2])
    with _sc:
        _term = st.text_input(
            "Pesquisar", placeholder="🔍 Busque por nome, cidade, CNPJ...",
            label_visibility="collapsed", key="search_info"
        )

    col_labels = {
        "nome":      "Nome",
        "status":    "Status",
        "atendente": "Atendente",
        "criado_em": "Cadastrado em",
        "cnpj":      "CNPJ",
        "cidade":    "Cidade",
        "estado":    "UF",
        "idade":     "Idades",
    }

    for col in col_labels:
        if col not in df.columns:
            df[col] = ""

    df_display = df[list(col_labels.keys())].copy().rename(columns=col_labels)

    if _term:
        _mask = df_display.apply(
            lambda c: c.astype(str).str.contains(_term, case=False, na=False)
        ).any(axis=1)
        df_display = df_display[_mask].reset_index(drop=True)

    st.caption("💡 Leads ordenados do mais recente para o mais antigo.")
    st.dataframe(
        df_display,
        use_container_width=True,
        hide_index=True,
        height=600,
    )
