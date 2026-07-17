import os
import requests
import json
from dotenv import load_dotenv

load_dotenv()
url = os.getenv('ZABBIX_API_URL')
token = os.getenv('ZABBIX_API_TOKEN')

payload = {
    "jsonrpc": "2.0",
    "method": "item.get",
    "params": {
        "output": ["itemid", "name", "key_", "lastvalue", "hostid"],
        "hostids": ["10636", "10623"]
    },
    "auth": token,
    "id": 1
}

resp = requests.post(url, json=payload, verify=False)
items = resp.json().get('result', [])

with open('zabbix_items_dump.txt', 'w') as f:
    for i in items:
        f.write(f"Host: {i['hostid']} | Key: {i['key_']} | Name: {i['name']} | LastValue: {i['lastvalue']}\n")
