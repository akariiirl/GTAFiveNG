# Conversion report

Checkpoint01: 272 visual instances, 108 distinct drawables, 494,024 instanced visual triangles, 122,908 collision triangles, 163 diffuse textures.
Region filter: GTA XY center (-370,-1330), radius 220 m. This is an asset-center selection radius, **not** a promise of complete coverage of a 440 m square. Collision bounds intersecting the selection can extend outside it.

Inputs: Legacy base archives; sc1_01 block, sc1_rd road network, selected shared texture dictionaries, missing-name asset pass. Update/DLC override precedence is not implemented.

Preserved: source positions, triangles, normals, primary UVs, material groups, world placement and scale. Coordinates remain Z-up meters, translated by (+370,+1330,0) to reduce origin distance. GTA placement quaternions are inverted as in CodeWalker. Triangle and oriented box YBN bounds are converted separately from visuals.

Known missing/incomplete:

- 67 unresolved asset names and 33 missing diffuse texture names in checkpoint01. Exact lists: `generated/prototype5/conversion_report.json`.
- Capsule, cylinder, and sphere collision primitives are counted but not yet converted.
- Embedded drawable collision and YDD/YFT archetype resolution are not yet implemented.
- No complete-neighborhood claim: neighboring blocks, vegetation, props, and surface coverage remain incomplete.
- Material translation is basic diffuse/cutout/decal only. Source shader blending, tangents, vertex colors, extra UV channels, normal/specular maps, and emissive behavior need further work.
- LOD meshes are exported where matched but not yet assembled into BeamNG detail chains. No custom streaming, Forest instancing, traffic, or whole-island build.
- Original source textures retain DDS mipmaps. Shared texture name collisions need a proper dictionary-scoped resolver.

Full local inventory: `generated/source/inventory.jsonl` (157,769 files / 1,479 archives). Proprietary exports and packages are ignored by Git.
