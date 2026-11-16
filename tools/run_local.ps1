param(
  [Parameter(Mandatory=$true)][string]$Regions,
  [Parameter(Mandatory=$true)][string]$Workspace,
  [string]$GtaRoot=$env:GTA_ROOT,
  [string]$Policy,
  [switch]$DryRun,
  [switch]$ReuseCatalog,
  [switch]$AllowMissing
)
$ErrorActionPreference='Stop'
$project=Split-Path $PSScriptRoot -Parent
$python=Join-Path $project '.venv/Scripts/python.exe'
if (!(Test-Path -LiteralPath $python)) { $python=(Get-Command python -ErrorAction Stop).Source }
$arguments=@((Join-Path $project 'src/local_workflow.py'),'--regions',$Regions,'--workspace',$Workspace)
if ($GtaRoot) { $arguments+=@('--gta-root',$GtaRoot) }
if ($Policy) { $arguments+=@('--policy',$Policy) }
if ($DryRun) { $arguments+='--dry-run' }
if ($ReuseCatalog) { $arguments+='--reuse-catalog' }
if ($AllowMissing) { $arguments+='--allow-missing' }
& $python @arguments
if ($LASTEXITCODE -ne 0) { throw "Local workflow failed (exit $LASTEXITCODE); inspect workflow-state.json and error-*.json in $Workspace" }
