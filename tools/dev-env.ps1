# Windows compatibility adapter. Portable environment logic lives in tools/dev.py.
param([switch]$CreateVenv)
$ErrorActionPreference = 'Stop'
$env:PYTHONUTF8 = '1'
$env:PYTHONIOENCODING = 'utf-8'
$Arguments = @((Join-Path $PSScriptRoot 'dev.py'), 'env')
if ($CreateVenv) { $Arguments += '--create-venv' }
$Info = (& python @Arguments | ConvertFrom-Json)
if ($LASTEXITCODE -ne 0) { throw 'Python environment setup failed.' }
$ProjectTemp = $Info.project_temp
$Python = $Info.python
foreach ($Property in $Info.env.PSObject.Properties) {
    [Environment]::SetEnvironmentVariable($Property.Name, $Property.Value, 'Process')
}
# Optional Windows Pi-harness compatibility; ordinary Python commands need no junction.
$HarnessTasks = Join-Path $ProjectTemp 'harness-tasks'
New-Item -ItemType Directory -Path $HarnessTasks -Force | Out-Null
$RepoRoot = Split-Path $PSScriptRoot -Parent
$PiDirectory = Join-Path $RepoRoot '.pi'
$PiTasks = Join-Path $PiDirectory 'tasks'
if (!(Test-Path -LiteralPath $PiTasks)) {
    New-Item -ItemType Directory -Path $PiDirectory -Force | Out-Null
    New-Item -ItemType Junction -Path $PiTasks -Target $HarnessTasks | Out-Null
} elseif (!((Get-Item -LiteralPath $PiTasks).Attributes -band [IO.FileAttributes]::ReparsePoint)) {
    Write-Warning 'Existing .pi/tasks is local. Relocate it only after all background tasks finish.'
}
Write-Host "Development state: $ProjectTemp"
