import re
import pandas as pd
from typing import List, Dict, Any, Optional
from datetime import datetime
try:
    import pytesseract
    from PIL import Image
    import io
    
    # Configurar caminho do executável do Tesseract para Windows
    pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
except ImportError:
    pass # Lidar com a falta de biblioteca OCR se necessário

# Mapeamento de Servidores baseado no PDF
SERVERS = {
    "SHIFT_DB_PRD": {
        "ip": "192.168.1.1",
        "so": "Linux",
        "identifiers": ["192.168.1.1", "rhel-dados", "rhel-root", "rhel-binario", "rhel-backup", "rhel-tmp", "rhel-journal"]
    },
    "SHIFT_SHADOW": {
         "ip": "192.168.1.2",
         "so": "Linux",
         "identifiers": ["192.168.1.2"]
    },
    "SHIFT_AUTOMACAO": {
        "ip": "192.168.1.3",
        "so": "Windows",
        "identifiers": ["192.168.1.3", "C:", "D:"]
    },
    "SHIFT_WEB": {
        "ip": "192.168.1.4",
        "so": "Linux",
        "identifiers": ["192.168.1.4"]
    },
    "VIVACE_PACS_01": {
        "ip": "192.168.1.5",
        "so": "Windows",
        "identifiers": ["192.168.1.5", "PACS01", "PACS02", "TEMPORARIO"]
    },
    "VIVACE_PACS_02": {
        "ip": "192.168.1.6",
        "so": "Windows",
        "identifiers": ["192.168.1.6"]
    },
    "VIVACE_PACS_WEB": {
        "ip": "192.168.1.7",
        "so": "Windows",
        "identifiers": ["192.168.1.7"]
    },
    "MV_PRODUCAO_02": {
        "ip": "192.168.1.8",
        "so": "Linux",
        "identifiers": ["192.168.1.8"]
    },
    "MV_PRODUCAO_01": {
        "ip": "192.168.1.9",
        "so": "Windows",
        "identifiers": ["192.168.1.9"]
    },
    "MV_BALANCE": {
        "ip": "192.168.1.10",
        "so": "Linux",
        "identifiers": ["192.168.1.10", "vg_root-LogVol00", "vg_mv-LogVol00", "vg_hvmmvbalance0"]
    },
    "HINNO_APP": {
        "ip": "192.168.1.11",
        "so": "Linux",
        "identifiers": ["192.168.1.11", "ubuntu--vg"]
    },
    "GREEN": {
        "ip": "192.168.1.12",
        "so": "Linux",
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
    lines = text.strip().split('\n')
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
                
        elif len(parts) == 3 and parts[0].endswith(':'): # Formato wmic e PowerShell (Caption/DeviceId, FreeSpace, Size)
            # Ex: C:       45749219328   213645012992
            particao = parts[0]
            try:
                free_bytes = float(parts[1])
                total_bytes = float(parts[2])
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

def process_image_ocr(image_file, server_name: str = None) -> List[Dict[str, Any]]:
    """Processa uma imagem do Windows Explorer com PyTesseract"""
    try:
        img = Image.open(image_file)
        # Custom config for better number/drive letter reading
        custom_config = r'--oem 3 --psm 6' 
        text = pytesseract.image_to_string(img, config=custom_config)
        
        # Simple parsing for Windows Disk space
        results = []
        if not server_name:
             server_name = identify_server_from_text(text)
             if not server_name:
                 server_name = "VIVACE_PACS_01"
                 
        server_info = SERVERS.get(server_name, {"ip": "Desconhecido", "so": "Windows"})
        
        # O tesseract pode ler a imagem linha a linha. Vamos tentar as duas abordagens.
        lines = text.split('\n')
        
        for line in lines:
            line = line.strip()
            if not line: continue
            
            # Padrão 1: "Local Disk (C:) 42.8 GB free of 199 GB"
            pattern1 = r'\(?([A-Z]:)\)?\s*([\d\.,]+)\s*([KMGT]B)\s*[fF]ree\s*[oO]f\s*([\d\.,]+)\s*([KMGT]B)'
            m1 = re.search(pattern1, line, re.IGNORECASE)
            
            # Padrão 2: "Local Disk (C:) Local Disk 199 GB 42.6 GB" (Visualização Detalhes)
            # Extrai: Letra, Total Num, Total Unit, Free Num, Free Unit
            pattern2 = r'\(?([A-Z]:)\)?.*?([\d\.,]+)\s*([KMGT]B).*?([\d\.,]+)\s*([KMGT]B)'
            m2 = re.search(pattern2, line, re.IGNORECASE)
            
            particao = free_val = free_unit = total_val = total_unit = None
            
            if m1:
                particao = m1.group(1)
                free_val = m1.group(2).replace(',', '.')
                free_unit = m1.group(3).upper()
                total_val = m1.group(4).replace(',', '.')
                total_unit = m1.group(5).upper()
            elif m2:
                # Na visualização Detalhes, a primeira coluna numérica é o Total Size, e a segunda é o Free Space
                particao = m2.group(1)
                total_val = m2.group(2).replace(',', '.')
                total_unit = m2.group(3).upper()
                free_val = m2.group(4).replace(',', '.')
                free_unit = m2.group(5).upper()
            else:
                continue
                
            disponivel_str = f"{free_val} {free_unit}"
            capacidade_str = f"{total_val} {total_unit}"
            
            def to_gb(val, unit):
                v = float(val)
                if unit == 'TB': return v * 1024
                if unit == 'MB': return v / 1024
                if unit == 'KB': return v / (1024*1024)
                return v
                
            free_gb = to_gb(free_val, free_unit)
            total_gb = to_gb(total_val, total_unit)
            
            ocupado_gb = total_gb - free_gb
            ocupado_str = f"{ocupado_gb:.1f} GB"
            
            perc = (ocupado_gb / total_gb * 100) if total_gb > 0 else 0.0
            status = determine_status(perc)
            
            results.append({
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "servidor": server_name,
                "ip": server_info["ip"],
                "so": "Windows",
                "particao": particao,
                "capacidade_total": capacidade_str,
                "espaco_ocupado": ocupado_str,
                "espaco_disponivel": disponivel_str,
                "percentual_uso": f"{int(perc)}%",
                "status_alerta": status,
                "raw_percent": perc
            })
            
        if not results:
            # Fallback
            results.append({
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), 
                "servidor": server_name, 
                "ip": server_info["ip"], 
                "so": "Windows", 
                "particao": "Erro OCR - Leia a Dica", 
                "capacidade_total": "N/A", 
                "espaco_ocupado": "N/A", 
                "espaco_disponivel": "N/A", 
                "percentual_uso": "0%", 
                "status_alerta": "NORMAL", 
                "raw_percent": 0.0
            })
            
        return results
        
    except Exception as e:
        erro_msg = str(e)
        print(f"Erro OCR: {erro_msg}")
        return [{
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), 
            "servidor": "Erro OCR", 
            "ip": "N/A", 
            "so": "Windows", 
            "particao": erro_msg[:40], 
            "capacidade_total": "N/A", 
            "espaco_ocupado": "N/A", 
            "espaco_disponivel": "N/A", 
            "percentual_uso": "0%", 
            "status_alerta": "NORMAL", 
            "raw_percent": 0.0
        }]
