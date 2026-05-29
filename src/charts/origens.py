import plotly.graph_objects as go


def grafico_origens(df):
    vendas  = df[df["status"] == "Venda Realizada"]
    ranking = vendas["origem"].value_counts().head(10)
    fig = go.Figure(go.Bar(
        x=ranking.values.tolist(), y=ranking.index.tolist(), orientation="h",
        marker=dict(
            color=ranking.values.tolist(),
            colorscale=[[0, "#050b14"], [1, "#22c55e"]],
            line=dict(color="#152a4a", width=1)
        ),
        text=ranking.values.tolist(), textposition="outside",
        textfont=dict(color="#e8eef8", size=12),
        hovertemplate="<b>%{y}</b><br>%{x} vendas<extra></extra>",
    ))
    fig.update_layout(
        margin=dict(t=10, b=10, l=10, r=40), height=280,
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(showgrid=True, gridcolor="#152a4a", color="#7a9cc7", zeroline=False),
        yaxis=dict(color="#e8eef8", autorange="reversed"),
    )
    return fig
