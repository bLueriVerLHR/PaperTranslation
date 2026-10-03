# Dot-source this file from the repository root before running Python tools.
# Only reproducible development state belongs here; never store paper sources in TEMP.
param([switch]$CreateVenv)

$RepoRoot = [IO.Path]::GetFullPath((Split-Path $PSScriptRoot -Parent))
$Hasher = [Security.Cryptography.SHA256]::Create()
try {
    $RepoHash = ([BitConverter]::ToString($Hasher.ComputeHash(
        [Text.Encoding]::UTF8.GetBytes($RepoRoot.ToLowerInvariant())
    ))).Replace('-', '').Substring(0, 12).ToLowerInvariant()
} finally {
    $Hasher.Dispose()
}
$ProjectTemp = Join-Path ([IO.Path]::GetTempPath()) "paper-translation-$RepoHash"
$Python = Join-Path $ProjectTemp 'venv\Scripts\python.exe'
# Windows redirected stdout may otherwise use cp1252 and fail on Chinese titles.
$env:PYTHONUTF8 = '1'
$env:PYTHONIOENCODING = 'utf-8'
$env:PYTHONPYCACHEPREFIX = Join-Path $ProjectTemp 'pycache'
$env:RUFF_CACHE_DIR = Join-Path $ProjectTemp 'ruff-cache'
# Quote the path for pytest's argument parser (Windows user paths may contain spaces).
$PytestCache = (Join-Path $ProjectTemp 'pytest-cache').Replace('\', '/')
$CacheOption = "-o cache_dir=`"$PytestCache`""
if (!$env:PYTEST_ADDOPTS -or !$env:PYTEST_ADDOPTS.Contains($CacheOption)) {
    $env:PYTEST_ADDOPTS = "$($env:PYTEST_ADDOPTS) $CacheOption".Trim()
}
foreach ($Directory in @($ProjectTemp, (Join-Path $ProjectTemp 'tasks'),
    (Join-Path $ProjectTemp 'reports'), (Join-Path $ProjectTemp 'scratch'))) {
    New-Item -ItemType Directory -Path $Directory -Force | Out-Null
}
# The background harness uses a fixed .pi/tasks path. A junction keeps its actual
# files in system TEMP without changing the harness's expected workspace path.
$HarnessTasks = Join-Path $ProjectTemp 'harness-tasks'
New-Item -ItemType Directory -Path $HarnessTasks -Force | Out-Null
$PiDirectory = Join-Path $RepoRoot '.pi'
$PiTasks = Join-Path $PiDirectory 'tasks'
if (!(Test-Path -LiteralPath $PiTasks)) {
    New-Item -ItemType Directory -Path $PiDirectory -Force | Out-Null
    New-Item -ItemType Junction -Path $PiTasks -Target $HarnessTasks | Out-Null
} elseif (!((Get-Item -LiteralPath $PiTasks).Attributes -band [IO.FileAttributes]::ReparsePoint)) {
    Write-Warning 'Existing .pi/tasks is local. Relocate it only after all background tasks finish.'
}
if ($CreateVenv) {
    & py -3.14 -m venv (Join-Path $ProjectTemp 'venv')
    if ($LASTEXITCODE -ne 0) { throw 'Failed to create the temporary development environment.' }
}
Write-Host "Development state: $ProjectTemp"
