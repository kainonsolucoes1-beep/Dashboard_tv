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


def render_card(icone, valor, label, cor, df=None, status_filtro=None, small=False):
    """Renderiza card de métrica com breakdown opcional por operador."""
    _pad         = "padding:12px 16px;" if small else ""
    _icone_style = "font-size:18px;margin-bottom:4px;display:block;" if small else ""
    _valor_style = f"color:{cor};font-size:30px;" if small else f"color:{cor};"
    _label_style = "font-size:9px;" if small else ""
    if df is not None:
        linhas = linhas_por_operador(df, status_filtro, cor)
        st.markdown(f"""
        <div class="card-status" style="border-left:4px solid {cor};{_pad}display:flex;gap:20px;align-items:flex-start;">
            <div style="min-width:100px;">
                <span class="card-icone" style="{_icone_style}">{icone}</span>
                <div class="card-valor" style="{_valor_style}">{valor}</div>
                <div class="card-label" style="{_label_style}">{label}</div>
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
        <div class="card-status" style="border-left:4px solid {cor};{_pad}">
            <span class="card-icone" style="{_icone_style}">{icone}</span>
            <div class="card-valor" style="{_valor_style}">{valor}</div>
            <div class="card-label" style="{_label_style}">{label}</div>
        </div>
        """, unsafe_allow_html=True)
