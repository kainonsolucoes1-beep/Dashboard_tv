import streamlit as st
from datetime import datetime

from src.data.historico_incremental import HistoricoIncremental


def formatar_data(data_iso: str) -> str:
    try:
        return datetime.fromisoformat(data_iso).strftime("%d/%m/%Y")
    except Exception:
        return data_iso[:10] if len(data_iso) >= 10 else data_iso


def render_modal_historico(lead_id: int, lead_nome: str = "") -> None:
    historico = HistoricoIncremental()
    anotacoes = historico.obter_por_lead_id(lead_id)

    titulo = f"Historico — {lead_nome}" if lead_nome else f"Historico — Lead #{lead_id}"

    with st.expander(f"📋 {titulo}", expanded=True):
        if not anotacoes:
            st.markdown(
                "<div style='padding:16px;color:#7a9cc7;font-size:14px;'>"
                "Sem historico registrado para este lead."
                "</div>",
                unsafe_allow_html=True,
            )
            return

        itens_html = ""
        cores = ["#0d1f35", "#0a1a2e"]
        for i, anotacao in enumerate(anotacoes):
            data_fmt = formatar_data(anotacao.get("data_importacao", ""))
            texto = anotacao.get("texto", "")
            if len(texto) > 300:
                texto = texto[:297] + "..."
            fonte = anotacao.get("fonte", "")
            cor_fundo = cores[i % 2]

            itens_html += f"""
<div style="background:{cor_fundo};border-left:3px solid #1e4080;
            padding:12px 16px;margin-bottom:6px;border-radius:4px;">
  <div style="display:flex;align-items:flex-start;gap:12px;">
    <div style="color:#4f8ef7;font-size:16px;margin-top:2px;flex-shrink:0;">└─</div>
    <div style="flex:1;min-width:0;">
      <div style="color:#7a9cc7;font-size:11px;font-weight:600;
                  letter-spacing:.5px;margin-bottom:4px;">{data_fmt}
        <span style="margin-left:8px;color:#3a4a5a;font-weight:400;">{fonte}</span>
      </div>
      <div style="color:#cdd9e5;font-size:13px;line-height:1.5;
                  white-space:pre-wrap;word-break:break-word;">{texto}</div>
    </div>
  </div>
</div>"""

        total = len(anotacoes)
        label_total = "anotacao" if total == 1 else "anotacoes"

        st.markdown(
            f"{itens_html}"
            f"<div style='padding:8px 4px;color:#4a5a6a;font-size:11px;text-align:right;'>"
            f"Total: {total} {label_total}</div>",
            unsafe_allow_html=True,
        )
