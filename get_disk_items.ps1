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
    method = "item.get"
    params = @{
        output = @("itemid", "name", "key_", "units")
        hostids = @("10541", "10458")
    }
    id = 1
} | ConvertTo-Json -Depth 5

$response = Invoke-RestMethod -Uri $env:ZABBIX_API_URL -Method Post -Body $body -Headers @{ "Content-Type"="application/json-rpc"; "Authorization"="Bearer $($env:ZABBIX_API_TOKEN)" }

$response.result | Where-Object { $_.name -match "disk|fs|espaço|space|used|livre" -or $_.key_ -match "vfs.fs" } | Select-Object itemid, name, key_, units | Format-Table -AutoSize | Out-String
