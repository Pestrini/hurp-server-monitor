# HURP Server Monitor (v0.4)

O **HURP Server Monitor** é uma aplicação web interativa desenvolvida em Python com [Streamlit](https://streamlit.io/), desenhada para otimizar e padronizar o processo de monitoramento de infraestrutura (servidores Windows e Linux) durante plantões de TI.

A partir da versão 0.4, o sistema consolidou suas capacidades de **Hub de Monitoramento Ativo** e aplicou rigorosas políticas de **Segurança de Dados** para ocultar IPs e Hostnames, integrando-se diretamente à API do Zabbix, aplicando inteligência preditiva e contando com um sistema robusto de autenticação e auditoria.

## 🚀 Novidades da Versão 0.4

- **Ocultação de Infraestrutura (Segurança):** Todos os IPs e Hostnames internos foram removidos do código-fonte e migrados para o arquivo `servers.json`, protegido pelo `.gitignore`.
- **Integração Zabbix via JSON-RPC:** Coleta automatizada de uso de disco, CPU, Memória, Swap, status de serviços e top processos diretamente da API do Zabbix, eliminando a necessidade de extrações manuais via terminal.
- **Inteligência Preditiva (Smart Status):** Cálculo automático da taxa de crescimento diário do disco (`crescimento_gb_dia`) e previsão de dias até o esgotamento total (`dias_para_encher`).
- **Autenticação e Perfis de Acesso:** Sistema de login com perfis de `admin` e `operador`, garantindo segurança no acesso e painel dedicado para gestão de usuários.
- **Segurança de Credenciais:** Integração de `.env` para proteção do token da API do Zabbix.

## ⚙️ Funcionalidades Principais

- **Ingestão Automatizada Zabbix:** Dispensa comandos manuais. Os discos importantes de servidores mapeados são lidos automaticamente com métricas precisas (suporta fallback manual via Clipboard-to-Report).
- **Processamento Inteligente e Predição:** 
  - Regras automáticas de status (`NORMAL`, `ATENÇÃO`, `CRÍTICO`, `ESTÁVEL`, `INATIVO`) baseadas não só na ocupação, mas no comportamento clínico preditivo de consumo.
- **Assistente de Resumo (IA de Plantão):** O sistema pré-preenche perguntas padrão de relatórios analisando o status clínico de cada disco e servidor inserido.
- **Múltiplos Formatos de Exportação:**
  - **Relatório TXT:** Para envio rápido via WhatsApp, Teams ou E-mail.
  - **Relatório Visual (HTML):** Dashboard HTML moderno e responsivo, categorizado por servidor (com suporte a impressão em PDF).
- **Dashboard de Histórico Integrado:**
  - Salva em um banco de dados local consolidado (`monitoramento_historico.csv` com 18 colunas de telemetria).
  - Painel gerencial (BI) na aba de histórico exibindo a evolução real da capacidade nos últimos meses.
- **Logs e Rastreabilidade:**
  - Registra erros não tratados em `logs/erros.log`.
  - Registra ações gerenciais e auditoria de usuários em `logs/acoes.log`.

## 🛠️ Tecnologias Utilizadas

- **[Python 3.9+](https://www.python.org/)**
- **[Streamlit](https://streamlit.io/):** Framework para a interface web.
- **[Pandas](https://pandas.pydata.org/):** Tratamento, limpeza e consolidação analítica dos dados.
- **[Requests](https://pypi.org/project/requests/):** Comunicação HTTP com a API RPC do Zabbix.

## ⚙️ Instalação e Configuração

### 1. Clonar o repositório

```bash
git clone https://github.com/Pestrini/hurp-server-monitor.git
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

### 3. Configuração de Variáveis de Ambiente (.env)
Crie um arquivo `.env` na raiz do projeto contendo as credenciais de acesso da API do Zabbix:
```env
ZABBIX_API_URL=http://<IP_OU_DOMINIO>/zabbix/api_jsonrpc.php
ZABBIX_API_TOKEN=<SEU_TOKEN_DE_ACESSO>
```

### 4. Gestão de Usuários Iniciais
No primeiro acesso, utilize o usuário admin configurado previamente no `users.json` para acessar a plataforma e cadastrar os demais analistas da equipe.

## 🏃 Como Executar

Se você estiver em um ambiente Windows local ou mapeamento de rede, basta utilizar o arquivo Batch já configurado:
```cmd
Iniciar_Monitoramento.bat
```

Ou inicie manualmente via terminal usando o Python (método recomendado para Windows):
```bash
python -m streamlit run app.py
```
O sistema abrirá automaticamente uma aba no seu navegador padrão (geralmente em `http://localhost:8501`), solicitando login.

## 📖 Como Usar (Fluxo Básico)

1. Faça Login com seu usuário na tela inicial.
2. Na aba de "Busca Zabbix", clique no botão de atualização para que o sistema puxe os dados automaticamente do servidor (Processador, RAM, Discos, Tendências).
3. Caso exista algum servidor que não está no Zabbix, cole a saída do terminal (`df -h` / `PowerShell`) na aba "Leitura Manual".
4. Verifique a tabela resultante e ajuste os status sugeridos pela Inteligência Preditiva, caso o seu conhecimento humano discorde da máquina.
5. Edite as considerações finais geradas pelo Assistente no rodapé da página.
6. Clique em **Salvar e Consolidar**. O arquivo de histórico será atualizado de forma segura, e os relatórios estarão prontos para cópia ou download.

## 🤝 Suporte e Autoria

Desenvolvido por **Gabriel Pestrini** (@PeSt)  
Contato: [gabriel.pestrini@unimedribeirao.com.br](mailto:gabriel.pestrini@unimedribeirao.com.br)

---
*Este é um projeto interno de monitoramento de infraestrutura desenhado para garantir agilidade operacional e previsibilidade de falhas para a equipe do HURP.*
