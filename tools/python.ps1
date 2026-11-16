param([Parameter(ValueFromRemainingArguments=$true)][string[]]$PythonArgs)
$runtime = Join-Path $PSScriptRoot '../.venv/Scripts/python.exe'
if (-not (Test-Path $runtime)) { $runtime = 'python' }
& $runtime @PythonArgs
exit $LASTEXITCODE
