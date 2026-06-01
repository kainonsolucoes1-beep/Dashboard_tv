import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from datetime import date, timedelta

from src.charts.rosca import CORES_STATUS
from src.charts.temperatura import CORES_PERCEPTION
from src.utils.formatters import fmt_brl
from src.utils.time import FERIADOS_BR, dias_uteis_lista


@st.dialog("Detalhamento de Leads", width="large")
def modal_leads_status(df_modal, label, cor, atendentes=None, operadores=None, show_perception=False):
    """
    atendentes: lista de nomes para filtro por atendente (ex: ["Giovanna", "Rayanna"]).
    operadores: lista de nomes para filtro por origem/operador (ex: SDR).
    show_perception: exibe coluna Temperatura (morno/frio) e filtro correspondente.
    """
    if df_modal.empty:
        st.info("Nenhum lead encontrado.")
        return

    df_filtrado = df_modal.copy()

    if show_perception:
        _fcol1, _fcol2, _fcol3 = st.columns([3, 2, 2])
    else:
        _fcol1, _fcol2 = st.columns([3, 2])

    with _fcol1:
        if atendentes:
            opcoes = ["Todas"] + atendentes
            escolha = st.radio(
                "👤 Atendente",
                opcoes,
                horizontal=True,
                key="modal_filtro_atendente",
            )
            if escolha != "Todas":
                df_filtrado = df_filtrado[
                    df_filtrado["atendente"].str.contains(escolha, case=False, na=False)
                ]
        elif operadores:
            opcoes = ["Todos"] + operadores
            escolha = st.radio(
                "👤 Operador",
                opcoes,
                horizontal=True,
                key="modal_filtro_operador",
            )
            if escolha != "Todos":
                df_filtrado = df_filtrado[df_filtrado["origem"] == escolha]

    with _fcol2:
        _status_opts = ["Todos"] + sorted(df_modal["status"].dropna().unique().tolist())
        _status_sel = st.selectbox("📊 Status", options=_status_opts, key="modal_filtro_status")
        if _status_sel != "Todos":
            df_filtrado = df_filtrado[df_filtrado["status"] == _status_sel]

    if show_perception:
        with _fcol3:
            _temp_opts = ["Todos", "🌡️ Morno", "🧊 Frio"]
            _temp_sel = st.selectbox("🌡️ Temperatura", options=_temp_opts, key="modal_filtro_temp")
            if _temp_sel != "Todos":
                df_filtrado = df_filtrado[df_filtrado["perception"] == _temp_sel]

    total       = len(df_filtrado)
    valor_total = df_filtrado["valor_proposta"].sum()

    st.markdown(
        f"<div style='margin-bottom:4px;'>"
        f"<span style='color:{cor};font-size:18px;font-weight:700;'>{label}</span>"
        f"&nbsp;&nbsp;<span style='color:#7a9cc7;font-size:13px;'>"
        f"{total} lead{'s' if total != 1 else ''}</span>"
        f"&nbsp;·&nbsp;<span style='color:#7a9cc7;font-size:13px;'>"
        f"Carteira: <strong style='color:{cor};'>{fmt_brl(valor_total)}</strong></span>"
        f"</div>",
        unsafe_allow_html=True,
    )

    if show_perception:
        _cols = ["nome", "status", "origem", "atendente", "perception", "valor_proposta", "criado_em", "atualizado_em"]
        _rename = {
            "nome": "Nome", "status": "Status", "origem": "Operador",
            "atendente": "Atendente", "perception": "Temperatura",
            "valor_proposta": "Valor (R$)", "criado_em": "Cadastrado em",
            "atualizado_em": "Última Atualização",
        }
    else:
        _cols = ["nome", "status", "origem", "atendente", "valor_proposta", "criado_em", "atualizado_em"]
        _rename = {
            "nome": "Nome", "status": "Status", "origem": "Operador",
            "atendente": "Atendente", "valor_proposta": "Valor (R$)",
            "criado_em": "Cadastrado em", "atualizado_em": "Última Atualização",
        }

    df_show = df_filtrado[_cols].copy()
    df_show["_sort"] = pd.to_datetime(df_show["atualizado_em"], format="%d/%m/%Y %H:%M", errors="coerce")
    df_show = df_show.sort_values("_sort", ascending=False).drop(columns="_sort").reset_index(drop=True)
    df_show = df_show.rename(columns=_rename)
    df_show["Valor (R$)"] = df_show["Valor (R$)"].apply(
        lambda v: fmt_brl(v) if v > 0 else "—"
    )

    st.dataframe(df_show, use_container_width=True, hide_index=True, height=400)


