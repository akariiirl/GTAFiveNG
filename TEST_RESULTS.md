# Test results

2026-11-16 visual tracker: generated and visually inspected 3080 × 2640 PNGs from existing neighborhood03 data. Raster footprint: approximately 376,300 m² at 2 m resolution. Selected-source instance match: 5,946 / 7,465 (79.65%); this is not geographic or whole-island completeness. Surface report: 1,510 / 1,511 samples within tolerance, one documented failure shown in red. Whole-island boundary and build-matched driving coverage are unavailable. Tracker unit check verifies overlap is counted once and vertical walls add no projected area. No additional neighborhood extraction was performed for the tracker.

2026-11-15:

- CodeWalker.Core compiled: zero errors.
- AssetReader compiled: zero errors; NuGet vulnerability lookup warning because the normal shell cannot reach the network. Build dependencies restored successfully during the earlier network-enabled operation.
- Four Python tests passed: nonfinite/invalid indices, zero-area removal, inverse quaternion orientation, Collada structure round-trip.
- Checkpoint01 structural validation passed: 290 scene objects, 118 shape files, 432 materials, 288 packaged files, no dangling generated shape/material/texture paths.
- ZIP CRC and level-root layout verified. Size 49,050,503 bytes; SHA256 `98ed5db13a95e22f26ef9cc4d92e3d1b128939384cdcf206d6106b33457ca93c`.
- Earlier prototype4 loaded in BeamNG 0.40.5.0.302427 and spawned a pickup. Log reached `worldReadyState to 1`. Its initial measurement extension path was wrong; fixed for subsequent tests. Initial reflection-map warning fixed in prototype5.
- Direct executable launch exited with code 50331652. Normal Steam launch succeeded. Current BeamNG creates a `current` subfolder under the supplied user path.
- Screen inspection through the app-control tool timed out awaiting app approval. No successful screenshot inspection recorded at this checkpoint.

Vehicle support, driving continuity, texture appearance and performance remain unverified until telemetry and visual evidence are recorded. Unit/structural checks do not establish them.
