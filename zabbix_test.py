import os
import requests
from dotenv import load_dotenv

load_dotenv()
url = os.getenv('ZABBIX_API_URL')
token = os.getenv('ZABBIX_API_TOKEN')

HOSTS = [
    {"hostid": "10636", "name": "SHIFT_DB_PRD"},
    {"hostid": "10595", "name": "VIVACE_PACS_01"}
]

for h in HOSTS:
    print(f"Host: {h['name']}, ID: {h['hostid']}")
    
    payload = {
        'jsonrpc': '2.0', 'method': 'item.get',
        'params': {'output': ['name', 'key_'], 'hostids': [h['hostid']]},
        'auth': token, 'id': 1
    }
    items = requests.post(url, json=payload, verify=False).json().get('result', [])
    print(f"Total items for {h['name']}: {len(items)}")
    for i in items:
        name = i['name'].lower()
        if 'cpu' in name or 'mem' in name or 'swap' in name or 'service' in name:
            print(f"    {i['key_']} -> {i['name']}")
