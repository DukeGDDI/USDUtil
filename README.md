# USD Utility Tool (Maya)

## Problem and intended user
Layout and lighting artists open large USD scenes (many references, payloads and
materials) in Maya. The Outliner is slow and hard to search, so they waste time
hunting for props, hidden prims and heavy payloads. This tool gives them a small
panel to load a USD file, find prims by name, material or visibility, and unload
or load payloads to keep the scene light, so they can focus on their art.

## Features
- Browse for and load a USD file into Maya (creates a `mayaUsdProxyShape`).
- Select prims by name (wildcards, case-insensitive).
- Select prims by bound material, or by USD kind (component, group, assembly).
  The Kitchen Set has no materials, so use kind there.
- Select all invisible prims, and make them visible.
- Unload / load payloads on the selected prims.
- Results list; click entries to select them in Maya.

## How to run (Maya 2027, macOS)
1. Put `usd_ops.py` and `usd_utility_ui.py` in one folder, e.g.
   `/Users/rodney/Workspace/USDUtil`.
2. In Maya, open the Script Editor, Python tab, and run:
   ```python
   import sys
   sys.path.append("/Users/rodney/Workspace/USDUtil")
   import usd_utility_ui
   usd_utility_ui.show()
   ```
   Re-running `show()` reloads the code, so edits take effect without restarting.
3. Make sure the **Maya USD** plugin (`mayaUsdPlugin`) is enabled in
   Windows > Settings/Preferences > Plug-in Manager. The tool tries to load it.

## Test scene
Pixar Kitchen Set: https://openusd.org/release/dl_kitchen_set.html
Load `Kitchen_set/Kitchen_set.usd`. (The scene is not included in this submission.)

## Files
- `usd_ops.py`: USD/UFE logic (no UI).
- `usd_utility_ui.py`: PySide window (PySide6 on Maya 2025+, PySide2 fallback).
