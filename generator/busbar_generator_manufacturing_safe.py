import cadquery as cq
import math

# ===== PATCH: manufacturing fidelity =====
class FeatureError(Exception):
    """Raised when a feature/bend cannot be produced exactly as the drawing specifies.
    For manufacturing, we refuse to emit an approximate STEP."""
    pass

def _radius_for_bend(bend_radius, index):
    """PATCH: per-bend radius. Accepts a list (one per bend) or a scalar (broadcast)."""
    if isinstance(bend_radius, (list, tuple)):
        if index < len(bend_radius):
            return bend_radius[index]
        raise FeatureError(f"No bend radius provided for bend index {index}")
    return bend_radius
# ===== END PATCH =====



# ============================================================
# 1. USER INPUT AREA
# ============================================================
BAR_THICKNESS = 10
BAR_WIDTH = 80
BEND_RADIUS = 10

DRAWING_LENGTHS = [97, 210, 72.9, 200.998]

BEND_ANGLES = [90, -10, 10]

LENGTH_REFERENCE = "outside"

LENGTH_CORRECTION_RULES = {
    1: {"start": None, "end": "outside"},
    2: {"start": "outside", "end": None},
    3: {"start": None, "end": None},
    4: {"start": None, "end": None},
}

HOLES_BY_SEGMENT = {
    1: {
    },

    2: {
        "j": [
            (30, 24),
            (30, 56),
        ],
        
        "i": [
            (50, 24),
            (50, 56),
        ],

    },

    3: {
    },

    4: {
        "b": [
            (182.2, 24),
            (182.2, 56),
            (150.2, 24),
            (150.2, 56),
        ],
    },

}

EXPORT_STEP = True
filename = "AGSC80185-01"
EXPORT_FILENAME = filename + ".step"


Customcircledim = 5.5
Customslotwidth = 11
Customslotlength = 16
Customcircledim2 = 0

# ============================================================
# END USER INPUT AREA
# ============================================================
# ============================================================
# 2. BASIC VECTOR FUNCTIONS
# ============================================================

def rotate_2d(vector, angle_deg):
    angle_rad = math.radians(angle_deg)
    x, y = vector

    return (
        x * math.cos(angle_rad) - y * math.sin(angle_rad),
        x * math.sin(angle_rad) + y * math.cos(angle_rad),
    )


def add_2d(a, b):
    return (
        a[0] + b[0],
        a[1] + b[1],
    )


def multiply_2d(vector, value):
    return (
        vector[0] * value,
        vector[1] * value,
    )


def polar(center, radius, angle_deg):
    angle_rad = math.radians(angle_deg)

    return (
        center[0] + radius * math.cos(angle_rad),
        center[1] + radius * math.sin(angle_rad),
    )


def angle_of_vector(vector):
    return math.degrees(math.atan2(vector[1], vector[0]))


def is_number(value):
    return isinstance(value, (int, float))


# ============================================================
# 3. CREATE ONE STRAIGHT SEGMENT
# ============================================================

def create_segment(
    segment_length,
    bar_thickness,
    bar_width,
    segment_start_xy,
    segment_angle_deg,
):
    """
    Creates one straight rectangular busbar segment.

    Local segment coordinates:
    - local X = segment length
    - local Y = material thickness
    - local Z = bar width

    The segment starts at segment_start_xy and points along segment_angle_deg.
    """

    segment = (
        cq.Workplane("XY")
        .box(
            segment_length,
            bar_thickness,
            bar_width,
            centered=(False, True, False),
        )
        .rotate((0, 0, 0), (0, 0, 1), segment_angle_deg)
        .translate((segment_start_xy[0], segment_start_xy[1], 0))
    )

    return segment


# ============================================================
# 4. BASIC CUTTER FUNCTIONS
# ============================================================

def make_round_cutter(
    radius,
    center_from_top,
    center_from_left,
    segment_start_xy,
    segment_angle_deg,
    cut_depth,
):
    """
    Makes a cylindrical cutter through local Y thickness direction.
    """

    start_local = cq.Vector(
        center_from_top,
        -cut_depth / 2,
        center_from_left,
    )

    direction_local = cq.Vector(0, 1, 0)

    cutter_solid = cq.Solid.makeCylinder(
        radius,
        cut_depth,
        start_local,
        direction_local,
    )

    cutter = (
        cq.Workplane()
        .add(cutter_solid)
        .rotate((0, 0, 0), (0, 0, 1), segment_angle_deg)
        .translate((segment_start_xy[0], segment_start_xy[1], 0))
    )

    return cutter


def make_box_cutter(
    size_along_segment,
    size_through_thickness,
    size_along_width,
    center_from_top,
    center_from_left,
    segment_start_xy,
    segment_angle_deg,
):
    """
    Makes a box cutter.

    Local cutter dimensions:
    - X = along segment length
    - Y = through material thickness
    - Z = along bar width
    """

    cutter = (
        cq.Workplane("XY")
        .box(
            size_along_segment,
            size_through_thickness,
            size_along_width,
            centered=(True, True, True),
        )
        .translate((center_from_top, 0, center_from_left))
        .rotate((0, 0, 0), (0, 0, 1), segment_angle_deg)
        .translate((segment_start_xy[0], segment_start_xy[1], 0))
    )

    return cutter


