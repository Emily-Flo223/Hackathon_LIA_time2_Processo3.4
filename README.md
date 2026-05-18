# Processo 3.4 — PROECE: Análise Automatizada de Relatórios de Ações de Extensão

## Visão Geral

Este projeto implementa um **agente inteligente baseado em LangGraph** para automatizar a análise de relatórios de ações de extensão submetidos à PROECE/UFMS, com uma **interface web completa** para revisão humana.

O sistema recebe relatórios em PDF ou DOCX, extrai os dados via LLM, valida as informações contra as bases institucionais e gera automaticamente:

- Parecer técnico em Markdown
- Minuta de e-mail para o coordenador
- JSON estruturado com todas as evidências
- Planilha consolidada de todas as auditorias
- Logs rastreáveis por execução (UUID)

O objetivo é reduzir o tempo de análise manual, padronizar decisões e aumentar a confiabilidade da auditoria documental na PROECE.

---

## Objetivo do Processo 3.4

O processo automatizado corresponde à etapa de:

> **Análise de Relatórios de Ações de Extensão (PROECE)**

O agente verifica se os relatórios enviados pelos coordenadores:

- possuem todas as seções obrigatórias
- apresentam coerência financeira com os fomentos concedidos
- possuem bolsistas válidos com vínculo e período corretos
- respeitam a carga horária declarada
- contêm informações suficientes para aprovação

Ao final, o sistema decide automaticamente entre:

| Decisão | Significado |
|---------|-------------|
| `APROVAR` | Relatório em conformidade total |
| `DEVOLVER PARA AJUSTES` | Divergências pontuais corrigíveis |
| `DEVOLVER PARA REELABORAÇÃO` | Ausência de seções obrigatórias (requer reescrita) |

---

## Arquitetura Geral

```
Relatórios PDF/DOCX
        │
        ▼
┌─────────────────────────────────────────────────────┐
│                  AGENTE LANGGRAPH                   │
│                                                     │
│  ingest → extract (LLM) → load_bases               │
│                                │                    │
│          ┌─────────────────────┤                    │
│          ▼         ▼           ▼                    │
│   check_financial  check_bolsistas  check_completeness │
│          └─────────────────────┘                    │
│                          │                          │
│                    compose_parecer                  │
│                          │                          │
│                      emit_artifacts                 │
└─────────────────────────────────────────────────────┘
        │
        ▼
  output/ (JSON + MD + TXT + XLSX)
        │
        ▼
┌─────────────────────────────────────────────────────┐
│              INTERFACE STREAMLIT                    │
│  Home · Detalhes · Estatísticas · Executar Agente  │
└─────────────────────────────────────────────────────┘
```

---

## Desenho do Grafo do Agente

```mermaid
flowchart TD
    START([START]) --> INGEST[ingest_report]
    INGEST --> EXTRACT[extract_structured]
    EXTRACT --> LOAD[load_internal_bases]

    LOAD --> FINANCEIRO[check_financial]
    LOAD --> BOLSISTAS[check_bolsistas]
    LOAD --> COMPLETUDE[check_completeness]

    FINANCEIRO --> COMPOSE[compose_parecer]
    BOLSISTAS --> COMPOSE
    COMPLETUDE --> COMPOSE

    COMPOSE --> EMIT[emit_artifacts]
    EMIT --> END([END])
```

---

## Estrutura do Projeto

