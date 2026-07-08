import streamlit as st
import pandas as pd
from datetime import datetime
from parser_engine import parse_df_h_output, process_image_ocr
from report_generator import pre_fill_answers, generate_txt_report, save_to_csv

import os

st.set_page_config(page_title="HURP Server Monitor", layout="wide")

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

st.sidebar.title("Configurações")
analista = st.sidebar.selectbox("Analista de Plantão", ["Gabriel Pestrini", "Adalberto Filho", "Djalma Santos"])

st.sidebar.markdown("---")
with st.sidebar.expander("📖 Passo a Passo & Comandos", expanded=True):
    st.markdown("""
    **1. Servidores Linux**
    - Acesse o servidor via PuTTY ou SSH.
    - Execute o comando: `df -h`
    - Copie a saída e cole na caixa de texto.

    **2. Servidores Windows**
    - Abra o **PowerShell** (não o Prompt de Comando antigo).
    - Execute o comando:
      `Get-CimInstance Win32_LogicalDisk | Where-Object DriveType -eq 3 | Select-Object DeviceId, FreeSpace, Size`
    - Copie o texto e cole na **mesma** caixa de texto da esquerda.
    - Selecione manualmente o Servidor no dropdown (ex: VIVACE_PACS_01).

    **3. Imagens (Opcional)**
    - Se usar prints do Windows Explorer, altere a exibição da pasta para **"Detalhes"**.
    - Faça o upload na área da direita.

    **4. Consolidando**
    - Revise a tabela gerada e ajuste os Status se necessário.
    - Revise as respostas do Assistente de IA.
    - Clique em **Salvar e Consolidar**!
    """)

with st.sidebar.expander("🖥️ Lista de Servidores", expanded=False):
    st.markdown("""
    | Servidor | SO | IP |
    |---|---|---|
    | **SHIFT_DB_PRD** | Linux | `192.168.1.1` |
    | **SHIFT_SHADOW** | Linux | `192.168.1.2` |
    | **SHIFT_AUTOMACAO** | Windows | `192.168.1.3` |
    | **SHIFT_WEB** | Linux | `192.168.1.4` |
    | **VIVACE_PACS_01** | Windows | `192.168.1.5` |
    | **VIVACE_PACS_02** | Windows | `192.168.1.6` |
    | **VIVACE_PACS_WEB** | Windows | `192.168.1.7` |
    | **MV_PRODUCAO_02** | Linux | `192.168.1.8` |
    | **MV_PRODUCAO_01** | Windows | `192.168.1.9` |
    | **MV_BALANCE** | Linux | `192.168.1.10` |
    | **HINNO_APP** | Linux | `192.168.1.11` |
    | **GREEN** | Linux | `192.168.1.12` |
    """)

st.title("HURP Server Monitor: Clipboard-to-Report")

