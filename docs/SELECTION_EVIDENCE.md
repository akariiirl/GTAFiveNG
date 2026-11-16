# Local CodeWalker selection diagnostics

These tools query CodeWalker's selected dictionaries, not GTA's running engine.
Use the pinned checkout from BUILD.md. No filename, timestamp, or alphabetic
priority is inferred. Outputs contain local game provenance and stay ignored.

```
dotnet build tools/SelectionEvidence/SelectionEvidence.csproj -c Release
dotnet tools/SelectionEvidence/bin/Release/net8.0/SelectionEvidence.dll GAME_ROOT NEW_EVIDENCE_JSON
python src/selection_diagnostic.py NEW_EVIDENCE_JSON SNAPSHOT/inventory.jsonl road.ybn
```

The probe calls `GameFileCache.InitDlcList`, `InitActiveMapRpfFiles`,
`InitGlobalDicts`, `InitMapDicts`, `InitArchetypeDicts`, `InitManifestDicts`, and
`InitGtxds` from the installed pinned assembly. This reads archive tables and
archetypes; it does not repeat the native XML catalog bootstrap. It exports
selected DLC, setup order, active mounts, nested patch mappings, resource hash
dictionaries, individual archetype owners, texture parent hashes, assembly hash,
and errors. Reflection intentionally fails if the pinned API changes.

`InitMapDicts` overwrites YMAP/YBN hash entries while traversing active map RPFs.
`InitGlobalDicts` builds visual and texture dictionaries from all RPFs.
`InitArchetypeDicts` builds both YTYP and individual archetype dictionaries from
all RPFs with DLC enabled. Archive membership alone is insufficient: multiple
mounts can contain candidates, and replaced archives can leave names absent.
Use the resulting dictionary entry, not a manually reconstructed ranking.
An absent dictionary name is not proof that GTA never loads it.

The local 2026-11-16 probe selected 27 of the 47 previously relevant conflicting
metadata names and left 20 absent from its map dictionary. It selected the
patchday3ng owner for the previously duplicate `v_lev_doors.ytyp`. Six other
YTYPs failed CodeWalker's archetype initialization despite successful raw XML
catalog exports. They were outside the selected prototype; errors are retained.
Never interpret zero raw catalog decode errors as zero archetype-loader errors.

`selected_region.py ROOT NEW_WORKSPACE --evidence EVIDENCE_FILENAME` is a bounded
South Central/Koreatown/downtown diagnostic planner. It searches 100 m cells near
the existing prototype, checks HD placements, uses individual archetype hashes,
and emits exact resource tasks with scoped texture ancestry and selected YBNs.
It verifies cached metadata hashes and refuses missing required visual owners.
It does not establish map activation flags, interiors, time-dependent variants,
GTA runtime fidelity, or completeness of resources beyond the selected cell.
Do not interpret embedded-texture verification pending as a passed texture check.

After the existing reader executes tasks, `prepare_selected.py ROOT WORKSPACE`
verifies every receipt and creates a separate sanitized XML view, preserving raw
exports. Hash-only text is replaced only when its known name is unique. Conversion
reports must still be inspected for unsupported/skinned models and texture misses.
No AllowMissing switch is used by these diagnostics.

`compare_collision.py EXPORTED_YBNS NEW_REPORT_JSON` compares world-space meshes
including composite transforms. Geometry sets round coordinates to five decimals
and ignore winding; triangle counts retain duplicates. Height samples use near-
horizontal triangles and report missing XY hits separately. This is neither
exhaustive topology equivalence nor runtime precedence evidence.

For the six local road candidates, the two older freeway exports were identical;
patchday27ng removed one triangle. Base sp1_rd_7 differed from the identical
patchday1ng/patchday2ng pair, with 52,396 common rounded triangles. The dictionary
selected patchday1ng for both names. Combining all versions would duplicate
overlapping surfaces. The real prototype uses only selected dictionary entries.

BeamNG 0.40 creates `current` below the requested `-userpath`. Put the package in
that isolated directory's `mods`, and instrumentation under `current/lua`, after
verifying the actual profile path. Complete first-run privacy choices manually.
Preserve every ZIP and log. Do not use a normal BeamNG profile for this test.
