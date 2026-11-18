# Project status — 2026-11-16

## Terrain texture recovery and native 3D map inspection — 2026-11-17

- Preserved Probe 09 and terrain-sprint-03. The separate terrain-sprint-04 ZIP is `D:\GTAFiveNG-local\master-integration-20261116\generated\real-integration-01\terrain-sprint-04\los-santos-terrain-stream.zip` (2,809,844,777 bytes; SHA-256 `074c1326d7a6843a5e9b6921bf7d91d523bd109d21817cabb8967a8b3c6dc234`). The local `terrain-report.json` and `integrity.json` contain the full diagnostics.
- For terrain archetypes lacking a texture dictionary, the resolver now considers only original YDR donors with the exact four-layer shader and sampler names, and accepts a texture only when donor file hashes agree. This recovered all ten previously missing terrain texture names. Triangle material choice now integrates GTA's bilinear vertex weights across the triangle. It still selects one dominant source layer per triangle; pixel-level four-layer blending is not implemented.
- The new ZIP textures 231 shapes and 306,656 terrain triangles, versus 227 shapes and 306,381 triangles in terrain-sprint-03. It adds 208 source textures/materials. ZIP CRC, all references, all stream manifests and all 6,641 collision shape entries passed the integrity check. One unsupported shader or vertex-layout category remains. No source-backed ground-gap or seam repair was proved.
- One isolated BeamNG 0.40.5 Direct3D12 session loaded the package and showed a controllable-spawn scene, the road-level camera, and BeamNG's built-in 3D big map. The game log records level load at 20.52 s, loading UI unloaded at 29.06 s, and the spawn cell ready at 30.46 s of game runtime. The latest streaming status records five ready cells and 6,343 objects at GTA (-407.97, -1537.84). No driving or terrain physics test was performed. Native-map and terrain camera captures are under the ignored `generated/terrain-sprint-04-evidence/` directory. The big map shows only loaded geometry, with large pale ground patches and empty blue surrounding space; a complete island map is neither implemented nor claimed. The screenshot is an aerial view from the native 3D map, as requested. The game was closed normally after this one session.
- Next terrain task: trace the pale ground material or missing-surface sources visible around the freeway, then implement source-backed geometry or material fixes in isolated cells. Validate any collision and seam changes in BeamNG before treating them as repaired.

## Layered GTA terrain material sprint — 2026-11-17

- The original 47-cell streamed Probe 09 ZIP remains preserved. A new local terrain ZIP at `D:\GTAFiveNG-local\master-integration-20261116\generated\real-integration-01\terrain-sprint-03\los-santos-terrain-stream.zip` is 2,809,844,158 bytes (SHA-256 `194d3b1cb78d2d18863294d7367d8c22c3f2ebb83991c3cca17a2c031a214500`). Its separate local `terrain-report.json` and `integrity.json` record the full results. No GTA assets or packages are tracked by Git.
- Pinned CodeWalker terrain shader logic and original GTA Colour1 vertex weights now select one original source layer texture per terrain triangle. The new build textures 306,381 triangles in 227 visual shapes and adds 208 material definitions and 208 source textures. The converter applies the same rule to future builds; a separate package upgrader handles preserved streamed builds without reconverting geometry. It inspected 46 prepared cell folders and used only matching active YDR sources with consistent scoped texture bindings.
- One package integrity check passed: full ZIP CRC, all material/texture references, all 47-cell stream manifests unchanged, and all 6,641 collision shape entries unchanged. Ten texture names remain unresolved in available scoped exports; one unsupported shader/vertex layout category remains. Original elevations, meshes, placement and collision are preserved. Four-layer blend interpolation is approximated by dominant triangle layer, and missing terrain surfaces, seams, coastlines and road-to-ground transitions have not been measured or repaired.
- Focused terrain regression tests passed (3 tests). The new package has **not** been opened in BeamNG. A prior Steam offline cloud-sync warning made an unattended launch unsafe, so visual appearance, terrain collision response, loading time and FPS for this build are pending. The next terrain task is one safe in-game visual/physics session followed by targeted work on the listed unresolved textures and measured ground gaps.