@st.dialog("📋 Detalhes do Lead", width="large")
def modal_lead(lead: pd.Series):
    nome    = lead.get("nome", "")    or ""
    status  = lead.get("status", "")  or ""
    temp    = lead.get("perception", "") or "Sem percepção"
    canal   = lead.get("origem", "")  or ""
    atend   = lead.get("atendente", "") or ""
    intere  = lead.get("interesse", "") or ""
    int2    = lead.get("interest_2", "") or ""
    int3    = lead.get("interest_3", "") or ""
    criado  = lead.get("criado_em", "")   or ""
    atualiz = lead.get("atualizado_em", "") or ""
    last_int= lead.get("last_interaction_at", "") or ""
    email   = lead.get("email", "")   or ""
    tel     = lead.get("telefone", "") or ""
    valor   = float(lead.get("valor_proposta", 0) or 0)
    ag_data   = lead.get("agendamento_data", "")   or ""
    ag_tipo   = lead.get("agendamento_tipo", "")   or ""
    ag_status = lead.get("agendamento_status", "") or ""
    msg_lead  = lead.get("message_lead", "")       or ""
    first_int = lead.get("first_interaction_at", "") or last_int

    em_atraso_flag = bool(lead.get("em_atraso", False))
    cor_s = CORES_STATUS.get(status, "#7a9cc7")
    cor_t = CORES_PERCEPTION.get(temp, "#7a9cc7")

    st.markdown(f"<h2 style='margin:0 0 8px;'>{nome}</h2>", unsafe_allow_html=True)
    badges = (
        f"<span style='background:{cor_s}22;color:{cor_s};border:1px solid {cor_s};"
        f"border-radius:99px;padding:3px 14px;font-size:13px;font-weight:600;margin-right:8px;'>"
        f"{status}</span>"
        f"<span style='background:{cor_t}22;color:{cor_t};border:1px solid {cor_t};"
        f"border-radius:99px;padding:3px 14px;font-size:13px;font-weight:600;margin-right:8px;'>"
        f"{temp}</span>"
        f"<span style='background:#152a4a;color:#7a9cc7;border:1px solid #152a4a;"
        f"border-radius:99px;padding:3px 14px;font-size:13px;font-weight:600;margin-right:8px;'>"
        f"📡 {canal}</span>"
    )
    if em_atraso_flag:
        badges += (
            "<span style='background:#ef444422;color:#ef4444;border:1px solid #ef4444;"
            "border-radius:99px;padding:3px 14px;font-size:13px;font-weight:600;'>"
            "🔴 Em atraso</span>"
        )
    st.markdown(badges, unsafe_allow_html=True)
    st.markdown("---")

    col_a, col_b = st.columns(2)

    with col_a:
        st.markdown(
            "<div style='color:#7a9cc7;font-size:11px;font-weight:600;"
            "text-transform:uppercase;letter-spacing:.7px;margin-bottom:8px;'>👤 Contato</div>",
            unsafe_allow_html=True,
        )
        st.markdown(f"**Atendente:** {atend}")
        if email:
            st.markdown(f"**E-mail:** {email}")
        if tel:
            st.markdown(f"**Telefone:** {tel}")

        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown(
            "<div style='color:#7a9cc7;font-size:11px;font-weight:600;"
            "text-transform:uppercase;letter-spacing:.7px;margin-bottom:8px;'>🎯 Interesse</div>",
            unsafe_allow_html=True,
        )
        interesses = [i for i in [intere, int2, int3] if i]
        if interesses:
            for i in interesses:
                st.markdown(f"• {i}")
        else:
            st.markdown(
                "<span style='color:#7a9cc7;font-size:13px;'>Não informado</span>",
                unsafe_allow_html=True,
            )

    with col_b:
        st.markdown(
            "<div style='color:#7a9cc7;font-size:11px;font-weight:600;"
            "text-transform:uppercase;letter-spacing:.7px;margin-bottom:8px;'>📅 Histórico</div>",
            unsafe_allow_html=True,
        )
        for label, val in [
            ("Cadastrado em",      criado),
            ("Última atualização", atualiz),
            ("Primeira interação", first_int),
            ("Última interação",   last_int),
        ]:
            if val:
                st.markdown(f"**{label}:** {val}")

        if valor > 0:
            st.markdown("<br>", unsafe_allow_html=True)
            st.markdown(
                "<div style='color:#7a9cc7;font-size:11px;font-weight:600;"
                "text-transform:uppercase;letter-spacing:.7px;margin-bottom:8px;'>💰 Proposta</div>",
                unsafe_allow_html=True,
            )
            st.markdown(
                f"<div style='font-size:26px;font-weight:700;color:#22c55e;'>{fmt_brl(valor)}</div>",
                unsafe_allow_html=True,
            )

    if ag_data or ag_tipo:
        st.markdown("---")
        st.markdown(
            "<div style='color:#7a9cc7;font-size:11px;font-weight:600;"
            "text-transform:uppercase;letter-spacing:.7px;margin-bottom:8px;'>📆 Último Agendamento</div>",
            unsafe_allow_html=True,
        )
        ag1, ag2 = st.columns(2)
        with ag1:
            if ag_data:
                st.markdown(f"**Data:** {ag_data}")
            if ag_tipo:
                st.markdown(f"**Motivo:** {ag_tipo}")
        with ag2:
            if ag_status:
                status_ag_map = {"pending": "⏳ Pendente", "done": "✅ Realizado", "canceled": "❌ Cancelado"}
                st.markdown(f"**Situação:** {status_ag_map.get(ag_status, ag_status)}")

    if msg_lead:
        st.markdown("---")
        st.markdown(
            "<div style='color:#7a9cc7;font-size:11px;font-weight:600;"
            "text-transform:uppercase;letter-spacing:.7px;margin-bottom:8px;'>📝 Campos do Lead</div>",
            unsafe_allow_html=True,
        )
        st.markdown(
            f"<div style='background:#060e1a;border:1px solid #152a4a;border-radius:8px;"
            f"padding:10px 14px;font-size:13px;color:#e8eef8;'>{msg_lead}</div>",
            unsafe_allow_html=True,
        )


