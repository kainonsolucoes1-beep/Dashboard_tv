import plotly.graph_objects as go

from src.charts.rosca import CORES_STATUS


def grafico_funil_status(df_atendente):
    """
    Gráfico de funil mostrando a quantidade de leads em cada etapa do status.
    O % exibido é individual de cada status em relação ao total de leads,
    e não acumulado em relação ao topo do funil.
    """
    ordem = [
        "Pendente",
        "Agendado",
        "Proposta Enviada",
        "Aguardando Pagamento",
    ]
    contagens = df_atendente["status"].value_counts()
    labels = [s for s in ordem if s in contagens.index]
    values = [contagens[s] for s in labels]
    cores  = [CORES_STATUS[s] for s in labels]

    total = len(df_atendente)

    textos = [
        f"{v}  ({v / total * 100:.1f}%)" if total > 0 else str(v)
        for v in values
    ]

    fig = go.Figure(go.Funnel(
        y=labels,
        x=values,
        textinfo="none",
        text=textos,
        textposition="inside",
        textfont=dict(color="#e8eef8", size=13, family="DM Sans"),
        marker=dict(color=cores, line=dict(color="#050b14", width=1)),
        connector=dict(line=dict(color="#152a4a", width=1)),
        hovertemplate="<b>%{y}</b><br>%{x} leads<br>%{text}<extra></extra>",
    ))
    fig.update_layout(
        margin=dict(t=10, b=10, l=10, r=10),
        height=max(160, len(labels) * 56),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        yaxis=dict(color="#e8eef8"),
    )
    return fig
