# Braille Cylinder STL Generator (OpenSCAD) — vendored copy

> **This folder is a vendored copy, not the source of truth.**
>
> | | |
> |---|---|
> | **Canonical repo** | [BrennenJohnston/braille-cylinder-stl-generator-openscad](https://github.com/BrennenJohnston/braille-cylinder-stl-generator-openscad) |
> | **Vendored from** | tag `v2.5.0` (commit `675f7a5`, released 2026-08-01) |
> | **Copied on** | 2026-08-01 |
> | **Machine-readable provenance** | [`VENDORED.json`](VENDORED.json) |
>
> The standalone repo **is** the active home for this program: it holds the
> dual-file desktop build, the 16-fixture cross-platform validation suite, and
> the CI that renders every configuration. Open issues and pull requests there,
> not here. This folder exists only so someone who found the web app can
> download the OpenSCAD version without leaving the site.
>
> Do not edit these files. Changes made here are overwritten on the next
> refresh, and `tests/test_vendored_openscad.py` fails if the `.scad` drifts
> from the hash recorded in `VENDORED.json`.
>
> **What you need:** just `Braille_Cylinder_STL_Generator.scad` and
> [OpenSCAD](https://openscad.org/) (2024.x or newer; 2026.01.03+ recommended).
> Everything else in this folder is documentation.

Parametric OpenSCAD program for generating braille embossing plates and counter
plates for cylindrical objects.

## Which build is this?

The vendored `.scad` is the upstream **MakerWorld single-file build**: the
desktop generator with `presets.scad` inlined, so it is one self-contained file
with no `include <...>`. Upstream that file is named
`makerworld/Braille_Cylinder_STL_Generator_MakerWorld_v2.scad`; it is renamed
here because this folder ships exactly one file and the suffix would only
confuse. The geometry body is byte-identical to the upstream dual-file desktop
build — upstream CI (`tests/test_makerworld_sync.py`) enforces that.

Practical consequence: this single file also uploads directly to MakerWorld's
Parametric Model Maker. See [`docs/MAKERWORLD_QUICK_START.md`](docs/MAKERWORLD_QUICK_START.md).

## Related projects

| Version | Link | Use case |
|---------|------|----------|
| **Web app** | [braille-cylinder-stl-generator.vercel.app](https://braille-cylinder-stl-generator.vercel.app) | Browser-based, automatic translation |
| **OpenSCAD (canonical)** | [braille-cylinder-stl-generator-openscad](https://github.com/BrennenJohnston/braille-cylinder-stl-generator-openscad) | Offline use, full parametric control, tests |
| **Web app source** | [braille-cylinder-stl-generator](https://github.com/BrennenJohnston/braille-cylinder-stl-generator) | This repository |

## Key difference from the web app

**This OpenSCAD version requires pre-translated Unicode braille text.** It does
not include automatic translation — the web app's liblouis integration is what
you give up by working offline.

The reverse gap has closed: as of 2026-07-29 the web app has a **Braille
(Unicode)** field that accepts pasted braille and uses it verbatim, so the
paste-braille-directly workflow below now works there too. The app also offers
`indicator_mode` = Tactile, matching this program. Feature parity between the two
versions is therefore: translation is web-only, everything else is in both.

### Phone numbers: hyphens versus periods

Both versions render exactly the cells you give them, so this is a translation
question — but it is the most common surprise, so it is worth stating in both
places. Under UEB a period or comma **keeps** numeric mode, while a hyphen or
parenthesis **ends** it:

| Typed | Braille | Cells | Number signs |
|---|---|---|---|
| `206.543.4779` | `⠼⠃⠚⠋⠲⠑⠙⠉⠲⠙⠛⠛⠊` | 13 | 1 |
| `206-543-4779` | `⠼⠃⠚⠋⠤⠼⠑⠙⠉⠤⠼⠙⠛⠛⠊` | 15 | 3 |

The 15-cell form is correct UEB, not a translator bug, and it will not fit a
13-cell row. Convert the hyphens to periods as BANA advises, or delete the extra
cells by hand before pasting.

## Quick start

1. **Translate your text** at <https://www.branah.com/braille-translator>:
   - Select Grade 1 or Grade 2 braille.
   - Ensure **Unicode Braille** is selected (NOT ASCII Braille).
   - Type your text and copy the braille output (e.g. `⠓⠑⠇⠇⠕`).
2. **Open `Braille_Cylinder_STL_Generator.scad`** in OpenSCAD and open the
   Customizer panel (View → Customizer).
3. **Configure**:
   - Paste braille into `Line_1`, `Line_2`, …
   - `plate_type`: Embossing Plate or Counter Plate.
   - `indicator_mode`: `Visual` (default) or `Tactile` — see below.
   - `paper_thickness_preset`: 0.4mm, 0.3mm, or Custom.
   - `dot_shape`: Rounded (default) or Cone.
4. **Generate**: Render (F6), then File → Export → Export as STL.

Generate the Embossing Plate and the Counter Plate separately — same settings,
only `plate_type` changes — so the two plates form a matching pair.

## What this makes

- **Cylinder emboss plate** — raised braille dots on a cylindrical surface.
- **Cylinder counter plate** — matching recesses that the emboss plate presses
  paper into.

## Indicator mode: Visual or Tactile

`indicator_mode` decides how each row is marked for alignment. Cylinder
diameter, height, and cutout are identical either way, so **both plates must use
the same mode**.

| | Visual (default) | Tactile |
|---|---|---|
| Where | Marker cells at the start of every row | One indicator per row, centred in the seam gap |
| Emboss plate | Recessed triangle (+ square when `indicators` is On) | Raised arrow pointing at the cylinder top |
| Counter plate | Mirrored recesses | Matching arrow recess the arrow nests into |
| Cells used for markers | 2 (On) or 1 (Off) | 0 |
| `indicators` toggle | Controls the square marker | Ignored |

Choose **Tactile** when a blind user needs to align the cylinders unaided: the
arrow is felt as a single continuous wedge, nothing like a braille dot, and its
point tells you which end is up on either plate. Raised-vs-recessed tells you
which cylinder you are holding. The arrow is deliberately lower than the braille
dots (0.8 mm vs 1.0 mm) so the dots, not the indicator, take the rolling
pressure.

Text capacity is `grid_columns` (default 13) in every mode.

## Other features

**Dot shapes** — `Rounded` (dome dots with spherical bowl recesses, the default)
or `Cone` (frustum cone dots with matching cone recesses).

**Paper thickness presets** — `0.4mm` (default, thicker paper, larger dots),
`0.3mm` (thinner paper, smaller dots), or `Custom` to use your own values. The
presets set 21 parameters at once, matching the web app's Card Thickness
dropdown. They deliberately do **not** touch `grid_columns` / `grid_rows`.

**Parametric control** — cylinder dimensions, braille spacing, per-shape dot
dimensions, counter recess dimensions, and positioning adjustments all map to
the web UI. See [`PARAMETER_MAPPING.md`](PARAMETER_MAPPING.md).

## Default settings

Defaults match the web app's 0.4 mm paper thickness preset:

| | |
|---|---|
| Cylinder diameter | 30.8 mm |
| Cylinder height | 52 mm |
| Polygonal cutout | 13 mm radius, 12 points |
| Seam offset | 0° |
| Cells per row | 13 (text capacity) |
| Rows | 4 |
| Cell / line / dot spacing | 6.5 / 10.0 / 2.5 mm |
| Rounded dot | 1.5 mm base ⌀, 0.5 mm base height, 1.0 mm dome ⌀, 0.5 mm dome height |
| Counter bowl | 1.8 mm base ⌀, 0.8 mm depth |

## 3D printing tips

- **Material:** PLA works; PETG is more durable for repeated embossing.
- **Layer height:** 0.1–0.2 mm for smooth dots.
- **Infill:** 40%+ for stiffness under rolling pressure.
- **Perimeters:** 3–4.
- **Orientation:** print upright, as oriented in the preview.
- **Speed:** slow the outer walls (≤ 30 mm/s) for smoother dots.

## Documentation

| Document | Description |
|----------|-------------|
| [`PARAMETER_MAPPING.md`](PARAMETER_MAPPING.md) | Parameter mapping between OpenSCAD and the web UI |
| [`docs/MAKERWORLD_QUICK_START.md`](docs/MAKERWORLD_QUICK_START.md) | Uploading this file to MakerWorld's Parametric Model Maker ([PDF](docs/MakerWorld_Quick_Start_Guide.pdf)) |
| [`docs/OPENSCAD_COORDINATE_SYSTEM_SPECIFICATIONS.md`](docs/OPENSCAD_COORDINATE_SYSTEM_SPECIFICATIONS.md) | Coordinate system reference |
| [`docs/WEB_TO_OPENSCAD_PORTING_GUIDE.md`](docs/WEB_TO_OPENSCAD_PORTING_GUIDE.md) | How the web geometry was ported to OpenSCAD |
| [`docs/QUICK_START_TESTING.md`](docs/QUICK_START_TESTING.md) | The upstream cross-platform validation suite (fixtures are not vendored) |

## Automated testing

The cross-platform validation suite — 16 reference STL fixtures comparing
OpenSCAD output against web-generated geometry, plus source guards and render
smoke tests — lives upstream and is not vendored here, to keep this download
light. Run it from
[braille-cylinder-stl-generator-openscad](https://github.com/BrennenJohnston/braille-cylinder-stl-generator-openscad)
if you need it. For day-to-day OpenSCAD use, none of it is needed.

## Troubleshooting

| Symptom | Cause / fix |
|---------|-------------|
| `INVALID CHARACTERS` | You pasted regular text instead of Unicode braille. Re-translate at Branah with Unicode Braille output. |
| `TEXT TOO LONG: 16/13` | A line exceeds the text capacity (longest line / capacity). Shorten or split the line, raise `grid_columns`, or set `text_limit_check` = Off to bypass. |
| `TACTILE GAP TOO SMALL` | Tactile mode only: the seam gap can no longer hold the indicator plus clearance. Lower `grid_columns`, raise `cylinder_diameter_mm`, or narrow `tactile_indicator_width`. |
| Dots don't align | Check `braille_y_adjust` (vertical) or `seam_offset_degrees` (angular). Spacing must match between the two plates. |
| Plates don't fit together | Both plates need the same `dot_shape` and the same `indicator_mode`; in Visual mode, the same `indicators` setting too. |
| Tactile indicator binds | Raise `tactile_recess_clearance` (outline) or `tactile_recess_extra_depth` (depth). |

## Support

Issues with the OpenSCAD program belong upstream:
[open an issue on braille-cylinder-stl-generator-openscad](https://github.com/BrennenJohnston/braille-cylinder-stl-generator-openscad/issues).
Issues with the web app, or with this vendored copy being stale, belong
[here](https://github.com/BrennenJohnston/braille-cylinder-stl-generator/issues).

## References

1. Web generator: <https://braille-cylinder-stl-generator.vercel.app>
2. Branah translator: <https://www.branah.com/braille-translator>
3. BANA size and spacing: <https://brailleauthority.org/size-and-spacing-braille-characters>
4. NLS Specification 800: <https://www.loc.gov/nls/>
5. 2010 ADA Standards: <https://archive.ada.gov/>

## Acknowledgments

- **Brennen Johnston** — original web-based generator and the OpenSCAD port.
- **Tobi Weinberg** — project inception and development support.
- **liblouis** — braille translation library (used in the web app).

## License

**PolyForm Noncommercial License 1.0.0** — free for personal, educational, and
non-commercial use; modification and remixing allowed; no commercial use. See
[LICENSE](LICENSE).
