# Architecture

The pipeline is a local, read-only prototype for a subset of GTA V Legacy, not a complete island converter. Source and output are separate from installed games.

1. `src/AssetReader` uses the pinned external CodeWalker.Core checkout to read GTA archives and keys from a user's local installation. It inventories resources and exports selected YMAP/YTYP/YDR/YDD/YFT/YBN/YTD data as XML and DDS into `generated/source`. Filters match resource names; `@report.json` uses missing names. A file fingerprint cache and temporary-file replacement are implemented, but cache completeness still needs validation. Errors are logged locally.
2. `src/convert.py` reads exported resources, selects a region around a GTA XY center, transforms positions and inverse placement quaternions into translated Z-up coordinates, generates Collada visual shapes and separate collision shapes, resolves basic materials/textures, and writes a BeamNG level plus a conversion report. `src/primitives.py` supplies rounded collision geometry. Export coverage, materials, asset resolution and LOD remain incomplete.
3. `src/validate_surfaces.py` samples visual road triangles against collision heights; this is a diagnostic rather than exhaustive coverage or a driving test. Python unit tests cover selected geometry and texture behavior.
4. `src/package.py` validates generated level references, writes a deterministic ZIP to a new path, checks ZIP integrity and emits a manifest. Structural success does not prove appearance or physics. `tools/launch_test.ps1` launches a local Steam BeamNG install with an isolated profile and `src/lsf_validation.lua` telemetry; its paths are machine-specific.

Data boundaries: tracked project source and documents are portable; `vendor/CodeWalker` must be restored separately, while `generated/`, `builds/`, game files and game-derived assets remain local and ignored. Reports inside generated directories also stay local; PROJECT_STATUS.md carries a short non-asset summary. LICENSES.md covers the relevant distribution constraints.

Cloud additions (2026-11-16): `dependencies.py` indexes flat exported YDR/YFT XML,
resolves basic YTYP `name` → `assetName` aliases, and reports ambiguous names and
unresolved aliases in `dependency_resolution`. It deliberately does not guess
archive precedence. Duplicate standalone drawable names now remain unresolved
instead of silently selecting a filename. The resolver API supports explicit
filename overrides; the converter CLI does not yet expose them. YDD members,
hash-only references and scoped texture inheritance still need implementation.
`region.py` adds immutable content-addressed whole-region builds and verified cache
reuse around the existing converter/package/map functions. No runtime streaming,
LOD generation, geographic chunks or shared-asset packaging is implemented.

Issue #2 additions: `planning.py` emits deterministic exported-source chunk/dependency
plans. `chunks.py` models resource residency by SHA-256, with shared references and
atomic transitions bounded by staged/retained payload size. Loading a new chunk may
require headroom for the previous chunk during staging; callers can unload first.
A loader's own temporary memory is outside this bound. Visibility and LOD policies
are pure functions for later integration; no BeamNG streaming hooks are installed.

`TextureCatalog` now connects opt-in scoped TXD policy to actual material/texture
packaging. Default conversion still uses flat DDS exports. Explicit asset-to-TXD
policy overrides YTYP fields; conflicting equal-priority YTYP dictionary definitions
remain unresolved. Parent dictionary traversal and source-relative texture targets
prevent collisions between same-named textures. Extracting this policy from the
installed game's active mount metadata remains deferred integration work.

`selection.py` centralizes radius/bbox validation, membership and coordinate frame.
`selection` in conversion reports is authoritative; legacy reports fall back to
origin/radius. Box builds select whole placements, translate about the midpoint,
and preserve the prior collision-by-visual-extent policy. Cache IDs distinguish
boxes from circles even with equal centers and circumscribed radii.

`resource_cache.py` adds opt-in persistent drawable conversion reuse under a region
workspace. Hash keys cover source XML/member, name, available texture bindings,
pipeline source and NumPy version. Verified immutable JSON entries hold mesh arrays
and replayable material/texture/diagnostic effects; no pickle is used. Atomic
no-clobber publication protects interrupted/concurrent writes. Packaging stays
self-contained; cached/uncached synthetic packages match byte-for-byte. This is
conversion CPU reuse, not runtime resource sharing or bounded-memory processing.

`extraction.py` bridges exported region metadata and inventory to exact reader tasks.
The native task protocol has source-only validation independent of game keys.
Task-mode exports use SHA-derived path prefixes, per-resource DDS directories and
verified receipts. Archive priorities/parent TXDs require explicit supplied policy;
collision selection requires inventory bounds. Native inventory currently only
provides names/sizes, so collision bounds stay unknown by default. The Python adapter
verifies receipts and builds scoped texture policy; it does not decode archives.

Shared collision entries retain world-space geometry and translate on replay, so
neighboring origins share conversion work. Texture cache metadata references
verified content-addressed binary payloads. Warm texture publication streams rather
than materializing output bytes in Python. Optional repair quarantines corrupt
metadata/payloads; no old build is overwritten. Mesh JSON still loads in full.
