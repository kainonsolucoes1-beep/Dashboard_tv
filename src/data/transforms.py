import pandas as pd

from src.data.api import fetch_leads_30dias, fetch_leads_80dias, fetch_leads_criticos, fetch_leads_hoje, ORIGEM_MAP


def _normalize_origens(df: pd.DataFrame) -> pd.DataFrame:
    if "origem" not in df.columns:
        return df
    df = df.copy()
    df["origem"] = df["origem"].apply(
        lambda o: ORIGEM_MAP.get(str(o).lower(), o) if o else o
    )
    return df


def _merge(df_hist, err1):
    df_crit, err2 = fetch_leads_criticos()
    if df_hist.empty and df_crit.empty:
        return pd.DataFrame(), err1 or err2
    partes = [p for p in [df_crit, df_hist] if not p.empty]
    merged = pd.concat(partes, ignore_index=True)
    if "id" in merged.columns:
        merged = merged.drop_duplicates(subset=["id"], keep="first")
    return _normalize_origens(merged), err1 or err2


def merge_leads_curto():
    """30 dias + hoje + críticos · usado em Visão Geral, Operador, Detalhamento e Leads."""
    df_hist, err1 = fetch_leads_30dias()
    df_hj, _ = fetch_leads_hoje()
    if not df_hj.empty:
        if not df_hist.empty and "id" in df_hist.columns and "id" in df_hj.columns:
            df_hist = pd.concat([df_hj, df_hist], ignore_index=True)
            df_hist = df_hist.drop_duplicates(subset=["id"], keep="first")
        elif df_hist.empty:
            df_hist = df_hj
    return _merge(df_hist, err1)


def merge_leads_longo():
    """80 dias + críticos · usado no Funil de Vendas."""
    df_hist, err1 = fetch_leads_80dias()
    return _merge(df_hist, err1)
