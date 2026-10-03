# Stage a validated reader-only site in a new TEMP checkout and commit to pages-content.
# No force push, no main-branch dist files, no deletion of the canonical dist tree.
param(
    [Parameter(Mandatory = $true)][string]$Site,
    [switch]$Push
)
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'dev-env.ps1')
$RepoRoot = Split-Path $PSScriptRoot -Parent
$Site = [IO.Path]::GetFullPath($Site)
$TempRoot = [IO.Path]::GetFullPath([IO.Path]::GetTempPath()).TrimEnd('\') + '\'
if (!$Site.StartsWith($TempRoot, [StringComparison]::OrdinalIgnoreCase)) {
    throw 'Site must be an absolute directory under system TEMP.'
}
& $Python (Join-Path $PSScriptRoot 'pages.py') --check $Site
if ($LASTEXITCODE -ne 0) { throw 'Public-site validation failed; nothing was pushed.' }
$Remote = git -C $RepoRoot remote get-url origin
if ($LASTEXITCODE -ne 0) { throw 'No origin remote.' }
$UserName = git -C $RepoRoot config user.name
$UserEmail = git -C $RepoRoot config user.email
if (!$UserName -or !$UserEmail) { throw 'Configure git user.name and user.email first.' }
$Checkout = Join-Path $ProjectTemp ('scratch\pages-checkout-' + [guid]::NewGuid().ToString('N'))
$Existing = git -C $RepoRoot ls-remote --heads origin pages-content
if ($LASTEXITCODE -ne 0) { throw 'Could not inspect the remote content branch.' }
if ($Existing) {
    git clone --single-branch --branch pages-content $Remote $Checkout
    if ($LASTEXITCODE -ne 0) { throw 'Could not clone content branch.' }
} else {
    git init --initial-branch=pages-content $Checkout
    if ($LASTEXITCODE -ne 0) { throw 'Could not initialize content checkout.' }
    git -C $Checkout remote add origin $Remote
}
git -C $Checkout config user.name $UserName
git -C $Checkout config user.email $UserEmail
# This is a fresh, dedicated TEMP checkout, never the user's working directory.
Get-ChildItem -LiteralPath $Checkout -Force | Where-Object Name -ne '.git' |
    Remove-Item -Recurse -Force
Get-ChildItem -LiteralPath $Site -Force | Where-Object Name -ne '.git' |
    Copy-Item -Destination $Checkout -Recurse -Force
& $Python (Join-Path $PSScriptRoot 'pages.py') --check $Checkout
if ($LASTEXITCODE -ne 0) { throw 'Content checkout validation failed.' }
git -C $Checkout add --all
if ($LASTEXITCODE -ne 0) { throw 'Could not stage public files.' }
git -C $Checkout diff --cached --quiet
if ($LASTEXITCODE -eq 1) {
    git -C $Checkout commit -m 'docs(pages): update public reading library'
    if ($LASTEXITCODE -ne 0) { throw 'Content commit failed.' }
} elseif ($LASTEXITCODE -ne 0) { throw 'Could not inspect staged content.' }
if ($Push) {
    git -C $Checkout push origin HEAD:pages-content
    if ($LASTEXITCODE -ne 0) { throw 'Push rejected; do not force. Re-run against the latest branch.' }
}
Write-Host "Content checkout: $Checkout"
Write-Host 'Main branch and canonical work trees were not changed by this command.'
