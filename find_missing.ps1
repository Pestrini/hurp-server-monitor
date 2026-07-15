$envPath = ".\.env"
if (Test-Path $envPath) {
    Get-Content $envPath | ForEach-Object {
        if ($_ -match "^(.*?)=(.*)$") {
            Set-Item -Path "env:\$($matches[1])" -Value $matches[2]
        }
    }
}

$body = @{
    jsonrpc = "2.0"
    method = "host.get"
    params = @{
        output = @("hostid", "host", "name")
        selectInterfaces = @("ip")
    }
    id = 1
} | ConvertTo-Json -Depth 5

$response = Invoke-RestMethod -Uri $env:ZABBIX_API_URL -Method Post -Body $body -Headers @{ "Content-Type"="application/json-rpc"; "Authorization"="Bearer $($env:ZABBIX_API_TOKEN)" }

Write-Host "Buscando por nomes aproximados (VIVACE, MV, HINNO, GREEN)..."
$response.result | Where-Object { $_.name -match 'vivace|mv|hinno|green|pacs' -or $_.host -match 'vivace|mv|hinno|green|pacs' } | Select-Object hostid, host, name, @{Name='IPs';Expression={$_.interfaces.ip -join ', '}} | Format-Table -AutoSize | Out-String