## Sprint 02 collision and guarded driving checkpoint — 2026-11-17

- A read-only audit of the preserved 47-cell composition compared collision objects by source identifier, all non-position Collada XML (including triangle topology, winding and material bindings), world-space positions within an absolute 0.00002 m tolerance, and collision object properties. It proved all 4,946 repeated objects equivalent: 6,641 collision objects reduce to 1,695 distinct objects. Ten `fwy_01_4.ybn` copies also matched. The new `src/compose.py` policy performs this conservative deduplication for future compositions; focused synthetic equivalence tests pass. The original composition and packages remain unchanged.
- A separate Probe 06 streaming ZIP rewrote only the 47 cell manifests and stream index using that proven mapping. It passed full ZIP CRC and SHA-256 checks. At an isolated controllable spawn, the loading overlay ended at 38.13 s of game runtime; five initial ready cells held 6,343 stream objects. A later snapshot showed 3.35 GiB BeamNG physical memory and 4,262 MiB total GPU memory use. Probe 05 ended its overlay at 35.86 s, but cache states differ, so no load-time improvement is claimed.
- Original `fwy_01_4`/`fwy_01_5` YBN geometry shows the freeway lane center moving east about 11 m between GTA Y -1540 and -1490. A test spawn at GTA X -401 struck a real guardrail and was rejected; no source collision was removed. A guarded low-speed run from the previous safe spawn followed the measured guardrail centers continuously for **83.89 m** through cells `-2_-7` and `-2_-6`, with zero vehicle damage and no sampled streaming pause. The maximum sampled speed was 7.12 m/s. The minimum sampled FPS was 9.97 during initial activity; later samples were above 253 FPS. At the end, eight cells and 9,540 objects were active, BeamNG used 3.68 GiB physical memory and total GPU use was 4,428 MiB. This is an actual in-game drive, not completion of the 2,196.07 m route.
- The preserved local evidence is under `D:\GTAFiveNG-local\master-integration-20261116\generated\real-integration-01`: `streaming-probe-06` and `streaming-probe-09` contain separate ZIPs, isolated logs, real screenshots and drive telemetry; `collision-dedup-audit-sprint02.json` is under the ignored C: `generated/` directory. Probe 09 package SHA-256 is `662c4523e9dbcf693f49c295d5944605ceed5bf273b56e0536465a8994628b1a`. The corrected drive summary is `streaming-probe-09/drive-summary-corrected.json`.
- The guardrail-pair tracer found no matching right boundary at GTA Y -1450 at its sampled road height in the 15 already extracted, spatially overlapping YBN resources. The next task is to derive a defensible lane continuation from original GTA navigation/visual-road data, preflight its road and collision coverage, then resume guarded driving. Terrain geometry/material changes, high-speed/return travel, and the full cross-city route remain unverified. No live credit meter is available.

## Cross-city route and terrain checkpoint — 2026-11-17

- Saved a separate Probe 05 and a 2,196.07 m offline visual-road candidate route through 11 technical cells. In-game testing confirmed a north-facing, four-wheel-supported spawn, but a bounded drive hit a freeway divider after 26.16 m of zero-damage travel. No cross-city drive is verified.
- Exact YBN comparisons reproduced the hit in base, patchday1ng and patchday27ng versions. Ten composed copies of `fwy_01_4.ybn` geometry agree within 0.00001 m, exposing a collision deduplication defect for the next build. Existing original GTA ground meshes already convert; the coarse mainland min/max heightmap cannot safely replace them. See `docs/CROSS_CITY_CHECKPOINT_2026-11-17.md` for evidence, local paths and limitations.

## Experimental streamed 47-cell BeamNG run — 2026-11-17

