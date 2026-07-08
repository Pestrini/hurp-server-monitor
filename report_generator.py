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
            
            # Regras específicas
            if row["servidor"] == "SHIFT_DB_PRD" and "dados" in row["particao"] and row["raw_percent"] > 75:
                acoes_imediatas.append("Avaliar expurgos/locks no Caché (SHIFT_DB_PRD /dados).")
                
            if "VIVACE_PACS" in row["servidor"] and ("Z:" in row["particao"] or "C:" in row["particao"]) and row["raw_percent"] > 85:
                acoes_imediatas.append("Limpar imagens temporárias / logs do Vivace.")
                pontos_atencao.append(f"Espaço da unidade {row['particao']} do PACS crítico ({row['percentual_uso']}).")

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
        alert_tag = f" [{row['status_alerta']}]" if row['status_alerta'] != "NORMAL" else ""
        line = f"• {row['servidor']} ({row['ip']}) - Partição {row['particao']}: Uso em {row['percentual_uso']} ({row['espaco_ocupado']} ocupados de {row['capacidade_total']}){alert_tag}"
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
    report.append("Relatório gerado automaticamente via Engine de Parser de Monitoramento.")
    
    return "\n".join(report)

def save_to_csv(parsed_data: List[Dict[str, Any]]):
    df = pd.DataFrame(parsed_data)
    # Remove colunas auxiliares que não vão para o CSV
    if 'raw_percent' in df.columns:
        df = df.drop(columns=['raw_percent'])
        
    # Reordenar de acordo com o modelo
    cols = ["timestamp", "servidor", "ip", "so", "particao", "capacidade_total", "espaco_ocupado", "espaco_disponivel", "percentual_uso", "status_alerta"]
    df = df[cols]
    
    write_header = not os.path.exists(CSV_FILE)
    df.to_csv(CSV_FILE, mode='a', header=write_header, index=False)
