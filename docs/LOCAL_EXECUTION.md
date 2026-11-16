# PC-return playbook (native decoding and engine results still unverified)

Use a fresh checkout/update of master; preserve earlier generated builds and profiles.
Install Python 3.12, .NET SDK 8.0.428 and Git, then from the repository root:

```powershell
py -3.12 -m venv .venv
./.venv/Scripts/python.exe -m pip install -r requirements-cloud.txt
git clone https://github.com/dexyfex/CodeWalker.git vendor/CodeWalker
git -C vendor/CodeWalker checkout 485d56bec00262ed7fa472261cce7bbc6202b96e
dotnet build src/AssetReader/AssetReader.csproj -c Release
./.venv/Scripts/python.exe tools/run_tests.py --output generated/local-tests-new.json
```

If vendor/CodeWalker already exists, verify its revision instead of cloning over it.
Create `config/regions-local.json` (selection example, not verified territory):

```json
[{"center":[-370,-1330],"radius":220},{"bbox":[-500,-1500,-200,-1200]}]
```

Choose the actual Legacy install path. Dry-run does not probe it:

```powershell
./tools/run_local.ps1 -Regions config/regions-local.json -Workspace generated/pc-return-01 -GtaRoot 'D:/SteamLibrary/steamapps/common/Grand Theft Auto V' -DryRun
```

Run the same command without `-DryRun`. `GTA_ROOT` can supply the path instead.
The root must contain GTA5.exe. Reader builds if its DLL is absent. The controller
runs native bootstrap, selects metadata, plans/extracts exact resources, converts
regions, composes one package, runs collision diagnostics/maps, and prepares an
isolated profile. It never launches the game automatically or controls a vehicle.

Active archive order is not guessed. If `Ambiguous metadata` or unresolved resource
diagnostics stop execution, inspect catalog/snapshot evidence and supply a policy
file with evidence-backed `archive_priorities` and `txd_parents`, via `-Policy`.
`-AllowMissing` explicitly permits incomplete output after reviewing diagnostics;
it is not a completeness or driving guarantee. Unknown collision bounds are exposed.

Retry the same command after interruption. Native checkpoints skip unchanged catalog
entries. Verified completed extraction tasks copy into a fresh attempt, incomplete
artifacts stay preserved. Region/composition retries preserve partial outputs;
completed packages and handoffs verify hashes and reuse without rebuilding. Source
changes create new snapshot/run IDs. Inspect workflow-state.json and error-*.json
for the failed stage, plus native errors.log/dependency-diagnostics.json.

The final printed path is `.../handoff/handoff.json`. Review missing resources,
collision sample failures, package SHA-256 and progress maps first. Then:

```powershell
& 'GENERATED_HANDOFF_DIRECTORY/launch.ps1' -BeamNGExe 'YOUR_BEAMNG_INSTALL/Bin64/BeamNG.drive.x64.exe'
```

The launcher checks the package hash and uses only the generated isolated userpath.
Keep Steam available if required by your installation. Confirm level loading,
materials, road alignment and missing collisions before driving. Record package-
matched logs, screenshots and performance observations. No generated game data,
keys, ZIPs or maps should be uploaded to GitHub. Cloud tests use original synthetic
native-protocol fixtures and a simulated reader; real archive decoding, key access,
all DLC combinations and actual BeamNG behavior remain local validation blockers.
