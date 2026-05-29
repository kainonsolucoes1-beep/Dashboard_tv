import streamlit as st


def linhas_por_operador(df, status_filtro, cor):
    """Gera linhas HTML de contagem por origem (operador) para um dado status."""
    df_f = df[df["status"] == status_filtro] if status_filtro else df
    ranking = (
        df_f.groupby("origem").size()
        .reset_index(name="qtd")
        .sort_values("qtd", ascending=False)
    )
    if ranking.empty:
        return '<span style="color:#7a9cc7;font-size:12px;">Sem registros</span>'
    html = ""
    for _, row in ranking.iterrows():
        html += (
            '<div style="display:flex;justify-content:space-between;align-items:center;'
            'padding:6px 0;border-bottom:1px solid var(--border);">'
            f'<span style="color:var(--text-main);font-size:14px;font-weight:500;">👤 {row["origem"]}</span>'
            f'<span style="color:{cor};font-weight:700;font-size:20px;line-height:1;">{row["qtd"]}</span>'
            '</div>'
        )
    return html


def render_card(icone, valor, label, cor, df=None, status_filtro=None):
    """Renderiza card de métrica com breakdown opcional por operador."""
    if df is not None:
        linhas = linhas_por_operador(df, status_filtro, cor)
        st.markdown(f"""
        <div class="card-status" style="border-left:4px solid {cor};display:flex;gap:20px;align-items:flex-start;">
            <div style="min-width:100px;">
                <span class="card-icone">{icone}</span>
                <div class="card-valor" style="color:{cor};">{valor}</div>
                <div class="card-label">{label}</div>
            </div>
            <div style="width:1px;background:var(--border);align-self:stretch;margin:4px 0;"></div>
            <div style="flex:1;min-width:0;padding-top:4px;">
                <div style="color:var(--text-sub);font-size:12px;font-weight:600;text-transform:uppercase;
                            letter-spacing:.7px;margin-bottom:8px;">Por Operador</div>
                {linhas}
            </div>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown(f"""
        <div class="card-status" style="border-left:4px solid {cor};">
            <span class="card-icone">{icone}</span>
            <div class="card-valor" style="color:{cor};">{valor}</div>
            <div class="card-label">{label}</div>
        </div>
        """, unsafe_allow_html=True)
