import re
import pandas as pd
from typing import List, Dict, Any, Optional
from datetime import datetime

# Mapeamento de Servidores
SERVERS = {
    "SHIFT_DB_PRD": {
        "ip": "192.168.1.1",
        "so": "Linux",
        "hostname": "SERVER-01",
        "identifiers": ["192.168.1.1", "rhel-dados", "rhel-root", "rhel-binario", "rhel-backup", "rhel-tmp", "rhel-journal"]
    },
    "SHIFT_SHADOW": {
         "ip": "192.168.1.2",
         "so": "Linux",
         "hostname": "SERVER-02",
         "identifiers": ["192.168.1.2"]
    },
    "SHIFT_AUTOMACAO": {
        "ip": "192.168.1.3",
        "so": "Windows",
        "hostname": "SERVER-03",
        "identifiers": ["192.168.1.3", "C:", "D:"]
    },
    "SHIFT_WEB": {
        "ip": "192.168.1.4",
        "so": "Linux",
        "hostname": "SERVER-04",
        "identifiers": ["192.168.1.4"]
    },
    "VIVACE_PACS_01": {
        "ip": "192.168.1.5",
        "so": "Windows",
        "hostname": "SERVER-05",
        "identifiers": ["192.168.1.5", "PACS01", "PACS02", "TEMPORARIO"]
    },
    "VIVACE_PACS_02": {
        "ip": "192.168.1.6",
        "so": "Windows",
        "hostname": "SERVER-06",
        "identifiers": ["192.168.1.6"]
    },
    "VIVACE_PACS_WEB": {
        "ip": "192.168.1.7",
        "so": "Windows",
        "hostname": "SERVER-07",
        "identifiers": ["192.168.1.7"]
    },
    "MV_PRODUCAO_02": {
        "ip": "192.168.1.8",
        "so": "Linux",
        "hostname": "SERVER-08",
        "identifiers": ["192.168.1.8"]
    },
    "MV_PRODUCAO_01": {
        "ip": "192.168.1.9",
        "so": "Windows",
        "hostname": "SERVER-09",
        "identifiers": ["192.168.1.9"]
    },
    "MV_BALANCE": {
        "ip": "192.168.1.10",
        "so": "Linux",
        "hostname": "SERVER-10",
        "identifiers": ["192.168.1.10", "vg_root-LogVol00", "vg_mv-LogVol00", "vg_hvmmvbalance0"]
    },
    "HINNO_APP": {
        "ip": "192.168.1.11",
        "so": "Linux",
        "hostname": "SERVER-11",
        "identifiers": ["192.168.1.11", "ubuntu--vg"]
    },
    "GREEN": {
        "ip": "192.168.1.12",
        "so": "Linux",
        "hostname": "SERVER-12",
        "identifiers": ["192.168.1.12", "vmmvgreen-root"]
    }
}

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
    """Faz o parse do output de df -h do linux"""
    raw_lines = text.strip().split('\n')
    lines = []
    i = 0
    while i < len(raw_lines):
        line = raw_lines[i].strip()
        if not line:
            i += 1
            continue
        parts = re.split(r'\s+', line)
        if len(parts) == 1 and i + 1 < len(raw_lines):
            # Broken line, merge with next
            line = line + " " + raw_lines[i+1].strip()
            i += 1
        lines.append(line)
        i += 1
        
    results = []
    
    if not server_name:
        server_name = identify_server_from_text(text)
        
    server_info = SERVERS.get(server_name, {"ip": "Desconhecido", "so": "Linux"})
    
    for line in lines:
        if ("Caption" in line and "Size" in text) or "DeviceId" in line or "--------" in line:
            # Pula cabeçalho do wmic e PowerShell
            continue
            
        parts = re.split(r'\s+', line.strip())
        if len(parts) >= 6 and "dev/mapper" in line or "%" in line: # Standard df -h format
            # Ex: /dev/mapper/rhel-dados 855G 693G 163G 81% /dados
            particao = parts[-1]
            capacidade = parts[1]
            ocupado = parts[2]
            disponivel = parts[3]
            perc_str = parts[4].replace('%', '')
            try:
                perc = float(perc_str)
            except ValueError:
                perc = 0.0
                
        elif len(parts) >= 3 and parts[0].endswith(':'): # Formato wmic e PowerShell (Caption/DeviceId, [VolumeName], FreeSpace, Size)
            # Ex: C:       Windows  45749219328   213645012992
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
            
        elif len(parts) == 3 or len(parts) == 4: # Format from PDF table (Partition, Used, Available)
            # Ex: /dev/mapper/rhel-dados (/dados) 693G 163G
            # or: /dev/mapper/rhel-root em / 11G 73G
            # This requires custom parsing since capacity and % are missing.
            # We'll calculate them.
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
                
            # Function to convert G/M/K/T to bytes for calculation
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
            "raw_percent": perc
        })
        
    return results