```text
.
├── data/                          # Dados de entrada
│   ├── relatorio_01_E3.docx       # Relatórios de extensão (PDF e DOCX)
│   ├── relatorio_02_E1.pdf        # ...
│   ├── edital_bolsistas.csv       # Base oficial de bolsistas do edital
│   ├── fomentos_concedidos.csv    # Valores de fomento aprovados por projeto
│   ├── gabarito.csv               # Gabarito das decisões corretas (para medir acurácia)
│   └── EDITAL_190_2026_PROECE_BOLSISTAS.pdf
│
├── nodes/                         # Nós do grafo LangGraph
│   ├── ingest_report.py           # Nó 1: leitura e extração de texto bruto
│   ├── extract_structured.py      # Nó 2: extração estruturada via LLM
│   ├── load_internal_bases.py     # Nó 3: carregamento das bases internas
│   ├── check_financial.py         # Nó 4: auditoria financeira (E1)
│   ├── check_bolsistas.py         # Nó 5: validação de bolsistas (E2, E3)
│   ├── check_completeness.py      # Nó 6: completude e carga horária (E4, E5)
│   ├── compose_parecer.py         # Nó 7: composição do parecer e decisão final
│   └── emit.py                    # Nó 8: gravação dos artefatos de saída
│
├── interface/                     # Interface web Streamlit
│   ├── app.py                     # Ponto de entrada (autenticação/login)
│   └── pages/
│       ├── home.py                # Kanban de relatórios + métricas + busca
│       ├── detalhes.py            # Detalhes, e-mail editável, downloads, anotação
│       ├── estatisticas.py        # Acurácia, distribuição de erros, comparação gabarito
│       └── executar.py            # Execução e reprocessamento do agente pela interface
│
├── output/                        # Saídas geradas pelo agente
│   ├── relatorio_01_E3/
│   │   ├── dados_auditoria_relatorio_01_E3.json
│   │   ├── parecer_auditoria_relatorio_01_E3.md
│   │   └── minuta_email_relatorio_01_E3.txt
│   ├── ...
│   └── consolidado_auditoria.xlsx
│
├── reviewed/                      # Relatórios marcados como revisados pelo auditor
│   └── relatorio_XX/
│       ├── dados_auditoria_*.json
│       ├── parecer_auditoria_*.md
│       ├── minuta_email_*.txt
│       └── anotacao_humana_*.txt  # Anotação do auditor humano
│
├── prompts/                       # Prompts do LLM
│   ├── extract_system_v1.0.txt
│   └── extract_user_v1.0.txt
│
├── logs/
│   └── agente_execucoes.jsonl     # Logs estruturados por execução (UUID)
│
├── tests/                         # Testes unitários
│   ├── test_ingest_report.py
│   └── test_load_internal_bases.py
│
├── utils/
│   └── logger.py                  # Logger estruturado JSON
│
├── graph.py                       # Montagem do grafo LangGraph
├── state.py                       # Estado compartilhado do agente
├── llm.py                         # Configuração do LLM via OpenRouter
├── run_graph.py                   # Script de execução em lote via terminal
├── gerar_relatorios_extensao.py   # Gerador de relatórios sintéticos para teste
└── requirements.txt
```

---

## Como Executar o Sistema Completo

### Pré-requisitos

