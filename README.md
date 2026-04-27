# 📋 Leads · Planos de Saúde

Sistema para gerenciar leads recebidos via WhatsApp.

## Como instalar e rodar

### 1. Instalar Python
Baixe em: https://www.python.org/downloads/

### 2. Instalar as dependências
Abra o terminal na pasta do projeto e rode:
```
pip install -r requirements.txt
```

### 3. Rodar o app
```
streamlit run app.py
```

O navegador vai abrir automaticamente em: http://localhost:8501

---

## Como usar

### ➕ Aba "Novo Lead"
1. Cole o texto copiado do WhatsApp na caixinha
2. Os campos serão preenchidos automaticamente
3. Confira e ajuste o que precisar
4. Clique em **Salvar Lead**

### 📊 Aba "Dashboard"
- Veja todos os leads cadastrados
- Filtre por status, tipo ou busque por nome/CNPJ
- Acompanhe os gráficos de distribuição

### ✏️ Aba "Editar / Status"
- Atualize o status de um lead rapidamente
- Edite todos os dados de um lead
- Exclua leads se necessário

---

## Status disponíveis
- 🔵 **Novo** — lead recém-cadastrado
- 🟡 **Contatado** — já entrou em contato
- 🟣 **Proposta enviada** — cotação enviada
- 🟢 **Fechado** — venda realizada
- 🔴 **Perdido** — não converteu

---

O banco de dados fica salvo no arquivo `leads.db` na mesma pasta.
Faça backup desse arquivo para não perder seus dados!
