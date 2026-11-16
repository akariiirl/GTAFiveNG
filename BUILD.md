# Setup, build and test

Commands below use PowerShell from the repository root. The tested environment was Windows, GTA V Legacy, BeamNG via Steam, .NET SDK 8.0.428, Python 3.12.14 and NumPy 2.3.5. Cloud/Linux execution of the reader and game integration has not been validated. A fresh checkout has neither game assets nor the ignored dependency checkout, SDK, caches, or builds. Network access is required to restore dependencies.

## Dependencies

Install Git, .NET SDK 8 (8.0.428 was tested), and Python 3 with NumPy (2.3.5 was tested). On Windows, create a project-local Python environment, then use it in place of the machine-specific `tools/python.ps1`:

```powershell
py -3.12 -m venv .venv
./.venv/Scripts/python.exe -m pip install numpy==2.3.5
git clone https://github.com/dexyfex/CodeWalker.git vendor/CodeWalker
git -C vendor/CodeWalker checkout 485d56bec00262ed7fa472261cce7bbc6202b96e
dotnet restore src/AssetReader/AssetReader.csproj
dotnet build src/AssetReader/AssetReader.csproj -c Release --no-restore
./.venv/Scripts/python.exe -m unittest discover -s tests
```

The exact clean setup above is a proposed reconstruction, not yet verified on a fresh machine. CodeWalker.Core references NuGet dependencies including SharpDX 4.2.0; restore may require network access. Existing `tools/python.ps1`, `tools/launch_test.ps1` and `config/project.json` contain this machine's paths. `config/project.json` is descriptive; check code arguments rather than assuming it drives the converter. The Python and build paths above avoid modifying those working scripts.

## Local conversion

Requires a legally obtained local GTA V Legacy installation, sufficient free storage, and .NET/CodeWalker. Replace the example path and choose **new**, empty output directories. Reader's output must be outside the GTA installation. The following recreates the documented small-region workflow, not neighborhood03 exactly:

```powershell
$gta = 'D:/SteamLibrary/steamapps/common/Grand Theft Auto V'
$reader = 'src/AssetReader/bin/Release/net8.0/AssetReader.dll'
$source = 'generated/source-new'
foreach ($filter in @('sc1_01','sc1_rd','cityeastrd','globalroads','sc1block01','sc1struc','sc1tram')) {
  dotnet $reader $gta $source $filter
  if ($LASTEXITCODE -ne 0) { throw "Reader failed for $filter" }
}
./.venv/Scripts/python.exe src/convert.py --source $source --output generated/new-build
dotnet $reader $gta $source '@generated/new-build/conversion_report.json'
./.venv/Scripts/python.exe src/convert.py --source $source --output generated/new-build-resolved
./.venv/Scripts/python.exe src/validate_surfaces.py generated/new-build-resolved
./.venv/Scripts/python.exe src/package.py generated/new-build-resolved builds/new-checkpoint/los_santos_fazes.zip
```

Review `errors.log`, conversion report and missing assets; reader can log individual extraction failures without failing the entire run. Extraction filters are incomplete and cache invalidation is not fully proven. Packaging refuses an existing ZIP; do not overwrite checkpoints. Reproduction depends on game version and resource availability and is not a promise of byte-identical results.

BeamNG validation requires a local installation and Steam; inspect `tools/launch_test.ps1` and adapt its hard-coded Steam path for the machine before use. It can stop a matching isolated project test instance and overwrite its profile's copied mod; choose a fresh profile. The ZIP and accompanying `.manifest.json` are required. Never target a normal user profile.

## Git and cloud

Review `git status`, `git diff` and `git diff --cached` before committing. `.gitignore` excludes the known large/proprietary paths and common secret types, but cannot detect every asset or secret. Review all staged files and history before creating a **private** GitHub repository; configure a remote only with user approval and never push without it. A cloud environment can develop and run source-only tests after dependencies are installed; conversion or BeamNG validation additionally requires supported runtime, licensed assets and separately configured access. Do not upload game assets, generated builds or credentials to the repository or cloud by default. Back up ignored checkpoints separately where authorized; a Git clone alone cannot restore them.

