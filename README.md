# Braille Cylinder STL Generator

[![Version](https://img.shields.io/badge/version-2.1.0-blue.svg)](https://github.com/BrennenJohnston/braille-cylinder-stl-generator/releases/tag/v2.1.0)
[![License: PolyForm Noncommercial](https://img.shields.io/badge/License-PolyForm%20Noncommercial-red.svg)](LICENSE)
[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)

A web app for generating 3D-printable braille. Type your text, pick a braille translation table, and download an STL file you can send straight to your 3D printer.

The goal is to make braille labels and cards accessible to anyone with a 3D printer, without needing to know braille yourself. The app handles translation (via [liblouis](https://liblouis.io/)) and turns it into a ready-to-print 3D model.

## What it does

- Translates text to Grade 1 or Grade 2 braille across 50+ language tables
- Generates STL files for cylindrical braille labels (jars, bottles, containers, etc.)
- All STL generation runs in the browser — nothing gets uploaded
- Shows a 3D preview before you download

Flat business card plates are **parked**, not in development here — the code is
still in the repo but disabled in the UI. See
[KNOWN_ISSUES.md](docs/KNOWN_ISSUES.md) for why. Directly readable braille cards
already ship as their own tool:
[braille-wedge-card-openscad](https://github.com/BrennenJohnston/braille-wedge-card-openscad).

## The device these cylinders go into

The cylinders this app generates are the interchangeable plates for the
**Custom Braille Embosser** — a hand-operated braille embosser built from ten
snap-fit 3D-printed parts, with no fasteners, springs, glue, or electronics, for
about $3–6 of filament. Generate an embossing plate and its matching counter
plate at the same card-stock thickness, print both, and snap them into the
holders.

Build files, print profiles, and documentation for the device are on
[Printables](https://www.printables.com/model/1742352-custom-braille-card-embosser-hand-operated),
[MakerWorld](https://makerworld.com/en/models/2881581-custom-braille-card-embosser-hand-operated),
and [Thingiverse](https://www.thingiverse.com/thing:7365273).

You can also use the cylinders on their own as tactile labels for jars, bottles,
and containers.

## Quick start

### Using the hosted app

Open <https://braille-cylinder-stl-generator.vercel.app> — nothing to install.

### Running locally

```bash
pip install -r requirements.txt
python backend.py
```

Open [http://localhost:5001](http://localhost:5001) in your browser.

### Deploying to Vercel

1. Connect the repo to Vercel
2. Deploy

That's it. No Redis, no blob storage, no API keys to manage. The server just serves static files and a lightweight JSON endpoint — all the heavy geometry work happens in your browser.

You can optionally set `PRODUCTION_DOMAIN` as an environment variable, but it's not required. See [Environment Variables](docs/security/ENVIRONMENT_VARIABLES.md) if you're curious.

## How to use it

1. Type your text (up to 4 lines)
2. Pick a braille translation table and grade
3. Set your cylinder dimensions — measure your container first
4. Click Generate
5. Download the STL and 3D print it

There's a **Help** button inside the app that walks you through choosing what to include, formatting your text, and measuring containers. For more depth, check the guides below.

## OpenSCAD version

Prefer working offline or want full parametric control? The OpenSCAD version is
maintained in its own repository —
**[braille-cylinder-stl-generator-openscad](https://github.com/BrennenJohnston/braille-cylinder-stl-generator-openscad)**
— and a copy of its latest release is vendored into [`OpenSCAD/`](OpenSCAD/)
here so you can download it without leaving the site.

- [`OpenSCAD/Braille_Cylinder_STL_Generator.scad`](OpenSCAD/Braille_Cylinder_STL_Generator.scad) — one self-contained script (open in [OpenSCAD](https://openscad.org/) and use the Customizer panel; it also uploads straight to MakerWorld's Parametric Model Maker)
- [`OpenSCAD/README.md`](OpenSCAD/README.md) — quick start, parameters, troubleshooting
- [`OpenSCAD/VENDORED.json`](OpenSCAD/VENDORED.json) — which upstream tag this copy came from
- [`OpenSCAD/PARAMETER_MAPPING.md`](OpenSCAD/PARAMETER_MAPPING.md) — how OpenSCAD parameters correspond to the web UI controls
- [`OpenSCAD/docs/`](OpenSCAD/docs/) — MakerWorld quick start, coordinate system reference, porting guide, testing notes

Issues and pull requests for the OpenSCAD program belong upstream. Nothing in
`OpenSCAD/` should be edited here — `tests/test_vendored_openscad.py` fails if it is.

The web app translates automatically; the OpenSCAD version needs you to translate manually (using [Branah.com](https://www.branah.com/braille-translator)), but it works without an internet connection and integrates with existing CAD workflows.

## Project layout

```
app/              Flask backend, geometry specs, validation
public/           Production HTML (served on Vercel)
static/           Frontend JS, CSS, Web Workers, liblouis tables
templates/        Development HTML (served by Flask locally)
tests/            Smoke tests and golden file regression tests
docs/             Guides, technical specs, deployment notes
```

See [PROJECT_STRUCTURE.md](PROJECT_STRUCTURE.md) for the full breakdown.

## Development

Requires Python 3.12+.

```bash
pip install -r requirements-dev.txt

# Run tests
pytest

# Lint and format
ruff check .
ruff format .
```

Pre-commit hooks are included — run `pre-commit install` to set them up.

## Guides

**Using the app:**

- [Cylinder Guide](docs/guides/CYLINDER_GUIDE.md) — measuring containers, setting parameters, worked examples
- [Business Card Guide](docs/guides/BUSINESS_CARD_TRANSLATION_GUIDE.md) — what to include and formatting rules, quoted verbatim from the BANA *Business Cards Fact Sheet* (approved March 2024). Flat cards are parked; the formatting rules still apply to cylinder text.

**Working on the code:**

- [Project Structure](PROJECT_STRUCTURE.md)
- [Specifications Index](docs/specifications/SPECIFICATIONS_INDEX.md)
- [Client-Side CSG](docs/development/CLIENT_SIDE_CSG_DOCUMENTATION.md)
- [Deployment Checklist](docs/deployment/DEPLOYMENT_CHECKLIST.md)

## Contributing

Contributions are welcome. See [CONTRIBUTING.md](CONTRIBUTING.md) for setup instructions and guidelines.

## Acknowledgments

This project started from [tobiwg/braile-card-generator](https://github.com/tobiwg/braile-card-generator) by Tobi Weinberg. Thanks to Tobi for getting it off the ground.

## Changelog

See [CHANGELOG.md](CHANGELOG.md) for release history.

## License

[PolyForm Noncommercial License 1.0.0](LICENSE)

Free for personal, educational, and non-commercial use. Modification and remixing allowed. No commercial use.
