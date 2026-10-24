# batch.ps1 - draai rcs-batch.scr met accoreconsole over alle *.dwg in een map.
# > ⚠️ Niet uitgevoerd: geen Windows/AutoCAD op deze Mac
# Vlaggen /i /s /l: AU-handout BES227196 (zie BRONNEN.md). Alle paden absoluut (aps-lisp-dotnet-skill SKILL.md r160).
param(
    [Parameter(Mandatory)] [string] $Map,
    [string] $Script  = (Join-Path $PSScriptRoot "rcs-batch.scr"),
    [string] $Accore  = "C:\Program Files\Autodesk\AutoCAD 2025\accoreconsole.exe",
    [string] $LogMap  = (Join-Path $PSScriptRoot "logs")
)
$ErrorActionPreference = "Stop"
$Map    = (Resolve-Path $Map).Path
$Script = (Resolve-Path $Script).Path
if (-not (Test-Path $Accore)) { Write-Error "accoreconsole niet gevonden: $Accore"; exit 1 }
New-Item -ItemType Directory -Force -Path $LogMap | Out-Null

$fouten = 0
Get-ChildItem -Path $Map -Filter *.dwg -File | ForEach-Object {
    $dwg = $_.FullName
    $log = Join-Path $LogMap ($_.BaseName + ".log")
    & $Accore /i "$dwg" /s "$Script" /l en-US *> $log
    $code = $LASTEXITCODE
    "{0}`t{1}`t{2}" -f (Get-Date -Format s), $code, $dwg | Add-Content (Join-Path $LogMap "batch.tsv")
    if ($code -ne 0) { $fouten++ ; Write-Warning "exitcode $code voor $dwg (zie $log)" }
}
exit $fouten
