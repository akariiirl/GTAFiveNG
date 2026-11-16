# Test results

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
