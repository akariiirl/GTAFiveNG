# Project Los Santos — local prototype

Visual milestone maps: see [tracker instructions](docs/PROGRESS_TRACKER.md). Latest PNGs and measured statistics are in `generated/progress_maps/`; earlier timestamped milestone images are preserved.

This is a partial South Los Santos conversion, **not the complete GTA V map**.
The current preserved ZIP is `builds/checkpoint01/los_santos_fazes.zip`.
It contains original local GTA geometry and textures; keep it private.

## Installation

1. In the BeamNG launcher, open Manage User Folder and open the current user folder.
2. Copy the ZIP into its `mods` directory. Do not replace an existing file of the same name without backing it up.
3. Select **Los Santos — South Central prototype** in Freeroam.
4. Stay on the converted roads. Edges are unfinished and neighboring blocks are missing.

An isolated developer installation is in `generated/beamng-user/current/mods/unpacked/los_santos_fazes`.
The test launcher uses Steam, `-userpath`, and this isolated profile. It does not change game installation files or your normal mods.

## Reproduce

Run commands from this directory in PowerShell:

```powershell
$env:DOTNET_CLI_HOME="$PWD/tools/.dotnet-home"
$env:NUGET_PACKAGES="$PWD/tools/.nuget"
./tools/dotnet/dotnet.exe build src/AssetReader -c Release
./tools/dotnet/dotnet.exe src/AssetReader/bin/Release/net8.0/AssetReader.dll 'D:/SteamLibrary/steamapps/common/Grand Theft Auto V' generated/source sc1_01
./tools/dotnet/dotnet.exe src/AssetReader/bin/Release/net8.0/AssetReader.dll 'D:/SteamLibrary/steamapps/common/Grand Theft Auto V' generated/source sc1_rd
# Also extract cityeastrd, globalroads, sc1block01, sc1struc, sc1tram with the same command.
./tools/python.ps1 src/convert.py --output generated/new-build
./tools/dotnet/dotnet.exe src/AssetReader/bin/Release/net8.0/AssetReader.dll 'D:/SteamLibrary/steamapps/common/Grand Theft Auto V' generated/source '@generated/new-build/conversion_report.json'
# Rebuild to a fresh output folder after resolving dependencies.
./tools/python.ps1 -m unittest discover -s tests
./tools/python.ps1 src/package.py generated/new-build builds/new-checkpoint/los_santos_fazes.zip
```

Dependencies: .NET SDK 8.0.428 (project-local), CodeWalker commit `485d56bec00262ed7fa472261cce7bbc6202b96e`, Python 3 with NumPy (bundled Codex runtime). `tools/python.ps1` contains this machine's exact Python path. The Windows Store python alias did not work.

The reader's fourth argument is a name substring or `@conversion_report.json` for missing-asset names. Completed XML exports are skipped on restart. This simple cache does **not** yet detect source updates: use a fresh source output directory after a game update. Converter output should likewise use a fresh directory. ZIP packaging refuses to overwrite an existing build.

Read TEST_RESULTS.md and CONVERSION_REPORT.md for verified status and limitations.
