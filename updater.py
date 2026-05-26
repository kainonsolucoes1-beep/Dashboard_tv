"""
updater.py — Atualizador de cache em background para o Dashboard O2 Solution
============================================================================
Roda separado do Streamlit e salva os dados da API em disco a cada 5 minutos.
O dashboard lê esses arquivos em vez de chamar a API diretamente.

Como rodar (em paralelo com o dashboard):
    python updater.py

Em produção, deixe os dois processos rodando juntos:
    streamlit run dashboard_tv_novo.py &
    python updater.py
"""

import time
import pickle
import os
import sys
import logging
from datetime import datetime, timedelta

import requests
import pandas as pd

# ── Configuração de log ────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [updater] %(message)s",
    datefmt="%d/%m/%Y %H:%M:%S",
)
log = logging.getLogger(__name__)

# ── Importa token e mapeamentos do próprio projeto ────────────────────────────
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)

from config import ACCESS_TOKEN

# Caminhos dos arquivos de cache em disco
CACHE_30_PATH  = os.path.join(SCRIPT_DIR, "cache_30dias.pkl")
CACHE_80_PATH  = os.path.join(SCRIPT_DIR, "cache_80dias.pkl")
CACHE_HOJE_PATH     = os.path.join(SCRIPT_DIR, "cache_hoje.pkl")
CACHE_CRITICOS_PATH = os.path.join(SCRIPT_DIR, "cache_criticos.pkl")

# Intervalo entre atualizações (segundos)
INTERVALO_SEGUNDOS = 300  # 5 minutos

# ── Mapeamentos (mesmos do dashboard) ─────────────────────────────────────────
ORIGEM_MAP = {
    "Livia": "O2 Solution",
    "Anny":  "O2 Solution",
}

STATUS_MAP = {
    "pending":            "Pendente",
    "scheduled":          "Agendado",
    "proposal_sent":      "Proposta Enviada",
    "waiting_billing":    "Venda Realizada",
    "sale_performed":     "Venda Realizada",
    "sale_not_performed": "Venda não Realizada",
}

PERCEPTION_MAP = {
    "hot":  "🔥 Quente",
    "warm": "🌡️ Morno",
    "cold": "🧊 Frio",
}


def _parse_dt(s):
    """Converte string de data da API para datetime no horário de Brasília (UTC-3)."""
    for fmt in ("%Y-%m-%dT%H:%M:%S.%fZ", "%Y-%m-%dT%H:%M:%SZ",
                "%Y-%m-%dT%H:%M:%S.%f+00:00", "%Y-%m-%dT%H:%M:%S+00:00"):
        try:
            return datetime.strptime(s, fmt) - timedelta(hours=3)
        except ValueError:
            continue
    return None


