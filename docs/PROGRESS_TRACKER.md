# Visual progress tracker

Run from the project root:

```powershell
./tools/python.ps1 src/progress_maps.py generated/neighborhood03 --checkpoint neighborhood03
```

The four deliverables appear under `generated/progress_maps/`. Each invocation first creates an immutable timestamped milestone directory, then refreshes the four latest convenience files. Earlier images are preserved. Generated images and proprietary geometry remain ignored by Git.

For future conversion milestones, use `tools/validate_milestone.ps1 -Build generated/new-build -Checkpoint unique-name` to run surface checks, generate maps, then validate and package the level. Existing packages are never overwritten.

Dependencies are NumPy, Pillow and Matplotlib. This machine has Matplotlib in ignored `tools/python-packages`; install with `./tools/python.ps1 -m pip install matplotlib --target tools/python-packages` if missing.

Blue maps actual projected triangles from DAE instances, including placement, rotation, scale and the original GTA coordinate offset. Yellow dots are unresolved placements in the selected available source YMAPs. Red crosses mark documented failed surface samples. The heatmap compares rasterized visual and collision triangle projections. It does not establish height agreement or drivable coverage. Gray means no converted footprint evidenced; it does not imply all source objects are known there.

Geographic area is a rasterized union at 2 m resolution by default; overlapping floors count once. This is an approximation with edge and thin-triangle error, not a surveyed area or the selected circle's area. Asset completeness counts matching instances in the available selected YMAPs, not all assets in GTA V. Skipped skinned submeshes mean a matching asset can still be partial.

There is no authoritative full-island outline in the current exports. `world_progress.png` therefore explicitly shows the available geographic evidence and reports the missing world context. Whole-island completion remains null. `--boundary path.geojson` can draw a supplied Polygon/MultiPolygon in original GTA metre coordinates; it does not assume longitude/latitude or invent island dimensions. Even with a boundary, geographic percentages remain null until footprint clipping is implemented.

Green is reserved for build-matched driving evidence. Existing vehicle logs lack a package hash and include control anomalies; the tracker does not automatically attribute them to this checkpoint. Verified drivable area and its percentage remain null. A vehicle path alone would establish travelled centreline, not the width or completeness of a road. The legend explicitly says no verified drive evidence is attributed.

Known limitations: world outline unavailable; no automatic build-matched telemetry ingestion; no polygon clipping against a world boundary; sampled failures show points rather than inferred failed zones. These limitations are repeated in machine-readable summaries.

Cloud milestone (2026-11-16): `src/region.py` now calls the tracker automatically for
nonempty converted regions, storing maps alongside each immutable region build.
Source-only tests generate PNGs from an original synthetic triangle and verify
selected-instance counts, unknown island percentages and preservation of earlier
milestones. These images are test evidence only, not converted GTA territory.
No new actual Los Santos milestone image can be generated without local exports.
Comparison PNGs, asset density and build-to-build summaries remain outstanding.

Issue #2 additions: `asset_density.png` plots converted placement counts, with
unresolved placement markers. The subtitle gives the count of missing texture
names; no texture failure area is inferred. `progress_summary.json` includes those
names and dependency-resolution provenance. Existing three map PNGs are preserved.
`src/reporting.py BEFORE_BUILD AFTER_BUILD NEW_OUTPUT` generates immutable
`comparison.png` and `comparison.json` with counts, deltas, report hashes and whether
region selections match. These counts are not a geographic coverage comparison;
whole-island completion and verified driving area remain unknown.

Bounding-box builds now use the same placement predicate for conversion and map
statistics; report `selection.bbox` is authoritative. Old reports still use radius.
Maps show actual exported geometry extending outside selection edges where whole
placed assets cross the box; no geometric clipping or driving coverage is implied.