- Reused the existing 47-cell converted asset library and 256 m manifests; no GTA extraction or conversion was repeated. `src/lsf_stream.lua` creates and deletes shared `TSStatic` objects by cell, preloads neighbors from measured player motion, rebuilds collision, pauses before an unready cell, and enforces a 20,000-object cap. BeamNG.Earth's implemented object lifecycle and collision APIs were audited in `docs/BEAMNG_EARTH_AUDIT.md`; no Earth source was transplanted.
- In an isolated Steam BeamNG profile, Probe 04 dismissed its loading overlay at 31.716 s of game runtime and finished the 1,003-object spawn cell at 58.921 s, then released its pause. Eight nearby cells had 10,229 active objects. A low-throttle, zero-damage drive crossed the `-2_-6`/`-2_-7` boundary. The preserved static 47-cell warm-load measurement was 183.1 s, but the sessions had different cache states and this is not a controlled cold-load comparison.
- Teleporting under a separate safety pause from spawn to `-2_-4`, back, then to `0_-6` exercised real scene activation/deletion. The previously budget-blocked `1_-7` cell reached ready with 13 cells, 19,243 objects, and 7,785 cumulative deletions; a unique unloaded collision object was absent from the live scene. Returning reduced active objects to 16,517 and BeamNG physical memory from 7.16 to 6.73 GiB. Total GPU use stayed near 5.8 GB, so full VRAM release is unproven. Initial eight-cell physical memory was 5.35 GiB; prior static 47-cell memory was about 18.78 GiB. A stable-scene CPU sample used 1.73 logical-core equivalents. Stream status reported about 269 FPS at 1280x720, not a route average.
- The local Probe 04 ZIP passed full CRC and resides under `generated/real-integration-01/streaming-probe-04` in the D: integration workspace; its SHA-256 is `e8c76461249deaf0b43449ec47c3b85233bc31a2ec853b4dbc78593bbdb091d4`. The in-game report, logs, and screenshots are local-only. The normal BeamNG profile, working 23-cell/47-cell ZIPs, caches, and original game installation remain untouched.
- The native big map displayed the loaded geometry but not unloaded converted cells, despite the existing waypoint bounds. High-speed transitions, long repeat driving, full VRAM eviction, distant LOD, and the user's earlier north/west invisible border remain unverified. A short unsteered ramp crash was consistent with leaving a curved, collision-supported road; no collision mesh was removed. The next work is a measured unloaded-territory map layer and longer driving/memory tests before labeling this streaming system production-ready.

## Playable connected corridor — 2026-11-16

- Reused the completed 297,372-resource catalog and CodeWalker selection evidence.
  Fixed anchor-only selection by transforming archetype bounds; filtered prepared
  YMAPs retain exactly the selected entities. Collision planning now covers the
  full selected visual bounds. Assetless metadata is reported explicitly rather
  than treated as a missing drawable. No bootstrap or game modifications.
- Sequential local processing saved the first improved package before expansion.
  Corrected stage01 reused 508 exports and added 61 collision resources; cache
  replay recorded 1,071 hits and 61 misses. Stage02 recovered 569 receipts from
  1,107 tasks and recorded 1,616 cache hits / 804 misses. All extraction receipts
  were verified. Frozen local source, logs, progress, locks and completion hashes
  support detached execution; a completed-job resume verified packages and skipped
  extraction/conversion. The bounded two-stage job is completed.
- The 400 x 600 m stage selected 3,928 HD entries and emitted 3,365 visual
  placements, 632 drawables, 3,695,507 visual triangles, 3,223,930 collision
  triangles and 1,103 textures. The 563 entries not emitted include unsupported,
  assetless and duplicate entries; this is not a claim of complete scenery.
  Five texture names remain unresolved, and layered ground shaders still appear
  as white patches. Structural validation passes. Whole-road offline sampling:
  15,094 of 15,122 within 0.5 m; 28 exceptions remain explicitly reported.
