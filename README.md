# HURP Server Monitor

O **HURP Server Monitor** é uma aplicação web interativa desenvolvida em Python com [Streamlit](https://streamlit.io/), desenhada para otimizar e padronizar o processo de monitoramento de discos de servidores (Windows e Linux) durante plantões de TI.

O sistema substitui rotinas manuais demoradas, permitindo que os analistas simplesmente copiem a saída de comandos do terminal (`df -h` no Linux ou comandos do PowerShell no Windows), colem na interface, e gerem relatórios automatizados, consolidados e visuais com apenas alguns cliques.

## 🚀 Funcionalidades Principais

- **Ingestão via Área de Transferência (Clipboard-to-Report):**
  - **Linux:** Suporte direto à saída do comando `df -h`. O sistema identifica automaticamente colunas, percentuais de uso, partições e monta o dataframe.
  - **Windows:** Suporte à saída de PowerShell (`Get-CimInstance Win32_LogicalDisk | Where-Object DriveType -eq 3 | Select-Object DeviceId, FreeSpace, Size`).
- **Suporte a OCR (Imagens):** Opcionalmente, os analistas podem realizar o upload de prints de tela do Windows Explorer, e o sistema utilizará OCR (`pytesseract`) para extrair as informações.
- **Processamento Automático:** 
  - Cálculo inteligente de GB/MB livres, usados e percentual total.
  - Regras automáticas de status (`NORMAL`, `ATENÇÃO`, `CRÍTICO`) baseadas em limites de capacidade.
- **Assistente de Resumo (IA de Plantão):** O sistema pré-preenche perguntas padrão de relatórios de plantão (Quais servidores apresentaram problema? Quais ações foram tomadas?) analisando o status de cada disco inserido.
- **Múltiplos Formatos de Exportação:**
  - **Relatório TXT:** Para envio rápido via WhatsApp, Teams ou E-mail.
  - **Relatório Visual (HTML):** Um dashboard HTML moderno e responsivo, categorizado por servidor (com suporte para impressão em PDF).
- **Dashboard de Histórico Integrado:**
  - Salva em um banco de dados local (`monitoramento_historico.csv`).
  - Painel gerencial (BI) na aba de histórico exibindo evolução da capacidade de disco dos últimos 3 meses usando gráficos de linha do Altair.
- **Logs e Rastreabilidade:**
  - Registra automaticamente erros não tratados na aplicação em `logs/erros.log`.
  - Registra ações gerenciais, como a limpeza de banco de dados e salvamento de dados atrelados ao Analista de Plantão em `logs/acoes.log`.

## 🛠️ Tecnologias Utilizadas

- **[Python 3.9+](https://www.python.org/)**
- **[Streamlit](https://streamlit.io/):** Framework para a interface web.
- **[Pandas](https://pandas.pydata.org/):** Tratamento, limpeza e organização estruturada dos dados.
- **[Pillow](https://python-pillow.org/) e [Pytesseract](https://pypi.org/project/pytesseract/):** Manipulação de imagens e OCR para leitura de prints.

## ⚙️ Instalação e Configuração

### 1. Clonar o repositório

```bash
git clone https://github.com/seu-usuario/hurp-server-monitor.git
cd hurp-server-monitor
```

### 2. Instalar as dependências

É recomendado criar um ambiente virtual (venv) antes de instalar os pacotes:

```bash
python -m venv venv
# No Windows:
venv\Scripts\activate
# No Linux/Mac:
source venv/bin/activate

pip install -r requirements.txt
```

### 3. Dependências de Sistema (Para OCR)
Caso vá utilizar a funcionalidade de leitura de imagens, você precisará ter o **Tesseract OCR** instalado no sistema operacional.
- **Windows:** Baixe e instale o [Tesseract at UB-Mannheim](https://github.com/UB-Mannheim/tesseract/wiki).
- **Linux:** `sudo apt-get install tesseract-ocr`

## 🏃 Como Executar

Se você estiver em um ambiente Windows, basta utilizar o arquivo Batch já configurado:
```cmd
Iniciar_Monitoramento.bat
```

Ou, inicie manualmente via terminal usando o Streamlit:
```bash
streamlit run app.py
```
O sistema abrirá automaticamente uma aba no seu navegador padrão (geralmente em `http://localhost:8501`).

## 📖 Como Usar (Fluxo Básico)

1. Selecione o **Analista de Plantão** na barra lateral.
2. Acesse seu servidor Linux via PuTTY/SSH, rode o comando `df -h` e copie o resultado.
3. Cole no campo de texto principal na aba de "Entrada de Dados" e clique em **Processar Texto**.
4. Repita o processo para os servidores Windows usando o script PowerShell recomendado.
5. Ajuste os status detectados na tabela se necessário.
6. Edite as considerações finais geradas pelo Assistente no rodapé da página.
7. Clique em **Salvar e Consolidar**. O arquivo de histórico será atualizado, e os botões de download dos relatórios (.txt e .html) ficarão disponíveis.

## 🤝 Suporte e Autoria

Desenvolvido por **Gabriel Pestrini** (@PeSt)  
Contato: [gabriel.pestrini@unimedribeirao.com.br](mailto:gabriel.pestrini@unimedribeirao.com.br)

---
*Este é um projeto interno de monitoramento de infraestrutura desenhado para garantir agilidade operacional para a equipe do HURP.*
