import os
import pickle
from datetime import datetime

import pandas as pd
import streamlit as st

_PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

CACHE_30_PATH       = os.path.join(_PROJECT_ROOT, "cache_30dias.pkl")
CACHE_80_PATH       = os.path.join(_PROJECT_ROOT, "cache_80dias.pkl")
CACHE_HOJE_PATH     = os.path.join(_PROJECT_ROOT, "cache_hoje.pkl")
CACHE_CRITICOS_PATH = os.path.join(_PROJECT_ROOT, "cache_criticos.pkl")


def _ler_cache_disco(path: str):
    """
    Lê um arquivo de cache gerado pelo updater.py.
    Retorna (DataFrame, datetime_atualizacao) ou (DataFrame vazio, None) se não existir.
    """
    try:
        with open(path, "rb") as f:
            payload = pickle.load(f)
        return payload["df"], payload["atualizado"]
    except Exception:
        return pd.DataFrame(), None


def _cache_disco_disponivel(path: str, max_age: int = 0) -> bool:
    """Retorna True se o arquivo existe e não está vazio.
    max_age > 0: exige que o arquivo tenha menos de max_age segundos."""
    if not os.path.exists(path) or os.path.getsize(path) == 0:
        return False
    if max_age > 0:
        idade = (datetime.now() - datetime.fromtimestamp(os.path.getmtime(path))).total_seconds()
        return idade < max_age
    return True


@st.fragment(run_every=30)
def _watcher_pkl(fetch_30, fetch_80, fetch_criticos, fetch_hoje):
    """Detecta quando o updater.py salva novos pkl e recarrega o dashboard automaticamente."""
    _pkls = {
        CACHE_30_PATH:       "mtime_30",
        CACHE_80_PATH:       "mtime_80",
        CACHE_HOJE_PATH:     "mtime_hoje",
        CACHE_CRITICOS_PATH: "mtime_criticos",
    }
    _changed = False
    for path, key in _pkls.items():
        if os.path.exists(path):
            mtime = os.path.getmtime(path)
            if st.session_state.get(key, 0) < mtime:
                st.session_state[key] = mtime
                _changed = True
    if _changed:
        fetch_30.clear()
        fetch_80.clear()
        fetch_criticos.clear()
        fetch_hoje.clear()
        st.session_state["_df_curto_stale"] = True
        st.rerun()
