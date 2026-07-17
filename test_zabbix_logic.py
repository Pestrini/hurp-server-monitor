import zabbix_client

hostids = list(zabbix_client.HOSTS.keys())

cpu_mem_items = zabbix_client.rpc_call("item.get", {
    "output": ["itemid", "name", "key_", "lastvalue", "hostid"],
    "hostids": hostids,
})

server_metrics = {}
for hid in hostids:
    server_metrics[hid] = {"cpu": "N/A", "ram": "N/A", "swap": "N/A"}
    
for item in cpu_mem_items:
    hid = item["hostid"]
    key = item["key_"]
    
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
            server_metrics[hid]["swap"] = round(val, 1) # If free percent is given, well, wait. Windows said 0. So used is 100-val? 
            # actually if it's 0 it might just mean no swap. Let's just leave it N/A if it's 0 for now.
            if val == 0:
                pass
            else:
                server_metrics[hid]["swap"] = round(100.0 - val, 1)

for hid, metrics in server_metrics.items():
    name = zabbix_client.HOSTS[hid]['name']
    print(f"{name}: CPU={metrics['cpu']}% RAM={metrics['ram']}% SWAP={metrics['swap']}%")