# ============================================================
# 5. FEATURE FIT CHECKS
# ============================================================

def feature_fits(
    center_from_top,
    center_from_left,
    segment_length,
    bar_width,
    margin_along_segment,
    margin_along_width,
):
    """
    Checks if a feature fits inside the face.

    It returns False instead of crashing.
    """

    if center_from_top - margin_along_segment < 0:
        return False

    if center_from_top + margin_along_segment > segment_length:
        return False

    if center_from_left - margin_along_width < 0:
        return False

    if center_from_left + margin_along_width > bar_width:
        return False

    return True


# ============================================================
# 6. ONE LARGE FEATURE / HOLE FUNCTION
# ============================================================

def cut_feature_by_type(
    segment,
    feature_type,
    center_from_top,
    center_from_left,
    segment_start_xy,
    segment_angle_deg,
    segment_length,
    bar_thickness,
    bar_width,
):
    """
    Main feature function.

    This is where the hardcoded feature library lives.

    The feature point is always the CENTER of the feature:
    - center_from_top  = distance down segment length
    - center_from_left = distance from Z=0 side

    Types:
    - a, b, c, d are round holes
    - e, f, g, h are compound slots
    """

    feature_type = str(feature_type).lower().strip()

    cut_depth = bar_thickness + 2


    # --------------------------------------------------------
    # a = 11 diameter round hole
    # --------------------------------------------------------
    if feature_type == "a":
        diameter = 11
        radius = diameter / 2

        if not feature_fits(
            center_from_top,
            center_from_left,
            segment_length,
            bar_width,
            radius,
            radius,
        ):
            raise FeatureError("Type a hole does not fit inside the bar at the given position. STEP refused — input does not match a manufacturable feature.")
            return segment

        cutter = make_round_cutter(
            radius=radius,
            center_from_top=center_from_top,
            center_from_left=center_from_left,
            segment_start_xy=segment_start_xy,
            segment_angle_deg=segment_angle_deg,
            cut_depth=cut_depth,
        )

        return segment.cut(cutter)


    # --------------------------------------------------------
    # b = 13 diameter round hole
    # --------------------------------------------------------
    elif feature_type == "b":
        diameter = 13
        radius = diameter / 2

        if not feature_fits(
            center_from_top,
            center_from_left,
            segment_length,
            bar_width,
            radius,
            radius,
        ):
            raise FeatureError("Type b hole does not fit inside the bar at the given position. STEP refused — input does not match a manufacturable feature.")
            return segment

        cutter = make_round_cutter(
            radius=radius,
            center_from_top=center_from_top,
            center_from_left=center_from_left,
            segment_start_xy=segment_start_xy,
            segment_angle_deg=segment_angle_deg,
            cut_depth=cut_depth,
        )

        return segment.cut(cutter)


    # --------------------------------------------------------
    # c = 14 diameter round hole
    # --------------------------------------------------------
    elif feature_type == "c":
        diameter = 14
        radius = diameter / 2

        if not feature_fits(
            center_from_top,
            center_from_left,
            segment_length,
            bar_width,
            radius,
            radius,
        ):
            raise FeatureError("Type c hole does not fit inside the bar at the given position. STEP refused — input does not match a manufacturable feature.")
            return segment

        cutter = make_round_cutter(
            radius=radius,
            center_from_top=center_from_top,
            center_from_left=center_from_left,
            segment_start_xy=segment_start_xy,
            segment_angle_deg=segment_angle_deg,
            cut_depth=cut_depth,
        )

        return segment.cut(cutter)

    # --------------------------------------------------------
    # d = 22 diameter round hole
    # --------------------------------------------------------
    elif feature_type == "d":
        diameter = 22
        radius = diameter / 2

        if not feature_fits(
            center_from_top,
            center_from_left,
            segment_length,
            bar_width,
            radius,
            radius,
        ):
            raise FeatureError("Type d hole does not fit inside the bar at the given position. STEP refused — input does not match a manufacturable feature.")
            return segment

        cutter = make_round_cutter(
            radius=radius,
            center_from_top=center_from_top,
            center_from_left=center_from_left,
            segment_start_xy=segment_start_xy,
            segment_angle_deg=segment_angle_deg,
            cut_depth=cut_depth,
        )

        return segment.cut(cutter)

    # --------------------------------------------------------
    # e = 13x18 compound slot 
    # --------------------------------------------------------

    elif feature_type == "e":
        """
        Compound slot.

        Definition:
        - 13 mm runs along the WIDTH of the segment, meaning Z direction.
        - 3 mm runs along the LENGTH of the segment.

        Local face interpretation:
        - X / from_top direction = segment length
        - Z / from_left direction = bar width

        Shape:
        - 3 x 13 rectangular box centered at the provided point.
        - Two 13 diameter circular cutters.
        - Each circle center lies on the midpoint of one of the 13 mm long sides.

        Therefore:
        - rectangle size along segment length = 3
        - rectangle size along bar width Z = 13
        - circle centers are shifted by +/- 1.5 along segment length
        - circle diameter = 13
        """

        slot_length_along_segment = 3
        slot_width_along_z = 13
        circle_diameter = 13
        circle_radius = circle_diameter / 2

        # Circle centers are on the midpoint of the two 13 mm sides.
        # Since the 3 mm dimension is along segment length,
        # shift the circles by +/- 1.5 along the segment.
        circle_offset_along_segment = slot_length_along_segment / 2

        # Total feature margin:
        # Along segment length, circle radius plus 1.5 offset.
        # Along Z width, just circle radius.
        margin_along_segment = circle_radius + circle_offset_along_segment
        margin_along_width = circle_radius

        if not feature_fits(
            center_from_top,
            center_from_left,
            segment_length,
            bar_width,
            margin_along_segment,
            margin_along_width,
        ):
            raise FeatureError("Type e slot does not fit inside the bar at the given position. STEP refused — input does not match a manufacturable feature.")
            return segment

        # 1. Cut the 3 x 13 rectangular part
        box_cutter = make_box_cutter(
            size_along_segment=slot_length_along_segment,
            size_through_thickness=cut_depth,
            size_along_width=slot_width_along_z,
            center_from_top=center_from_top,
            center_from_left=center_from_left,
            segment_start_xy=segment_start_xy,
            segment_angle_deg=segment_angle_deg,
        )

        segment = segment.cut(box_cutter)

        # 2. First 13 dia circle
        # Shift along segment length direction
        circle_1_center_from_top = center_from_top + circle_offset_along_segment

        circle_1 = make_round_cutter(
            radius=circle_radius,
            center_from_top=circle_1_center_from_top,
            center_from_left=center_from_left,
            segment_start_xy=segment_start_xy,
            segment_angle_deg=segment_angle_deg,
            cut_depth=cut_depth,
        )

        segment = segment.cut(circle_1)

        # 3. Second 13 dia circle
        # Shift along opposite segment length direction
        circle_2_center_from_top = center_from_top - circle_offset_along_segment

        circle_2 = make_round_cutter(
            radius=circle_radius,
            center_from_top=circle_2_center_from_top,
            center_from_left=center_from_left,
            segment_start_xy=segment_start_xy,
            segment_angle_deg=segment_angle_deg,
            cut_depth=cut_depth,
        )

        segment = segment.cut(circle_2)

        return segment

    # --------------------------------------------------------
    # f = 9x14 compound slot
    # --------------------------------------------------------
    elif feature_type == "f":

        slot_length_along_segment = 5
        slot_width_along_z = 9
        circle_diameter = 9
        circle_radius = circle_diameter / 2

        circle_offset_along_segment = slot_length_along_segment / 2

        # Total feature margin:
        # Along segment length, circle radius plus offset.
        # Along Z width, just circle radius.
        margin_along_segment = circle_radius + circle_offset_along_segment
        margin_along_width = circle_radius

        if not feature_fits(
            center_from_top,
            center_from_left,
            segment_length,
            bar_width,
            margin_along_segment,
            margin_along_width,
        ):
            raise FeatureError("Type d slot does not fit inside the bar at the given position. STEP refused — input does not match a manufacturable feature.")
            return segment

        # 1. Cut the 3 x 13 rectangular part
        box_cutter = make_box_cutter(
            size_along_segment=slot_length_along_segment,
            size_through_thickness=cut_depth,
            size_along_width=slot_width_along_z,
            center_from_top=center_from_top,
            center_from_left=center_from_left,
            segment_start_xy=segment_start_xy,
            segment_angle_deg=segment_angle_deg,
        )

        segment = segment.cut(box_cutter)

        # 2. First circle
        # Shift along segment length direction
        circle_1_center_from_top = center_from_top + circle_offset_along_segment

        circle_1 = make_round_cutter(
            radius=circle_radius,
            center_from_top=circle_1_center_from_top,
            center_from_left=center_from_left,
            segment_start_xy=segment_start_xy,
            segment_angle_deg=segment_angle_deg,
            cut_depth=cut_depth,
        )

        segment = segment.cut(circle_1)

        # 3. Second circle
        # Shift along opposite segment length direction
        circle_2_center_from_top = center_from_top - circle_offset_along_segment

        circle_2 = make_round_cutter(
            radius=circle_radius,
            center_from_top=circle_2_center_from_top,
            center_from_left=center_from_left,
            segment_start_xy=segment_start_xy,
            segment_angle_deg=segment_angle_deg,
            cut_depth=cut_depth,
        )

        segment = segment.cut(circle_2)

        return segment


    # --------------------------------------------------------
    # g = 11x15 compound slot
    # --------------------------------------------------------
    elif feature_type == "g":

        slot_length_along_segment = 4
        slot_width_along_z = 11
        circle_diameter = 11
        circle_radius = circle_diameter / 2

        circle_offset_along_segment = slot_length_along_segment / 2

        # Total feature margin:
        # Along segment length, circle radius plus 1.5 offset.
        # Along Z width, just circle radius.
        margin_along_segment = circle_radius + circle_offset_along_segment
        margin_along_width = circle_radius

        if not feature_fits(
            center_from_top,
            center_from_left,
            segment_length,
            bar_width,
            margin_along_segment,
            margin_along_width,
        ):
            raise FeatureError("Type d slot does not fit inside the bar at the given position. STEP refused — input does not match a manufacturable feature.")
            return segment

        # 1. Cut the 3 x 13 rectangular part
        box_cutter = make_box_cutter(
            size_along_segment=slot_length_along_segment,
            size_through_thickness=cut_depth,
            size_along_width=slot_width_along_z,
            center_from_top=center_from_top,
            center_from_left=center_from_left,
            segment_start_xy=segment_start_xy,
            segment_angle_deg=segment_angle_deg,
        )

        segment = segment.cut(box_cutter)

        # 2. First 13 dia circle
        # Shift along segment length direction
        circle_1_center_from_top = center_from_top + circle_offset_along_segment

        circle_1 = make_round_cutter(
            radius=circle_radius,
            center_from_top=circle_1_center_from_top,
            center_from_left=center_from_left,
            segment_start_xy=segment_start_xy,
            segment_angle_deg=segment_angle_deg,
            cut_depth=cut_depth,
        )

        segment = segment.cut(circle_1)

        # 3. Second 13 dia circle
        # Shift along opposite segment length direction
        circle_2_center_from_top = center_from_top - circle_offset_along_segment

        circle_2 = make_round_cutter(
            radius=circle_radius,
            center_from_top=circle_2_center_from_top,
            center_from_left=center_from_left,
            segment_start_xy=segment_start_xy,
            segment_angle_deg=segment_angle_deg,
            cut_depth=cut_depth,
        )

        segment = segment.cut(circle_2)

        return segment

    # --------------------------------------------------------
    # h = 5 diameter round hole
    # --------------------------------------------------------
    elif feature_type == "h":
        diameter = 5
        radius = diameter / 2

        if not feature_fits(
            center_from_top,
            center_from_left,
            segment_length,
            bar_width,
            radius,
            radius,
        ):
            raise FeatureError("Type h hole does not fit inside the bar at the given position. STEP refused — input does not match a manufacturable feature.")
            return segment

        cutter = make_round_cutter(
            radius=radius,
            center_from_top=center_from_top,
            center_from_left=center_from_left,
            segment_start_xy=segment_start_xy,
            segment_angle_deg=segment_angle_deg,
            cut_depth=cut_depth,
        )

        return segment.cut(cutter)

    # --------------------------------------------------------
    # i = CUSTOM compound slot
    # --------------------------------------------------------
    elif feature_type == "i":

        slot_length_along_segment = Customslotlength-Customslotwidth
        slot_width_along_z = Customslotwidth
        circle_diameter = Customslotwidth
        circle_radius = circle_diameter / 2

        circle_offset_along_segment = slot_length_along_segment / 2

        margin_along_segment = circle_radius + circle_offset_along_segment
        margin_along_width = circle_radius

        if not feature_fits(
            center_from_top,
            center_from_left,
            segment_length,
            bar_width,
            margin_along_segment,
            margin_along_width,
        ):
            raise FeatureError("Type i slot does not fit inside the bar at the given position. STEP refused — input does not match a manufacturable feature.")
            return segment

        # 1. Cut the rectangular part
        box_cutter = make_box_cutter(
            size_along_segment=slot_length_along_segment,
            size_through_thickness=cut_depth,
            size_along_width=slot_width_along_z,
            center_from_top=center_from_top,
            center_from_left=center_from_left,
            segment_start_xy=segment_start_xy,
            segment_angle_deg=segment_angle_deg,
        )

        segment = segment.cut(box_cutter)

        # 2. First 13 dia circle
        # Shift along segment length direction
        circle_1_center_from_top = center_from_top + circle_offset_along_segment

        circle_1 = make_round_cutter(
            radius=circle_radius,
            center_from_top=circle_1_center_from_top,
            center_from_left=center_from_left,
            segment_start_xy=segment_start_xy,
            segment_angle_deg=segment_angle_deg,
            cut_depth=cut_depth,
        )

        segment = segment.cut(circle_1)

        # 3. Second 13 dia circle
        # Shift along opposite segment length direction
        circle_2_center_from_top = center_from_top - circle_offset_along_segment

        circle_2 = make_round_cutter(
            radius=circle_radius,
            center_from_top=circle_2_center_from_top,
            center_from_left=center_from_left,
            segment_start_xy=segment_start_xy,
            segment_angle_deg=segment_angle_deg,
            cut_depth=cut_depth,
        )

        segment = segment.cut(circle_2)

        return segment

    # --------------------------------------------------------
    # j = CUSTOM round slot
    # --------------------------------------------------------
    elif feature_type == "j":

        diameter = Customcircledim
        radius = diameter / 2

        if not feature_fits(
            center_from_top,
            center_from_left,
            segment_length,
            bar_width,
            radius,
            radius,
        ):
            raise FeatureError("Type j hole does not fit inside the bar at the given position. STEP refused — input does not match a manufacturable feature.")
            return segment

        cutter = make_round_cutter(
            radius=radius,
            center_from_top=center_from_top,
            center_from_left=center_from_left,
            segment_start_xy=segment_start_xy,
            segment_angle_deg=segment_angle_deg,
            cut_depth=cut_depth,
        )

        return segment.cut(cutter)


    # --------------------------------------------------------
    # k = CUSTOM round slot 2
    # --------------------------------------------------------
    elif feature_type == "k":

        diameter = Customcircledim2
        radius = diameter / 2

        if not feature_fits(
            center_from_top,
            center_from_left,
            segment_length,
            bar_width,
            radius,
            radius,
        ):
            raise FeatureError("Type k hole does not fit inside the bar at the given position. STEP refused — input does not match a manufacturable feature.")
            return segment

        cutter = make_round_cutter(
            radius=radius,
            center_from_top=center_from_top,
            center_from_left=center_from_left,
            segment_start_xy=segment_start_xy,
            segment_angle_deg=segment_angle_deg,
            cut_depth=cut_depth,
        )

        return segment.cut(cutter)


    # --------------------------------------------------------
    # Unknown feature type = do nothing
    # --------------------------------------------------------
    else:
        raise FeatureError(f"Unknown feature type: {feature_type}. STEP refused.")
        return segment


