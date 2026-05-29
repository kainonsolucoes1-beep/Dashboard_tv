import plotly.graph_objects as go
import pandas as pd


def _hora(s: str):
    try:
        return int(str(s).split(" ")[1].split(":")[0])
    except (IndexError, ValueError, AttributeError):
        return None


def grafico_horarios_pico(df: pd.DataFrame) -> go.Figure:
    horas_captura = df["criado_em"].apply(_hora).dropna().astype(int)

    df_vendas = df[df["status"] == "Venda Realizada"].copy()
    horas_venda = df_vendas["atualizado_em"].apply(_hora).dropna().astype(int)

    horas = list(range(24))
    cap_counts = [int((horas_captura == h).sum()) for h in horas]
    vnd_counts = [int((horas_venda == h).sum()) for h in horas]

    top3_cap = set(sorted(range(24), key=lambda h: cap_counts[h], reverse=True)[:3])
    top3_vnd = set(sorted(range(24), key=lambda h: vnd_counts[h], reverse=True)[:3])

    colors_cap = ["#f59e0b" if h in top3_cap else "#4f8ef7" for h in horas]
    colors_vnd = ["#16a34a" if h in top3_vnd else "#22c55e" for h in horas]

    labels = [f"{h:02d}h" for h in horas]

    fig = go.Figure()
    fig.add_trace(go.Bar(
        name="Capturas",
        x=labels,
        y=cap_counts,
        marker_color=colors_cap,
        hovertemplate="<b>%{x}</b><br>%{y} capturas<extra></extra>",
    ))
    fig.add_trace(go.Bar(
        name="Vendas",
        x=labels,
        y=vnd_counts,
        marker_color=colors_vnd,
        hovertemplate="<b>%{x}</b><br>%{y} vendas<extra></extra>",
    ))

    fig.update_layout(
        barmode="group",
        margin=dict(t=20, b=20, l=10, r=20),
        height=320,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        legend=dict(orientation="h", y=1.12, x=0, font=dict(color="#e8eef8", size=13)),
        xaxis=dict(showgrid=False, color="#7a9cc7", tickfont=dict(color="#e8eef8", size=11)),
        yaxis=dict(showgrid=True, gridcolor="#152a4a", color="#7a9cc7",
                   tickfont=dict(color="#e8eef8", size=12), zeroline=False),
        hovermode="x unified",
    )
    return fig, top3_cap, top3_vnd, cap_counts, vnd_counts
