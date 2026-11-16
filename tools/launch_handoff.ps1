param([Parameter(Mandatory=$true)][string]$BeamNGExe)
$ErrorActionPreference='Stop'
if (!(Test-Path -LiteralPath $BeamNGExe -PathType Leaf)) { throw 'BeamNG executable not found' }
$handoff=Get-Content -Raw -LiteralPath (Join-Path $PSScriptRoot 'handoff.json') | ConvertFrom-Json
$hash=(Get-FileHash -LiteralPath $handoff.profile_package -Algorithm SHA256).Hash.ToLowerInvariant()
if ($hash -ne $handoff.package_sha256) { throw 'Isolated profile package hash mismatch; refusing launch' }
Start-Process -FilePath $BeamNGExe -ArgumentList @('-userpath',('"'+$handoff.profile+'"'),'-level','los_santos_fazes')