@st.dialog("👤 Detalhes do Operador", width="large")
def modal_operador(op: str, df_op: pd.DataFrame, cor: str, de: date, ate: date):
    st.markdown(
        f"<h3 style='color:{cor};margin-bottom:4px;'>👤 {op}</h3>",
        unsafe_allow_html=True,
    )
    st.markdown("---")

    total   = len(df_op)
    vendas  = int((df_op["status"] == "Venda Realizada").sum())
    conv    = round(vendas / total * 100, 1) if total > 0 else 0
    valor   = df_op["valor_proposta"].sum()
    lc_val  = int((df_op["valor_proposta"] > 0).sum())
    ticket  = valor / lc_val if lc_val > 0 else 0
    du_lista      = dias_uteis_lista(de, ate)
    leads_por_dia = df_op[df_op["data_obj"].notna()].groupby("data_obj").size()
    du            = len(du_lista)
    media         = round(total / du, 1) if du > 0 else 0

    # Tendência: média leads/dia útil — semana atual vs semana anterior (calendário real)
    if du_lista:
        _last_du     = max(du_lista)
        _curr_mon    = _last_du - timedelta(days=_last_du.weekday())
        _prev_mon    = _curr_mon - timedelta(weeks=1)
        _curr_days   = [d for d in du_lista if d >= _curr_mon]
        _prev_days   = [d for d in du_lista if _prev_mon <= d < _curr_mon]
        _curr_leads  = sum(int(leads_por_dia.get(d, 0)) for d in _curr_days)
        _prev_leads  = sum(int(leads_por_dia.get(d, 0)) for d in _prev_days)
        _curr_avg    = round(_curr_leads / len(_curr_days), 1) if _curr_days else 0
        _prev_avg    = round(_prev_leads / len(_prev_days), 1) if _prev_days else 0
        if not _prev_days:
            tend_label, tend_cor, tend_sub = "—", "#7a9cc7", "sem semana anterior"
        elif _curr_avg > _prev_avg:
            tend_label, tend_cor = "↑ Subindo", "#22c55e"
            tend_sub = f"{_prev_avg} → {_curr_avg} leads/dia"
        elif _curr_avg < _prev_avg:
            tend_label, tend_cor = "↓ Caindo", "#ef4444"
            tend_sub = f"{_prev_avg} → {_curr_avg} leads/dia"
        else:
            tend_label, tend_cor = "→ Estável", "#7a9cc7"
            tend_sub = f"{_curr_avg} leads/dia"
    else:
        tend_label, tend_cor, tend_sub = "—", "#7a9cc7", ""

    st.markdown(f"""
    <div style="display:flex;gap:0;flex-wrap:wrap;background:#0a1628;border-radius:10px;
                border:1px solid #152a4a;overflow:hidden;margin-bottom:8px;">
      <div style="flex:1;min-width:90px;padding:14px 18px;border-right:1px solid #152a4a;">
        <div style="font-size:11px;color:#7a9cc7;text-transform:uppercase;letter-spacing:.7px;font-weight:600;">Leads</div>
        <div style="font-size:26px;font-weight:700;color:#e8eef8;margin-top:2px;">{total}</div>
      </div>
      <div style="flex:1;min-width:90px;padding:14px 18px;border-right:1px solid #152a4a;">
        <div style="font-size:11px;color:#7a9cc7;text-transform:uppercase;letter-spacing:.7px;font-weight:600;">Dias úteis</div>
        <div style="font-size:26px;font-weight:700;color:#e8eef8;margin-top:2px;">{du}</div>
      </div>
      <div style="flex:1;min-width:90px;padding:14px 18px;border-right:1px solid #152a4a;">
        <div style="font-size:11px;color:#7a9cc7;text-transform:uppercase;letter-spacing:.7px;font-weight:600;">Média/dia</div>
        <div style="font-size:26px;font-weight:700;color:{cor};margin-top:2px;">{media}</div>
      </div>
      <div style="flex:1;min-width:110px;padding:14px 18px;border-right:1px solid #152a4a;">
        <div style="font-size:11px;color:#7a9cc7;text-transform:uppercase;letter-spacing:.7px;font-weight:600;">Carteira</div>
        <div style="font-size:22px;font-weight:700;color:#f59e0b;margin-top:2px;">{fmt_brl(valor)}</div>
      </div>
      <div style="flex:1;min-width:110px;padding:14px 18px;border-right:1px solid #152a4a;">
        <div style="font-size:11px;color:#7a9cc7;text-transform:uppercase;letter-spacing:.7px;font-weight:600;">Ticket Médio</div>
        <div style="font-size:22px;font-weight:700;color:#4f8ef7;margin-top:2px;">{fmt_brl(ticket)}</div>
      </div>
      <div style="flex:1;min-width:110px;padding:14px 18px;">
        <div style="font-size:11px;color:#7a9cc7;text-transform:uppercase;letter-spacing:.7px;font-weight:600;">Tendência</div>
        <div style="font-size:20px;font-weight:700;color:{tend_cor};margin-top:4px;">{tend_label}</div>
        <div style="font-size:11px;color:#7a9cc7;margin-top:4px;">{tend_sub}</div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("#### 📈 Leads por Semana (dias úteis)")

    registros = [{"data_obj": d, "leads": int(leads_por_dia.get(d, 0))} for d in du_lista]
    df_dia = pd.DataFrame(registros)

    semanas_ord = sorted(df_dia["data_obj"].apply(lambda d: d.isocalendar()[1]).unique())
    semana_map  = {w: f"Semana {i+1}" for i, w in enumerate(semanas_ord)}
    df_dia["semana"] = df_dia["data_obj"].apply(lambda d: semana_map[d.isocalendar()[1]])

    por_semana = df_dia.groupby("semana", sort=False)["leads"].sum().reset_index()
    por_semana["_ord"] = por_semana["semana"].map({v: k for k, v in enumerate(semana_map.values())})
    por_semana = por_semana.sort_values("_ord").drop(columns="_ord")

    # Mapeamento semana_label → datas
    semana_dates: dict = {}
    for _d in du_lista:
        _wk = _d.isocalendar()[1]
        _lbl = semana_map[_wk]
        semana_dates.setdefault(_lbl, []).append(_d)

    fig_sem = go.Figure()
    fig_sem.add_trace(go.Scatter(
        x=por_semana["semana"].tolist(),
        y=por_semana["leads"].tolist(),
        mode="lines+markers+text",
        text=por_semana["leads"].tolist(),
        textposition="top center",
        textfont=dict(color="#e8eef8", size=13, family="DM Sans"),
        line=dict(color=cor, width=3),
        marker=dict(color=cor, size=12),
        hovertemplate="<b>%{x}</b><br>%{y} leads — clique para ver detalhes<extra></extra>",
    ))
    _max_sem = max(int(por_semana["leads"].max()), 1)
    fig_sem.update_layout(
        height=280,
        margin=dict(t=70, b=20, l=10, r=10),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(showgrid=False, color="#7a9cc7", tickfont=dict(color="#e8eef8", size=13)),
        yaxis=dict(showgrid=True, gridcolor="#152a4a", color="#7a9cc7",
                   tickfont=dict(color="#e8eef8", size=12), zeroline=False,
                   range=[0, _max_sem * 1.35]),
    )
    _sem_evt = st.plotly_chart(
        fig_sem, use_container_width=True,
        key=f"modal_sem_{op}", on_select="rerun",
    )

    st.markdown("---")

    _pts = (_sem_evt.selection or {}).get("points", []) if _sem_evt else []
    _sem_sel = _pts[0].get("x") if _pts else None

    if _sem_sel and _sem_sel in semana_dates:
        _datas_sem = semana_dates[_sem_sel]
        _df_sem = df_op[df_op["data_obj"].isin(_datas_sem)].copy()
        _df_sem = _df_sem.sort_values("data_obj", ascending=False).reset_index(drop=True)

        st.markdown(
            f"<div style='display:flex;align-items:center;gap:10px;margin-bottom:12px;'>"
            f"<div style='font-size:16px;font-weight:700;color:{cor};'>📅 {_sem_sel}</div>"
            f"<div style='font-size:13px;color:#7a9cc7;'>{len(_df_sem)} lead(s)  ·  "
            f"{_datas_sem[0].strftime('%d/%m')} → {_datas_sem[-1].strftime('%d/%m')}</div>"
            f"<div style='font-size:12px;color:#7a9cc7;margin-left:auto;'>Clique em outro ponto para trocar de semana</div>"
            f"</div>",
            unsafe_allow_html=True,
        )

        for _, _lr in _df_sem.iterrows():
            _status_cor = {"Venda Realizada": "#22c55e", "Venda não Realizada": "#ef4444"}.get(
                str(_lr.get("status", "")), "#7a9cc7"
            )
            _valor_str = fmt_brl(float(_lr.get("valor_proposta") or 0))
            _valor_str = _valor_str if float(_lr.get("valor_proposta") or 0) > 0 else "—"
            st.markdown(f"""
            <div style="background:#0a1628;border:1px solid #152a4a;border-left:4px solid {cor};
                        border-radius:10px;padding:14px 18px;margin-bottom:10px;">
              <div style="display:flex;align-items:flex-start;gap:20px;flex-wrap:wrap;">
                <div style="min-width:180px;flex:2;">
                  <div style="font-size:15px;font-weight:700;color:#e8eef8;margin-bottom:4px;">
                    {_lr.get('nome','—')}</div>
                  <div style="font-size:12px;color:#7a9cc7;">
                    {_lr.get('criado_em','').split(' ')[0] if _lr.get('criado_em') else '—'}
                    &nbsp;·&nbsp; {_lr.get('interesse','—')}
                  </div>
                </div>
                <div style="flex:1;min-width:120px;">
                  <div style="font-size:11px;color:#7a9cc7;text-transform:uppercase;letter-spacing:.6px;font-weight:600;">Status</div>
                  <div style="font-size:14px;font-weight:700;color:{_status_cor};">{_lr.get('status','—')}</div>
                </div>
                <div style="flex:1;min-width:120px;">
                  <div style="font-size:11px;color:#7a9cc7;text-transform:uppercase;letter-spacing:.6px;font-weight:600;">Atendente</div>
                  <div style="font-size:14px;font-weight:600;color:#e8eef8;">{_lr.get('atendente','—')}</div>
                </div>
                <div style="flex:1;min-width:100px;">
                  <div style="font-size:11px;color:#7a9cc7;text-transform:uppercase;letter-spacing:.6px;font-weight:600;">Valor</div>
                  <div style="font-size:14px;font-weight:700;color:#f59e0b;">{_valor_str}</div>
                </div>
                <div style="flex:1;min-width:100px;">
                  <div style="font-size:11px;color:#7a9cc7;text-transform:uppercase;letter-spacing:.6px;font-weight:600;">Temperatura</div>
                  <div style="font-size:14px;font-weight:600;color:#e8eef8;">{_lr.get('perception','—')}</div>
                </div>
              </div>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.markdown(
            "<div style='font-size:13px;color:#7a9cc7;margin-bottom:8px;'>"
            "💡 Clique em um ponto do gráfico acima para ver os leads daquela semana."
            "</div>",
            unsafe_allow_html=True,
        )