# ============================================================
# 7. POSITION NORMALIZATION
# ============================================================

def normalize_position_list(positions):
    """
    Accepts either:

    "a": (20, 14)

    or:

    "a": [
        (20, 14),
        (20, 26),
    ]

    It returns a clean list of positions.
    """

    if positions is None:
        return []

    # Single tuple: (from_top, from_left)
    if isinstance(positions, tuple):
        return [positions]

    # Single list written like [20, 14]
    if (
        isinstance(positions, list)
        and len(positions) == 2
        and is_number(positions[0])
        and is_number(positions[1])
    ):
        return [positions]

    # Normal list of tuples
    if isinstance(positions, list):
        return positions

    return []


# ============================================================
# 8. MAKE ALL FEATURES ON CURRENT SEGMENT
# ============================================================

def make_holes(
    segment,
    segment_holes_dictionary,
    segment_start_xy,
    segment_angle_deg,
    segment_length,
    bar_thickness,
    bar_width,
):
    """
    Loops through the nested dictionary for one segment.

    Example input:

    {
        "a": [(20, 14), (20, 26)],
        "d": [(80, 20)],
    }

    Empty dictionary means no features.
    """

    if not segment_holes_dictionary:
        return segment

    for feature_type, positions in segment_holes_dictionary.items():
        position_list = normalize_position_list(positions)

        if not position_list:
            continue

        for position in position_list:
            if len(position) < 2:
                continue

            center_from_top = position[0]
            center_from_left = position[1]

            if not is_number(center_from_top) or not is_number(center_from_left):
                raise FeatureError(f"Feature {feature_type}: invalid position {position}. STEP refused.")
                continue

            segment = cut_feature_by_type(
                segment=segment,
                feature_type=feature_type,
                center_from_top=center_from_top,
                center_from_left=center_from_left,
                segment_start_xy=segment_start_xy,
                segment_angle_deg=segment_angle_deg,
                segment_length=segment_length,
                bar_thickness=bar_thickness,
                bar_width=bar_width,
            )

    return segment


