import re
from typing import List, Dict, Any, Optional

def parse_unified_output(text: str, server_name: str = None) -> List[Dict[str, Any]]:
    lines = [line.strip() for line in text.split('\n') if line.strip()]
    
    sections = {"HOST": "", "DISK": [], "MEM_SWAP": [], "TOP_CPU": [], "SERVICES": []}
    current_section = None
    
    for i, line in enumerate(lines):
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
        elif current_section:
            if current_section == "DISK":
                # handle broken lines in DISK just like before
                parts = re.split(r'\s+', line)
                if len(parts) == 1 and i + 1 < len(lines) and not lines[i+1].startswith("---"):
                    line = line + " " + lines[i+1].strip()
                    lines[i+1] = "" # clear next line
                if line: sections[current_section].append(line)
            else:
                sections[current_section].append(line)
                
    print(sections)

text = """===HURP_DIAGNOSTICO===
HOST: hvmmvappprod02
---DISK---
/dev/mapper/vg_mv-LogVol00 292G 225G 54G 81% /mv
---MEM_SWAP---
              total        used        free      shared  buff/cache   available
Mem:          31994        3000       25000          50        3944       28000
Swap:          8191           0        8191
---TOP_CPU---
 1.2  5.4 java
 0.0  0.1 sshd
---SERVICES---
tomcat:active
httpd:not_installed
"""
parse_unified_output(text)
