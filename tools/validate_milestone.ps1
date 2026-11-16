param([Parameter(Mandatory=$true)][string]$Build, [Parameter(Mandatory=$true)][string]$Checkpoint)
$ErrorActionPreference='Stop'
& "$PSScriptRoot/python.ps1" src/validate_surfaces.py $Build
if ($LASTEXITCODE -ne 0) { throw 'Surface validation failed' }
& "$PSScriptRoot/python.ps1" src/progress_maps.py $Build --checkpoint $Checkpoint
if ($LASTEXITCODE -ne 0) { throw 'Progress maps failed' }
& "$PSScriptRoot/python.ps1" src/package.py $Build "builds/$Checkpoint/los_santos_fazes.zip"
if ($LASTEXITCODE -ne 0) { throw 'Packaging failed' }