# ============================================================
# 9. MAKE BEND BODY
# ============================================================

def make_bend(
    segment_end_xy,
    segment_angle_deg,
    bend_angle_clockwise,
    bar_thickness,
    bar_width,
    bend_radius,
):
    """
    Creates curved bend body after a segment.

    Positive bend_angle_clockwise = clockwise
    Negative bend_angle_clockwise = counterclockwise

    Returns:
    - bend body
    - next segment start point
    - next segment angle
    """

    if bend_angle_clockwise is None:
        return None, segment_end_xy, segment_angle_deg

    if abs(bend_angle_clockwise) < 0.000001:
        return None, segment_end_xy, segment_angle_deg

    if bend_radius <= 0:
        raise FeatureError("Bend radius must be positive. STEP refused.")

    if abs(bend_angle_clockwise) >= 180:
        raise FeatureError("Bend angle >= 180 degrees not supported. STEP refused.")

    turn_angle = -bend_angle_clockwise
    next_segment_angle = segment_angle_deg + turn_angle

    left_normal = rotate_2d((0, 1), segment_angle_deg)
    right_normal = rotate_2d((0, -1), segment_angle_deg)

    if bend_angle_clockwise > 0:
        inner_normal = right_normal
    else:
        inner_normal = left_normal

    inner_radius = bend_radius
    outer_radius = bend_radius + bar_thickness
    center_radius = bend_radius + bar_thickness / 2

    bend_center = add_2d(
        segment_end_xy,
        multiply_2d(inner_normal, center_radius),
    )

    start_inner_vector = multiply_2d(inner_normal, -inner_radius)
    start_outer_vector = multiply_2d(inner_normal, -outer_radius)

    start_inner_angle = angle_of_vector(start_inner_vector)
    start_outer_angle = angle_of_vector(start_outer_vector)

    end_inner_angle = start_inner_angle + turn_angle
    end_outer_angle = start_outer_angle + turn_angle

    mid_inner_angle = start_inner_angle + turn_angle / 2
    mid_outer_angle = start_outer_angle + turn_angle / 2

    inner_start = polar(bend_center, inner_radius, start_inner_angle)
    inner_mid = polar(bend_center, inner_radius, mid_inner_angle)
    inner_end = polar(bend_center, inner_radius, end_inner_angle)

    outer_start = polar(bend_center, outer_radius, start_outer_angle)
    outer_mid = polar(bend_center, outer_radius, mid_outer_angle)
    outer_end = polar(bend_center, outer_radius, end_outer_angle)

    bend_body = (
        cq.Workplane("XY")
        .moveTo(*inner_start)
        .threePointArc(inner_mid, inner_end)
        .lineTo(*outer_end)
        .threePointArc(outer_mid, outer_start)
        .close()
        .extrude(bar_width)
    )

    start_center_vector = multiply_2d(inner_normal, -center_radius)
    end_center_vector = rotate_2d(start_center_vector, turn_angle)

    next_segment_start_xy = add_2d(
        bend_center,
        end_center_vector,
    )

    return bend_body, next_segment_start_xy, next_segment_angle


