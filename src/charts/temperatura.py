import plotly.graph_objects as go

CORES_PERCEPTION = {
    "🔥 Quente": "#ef4444",
    "🌡️ Morno":  "#f59e0b",
    "🧊 Frio":   "#4f8ef7",
}


def grafico_temperatura_pizza(df_atendente):
    """
    Gráfico de pizza com a distribuição de temperatura (quente/morno/frio)
    para os leads com percepção preenchida.
    """
    df_com_temp = df_atendente[df_atendente["perception"] != "Sem percepção"]
    if df_com_temp.empty:
        return None

    contagens = df_com_temp["perception"].value_counts()
    labels = contagens.index.tolist()
    values = contagens.values.tolist()
    cores  = [CORES_PERCEPTION.get(l, "#7a9cc7") for l in labels]

    fig = go.Figure(go.Pie(
        labels=labels, values=values, hole=0.65,
        marker=dict(colors=cores, line=dict(color="rgba(0,0,0,0)", width=0)),
        textinfo="percent",
        textfont=dict(size=11, color="#e8eef8"),
        hovertemplate="<b>%{label}</b><br>%{value} leads (%{percent})<extra></extra>",
    ))
    fig.update_layout(
        margin=dict(t=10, b=10, l=10, r=10),
        showlegend=True,
        legend=dict(
            orientation="v", x=1.02, y=0.5,
            font=dict(color="#e8eef8", size=11),
            bgcolor="rgba(0,0,0,0)",
        ),
        height=280,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
    )
    return fig
