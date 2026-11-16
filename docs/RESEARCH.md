# Research log

Checked 2026-11-15. Search results can contain ambiguous dates; do not assume a version/date without source verification.

- https://github.com/Sollumz/Sollumz/releases : native Legacy/Enhanced import is available through optional Windows PyMateria. YMAP support must be checked separately. Blender is not yet located.
- https://github.com/dexyfex/CodeWalker : existing C# archive/resource parsers and XML export; downloaded commit 485d56bec00262ed7fa472261cce7bbc6202b96e (2025-04-11). Prefer reuse for initial Legacy conversion.
- https://github.com/BxdiS/CodeWalker-CLI : existing CLI fork worth comparing for extraction.
- https://github.com/VIRUXE/vespucci : Rust GTA renderer/editor and archive CLI. Not a demonstrated BeamNG export pipeline.
- https://github.com/cngil/gtav-mapagent : CodeWalker-based GTA placement editor; not a complete BeamNG converter.
- https://documentation.beamng.com/modding/levels/level_classes/tsstatic/ : DAE static shapes, collision meshes, transform fields, native shape LOD; Forest preferred for many repeated props.
- https://docs.beamng.com/modding/levels/export_dae/ : Collada hierarchy and Colmesh-1 naming.

The installed game's NOTE_FOR_MODDERS.md was read. Work from installed examples; do not change installation files or override stock content. A new unique level and isolated user folder will be used for testing where possible.

No stable full-world streaming implementation selected. First validate small contiguous region using supported static meshes and collision.
