import streamlit as st
import pandas as pd
from datetime import datetime, date, timedelta

from src.data.api import fetch_leads_30dias, fetch_leads_criticos
from src.data.transforms import merge_leads_curto


@st.fragment
def render_estagio_lead():
    _est_h, _est_btn = st.columns([5, 1])
    with _est_btn:
        _est_atualizar = st.button("🔄 Atualizar", key="estagio_refresh", use_container_width=True)
    if _est_atualizar:
        fetch_leads_30dias.clear()
        fetch_leads_criticos.clear()
        st.rerun(scope="fragment")

    df_todos, _ = merge_leads_curto()
    if df_todos.empty:
        st.info("Nenhum dado disponível.")
        return

    origens_disp    = sorted(df_todos["origem"].dropna().unique().tolist())
    atendentes_disp = sorted(df_todos["atendente"].dropna().unique().tolist())

    _default_de = date.today() - timedelta(days=30)
    _default_ate = date.today()
    sel_origem = st.session_state.get("est_origem", [])
    sel_atend  = st.session_state.get("est_atend", [])
    est_de     = st.session_state.get("est_de", _default_de)
    est_ate    = st.session_state.get("est_ate", _default_ate)

    with st.expander("🔍 Filtros — Origem/SDR · Atendente · Período", expanded=False):
        with st.form("filtros_estagio", border=False):
            fc1, fc2, fc3, fc4, fc5 = st.columns([2, 2, 1.5, 1.5, 1])
            with fc1:
                sel_origem = st.multiselect(
                    "🎯 Origem/SDR", options=origens_disp, default=sel_origem, key="est_origem"
                )
            with fc2:
                sel_atend = st.multiselect(
                    "🎧 Atendente", options=atendentes_disp, default=sel_atend, key="est_atend"
                )
            with fc3:
                est_de = st.date_input(
                    "📅 De", value=est_de, format="DD/MM/YYYY", key="est_de"
                )
            with fc4:
                est_ate = st.date_input(
                    "📅 Até", value=est_ate, format="DD/MM/YYYY", key="est_ate"
                )
            with fc5:
                st.markdown("<div style='margin-top:24px'>", unsafe_allow_html=True)
                submitted = st.form_submit_button("✔ Aplicar", use_container_width=True)
                st.markdown("</div>", unsafe_allow_html=True)
            if submitted:
                sel_origem = st.session_state.get("est_origem", [])
                sel_atend  = st.session_state.get("est_atend", [])
                est_de     = st.session_state.get("est_de", _default_de)
                est_ate    = st.session_state.get("est_ate", _default_ate)

    df = df_todos.copy()
    df = df[df["data_obj"].apply(lambda d: d is not None and est_de <= d <= est_ate)]
    if sel_origem:
        df = df[df["origem"].isin(sel_origem)]
    if sel_atend:
        df = df[df["atendente"].isin(sel_atend)]

    if df.empty:
        st.info("Nenhum lead no período/filtro selecionado.")
        return

    def _dias_entre(criado, atualizado):
        try:
            fmt = "%d/%m/%Y %H:%M"
            diff = (datetime.strptime(atualizado, fmt) - datetime.strptime(criado, fmt)).total_seconds() / 86400
            return max(round(diff, 1), 0)
        except Exception:
            return None

    df = df.copy()
    df["dias_no_status"] = df.apply(
        lambda r: _dias_entre(r["criado_em"], r["atualizado_em"])
        if r["criado_em"] and r["atualizado_em"] else None, axis=1,
    )

    PIPELINE = [
        ("Pendente",         "#4f8ef7", "#0c1c30"),
        ("Agendado",         "#f59e0b", "#1c1400"),
        ("Proposta Enviada", "#8b5cf6", "#130c25"),
        ("Venda Realizada",  "#22c55e", "#0a1c10"),
    ]
    LOST = ("Venda não Realizada", "#ef4444", "#1c0a0a")
    TODOS_STAGES = PIPELINE + [LOST]
    STATUS_COR   = {s: c for s, c, _ in TODOS_STAGES}

    total     = len(df)
    vendas    = int((df["status"] == "Venda Realizada").sum())
    conv_pct  = round(vendas / total * 100, 1) if total else 0
    ciclo_med = df["dias_no_status"].dropna().mean()
    ciclo_str = f"{ciclo_med:.1f}" if not pd.isna(ciclo_med) else "—"

    m1, m2, m3, m4 = st.columns(4)
    for col, val, label in [
        (m1, total,          "Total de leads"),
        (m2, vendas,         "Vendas realizadas"),
        (m3, f"{conv_pct}%", "Taxa de conversão"),
        (m4, ciclo_str,      "Ciclo médio (dias)"),
    ]:
        with col:
            st.markdown(
                f"<div style='background:var(--bg-card);border:1px solid var(--border);"
                f"border-radius:12px;padding:22px 18px;text-align:center;'>"
                f"<div style='color:#7a9cc7;font-size:11px;font-weight:600;"
                f"text-transform:uppercase;letter-spacing:.7px;margin-bottom:10px;'>{label}</div>"
                f"<div style='color:#e8eef8;font-size:38px;font-weight:700;line-height:1;'>{val}</div>"
                f"</div>",
                unsafe_allow_html=True,
            )

    st.markdown("<div style='height:28px'></div>", unsafe_allow_html=True)

    def _pipe_card(status, cor, bg, dashed=False):
        sub     = df[df["status"] == status]
        qtd     = len(sub)
        med_val = sub["dias_no_status"].dropna().mean()
        med_str = f"{med_val:.1f}d" if qtd and not pd.isna(med_val) else "—"
        bar_pct = min(int(qtd / total * 100), 100) if total else 0
        border  = f"1.5px dashed {cor}55" if dashed else f"1px solid {cor}44"
        return (
            f"<div style='background:{bg};border:{border};border-radius:14px;"
            f"padding:26px 16px 22px;text-align:center;height:100%;box-sizing:border-box;'>"
            f"<div style='width:30px;height:30px;border:2px solid {cor}88;border-radius:7px;"
            f"margin:0 auto 14px;display:flex;align-items:center;justify-content:center;'>"
            f"<div style='width:12px;height:12px;background:{cor};border-radius:3px;'></div></div>"
            f"<div style='color:{cor};font-size:16px;font-weight:700;margin-bottom:14px;"
            f"white-space:nowrap;overflow:hidden;text-overflow:ellipsis;'>{status}</div>"
            f"<div style='color:#e8eef8;font-size:46px;font-weight:800;line-height:1;"
            f"margin-bottom:8px;'>{qtd}</div>"
            f"<div style='color:#7a9cc7;font-size:13px;margin-bottom:16px;'>média {med_str}</div>"
            f"<div style='background:#152a4a;border-radius:99px;height:5px;overflow:hidden;'>"
            f"<div style='background:{cor};width:{bar_pct}%;height:100%;border-radius:99px;'></div></div>"
            f"</div>"
        )

    n_pend    = int((df["status"] == "Pendente").sum())
    n_agend   = int((df["status"] == "Agendado").sum())
    n_prop    = int((df["status"] == "Proposta Enviada").sum())
    n_perdido = int((df["status"] == "Venda não Realizada").sum())

    atingiram_agend = n_agend + n_prop + vendas + n_perdido
    atingiram_prop  = n_prop + vendas + n_perdido

    pct_pend_agend   = round(atingiram_agend  / total           * 100, 1) if total           else 0
    pct_agend_prop   = round(atingiram_prop   / atingiram_agend * 100, 1) if atingiram_agend else 0
    pct_prop_venda   = round(vendas           / atingiram_prop  * 100, 1) if atingiram_prop  else 0
    pct_prop_perdido = round(n_perdido        / atingiram_prop  * 100, 1) if atingiram_prop  else 0

    def _arrow_pct(pct, cor, label="passaram"):
        return (
            f"<div style='display:flex;flex-direction:column;align-items:center;"
            f"justify-content:center;padding:0 10px;flex-shrink:0;min-width:80px;gap:5px;'>"
            f"<div style='color:{cor};font-size:15px;font-weight:800;line-height:1;'>{pct}%</div>"
            f"<div style='color:#7a9cc7;font-size:10px;text-transform:uppercase;"
            f"letter-spacing:.5px;'>{label}</div>"
            f"<svg width='42' height='14' viewBox='0 0 42 14'>"
            f"<line x1='0' y1='7' x2='33' y2='7' stroke='{cor}' stroke-width='2'/>"
            f"<polygon points='29,2 40,7 29,12' fill='{cor}'/>"
            f"</svg>"
            f"</div>"
        )

    _h_pend  = _pipe_card("Pendente",            "#4f8ef7", "#0c1c30")
    _h_agend = _pipe_card("Agendado",            "#f59e0b", "#1c1400")
    _h_prop  = _pipe_card("Proposta Enviada",    "#8b5cf6", "#130c25")
    _h_venda = _pipe_card("Venda Realizada",     "#22c55e", "#0a1c10")
    _h_perd  = _pipe_card("Venda não Realizada", "#ef4444", "#1c0a0a", dashed=True)

    _fork_col = (
        f"<div style='display:flex;flex-direction:column;align-items:center;"
        f"justify-content:center;padding:0 10px;flex-shrink:0;min-width:86px;gap:4px;'>"
        f"<div style='color:#22c55e;font-size:15px;font-weight:800;line-height:1;'>{pct_prop_venda}%</div>"
        f"<div style='color:#7a9cc7;font-size:10px;text-transform:uppercase;letter-spacing:.5px;'>vendas</div>"
        f"<svg width='42' height='14' viewBox='0 0 42 14'>"
        f"<line x1='0' y1='7' x2='33' y2='7' stroke='#22c55e' stroke-width='2'/>"
        f"<polygon points='29,2 40,7 29,12' fill='#22c55e'/>"
        f"</svg>"
        f"<div style='height:22px;border-left:1.5px dashed #7a9cc755;margin:2px 0;'></div>"
        f"<svg width='42' height='14' viewBox='0 0 42 14'>"
        f"<line x1='0' y1='7' x2='33' y2='7' stroke='#ef4444' stroke-width='1.5' stroke-dasharray='5,3'/>"
        f"<polygon points='29,2 40,7 29,12' fill='#ef4444'/>"
        f"</svg>"
        f"<div style='color:#7a9cc7;font-size:10px;text-transform:uppercase;letter-spacing:.5px;'>perdidos</div>"
        f"<div style='color:#ef4444;font-size:15px;font-weight:800;line-height:1;'>{pct_prop_perdido}%</div>"
        f"</div>"
    )

    st.markdown(
        f"<div style='display:flex;align-items:stretch;gap:0;'>"
        f"  <div style='flex:1;'>{_h_pend}</div>"
        f"  {_arrow_pct(pct_pend_agend, '#4f8ef7')}"
        f"  <div style='flex:1;'>{_h_agend}</div>"
        f"  {_arrow_pct(pct_agend_prop, '#8b5cf6')}"
        f"  <div style='flex:1;'>{_h_prop}</div>"
        f"  {_fork_col}"
        f"  <div style='flex:1;display:flex;flex-direction:column;gap:10px;'>"
        f"    <div style='flex:1;'>{_h_venda}</div>"
        f"    <div style='flex:1;'>{_h_perd}</div>"
        f"  </div>"
        f"</div>",
        unsafe_allow_html=True,
    )

    st.markdown("<div style='height:36px'></div>", unsafe_allow_html=True)

    AVATAR_BG  = ["#0e2040","#0c2818","#28100e","#180e28","#281e0e","#0e2828"]
    AVATAR_COR = ["#4f8ef7","#22c55e","#ef4444","#8b5cf6","#f59e0b","#22c5c5"]
    STAGE_EMOJI = {
        "Pendente":            "🔵",
        "Agendado":            "🟡",
        "Proposta Enviada":    "🟣",
        "Venda Realizada":     "🟢",
        "Venda não Realizada": "🔴",
    }

    st.markdown(
        "<div style='color:#7a9cc7;font-size:13px;font-weight:600;"
        "text-transform:uppercase;letter-spacing:.6px;margin-bottom:10px;'>"
        "Leads por estágio</div>",
        unsafe_allow_html=True,
    )

    df_sorted = df.sort_values("data_obj", ascending=False).reset_index(drop=True)

    for status, cor, bg in TODOS_STAGES:
        df_stage = df_sorted[df_sorted["status"] == status].reset_index(drop=True)
        qtd  = len(df_stage)
        icon = STAGE_EMOJI.get(status, "●")
        with st.expander(f"{icon}  {status}  —  {qtd} lead{'s' if qtd != 1 else ''}", expanded=False):
            if qtd == 0:
                st.info("Nenhum lead neste estágio.")
            else:
                cards_html = ""
                for i, row in df_stage.iterrows():
                    nome      = str(row.get("nome", "") or "").strip() or "—"
                    palavras  = [p for p in nome.split() if p]
                    initials  = (palavras[0][0] + (palavras[1][0] if len(palavras) > 1 else "")).upper()
                    av_bg     = AVATAR_BG[i % len(AVATAR_BG)]
                    av_cor    = AVATAR_COR[i % len(AVATAR_COR)]
                    status_v  = str(row.get("status", "") or "—")
                    badge_cor = STATUS_COR.get(status_v, "#7a9cc7")
                    interesse = str(row.get("interesse", "") or row.get("base", "") or "").strip()
                    if not interesse or interesse == "nan":
                        interesse = str(row.get("atendente", "") or "").strip() or "—"
                    dias     = row.get("dias_no_status")
                    dias_str = f"{int(dias)}d total" if dias is not None and not pd.isna(dias) else "—"
                    cards_html += (
                        f"<div style='background:var(--bg-card);border:1px solid var(--border);"
                        f"border-radius:12px;padding:14px 18px;display:flex;align-items:center;"
                        f"gap:14px;margin-bottom:8px;'>"
                        f"<div style='width:44px;height:44px;border-radius:50%;background:{av_bg};"
                        f"border:1.5px solid {av_cor}55;display:flex;align-items:center;"
                        f"justify-content:center;flex-shrink:0;'>"
                        f"<span style='color:{av_cor};font-weight:700;font-size:13px;'>{initials}</span></div>"
                        f"<div style='flex:1;min-width:0;'>"
                        f"<div style='color:#e8eef8;font-weight:600;font-size:14px;"
                        f"white-space:nowrap;overflow:hidden;text-overflow:ellipsis;'>{nome}</div>"
                        f"<div style='color:#7a9cc7;font-size:12px;margin-top:2px;"
                        f"white-space:nowrap;overflow:hidden;text-overflow:ellipsis;'>{interesse}</div>"
                        f"</div>"
                        f"<div style='background:{badge_cor}1a;border:1px solid {badge_cor}44;"
                        f"border-radius:99px;padding:5px 14px;flex-shrink:0;'>"
                        f"<span style='color:{badge_cor};font-size:12px;font-weight:600;"
                        f"white-space:nowrap;'>{status_v}</span></div>"
                        f"<div style='color:#7a9cc7;font-size:13px;min-width:58px;"
                        f"text-align:right;flex-shrink:0;'>{dias_str}</div>"
                        f"</div>"
                    )
                st.markdown(cards_html, unsafe_allow_html=True)
