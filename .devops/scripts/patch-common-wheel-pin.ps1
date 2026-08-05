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

$Lines = @(
    [System.IO.File]::ReadAllLines($Dockerfile)
)

$SourceCopyLine = "COPY port_strategy_common/ ./port_strategy_common/"
$ResearchCopyLine = "COPY port_strategy_research/ ./port_strategy_research/"

$SourceIndexes = @()

for ($Index = 0; $Index -lt $Lines.Count; $Index++) {
    if ($Lines[$Index].Trim() -eq $SourceCopyLine) {
        $SourceIndexes += $Index
    }
}

if ($SourceIndexes.Count -ne 1) {
    throw "COMMON_SOURCE_COPY_MATCH_COUNT=$($SourceIndexes.Count)"
}

$SourceIndex = $SourceIndexes[0]

if (($SourceIndex + 1) -ge $Lines.Count) {
    throw "RESEARCH_COPY_LINE_NOT_FOUND_AFTER_SOURCE_COPY"
}

if ($Lines[$SourceIndex + 1].Trim() -ne $ResearchCopyLine) {
    throw "UNEXPECTED_LINE_AFTER_COMMON_SOURCE_COPY=$($Lines[$SourceIndex + 1])"
}

$ReplacementLines = @(
    "COPY .devops/packages/port_strategy_common-1.0.0-py3-none-any.whl /tmp/packages/port_strategy_common-1.0.0-py3-none-any.whl",
    "",
    "RUN pip install --no-cache-dir --no-deps /tmp/packages/port_strategy_common-1.0.0-py3-none-any.whl ``",
    "    && python -c `"import importlib.metadata; version = importlib.metadata.version('port-strategy-common'); assert version == '1.0.0', version`""
)

$OutputLines = New-Object System.Collections.Generic.List[string]

for ($Index = 0; $Index -lt $Lines.Count; $Index++) {
    if ($Index -eq $SourceIndex) {
        foreach ($ReplacementLine in $ReplacementLines) {
            $OutputLines.Add($ReplacementLine)
        }

        continue
    }

    $OutputLines.Add($Lines[$Index])
}

$OutputText = [string]::Join(
    [Environment]::NewLine,
    $OutputLines
)

$OutputText += [Environment]::NewLine

if ($OutputText.Contains(
    "COPY port_strategy_common/ ./port_strategy_common/"
)) {
    throw "COMMON_SOURCE_COPY_REMAINS_AFTER_PATCH"
}

if (-not $OutputText.Contains(
    "COPY .devops/packages/port_strategy_common-1.0.0-py3-none-any.whl"
)) {
    throw "COMMON_WHEEL_COPY_NOT_ADDED"
}

if (-not $OutputText.Contains(
    "pip install --no-cache-dir --no-deps /tmp/packages/port_strategy_common-1.0.0-py3-none-any.whl"
)) {
    throw "COMMON_WHEEL_INSTALL_NOT_ADDED"
}

if (-not $OutputText.Contains(
    "assert version == '1.0.0'"
)) {
    throw "COMMON_VERSION_ASSERT_NOT_ADDED"
}

[System.IO.File]::WriteAllText(
    $Dockerfile,
    $OutputText,
    $UTF8_NO_BOM
)

Write-Host "PATCHED_FILE=$Dockerfile"
Write-Host "DOCKERFILE_LINE_PATCH=SUCCESS"