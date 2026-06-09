"""
Importação de Excel exportado do Followize para o histórico incremental.

Uso via terminal:
    python -m src.data.importar_excel_followize "caminho/arquivo.xlsx"
"""

import sys
from pathlib import Path

import pandas as pd

from src.data.historico_incremental import HistoricoIncremental


def processar_excel_followize(
    caminho_excel: str,
    caminho_historico: str = "data/historico_consolidado.json",
) -> dict:
    """
    Valida o arquivo, importa para o histórico incremental e imprime resultado.

    Retorna dict com chaves: sucesso, novos, duplicatas, leads_processados.
    """
    path = Path(caminho_excel)
    if not path.exists():
        print(f"❌ Arquivo não encontrado: {caminho_excel}")
        return {"sucesso": False, "erro": "Arquivo não encontrado"}

    if path.suffix.lower() not in {".xlsx", ".xls"}:
        print(f"❌ Formato não suportado: {path.suffix}. Use .xlsx ou .xls")
        return {"sucesso": False, "erro": "Formato não suportado"}

    print(f"Lendo arquivo: {path.name}")
    historico = HistoricoIncremental(caminho_historico)
    resultado = historico.adicionar_do_excel(caminho_excel)

    if not resultado.get("sucesso"):
        print(f"ERRO ao processar: {resultado.get('erro', 'desconhecido')}")
        return resultado

    print(f"Importacao concluida!")
    print(f"Leads processados : {resultado['leads_processados']}")
    print(f"Anotacoes novas   : {resultado['novos']}")
    print(f"Duplicatas        : {resultado['duplicatas']}")
    print(f"Salvo em          : {caminho_historico}")

    meta = historico.metadata
    print(f"\nTotais acumulados no historico:")
    print(f"  Leads : {meta['total_leads']}")
    print(f"  Notas : {meta['total_anotacoes']}")

    return resultado


def mesclar_historico_com_api(
    df_leads: pd.DataFrame,
    caminho_historico: str = "data/historico_consolidado.json",
) -> pd.DataFrame:
    """
    Adiciona coluna 'historico' ao DataFrame vindo da API.
    Retorna DataFrame enriquecido — linhas sem histórico recebem lista vazia.
    """
    try:
        historico = HistoricoIncremental(caminho_historico)
        return historico.exportar_para_dataframe(df_leads)
    except Exception as e:
        print(f"AVISO: Nao foi possivel mesclar historico: {e}")
        df_leads = df_leads.copy()
        df_leads["historico"] = [[] for _ in range(len(df_leads))]
        return df_leads


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python -m src.data.importar_excel_followize <caminho_do_excel>")
        print("Exemplo: python -m src.data.importar_excel_followize exports/leads_junho.xlsx")
        sys.exit(0)

    processar_excel_followize(sys.argv[1])
