param([Parameter(ValueFromRemainingArguments=$true)][string[]]$PythonArgs)
$runtime = 'C:\Program Files\WindowsApps\OpenAI.CodexPrimaryRuntime.v26-1112-737-0_26.1112.737.0_x64__3k8sg7r9htsxt\dependencies\python\python.exe'
& $runtime @PythonArgs
exit $LASTEXITCODE