## Verified Linux cloud setup — 2026-11-16

Python 3.12.14 and .NET SDK 8.0.428 were used on a fresh Linux checkout.

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-cloud.txt
MPLCONFIGDIR=/tmp/los-santos-mpl .venv/bin/python -m unittest discover -s tests -v
git clone https://github.com/dexyfex/CodeWalker.git vendor/CodeWalker
git -C vendor/CodeWalker checkout 485d56bec00262ed7fa472261cce7bbc6202b96e
dotnet build src/AssetReader/AssetReader.csproj -c Release
```

Install SDK 8.0.428 first if absent (the official dotnet-install script supports a
user-selected directory). Clean reader restore/build succeeded with zero warnings
and errors. This proves compilation, not Linux archive extraction or key handling.
The pinned Python requirements include transitive dependencies. Tests use stdlib
unittest. CI runs Python tests and a separate reader compilation job; neither
requires game files. The PowerShell Python helper prefers `.venv`, then PATH.

With **local authorized exports**, the new incremental wrapper is:

```bash
.venv/bin/python src/region.py --source generated/source-new --workspace generated/regions-new --center -370 -1330 --radius 220
```

The source and workspace must be separate directories. Outputs are keyed by region
selection, all exported source bytes, all pipeline Python modules and map settings.
Each contains `build/`, `region.zip`, its package manifest, optional progress maps,
and `region-manifest.json`. Cache reuse hashes every output and structurally
validates the level. Tampered or incomplete outputs are preserved and rejected;
use a new workspace to recover. Changed inputs produce a new directory. This is
conservative whole-region rebuilding, not shared extraction or chunk caching.
Do not upload real exports to cloud. Keep using existing local conversion commands
when reproducing old builds. The wrapper does not invoke AssetReader, resolve all
missing resources, choose archive precedence, or provide bounding box selection.

Issue #2 dependency policy: optional `dependency-policy.json` beside exports accepts
`priorities: {"export.ydr.xml": 10}` (larger wins), `overrides: {"asset":
"pack.ydd.xml#member"}`, `txd_parents: {"child": "parent"}`, and
`textures: {"parent": {"texture": "relative-file.dds"}}`. Equal priorities remain
conflicts. `dependencies.texture_lookup` is a scoped lookup API with parent-cycle
and source-escape checks; conversion still uses its legacy flat DDS lookup. Do not
assume this policy is automatically generated from installed DLC metadata.

Read-only extraction planning from exported XML (exclusive output creation):

```bash
.venv/bin/python src/planning.py --source generated/source-new --bbox -500 -1500 -200 -1200 --chunk-size 256 --output generated/plan-new.json
```

Alternatively use `--center X Y --radius R`. The planner returns selected placement
asset names, chunk memberships, resolved export filenames and unresolved names.
`planning.reconcile(plan, source, previous)` verifies task bytes; pending tasks may
be retried by a future archive extraction adapter. It never writes source files.

Compare two existing conversion reports without overwriting earlier evidence:

```bash
.venv/bin/python src/reporting.py generated/build-before generated/build-after generated/comparison-new
.venv/bin/python tools/run_tests.py --output ci-synthetic/test-summary.json
```

Comparisons count resources/triangles, not geographic or gameplay completion.
Source fingerprints appear in the JSON. Progress maps additionally emit
`asset_density.png` (converted placements per bin, with unresolved placements).
CI uploads only original synthetic comparison PNG/JSON and a test-result summary.

Scoped texture conversion is opt-in: set `"scoped_textures": true` in the export
policy, map `asset_txds` from archetype names to dictionary names (or supply YTYP
`textureDictionary` fields), and provide the `textures` and `txd_parents` maps above.
Child dictionaries override parents. Output texture filenames are derived from
source-relative paths so identically named textures in different dictionaries do
not overwrite each other. Missing dictionary metadata stays unresolved; scoped
mode never silently falls back to an unrelated flat DDS. Default mode preserves
existing flat exports. Actual game dictionary metadata extraction remains deferred.