# ============================================================
# 10. UNION FUNCTION
# ============================================================

def union_parts(parts):
    clean_parts = [part for part in parts if part is not None]

    if not clean_parts:
        return None

    final_part = clean_parts[0]

    for part in clean_parts[1:]:
        final_part = final_part.union(part)

    return final_part

def bend_setback_for_drawing_dimension(
    bend_angle_deg,
    bend_radius,
    bar_thickness,
    reference="outside",
):
    """
    Calculates how much straight length is eaten by the bend.

    Use:
    - reference="outside" for normal drawing outside dimensions
    - reference="inside" if the drawing dimension is taken from the inside line
    - reference="centerline" if the drawing dimension is taken from the centerline

    For your drawings, use "outside" most of the time.
    """

    angle = abs(bend_angle_deg)

    if angle < 0.000001:
        return 0

    if reference == "inside":
        radius = bend_radius

    elif reference == "centerline":
        radius = bend_radius + bar_thickness / 2

    elif reference == "outside":
        radius = bend_radius + bar_thickness

    else:
        raise ValueError("reference must be 'inside', 'centerline', or 'outside'")

    return radius * math.tan(math.radians(angle / 2))


def get_bend_setback(
    bend_angle_deg,
    bend_radius,
    bar_thickness,
    length_reference="outside",
):
    """
    This is the CAD-style fillet setback.

    It calculates how much straight rectangle length is consumed by the bend.

    length_reference:
    - "outside"    = drawing dimension taken from outside edge
    - "inside"     = drawing dimension taken from inside edge
    - "centerline" = drawing dimension taken from centerline
    """

    angle = abs(bend_angle_deg)

    if angle < 0.000001:
        return 0

    if length_reference == "inside":
        radius = bend_radius

    elif length_reference == "centerline":
        radius = bend_radius + bar_thickness / 2

    elif length_reference == "outside":
        radius = bend_radius + bar_thickness

    else:
        raise ValueError("length_reference must be outside, inside, or centerline")

    return radius * math.tan(math.radians(angle / 2))