- Preserved a smaller package with 269.041 m of in-game movement and 268 matching
  visible-asphalt/collision samples. The larger package reached its route target
  after 531.573 m, excluding the first two seconds of initial vehicle setup.
  All 535 later vehicle-center samples match non-decal road/road-edge triangles
  and runtime ground rays within 0.5 m. A strict asphalt-only audit initially
  missed one point; exact source inspection identified IM_Road_edge_001 at that
  point, and the separate corrected audit preserves the initial result. This is
  sampled route evidence, not exhaustive tire-contact or whole-map validation.
- At least one four-way intersection was visually inspected and traversed; the
  smaller test also exercised a turn. No inventory-wide intersection pass or
  traffic support is claimed. Game screenshots show recognizable streets,
  buildings, signs and the freeway, with incomplete map edges and ground materials.
  Desktop capture overstates brightness compared with the game's own PNGs.
- Latest tested package (183,759,429 bytes):
  D:/GTAFiveNG-local/master-integration-20261116/generated/real-integration-01/
  corridor-drive-03/neighborhood-daylight.zip. Its hash-checked manual launcher is
  launch-playable.ps1 beside it. Telemetry and nine screenshots are under
  profile/current; drive-audit-road-surfaces.json records the 531.573 m audit.
  The job/config/resume proof and both original packages remain in sibling
  playable-corridor-02. Previous prototypes and neighborhood03 remain preserved.
- Focused source regressions: 26 passed, then the expanded five-test corridor
  suite passed. CI must pass before merge. Next focused defect: implement the
  actual layered ground material bindings responsible for white terrain patches;
  do not substitute invented geometry or claim the entire exported region passes.


## First real CodeWalker-selected road prototype — 2026-11-16

- Reused the 297,372-resource native catalog without bootstrap. Actual pinned
  CodeWalker dictionaries selected 27 of the original 47 relevant metadata
  conflicts; 20 names were absent from its active map dictionary. The duplicate
  v_lev_doors owner is patchday3ng. This is CodeWalker evidence, not verified GTA
  runtime precedence. Six unrelated YTYP archetype-initialization errors remain
  in the probe, distinct from the zero raw catalog XML errors.
- Compared all six previously exported road collision candidates. Older freeway
  copies were identical; patchday27ng removed one of 9,371 triangles. Base sp1_rd_7
  had 54,460 triangles versus 54,412 in the identical patchday1ng/2ng copies;
  52,396 rounded triangles were shared. Roadlike height samples differed by at
  most 0.000235 m with one missing XY hit. CodeWalker selected patchday1ng for
  both resource names; alternative versions were not combined.
- A bounded 463-map search found 26,936 HD placements. Selected the 100 m cell
  [-400,-1500,-300,-1400], with 159 HD placements and two actual road placements.
  All 152 exact extraction tasks have verified receipts. The new build converts
  111 visual placements, 53 drawables, 132,420 visual triangles, 427,502 collision
  triangles and 146 textures. Eighteen unsupported model names account for 48
  omitted placements. No missing texture names or texture-resolution diagnostics
  remain. Repeated placement reasons had caused embedded-texture parent cycles;
  the fix preserves the original parent and rejects conflicting parents.
- All 1,651 sampled upward visual-road triangle centers have collision within
  0.5 m. Structural packaging passes with 225 files, 72 shapes and 172 materials.
  ZIP is 23,751,047 bytes; projected visual footprint is 0.009532 km². These are
  offline measurements, not proof of exhaustive collision coverage.
- New local package: D:/GTAFiveNG-local/master-integration-20261116/generated/
  real-integration-01/selected-prototype-03/packages/los_santos_codewalker_road01.zip.
  Build, progress PNGs, raw exports and isolated profile are sibling directories.
  Older checkpoints and game installations are preserved. No generated data is
  included in this commit.
