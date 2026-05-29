import json
import os

import pandas as pd

_PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
_ALIASES_PATH = os.path.join(_PROJECT_ROOT, "base_aliases.json")


def load_base_aliases() -> dict:
    if os.path.exists(_ALIASES_PATH):
        try:
            with open(_ALIASES_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def save_base_aliases(aliases: dict):
    with open(_ALIASES_PATH, "w", encoding="utf-8") as f:
        json.dump(aliases, f, ensure_ascii=False, indent=2)


def apply_base_aliases(df: pd.DataFrame, aliases: dict) -> pd.DataFrame:
    if aliases and "base" in df.columns:
        df = df.copy()
        aliases_norm = {k.strip().lower(): v for k, v in aliases.items()}

        def _lookup(b):
            if not b:
                return b
            if b in aliases:
                return aliases[b]
            return aliases_norm.get(b.strip().lower(), b)

        for _ in range(5):
            antes = df["base"].copy()
            df["base"] = df["base"].apply(_lookup)
            if df["base"].equals(antes):
                break
    return df
