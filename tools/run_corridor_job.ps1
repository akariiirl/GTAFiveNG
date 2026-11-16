param([Parameter(Mandatory=$true)][string]$Config)
$ErrorActionPreference='Stop'
$settings=Get-Content -Raw -LiteralPath $Config | ConvertFrom-Json
$memory=Get-CimInstance Win32_OperatingSystem
if ($memory.FreePhysicalMemory -lt 8GB/1KB) { throw 'At least 8 GiB available RAM required; no work started' }
$env:PYTHONPATH=$settings.python_packages
# One extraction/conversion at a time; planner uses at most four readers.
$env:OMP_NUM_THREADS='4'
$env:OPENBLAS_NUM_THREADS='4'
& $settings.python -u (Join-Path (Split-Path $PSScriptRoot -Parent) 'src/corridor_job.py') $Config
exit $LASTEXITCODE
