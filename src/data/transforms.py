import pandas as pd

from src.data.api import fetch_leads_30dias, fetch_leads_80dias, fetch_leads_criticos


def _merge(df_hist, err1):
    df_crit, err2 = fetch_leads_criticos()
    if df_hist.empty and df_crit.empty:
        return pd.DataFrame(), err1 or err2
    partes = [p for p in [df_crit, df_hist] if not p.empty]
    merged = pd.concat(partes, ignore_index=True)
    if "id" in merged.columns:
        merged = merged.drop_duplicates(subset=["id"], keep="first")
    return merged, err1 or err2


def merge_leads_curto():
    """30 dias + críticos · usado em Visão Geral, Operador, Detalhamento e Leads."""
    df_hist, err1 = fetch_leads_30dias()
    return _merge(df_hist, err1)


def merge_leads_longo():
    """80 dias + críticos · usado no Funil de Vendas."""
    df_hist, err1 = fetch_leads_80dias()
    return _merge(df_hist, err1)
