$envPath = ".\.env"
if (Test-Path $envPath) {
    Get-Content $envPath | ForEach-Object {
        if ($_ -match "^(.*?)=(.*)$") {
            Set-Item -Path "env:\$($matches[1])" -Value $matches[2]
        }
    }
}

$apiUrl = $env:ZABBIX_API_URL
$apiToken = $env:ZABBIX_API_TOKEN

$headers = @{
    "Content-Type" = "application/json-rpc"
    "Authorization" = "Bearer $apiToken"
}

$servers = @(
    @{ Name = "SHIFT_DB_PRD"; IP = "192.168.1.1" },
    @{ Name = "SHIFT_SHADOW"; IP = "192.168.1.2" },
    @{ Name = "SHIFT_AUTOMACAO"; IP = "192.168.1.3" },
    @{ Name = "SHIFT_WEB"; IP = "192.168.1.4" },
    @{ Name = "VIVACE_PACS_01"; IP = "192.168.1.5" },
    @{ Name = "VIVACE_PACS_02"; IP = "192.168.1.6" },
    @{ Name = "VIVACE_PACS_WEB"; IP = "192.168.1.7" },
    @{ Name = "MV_PRODUCAO_02"; IP = "192.168.1.8" },
    @{ Name = "MV_PRODUCAO_01"; IP = "192.168.1.9" },
    @{ Name = "MV_BALANCE"; IP = "192.168.1.10" },
    @{ Name = "HINNO_APP"; IP = "192.168.1.11" },
    @{ Name = "GREEN"; IP = "192.168.1.12" }
)

# Buscar todos os hosts com suas interfaces para mapear por IP
$body = @{
    jsonrpc = "2.0"
    method = "host.get"
    params = @{
        output = @("hostid", "host", "name")
        selectInterfaces = @("ip")
    }
    id = 1
} | ConvertTo-Json -Depth 5

$results = @()

try {
    $response = Invoke-RestMethod -Uri $apiUrl -Method Post -Body $body -Headers $headers
    $allHosts = $response.result
    
    foreach ($server in $servers) {
        $foundHost = $null
        foreach ($h in $allHosts) {
            foreach ($intf in $h.interfaces) {
                if ($intf.ip -eq $server.IP) {
                    $foundHost = $h
                    break
                }
            }
            if ($foundHost) { break }
        }
        
        if ($foundHost) {
            $results += [PSCustomObject]@{
                NomeSolicitado = $server.Name
                IP = $server.IP
                ZabbixHostId = $foundHost.hostid
                ZabbixHost = $foundHost.host
                ZabbixName = $foundHost.name
            }
        } else {
            $results += [PSCustomObject]@{
                NomeSolicitado = $server.Name
                IP = $server.IP
                ZabbixHostId = "N/A"
                ZabbixHost = "Não Encontrado"
                ZabbixName = "Não Encontrado"
            }
        }
    }
} catch {
    Write-Host "Erro ao buscar hosts no Zabbix: $_"
}

$results | Format-Table -AutoSize | Out-String
