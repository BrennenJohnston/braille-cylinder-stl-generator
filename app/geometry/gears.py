"""
Gear-integrated one-piece roller (BETA) constants and math.

Gear mode ships each cylinder as ONE watertight solid with its top and bottom
drive gears already attached, instead of a bare barrel that separately printed
gears are pushed onto. Meshing the two rollers' gears is what holds the paired
cylinders rotationally synchronised.

Everything here is a pure function or a constant: no I/O, no globals mutated,
no settings objects. Lengths are millimetres, angles degrees.

The gears are NOT parametric. They are a 1:1 replication of the gear rings of
Brennen's Version 1 gear holders (since 2026-09-28; the 2026-08-24 sample set
before that - same teeth, but its B hub was the newer design's and never fitted
the Version 1 housing), vendored as static/assets/gears/gears_a.bin and
gears_b.bin and regenerated only by scripts/derive_gear_assets.py. Every
number below was measured from the 2026-08-24 samples (research folder
01_SAMPLE_GEOMETRY_AUDIT.md), whose tooth ring the holders share, and
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

# Embosser Version 2 fixed gears (2026-09-20 programme, sub-plan B): the v8
# Version 2 gear set, vendored as static/assets/gears/v2_gears_a.bin and
# v2_gears_b.bin and regenerated only by scripts/derive_gear_assets_v2.py
# (research folder 01_V2_GEAR_AUDIT.md). Same tooth count, tip radius and
# 10 mm thickness as the Version 1 set; the 15 mm keyed pegs sit inside the
# barrel and the gear bodies sit at |z| 27..37 around the 54 mm Version 2
# barrel. Its reference size is read from app/geometry/version2.py, the one
# place every Version 2 number lives - never retyped here.
V2_GEAR_ASSET_BY_PLATE = {'positive': 'v2_gears_a', 'negative': 'v2_gears_b'}
SUPPORTED_VERSIONS = (1, 2)


def _require_version(version: int) -> int:
    if version not in SUPPORTED_VERSIONS:
        raise ValueError(f'unknown embosser version {version!r}; known: {SUPPORTED_VERSIONS}')
    return version


def gear_asset_for(plate_type: str, version: int = 1) -> str:
    """The vendored gear set this plate carries for this embosser version."""
    table = GEAR_ASSET_BY_PLATE if _require_version(version) == 1 else V2_GEAR_ASSET_BY_PLATE
    if plate_type not in table:
        raise ValueError(f'unknown plate type {plate_type!r}; known: {sorted(table)}')
    return table[plate_type]


def reference_barrel(version: int = 1) -> tuple[float, float]:
    """
    (diameter, height) the vendored gears of this version were measured against.

    Version 2's size comes from app/geometry/version2.py, imported here rather
    than at module level because that module imports _format_mm from this one.
    """
    if _require_version(version) == 1:
        return GEAR_BARREL_DIAMETER_MM, GEAR_BARREL_HEIGHT_MM
    from app.geometry import version2

    return version2.V2_BARREL_DIAMETER_MM, version2.V2_BARREL_HEIGHT_MM


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

# Each gear body is this thick (both sets, measured; the manifests record it).
# A fused roller's bed plane therefore sits height/2 + this below the barrel's
# centre, which is where the Version 2 axis cuts measure from (version2.py).
GEAR_BODY_THICKNESS_MM = 10.0

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

# The housing-pin socket in each Version 1 gear, MEASURED 2026-09-30 by vertex
# fits on the vendored rings: identical on A1, A2, B1 and B2, and concentric
# with the roller axis to 0.00003 mm. From the gear's outer face (its mouth):
# a 1.0 mm 45 degree chamfer, the r 7.0 key bore to depth 6.7, a 45 degree
# taper to the r 5.2 rim at depth 8.5, and there a FLAT blind end, 1.5 mm from
# the barrel face. The Version 1 housing pin (diameter 13.7 x 6.25 then
# 10.17 x 2, so 8.25 deep) is a close fit in it: recorded hardware, not ours
# to adjust, and the axis cuts below may not touch any of it (Brennen,
# 2026-09-30). BOTTOM gears print mouth down; TOP gears mouth up.
V1_GEAR_SOCKET = {
    'positive': {
        'gear': 'A2',
        'mouth_chamfer': 1.0,
        'bore_radius': 7.0,
        'taper_start_depth': 6.7,
        'rim_radius': 5.2,
        'depth': 8.5,
    },
    'negative': {
        'gear': 'B2',
        'mouth_chamfer': 1.0,
        'bore_radius': 7.0,
        'taper_start_depth': 6.7,
        'rim_radius': 5.2,
        'depth': 8.5,
    },
}
V1_TOP_GEAR_SOCKET = {
    'positive': {
        'gear': 'A1',
        'mouth_chamfer': 1.0,
        'bore_radius': 7.0,
        'taper_start_depth': 6.7,
        'rim_radius': 5.2,
        'depth': 8.5,
    },
    'negative': {
        'gear': 'B1',
        'mouth_chamfer': 1.0,
        'bore_radius': 7.0,
        'taper_start_depth': 6.7,
        'rim_radius': 5.2,
        'depth': 8.5,
    },
}

# The Version 1 fused roller's vent and self-supporting sockets (2026-09-30,
# Brennen's approved plan: Version 2's D-1 and D-K5 with the vent, ported).
# Printed as generated, bottom gear down, the bottom socket's flat blind end
# is a roof over air that needed support inside the hole; a cone continuing
# the socket's own 45 degree taper up to a 2 mm vent along the whole axis
# lays nothing over air, and the vent lets the roller come off its pin with
# no vacuum. Unlike Version 2's cone, which grows into its taper, this one
# runs V1_SOCKET_CONE_INSET_MM INSIDE it, so the mouth, the key bore and the
# taper stay exactly as vendored (decision 1); a ring that narrow is all that
# remains of the flat end, far below anything a printer can lay.
V1_VENT_RADIUS_MM = 1.0
V1_VENT_OVERSHOOT_MM = 1.0  # past both gear mouths
V1_SOCKET_CONE_OVERLAP_MM = 0.5  # the cone starts this far short of the blind end, in the socket's air
# How far inside the socket's taper the cone runs, touching none of it. The
# plan said 0.01; implementing it showed the taper's flat facets (a strip
# between a 57-gon and a 49-gon) dip up to V1_SOCKET_TAPER_FACET_DIP_MM inside
# the ideal cone, and the cutter's corners sit ON its nominal radius, so at
# 0.01 they clipped the taper by up to 0.0004 mm. At 0.02 every point sampled
# on the mouth chamfer, key bore and taper comes through the cut at 0.000000 mm
# (measured 2026-09-30, both cylinders). axis_cut_blocks refuses any inset
# that does not clear the dip, recorded as a bound on the measured 0.01071.
V1_SOCKET_TAPER_FACET_DIP_MM = 0.0108
V1_SOCKET_CONE_INSET_MM = 0.02
V1_SOCKET_CONE_VENT_GROWTH_MM = 0.01  # its narrow end overlaps the vent by this, nothing coplanar


def cylinder_dimensions(cylinder_params: dict) -> tuple[float, float]:
    """
    Read (diameter, height) from a request's cylinder_params.

    Both spellings of each key are accepted because both appear on the wire;
    app/geometry_spec.py calls this so there is exactly one such reader.
    """
    diameter = float(cylinder_params.get('diameter', cylinder_params.get('diameter_mm', DEFAULT_CYLINDER_DIAMETER_MM)))
    height = float(cylinder_params.get('height', cylinder_params.get('height_mm', DEFAULT_CYLINDER_HEIGHT_MM)))
    return diameter, height


def matches_reference_roller(diameter: float, height: float, version: int = 1) -> bool:
    """True when this cylinder is the one this version's vendored gears were measured against."""
    want_diameter, want_height = reference_barrel(version)
    return (
        abs(diameter - want_diameter) <= GEAR_BARREL_TOLERANCE_MM
        and abs(height - want_height) <= GEAR_BARREL_TOLERANCE_MM
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


def reference_roller_message(diameter: float, height: float, version: int = 1) -> str:
    """
    Version 1: the S7 sentence, signed off by Brennen 2026-08-24 - reword only
    with his sign-off. Version 2: S-G1, signed off by Brennen on 2026-09-21 (2026-09-20
    programme, phase B2); reword only with his sign-off. Used as the request-level rejection and, for direct
    callers that bypass validation, as the spec warning.
    """
    want_diameter, want_height = reference_barrel(version)
    received = f'Received {_format_mm(diameter)} mm x {_format_mm(height)} mm.'
    if version == 1:
        return (
            f'Integrated gears are matched to the reference roller and only fit a '
            f'{_format_mm(want_diameter)} mm x {_format_mm(want_height)} mm cylinder. {received}'
        )
    return (
        f'Fixed gears for the Version 2 embosser fit only a '
        f'{_format_mm(want_diameter)} mm x {_format_mm(want_height)} mm cylinder. {received}'
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


def _check_socket(socket: dict) -> None:
    """Refuse a socket table the inset cone could touch or would not continue."""
    taper_run = socket['depth'] - socket['taper_start_depth']
    if not socket['rim_radius'] < socket['bore_radius']:
        raise ValueError(f'{socket["gear"]} socket rim {socket["rim_radius"]} must be inside its bore')
    # The cone runs parallel to the taper, which holds only for a 45 degree taper.
    if abs((socket['bore_radius'] - socket['rim_radius']) - taper_run) > 1e-9:
        raise ValueError(f'{socket["gear"]} socket taper is not 45 degrees: {socket}')
    # The cone's base must sit on the taper, never beside the key bore.
    if not taper_run > V1_SOCKET_CONE_OVERLAP_MM:
        raise ValueError(
            f'{socket["gear"]} cone overlap {V1_SOCKET_CONE_OVERLAP_MM} reaches past the taper ({taper_run})'
        )


def axis_cut_blocks(plate_type: str, height: float) -> list[dict]:
    """
    The Version 1 fused roller's three axis cuts, taken LAST in the worker after
    every union: the vent the full length of the roller, the bottom socket's
    cone and the top socket's mirror cone (2026-09-30, Brennen's approved plan).

    z is measured from each gear's mouth, which sits height/2 + the gear's
    thickness from the barrel's centre. Each cone starts V1_SOCKET_CONE_OVERLAP_MM
    short of its socket's blind end, in the socket's air, at the taper's radius
    there less V1_SOCKET_CONE_INSET_MM, and runs at 45 degrees to the vent: so
    its side is parallel to the taper and inside it, and it removes material
    only beyond the old blind end. Same block shape as Version 2's
    (version2.axis_cut_blocks): z_from < z_to with r_from at z_from, so the top
    cone is emitted apex first, and the worker and tests/test_golden.py cut both
    versions the same way.
    """
    if plate_type not in V1_GEAR_SOCKET or plate_type not in V1_TOP_GEAR_SOCKET:
        raise ValueError(f'unknown plate type {plate_type!r}; known: {sorted(V1_GEAR_SOCKET)}')
    if height <= 0:
        raise ValueError(f'cylinder height must be positive, got {height}')
    if not V1_SOCKET_TAPER_FACET_DIP_MM < V1_SOCKET_CONE_INSET_MM < V1_SOCKET_CONE_OVERLAP_MM:
        raise ValueError(
            f'cone inset {V1_SOCKET_CONE_INSET_MM} must clear the taper facets '
            f'({V1_SOCKET_TAPER_FACET_DIP_MM}) and stay below the overlap'
        )

    bottom = V1_GEAR_SOCKET[plate_type]
    top = V1_TOP_GEAR_SOCKET[plate_type]
    _check_socket(bottom)
    _check_socket(top)
    narrow = V1_VENT_RADIUS_MM + V1_SOCKET_CONE_VENT_GROWTH_MM
    if not 0 < V1_VENT_RADIUS_MM < WELD_RING_R_IN_MM:
        raise ValueError(f'vent radius {V1_VENT_RADIUS_MM} mm would reach the weld rings')

    mouth = height / 2.0 + GEAR_BODY_THICKNESS_MM
    reach = mouth + V1_VENT_OVERSHOOT_MM
    vent = {
        'kind': 'vent',
        'radius': V1_VENT_RADIUS_MM,
        'z_from': round(-reach, 6),
        'z_to': round(reach, 6),
    }

    blocks = [vent]
    for socket, end in ((bottom, 'bottom'), (top, 'top')):
        wide = socket['rim_radius'] + V1_SOCKET_CONE_OVERLAP_MM - V1_SOCKET_CONE_INSET_MM
        if not narrow < wide < WELD_RING_R_IN_MM:
            raise ValueError(f'{socket["gear"]} cone must narrow from r {wide} to the vent inside the weld rings')
        rise = wide - narrow  # 45 degrees
        if end == 'bottom':
            start = -mouth + socket['depth'] - V1_SOCKET_CONE_OVERLAP_MM
            blocks.append(
                {
                    'kind': 'cone',
                    'gear': socket['gear'],
                    'end': end,
                    'z_from': round(start, 6),
                    'r_from': round(wide, 6),
                    'z_to': round(start + rise, 6),
                    'r_to': round(narrow, 6),
                }
            )
        else:
            start = mouth - socket['depth'] + V1_SOCKET_CONE_OVERLAP_MM
            blocks.append(
                {
                    'kind': 'cone',
                    'gear': socket['gear'],
                    'end': end,
                    'z_from': round(start - rise, 6),
                    'r_from': round(narrow, 6),
                    'z_to': round(start, 6),
                    'r_to': round(wide, 6),
                }
            )
    return blocks