def buscar_leads_api(days: int, date_of: str = "creation") -> pd.DataFrame:
    """
    Busca leads da API Followize e retorna um DataFrame processado.
    Igual ao _fetch_leads_from_api do dashboard, mas sem depender do Streamlit.
    """
    headers = {"Authorization": f"Bearer {ACCESS_TOKEN}", "Accept": "application/json"}
    todos_leads = []
    pagina = 1
    date_from = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")

    log.info(f"Buscando {days} dias (date_of={date_of}) a partir de {date_from}...")

    while True:
        params = {
            "date_from": date_from,
            "date_of":   date_of,
            "per_page":  200,
            "page":      pagina,
        }
        data = None
        for tentativa in range(3):
            try:
                response = requests.get(
                    "https://api.followize.com.br/v3/leads",
                    headers=headers,
                    params=params,
                    timeout=60,
                )
                if response.status_code != 200:
                    log.error(f"Erro na API: status {response.status_code}")
                    return pd.DataFrame()
                data = response.json()
                break
            except Exception as e:
                log.warning(f"Tentativa {tentativa + 1}/3 falhou: {e}")
                time.sleep(2)

        if data is None:
            log.error("Não foi possível buscar dados após 3 tentativas.")
            return pd.DataFrame()

        leads = data.get("data", [])
        if not leads:
            break

        todos_leads.extend(leads)
        meta = data.get("meta", {})
        log.info(f"  → Página {pagina}/{meta.get('last_page', '?')} — {len(todos_leads)} leads até agora")

        if pagina >= meta.get("last_page", 1):
            break
        pagina += 1

    # ── Processa cada lead (igual ao dashboard) ────────────────────────────────
    registros = []
    for lead in todos_leads:
        atendente = (
            ((lead.get("contact") or {}).get("attendant") or {}).get("name")
            or (lead.get("attendant") or {}).get("name", "Sem atendente")
        )
        status_raw     = lead.get("status", "")
        status_pt      = STATUS_MAP.get(status_raw, status_raw)
        origem_raw     = (lead.get("tracking") or {}).get("source", "") or "Sem origem"
        origem         = ORIGEM_MAP.get(origem_raw, origem_raw)
        equipe         = ((lead.get("contact") or {}).get("team") or {}).get("name", "")
        interesse      = ((lead.get("interests") or {}).get("interest_1") or {}).get("name", "")
        criado_em      = lead.get("created_at", "")
        atualizado_em  = lead.get("updated_at", "")
        perception_raw = lead.get("perception") or ""
        perception_pt  = PERCEPTION_MAP.get(perception_raw, perception_raw or "Sem percepção")
        last_proposal  = lead.get("last_proposal") or {}
        finalization   = lead.get("finalization") or {}
        valor_proposta = (last_proposal.get("amount") or finalization.get("amount") or 0.0)

        data_obj = None
        if criado_em:
            dt = _parse_dt(criado_em)
            if dt:
                data_obj  = dt.date()
                criado_em = dt.strftime("%d/%m/%Y %H:%M")

        atualizado_obj = None
        if atualizado_em:
            dt = _parse_dt(atualizado_em)
            if dt:
                atualizado_obj = dt.date()
                atualizado_em  = dt.strftime("%d/%m/%Y %H:%M")

        email    = (lead.get("contact") or {}).get("email", "") or ""
        telefone = ((lead.get("contact") or {}).get("cellphone") or
                    (lead.get("contact") or {}).get("phone", "")) or ""
        int2 = ((lead.get("interests") or {}).get("interest_2") or {}).get("name", "") or ""
        int3 = ((lead.get("interests") or {}).get("interest_3") or {}).get("name", "") or ""

        msg_raw = lead.get("message", "") or ""
        base = ""
        if msg_raw:
            first_line = msg_raw.split("\n")[0]
            if first_line.startswith("Base:"):
                base = first_line[5:].strip().strip("|").strip()

        last_inter = lead.get("last_interaction_at", "") or ""
        last_inter_dt = None
        if last_inter:
            dt = _parse_dt(last_inter)
            if dt:
                last_inter_dt = dt
                last_inter = dt.strftime("%d/%m/%Y %H:%M")

        status_fechado = status_raw in ("sale_performed", "sale_not_performed", "waiting_billing")
        em_atraso = False
        if last_inter_dt and not status_fechado:
            # Simplificado: usa horas corridas (sem cálculo de dias úteis no updater)
            horas = (datetime.now() - last_inter_dt).total_seconds() / 3600
            em_atraso = horas > 24

        last_sched = lead.get("last_schedule") or {}
        sched_data, sched_tipo, sched_status = "", "", ""
        if isinstance(last_sched, dict) and last_sched:
            _v = last_sched.get("date", "")
            if _v:
                _dt2 = _parse_dt(str(_v))
                sched_data = _dt2.strftime("%d/%m/%Y %H:%M") if _dt2 else str(_v)
            sched_tipo   = ((last_sched.get("reason") or {}).get("name", "")) or ""
            sched_status = last_sched.get("status", "") or ""

        registros.append({
            "id":                   lead.get("id"),
            "nome":                 lead.get("name", ""),
            "status":               status_pt,
            "atendente":            atendente,
            "atualizado_obj":       atualizado_obj,
            "origem":               origem,
            "equipe":               equipe,
            "interesse":            interesse,
            "criado_em":            criado_em,
            "data_obj":             data_obj,
            "perception":           perception_pt,
            "valor_proposta":       float(valor_proposta),
            "atualizado_em":        atualizado_em,
            "email":                email,
            "telefone":             telefone,
            "interest_2":           int2,
            "interest_3":           int3,
            "last_interaction_at":  last_inter,
            "agendamento_data":     sched_data,
            "agendamento_tipo":     sched_tipo,
            "agendamento_status":   sched_status,
            "first_interaction_at": last_inter,
            "message_lead":         lead.get("message", "") or "",
            "base":                 base,
            "em_atraso":            em_atraso,
        })

    df = pd.DataFrame(registros)
    log.info(f"  ✓ {len(df)} leads processados.")
    return df


def salvar_cache(df: pd.DataFrame, path: str, label: str):
    """Salva o DataFrame em disco como pickle com timestamp."""
    payload = {
        "df":         df,
        "atualizado": datetime.now(),
    }
    tmp = path + ".tmp"
    with open(tmp, "wb") as f:
        pickle.dump(payload, f)
    os.replace(tmp, path)  # operação atômica — evita leitura de arquivo pela metade
    log.info(f"  💾 {label} salvo em disco ({len(df)} leads) → {os.path.basename(path)}")


def ciclo_de_atualizacao():
    """Executa um ciclo completo: busca 30 dias, 80 dias e hoje, salva tudo."""
    inicio = datetime.now()
    log.info("═" * 55)
    log.info("Iniciando ciclo de atualização...")

    # 30 dias (Visão Geral, Operadores, Detalhamento, Leads)
    df_30 = buscar_leads_api(days=60, date_of="creation")
    if not df_30.empty:
        salvar_cache(df_30, CACHE_30_PATH, "30 dias")

    # 80 dias (Funil de Vendas)
    df_80 = buscar_leads_api(days=80, date_of="creation")
    if not df_80.empty:
        salvar_cache(df_80, CACHE_80_PATH, "80 dias")

    # Hoje (painel Hoje da Visão Geral) — 5 dias garante que sexta aparece na segunda
    df_hoje = buscar_leads_api(days=5, date_of="creation")
    if not df_hoje.empty:
        salvar_cache(df_hoje, CACHE_HOJE_PATH, "hoje")

    # Críticos — últimos 4 dias por atualização (captura leads modificados)
    df_crit = buscar_leads_api(days=4, date_of="change")
    if not df_crit.empty:
        salvar_cache(df_crit, CACHE_CRITICOS_PATH, "criticos")

    duracao = (datetime.now() - inicio).seconds
    log.info(f"Ciclo concluído em {duracao}s. Próxima atualização em {INTERVALO_SEGUNDOS // 60} minutos.")
    log.info("═" * 55)


def main():
    log.info("🚀 Updater iniciado — O2 Solution Dashboard")
    log.info(f"Intervalo de atualização: {INTERVALO_SEGUNDOS // 60} minutos")
    log.info(f"Arquivos de cache: {SCRIPT_DIR}")

    while True:
        try:
            ciclo_de_atualizacao()
        except Exception as e:
            log.error(f"Erro inesperado no ciclo: {e}. Tentando novamente em 60s.")
            time.sleep(60)
            continue

        time.sleep(INTERVALO_SEGUNDOS)


if __name__ == "__main__":
    main()