tab1, tab2 = st.tabs(["Entrada de Dados (Cole os Logs/Imagens)", "Histórico de Monitoramento (Métricas de BI)"])

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
            
        server_txt = st.selectbox("Servidor (Opcional - força um servidor)", ["Automático"] + list(SERVERS.keys()), key="srv_txt")
        text_input = st.text_area("Cole aqui o output do 'df -h' (Linux) ou PowerShell (Windows)", height=250, key="raw_text")
        
        c_btn1, c_btn2 = st.columns(2)
        with c_btn1:
            if st.button("Processar Texto", use_container_width=True):
                if text_input:
                    srv_param = None if server_txt == "Automático" else server_txt
                    new_data = parse_df_h_output(text_input, server_name=srv_param)
                    st.session_state["parsed_data"].extend(new_data)
                    st.success("Texto processado!")
        with c_btn2:
            st.button("Limpar Campos", on_click=clear_inputs, use_container_width=True)
                
    with col2:
        from parser_engine import SERVERS
        server_img = st.selectbox("Servidor (Opcional - força um servidor)", ["Automático"] + list(SERVERS.keys()), key="srv_img")
        img_input = st.file_uploader("Upload / Cole a imagem das partições", type=['png', 'jpg', 'jpeg'])
        
        if img_input:
            st.image(img_input, caption="Imagem Carregada", use_container_width=True)
            if st.button("Processar Imagem (OCR)"):
                srv_param = None if server_img == "Automático" else server_img
                new_data = process_image_ocr(img_input, server_name=srv_param)
                st.session_state["parsed_data"].extend(new_data)
                st.success("Imagem processada!")

    if st.session_state["parsed_data"]:
        col_title, col_btn = st.columns([0.8, 0.2])
        with col_title:
            st.subheader("Dados Extraídos (Edite se necessário)")
        with col_btn:
            if st.button("Limpar Área", type="secondary", use_container_width=True):
                st.session_state["parsed_data"] = []
                st.rerun()
        
        # Criação de um editor de dataframe no Streamlit
        df = pd.DataFrame(st.session_state["parsed_data"])
        
        edited_df = st.data_editor(
            df,
            num_rows="dynamic",
            column_config={
                "status_alerta": st.column_config.SelectboxColumn(
                    "Status",
                    help="Status do disco",
                    options=["NORMAL", "ATENÇÃO", "CRÍTICO"],
                    required=True
                )
            },
            hide_index=True
        )
        
        # IA preenche perguntas
        st.subheader("Assistente de IA - Respostas do Plantão")
        answers = pre_fill_answers(edited_df.to_dict('records'))
        
        q1 = st.text_area("1. QUAIS SERVIDORES APRESENTARAM PROBLEMA?", value=answers["q1"])
        q2 = st.text_area("2. QUAIS AS AÇÕES IMEDIATAS?", value=answers["q2"])
        q3 = st.text_area("3. QUAIS PONTOS DE ATENÇÃO?", value=answers["q3"])
        q4 = st.text_area("4. ALGUMA INFORMAÇÃO ADICIONAL?", value=answers["q4"])
        q5 = st.text_area("5. ATIVIDADES PLANEJADAS (PROXIMOS PASSOS):", value=answers["q5"])
        
        final_answers = {"q1": q1, "q2": q2, "q3": q3, "q4": q4, "q5": q5}
        
        if st.button("Salvar e Consolidar", type="primary"):
            final_data = edited_df.to_dict('records')
            
            # 1. Salvar no CSV
            save_to_csv(final_data)
            st.success("Dados salvos em monitoramento_historico.csv com sucesso!")
            
            # 2. Gerar dados do relatório e salvar no Session State
            ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            st.session_state["generated_txt_report"] = generate_txt_report(final_data, final_answers, analista, ts)
            st.session_state["final_data"] = final_data
            st.session_state["final_answers"] = final_answers
            st.session_state["report_ts"] = ts
            st.session_state["analista_sessao"] = analista

        # Exibir o Relatório caso exista no Session State (isso evita que ele suma ao clicar em Download)
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
            st.subheader("Relatório Visual (Planilha Gráfica)")
            
            FRIENDLY_NAMES = {
                "SHIFT_DB_PRD": "SHIFT PRODUÇÃO",
                "SHIFT_SHADOW": "SHIFT SHADOW",
                "VIVACE_PACS_01": "VIVACE PACS 01",
                "VIVACE_PACS_02": "VIVACE PACS 02",
                "VIVACE_PACS_WEB": "VIVACE PACS WEB",
                "SHIFT_AUTOMACAO": "SHIFT AUTO",
                "SHIFT_WEB": "WEB SERVER",
                "MV_PRODUCAO_01": "MV PRODUÇÃO",
                "MV_PRODUCAO_02": "MV TOMCAT",
                "MV_BALANCE": "MV BALANCE",
                "HINNO_APP": "HINNO APP",
                "GREEN": "GREEN"
            }
            
            weekday_map = {0: "Segunda-feira", 1: "Terça-feira", 2: "Quarta-feira", 3: "Quinta-feira", 4: "Sexta-feira", 5: "Sábado", 6: "Domingo"}
            weekday_str = weekday_map[datetime.now().weekday()]
            
            html_content = f"""
            <html><head><style>
            body {{ font-family: Arial, sans-serif; }}
            @media print {{
                body {{
                    -webkit-print-color-adjust: exact !important;
                    print-color-adjust: exact !important;
                }}
            }}
            .grid {{ display: flex; flex-wrap: wrap; gap: 10px; }}
            .card {{ width: 180px; padding: 10px; border-radius: 8px; color: white; box-shadow: 1px 1px 3px rgba(0,0,0,0.3); }}
            .card h4 {{ margin: 0 0 5px 0; font-size: 14px; border-bottom: 1px solid rgba(255,255,255,0.3); padding-bottom: 3px; }}
            .card .part {{ font-size: 12px; margin-bottom: 5px; }}
            .card .uso {{ font-size: 18px; font-weight: bold; margin: 0; }}
            .card .livre {{ font-size: 11px; opacity: 0.9; margin-top: 3px; }}
            .normal {{ background-color: #2e7d32 !important; }}
            .atencao {{ background-color: #f57f17 !important; }}
            .critico {{ background-color: #c62828 !important; }}
            .qa {{ background-color: #f4f4f4 !important; padding: 15px; border-left: 5px solid #1976d2 !important; margin-bottom: 20px; }}
            .header-visual {{ background-color: #1976d2 !important; color: white !important; padding: 20px; border-radius: 8px; margin-bottom: 20px; text-align: center; }}
            </style></head><body>
            <div class="header-visual">
                <h1 style="margin: 0;">Relatório de Monitoramento de Servidores</h1>
                <p style="margin: 5px 0 0 0; font-size: 16px;">Analista Responsável: <b>{analista_str}</b> | Data: <b>{ts} ({weekday_str})</b></p>
            </div>
            <h2>Status dos Discos e Servidores</h2>
            """
            
            # Agrupar dados por servidor
            grouped_data = {}
            for row in final_data:
                serv = row['servidor']
                if serv not in grouped_data:
                    grouped_data[serv] = []
                grouped_data[serv].append(row)
                
            # Gerar a interface separada por servidor
            for serv, rows in grouped_data.items():
                friendly = FRIENDLY_NAMES.get(serv, serv)
                
                # HTML Exportado: Título do Servidor + Abre Grid
                html_content += f"<h3 style='margin-top: 20px; margin-bottom: 10px; border-bottom: 2px solid #ccc; color: #333;'>🖥️ {friendly}</h3><div class='grid'>"
                
                # Streamlit: Título do Servidor + Abre Colunas
                st.markdown(f"<h4 style='margin-top: 15px; border-bottom: 1px solid #ddd; padding-bottom: 5px;'>🖥️ {friendly}</h4>", unsafe_allow_html=True)
                cols = st.columns(4)
                
                for i, row in enumerate(rows):
                    if row['status_alerta'] == "NORMAL":
                        cls, bg_color = "normal", "#2e7d32"
                    elif row['status_alerta'] == "ATENÇÃO":
                        cls, bg_color = "atencao", "#f57f17"
                    else:
                        cls, bg_color = "critico", "#c62828"
                    
                    # O card agora não precisa repetir o nome do servidor em destaque gigante, pois já está agrupado
                    # Mas vamos manter sutilmente
                    card_inner = f"""
                    <div style="font-size:14px; margin-bottom:8px; border-bottom:1px solid rgba(255,255,255,0.3); padding-bottom:3px;"><b>{row['particao']}</b></div>
                    <div style="font-size:18px; font-weight:bold; margin:0;">Uso: {row['percentual_uso']}</div>
                    <div style="font-size:11px; opacity:0.9; margin-top:3px;">Livre: {row['espaco_disponivel']}</div>
                    """
                    
                    # Para o Streamlit
                    cols[i % 4].markdown(f'<div style="background-color:{bg_color}; padding:10px; border-radius:8px; color:white; margin-bottom:10px; box-shadow: 1px 1px 3px rgba(0,0,0,0.3);">{card_inner}</div>', unsafe_allow_html=True)
                    
                    # Para o Arquivo HTML Exportado
                    html_content += f'<div class="card {cls}">{card_inner}</div>'
                    
                # Fecha o grid do servidor atual no HTML
                html_content += "</div>"
                
            # Adicionar Perguntas e Respostas APENAS ao HTML Exportado
            qa_html = f"""
            <h2 style="margin-top: 30px;">Relatório de Ocorrências</h2>
            <div class="qa">
                <p><b>1. QUAIS SERVIDORES APRESENTARAM PROBLEMA?</b><br>{final_answers['q1']}</p>
                <p><b>2. QUAIS AS AÇÕES IMEDIATAS?</b><br>{final_answers['q2']}</p>
                <p><b>3. QUAIS PONTOS DE ATENÇÃO?</b><br>{final_answers['q3']}</p>
                <p><b>4. ALGUMA INFORMAÇÃO ADICIONAL?</b><br>{final_answers['q4']}</p>
                <p><b>5. ATIVIDADES PLANEJADAS:</b><br>{final_answers['q5']}</p>
            </div>
            """
            html_content += qa_html
            
            html_content += "</body></html>"
            
            st.markdown("### Downloads Disponíveis")
            
            # Injetar CSS para forçar os botões de download a ficarem verdes no Streamlit
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
            
            c_down1, c_down2 = st.columns(2)
            
            with c_down1:
                st.download_button(
                    label="📄 Baixar Relatório TXT",
                    data=txt_report,
                    file_name=f"relatorio_plantao_{datetime.now().strftime('%Y%m%d')}.txt",
                    mime="text/plain",
                    type="primary",
                    use_container_width=True
                )
                
            with c_down2:
                st.download_button(
                    label="🖼️ Baixar Relatório Visual HTML (Salvar como PDF)",
                    data=html_content,
                    file_name=f"relatorio_visual_{datetime.now().strftime('%Y%m%d')}.html",
                    mime="text/html",
                    type="secondary",
                    use_container_width=True
                )
            
            
            # Limpar sessão se quiser (Opcional, comentando para manter caso queira re-editar)
            # st.session_state["parsed_data"] = []