- BeamNG 0.40.5 Direct3D12 loaded the level and spawned a pickup on the road using
  the RTX 4070. The screenshot shows overbright lighting and unfinished edges;
  visual fidelity is not passed. Thirty instrumented samples show 25.594 m net
  movement, 7.751 m/s peak speed, and a stable stop above collision. Screenshots
  show the vehicle leaves the visible road patch for collision-only ground; this
  is a partial drive, not a passed neighborhood or boundary-driving test.
  First observed process working set was 2,527,121,408 bytes; GPU-wide usage was
  3,196 MiB, not process-specific VRAM. The measured 265.28 game update calls per
  second are not rendered FPS. Raw telemetry and two in-game screenshots remain
  in the isolated profile's current directory. No rendered-FPS benchmark or
  regional-boundary drive is claimed.
- SelectionEvidence builds; 42 focused local source regressions pass. Full local
  discovery encountered sandbox hardlink restrictions and missing optional lupa;
  the focused suite was rerun outside the sandbox. CI remains authoritative for
  the complete synthetic suite. See docs/SELECTION_EVIDENCE.md for reproduction
  and the distinction between dictionary evidence and GTA runtime behavior.
- Exact next integration blockers: extend visual selection beyond placement
  anchors to cover the driving route, support the omitted skinned/fragment
  geometry, and correct lighting/material presentation before expanding. The
  297,372 catalog paths are unique after case/slash normalization. No required
  resource ambiguity remains for this explicit CodeWalker-selected prototype;
  matching GTA runtime activation/precedence remains unverified.


## CodeWalker nested-mount diagnostics — 2026-11-16

- The local CodeWalker probe reports 3,920 active archive mappings and 646 patch mappings, with zero logged errors. Some patches replace nested RPF archives, not individual entries. Comparing each of the 47 relevant metadata conflicts after applying archive-prefix patches still produced 26 with one candidate in the reported active archives, 20 with none, and one with two. This is diagnostic evidence, not proof of the running game's selection: never silently choose a candidate from this result.
- The missing cases include archive paths superseded by other virtual mounts; the duplicate includes simultaneously listed base and DLC archives. The pinned CodeWalker implementation also uses all RPFs for YTYP loading and does not establish GTA runtime precedence. A small 23 m region is being evaluated locally as a fallback. No new extraction, package or driving result is established at this checkpoint.
- `src/mount_diagnostics.py` compares normalized physical paths with explicit nested patch mappings, reports zero/one/multiple candidates, and rejects cycles, conflicting normalized mappings and error-bearing evidence. Synthetic tests cover archive substitution and unresolved cases. Local game-derived diagnostic files remain ignored and must not be uploaded.

## Local region conflict audit — 2026-11-16

- A completed 297,372-resource native catalog was reused without re-running bootstrap. A region-aware scan of the two adjacent 200 m boxes found 47 conflicting metadata names potentially relevant to the selection and 2,604 unrelated conflicting names. The local report preserves the candidates; no active mount order was inferred.
- CodeWalker reads DLC activation and setup order, applies patch mappings and content changes, and builds active RPF mounts. This is stronger evidence than filename order but the converter does not yet reproduce or export the complete active mount mapping. The 47 required conflicts therefore block extraction; no new package or BeamNG validation is claimed.
- Region selection now checks every YMAP candidate before discarding unrelated conflicts, includes YTYP candidates for selected archetypes including hash references, and verifies catalog XML hashes. A real exported YTYP contained invalid control-character references; these are removed only after hash verification. Explicit catalog reuse checks archive/reader modification times, not archive content hashes; files replaced while preserving timestamps require a fresh bootstrap. See `docs/LOCAL_EXECUTION.md`.
- Focused local controller tests passed; full CI and integration status must be checked separately. Next: derive and validate active mounts from the installed game's CodeWalker DLC setup and patch evidence, resolve the remaining required candidates, then resume exact extraction and inspect its diagnostics. Preserve all local outputs and game files.

## Predictive streaming cloud prototype (Issue #21, synthetic only)

- Added an opt-in offline scheduler using vehicle position, heading, speed and
  lookahead, plus dependency closure, load budgets, retained-chunk hysteresis,
  missing-dependency reporting and a collision inventory signal. `drivable_chunks`
  remains empty; no engine API or gameplay state is claimed.
