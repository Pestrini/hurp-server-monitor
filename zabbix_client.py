import os
import requests
import time
import numpy as np
from datetime import datetime
from dotenv import load_dotenv

def get_env_var(var_name):
    val = os.environ.get(var_name)
    if not val:
        basedir = os.path.abspath(os.path.dirname(__file__))
        load_dotenv(os.path.join(basedir, '.env'))
        val = os.environ.get(var_name)
    return val

HOSTS = {
    "10541": {"name": "SHIFT_DB_PRD", "ip": "192.168.1.1", "zabbix_hostname": "SERVER-01"},
    "10542": {"name": "SHIFT_SHADOW", "ip": "192.168.1.2", "zabbix_hostname": "SERVER-02"},
    "10543": {"name": "SHIFT_WEB", "ip": "192.168.1.4", "zabbix_hostname": "SERVER-04"},
    "10458": {"name": "SHIFT_AUTOMACAO", "ip": "192.168.1.3", "zabbix_hostname": "SERVER-03"},
    "10504": {"name": "MV_BALANCE", "ip": "192.168.1.10", "zabbix_hostname": "SERVER-10"},
    "10513": {"name": "MV_PRODUCAO_01", "ip": "192.168.1.9", "zabbix_hostname": "SERVER-09"},
    "10623": {"name": "VIVACE_PACS_01", "ip": "192.168.1.5", "zabbix_hostname": "SERVER-05"}
}

def rpc_call(method, params):
    api_url = get_env_var("ZABBIX_API_URL")
    api_token = get_env_var("ZABBIX_API_TOKEN")
    
    if not api_url or not api_token:
        raise Exception("ZABBIX_API_URL ou ZABBIX_API_TOKEN não configurados no ambiente. Crie um arquivo .env.")
    
    headers = {
        "Content-Type": "application/json-rpc",
        "Authorization": f"Bearer {api_token}"
    }
    
    payload = {
        "jsonrpc": "2.0",
        "method": method,
        "params": params,
        "id": 1
    }
    
    resp = requests.post(api_url, headers=headers, json=payload, verify=False)
    resp.raise_for_status()
    data = resp.json()
    
    if "error" in data:
        raise Exception(f"Erro na API Zabbix: {data['error']}")
        
    return data.get("result", [])

def get_smart_status(percent_used, dias_encher, crescimento_gb_dia):
    # Regra 1: Se vai encher rápido, é o mais urgente!
    if dias_encher != "N/A":
        if dias_encher <= 20:
            return "CRÍTICO"
        if dias_encher <= 40:
            return "ATENÇÃO"
            
    # Regra 2: Se não cresce ou cresce muito devagar (nunca enche ou enche em > 1 ano)
    if dias_encher == "N/A" or dias_encher > 365:
        if percent_used < 75 and crescimento_gb_dia <= 0.01:
            return "INATIVO"
        return "ESTÁVEL"
        
    # Regra 3: Se vai encher entre 40 e 365 dias, avalia pela ocupação bruta
    if percent_used >= 90:
        return "CRÍTICO"
    if percent_used >= 85:
        return "ATENÇÃO"
        
    return "NORMAL"

def is_important_disk(server_name, part_name):
    part = part_name.upper()
    if "VIVACE" in server_name.upper():
        if part in ["C:", "Z:", "R:", "P:"]:
            return True
        return False
    elif "SHIFT_DB" in server_name.upper():
        if "DADOS" in part or "JOURNAL" in part or "BINARIO" in part or "ROOT" in part or "BACKUP" in part or "/" == part:
            return True
        return False
    elif "MV_PRODUCAO" in server_name.upper():
        if part in ["C:", "D:"]:
            return True
        return False
    
    if part in ["C:", "/", "/DADOS", "/VAR", "D:"]:
        return True
    return False

