# Project Los Santos

2026-11-15: Development started. No converted or playable GTA region yet.

- Verified GTA V Legacy in D:/SteamLibrary/steamapps/common/Grand Theft Auto V.
- Verified BeamNG installation in D:/SteamLibrary/steamapps/common/BeamNG.drive.
- Initial free space: C: 8.0 GiB; D: 381.8 GiB. Keep initial working set small.
- Python available through Codex bundled runtime; Windows Store python alias is broken.
- .NET runtime exists; SDK installation underway locally in tools/dotnet.
- CodeWalker source downloaded read-only dependency at vendor/CodeWalker.
- Source games will remain unchanged. Proprietary outputs remain ignored and local.
- Usage interface at startup reported 3% of five-hour allowance used, 16% weekly. No guaranteed execution time or token balance was supplied.

## Preserved checkpoints

- Source checkpoint `425abda` saved; source games remain unchanged.
- Read-only inventory completed: 157,769 resources / 1,479 archives.
- Exported South Central block, road network, shared textures and selected props through CodeWalker XML/DDS.
- Implemented XML-to-Collada conversion, placement/quaternion conversion, separate YBN triangle/box collision, level construction, structural validation and deterministic ZIP packaging.
- Four focused geometry tests pass.
- Checkpoint01: `builds/checkpoint01/los_santos_fazes.zip` (preserved initial spawn bug).
- Checkpoint02: `builds/checkpoint02/los_santos_fazes.zip` (corrected road spawn and nonnegative collision-shape detail).
- Current subset: 272 visual instances, 108 visual shapes, 122,908 collision triangles, 163 diffuse textures. 67 asset names and 33 diffuse texture names unresolved.
- BeamNG 0.40.5 launched via Steam with isolated profile, loaded actual original geometry and collision, and spawned pickup. Initial spawn fell through a geographic gap; telemetry exposed it. Revised spawn testing underway.

Stage A loading and Stage B geometry import have engine-log evidence. Visual inspection and Stage C driving test are pending. No Stage D–G completion or FPS claim.

Usage checkpoint: supported interface reported 70% of five-hour allowance used. Prioritize tested packaging and saved continuation over new broad expansion.
