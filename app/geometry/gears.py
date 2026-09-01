"""
Gear-integrated one-piece roller (BETA) constants and math.

Gear mode ships each cylinder as ONE watertight solid with its top and bottom
drive gears already attached, instead of a bare barrel that separately printed
gears are pushed onto. Meshing the two rollers' gears is what holds the paired
cylinders rotationally synchronised.

Everything here is a pure function or a constant: no I/O, no globals mutated,
no settings objects. Lengths are millimetres, angles degrees.

The gears are NOT parametric. They are a 1:1 replication of Brennen's reference
set, vendored as static/assets/gears/gears_a.bin and gears_b.bin and
regenerated only by scripts/derive_gear_assets.py. Every number below was
measured from those samples (research folder 01_SAMPLE_GEOMETRY_AUDIT.md) and
is reproduced here so app/validation.py and app/geometry_spec.py read ONE
source - cross-file default drift is this project's most common historical bug.

Why the barrel size is a hard requirement rather than a preference: the gears
are baked at fixed heights (z -10..0 and 52..62 around a base-at-zero barrel)
and do NOT move with the cylinder. Measured on the real assets 2026-08-24:

  * a barrel 1 mm short (51.0) exports as THREE loose bodies, the gears
    floating free - and each shell is closed, so the mesh still reports
    "watertight"; only a body count catches it;
  * a barrel 10 mm tall (62.0) swallows 5 mm of each gear, and the teeth at
    that end are gone;
  * the diameter never breaks the union, but it sets the nip. Two rollers at
    the reference 32.0473 mm axis distance leave (32.0473 - diameter) of
    surface gap, so 30.75 gives 1.2973 mm instead of 1.2473 mm and cuts the
    dot-into-card engagement from about 0.153 mm to about 0.103 mm. At
    32.2187 the barrel reaches the tooth tips and the pair cannot mesh at all.
"""

from __future__ import annotations

# The reference roller (audit section 2). This is the LAYER-2 live UI cylinder
# (diameter 30.8), not the Layer-1 schema default of 30.75 - the gears were
# measured against a 15.400 mm radius barrel.
GEAR_BARREL_DIAMETER_MM = 30.8
GEAR_BARREL_HEIGHT_MM = 52.0
# Float slack only. At 32 mm a float32 ULP is 3.8e-6 mm, so 0.001 is about 250
# times the representation noise and far below any dimension a user can type.
GEAR_BARREL_TOLERANCE_MM = 0.001

# Fallbacks for an absent cylinder_params field. cylinder_dimensions below is
# the ONE reader both app/validation.py and app/geometry_spec.py call, so the
# two can never disagree about what an absent field means. Height no longer
# tracks card_height (decoupled 2026-08-31); it is the VERSION 1 STANDARD
# barrel, the height every previously shipped V1 gear model pairs with, so a
# default-height cylinder passes the S7 gate again. The 1 mm card-shelf
# barrel (54) is Embosser Version 2 ONLY: its UI preset always sends the
# height explicitly, and an absent-height V2 request draws the soft S-V5
# size warning rather than silently building at 54.
DEFAULT_CYLINDER_DIAMETER_MM = 30.75
DEFAULT_CYLINDER_HEIGHT_MM = 52.0

# Which vendored asset a plate carries. Cylinder A (the embossing/positive
# plate) takes the A gears, Cylinder B (the counter/negative plate) the B ones;
# B's teeth are clocked to mesh with A's at the sample pose.
GEAR_ASSET_BY_PLATE = {'positive': 'gears_a', 'negative': 'gears_b'}

# Hidden weld ring at each gear/barrel interface (audit section 5). The gear
# meets the barrel on an exactly coincident face, which the project's
# printability rules forbid and float32 STL rounding can turn into a pinch
# edge, so a 0.1 mm tall annulus straddles the contact plane. It is proved
# solid on both sides at every probed angle and is entirely buried: measured
# contribution to the roller's volume is 0.000000 mm3, and no external surface
# changes anywhere.
WELD_RING_R_IN_MM = 8.0
WELD_RING_R_OUT_MM = 13.0
WELD_RING_HEIGHT_MM = 0.1

# Decision D-8a. The raised tactile row arrows are 10 mm long on 10 mm line
# spacing, so each arrow's apex touches the next arrow's base exactly; float32
# STL rounding welds that tangency into a non-manifold pinch edge. Gear mode
# promises a watertight one-piece roller, so while it is on the raised arrow
# outline grows by 5 um and the tangency becomes a real overlap. Physically
# negligible (2.5% of the recess nesting clearance, far below 0.1 mm print
# accuracy) and applied ONLY in gear mode, so toggle-off geometry keeps the
# exact tangency it ships with today. Recess arrows are untouched - their
# 0.2 mm clearance growth already overlaps.
GEAR_ARROW_WELD_MM = 0.005


def cylinder_dimensions(cylinder_params: dict) -> tuple[float, float]:
    """
    Read (diameter, height) from a request's cylinder_params.

    Both spellings of each key are accepted because both appear on the wire;
    app/geometry_spec.py calls this so there is exactly one such reader.
    """
    diameter = float(cylinder_params.get('diameter', cylinder_params.get('diameter_mm', DEFAULT_CYLINDER_DIAMETER_MM)))
    height = float(cylinder_params.get('height', cylinder_params.get('height_mm', DEFAULT_CYLINDER_HEIGHT_MM)))
    return diameter, height


def matches_reference_roller(diameter: float, height: float) -> bool:
    """True when this cylinder is the one the vendored gears were measured against."""
    return (
        abs(diameter - GEAR_BARREL_DIAMETER_MM) <= GEAR_BARREL_TOLERANCE_MM
        and abs(height - GEAR_BARREL_HEIGHT_MM) <= GEAR_BARREL_TOLERANCE_MM
    )


def _format_mm(value: float) -> str:
    """
    Render a millimetre value the way a person writes it: 52, not 52.0.

    The signed S7 sentence says "30.8 mm x 52 mm", and Python's default float
    formatting would say "52.0 mm" - the same words, a different number. The
    UI writes the signed form, so the server has to as well, or a user who
    reads the live warning and then triggers the error sees two spellings of
    one message.
    """
    text = f'{value:.3f}'.rstrip('0').rstrip('.')
    return text if text else '0'


def reference_roller_message(diameter: float, height: float) -> str:
    """
    The S7 sentence, signed off by Brennen 2026-08-24 - reword only with his
    sign-off. Used as the request-level rejection and, for direct callers that
    bypass validation, as the spec warning.
    """
    return (
        f'Integrated gears are matched to the reference roller and only fit a '
        f'{_format_mm(GEAR_BARREL_DIAMETER_MM)} mm x {_format_mm(GEAR_BARREL_HEIGHT_MM)} mm cylinder. '
        f'Received {_format_mm(diameter)} mm x {_format_mm(height)} mm.'
    )


def weld_rings(height: float) -> list[dict]:
    """
    The two hidden weld rings, one at each gear/barrel interface.

    The worker's cylinder is centred on z=0, so the interfaces sit at
    +/- height/2 - computed, never hardcoded to +/-26, even though the
    validation gate means height is always 52.000 on the request path.
    """
    half_height = height / 2.0
    return [
        {
            'z_center': z_center,
            'r_in': WELD_RING_R_IN_MM,
            'r_out': WELD_RING_R_OUT_MM,
            'height': WELD_RING_HEIGHT_MM,
        }
        for z_center in (-half_height, half_height)
    ]
