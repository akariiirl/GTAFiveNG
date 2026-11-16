# Isolated prefab/chunk experiment — engine behavior unverified

Official references checked 2026-11-16:
- [Prefab file format](https://documentation.beamng.com/modding/levels/level_formats/prefab/)
- [Prefab scene object fields](https://documentation.beamng.com/modding/levels/level_classes/prefab/)
- [Lua object creation examples](https://documentation.beamng.com/modding/postfx/compute_example/)
- [Console/FS/log interfaces](https://documentation.beamng.com/modding/programming/console/)

The generated JSON prefab format and filename/loadMode fields follow those docs.
Mapping Lua object registration/deletion to actual prefab lifecycle is a guarded
experimental adapter, not engine-verified behavior. Documentation is incomplete;
verify bindings against the installed BeamNG version. No game source was copied.

```powershell
./.venv/Scripts/python.exe src/runtime_plan.py GENERATED_COMPOSED_BUILD --output generated/runtime-experiment-new --max-chunks 4 --max-bytes 536870912
```

This exports a separate asset tree, original Lua extension, JSON prefabs and
runtime-plan.json. It never changes the normal package or testing profile. Boundary
objects have one owner; other chunks depend on that owner. Plans include common
origin, conservative file-size estimates, limits and explicit unverified flags.

Only after the normal composed package is locally inspected, prepare a **different
isolated profile with an empty scene**. Do not load these prefabs over the composed
scene: that duplicates objects and collision. Manually install the experiment's
`levels/` and `lua/` into a new unpacked mod in that profile and place runtime-plan.json
at a known VFS path. Nothing auto-loads. GE-console experiment, subject to installed
version/API verification:

```lua
extensions.load('lsf_chunkPrototype')
extensions.lsf_chunkPrototype.start('/YOUR_EXPERIMENT/runtime-plan.json')
extensions.lsf_chunkPrototype.transition({'0_0'}) -- choose IDs actually in the plan
extensions.lsf_chunkPrototype.stats()
extensions.lsf_chunkPrototype.reload('0_0')
extensions.lsf_chunkPrototype.transition({})
```

IDs above are examples, not evidence of GTA coverage. Test paused/stationary; never
assume collision remains active during reload. Logs record missing files, load/unload
failure and retained handles when cleanup fails. Peak count/file budgets may require
unloading first. Lua heap KiB and estimated file bytes are not engine RAM/VRAM or
FPS. Existing residency-model tests and new real-Lua mock-adapter tests validate
control logic only. Actual prefab loading, materials, physics lifecycle, unload,
reload, memory recovery and performance remain PC-only validation.
