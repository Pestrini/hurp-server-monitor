$ErrorActionPreference = "Stop"
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

$hostids = @("10541", "10542", "10543", "10458", "10504", "10513", "10623")
$hostNames = @{
    "10541" = "SHIFT_DB_PRD"
    "10542" = "SHIFT_SHADOW"
    "10543" = "SHIFT_WEB"
    "10458" = "SHIFT_AUTOMACAO"
    "10504" = "MV_BALANCE"
    "10513" = "MV_PRODUCAO_01"
    "10623" = "VIVACE_PACS_01"
}

Write-Host "Buscando itens de disco..."
$itemsBody = @{
    jsonrpc = "2.0"
    method = "item.get"
    params = @{
        output = @("itemid", "name", "key_", "value_type", "hostid", "lastvalue")
        hostids = $hostids
    }
    id = 1
} | ConvertTo-Json -Depth 5

$response = Invoke-RestMethod -Uri $apiUrl -Method Post -Body $itemsBody -Headers $headers
$allItems = $response.result

$partitions = @{} 

foreach ($item in $allItems) {
    if ($item.key_ -match "^vfs\.fs\.size\[(.*),(used|total)\]$") {
        $fs = $matches[1]
        $metric = $matches[2]
        $hostid = $item.hostid
        
        if (-not $partitions.ContainsKey($hostid)) {
            $partitions[$hostid] = @{}
        }
        if (-not $partitions[$hostid].ContainsKey($fs)) {
            $partitions[$hostid][$fs] = @{}
        }
        
        if ($metric -eq "used") {
            $partitions[$hostid][$fs].UsedItemId = $item.itemid
            $partitions[$hostid][$fs].LastUsed = [double]$item.lastvalue
        } elseif ($metric -eq "total") {
            $partitions[$hostid][$fs].TotalBytes = [double]$item.lastvalue
        }
    }
}

$now = [int][double]::Parse((Get-Date -UFormat %s))
$timeFrom = $now - (365 * 24 * 3600)

$report = "# Analise Critica de Espaco em Disco (Ultimos 365 Dias)`n`n"

Write-Host "Buscando historico e calculando projecoes..."

foreach ($hostid in $partitions.Keys) {
    $hostName = $hostNames[$hostid]
    $report += "## Servidor: $hostName`n`n"
    $report += "| Particao | Total (GB) | Uso Atual | Crescimento Diario | Tempo p/ Encher | Volatilidade | Status Critico |`n"
    $report += "| :--- | :--- | :--- | :--- | :--- | :--- | :--- |`n"

    foreach ($fs in $partitions[$hostid].Keys) {
        $part = $partitions[$hostid][$fs]
        if (-not $part.UsedItemId -or -not $part.TotalBytes -or $part.TotalBytes -eq 0) {
            continue
        }

        $body = @{
            jsonrpc = "2.0"
            method = "trend.get"
            params = @{
                output = @("clock", "value_avg")
                itemids = @($part.UsedItemId)
                time_from = $timeFrom
                time_till = $now
            }
            id = 2
        } | ConvertTo-Json -Depth 5

        try {
            $trendResp = Invoke-RestMethod -Uri $apiUrl -Method Post -Body $body -Headers $headers
            $trends = $trendResp.result

            $totalGb = [math]::Round($part.TotalBytes / 1GB, 2)
            $usedGb = [math]::Round($part.LastUsed / 1GB, 2)

            if ($trends.Count -lt 5) {
                $report += "| $fs | $totalGb | $usedGb GB | Sem Dados Historicos suficientes | N/A | N/A | N/A |`n"
                continue
            }

            $minClock = $trends[0].clock
            $sumX = 0; $sumY = 0; $sumX2 = 0; $sumXY = 0; $n = $trends.Count
            $values = @()

            foreach ($t in $trends) {
                $days = ($t.clock - $minClock) / 86400.0
                $val = [double]$t.value_avg
                $sumX += $days
                $sumY += $val
                $sumX2 += ($days * $days)
                $sumXY += ($days * $val)
                $values += $val
            }

            $denominator = ($n * $sumX2) - ($sumX * $sumX)
            if ($denominator -eq 0) { $denominator = 1 }
            $m = (($n * $sumXY) - ($sumX * $sumY)) / $denominator 

            $avgY = $sumY / $n
            $sumSqDiff = 0
            foreach ($v in $values) {
                $sumSqDiff += [math]::Pow($v - $avgY, 2)
            }
            $stdDev = [math]::Sqrt($sumSqDiff / $n)
            $volatilityPct = 0
            if ($avgY -gt 0) {
                $volatilityPct = ($stdDev / $avgY) * 100
            }

            $currentUsagePct = ($part.LastUsed / $part.TotalBytes) * 100
            $bytesRemaining = $part.TotalBytes - $part.LastUsed
            
            $daysToFull = -1
            if ($m -gt 0) {
                $daysToFull = $bytesRemaining / $m
            }

            $mGb = [math]::Round($m / 1GB, 4)
            
            $daysStr = "N/A"
            if ($m -le 0) {
                $daysStr = "Estavel/Reduzindo"
            } elseif ($daysToFull -gt 1000) {
                $daysStr = "> 3 anos"
            } else {
                $dRounded = [math]::Round($daysToFull)
                $daysStr = "**$dRounded dias**"
            }

            $critico = "Normal"
            if ($currentUsagePct -gt 90) {
                if ($volatilityPct -gt 5 -or ($daysToFull -gt 0 -and $daysToFull -lt 30)) {
                    $critico = "ALERTA MAXIMO"
                } else {
                    $critico = "Atencao (Cheio mas estavel)"
                }
            } elseif ($currentUsagePct -gt 80) {
                if ($daysToFull -gt 0 -and $daysToFull -lt 60) {
                    $critico = "Cuidado (Enchendo rapido)"
                } else {
                    $critico = "Atencao"
                }
            } elseif ($daysToFull -gt 0 -and $daysToFull -lt 30) {
                $critico = "ALERTA (Espaco acabando rapido)"
            }

            $vRounded = [math]::Round($volatilityPct, 2)
            $volatilityStr = "$vRounded%"
            $pctRounded = [math]::Round($currentUsagePct, 1)

            $report += "| **$fs** | $totalGb | $usedGb GB ($pctRounded%) | $mGb GB | $daysStr | $volatilityStr | $critico |`n"

        } catch {
            $report += "| $fs | ERRO | ERRO | ERRO | ERRO | ERRO | ERRO |`n"
        }
    }
    $report += "`n"
}

$report | Out-File -FilePath ".\disk_analysis_report.md" -Encoding utf8
Write-Host "Relatorio gerado em .\disk_analysis_report.md"
