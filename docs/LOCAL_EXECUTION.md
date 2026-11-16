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

To reuse a completed native catalog without rescanning game archives, pass
`-ReuseCatalog`. This checks archive and reader modification times against the
bootstrap completion time, checks indexed physical archives are still present,
and validates each candidate metadata XML hash as it is read. Modification times
are not cryptographic proof that archive bytes are unchanged: rerun bootstrap if
archives may have been replaced with preserved times.
Region conflict checking inspects all YMAP candidates and relevant YTYP candidates;
unrelated metadata conflicts are reported in `metadata-conflicts.json`, while
unresolved relevant conflicts stop the workflow. Active mount precedence is not
inferred from filenames.

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

Optional streaming-readiness work is deliberately excluded from the normal launch.
See `docs/RUNTIME_EXPERIMENT.md` for the separate empty-scene profile, generated
prefab plan, version-dependent Lua adapter and explicit engine-validation checklist.

## Two-adjacent-chunk streaming validation (experimental)

Do not treat the offline predictive planner as an engine loader or drivable-state
signal. For the first local experiment, use two adjacent synthetic or converted
chunks with a road crossing the shared edge. Keep the existing package/profile
unchanged and use a fresh isolated profile. Record the composed package SHA-256
alongside BeamNG version, logs, screenshots and each observation.

1. Verify each chunk's collision files are present and run structural validation;
   inspect/raycast the road on both sides of the boundary before driving.
2. Load stationary, confirm both visual chunks and collision surfaces, then cross
   the boundary slowly in both directions. Record missing surfaces, visible gaps,
   load/unload timestamps and any stalls.
3. Repeat with unload/reload, then collect BeamNG FPS and process RAM readings at
   fixed intervals. Record the exact package hash with all results; cloud byte and
   Lua-heap estimates are not engine RAM/VRAM/FPS measurements.
4. Stop driving if either side's collision cannot be confirmed. Collision
   inventory/availability is not proof of collision loaded or drivable.

### Synthetic showcase and CI preview

Generate a self-contained dashboard, isometric PNG, SVG scheduler chart and JSON
summary without any game data:

```powershell
./.venv/Scripts/python.exe tools/streaming_showcase.py --output generated/streaming-showcase
```

Open `generated/streaming-showcase/index.html` locally. In GitHub, open the
successful Source-only tests Actions run and download the
`synthetic-evidence-windows-latest` artifact; extract it and open
`showcase/index.html` on a phone. The artifact is synthetic-only and expires after
14 days. The PNG can be viewed directly in the artifact or downloaded separately.
No server or external JS/CDN is used.

The built-in scenario is fixed at 1,200 synthetic chunks and 80 ticks. The current
result is 26 peak active chunks, 322 scheduled loads and 9,300,000 estimated
resident payload bytes. Run twice and compare `streaming-summary.json` and
`streaming-preview.png` hashes to check deterministic output. Estimates exclude
engine/interpreter overhead and are not RAM, VRAM, FPS, collision-build or hitch
measurements. The scene is a static 3D-style illustration, not converted geometry.

The planner is offline and opt-in. Its `collision_ready` list means only that
synthetic/input inventory marked collision available; `drivable_chunks` is always
empty. It does not call the Lua prototype or BeamNG. Existing composed maps and
normal launch behavior are unchanged.

For local Lua mock and source validation, run `./.venv/Scripts/python.exe
tools/run_tests.py --output generated/streaming-tests.json`; the existing runtime
tests execute Lua through pinned Lupa. Build AssetReader with
`dotnet build src/AssetReader/AssetReader.csproj -c Release` when validating the
native reader. This streaming milestone does not change AssetReader.