def rule_value_for_segment_end(
    segment_number,
    side,
    correction_rules,
    default_reference,
):
    """
    side = "start" or "end"

    Returns:
    - None        = no correction
    - "outside"   = outside correction
    - "inside"    = inside correction
    - "centerline" = centerline correction
    """

    if correction_rules is None:
        return default_reference

    segment_rule = correction_rules.get(segment_number, {})

    value = segment_rule.get(side, default_reference)

    if value in [None, False, "none", "no", "off"]:
        return None

    if value is True:
        return default_reference

    return value


def convert_drawing_lengths_to_cad_straights(
    drawing_lengths,
    bend_angles,
    bend_radius,
    bar_thickness,
    length_reference="outside",
    correction_rules=None,
):
    """
    Converts drawing dimensions into internal straight segment lengths.

    Unlike the old version, this does NOT blindly subtract every adjacent bend.
    Each segment can control whether its start/end gets corrected.
    """

    straight_lengths = []

    for i, drawing_length in enumerate(drawing_lengths):
        segment_number = i + 1
        subtract = 0

        # Correction at start of this segment from previous bend
        if i > 0 and i - 1 < len(bend_angles):
            start_reference = rule_value_for_segment_end(
                segment_number=segment_number,
                side="start",
                correction_rules=correction_rules,
                default_reference=length_reference,
            )

            if start_reference is not None:
                subtract += get_bend_setback(
                    bend_angle_deg=bend_angles[i - 1],
                    bend_radius=bend_radius,
                    bar_thickness=bar_thickness,
                    length_reference=start_reference,
                )

        # Correction at end of this segment from next bend
        if i < len(bend_angles):
            end_reference = rule_value_for_segment_end(
                segment_number=segment_number,
                side="end",
                correction_rules=correction_rules,
                default_reference=length_reference,
            )

            if end_reference is not None:
                subtract += get_bend_setback(
                    bend_angle_deg=bend_angles[i],
                    bend_radius=bend_radius,
                    bar_thickness=bar_thickness,
                    length_reference=end_reference,
                )

        corrected_length = drawing_length - subtract

        if corrected_length <= 0:
            raise ValueError(
                f"Segment {segment_number} became too short after correction. "
                f"Drawing length={drawing_length}, subtract={subtract}"
            )

        straight_lengths.append(round(corrected_length, 3))

        print(
            f"Segment {segment_number}: drawing={drawing_length}, "
            f"subtract={round(subtract, 4)}, internal={round(corrected_length, 4)}"
        )

    return straight_lengths

