param([string]$Folder = ".\emails")

New-Item -ItemType Directory -Force -Path ".\outputs" | Out-Null

Get-ChildItem -Path $Folder -Filter *.txt | ForEach-Object {
  $name = $_.BaseName

  # Read as a single string
  $raw  = Get-Content $_.FullName -Raw -ErrorAction Stop
  if ($null -eq $raw -or $raw.Trim().Length -eq 0) {
    Write-Warning ("Skipping {0}: file is empty." -f $name)
    return
  }
  $text = [string]$raw

  # Build JSON body
  $json = @{ text = $text } | ConvertTo-Json -Depth 5 -Compress

  try {
    $resp = Invoke-RestMethod -Method Post `
      -Uri http://127.0.0.1:8080/summarize `
      -ContentType 'application/json; charset=utf-8' `
      -Body $json `
      -ErrorAction Stop

    $ts  = Get-Date -Format "yyyyMMdd-HHmm"
    $out = ".\outputs\$($name)-summary-$ts.md"
    $resp.summary_markdown | Out-File $out -Encoding utf8
    Write-Host ("✓ {0} -> {1}" -f $name, $out)
  } catch {
    $server = $_.ErrorDetails.Message
    if ([string]::IsNullOrWhiteSpace($server)) { $server = $_.Exception.Message }
    Write-Warning ("Failed on {0}: {1}`nServer said: {2}" -f $name, $_.Exception.Message, $server)
    Write-Verbose ("Sent JSON (first 200): {0}" -f ($json.Substring(0, [Math]::Min(200, $json.Length))))
  }
}
