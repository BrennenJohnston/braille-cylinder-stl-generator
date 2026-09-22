# Browser-exported fixtures

These files were downloaded from the real browser pipeline (Chromium, Playwright,
Manifold WASM worker) and are compared byte for byte by the e2e suite. They are
NOT the Python golden fixtures in `tests/fixtures/`, which `python -m
tests.test_golden` regenerates; nothing regenerates these. Capture a new one
only when the geometry is meant to change, and say why in the commit.

| File | Captured | What it is |
|---|---|---|
| `embossing_0.4_abc_before_seam_channel.stl` | 2026-09-20, Phase A1 of the seam-channel work | The embossing plate for the text `abc` on untouched dials (0.4 mm card-stock preset, 30.8 x 52 mm barrel, 15 x 4 cells, visual row markers, Version 1, single-sided, no gears) exported BEFORE the slicer seam channel existed. 1946 triangles, 97 384 bytes. |
| `counter_0.4_abc_before_seam_channel.stl` | same | The counter plate for the same request. 74 576 triangles, 3 728 884 bytes. |
| `*.request.json` | same | The exact `/geometry_spec` request body each STL came from, so a test can prove it sends the same settings plus `seam_channel_enabled: 0`. |

The capture was run twice and both plates matched byte for byte, so the export
is deterministic and a byte comparison is a fair test. `seamChannel.spec.ts`
turns the Expert Mode seam-channel switch off and expects the download to equal
these bytes exactly: that is the proof that the switch restores the pre-channel
barrel (decision D-2, 2026-09-20).
