import plotly.graph_objects as go

CORES_BASES = [
    "#4f8ef7", "#22c55e", "#f59e0b", "#8b5cf6",
    "#ef4444", "#f97316", "#06b6d4", "#ec4899",
]


def grafico_rosca_bases(df):
    """Rosca agrupada por base de clientes (campo 'base')."""
    import pandas as pd
    col = "base"
    if col not in df.columns:
        return None
    serie = df[col].fillna("Sem base").replace("", "Sem base")
    counts = serie.value_counts()
    labels = counts.index.tolist()
    values = counts.values.tolist()
    colors = [CORES_BASES[i % len(CORES_BASES)] for i in range(len(labels))]
    fig = go.Figure(go.Pie(
        labels=labels, values=values, hole=0.68,
        domain=dict(x=[0, 0.55]),
        marker=dict(colors=colors, line=dict(color="rgba(0,0,0,0)", width=0)),
        textinfo="value+percent",
        textfont=dict(size=11, color="#e8eef8"),
        hovertemplate="<b>%{label}</b><br>%{value} leads (%{percent})<extra></extra>",
    ))
    fig.update_layout(
        margin=dict(t=10, b=10, l=10, r=10),
        showlegend=True,
        legend=dict(
            orientation="v", x=0.58, y=0.5,
            xanchor="left", yanchor="middle",
            font=dict(color="#e8eef8", size=13),
            bgcolor="rgba(0,0,0,0)",
        ),
        height=300,
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
    )
    return fig


CORES_STATUS = {
    "Pendente":             "#4f8ef7",
    "Agendado":             "#f59e0b",
    "Proposta Enviada":     "#8b5cf6",
    "Aguardando Pagamento": "#f97316",
    "Venda Realizada":      "#22c55e",
    "Venda não Realizada":  "#ef4444",
}


def grafico_rosca_dashboard(df):
    """Versão com labels externos e linhas — estilo dashboard executivo."""
    counts = df["status"].value_counts()
    labels = counts.index.tolist()
    values = counts.values.tolist()
    colors = [CORES_STATUS.get(l, "#aaa") for l in labels]
    fig = go.Figure(go.Pie(
        labels=labels, values=values, hole=0.60,
        marker=dict(colors=colors, line=dict(color="#0d1f38", width=2)),
        textinfo="label+percent",
        textposition="outside",
        textfont=dict(size=11, color="#e8eef8"),
        hovertemplate="<b>%{label}</b><br>%{value} leads (%{percent})<extra></extra>",
        showlegend=False,
    ))
    fig.update_layout(
        margin=dict(t=20, b=20, l=20, r=20),
        height=300,
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
    )
    return fig


def grafico_rosca(df):
    counts = df["status"].value_counts()
    labels = counts.index.tolist()
    values = counts.values.tolist()
    colors = [CORES_STATUS.get(l, "#aaa") for l in labels]
    fig = go.Figure(go.Pie(
        labels=labels, values=values, hole=0.68,
        domain=dict(x=[0, 0.58]),
        marker=dict(colors=colors, line=dict(color="rgba(0,0,0,0)", width=0)),
        textinfo="percent",
        textfont=dict(size=11, color="#e8eef8"),
        hovertemplate="<b>%{label}</b><br>%{value} leads (%{percent})<extra></extra>",
    ))
    fig.update_layout(
        margin=dict(t=10, b=10, l=10, r=10),
        showlegend=True,
        legend=dict(
            orientation="v", x=0.61, y=0.5,
            xanchor="left", yanchor="middle",
            font=dict(color="#e8eef8", size=15),
            bgcolor="rgba(0,0,0,0)",
        ),
        height=280,
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
    )
    return fig
