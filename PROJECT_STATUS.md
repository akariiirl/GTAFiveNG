# Project status — 2026-11-16

Read this first. Project Los Santos is a partial GTA V Legacy to BeamNG conversion prototype, not a complete map. Existing source changes were already uncommitted when this handoff began; retain them. `git status` is authoritative. Older PROGRESS.md, NEXT_STEPS.md, START_HERE.md and CONVERSION_REPORT.md describe earlier checkpoints and can conflict with current code.

## Verified in this workspace

- Git exists, branch `master`; `c467cde` was the latest commit before this handoff, and no remote was configured when inspected. This handoff preserves newer source and test changes, including `src/primitives.py` and `src/validate_surfaces.py`; check `git status` and history for their checkpoint state.
- On 2026-11-16, `./tools/python.ps1 -m unittest discover -s tests` passed 7 tests. The local .NET 8.0.428 Release build of AssetReader succeeded with `--no-restore`; NU1900 warned that NuGet vulnerability metadata was unreachable. This does not verify a clean restore.
- Local `builds/neighborhood03/los_santos_fazes.zip` has a package manifest reporting 6,142 scene objects, 991 shapes, 3,554 materials, 2,033 files, zero structural dependency errors, 284,102,536 bytes, SHA-256 `ce4ffb926f8de78e0ca47e7ca51d2b5e09ba6269bbf9b730c32fd9505d12e4fb`. These are recorded manifest results, not a fresh hash verification. Earlier checkpoint01–03 packages remain locally preserved. All builds are ignored and will not travel in Git.
- `generated/neighborhood03/conversion_report.json` records radius 800 m, 6,066 visual instances, 923 drawables, 1,431,038 collision triangles, 133 missing assets and 38 missing textures; its `in_game_verified` field is false. `surface_validation.json` records 1,510 of 1,511 sampled road points within 0.5 m of collision, with one missing hit. Sampling is not exhaustive.
- Local BeamNG telemetry exists at `generated/beamng-neighborhood03/current/lsf_validation.json`, but has not been fully assessed for driving or visual quality in this handoff. Earlier evidence of loading does not establish a playable neighborhood. No reliable performance benchmark is established.

## Blockers and unresolved work

The precise extraction filters and sequence that produced neighborhood03 are not recorded completely; the older small-region recipe does not reproduce it exactly. Asset and texture resolution remains incomplete; inspect the local report. Collision sampling has one unresolved miss; visual appearance, sustained driving, coverage and performance need verification. YTYP/YDD/YFT resolution, texture dictionary scoping, DLC/update precedence, detail chains and streaming need further investigation. Current code adds sphere/capsule/cylinder collision and source fingerprinting, but their coverage and cache invalidation are not fully verified. Do not rely on older claims that those changes are absent or that the cache merely checks file existence.

## Exact next steps

1. Check `git status` and history before starting work. Do not stage ignored proprietary outputs. Back up ignored checkpoints separately to authorized private storage if the user wants them on another machine.
2. Inspect the neighborhood03 report, surface miss and complete BeamNG telemetry; visually inspect and drive the existing local build with an isolated profile. Record evidence, or explicitly record what could not be checked. Avoid overwriting the profile or packages.
3. Resolve the missing road collision hit and highest-impact assets/textures; add targeted tests. Record extraction inputs and exact commands for any new build, use fresh directories, then package under a new name.
4. For a new computer or cloud environment follow BUILD.md, restore the pinned external dependency, and run source-only tests before attempting a conversion. Cloud conversion also requires separately provisioned authorized local game assets; repository checkout alone is insufficient.

Update this file after each major development milestone, including commands, results and remaining uncertainty.

## Cloud milestone — 2026-11-16 (base dbcd1e9)

Fresh Linux checkout; no Windows files, game installations, existing generated
builds, desktop or game-derived assets accessed. Prior checkpoint remains intact.

- Phase A: pinned Python 3.12 dependency environment and source-only GitHub Actions
  added. Clean .NET 8.0.428 restore/Release build with CodeWalker
  `485d56bec00262ed7fa472261cce7bbc6202b96e` passed (0 warnings/errors).
  Portable Python helper now uses project venv or PATH.
- Phase B: 13 unittest tests pass, including original synthetic XML/triangle fixtures,
  inclusive radius selection, missing asset/texture reports, reproducible packaging,
  structural missing-shape detection, cache invalidation/tampering, and progress PNG
  generation with immutable earlier milestones. This is useful coverage, not the
  comprehensive requested fixture matrix; archive extraction is not exercised.
- Phase C partial: YTYP aliases for standalone YDR/YFT, explicit duplicate diagnostics,
  unresolved alias/dictionary reports. Automatic archive precedence, YDD member
  resolution, texture inheritance and safe incremental extraction remain pending.
- Phase D partial: source-export region CLI, deterministic IDs, content-addressed
  conversion, persistent verified manifests, validation/package/map orchestration.
  Bounding boxes and automatic extraction remain pending.
- Phase E pending: geographic chunks, cross-chunk assets/dependencies, shared cache,
  LOD generation and collision complexity analysis. Current cache rebuilds whole
  regions conservatively when any input or pipeline source changes.
- Phase F partial: existing maps run automatically per region, synthetic coverage
  and preservation tested. Comparison PNGs, density/texture diagnostics and
  build-to-build summaries remain pending. No GTA coverage or driving claims added.

Credit consumption is not measurable/cappable through these tools. No credit
purchase or agents were used; further large uncertain work was avoided. Actual
remaining balance and compliance with the numeric allocation cannot be certified.

Next PC session: preserve neighborhood03 and profiles; restore dependencies using
BUILD.md; run the 13 tests; inspect prior missing collision sample and telemetry;
run the region CLI against authorized local exports in a fresh workspace; inspect
new dependency_resolution and missing resource lists; compare with the old package;
then load using an isolated BeamNG profile and record package-hash-matched visual,
collision, driving and performance evidence. Do not expand extraction broadly until
archive precedence, YDD members and texture scoping have targeted local fixtures.

Publication blocker: local development commit `4ccb77a` was created and the working
source checks passed. Both Git push and the connected GitHub create-branch API
returned HTTP 403 (API: Resource not accessible by integration). No remote branch
or PR was created. Repository contents/actions write permission is needed before
`git push -u origin dev/cloud-foundation-regions` and opening a PR against master.

Publication update: Git push subsequently succeeded on 2026-11-16. The development
branch `dev/cloud-foundation-regions` is now saved on origin; the earlier HTTP 403
publication blocker is resolved for Git push.

## Issue #2 — dependency milestone (2026-11-16)

Started from merged master 3ee47ba. Added YDD member conversion, fixed-point YTYP
alias chains, explicit exported-filename priority/override policy and candidate
provenance. Added scoped parent-TXD lookup API; it is not yet wired into material
conversion, which retains legacy flat DDS behavior. Synthetic tests exercise
conflicts, priorities, chains/cycles, YDD conversion and texture scope/escape checks.
Real archive mount order, hash-only member names and actual texture fidelity remain
PC validation/integration work. No licensed assets accessed. Credit meter unavailable.
