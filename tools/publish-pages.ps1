# Compatibility adapter; the portable implementation is tools/publish_pages.py.
param(
    [Parameter(Mandatory = $true)][string]$Site,
    [switch]$Push
)
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'dev-env.ps1')
$Arguments = @((Join-Path $PSScriptRoot 'publish_pages.py'), '--site', $Site)
if ($Push) { $Arguments += '--push' }
& $Python @Arguments
if ($LASTEXITCODE -ne 0) {
    throw 'Python publication failed. Inspect its result; do not force or replay a successful push.'
}
