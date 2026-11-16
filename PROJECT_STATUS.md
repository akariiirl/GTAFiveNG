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

### Issue #2 B — exported-source planning

Phase A PR #3 passed GitHub Actions (runs 43901240885 and 43901222383).
Added read-only radius/bounding-box planning, deterministic geographic chunk IDs,
source content fingerprints, per-chunk dependencies and verified/pending task
reconciliation. 18 source-only tests pass. Plans do not execute extraction, cover
world-space collision bounds or replace the existing radius converter. Neighboring
plans identify shared names but do not yet share converted geometry on disk.

### Issue #2 C — offline residency/visibility foundations

Added content-hash resource sharing, reference counting, unloading, atomic failed
transitions, deterministic residency manifests, geographic visibility selection and
LOD threshold selection. 21 synthetic tests pass. Payload budget tests cover missing,
corrupt and oversized resources; the budget excludes Python/loader overhead and
cannot bound allocations performed inside a supplied loader. This is an offline
model, not BeamNG runtime integration, geometry simplification or proven streaming.

### Issue #2 D — collision/transform reliability

Planning PR #4 and corrected residency PR #5 passed both GitHub Actions runs.
24 synthetic tests pass after mirrored collision winding/NumPy truth-value fix,
finite quaternion and primitive argument validation, and no-collision diagnostics.
Surface tests show missing hits without collision and aligned hits with an original
synthetic road/collision triangle. These are sampled geometry checks, not verified
drivable territory. Actual neighborhood03 collision miss remains unassessed locally.

### Issue #2 E — reporting and cross-platform CI

Collision PR #6 passed both GitHub Actions runs (43902148783, 43902129083).
Added immutable count-comparison PNG/JSON with source report hashes, signed deltas,
selection comparison and explicit unknown island/driving coverage. Progress maps
now include placement-density PNG and missing texture names/dependency provenance
in summaries, without assigning texture misses invented geographic footprints.
25 Linux tests pass. CI now tests Python on Windows and Linux and uploads only an
explicit allowlist of synthetic comparison/test evidence; reader compilation stays
on Linux. CI outcomes for the new matrix must be checked before claiming Windows
verification. No actual game map images or game-derived assets were uploaded.

Roadmap remains partial: scoped texture lookup is an API pending converter wiring;
DLC mount metadata still requires an extraction adapter; plans don't extract game
archives; residency/LOD are offline policies, not engine streaming or simplified
meshes. No resource/performance benchmark beyond synthetic tests is claimed. Credit
usage/balance remains unavailable, so preserving the exact 60-credit reserve cannot
be certified. This bounded pass stops after CI review rather than launching large,
unmetered integration work. PRs #3–#7 are stacked; review/merge in numerical order.

### Issue #2 A follow-up — scoped textures reach packaging

Opt-in scoped texture conversion now binds archetype TXDs, follows parent lookup,
uses distinct output paths for conflicting texture names and reports missing or
conflicting dictionaries. Legacy flat-texture behavior remains default. 26 tests
pass locally, including two drawables using different original synthetic DDS
payloads under the same texture name, inherited lookup and structural packaging.
Windows CI initially exposed a short/long temp-path assertion mismatch in PR #7;
the assertion now compares canonical paths and CI is rerunning. No game-derived
texture metadata or appearance has been validated. This supersedes the earlier
note that the scoped lookup API was not wired into conversion.

### Issue #2 B follow-up — bounding-box conversion

User reports 430 credits remaining after 17 used; 60-credit reserve means 370 above
the reserve at that report. Tools still expose no live meter. Added shared region
selection for planner, converter, cache IDs, progress statistics and comparisons.
Bounding-box CLI now builds/packages/maps actual selected synthetic inputs. 28 tests
pass locally, including inclusive edges, invalid/mixed selections, planner/map
counts, box origin/size and cache reuse. Legacy radius calls/reports remain supported.
Selection includes whole placed assets; no triangle clipping or gameplay validation.
This supersedes the earlier limitation that bbox was planning-only.

### Budget correction and shared-cache milestone

Latest user balance: 426 credits for the entire project. Original limits apply:
maximum 180 cloud credits total, preserve 276 for local development. At that report,
at most 150 additional credits could be spent while preserving 276. This supersedes
the 60-credit-only reserve calculation above; no live credit meter is available.

Added opt-in persistent drawable conversion caching between regions. Thirty-one tests
pass locally: neighboring cache reuse, byte-identical cached/uncached ZIP/report,
source invalidation, immutable entry conflicts and corruption rejection. Entries
include replayed material/texture/report effects; source exports remain read-only.
Cache is local/ignored with generated workspace, fully loads individual JSON mesh
entries, and does not cache collisions or establish runtime streaming. PR #9 bbox
CI passed Windows/Linux tests and Linux reader compilation. No game assets used.

## Autonomous integration/extraction milestone — 2026-11-16

PRs #3 through #10 merged sequentially with passing checks and merge commits; all
were retargeted to master in dependency order. Integrated master 050fef2 matches
the final stacked source tree, and its 31-test suite passed locally. No protections
or checks bypassed. Future milestones are authorized for clean automatic merging.

Added Python region-to-exact-extraction planning and AssetReader --tasks protocol:
YMAP/YTYP metadata, YDR/YDD/YFT requests, TXD parent closure, supplied archive
priorities, known-bounds YBN selection, deterministic naming, missing/conflict
reports, SHA-256 source/output receipts and resume verification. Native task mode
recurses archives, isolates texture outputs, rejects failed/missing tasks with a
nonzero exit, and preserves changed/corrupt/incomplete outputs. Python validates
receipts and emits scoped texture policy for conversion. Legacy modes retained.
33 Python tests pass; .NET build and native/Python synthetic task-protocol smoke
check pass. Seed placement/type metadata is required; hash-only references, actual
mount metadata and native collision-bounds inventory remain gaps. No actual game
archives or keys were accessed. Current balance remains last user report 426;
original 180 cloud total/276 local reserve applies, with no live usage meter.

### Shared collision/texture cache and measured synthetic memory

Extraction PR #11 merged after Windows/Linux Python tests, native build and protocol
smoke check passed; master includes merge 7de401e. Extended shared caching to
world-space collision meshes with per-region translation and binary normalized DDS
payloads. Cache hits stream verified texture payloads; duplicate outputs share one
blob. Opt-in repair quarantines invalid entries without deletion; default remains
fail-fast. Cached/uncached synthetic builds including visuals, collision and texture
produce identical ZIPs and conversion reports. 35 tests are covered by the suite.

One Linux Python 3.12.14 synthetic 1024x1024 alpha-DDS observation: cold 0.05654 s /
13,633,380 traced Python peak bytes; warm 0.01412 s / 2,103,635 bytes. Input 1,048,704
bytes, output 4,194,432 bytes; outputs identical. Single observation, not RSS, real
asset workload, streaming or BeamNG performance. Benchmark script is reproducible.
