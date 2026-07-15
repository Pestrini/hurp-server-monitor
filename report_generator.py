import os
import pandas as pd
from typing import List, Dict, Any

CSV_FILE = "monitoramento_historico.csv"

def pre_fill_answers(parsed_data: List[Dict[str, Any]]) -> Dict[str, str]:
    servers_problem = set()
    acoes_imediatas = []
    pontos_atencao = []
    
    for row in parsed_data:
        if row["status_alerta"] in ["ATENÇÃO", "CRÍTICO"]:
            servers_problem.add(row["servidor"])
            
            if row["servidor"] == "SHIFT_DB_PRD" and "dados" in row.get("particao", "").lower() and row.get("raw_percent", 0) > 75:
                acoes_imediatas.append("Avaliar expurgos/locks no Caché (SHIFT_DB_PRD /dados).")
                
            if "VIVACE_PACS" in row["servidor"] and ("Z:" in row.get("particao", "") or "C:" in row.get("particao", "")) and row.get("raw_percent", 0) > 85:
                acoes_imediatas.append(f"Limpar imagens temporárias / logs do Vivace (Unidade {row['particao']}).")
                pontos_atencao.append(f"Espaço da unidade {row['particao']} do PACS alto ({row.get('percentual_uso', '')}).")
                
        # Lógica preditiva (Zabbix)
        dias = row.get("dias_para_encher", "N/A")
        if dias != "N/A":
            try:
                if float(dias) <= 30:
                    pontos_atencao.append(f"Disco {row['particao']} do {row['servidor']} vai encher em {dias} dias! Crescimento de {row.get('crescimento_gb_dia', 0)} GB/dia.")
            except:
                pass

    if not servers_problem:
        ans1 = "Nenhum"
        ans2 = "Nenhuma"
        ans3 = "Nenhum"
    else:
        ans1 = ", ".join(servers_problem)
        ans2 = " ".join(acoes_imediatas) if acoes_imediatas else "Verificar partições com alerta."
        ans3 = " ".join(pontos_atencao) if pontos_atencao else "Acompanhar crescimento."
        
    return {
        "q1": ans1,
        "q2": ans2,
        "q3": ans3,
        "q4": "Nenhuma",
        "q5": "Nenhuma"
    }

def generate_txt_report(parsed_data: List[Dict[str, Any]], answers: Dict[str, str], analyst: str, timestamp: str) -> str:
    report = []
    report.append("============================================================")
    report.append("RELATÓRIO DE MONITORAMENTO DE SERVIDORES - TI HURP")
    report.append(f"Data/Hora: {timestamp}")
    report.append(f"Analista Responsável: {analyst}")
    report.append("============================================================\n")
    
    report.append("1. ANÁLISE DE ESPAÇO EM DISCO DAS PARTIÇÕES CRÍTICAS:")
    report.append("------------------------------------------------------------")
    
    for row in parsed_data:
        alert_tag = f" [{row['status_alerta']}]" if row['status_alerta'] not in ["NORMAL", "ESTÁVEL", "INATIVO"] else f" [{row['status_alerta']}]"
        
        srv_name = row['servidor']
        ip = row.get('ip', '')
        zbx = row.get('zabbix_hostname', '')
        if zbx and zbx != "N/A":
            ident_str = f"{ip} - {zbx}"
        else:
            ident_str = f"{ip}"
            
        proj_str = ""
        dias = row.get("dias_para_encher", "N/A")
        crescimento = row.get("crescimento_gb_dia", 0.0)
        
        if dias != "N/A":
            try:
                d = float(dias)
                if d > 365:
                    proj_str = f" ℹ️ Cresce {crescimento} GB/dia, enche em mais de 1 ano."
                elif d < 40 and d > 0:
                    proj_str = f" ⚠️ Cresce {crescimento} GB/dia, enche em {int(d)} dias!"
                elif d == 0:
                    proj_str = f" ⚠️ Cresce {crescimento} GB/dia, enche em 0 dias!"
                elif d > 365 or crescimento <= 0:
                    proj_str = f" ℹ️ Cresce {crescimento} GB/dia, estável."
                else:
                    proj_str = f" ℹ️ Cresce {crescimento} GB/dia, enche em {int(d)} dias."
            except:
                pass
        
        line = f"• {srv_name} ({ident_str}) - Partição {row['particao']}: Uso em {row['percentual_uso']}{alert_tag}{proj_str}"
        report.append(line)
        
    report.append("\n2. RESPOSTAS OBRIGATÓRIAS DO PLANTÃO:")
    report.append("------------------------------------------------------------")
    
    report.append("QUAIS SERVIDORES APRESENTARAM PROBLEMA?")
    report.append(f"R: {answers['q1']}\n")
    
    report.append("QUAIS AS AÇÕES IMEDIATAS?")
    report.append(f"R: {answers['q2']}\n")
    
    report.append("QUAIS PONTOS DE ATENÇÃO?")
    report.append(f"R: {answers['q3']}\n")
    
    report.append("ALGUMA INFORMAÇÃO ADICIONAL?")
    report.append(f"R: {answers['q4']}\n")
    
    report.append("ATIVIDADADES PLANEJADAS (PROXIMOS PASSOS):")
    report.append(f"R: {answers['q5']}\n")
    
    report.append("------------------------------------------------------------")
    report.append("Relatório gerado automaticamente.")
    
    return "\n".join(report)

def save_to_csv(parsed_data: List[Dict[str, Any]]):
    df = pd.DataFrame(parsed_data)
    if 'raw_percent' in df.columns:
        df = df.drop(columns=['raw_percent'])
        
    base_cols = ["timestamp", "servidor", "ip", "so", "particao", "capacidade_total", "espaco_ocupado", "espaco_disponivel", "percentual_uso", "status_alerta"]
    new_cols = []
    if "zabbix_hostname" in df.columns:
        new_cols.append("zabbix_hostname")
    if "crescimento_gb_dia" in df.columns:
        new_cols.append("crescimento_gb_dia")
    if "dias_para_encher" in df.columns:
        new_cols.append("dias_para_encher")
        
    cols = base_cols + new_cols
    
    # Preencher colunas que faltam caso venha do OCR/Manual
    for c in cols:
        if c not in df.columns:
            df[c] = "N/A"
            
    df = df[cols]
    
    csv_path = os.path.join(os.path.abspath(os.path.dirname(__file__)), CSV_FILE)
    write_header = not os.path.exists(csv_path)
    df.to_csv(csv_path, mode='a', header=write_header, index=False)
