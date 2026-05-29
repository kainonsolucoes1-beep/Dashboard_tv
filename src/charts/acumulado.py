import plotly.graph_objects as go


def grafico_acumulado(df, operadores):
    CORES_OP = ["#4f8ef7", "#22c55e", "#f59e0b", "#8b5cf6", "#ef4444", "#f97316"]
    fig = go.Figure()
    for i, operador in enumerate(operadores):
        df_op = df[df["origem"] == operador].copy()
        df_op = df_op[df_op["data_obj"].notna()]
        if df_op.empty:
            continue
        por_dia = df_op.groupby("data_obj").size().reset_index(name="leads")
        por_dia = por_dia.sort_values("data_obj")
        por_dia["acumulado"] = por_dia["leads"].cumsum()
        cor = CORES_OP[i % len(CORES_OP)]
        fig.add_trace(go.Scatter(
            x=por_dia["data_obj"].tolist(), y=por_dia["acumulado"].tolist(),
            name=operador, mode="lines+markers",
            line=dict(color=cor, width=3),
            marker=dict(color=cor, size=8, symbol="circle"),
            hovertemplate=f"<b>{operador}</b><br>%{{x|%d/%m}}<br>%{{y}} leads acumulados<extra></extra>",
        ))
    fig.update_layout(
        margin=dict(t=20, b=20, l=10, r=20), height=320,
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        legend=dict(orientation="h", y=1.1, x=0, font=dict(color="#e8eef8", size=13)),
        xaxis=dict(showgrid=True, gridcolor="#152a4a", color="#7a9cc7",
                   tickformat="%d/%m", tickfont=dict(color="#e8eef8", size=12)),
        yaxis=dict(showgrid=True, gridcolor="#152a4a", color="#7a9cc7",
                   tickfont=dict(color="#e8eef8", size=12), zeroline=False),
        hovermode="x unified",
    )
    return fig
