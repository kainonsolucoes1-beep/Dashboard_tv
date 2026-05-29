import plotly.graph_objects as go
import streamlit as st

from src.ui.cards import render_card


def grafico_ranking_vendas(dados: dict):
    """Barras verticais de ranking de vendas — top performer em verde, demais em azul."""
    if not dados:
        return None
    operadores = list(dados.keys())
    valores    = list(dados.values())
    max_val    = max(valores)
    cores      = ["#1D9E75" if v == max_val else "#378ADD" for v in valores]

    fig = go.Figure(go.Bar(
        x=operadores,
        y=valores,
        marker=dict(
            color=cores,
            line=dict(color="rgba(0,0,0,0)", width=0),
        ),
        text=valores,
        textposition="outside",
        textfont=dict(color="#e8eef8", size=14, family="DM Sans"),
        hovertemplate="<b>%{x}</b><br>%{y} venda(s)<extra></extra>",
    ))
    fig.update_layout(
        margin=dict(t=30, b=10, l=10, r=10),
        height=300,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(
            color="#e8eef8",
            tickfont=dict(size=13, family="DM Sans", color="#e8eef8"),
            showgrid=False,
            zeroline=False,
        ),
        yaxis=dict(
            showgrid=True,
            gridcolor="#152a4a",
            color="#7a9cc7",
            tickfont=dict(size=11),
            zeroline=False,
            dtick=1,
        ),
        bargap=0.45,
    )
    return fig


def render_ranking_vendas(dados: dict | None = None):
    """
    Cards de métrica + gráfico de barras de ranking de vendas por operador.
    `dados`: dict {operador: qtd_vendas}. Usa exemplo se None.
    """
    if dados is None:
        dados = {"Indicação": 2, "Isaac": 1, "Orgânico": 1}

    total_vendas      = sum(dados.values())
    top_operador      = max(dados, key=dados.get) if dados else "—"
    operadores_ativos = len(dados)

    st.markdown("#### 🏆 Ranking de Vendas")

    c1, c2, c3 = st.columns(3)
    with c1:
        render_card("🏆", total_vendas,       "Total de Vendas",   "#1D9E75")
    with c2:
        render_card("⭐", top_operador,        "Top Operador",      "#378ADD")
    with c3:
        render_card("👥", operadores_ativos,   "Operadores Ativos", "#f59e0b")

    fig = grafico_ranking_vendas(dados)
    if fig:
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