def fetch_zabbix_data(months=6):
    hostids = list(HOSTS.keys())
    
    # 1. Busca os itemids do Zabbix (vfs.fs.size, CPU, Mem, Swap)
    items = rpc_call("item.get", {
        "output": ["itemid", "name", "key_", "lastvalue", "hostid"],
        "hostids": hostids
    })
    
    # Extrair metricas comportamentais
    server_metrics = {}
    for hid in hostids:
        server_metrics[hid] = {"cpu": "N/A", "ram": "N/A", "swap": "N/A"}
        
    partitions = {}
    for item in items:
        hid = item["hostid"]
        key = item["key_"]
        
        # Metricas Comportamentais
        keys_of_interest = ["system.cpu.util[,,avg5]", "system.cpu.util[all,system,avg1]", 
                            "vm.memory.size[pavailable]", "vm.memory.size[pused]", 
                            "system.swap.size[,pfree]", "system.swap.free.percent"]
        if key in keys_of_interest:
            val = float(item["lastvalue"]) if item["lastvalue"] else 0.0
            if key in ["system.cpu.util[,,avg5]", "system.cpu.util[all,system,avg1]"]:
                server_metrics[hid]["cpu"] = round(val, 1)
            elif key == "vm.memory.size[pavailable]":
                server_metrics[hid]["ram"] = round(100.0 - val, 1)
            elif key == "vm.memory.size[pused]":
                server_metrics[hid]["ram"] = round(val, 1)
            elif key == "system.swap.size[,pfree]":
                server_metrics[hid]["swap"] = round(100.0 - val, 1)
            elif key == "system.swap.free.percent":
                if val > 0: server_metrics[hid]["swap"] = round(100.0 - val, 1)
                
        # Discos
        import re
        match = re.match(r"^vfs\.fs\.size\[(.*),(used|total)\]$", key)
        if match:
            fs = match.group(1)
            metric = match.group(2)
            
            if hid not in partitions:
                partitions[hid] = {}
            if fs not in partitions[hid]:
                partitions[hid][fs] = {}
            
            if metric == "used":
                partitions[hid][fs]["used_itemid"] = item["itemid"]
                partitions[hid][fs]["last_used"] = float(item["lastvalue"])
            elif metric == "total":
                partitions[hid][fs]["total_bytes"] = float(item["lastvalue"])

    now_ts = int(time.time())
    days_to_fetch = months * 30
    time_from = now_ts - (days_to_fetch * 24 * 3600)
    
    results = []
    
    for hid, fs_dict in partitions.items():
        server_info = HOSTS[hid]
        
        for fs, data in fs_dict.items():
            if "used_itemid" not in data or "total_bytes" not in data or data["total_bytes"] == 0:
                continue
                
            total_bytes = data["total_bytes"]
            last_used = data["last_used"]
            percent = (last_used / total_bytes) * 100
            
            trends = rpc_call("trend.get", {
                "output": ["clock", "value_avg"],
                "itemids": [data["used_itemid"]],
                "time_from": time_from,
                "time_till": now_ts
            })
            
            crescimento_dia_gb = 0.0
            dias_para_encher = "N/A"
            
            if len(trends) >= 5:
                clocks = [float(t["clock"]) for t in trends]
                vals = [float(t["value_avg"]) for t in trends]
                
                min_c = min(clocks)
                x_days = [(c - min_c)/86400.0 for c in clocks]
                
                if len(x_days) > 1:
                    m, b = np.polyfit(x_days, vals, 1)
                    crescimento_dia_gb = m / (1024**3)
                    
                    if m > 0:
                        bytes_remaining = total_bytes - last_used
                        dias_para_encher = round(bytes_remaining / m)
                        if dias_para_encher > 9999:
                            dias_para_encher = 9999
            
            status = get_smart_status(percent, dias_para_encher, crescimento_dia_gb)
            is_imp = is_important_disk(server_info["name"], fs)
            
            free_bytes = total_bytes - last_used
            
            particao_formatada = fs
            if "Windows" in ("Linux" if "/" in fs else "Windows"):
                if server_info["name"] == "VIVACE_PACS_01":
                    vivace_labels = {
                        "C:": "OS", "E:": "DATA_NEW", "F:": "Gravacoes", 
                        "H:": "PACS01", "I:": "PACS02", "J:": "PACS03", 
                        "K:": "PACS04", "L:": "PACS05", "M:": "PACS06", 
                        "N:": "PACS07", "O:": "ARQUIVOS", "P:": "PACS08", 
                        "Q:": "PACS09", "R:": "PACS10", "Z:": "TEMPORARIO"
                    }
                    if fs in vivace_labels:
                        particao_formatada = f"{fs} ({vivace_labels[fs]})"
                elif server_info["name"] == "SHIFT_AUTOMACAO":
                    if fs == "C:": particao_formatada = "C: (OS)"
                    elif fs == "D:": particao_formatada = "D: (DATA)"
                elif server_info["name"] == "MV_PRODUCAO_01":
                    if fs == "C:": particao_formatada = "C: (OS)"
            
            results.append({
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "servidor": server_info["name"],
                "ip": server_info["ip"],
                "zabbix_hostname": server_info["zabbix_hostname"],
                "so": "Linux" if "/" in fs else "Windows",
                "particao": particao_formatada,
                "capacidade_total": f"{total_bytes / (1024**3):.2f} GB",
                "espaco_ocupado": f"{last_used / (1024**3):.2f} GB",
                "espaco_disponivel": f"{free_bytes / (1024**3):.2f} GB",
                "percentual_uso": f"{int(percent)}%",
                "crescimento_gb_dia": round(crescimento_dia_gb, 2),
                "dias_para_encher": dias_para_encher,
                "raw_percent": percent,
                "status_alerta": status,
                "importante": is_imp,
                "fonte": "Zabbix",
                "cpu_percent": server_metrics[hid]["cpu"],
                "ram_percent": server_metrics[hid]["ram"],
                "swap_percent": server_metrics[hid]["swap"],
                "servicos_status": "N/A",
                "processos_top": "N/A"
            })
            
    return results
