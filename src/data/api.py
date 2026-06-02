from datetime import datetime, date, timedelta

import pandas as pd
import requests
import streamlit as st

from config import ACCESS_TOKEN
from src.auth.token import _renovar_token_auto
from src.data.cache import (
    _ler_cache_disco, _cache_disco_disponivel,
    CACHE_30_PATH, CACHE_80_PATH, CACHE_HOJE_PATH, CACHE_CRITICOS_PATH,
)
from src.utils.time import horas_uteis

ORIGEM_MAP = {
    "livia":      "O2 Solution",
    "anny":       "O2 Solution",
    "kauany":     "O2 Solution",
    "emily":      "O2 Solution",
    "rodolfo":    "O2 Solution",
    "discadora":  "O2 Solution",
    "gabrieli":   "O2 Solution",
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

DIAS_CRITICOS = 10


def _fetch_leads_from_api(days: int, date_of: str = "creation"):
    global ACCESS_TOKEN
    headers = {"Authorization": f"Bearer {ACCESS_TOKEN}", "Accept": "application/json"}
    todos_leads = []
    pagina = 1
    date_from = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    _token_renovado = False
    while True:
        params = {"date_from": date_from, "date_of": date_of, "per_page": 200, "page": pagina}
        ultimo_erro = None
        data = None
        for _ in range(3):
            try:
                response = requests.get(
                    "https://api.followize.com.br/v3/leads",
                    headers=headers, params=params, timeout=60
                )
                if response.status_code == 401 and not _token_renovado:
                    novo = _renovar_token_auto()
                    if novo:
                        ACCESS_TOKEN = novo
                        headers["Authorization"] = f"Bearer {novo}"
                        _token_renovado = True
                        continue
                if response.status_code != 200:
                    return pd.DataFrame(), f"Erro na API: {response.status_code}"
                data = response.json()
                ultimo_erro = None
                break
            except Exception as e:
                ultimo_erro = e
        if ultimo_erro is not None:
            return pd.DataFrame(), f"Erro ao buscar leads: {ultimo_erro}"
        leads = data.get("data", [])
        if not leads:
            break
        todos_leads.extend(leads)
        meta = data.get("meta", {})
        if pagina >= meta.get("last_page", 1):
            break
        pagina += 1

    registros = []
    for lead in todos_leads:
        atendente = (
            ((lead.get("contact") or {}).get("attendant") or {}).get("name")
            or (lead.get("attendant") or {}).get("name", "Sem atendente")
        )
        status_raw     = lead.get("status", "")
        status_pt      = STATUS_MAP.get(status_raw, status_raw)
        origem_raw     = (lead.get("tracking") or {}).get("source", "") or "Sem origem"
        origem         = ORIGEM_MAP.get(origem_raw.lower(), origem_raw)
        equipe         = ((lead.get("contact") or {}).get("team") or {}).get("name", "")
        interesse      = ((lead.get("interests") or {}).get("interest_1") or {}).get("name", "")
        criado_em      = lead.get("created_at", "")
        atualizado_em  = lead.get("updated_at", "")
        perception_raw = lead.get("perception") or ""
        perception_pt  = PERCEPTION_MAP.get(perception_raw, perception_raw or "Sem percepção")
        last_proposal  = lead.get("last_proposal") or {}
        finalization   = lead.get("finalization") or {}
        valor_proposta = (
            last_proposal.get("amount")
            or finalization.get("amount")
            or 0.0
        )

        def _parse_dt(s):
            for fmt in ("%Y-%m-%dT%H:%M:%S.%fZ", "%Y-%m-%dT%H:%M:%SZ",
                        "%Y-%m-%dT%H:%M:%S.%f+00:00", "%Y-%m-%dT%H:%M:%S+00:00"):
                try:
                    return datetime.strptime(s, fmt) - timedelta(hours=3)
                except ValueError:
                    continue
            return None

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
        int2     = ((lead.get("interests") or {}).get("interest_2") or {}).get("name", "") or ""
        int3     = ((lead.get("interests") or {}).get("interest_3") or {}).get("name", "") or ""

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
            em_atraso = horas_uteis(last_inter_dt, datetime.now()) > 24

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
            "id":                  lead.get("id"),
            "nome":                lead.get("name", ""),
            "status":              status_pt,
            "atendente":           atendente,
            "atualizado_obj":      atualizado_obj,
            "origem":              origem,
            "equipe":              equipe,
            "interesse":           interesse,
            "criado_em":           criado_em,
            "data_obj":            data_obj,
            "perception":          perception_pt,
            "valor_proposta":      float(valor_proposta),
            "atualizado_em":       atualizado_em,
            "email":               email,
            "telefone":            telefone,
            "interest_2":          int2,
            "interest_3":          int3,
            "last_interaction_at": last_inter,
            "agendamento_data":    sched_data,
            "agendamento_tipo":    sched_tipo,
            "agendamento_status":  sched_status,
            "first_interaction_at": last_inter,
            "message_lead":        lead.get("message", "") or "",
            "base":                base,
            "conversion_goal":     lead.get("conversion_goal", "") or "",
            "em_atraso":           em_atraso,
        })
    return pd.DataFrame(registros), None


@st.cache_data(ttl=120, show_spinner=False)
def fetch_leads_30dias():
    """60 dias por criação. Prioriza cache em disco do updater.py."""
    if _cache_disco_disponivel(CACHE_30_PATH):
        df, _ = _ler_cache_disco(CACHE_30_PATH)
        if not df.empty:
            return df, None
    return _fetch_leads_from_api(days=60, date_of="creation")


@st.cache_data(ttl=120, show_spinner=False)
def fetch_leads_80dias():
    """80 dias por criação. Prioriza cache em disco do updater.py."""
    if _cache_disco_disponivel(CACHE_80_PATH):
        df, _ = _ler_cache_disco(CACHE_80_PATH)
        if not df.empty:
            return df, None
    return _fetch_leads_from_api(days=80, date_of="creation")


@st.cache_data(ttl=60, show_spinner=False)
def fetch_leads_criticos():
    """Últimos 4 dias por atualização. Prioriza cache em disco do updater.py."""
    if _cache_disco_disponivel(CACHE_CRITICOS_PATH):
        df, _ = _ler_cache_disco(CACHE_CRITICOS_PATH)
        if not df.empty:
            return df, None
    return _fetch_leads_from_api(days=DIAS_CRITICOS, date_of="change")


@st.cache_data(ttl=55, show_spinner=False)
def fetch_leads_hoje():
    """Leads criados nos últimos 5 dias. Prioriza cache em disco do updater.py."""
    if _cache_disco_disponivel(CACHE_HOJE_PATH):
        df, _ = _ler_cache_disco(CACHE_HOJE_PATH)
        if not df.empty and "data_obj" in df.columns:
            hoje_local = date.today()
            _ult = hoje_local - timedelta(days=1)
            while _ult.weekday() >= 5:
                _ult -= timedelta(days=1)
            tem_hoje = (df["data_obj"] == hoje_local).any()
            tem_util = (df["data_obj"] == _ult).any()
            if tem_hoje or tem_util:
                return df, None
    return _fetch_leads_from_api(days=5, date_of="creation")
