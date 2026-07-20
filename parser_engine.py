import re
import pandas as pd
from typing import List, Dict, Any, Optional
from datetime import datetime

import json
import os

def load_servers():
    config_path = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'servers.json')
    if os.path.exists(config_path):
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"Erro ao ler servers.json: {e}")
            
    # Cria template caso não exista
    dummy = {
        "DUMMY_SERVER": {
            "ip": "127.0.0.1",
            "so": "Linux",
            "hostname": "localhost",
            "identifiers": ["127.0.0.1"]
        }
    }
    try:
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(dummy, f, indent=4)
    except Exception as e:
        print(f"Erro ao criar servers.json: {e}")
    return dummy

SERVERS = load_servers()

def determine_status(percentual: float) -> str:
    if percentual < 75.0:
        return "NORMAL"
    elif percentual <= 85.0:
        return "ATENÇÃO"
    else:
        return "CRÍTICO"

def identify_server_from_text(text: str) -> Optional[str]:
    # Tenta achar IP no texto
    ip_match = re.search(r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b', text)
    if ip_match:
        ip = ip_match.group(0)
        for srv, info in SERVERS.items():
            if info["ip"] == ip:
                return srv
                
    # Procura por LVMs ou identificadores específicos
    for srv, info in SERVERS.items():
        for identifier in info["identifiers"]:
            if identifier in text:
                return srv
    return None

def parse_df_h_output(text: str, server_name: str = None) -> List[Dict[str, Any]]:
    """Faz o parse do output de df -h ou comando unificado"""
    lines = [line.strip() for line in text.strip().split('\n')]
    
    sections = {"HOST": "", "DISK": [], "MEM_SWAP": [], "TOP_CPU": [], "SERVICES": [], "CPU_PERCENT": []}
    current_section = "DISK" # default if missing
    
    i = 0
    while i < len(lines):
        line = lines[i]
        if not line:
            i += 1; continue
            
        if line.startswith("HOST:"):
            sections["HOST"] = line.replace("HOST:", "").strip()
        elif line == "---DISK---":
            current_section = "DISK"
        elif line == "---MEM_SWAP---":
            current_section = "MEM_SWAP"
        elif line == "---TOP_CPU---":
            current_section = "TOP_CPU"
        elif line == "---SERVICES---":
            current_section = "SERVICES"
        elif line == "---CPU_PERCENT---":
            current_section = "CPU_PERCENT"
        elif line.startswith("===HURP"):
            pass
        elif current_section:
            if current_section == "DISK":
                parts = re.split(r'\s+', line)
                if len(parts) == 1 and i + 1 < len(lines) and not lines[i+1].startswith("---"):
                    line = line + " " + lines[i+1].strip()
                    i += 1
                if line: sections[current_section].append(line)
            else:
                sections[current_section].append(line)
        i += 1
        
    results = []
    
    if not server_name:
        if sections["HOST"]:
            server_name = identify_server_from_text(sections["HOST"])
        if not server_name:
            server_name = identify_server_from_text(text)
        
    server_info = SERVERS.get(server_name, {"ip": "Desconhecido", "so": "Linux"})
    
    # Processa Discos
    for line in sections["DISK"]:
        if ("Caption" in line and "Size" in text) or "DeviceId" in line or "--------" in line:
            continue
            
        parts = re.split(r'\s+', line.strip())
        if len(parts) >= 6 and "dev/mapper" in line or "%" in line:
            particao = parts[-1]
            capacidade = parts[1]
            ocupado = parts[2]
            disponivel = parts[3]
            perc_str = parts[4].replace('%', '')
            try:
                perc = float(perc_str)
            except ValueError:
                perc = 0.0
                
        elif len(parts) >= 3 and parts[0].endswith(':'):
            particao = parts[0]
            volume_parts = parts[1:-2]
            if volume_parts:
                nome_volume = " ".join(volume_parts)
                particao = f"{particao} ({nome_volume})"
            else:
                if server_name in ["VIVACE_PACS_02", "VIVACE_PACS_WEB"] and particao == "C:":
                    particao = "C: (OS)"
            
            try:
                free_bytes = float(parts[-2])
                total_bytes = float(parts[-1])
            except ValueError:
                continue
                
            free_gb = free_bytes / (1024**3)
            total_gb = total_bytes / (1024**3)
            ocupado_gb = total_gb - free_gb
            
            capacidade = f"{total_gb:.1f} GB"
            ocupado = f"{ocupado_gb:.1f} GB"
            disponivel = f"{free_gb:.1f} GB"
            perc = (ocupado_gb / total_gb * 100) if total_gb > 0 else 0.0
            
        elif len(parts) == 3 or len(parts) == 4:
            particao = parts[0]
            if "(" in parts[1]:
                particao = parts[1].strip("()")
                ocupado = parts[2]
                disponivel = parts[3]
            elif "em" in parts[1]:
                particao = parts[2]
                ocupado = parts[3]
                disponivel = parts[4]
            else:
                ocupado = parts[1]
                disponivel = parts[2]
                
            def to_gb(val_str):
                val_str = val_str.replace(',', '.')
                num = re.findall(r'[\d\.]+', val_str)
                if not num: return 0.0
                num = float(num[0])
                if 'T' in val_str: return num * 1024
                if 'G' in val_str: return num
                if 'M' in val_str: return num / 1024
                if 'K' in val_str: return num / (1024*1024)
                return num
                
            oc_gb = to_gb(ocupado)
            dis_gb = to_gb(disponivel)
            cap_gb = oc_gb + dis_gb
            
            capacidade = f"{cap_gb:.1f}G"
            perc = (oc_gb / cap_gb * 100) if cap_gb > 0 else 0.0
            
        else:
            continue
            
        status = determine_status(perc)
        
        results.append({
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "servidor": server_name or "Desconhecido",
            "ip": server_info["ip"],
            "zabbix_hostname": server_info.get("hostname", "N/A"),
            "so": server_info["so"],
            "particao": particao,
            "capacidade_total": capacidade,
            "espaco_ocupado": ocupado,
            "espaco_disponivel": disponivel,
            "percentual_uso": f"{int(perc)}%",
            "status_alerta": status,
            "raw_percent": perc,
            "cpu_percent": "N/A",
            "ram_percent": "N/A",
            "swap_percent": "N/A",
            "servicos_status": "N/A",
            "processos_top": "N/A"
        })
        
    # Processa Memoria, CPU e Servicos (mesmo se nao houver particoes)
    if sections["MEM_SWAP"] or sections["TOP_CPU"] or sections["SERVICES"] or sections["CPU_PERCENT"]:
        # Valores globais
        ram_perc = "N/A"
        swap_perc = "N/A"
        cpu_perc_global = "N/A"
        top_procs = []
        svc_stats = []
        
        # CPU PERCENT GLOBAL
        for line in sections["CPU_PERCENT"]:
            if server_info["so"] == "Linux" and "Cpu(s)" in line:
                m = re.search(r'(\d+\.\d+)\s+id', line)
                if m:
                    cpu_perc_global = round(100.0 - float(m.group(1)), 1)
            elif server_info["so"] == "Windows":
                try:
                    cpu_perc_global = round(float(line.strip()), 1)
                except ValueError:
                    pass

        
        # MEM
        if server_info["so"] == "Linux":
            for line in sections["MEM_SWAP"]:
                if line.startswith("Mem:"):
                    p = re.split(r'\s+', line)
                    if len(p) >= 4:
                        tot, us = float(p[1]), float(p[2])
                        if tot > 0: ram_perc = round((us/tot)*100, 1)
                elif line.startswith("Swap:"):
                    p = re.split(r'\s+', line)
                    if len(p) >= 4:
                        tot, us = float(p[1]), float(p[2])
                        if tot > 0: swap_perc = round((us/tot)*100, 1)
        else: # Windows
            mem_data = {}
            for line in sections["MEM_SWAP"]:
                if ":" in line:
                    k, v = line.split(":", 1)
                    try:
                        mem_data[k.strip()] = float(v.strip())
                    except: pass
            if "TotalVisibleMemorySize" in mem_data and "FreePhysicalMemory" in mem_data:
                tot = mem_data["TotalVisibleMemorySize"]
                free = mem_data["FreePhysicalMemory"]
                if tot > 0: ram_perc = round(((tot-free)/tot)*100, 1)
            if "TotalVirtualMemorySize" in mem_data and "FreeVirtualMemory" in mem_data:
                tot = mem_data["TotalVirtualMemorySize"]
                free = mem_data["FreeVirtualMemory"]
                if tot > 0: swap_perc = round(((tot-free)/tot)*100, 1)
                
        # CPU
        for line in sections["TOP_CPU"]:
            if not line or "CPU" in line or "WorkingSet" in line or "Name" in line: continue
            parts = re.split(r'\s+', line.strip())
            if server_info["so"] == "Linux" and len(parts) >= 3:
                top_procs.append(f"{parts[-1]} ({parts[0]}%)")
            elif server_info["so"] == "Windows" and len(parts) >= 2:
                cpu = parts[-2]
                name = " ".join(parts[:-2])
                top_procs.append(f"{name} ({cpu}%)")
                
        # Services
        for line in sections["SERVICES"]:
            if not line or "Status" in line or "Name" in line or "----" in line: continue
            if ":" in line: # Linux
                svc, st = line.split(":", 1)
                if st.strip() != "not_installed":
                    svc_stats.append(f"{svc.strip()} ({st.strip()})")
            else: # Windows
                parts = re.split(r'\s{2,}', line.strip())
                if len(parts) == 1:
                    parts = re.split(r'\s+', line.strip())
                if len(parts) >= 2:
                    svc_stats.append(f"{parts[0].strip()} ({parts[1].strip()})")
                    
        # Se nao houver particoes lidas, crie uma linha METRICS_ONLY
        if not results:
            results.append({
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "servidor": server_name or "Desconhecido",
                "ip": server_info["ip"],
                "zabbix_hostname": server_info.get("hostname", "N/A"),
                "so": server_info["so"],
                "particao": "METRICS_ONLY",
                "capacidade_total": "N/A",
                "espaco_ocupado": "N/A",
                "espaco_disponivel": "N/A",
                "percentual_uso": "N/A",
                "status_alerta": "NORMAL",
                "raw_percent": 0.0,
                "cpu_percent": "N/A",
                "ram_percent": "N/A",
                "swap_percent": "N/A",
                "servicos_status": "N/A",
                "processos_top": "N/A"
            })
                    
        # Apply to all disks of this server
        for r in results:
            r["ram_percent"] = ram_perc
            r["swap_percent"] = swap_perc
            if cpu_perc_global != "N/A": r["cpu_percent"] = cpu_perc_global
            if top_procs: r["processos_top"] = " | ".join(top_procs[:3])
            if svc_stats: r["servicos_status"] = " | ".join(svc_stats)
            
    return results
