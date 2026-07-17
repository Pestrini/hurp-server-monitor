import streamlit as st
import pandas as pd
from datetime import datetime
from parser_engine import parse_df_h_output
from report_generator import pre_fill_answers, generate_txt_report, save_to_csv
import auth_manager
import zabbix_client

import os
import logging

st.set_page_config(page_title="HURP Server Monitor", layout="wide")

if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False
if "username" not in st.session_state:
    st.session_state["username"] = ""
if "name" not in st.session_state:
    st.session_state["name"] = ""
if "role" not in st.session_state:
    st.session_state["role"] = ""
if "editing_user" not in st.session_state:
    st.session_state["editing_user"] = None

if not os.path.exists("logs"):
    os.makedirs("logs")

error_logger = logging.getLogger("error_logger")
error_logger.setLevel(logging.ERROR)
if not error_logger.handlers:
    fh = logging.FileHandler("logs/erros.log", encoding="utf-8")
    fh.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
    error_logger.addHandler(fh)

action_logger = logging.getLogger("action_logger")
action_logger.setLevel(logging.INFO)
if not action_logger.handlers:
    fh2 = logging.FileHandler("logs/acoes.log", encoding="utf-8")
    fh2.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
    action_logger.addHandler(fh2)

try:

    st.markdown("""
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    .custom-footer {
        position: fixed;
        bottom: 0;
        right: 15px;
        width: auto;
        background-color: transparent;
        color: #888;
        text-align: right;
        padding: 10px;
        font-size: 13px;
        z-index: 1000;
    }
    .custom-footer a {
        color: #1976d2;
        text-decoration: none;
        font-weight: bold;
    }
    </style>
    <div class="custom-footer">
        by: <b>PeSt</b> | support: <a href="mailto:gabriel.pestrini@unimedribeirao.com.br">gabriel.pestrini@unimedribeirao.com.br</a>
    </div>
    """, unsafe_allow_html=True)

    if "parsed_data" not in st.session_state:
        st.session_state["parsed_data"] = []

    if os.path.exists("hurp_server_monitor_logo.png"):
        st.sidebar.image("hurp_server_monitor_logo.png", use_container_width=True)

    if not st.session_state["logged_in"]:
        st.title("HURP Server Monitor - Login")
        with st.form("login_form"):
            user_input = st.text_input("Usuário")
            pass_input = st.text_input("Senha", type="password")
            submitted = st.form_submit_button("Entrar")
            
            if submitted:
                user_data = auth_manager.authenticate(user_input, pass_input)
                if user_data:
                    st.session_state["logged_in"] = True
                    st.session_state["username"] = user_input
                    st.session_state["role"] = user_data["role"]
                    st.session_state["name"] = user_data["name"]
                    st.success("Login realizado com sucesso!")
                    st.rerun()
                else:
                    st.error("Usuário ou senha inválidos.")
        st.stop()

    st.sidebar.title(f"Bem-vindo, {st.session_state['name']}!")
    if st.sidebar.button("Sair (Logout)"):
        st.session_state["logged_in"] = False
        st.session_state["username"] = ""
        st.session_state["name"] = ""
        st.session_state["role"] = ""
        st.rerun()
        
    analista = st.session_state["name"]

    if st.session_state["role"] == "admin":
        st.sidebar.markdown("---")
        with st.sidebar.expander("⚙️ Gerenciar Usuários", expanded=False):
            users = auth_manager.get_all_users()
            
            tab_new, tab_edit = st.tabs(["Novo", "Usuários"])
            with tab_new:
                with st.form("add_user_form", clear_on_submit=True):
                    new_user = st.text_input("Novo Usuário (Login)")
                    new_name = st.text_input("Nome Completo")
                    new_pass = st.text_input("Senha", type="password")
                    new_role = st.selectbox("Perfil", ["operador", "admin"])
                    if st.form_submit_button("Criar Usuário"):
                        if new_user and new_pass and new_name:
                            if new_user in users:
                                st.error("Usuário já existe.")
                            else:
                                auth_manager.add_user(new_user, new_pass, new_role, new_name, st.session_state["username"])
                                st.success(f"Usuário {new_user} salvo!")
                                st.rerun()
                        else:
                            st.error("Preencha todos os campos obrigatórios.")
            
            with tab_edit:
                if st.session_state["editing_user"]:
                    selected_user = st.session_state["editing_user"]
                    if selected_user in users:
                        u_data = users[selected_user]
                        st.markdown(f"**Editando:** {selected_user}")
                        with st.form("edit_user_form", clear_on_submit=True):
                            edit_name = st.text_input("Nome Completo", value=u_data['name'])
                            role_options = ["operador", "admin"]
                            try:
                                role_index = role_options.index(u_data['role'])
                            except ValueError:
                                role_index = 0
                            edit_role = st.selectbox("Perfil", role_options, index=role_index)
                            edit_pass = st.text_input("Nova Senha (deixe em branco para manter)", type="password")
                            
                            c1, c2, c3 = st.columns(3)
                            with c1:
                                if st.form_submit_button("Salvar"):
                                    if edit_name:
                                        auth_manager.update_user_info(selected_user, edit_role, edit_name, st.session_state["username"], edit_pass)
                                        st.session_state["editing_user"] = None
                                        st.success("Atualizado!")
                                        st.rerun()
                                    else:
                                        st.error("Nome obrigatório.")
                            with c2:
                                if st.form_submit_button("Excluir"):
                                    if selected_user == st.session_state["username"]:
                                        st.error("Você não pode excluir a si mesmo.")
                                    elif auth_manager.delete_user(selected_user, st.session_state["username"]):
                                        st.session_state["editing_user"] = None
                                        st.success("Excluído!")
                                        st.rerun()
                            with c3:
                                if st.form_submit_button("Cancelar"):
                                    st.session_state["editing_user"] = None
                                    st.rerun()
                else:
                    st.write("Usuários atuais:")
                    for u, data in users.items():
                        c_name, c_btn = st.columns([0.7, 0.3])
                        with c_name:
                            st.markdown(f"- **{u}** ({data['name']})")
                        with c_btn:
                            if st.button("Editar", key=f"btn_edit_{u}"):
                                st.session_state["editing_user"] = u
                                st.rerun()
    
    with st.sidebar.expander("🔐 Alterar Minha Senha", expanded=False):
        with st.form("change_pass_form", clear_on_submit=True):
            old_pass = st.text_input("Senha Atual", type="password")
            new_pass = st.text_input("Nova Senha", type="password")
            if st.form_submit_button("Alterar Senha"):
                if auth_manager.change_password(st.session_state["username"], old_pass, new_pass):
                    st.success("Senha alterada com sucesso!")
                else:
                    st.error("Senha atual incorreta.")

    st.sidebar.markdown("---")
    with st.sidebar.expander("📖 Passo a Passo & Comandos", expanded=True):
        st.markdown("""
        **1. Buscar no Zabbix**
        - Clique no botão à direita para buscar automaticamente dados de 1 ano.

        **2. Servidores Linux (Não Zabbix)**
        - Acesse o servidor via PuTTY ou SSH.
        - Execute o comando unificado abaixo:
        ```bash
        echo "===HURP_DIAGNOSTICO===" && echo "HOST: $(hostname)" && echo "---DISK---" && df -h | grep -E 'dados|backup|binario|root|tmp|boot|/dev/mapper|/' && echo "---MEM_SWAP---" && free -m && echo "---TOP_CPU---" && ps -eo %cpu,%mem,comm --sort=-%cpu | head -n 6 && echo "---SERVICES---" && for svc in cache tomcat httpd nginx docker; do echo "$svc:$(systemctl is-active $svc 2>/dev/null || echo 'not_installed')"; done
        ```
        - Copie a saída completa e cole na caixa de texto.

        **3. Servidores Windows (Não Zabbix)**
        - Acesse o servidor via RDP.
        - Abra o PowerShell **como Administrador**.
        - Execute o comando unificado abaixo:
        ```powershell
        Write-Output "===HURP_DIAGNOSTICO==="; Write-Output "HOST: $env:COMPUTERNAME"; Write-Output "---DISK---"; Get-Volume | Where-Object {$_.DriveLetter -in @('C','Z','E','H','F')} | Format-Table DriveLetter, FileSystemLabel, SizeRemaining, Size -HideTableHeaders; Write-Output "---MEM_SWAP---"; Get-CimInstance Win32_OperatingSystem | Select-Object TotalVisibleMemorySize, FreePhysicalMemory, TotalVirtualMemorySize, FreeVirtualMemory | Format-List; Write-Output "---TOP_CPU---"; Get-Process | Sort-Object CPU -Descending | Select-Object -First 5 Name, CPU, WorkingSet | Format-Table -HideTableHeaders; Write-Output "---SERVICES---"; Get-Service -Name "IISADMIN", "Tomcat*", "MConnect", "IDCE", "Cache*" -ErrorAction SilentlyContinue | Select-Object Name, Status | Format-Table -HideTableHeaders
        ```
        - Copie a saída e cole na caixa de texto.
        **4. Consolidando**
        - Revise a tabela gerada, valide a marcação de 'Importante' para os discos.
        - Revise as respostas do Assistente de IA.
        - Clique em **Salvar e Consolidar**!
        """)

    with st.sidebar.expander("🖥️ Lista de Servidores", expanded=False):
        st.markdown("**Monitorados pelo Zabbix (Automático):**")
        df_zabbix = pd.DataFrame([
            ["SHIFT_DB_PRD", "Linux", "192.168.1.1", "SERVER-01"],
            ["SHIFT_SHADOW", "Linux", "192.168.1.2", "SERVER-02"],
            ["SHIFT_WEB", "Linux", "192.168.1.4", "SERVER-04"],
            ["SHIFT_AUTOMACAO", "Windows", "192.168.1.3", "SERVER-03"],
            ["MV_BALANCE", "Linux", "192.168.1.10", "SERVER-10"],
            ["MV_PRODUCAO_01", "Windows", "192.168.1.9", "SERVER-09"],
            ["VIVACE_PACS_01", "Windows", "192.168.1.5", "SERVER-05"]
        ], columns=["Servidor", "SO", "IP", "Hostname"])
        st.dataframe(df_zabbix, hide_index=True)
        
        st.markdown("**NÃO Monitorados (Copiar e Colar):**")
        df_manuais = pd.DataFrame([
            ["VIVACE_PACS_02", "Windows", "192.168.1.6", "SERVER-06"],
            ["VIVACE_PACS_WEB", "Windows", "192.168.1.7", "SERVER-07"],
            ["MV_PRODUCAO_02", "Linux", "192.168.1.8", "SERVER-08"],
            ["HINNO_APP", "Linux", "192.168.1.11", "SERVER-11"],
            ["GREEN", "Linux", "192.168.1.12", "SERVER-12"]
        ], columns=["Servidor", "SO", "IP", "Hostname"])
        st.dataframe(df_manuais, hide_index=True)

    st.title("HURP Server Monitor")

    tab1, tab2 = st.tabs(["Entrada de Dados", "Histórico de Monitoramento (Métricas de BI)"])

    with tab1:
        st.header("Área de Ingestão")
    
        col1, col2 = st.columns(2)
        with col1:
            from parser_engine import SERVERS
        
            if "raw_text" not in st.session_state:
                st.session_state["raw_text"] = ""
            
            def clear_inputs():
                st.session_state["raw_text"] = ""
                st.session_state["srv_txt"] = "Automático"
                if "generated_txt_report" in st.session_state:
                    st.session_state["generated_txt_report"] = None
            
            # Prioriza os servidores não-Zabbix no selectbox
            manual_servers = ["VIVACE_PACS_02", "VIVACE_PACS_WEB", "MV_PRODUCAO_02", "HINNO_APP", "GREEN"]
            zabbix_servers = ["SHIFT_DB_PRD", "SHIFT_SHADOW", "SHIFT_WEB", "SHIFT_AUTOMACAO", "MV_BALANCE", "MV_PRODUCAO_01", "VIVACE_PACS_01"]
            ordered_servers = manual_servers + zabbix_servers
            
            server_txt = st.selectbox("Servidor (Para inserção manual)", ["Automático"] + ordered_servers, key="srv_txt")
            text_input = st.text_area("Cole aqui o output do 'df -h' ou PowerShell", height=250, key="raw_text")
        
            c_btn1, c_btn2 = st.columns(2)
            with c_btn1:
                if st.button("Processar Texto Manual", use_container_width=True):
                    if text_input:
                        srv_param = None if server_txt == "Automático" else server_txt
                        new_data = parse_df_h_output(text_input, server_name=srv_param)
                        if new_data:
                            servers_in_new_data = set(item['servidor'] for item in new_data)
                            st.session_state["parsed_data"] = [
                                item for item in st.session_state["parsed_data"] 
                                if item['servidor'] not in servers_in_new_data
                            ]
                            st.session_state["parsed_data"].extend(new_data)
                            st.success("Texto processado!")
            with c_btn2:
                st.button("Limpar Campos", on_click=clear_inputs, use_container_width=True)
                
        with col2:
            st.subheader("📡 Integração Automática Zabbix")
            st.write("Busca as partições e gera a projeção matemática de tempo para encher baseado no histórico.")
            
            meses_opcoes = {"Últimos 6 Meses": 6, "Últimos 12 Meses": 12}
            meses_selecionado = st.selectbox("Período de Análise (Regressão)", list(meses_opcoes.keys()))
            
            if st.button("Buscar no Zabbix", use_container_width=True, type="primary"):
                action_logger.info(f"Analista {analista} iniciou busca no Zabbix (Período: {meses_selecionado}).")
                with st.spinner("Conectando à API do Zabbix e calculando projeções... (pode levar alguns segundos)"):
                    try:
                        meses = meses_opcoes[meses_selecionado]
                        zabbix_data = zabbix_client.fetch_zabbix_data(months=meses)
                        st.session_state["parsed_data"].extend(zabbix_data)
                        st.success("Dados do Zabbix importados com sucesso!")
                    except Exception as e:
                        st.error(f"Erro ao buscar no Zabbix: {str(e)}")

        if st.session_state["parsed_data"]:
            col_title, col_btn = st.columns([0.8, 0.2])
            with col_title:
                st.subheader("Dados Extraídos (Edite se necessário)")
            with col_btn:
                if st.button("Limpar Área", type="secondary", use_container_width=True):
                    st.session_state["parsed_data"] = []
                    st.rerun()
        
            df = pd.DataFrame(st.session_state["parsed_data"])
            
            if 'importante' not in df.columns:
                df['importante'] = False
            for col in ['cpu_percent', 'ram_percent', 'swap_percent', 'servicos_status', 'processos_top']:
                if col not in df.columns:
                    df[col] = "N/A"
        
            df = df[['importante', 'status_alerta', 'servidor', 'particao', 'percentual_uso', 'espaco_ocupado', 'espaco_disponivel', 'capacidade_total', 'crescimento_gb_dia', 'dias_para_encher', 'ip', 'so', 'zabbix_hostname', 'raw_percent', 'fonte', 'cpu_percent', 'ram_percent', 'swap_percent', 'servicos_status', 'processos_top']]
            
            edited_df = st.data_editor(
                df,
                num_rows="dynamic",
                column_config={
                    "status_alerta": st.column_config.SelectboxColumn(
                        "Status",
                        help="Status do disco",
                        options=["NORMAL", "ATENÇÃO", "CRÍTICO", "ESTÁVEL", "INATIVO"],
                        required=True
                    ),
                    "importante": st.column_config.CheckboxColumn(
                        "Importante",
                        help="Marcar para aparecer no relatório resumido",
                        default=False
                    ),
                    "cpu_percent": None,
                    "ram_percent": None,
                    "swap_percent": None,
                    "servicos_status": None,
                    "processos_top": None
                },
                hide_index=True
            )
        
            st.subheader("Assistente de IA - Respostas do Plantão")
            
            # --- DETECTOR DE COMPORTAMENTO CLINICO UI ---
            alertas_comportamentais = []
            servidores_processados = set()
            for row in edited_df.to_dict('records'):
                srv = row['servidor']
                if srv not in servidores_processados:
                    servidores_processados.add(srv)
                    cpu = row.get('cpu_percent', 'N/A')
                    ram = row.get('ram_percent', 'N/A')
                    swap = row.get('swap_percent', 'N/A')
                    svcs = row.get('servicos_status', 'N/A')
                    
                    if cpu != 'N/A' and isinstance(cpu, (int, float)) and cpu >= 90:
                        alertas_comportamentais.append(f"⚠️ **{srv}**: CPU alta ({cpu}%)")
                    if ram != 'N/A' and isinstance(ram, (int, float)) and ram >= 90:
                        alertas_comportamentais.append(f"⚠️ **{srv}**: RAM alta ({ram}%)")
                    if swap != 'N/A' and isinstance(swap, (int, float)) and swap >= 20:
                        alertas_comportamentais.append(f"⚠️ **{srv}**: Swap alta ({swap}%)")
                    if svcs != 'N/A' and any('not_installed' not in s and 'active' not in s.lower() and 'running' not in s.lower() for s in str(svcs).split('|')):
                        alertas_comportamentais.append(f"⚠️ **{srv}**: Serviços com problema ({svcs})")
            
            if alertas_comportamentais:
                st.warning("🚨 **Alertas Comportamentais Detectados:**\n\n" + "\n".join(alertas_comportamentais))
                
            answers = pre_fill_answers(edited_df.to_dict('records'))
        
            q1 = st.text_area("1. QUAIS SERVIDORES APRESENTARAM PROBLEMA?", value=answers["q1"])
            q2 = st.text_area("2. QUAIS AS AÇÕES IMEDIATAS?", value=answers["q2"])
            q3 = st.text_area("3. QUAIS PONTOS DE ATENÇÃO?", value=answers["q3"])
            q4 = st.text_area("4. ALGUMA INFORMAÇÃO ADICIONAL?", value=answers["q4"])
            q5 = st.text_area("5. ATIVIDADES PLANEJADAS (PROXIMOS PASSOS):", value=answers["q5"])
        
            final_answers = {"q1": q1, "q2": q2, "q3": q3, "q4": q4, "q5": q5}
        
            if st.button("Salvar e Consolidar", type="primary"):
                final_data = edited_df.to_dict('records')
                
                ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                for row in final_data:
                    row['timestamp'] = ts
            
                save_to_csv(final_data)
                action_logger.info(f"Analista {analista} salvou e consolidou os dados.")
                st.success("Dados salvos em monitoramento_historico.csv com sucesso!")
            
                ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                st.session_state["generated_txt_report"] = generate_txt_report(final_data, final_answers, analista, ts)
                st.session_state["final_data"] = final_data
                st.session_state["final_answers"] = final_answers
                st.session_state["report_ts"] = ts
                st.session_state["analista_sessao"] = analista

            if st.session_state.get("generated_txt_report"):
                txt_report = st.session_state["generated_txt_report"]
                final_data = st.session_state["final_data"]
                final_answers = st.session_state["final_answers"]
                ts = st.session_state["report_ts"]
                analista_str = st.session_state["analista_sessao"]
            
                st.subheader("Relatório Gerado (Texto)")
                st.code(txt_report, language="text")
                st.info("Utilize o botão no canto superior direito do bloco de texto para copiar para a área de transferência.")
            
                st.markdown("---")
                st.subheader("Downloads Disponíveis")
                
                def build_html_report(rows_data, answers, report_type="full"):
                    FRIENDLY_NAMES = {
                        "SHIFT_DB_PRD": "SHIFT PRODUÇÃO",
                        "SHIFT_SHADOW": "SHIFT SHADOW",
                        "VIVACE_PACS_01": "VIVACE PACS 01",
                        "VIVACE_PACS_02": "VIVACE PACS 02",
                        "VIVACE_PACS_WEB": "VIVACE PACS WEB",
                        "SHIFT_AUTOMACAO": "SHIFT AUTOMACAO",
                        "SHIFT_WEB": "SHIFT WEB",
                        "MV_PRODUCAO_01": "MV PRODUÇÃO",
                        "MV_PRODUCAO_02": "MV TOMCAT",
                        "MV_BALANCE": "MV BALANCE",
                        "HINNO_APP": "HINNO APP",
                        "GREEN": "GREEN"
                    }
                    
                    weekday_map = {0: "Segunda-feira", 1: "Terça-feira", 2: "Quarta-feira", 3: "Quinta-feira", 4: "Sexta-feira", 5: "Sábado", 6: "Domingo"}
                    weekday_str = weekday_map[datetime.strptime(ts, "%Y-%m-%d %H:%M:%S").weekday()]
                    
                    title = "Relatório Completo de Monitoramento" if report_type == "full" else "Relatório Resumido de Monitoramento"
                    
                    html_content = f"""
                    <html><head><style>
                    body {{ font-family: Arial, sans-serif; }}
                    @media print {{
                        body {{
                            -webkit-print-color-adjust: exact !important;
                            print-color-adjust: exact !important;
                        }}
                    }}
                    .grid {{ display: flex; flex-wrap: wrap; gap: 8px; }}
                    .card {{ width: 140px; padding: 8px; border-radius: 6px; color: white; box-shadow: 1px 1px 3px rgba(0,0,0,0.3); }}
                    .card h4 {{ margin: 0 0 4px 0; font-size: 13px; border-bottom: 1px solid rgba(255,255,255,0.3); padding-bottom: 2px; }}
                    .card .part {{ font-size: 11px; margin-bottom: 4px; }}
                    .card .uso {{ font-size: 15px; font-weight: bold; margin: 0; }}
                    .card .livre {{ font-size: 10px; opacity: 0.9; margin-top: 2px; }}
                    .normal {{ background-color: #2e7d32 !important; }}
                    .estável {{ background-color: #81c784 !important; color: #000 !important; }}
                    .atenção {{ background-color: #f57f17 !important; }}
                    .crítico {{ background-color: #c62828 !important; }}
                    .inativo {{ background-color: #607d8b !important; }}
                    .qa {{ background-color: #f4f4f4 !important; padding: 15px; border-left: 5px solid #1976d2 !important; margin-bottom: 20px; }}
                    .header-visual {{ background-color: #1976d2 !important; color: white !important; padding: 15px; border-radius: 8px; margin-bottom: 15px; text-align: center; }}
                    .legend {{ display: flex; gap: 15px; flex-wrap: wrap; margin-top: 30px; font-size: 13px; align-items: center; justify-content: center; background: #f4f4f4; padding: 8px; border-radius: 8px; }}
                    .leg-item {{ display: flex; align-items: center; gap: 5px; }}
                    .dot {{ width: 12px; height: 12px; border-radius: 50%; display: inline-block; }}
                    </style></head><body>
                    <div class="header-visual">
                        <h1 style="margin: 0;">{title}</h1>
                        <p style="margin: 5px 0 0 0; font-size: 14px;">Analista Responsável: <b>{analista_str}</b> | Data: <b>{ts} ({weekday_str})</b></p>
                    </div>
                    <h2>Status dos Discos e Comportamento</h2>
                    """
                    
                    grouped_data = {}
                    for row in rows_data:
                        if report_type == "resumido" and not row.get("importante", False):
                            continue
                        serv = row['servidor']
                        if serv not in grouped_data:
                            grouped_data[serv] = []
                        grouped_data[serv].append(row)
                        
                    for serv, rows in grouped_data.items():
                        friendly = FRIENDLY_NAMES.get(serv, serv)
                        ip_info = rows[0].get('ip', 'Desconhecido')
                        zbx_info = rows[0].get('zabbix_hostname', 'N/A')
                        if zbx_info and zbx_info != "N/A":
                            ip_info = f"{ip_info} - {zbx_info}"
                            
                        cpu = rows[0].get('cpu_percent', 'N/A')
                        ram = rows[0].get('ram_percent', 'N/A')
                        swap = rows[0].get('swap_percent', 'N/A')
                        svcs = rows[0].get('servicos_status', 'N/A')
                        procs = rows[0].get('processos_top', 'N/A')
                        
                        beh_html = f"<div style='font-size: 13px; color: #555; margin-bottom: 10px;'>"
                        beh_html += f"<b>CPU:</b> {cpu}% | <b>RAM:</b> {ram}% | <b>Swap:</b> {swap}%"
                        if svcs != 'N/A': beh_html += f"<br><b>Serviços:</b> {svcs}"
                        if procs != 'N/A': beh_html += f"<br><b>Top Proc:</b> {procs}"
                        beh_html += "</div>"
                            
                        html_content += f"<h3 style='margin-top: 20px; margin-bottom: 5px; border-bottom: 2px solid #ccc; color: #333;'>🖥️ {friendly} ({ip_info})</h3>"
                        html_content += beh_html
                        html_content += "<div class='grid'>"
                        
                        for row in rows:
                            status = row.get('status_alerta', 'NORMAL').upper()
                            if status == "NORMAL":
                                cls = "normal"
                            elif status == "ESTÁVEL":
                                cls = "estável"
                            elif status == "ATENÇÃO":
                                cls = "atenção"
                            elif status == "CRÍTICO":
                                cls = "crítico"
                            else:
                                cls = "inativo"
                                
                            dias_str = ""
                            dias_val = row.get("dias_para_encher", "N/A")
                            if dias_val != "N/A":
                                try:
                                    d = float(dias_val)
                                    if d > 365:
                                        dias_str = f'<div style="font-size:10px; margin-top:4px; color:white; font-weight:bold; background: rgba(0,0,0,0.2); padding: 2px 4px; border-radius: 3px;">Enche em: > 1 ano</div>'
                                    else:
                                        color = "red" if d < 30 and d >= 0 else "white"
                                        dias_str = f'<div style="font-size:10px; margin-top:4px; color:{color}; font-weight:bold; background: rgba(0,0,0,0.2); padding: 2px 4px; border-radius: 3px;">Enche em: {int(d)} dias</div>'
                                except:
                                    pass
                            
                            card_inner = f"""
                            <div style="font-size:13px; margin-bottom:6px; border-bottom:1px solid rgba(255,255,255,0.3); padding-bottom:2px;"><b>{row['particao']}</b></div>
                            <div style="font-size:15px; font-weight:bold; margin:0;">Uso: {row['percentual_uso']}</div>
                            <div style="font-size:10px; opacity:0.9; margin-top:2px;">Livre: {row['espaco_disponivel']}</div>
                            {dias_str}
                            """
                            html_content += f'<div class="card {cls}">{card_inner}</div>'
                        html_content += "</div>"
                        
                    qa_html = f"""
                    <h2 style="margin-top: 30px;">Relatório de Ocorrências</h2>
                    <div class="qa">
                        <p><b>1. QUAIS SERVIDORES APRESENTARAM PROBLEMA?</b><br>{answers['q1']}</p>
                        <p><b>2. QUAIS AS AÇÕES IMEDIATAS?</b><br>{answers['q2']}</p>
                        <p><b>3. QUAIS PONTOS DE ATENÇÃO?</b><br>{answers['q3']}</p>
                        <p><b>4. ALGUMA INFORMAÇÃO ADICIONAL?</b><br>{answers['q4']}</p>
                        <p><b>5. ATIVIDADES PLANEJADAS:</b><br>{answers['q5']}</p>
                    </div>
                    
                    <div class="legend">
                        <b>Legenda:</b>
                        <div class="leg-item"><span class="dot" style="background-color: #2e7d32;"></span> Normal</div>
                        <div class="leg-item"><span class="dot" style="background-color: #81c784;"></span> Estável</div>
                        <div class="leg-item"><span class="dot" style="background-color: #f57f17;"></span> Atenção</div>
                        <div class="leg-item"><span class="dot" style="background-color: #c62828;"></span> Crítico</div>
                        <div class="leg-item"><span class="dot" style="background-color: #607d8b;"></span> Inativo</div>
                    </div>
                    """
                    html_content += qa_html
                    html_content += "</body></html>"
                    return html_content

                html_full = build_html_report(final_data, final_answers, report_type="full")
                html_resum = build_html_report(final_data, final_answers, report_type="resumido")
            
                st.markdown("""
                <style>
                div[data-testid="stDownloadButton"] > button {
                    background-color: #2e7d32 !important;
                    color: white !important;
                    border: none !important;
                }
                div[data-testid="stDownloadButton"] > button:hover {
                    background-color: #1b5e20 !important;
                }
                </style>
                """, unsafe_allow_html=True)
            
                c_down1, c_down2, c_down3 = st.columns(3)
            
                with c_down1:
                    st.download_button(
                        label="📄 Relatório TXT",
                        data=txt_report,
                        file_name=f"relatorio_plantao_{datetime.now().strftime('%Y%m%d')}.txt",
                        mime="text/plain",
                        type="primary",
                        use_container_width=True
                    )
                
                with c_down2:
                    st.download_button(
                        label="🖼️ HTML Completo",
                        data=html_full,
                        file_name=f"relatorio_visual_completo_{datetime.now().strftime('%Y%m%d')}.html",
                        mime="text/html",
                        type="secondary",
                        use_container_width=True
                    )
                    
                with c_down3:
                    st.download_button(
                        label="🖼️ HTML Resumido",
                        data=html_resum,
                        file_name=f"relatorio_visual_resumido_{datetime.now().strftime('%Y%m%d')}.html",
                        mime="text/html",
                        type="secondary",
                        use_container_width=True
                    )

    with tab2:
        st.header("Análise e Histórico de Monitoramento")
    
        from datetime import timedelta
    
        col_hist1, col_hist2 = st.columns([0.8, 0.2])
        if st.session_state["role"] == "admin":
            with col_hist2:
                with st.expander("Configurações Avançadas"):
                    st.warning("Ação irreversível:")
                    if st.button("🗑️ Zerar Histórico CSV", type="primary", use_container_width=True):
                        csv_path = os.path.join(os.path.abspath(os.path.dirname(__file__)), "monitoramento_historico.csv")
                        if os.path.exists(csv_path):
                            os.remove(csv_path)
                        action_logger.info(f"Analista {analista} limpou o histórico CSV.")
                        st.success("Histórico zerado!")
                        st.rerun()

        csv_path = os.path.join(os.path.abspath(os.path.dirname(__file__)), "monitoramento_historico.csv")
        try:
            hist_df = pd.read_csv(csv_path)
        
            if 'percentual_uso' in hist_df.columns:
                hist_df['percentual_num'] = hist_df['percentual_uso'].astype(str).str.replace('%', '').astype(float)
            
            hist_df['timestamp'] = pd.to_datetime(hist_df['timestamp'])
        
            tres_meses_atras = datetime.now() - timedelta(days=90)
            df_3_meses = hist_df[hist_df['timestamp'] >= tres_meses_atras]
        
            st.subheader("Tabela Histórica")
        
            df_display = df_3_meses.drop(columns=['percentual_num'], errors='ignore').copy()
        
            def add_emoji(status):
                if status == 'NORMAL': return '🟢 NORMAL'
                if status == 'ATENÇÃO': return '🟡 ATENÇÃO'
                if status == 'CRÍTICO': return '🔴 CRÍTICO'
                if status == 'ESTÁVEL': return '🔵 ESTÁVEL'
                if status == 'INATIVO': return '⚪ INATIVO'
                return status
            
            if 'status_alerta' in df_display.columns:
                df_display['status_alerta'] = df_display['status_alerta'].apply(add_emoji)
            
            st.dataframe(df_display, use_container_width=True)
        
            st.subheader("Evolução do Uso de Disco (Últimos 3 Meses)")
            if not df_3_meses.empty:
                df_3_meses['data'] = df_3_meses['timestamp'].dt.date
                df_3_meses['chave'] = df_3_meses['servidor'] + " - " + df_3_meses['particao'].str.replace(':', '', regex=False)
                chart_data = df_3_meses.pivot_table(index='data', columns='chave', values='percentual_num', aggfunc='mean')
                st.line_chart(chart_data)
            else:
                st.info("Não há dados suficientes nos últimos 3 meses para gerar o gráfico.")
            
        except FileNotFoundError:
            st.write("Nenhum histórico encontrado ainda. Arquivo 'monitoramento_historico.csv' será criado após o primeiro salvamento.")

except Exception as e:
    error_logger.error("Um erro ocorreu na aplicação.", exc_info=True)
    st.error(f"Ocorreu um erro inesperado. Por favor, verifique os logs. Detalhes: {str(e)}")
