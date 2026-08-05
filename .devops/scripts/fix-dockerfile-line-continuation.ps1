param(
    [Parameter(Mandatory = $true)]
    [string]$RepositoryPath
)

$ErrorActionPreference = "Stop"
$UTF8_NO_BOM = New-Object System.Text.UTF8Encoding($false)

$Dockerfile = Join-Path $RepositoryPath "Dockerfile"

if (-not (Test-Path $Dockerfile)) {
    throw "DOCKERFILE_NOT_FOUND=$Dockerfile"
}

$Before = [System.IO.File]::ReadAllText($Dockerfile)

$InvalidLine = "RUN pip install --no-cache-dir --no-deps /tmp/packages/port_strategy_common-1.0.0-py3-none-any.whl ``"
$ValidLine = "RUN pip install --no-cache-dir --no-deps /tmp/packages/port_strategy_common-1.0.0-py3-none-any.whl \"

$MatchCount = ([regex]::Matches(
    $Before,
    [regex]::Escape($InvalidLine)
)).Count

if ($MatchCount -ne 1) {
    throw "INVALID_CONTINUATION_MATCH_COUNT=$MatchCount"
}

$After = $Before.Replace($InvalidLine, $ValidLine)

if ($After -eq $Before) {
    throw "DOCKERFILE_CONTINUATION_FIX_NOT_APPLIED"
}

if ($After.Contains($InvalidLine)) {
    throw "INVALID_CONTINUATION_REMAINS"
}

if (-not $After.Contains($ValidLine)) {
    throw "VALID_CONTINUATION_NOT_FOUND"
}

[System.IO.File]::WriteAllText(
    $Dockerfile,
    $After,
    $UTF8_NO_BOM
)

Write-Host "PATCHED_FILE=$Dockerfile"
Write-Host "DOCKERFILE_CONTINUATION_FIX=SUCCESS"