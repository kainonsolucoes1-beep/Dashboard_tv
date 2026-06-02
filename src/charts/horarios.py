import plotly.graph_objects as go
import pandas as pd

HORAS = list(range(9, 19))  # 09h – 18h (horário comercial)


def _hora(s: str):
    try:
        return int(str(s).split(" ")[1].split(":")[0])
    except (IndexError, ValueError, AttributeError):
        return None


def grafico_horarios_pico(df: pd.DataFrame):
    horas_captura = df["criado_em"].apply(_hora).dropna().astype(int)
    horas_captura = horas_captura[horas_captura.isin(HORAS)]

    df_vendas = df[df["status"] == "Venda Realizada"].copy()
    horas_venda = df_vendas["atualizado_em"].apply(_hora).dropna().astype(int)
    horas_venda = horas_venda[horas_venda.isin(HORAS)]

    cap_counts = [int((horas_captura == h).sum()) for h in HORAS]
    vnd_counts = [int((horas_venda == h).sum()) for h in HORAS]
    conv_counts = [
        round(vnd_counts[i] / cap_counts[i] * 100, 1) if cap_counts[i] > 0 else 0
        for i in range(len(HORAS))
    ]

    def _top3(counts):
        pairs = sorted(enumerate(counts), key=lambda x: x[1], reverse=True)
        return {HORAS[i] for i, c in pairs[:3] if c > 0}

    top3_cap = _top3(cap_counts)
    top3_vnd = _top3(vnd_counts)

    colors_cap = ["#f59e0b" if h in top3_cap else "#4f8ef7" for h in HORAS]
    colors_vnd = ["#16a34a" if h in top3_vnd else "#22c55e" for h in HORAS]
    labels = [f"{h:02d}h" for h in HORAS]

    fig = go.Figure()
    fig.add_trace(go.Bar(
        name="Capturas",
        x=labels,
        y=cap_counts,
        marker_color=colors_cap,
        yaxis="y",
        hovertemplate="<b>%{x}</b><br>%{y} capturas<extra></extra>",
    ))
    fig.add_trace(go.Bar(
        name="Vendas",
        x=labels,
        y=vnd_counts,
        marker_color=colors_vnd,
        yaxis="y",
        hovertemplate="<b>%{x}</b><br>%{y} vendas<extra></extra>",
    ))
    fig.add_trace(go.Scatter(
        name="Conversão (%)",
        x=labels,
        y=conv_counts,
        mode="lines+markers",
        line=dict(color="#e879f9", width=2, dash="dot"),
        marker=dict(size=6, color="#e879f9"),
        yaxis="y2",
        hovertemplate="<b>%{x}</b><br>%{y}% conversão<extra></extra>",
    ))

    fig.update_layout(
        barmode="group",
        margin=dict(t=20, b=20, l=10, r=50),
        height=320,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        legend=dict(orientation="h", y=1.12, x=0, font=dict(color="#e8eef8", size=12)),
        xaxis=dict(showgrid=False, color="#7a9cc7", tickfont=dict(color="#e8eef8", size=11)),
        yaxis=dict(showgrid=True, gridcolor="#152a4a", color="#7a9cc7",
                   tickfont=dict(color="#e8eef8", size=12), zeroline=False),
        yaxis2=dict(
            overlaying="y", side="right",
            showgrid=False, tickfont=dict(color="#e879f9", size=11),
            zeroline=False, rangemode="tozero",
        ),
        hovermode="x unified",
    )
    return fig, top3_cap, top3_vnd, cap_counts, vnd_counts