# ============================================================
# 10B. CAD-STYLE INPUT PREPARATION LAYER
# ============================================================

def get_user_length_input():
    """
    Keeps old input blocks working.

    Preferred input:
        DRAWING_LENGTHS = [...]

    Fallback for older saved blocks:
        SEGMENT_LENGTHS = [...]
    """

    if "DRAWING_LENGTHS" in globals():
        return list(DRAWING_LENGTHS)

    if "SEGMENT_LENGTHS" in globals():
        return list(SEGMENT_LENGTHS)

    raise ValueError("You need either DRAWING_LENGTHS or SEGMENT_LENGTHS in the user input block.")


def get_start_setback_for_segment(
    segment_index,
    bend_angles,
    bend_radius,
    bar_thickness,
    length_reference="outside",
    correction_rules=None,
):
    """
    Returns how much to subtract from a hole's from_top value because
    this segment starts after a corrected bend.

    segment_index is zero-based:
        segment 1 = 0
        segment 2 = 1

    Important:
    This now respects LENGTH_CORRECTION_RULES.
    If segment 4 has {"start": None}, holes on segment 4 are NOT shifted.
    """

    if segment_index <= 0:
        return 0

    previous_bend_index = segment_index - 1

    if previous_bend_index >= len(bend_angles):
        return 0

    segment_number = segment_index + 1

    start_reference = rule_value_for_segment_end(
        segment_number=segment_number,
        side="start",
        correction_rules=correction_rules,
        default_reference=length_reference,
    )

    if start_reference is None:
        return 0

    return get_bend_setback(
        bend_angle_deg=bend_angles[previous_bend_index],
        bend_radius=bend_radius,
        bar_thickness=bar_thickness,
        length_reference=start_reference,
    )


def convert_hole_positions_to_internal(
    holes_by_segment,
    bend_angles,
    bend_radius,
    bar_thickness,
    length_reference="outside",
    correction_rules=None,
):
    """
    Converts HOLES_BY_SEGMENT from drawing coordinates to internal
    straight-segment coordinates.

    Your user input stays unchanged:
        (from_top, from_left)

    The code subtracts the start bend setback from from_top ONLY when
    LENGTH_CORRECTION_RULES says that the start of that segment was corrected.
    from_left stays unchanged because bends do not affect Z width location.
    """

    converted = {}

    if not holes_by_segment:
        return converted

    for segment_number, feature_dict in holes_by_segment.items():
        segment_index = int(segment_number) - 1

        start_setback = get_start_setback_for_segment(
            segment_index=segment_index,
            bend_angles=bend_angles,
            bend_radius=bend_radius,
            bar_thickness=bar_thickness,
            length_reference=length_reference,
            correction_rules=correction_rules,
        )

        converted[segment_number] = {}

        if not feature_dict:
            continue

        for feature_type, positions in feature_dict.items():
            converted_positions = []

            for position in normalize_position_list(positions):
                if len(position) < 2:
                    continue

                from_top = position[0]
                from_left = position[1]

                if not is_number(from_top) or not is_number(from_left):
                    raise FeatureError(f"Feature {feature_type}: invalid drawing position {position}. STEP refused.")
                    continue

                internal_from_top = round(from_top - start_setback, 3)

                if internal_from_top < 0:
                    print(
                        f"WARNING: segment {segment_number}, feature {feature_type} at {position} "
                        f"falls inside/before the corrected start zone. "
                        f"Converted from_top={internal_from_top}."
                    )

                converted_positions.append((internal_from_top, from_left))

            converted[segment_number][feature_type] = converted_positions

    return converted


