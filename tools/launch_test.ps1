param([string]$PackagePath='builds/checkpoint03/los_santos_fazes.zip', [string]$ProfileName='beamng-test03')
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path $PSScriptRoot -Parent
if ($ProfileName -notmatch '^[a-zA-Z0-9_-]+$') { throw 'Invalid profile name' }
$package = (Resolve-Path -LiteralPath (Join-Path $projectRoot $PackagePath)).Path
if (!(Test-Path -LiteralPath ($package -replace '\.zip$','.manifest.json'))) { throw 'Package validation manifest required' }
$profile = Join-Path $projectRoot ('generated/'+$ProfileName)
$matches = @(Get-CimInstance Win32_Process -Filter "Name='BeamNG.drive.x64.exe'" | Where-Object { $_.CommandLine -like "*-userpath*$projectRoot*" -and $_.CommandLine -notlike '*--type=*' })
if ($matches.Count -gt 1) { throw 'More than one matching test instance; refusing to stop any.' }
foreach ($p in $matches) { Stop-Process -Id $p.ProcessId }
if ($matches.Count) { Start-Sleep -Seconds 4 }
$ext = Join-Path $profile 'current/lua/ge/extensions/lsf'
New-Item -ItemType Directory -Force $ext | Out-Null
Copy-Item -LiteralPath (Join-Path $projectRoot 'src/lsf_validation.lua') -Destination (Join-Path $ext 'validation.lua') -Force
$mods = Join-Path $profile 'current/mods'
New-Item -ItemType Directory -Force $mods | Out-Null
Copy-Item -LiteralPath $package -Destination (Join-Path $mods 'los_santos_fazes.zip') -Force
Start-Process -FilePath 'C:\Program Files (x86)\Steam\steam.exe' -ArgumentList @('-applaunch','284160','-userpath',('"'+$profile+'"'),'-level','los_santos_fazes','-onLevelLoad_ext','lsf_validation') -WindowStyle Hidden