- Added original synthetic tests for stopping/reverse/turn/fast motion, boundary
  selection, teleport, dependency failure, collision distinction and load pressure.
- Reproducible 1,200-chunk, 80-tick simulation: 26 peak active, 322 load operations,
  9,300,000 estimated payload bytes. This is a model estimate, not process/engine
  memory, performance or collision readiness.
- `tools/streaming_showcase.py` exports a self-contained responsive HTML page,
  static isometric PNG, SVG scheduler graph and JSON summary; all visuals are
  labeled synthetic. Run instructions and the two-chunk local test are in
  `docs/LOCAL_EXECUTION.md`.
- Pending full test/build/CI/PR verification. BeamNG.Earth-inspired ideas are
  implemented independently; no engine streaming API is asserted. Two-chunk
  vehicle behavior, actual collision loading, FPS/RAM and moving-origin behavior
  still require PC/BeamNG testing.

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

### Multi-region and streaming-package milestone

Cache PR #12 merged as adf13f9 only after all six push/PR checks passed. Automatic
review correctly blocked an earlier premature attempt while one run was pending;
no check/protection was bypassed. Added mixed radius/bbox batch conversion with
shared cache, deterministic chunk/shared-art indexes, package hashes, preserved
completion state, immutable manifests and per-region maps by default. Tests cover
neighbor reuse and synthetic interruption/retry without rewriting completed ZIPs.
Packaging streams source files and ZIP hashing in 1 MiB blocks; a regression test
confirms byte-identical results against the original writer. Suite has 38 tests.
Batch packages remain independent same-level variants, not a combined streaming
map. Actual mesh LOD generation, chunked geometry packaging, extraction bootstrap
metadata, hash-only linkage and game validation remain incomplete.

### Experimental visual LOD, collision budgets and synthetic map artifacts

Multi-region PR #13 merged as 165687c after all checks passed. Added opt-in visual
LOD preview generation outside packaged levels, preserving boundary/seam vertices
with orientation/empty fallback. Collision meshes are never simplified. Optional
collision triangle limits reject oversized builds with diagnostics, preserving
partial output instead of publishing incomplete physics. Forty tests pass locally,
including deterministic grid reduction, preserved boundaries, package equivalence
with previews and collision budget failure. CI now retains allowlisted original
synthetic coverage/density/collision PNGs and progress JSON in addition to test and
comparison evidence. No real game output is uploaded.

One 64x64 synthetic flat-grid observation: 7,938 -> 762 triangles at 4 m cell size,
0.03913 s, max vertex-to-cluster displacement 2.1213 m. This is not a Hausdorff bound,
quality approval or game performance test. Preview LOD remains unintegrated with
engine detail selection; it is deliberately excluded from gameplay packaging.

## Confirmed integrated handoff — 2026-11-16

PRs #3–#10 and new milestones #11–#14 are merged into master. Functional integration
head: 0f14a5e26f98d6b6f710ce987148834e6c019166. Post-merge master CI
43910964048 passed all 40 Python tests on Windows and Linux, Linux .NET AssetReader
build and native/Python task-protocol smoke check. CI contains allowlisted synthetic
map/comparison/test artifacts. Source commits now on master include f5a68b7
(extraction), 55f866c (collision/texture cache), a1dae8f (batches/streaming packages)
and d5c6a79 (LOD previews/budgets). No runtime/gameplay verification claimed.

Next highest-value cloud milestone: bootstrap placement/type metadata and inventory
collision bounds, then test source-version changes, receipt corruption and nested
archive selection with original synthetic protocol fixtures. Real GTA integration
still needs authorized local installation/keys; current extraction requires seed
YMAP/YTYP exports and supplied mount/TXD policy. Hash-only references remain partial.
Batch packages share a fixed legacy level ID and cannot be installed together;
composed-map packaging and runtime chunk streaming remain future integration.
Experimental LOD previews stay outside ZIPs pending visual/topology validation.