- Python 3.12+
- Conta e chave de API no [OpenRouter](https://openrouter.ai) (gratuito para começar)
- Git

---

### 1. Clone o repositório

```bash
git clone <url-do-repositorio>
cd Hackathon_LIA_time2_Processo3.4
```

---

### 2. Crie e ative o ambiente virtual

**Linux/macOS:**
```bash
python -m venv venv
source venv/bin/activate
```

**Windows:**
```bash
python -m venv venv
venv\Scripts\activate
```

---

### 3. Instale as dependências

```bash
pip install -r requirements.txt
```

---

### 4. Configure a variável de ambiente

Crie um arquivo `.env` na raiz do projeto:

```env
OPENROUTER_API_KEY=sk-or-v1-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

> Obtenha sua chave gratuitamente em [openrouter.ai/keys](https://openrouter.ai/keys).  
> O agente usa o modelo `openai/gpt-4o-mini` por padrão (baixo custo).

---

### 5. Gere os relatórios sintéticos de teste (opcional)

Se a pasta `data/` ainda não tiver relatórios, gere 30 documentos sintéticos:

```bash
python gerar_relatorios_extensao.py
```

Isso cria 15 arquivos `.docx` e 15 arquivos `.pdf` com diferentes cenários de erro.

---

### 6. Execute o agente (via terminal)

```bash
python run_graph.py
```

O agente processa todos os relatórios da pasta `data/` e salva os resultados em `output/`.

Para controlar a quantidade de relatórios processados, edite a variável no topo do arquivo:

```python
QUANTIDADE_A_EXECUTAR = 30  # altere conforme necessário
```

---

### 7. Inicie a interface web

```bash
streamlit run interface/app.py
```

Acesse em: **http://localhost:8501**

---

### Credenciais de acesso (ambiente de teste)

| Usuário | Senha | Perfil | Permissões |
|---------|-------|--------|------------|
| `admin` | `proece2024` | Administrador | Acesso total |
| `auditor` | `ufms2024` | Auditor | Acesso total |
| `demo` | `demo` | Visualizador | Somente leitura (não pode executar o agente) |

---

## Interface Web

A interface foi construída em Streamlit e possui 4 telas:

### Home
- Kanban com duas colunas: **Analisar** (resultados do agente) e **Analisados** (revisados pelo auditor)
- Métricas em tempo real: total processados, aprovados, ajustes, reelaborações
- Barra de progresso de aprovação
- Busca por nome do projeto ou coordenador
- Filtros por classificação em cada coluna
- Botão **↩️ Reavaliar** para devolver um relatório da coluna Analisados de volta para revisão

### Detalhes
- Banner colorido com a decisão do agente (verde/amarelo/vermelho)
- Informações extraídas do relatório (título, coordenador, protocolo, tipo)
- Cards das 3 auditorias paralelas com status e evidências
- Lista expandida de divergências acumuladas
- **Anotação do auditor** ao marcar como Analisado (salva em arquivo)
- **E-mail editável**: o auditor pode editar a minuta antes de enviar, salvar as alterações e restaurar o original
- **Downloads diretos**: parecer `.md`, e-mail `.txt`, dados `.json`

### Estatísticas
- Acurácia do agente comparada com o gabarito oficial (`data/gabarito.csv`)
- Distribuição das decisões (aprovados / ajustes / reelaboração)
- Tabela comparativa Agente vs Gabarito com filtro acertos/erros
- Distribuição por tipo de erro (E1 a E6)
- Taxa de falha por componente de auditoria

### Executar Agente
- Card com relatórios classificados como **Reelaboração** e botão de reprocessamento direto
- Slider para configurar quantidade de relatórios a processar
- Preview dos relatórios que serão processados
- Log em tempo real durante a execução
- Bloqueado para o perfil Visualizador

---

## Fluxo Completo do Agente

### Nó 1 — Ingestão (`ingest_report.py`)

Lê o arquivo PDF ou DOCX, extrai o texto bruto e normaliza o conteúdo para processamento.

### Nó 2 — Extração Estruturada (`extract_structured.py`)

Usa o LLM (GPT-4o-mini via OpenRouter) com saída estruturada para extrair:
- coordenador, protocolo, título, tipo de relatório
- bolsistas com nome, CPF, vínculo e período de atuação
- recursos financeiros e prestação de contas
- atividades realizadas com carga horária
- seções textuais obrigatórias (objetivo, metodologia, resultados etc.)

Complementa a extração com regex para protocolo (`FAENG.123456`), ID do relatório e tipo.

### Nó 3 — Carregamento das Bases (`load_internal_bases.py`)

Carrega os CSVs institucionais que servem como fonte de verdade:
- `fomentos_concedidos.csv` — valores aprovados por projeto
- `edital_bolsistas.csv` — lista oficial de bolsistas

### Nós 4, 5, 6 — Verificações Paralelas

Executados simultaneamente pelo LangGraph:

| Nó | Arquivo | Erros detectados |
|----|---------|-----------------|
| check_financial | `check_financial.py` | **E1**: valor declarado diverge do concedido em mais de 1% |
| check_bolsistas | `check_bolsistas.py` | **E2**: bolsista não consta no edital; **E3**: período de vigência incorreto |
| check_completeness | `check_completeness.py` | **E4**: seção obrigatória ausente; **E5**: soma de horas inconsistente |

> **E6** (tipo de relatório inadequado para a fase do projeto) é identificado na extração e validado no compose.

### Nó 7 — Composição do Parecer (`compose_parecer.py`)

Consolida todas as divergências e aplica a regra de decisão:

```
E4 encontrado?  → DEVOLVER PARA REELABORAÇÃO
Outra divergência? → DEVOLVER PARA AJUSTES
Nenhuma divergência? → APROVAR
```

Gera o parecer técnico em Markdown e a minuta de e-mail para o coordenador.

### Nó 8 — Emissão de Artefatos (`emit.py`)

Salva todos os artefatos em `output/{nome_relatorio}/` e atualiza a planilha consolidada.

---

## Saídas Geradas

Para cada relatório processado:

```text
output/
└── relatorio_01_E3/
    ├── dados_auditoria_relatorio_01_E3.json    ← estrutura completa da auditoria
    ├── parecer_auditoria_relatorio_01_E3.md    ← parecer técnico formatado
    └── minuta_email_relatorio_01_E3.txt        ← e-mail para o coordenador
```

Consolidado geral:

```text
output/consolidado_auditoria.xlsx   ← todas as auditorias em abas "Divergências" e "Estatísticas"
```

Após revisão humana via interface:

```text
reviewed/
└── relatorio_01_E3/
    ├── dados_auditoria_relatorio_01_E3.json
    ├── parecer_auditoria_relatorio_01_E3.md
    ├── minuta_email_relatorio_01_E3.txt
    └── anotacao_humana_relatorio_01_E3.txt     ← nota do auditor
```

---

## Logs Estruturados

```text
logs/agente_execucoes.jsonl
```

Cada linha é um evento JSON com:
- `execution_id` — UUID único por execução
- `timestamp` — data e hora do evento
- `arquivo` — relatório processado
- `message` — decisão final ou evento do pipeline

Permite rastreabilidade completa e auditoria das execuções.

---

## Categorias de Erro

| Código | Nome | Regra | Decisão |
|--------|------|-------|---------|
| E1 | Inconsistência Financeira | Valor declarado diverge do concedido em mais de 1% | Ajustes |
| E2 | Bolsista Inválido | Bolsista não consta no edital oficial | Ajustes |
| E3 | Período Inválido | Período de vigência do bolsista difere do edital | Ajustes |
| E4 | Seção Ausente | Seção obrigatória não preenchida | **Reelaboração** |
| E5 | Horas Inconsistentes | Soma das atividades diverge do total declarado | Ajustes |
| E6 | Tipo Inadequado | Tipo de relatório incompatível com a fase do projeto | Ajustes |
| OK | Sem erros | Todas as validações passaram | Aprovado |

---

## Tecnologias Utilizadas

| Tecnologia | Uso |
|------------|-----|
| Python 3.12+ | Linguagem principal |
| LangGraph | Orquestração do agente em grafo com paralelismo |
| LangChain / langchain-openai | Integração com LLM |
| OpenRouter + GPT-4o-mini | Extração estruturada via LLM |
| Pydantic v2 | Validação de schemas e estado do agente |
| Streamlit | Interface web |
| Pandas | Manipulação de dados e planilhas |
| PDFPlumber + PyPDF | Extração de texto de PDFs |
| python-docx | Leitura de arquivos DOCX |
| openpyxl | Geração da planilha consolidada (.xlsx) |
| reportlab | Geração de PDFs sintéticos |
| python-dotenv | Gerenciamento de variáveis de ambiente |
| pytest | Testes unitários |

---

## Testes

```bash
pytest
```

Testes disponíveis em `tests/`:
- `test_ingest_report.py` — ingestão de PDF e DOCX
- `test_load_internal_bases.py` — carregamento das bases CSV

---

## Diferenciais Técnicos

**Execução paralela real**  
Os nós `check_financial`, `check_bolsistas` e `check_completeness` rodam simultaneamente via LangGraph fan-out/fan-in, reduzindo o tempo de auditoria.

**Estado compartilhado tipado**  
Todos os nós leem e escrevem em um `AgenteState` centralizado com tipos definidos em Pydantic, garantindo consistência e facilidade de debug.

**Extração robusta com fallback**  
A extração combina LLM (para texto semântico) com regex (para campos estruturados como protocolo e ID), tornando o sistema resiliente a diferentes formatos de documento.

**Rastreabilidade por UUID**  
Cada execução tem um identificador único persistido nos logs e nos JSONs de saída.

**Interface com revisão humana completa**  
O fluxo de revisão humana — ver resultado, editar e-mail, anotar, mover para analisados, devolver para reavaliação — está completamente implementado na interface.

---

## Limitações Conhecidas

- Dependência da qualidade de extração do LLM em documentos muito mal formatados
- PDFs baseados em imagem (sem OCR) não são suportados
- A chave do OpenRouter é necessária para rodar o agente (extração LLM); sem ela, somente a interface com dados já processados funciona

---

## Possíveis Evoluções

- Integração direta com SEI/SIGProj para recebimento automático dos relatórios
- RAG com as normativas da PROECE para fundamentação regulamentar dos pareceres
- Assinatura digital automática dos pareceres aprovados
- Banco de dados institucional para persistência e histórico
- Notificações automáticas por e-mail aos coordenadores
- Suporte a OCR para PDFs baseados em imagem

---

## Conclusão

O projeto demonstra uma arquitetura moderna de agentes baseada em grafos para automação documental institucional. A solução atende aos objetivos do Processo 3.4 da PROECE ao:

- automatizar auditorias que antes eram feitas manualmente
- padronizar decisões com critérios objetivos e rastreáveis
- reduzir esforço operacional da equipe técnica
- gerar documentação estruturada e auditável
- oferecer interface completa para revisão e controle humano

A arquitetura modular baseada em LangGraph permite expansão futura para outros processos administrativos da UFMS sem reescrita do núcleo do sistema.

---

*Desenvolvido para o Hackathon LIA — UFMS Apoia MDA | Time 2 — Processo 3.4*
