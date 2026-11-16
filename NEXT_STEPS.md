# Exact continuation

1. Read PROGRESS.md, TEST_RESULTS.md and `generated/prototype5/conversion_report.json`.
2. Inspect `generated/beamng-user/current/lsf_validation.json` and `beamng.log`. The test extension should be `current/lua/ge/extensions/lsf/validation.lua` (underscore in extension name resolves to a directory).
3. Confirm vehicle settles on original collision, then drive a short road route and record position/ground samples. Inspect a game-generated screenshot. Do not mark Stage C on loading evidence alone.
4. Fix spawn using collision ray tests if needed; current spawn is (0,0,36) in translated coordinates.
5. Resolve remaining assets through YTYP archetypes (asset name can differ from archetype name, or live in YDD/YFT). Resolve texture dictionaries and parent dictionaries before broad export.
6. Add capsule/cylinder/sphere and embedded drawable collision, and compare visible road heights against collision samples.
7. Add source fingerprints, atomic export writes, per-sector manifests, bounded batches, and native DAE LOD hierarchy before expanding. Current XML cache only skips existing exports.
8. Use a fresh generated build folder, package with `src/package.py`, retain prior ZIPs. No stock files or existing user mods should be replaced.

`tools/launch_test.ps1` stops only the unique game process whose command line points into this project's isolated profile, copies the measurement extension and launches through Steam. It waits briefly for Steam to notice shutdown. If Steam does not restart the game, issue the Steam launch once the prior process is gone; do not repeatedly kill unrelated game processes.
