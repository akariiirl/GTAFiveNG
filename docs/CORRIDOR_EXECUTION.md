# Bounded local corridor execution

`selected_region.py --bbox XMIN YMIN XMAX YMAX` selects HD placements by their
transformed archetype bounds, including placements whose anchors are outside the
box. Collision selection covers those bounds too. Assetless archetypes are
reported as nonvisual metadata; missing visual resources still stop planning.
`prepare_selected.py` preserves raw exports and retains only planned YMAP entity
indices. The corridor calls `build(..., preselected=True)` on this filtered view;
the ordinary converter retains its original point-selection behavior.

`src/corridor_job.py CONFIG_JSON` runs a small sequential list of boxes using the
existing exact-task reader, verified receipts, preparation, immutable mesh cache,
structural validator, collision samples, packager and progress maps. No catalog
bootstrap or game writes are performed. Example config keys:

```
root, workspace, evidence, dotnet, reader, gta, python, python_packages,
reuse_sources, spawn, stages: [{name, bbox}]
```

Paths are supplied locally, not embedded in tracked configuration. `spawn` is
world GTA XYZ. `evidence` names the existing CodeWalker dictionary JSON relative
to `root`. Use an existing completed catalog and a new output workspace. All
game-derived inputs and outputs remain on the local data drive.

Copy the current `src/*.py` and `tools/run_corridor_job.ps1` into a local
`code/src` and `code/tools` snapshot under the workspace before detached launch.
This keeps resume independent of subsequent source edits. Start it with:

```powershell
Start-Process pwsh -WindowStyle Hidden -ArgumentList @(
  '-NoProfile','-File',"$job/code/tools/run_corridor_job.ps1",
  '-Config',"$job/config.json"
) -RedirectStandardOutput "$job/console.log" -RedirectStandardError "$job/stderr.log"
```

The launcher requires 8 GiB available RAM. Extraction/conversion are sequential;
metadata planning uses four readers and numerical-library threads are capped at
four. Stage boundaries require 20 GiB free on the output volume. No service or
startup setting is installed. Processing continues after the agent disconnects.

Inspect `progress.json` for the Python PID, current stage, package and failures.
Inspect `console.log`, `stderr.log`, and each stage's `extraction.log` for detail.
The first package is saved before plotting or starting a larger box. A later
failure preserves it. `complete.json` records processing completion, not an
in-game driving pass; inspect texture omissions and collision failures.

Resume by invoking the same frozen launcher and config. It verifies completed
package hashes, prepared files and converted outputs before reuse. Exact-task
reader receipts recover extraction; incomplete conversion directories are kept
and a fresh attempt is created. The input signature rejects changed source/config.
If a process was terminated without cleanup, verify its recorded PID has exited
before removing only `job.lock`. Never remove a live job's lock.

For another workspace, `mesh_cache` can reference an existing immutable cache.
Optional `cache_inputs` names that prior job's input manifest. It permits reuse
after planning-only changes only when convert.py, primitives.py, lod.py,
dependencies.py and resource_cache.py hashes match. Changed conversion semantics
fail this compatibility check; do not force old entries into a new conversion.

Offline road coverage and collision samples are not proof of a navigable route.
An actual route test must exclude sidewalks/medians, inspect traffic obstacles,
record vehicle telemetry and screenshots, and distinguish any initial vehicle
placement from driven distance. Keep the last known-good package after failures.
