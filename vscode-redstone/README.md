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
- **Spec**: name, traits and description above the tests (read-only).
- **Tests**: listed from the file (truth tables as tables, steps as lists, with delays and `settle`). Click one to load
  `<workspace>/traces/<spec name>/<test name>.json`; play, step (arrow keys), scrub, change speed.
  The truth-table row being exercised is highlighted. Traces reload when the files change.
  A sparse trace (`"sparse": true`, a run without `REDSTONE_TRACE=1`) records only the named cells;
  every other cell is drawn as placed, and its tooltip says "not recorded". A dense trace's comparator
  output strengths (`levels`) are shown on each comparator and in the tooltip. A failed run's failures
  are listed above the player ("Test failed at tick T: message"); click one to jump to that tick.
- **Run test**: runs `.venv/bin/python -m pytest -q "tests/test_library.py::test_spec[<spec>::<test>]"` with
  `REDSTONE_TRACE=1` (a dense trace) as a VS Code task in the workspace root, then reloads the trace.
  It sets no `REDSTONE_PLOT` (VS Code's own environment still passes through), so the test builds in the
  `main` plot, or in its own plot if the build does not fit main; `python -m scripts.try` instead builds in
  the plot of the spec's folder, on an idle satellite when one is up.

Build: `npm install && npm run build`; `npm run package` writes a `.vsix`; `npm test` runs the unit tests
over the specs and traces in `test/fixtures/` (needs the repo's `.venv` for the Python loader check; no server);
`npm run render` writes PNGs of library files to `out/render/`.
