"""
Gerenciamento incremental de histórico de anotações de leads.
Armazena em JSON local, evita duplicatas via hash MD5.
"""

import json
import hashlib
from pathlib import Path
from datetime import datetime, timezone
from typing import Any, Dict, List

import pandas as pd


class HistoricoIncremental:
    """Histórico incremental de anotações de leads exportados do Followize."""

    def __init__(self, caminho_json: str = "data/historico_consolidado.json"):
        self._path = Path(caminho_json)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._dados = self._carregar()

    # ------------------------------------------------------------------
    # Persistência
    # ------------------------------------------------------------------

    def _carregar(self) -> Dict[str, Any]:
        if self._path.exists():
            try:
                with open(self._path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except (json.JSONDecodeError, OSError):
                pass
        return {
            "metadata": {
                "criado_em": datetime.now(timezone.utc).isoformat(),
                "ultima_importacao": None,
                "total_leads": 0,
                "total_anotacoes": 0,
            },
            "leads": {},
        }

    def _salvar(self) -> None:
        leads = self._dados["leads"]
        self._dados["metadata"]["total_leads"] = len(leads)
        self._dados["metadata"]["total_anotacoes"] = sum(
            len(v["anotacoes"]) for v in leads.values()
        )
        self._dados["metadata"]["ultima_importacao"] = datetime.now(timezone.utc).isoformat()
        with open(self._path, "w", encoding="utf-8") as f:
            json.dump(self._dados, f, ensure_ascii=False, indent=2)

    # ------------------------------------------------------------------
    # Lógica interna
    # ------------------------------------------------------------------

    def _processar_mensagem(self, mensagem: str) -> str:
        if not isinstance(mensagem, str):
            mensagem = str(mensagem)
        linhas = [l.strip() for l in mensagem.splitlines()]
        return "\n".join(l for l in linhas if l)

    def _hash(self, texto: str) -> str:
        return hashlib.md5(texto.encode("utf-8")).hexdigest()

    # ------------------------------------------------------------------
    # API pública
    # ------------------------------------------------------------------

    def adicionar_do_excel(self, caminho_excel: str) -> Dict[str, int]:
        """
        Lê Excel do Followize e adiciona apenas registros novos ao histórico.

        Retorna: {"sucesso": bool, "novos": int, "duplicatas": int, "leads_processados": int}
        """
        try:
            df = pd.read_excel(caminho_excel, dtype=str)
        except Exception as e:
            return {"sucesso": False, "novos": 0, "duplicatas": 0, "leads_processados": 0, "erro": str(e)}

        col_id = self._detectar_coluna(df, ["número", "numero", "id", "lead_id", "Número"])
        col_msg = self._detectar_coluna(df, ["mensagem da conversão", "mensagem da conversao", "mensagem", "anotacao", "anotação"])

        if col_id is None or col_msg is None:
            return {
                "sucesso": False,
                "novos": 0,
                "duplicatas": 0,
                "leads_processados": 0,
                "erro": f"Colunas não encontradas. Disponíveis: {list(df.columns)}",
            }

        novos = 0
        duplicatas = 0
        leads_processados = set()
        agora = datetime.now(timezone.utc).isoformat()

        for _, row in df.iterrows():
            lead_id = str(row[col_id]).strip()
            mensagem_raw = row[col_msg]

            if pd.isna(row[col_msg]) or str(mensagem_raw).strip() == "":
                continue

            texto = self._processar_mensagem(mensagem_raw)
            h = self._hash(texto)
            leads_processados.add(lead_id)

            if lead_id not in self._dados["leads"]:
                self._dados["leads"][lead_id] = {
                    "anotacoes": [],
                    "primeira_anotacao": agora,
                    "ultima_atualizacao": agora,
                }

            registro = self._dados["leads"][lead_id]
            hashes_existentes = {a["hash"] for a in registro["anotacoes"]}

            if h in hashes_existentes:
                duplicatas += 1
                continue

            registro["anotacoes"].append({
                "texto": texto,
                "hash": h,
                "data_importacao": agora,
                "fonte": str(Path(caminho_excel).name),
            })
            registro["ultima_atualizacao"] = agora
            novos += 1

        self._salvar()
        return {
            "sucesso": True,
            "novos": novos,
            "duplicatas": duplicatas,
            "leads_processados": len(leads_processados),
        }

    def _detectar_coluna(self, df: pd.DataFrame, candidatos: List[str]) -> str | None:
        colunas_lower = {c.lower().strip(): c for c in df.columns}
        for c in candidatos:
            if c.lower().strip() in colunas_lower:
                return colunas_lower[c.lower().strip()]
        return None

    def obter_por_lead_id(self, lead_id: int | str) -> List[Dict]:
        """Retorna anotações de um lead, ordenadas por data de importação."""
        registro = self._dados["leads"].get(str(lead_id))
        if not registro:
            return []
        return sorted(registro["anotacoes"], key=lambda a: a["data_importacao"])

    def obter_historico_estruturado(self) -> Dict[str, List[Dict]]:
        """Retorna {lead_id: [anotações]} para todos os leads."""
        return {
            lead_id: sorted(v["anotacoes"], key=lambda a: a["data_importacao"])
            for lead_id, v in self._dados["leads"].items()
        }

    def exportar_para_dataframe(self, df_original: pd.DataFrame) -> pd.DataFrame:
        """
        Adiciona coluna 'historico' ao DataFrame com lista de anotações por lead.
        Espera coluna 'id' ou 'lead_id' no DataFrame.
        """
        historico = self.obter_historico_estruturado()

        col_id = None
        for c in ["id", "lead_id", "numero", "número"]:
            if c in df_original.columns:
                col_id = c
                break

        if col_id is None:
            df_original["historico"] = [[] for _ in range(len(df_original))]
            return df_original

        df = df_original.copy()
        df["historico"] = df[col_id].apply(lambda x: historico.get(str(x), []))
        return df

    @property
    def metadata(self) -> Dict:
        return self._dados["metadata"]