def prepare_cad_inputs():
    """
    Single conversion gate before building.

    User block stays human/drawing-based:
        DRAWING_LENGTHS or old SEGMENT_LENGTHS
        HOLES_BY_SEGMENT in drawing coordinates
        BEND_ANGLES
        LENGTH_REFERENCE
        optional LENGTH_CORRECTION_RULES

    Builder receives CAD-internal values:
        INTERNAL_SEGMENT_LENGTHS
        INTERNAL_HOLES_BY_SEGMENT
    """

    raw_lengths = get_user_length_input()
    length_reference = globals().get("LENGTH_REFERENCE", "outside")
    correction_rules = globals().get("LENGTH_CORRECTION_RULES", None)

    internal_segment_lengths = convert_drawing_lengths_to_cad_straights(
        drawing_lengths=raw_lengths,
        bend_angles=BEND_ANGLES,
        bend_radius=BEND_RADIUS,
        bar_thickness=BAR_THICKNESS,
        length_reference=length_reference,
        correction_rules=correction_rules,
    )

    internal_holes_by_segment = convert_hole_positions_to_internal(
        holes_by_segment=HOLES_BY_SEGMENT,
        bend_angles=BEND_ANGLES,
        bend_radius=BEND_RADIUS,
        bar_thickness=BAR_THICKNESS,
        length_reference=length_reference,
        correction_rules=correction_rules,
    )

    print("Drawing lengths:", raw_lengths)
    print("Internal straight lengths:", internal_segment_lengths)
    print("Internal holes:", internal_holes_by_segment)

    return internal_segment_lengths, internal_holes_by_segment

# ============================================================
# 11. MAIN BUSBAR BUILDER LOOP
# ============================================================

def build_busbar(
    segment_lengths,
    bend_angles,
    holes_by_segment,
    bar_thickness,
    bar_width,
    bend_radius,
):
    """
    Main busbar builder.

    Loop:
    1. Create segment
    2. Cut features for that segment
    3. Add bend if a bend angle exists
    4. Move to next segment
    """

    parts = []

    current_start_xy = (0, 0)
    current_angle_deg = 0

    for i, segment_length in enumerate(segment_lengths):
        segment_number = i + 1

        if segment_length <= 0:
            raise FeatureError(f"Segment {segment_number} length must be positive. STEP refused.")
        
        # 1. Create straight segment
        segment = create_segment(
            segment_length=segment_length,
            bar_thickness=bar_thickness,
            bar_width=bar_width,
            segment_start_xy=current_start_xy,
            segment_angle_deg=current_angle_deg,
        )

        # 2. Get feature dictionary for this segment
        current_segment_holes = holes_by_segment.get(segment_number, {})

        # 3. Cut features into this segment
        segment = make_holes(
            segment=segment,
            segment_holes_dictionary=current_segment_holes,
            segment_start_xy=current_start_xy,
            segment_angle_deg=current_angle_deg,
            segment_length=segment_length,
            bar_thickness=bar_thickness,
            bar_width=bar_width,
        )

        parts.append(segment)

        # 4. Find the end of current segment
        segment_direction = rotate_2d((1, 0), current_angle_deg)

        segment_end_xy = add_2d(
            current_start_xy,
            multiply_2d(segment_direction, segment_length),
        )

        # 5. Add bend if one exists after this segment
        if i < len(segment_lengths) - 1 and i < len(bend_angles):
            bend_angle = bend_angles[i]

            bend_body, next_start_xy, next_angle_deg = make_bend(
                segment_end_xy=segment_end_xy,
                segment_angle_deg=current_angle_deg,
                bend_angle_clockwise=bend_angle,
                bar_thickness=bar_thickness,
                bar_width=bar_width,
                bend_radius=_radius_for_bend(bend_radius, i),  #PATCH per-bend radius
            )

            if bend_body is not None:
                parts.append(bend_body)

            current_start_xy = next_start_xy
            current_angle_deg = next_angle_deg

        else:
            # No more bend angle available.
            # Next segment, if any, continues straight from here.
            current_start_xy = segment_end_xy

    final_busbar = union_parts(parts)

    return final_busbar


# ============================================================
# 12. RUN
# ============================================================

INTERNAL_SEGMENT_LENGTHS, INTERNAL_HOLES_BY_SEGMENT = prepare_cad_inputs()

busbar = build_busbar(
    segment_lengths=INTERNAL_SEGMENT_LENGTHS,
    bend_angles=BEND_ANGLES,
    holes_by_segment=INTERNAL_HOLES_BY_SEGMENT,
    bar_thickness=BAR_THICKNESS,
    bar_width=BAR_WIDTH,
    bend_radius=BEND_RADIUS,
)

show_object(busbar)

if EXPORT_STEP and busbar is not None:
    cq.exporters.export(busbar, EXPORT_FILENAME)
    print(f"Exported STEP file: {EXPORT_FILENAME}")