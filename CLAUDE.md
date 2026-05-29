# Dashboard Leads — O2 Solution

Dashboard de acompanhamento de leads em tempo real, construído com Streamlit. Consome API externa via token OAuth.

## Arquivos do projeto

| Arquivo | Descrição |
|---|---|
| `dashboard_tv_novo.py` | Arquivo principal (~2200 linhas) |
| `config.py` | Carrega variáveis de ambiente (ACCESS_TOKEN, REFRESH_TOKEN, CLIENT_ID, CLIENT_SECRET) |
| `renovar_token.py` | Renovação do token OAuth |
| `app.py` | Versão anterior/alternativa |
| `dashboard_tv.py` | Versão antiga |
| `teste_api.py` / `teste2_status.py` | Scripts de teste da API |
| `inspecionar_lead.py` / `inspecionar_anotacoes.py` | Utilitários de inspeção |
| `requirements.txt` | Dependências |
| `fotos/` | Fotos dos operadores (giovanna.jpg, rayanna.jpg) |

## Mapa de seções — dashboard_tv_novo.py

| Linha | Seção |
|---|---|
| 1–10 | Imports |
| 13–20 | Config Streamlit (`st.set_page_config`) |
| 22–58 | Constantes: `ORIGEM_MAP`, `STATUS_MAP`, `PERCEPTION_MAP`, `CORES_STATUS`, `CORES_PERCEPTION` |
| 60–86 | `horas_uteis()` — cálculo de horas úteis (pula fins de semana e feriados BR) |
| 89–334 | `inject_css()` — todo o CSS customizado (tema escuro, variáveis CSS, cards, tabelas) |
| 335–521 | Busca de dados da API |
| 522–590 | Helpers gerais |
| 591–922 | Funções de gráficos |
| 923–1059 | `modal_lead()` — modal de detalhes do lead |
| 1060–1336 | Fragments de tempo real (abas) |
| 1337–2170 | MAIN: cabeçalho, loading, abas, rodapé |
| 2171+ | Rodapé |

## Funções principais

### Busca de dados (linhas 335–521)
- `_fetch_leads_from_api(days, date_of)` — chamada base à API com paginação
- `fetch_leads_30dias()` — leads dos últimos 30 dias
- `fetch_leads_80dias()` — leads dos últimos 80 dias
- `fetch_leads_criticos()` — leads críticos
- `fetch_leads_hoje()` — leads do dia
- `merge_leads_curto()` / `merge_leads_longo()` — merge dos dataframes curto/longo

### Helpers (linhas 522–590)
- `fmt_brl(valor)` — formata valor em R$
- `foto_base64(path)` — carrega foto como base64
- `linhas_por_operador(df, status_filtro, cor)` — HTML de linhas de leads por operador
- `render_card(icone, valor, label, cor, df, status_filtro)` — card HTML de métrica

### Gráficos (linhas 591–922)
- `grafico_rosca(df)` — rosca de status
- `grafico_origens(df)` — barras de origens
- `grafico_acumulado(df, operadores)` — linha acumulada por operador
- `grafico_funil_status(df_atendente)` — funil por atendente
- `grafico_temperatura_pizza(df_atendente)` — pizza de temperatura (quente/morno/frio)
- `render_painel_atendente(df_atendente, nome, cor, foto_path)` — painel completo do atendente (linhas 748–922)

### Abas principais (linhas 1337+)
- `render_visao_geral(df_todos)` — aba Visão Geral (linha 1390)
- `render_operadores(df_todos)` — aba Operadores (linha 1501)
- `render_detalhamento(df_todos)` — aba Detalhamento/tabela (linha 1537)
- `render_crm()` — aba CRM (linha 1765)
- `render_funil_rt()` — fragment Funil tempo real (linha 1076)
- `render_hoje_rt()` — fragment Hoje tempo real (linha 1182)
- `render_leads_rt()` — fragment Leads tempo real (linha 1273)

## Constantes importantes

```python
STATUS_MAP = {
    "pending": "Primeiro Contato",
    "scheduled": "Agendado",
    "proposal_sent": "Proposta Enviada",
    "waiting_billing": "Aguardando Pagamento",
    "sale_performed": "Venda Realizada",
    "sale_not_performed": "Venda não Realizada",
}

PERCEPTION_MAP = { "hot": "🔥 Quente", "warm": "🌡️ Morno", "cold": "🧊 Frio" }

CORES_STATUS = {
    "Primeiro Contato": "#4f8ef7",
    "Agendado": "#f59e0b",
    "Proposta Enviada": "#8b5cf6",
    "Aguardando Pagamento": "#f97316",
    "Venda Realizada": "#22c55e",
    "Venda não Realizada": "#ef4444",
}
```

## Variáveis de ambiente necessárias (.env)
- `ACCESS_TOKEN` — token de acesso à API
- `REFRESH_TOKEN` — token de renovação
- `CLIENT_ID` / `CLIENT_SECRET` — credenciais OAuth

## Como rodar
```bash
streamlit run dashboard_tv_novo.py
```

## Fluxo de trabalho
- **Commitar após cada mudança:** sempre que um arquivo for editado, fazer commit imediatamente para que o servidor SSH possa dar `git pull` e receber as alterações.

## Padrões do projeto
- Tema escuro com variáveis CSS em `:root`
- Fonte: DM Sans (Google Fonts)
- Cor de destaque principal: `#4f8ef7` (azul)
- Cards HTML inline via `st.markdown(..., unsafe_allow_html=True)`
- Gráficos com Plotly (`plotly.graph_objects`)
- Cache de dados com `@st.cache_data`