Standing automatic merge authorization and original 180/276 overall budget rules
are persisted in AGENTS.md. Latest balance remains user-reported 426, not a current
meter reading; session usage cannot be measured. Qualitative completion estimate:
meaningful source automation/scalability progress; no measured change in actual
converted/drivable territory and no defensible whole-project percentage.

## Final cloud preparation — native bootstrap milestone

Latest user budget supersedes prior allocations: 380 remaining out of 500, 120 spent,
preserve 320 for local work and target no more than 60 additional cloud credits.
No live usage meter; no enforcement/usage claim is made.
Native --bootstrap now discovers/export YMAP/YTYP metadata without previous XML,
inventories supported resource paths and transformed native YBN bounds, and retains
content-addressed snapshots with per-resource verified resume checkpoints. Full outer
archive SHA-256 plus reader/resource identity invalidates snapshots. Provenance is
recorded; mount order is not guessed. Hash-only reference strings remain diagnostic.
Native synthetic checks cover nested archive paths, child transforms, missing/invalid
bounds, hash diagnostics, decode-free resume and source invalidation. A malformed
synthetic Geometry child was corrected to a valid Box fixture; native checks pass.
Real GTA archive/keys and engine semantics remain unverified. Python collision planner
tests cover boundary intersection and invalid bounds. Legacy reader modes retained.

### Offline composition milestone

Native bootstrap PR #16 merged as 852ff8c after all CI checks passed. Added experimental
single-level composition with common origin, material/texture/shape deduplication,
stable object IDs, overlapping placement/collision deduplication and chunk membership
from geometry extents. One validated deterministic package replaces separate variants.
Tests cover neighboring synthetic roads, collision alignment/preservation, distinct
same-named texture payloads, reversed-input ZIP equality and verified resume after
adding diagnostics. Forty-three Python tests pass locally. Collision transforms
outside converter-native identity are rejected; exact canonical meshes deduplicate,
so old rounded exports can retain distinct collision shapes. Runtime remains unverified.

### One-command local entrypoint milestone

Composer PR #17 merged as e9df24d after all checks passed. Added Windows PowerShell
entrypoint and local controller for bootstrap -> explicit metadata precedence ->
exact extraction -> mixed region conversion -> composition -> collision/maps ->
hash-verified isolated testing handoff. Dry-run does not inspect game files or
create workspace directories. Interrupted extraction preserves partial data and
recovers verified receipts into a fresh attempt; region/composition partial outputs
are retained, completed handoffs verify/reuse. Strict default stops on dependency
uncertainty; AllowMissing is explicit and never a completeness claim. Original
synthetic integration simulates the reader and tests interruption/recovery through
an isolated package. Windows CI checks the PowerShell dry-run; Linux skips that test
when pwsh is absent. Actual native game decoding and BeamNG launch remain unverified.
PC-return commands and exact blockers are recorded in docs/LOCAL_EXECUTION.md.

### Isolated prefab/chunk prototype

Local workflow PR #18 merged as 7aa8a49 after Windows/Linux/native CI passed;
Windows specifically executed the PowerShell dry-run. Added a separate experimental
prefab export and Lua controller based on official prefab format/fields and public
Lua creation/FS/log references. Scene registration/deletion bindings remain guarded
and engine-unverified. Shared boundary objects have one owner with dependency closure.
Mock-adapter tests execute real Lua (pinned Lupa) for load/unload/reload, missing files,
cycles, budgets and cleanup failure retention. Export tests ensure normal ZIP bytes
stay unchanged and objects are not duplicated across owned prefabs. File estimates
and Lua heap are explicitly not engine/GPU memory. No automatic prototype activation;
normal local workflow/launch remains offline composition. Runtime research sources
and exact isolated experiment are in docs/RUNTIME_EXPERIMENT.md. Actual engine
loading/physics/memory/streaming still requires local testing.
