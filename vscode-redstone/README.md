# Redstone Build Viewer

Visual viewer, editor and test-trace player for `*.redstone.yaml` Minecraft redstone builds.
Opens by default for those files; use "Reopen Editor With... > Text Editor" for the raw YAML.

- **Layer view**: one y layer at a time (north up, east right), the layer below drawn faintly.
  `[` / `]` or PageDown / PageUp change layer; the strip on the right is an all-layers overview.
- **Editing**: pick a block from the palette (file palette + common blocks), left-drag to paint,
  right-drag to erase. `R` rotates the block under the cursor (or the brush), `D` cycles repeater delay,
  `I` picks the block under the cursor. Toolbar: add/remove layer, add/remove row or column at each edge.
  Named cells: choose input/output/name and a name in "Named cell", then paint. Select tool + Rename to change a name.
  Only `palette` and `layers` are rewritten; everything else keeps its text. Undo/redo is normal VS Code undo.
- **Tests**: listed from the file (truth tables as tables, steps as lists). Click one to load
  `<workspace>/traces/<spec name>/<test name>.json`; play, step (arrow keys), scrub, change speed.
  The truth-table row being exercised is highlighted. Traces reload when the files change.
- **Run test**: runs `.venv/bin/python -m pytest -q -k "<spec> and <test words>"` with `REDSTONE_TRACE=1`
  as a VS Code task in the workspace root, then reloads the trace.

Build: `npm install && npm run build`; `npm run package` writes a `.vsix`; `npm test` runs the unit tests
(needs the repo's `.venv` for the Python loader check); `npm run render` writes PNGs of library files to `out/render/`.