with tab2:
    st.header("Análise e Histórico de Monitoramento")
    
    import os
    from datetime import timedelta
    
    col_hist1, col_hist2 = st.columns([0.8, 0.2])
    with col_hist2:
        with st.expander("Configurações Avançadas"):
            st.warning("Ação irreversível:")
            if st.button("🗑️ Zerar Histórico CSV", type="primary", use_container_width=True):
                if os.path.exists("monitoramento_historico.csv"):
                    os.remove("monitoramento_historico.csv")
                st.success("Histórico zerado!")
                st.rerun()

    try:
        hist_df = pd.read_csv("monitoramento_historico.csv")
        
        # Converter string de percentual ("81%") para numérico para o gráfico
        if 'percentual_uso' in hist_df.columns:
            hist_df['percentual_num'] = hist_df['percentual_uso'].str.replace('%', '').astype(float)
            
        hist_df['timestamp'] = pd.to_datetime(hist_df['timestamp'])
        
        # Filtrar últimos 3 meses
        tres_meses_atras = datetime.now() - timedelta(days=90)
        df_3_meses = hist_df[hist_df['timestamp'] >= tres_meses_atras]
        
        st.subheader("Tabela Histórica")
        
        # Adicionar ícones visuais ao invés de colorir o fundo (evita erro do Jinja2 no Pandas)
        df_display = df_3_meses.drop(columns=['percentual_num'], errors='ignore').copy()
        
        def add_emoji(status):
            if status == 'NORMAL': return '🟢 NORMAL'
            if status == 'ATENÇÃO': return '🟡 ATENÇÃO'
            if status == 'CRÍTICO': return '🔴 CRÍTICO'
            return status
            
        if 'status_alerta' in df_display.columns:
            df_display['status_alerta'] = df_display['status_alerta'].apply(add_emoji)
            
        st.dataframe(df_display, use_container_width=True)
        
        st.subheader("Evolução do Uso de Disco (Últimos 3 Meses)")
        if not df_3_meses.empty:
            # Extrair apenas a data (sem a hora) para agrupar por dia
            df_3_meses['data'] = df_3_meses['timestamp'].dt.date
            
            # Preparar dados para o gráfico de linhas (pivot table)
            df_3_meses['chave'] = df_3_meses['servidor'] + " - " + df_3_meses['particao']
            chart_data = df_3_meses.pivot_table(index='data', columns='chave', values='percentual_num', aggfunc='mean')
            
            st.line_chart(chart_data)
        else:
            st.info("Não há dados suficientes nos últimos 3 meses para gerar o gráfico.")
            
    except FileNotFoundError:
        st.write("Nenhum histórico encontrado ainda. Arquivo 'monitoramento_historico.csv' será criado após o primeiro salvamento.")
