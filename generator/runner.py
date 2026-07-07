import re
import subprocess
from pathlib import Path

CQ_PYTHON = r"C:\Users\naqiy\miniconda3\envs\busbar\python.exe"

BASE_DIR = Path(__file__).parent.parent.resolve()
GENERATOR_PATH = Path(__file__).parent / "busbar_generator_manufacturing_safe.py"
OUTPUT_DIR = BASE_DIR / "output"
TEMP_RUNNER_PATH = OUTPUT_DIR / "_temp_runner.py"

USER_INPUT_PATTERN = re.compile(
    r"# 1\. USER INPUT AREA.*?# 2\. BASIC VECTOR FUNCTIONS",
    re.DOTALL,
)


def format_holes_dict(holes_by_segment: dict) -> str:
    if not holes_by_segment:
        return "{}"

    lines = ["{"]
    for key in sorted(holes_by_segment.keys(), key=lambda k: int(k)):
        seg = int(key)
        features = holes_by_segment[key] or {}
        if not features:
            lines.append(f"    {seg}: {{}},")
            continue

        lines.append(f"    {seg}: {{")
        for feat_key, positions in features.items():
            lines.append(f'        "{feat_key}": [')
            for pos in positions:
                lines.append(f"            ({pos[0]}, {pos[1]}),")
            lines.append("        ],")
        lines.append("    },")
    lines.append("}")
    return "\n".join(lines)


def _abs_path(path: Path) -> str:
    return str(path.resolve())


def _build_user_input_area(params: dict, step_path: Path) -> str:
    filename = params["filename"]
    holes_block = format_holes_dict(params.get("holes_by_segment", {}))

    return f"""# ============================================================
# 1. USER INPUT AREA
# ============================================================
BAR_THICKNESS = {params['bar_thickness']}
BAR_WIDTH = {params['bar_width']}
BEND_RADIUS = {params['bend_radius']}

DRAWING_LENGTHS = {params['drawing_lengths']}

BEND_ANGLES = {params['bend_angles']}

LENGTH_REFERENCE = "{params['length_reference']}"

LENGTH_CORRECTION_RULES = None

HOLES_BY_SEGMENT = {holes_block}

EXPORT_STEP = True
filename = "{filename}"
EXPORT_FILENAME = r"{_abs_path(step_path)}"

Customcircledim = {params['custom_circle_dim']}
Customslotwidth = {params['custom_slot_width']}
Customslotlength = {params['custom_slot_length']}
Customcircledim2 = {params['custom_circle_dim2']}

# ============================================================
# END USER INPUT AREA
# ============================================================
"""


def _prepare_source(params: dict) -> str:
    filename = params["filename"]
    step_path = OUTPUT_DIR / f"{filename}.step"
    glb_path = OUTPUT_DIR / f"{filename}.glb"

    source = GENERATOR_PATH.read_text(encoding="utf-8")
    user_input = _build_user_input_area(params, step_path)

    if not USER_INPUT_PATTERN.search(source):
        raise ValueError("USER INPUT AREA block not found in generator file")

    replacement = (
        user_input.rstrip()
        + "\n\n# ============================================================\n# 2. BASIC VECTOR FUNCTIONS"
    )
    source = USER_INPUT_PATTERN.sub(lambda _: replacement, source, count=1)
    source = source.replace("show_object(busbar)", "# show_object(busbar)")

    glb_block = f"""
if busbar is not None:
    _glb_path = r"{_abs_path(glb_path)}"
    cq.exporters.export(busbar, _glb_path)
    print("Exported GLB:", _glb_path)
"""
    marker = 'print(f"Exported STEP file: {EXPORT_FILENAME}")'
    if marker in source:
        source = source.replace(marker, marker + glb_block, 1)
    else:
        source = source + glb_block

    return source


def run_generation(params: dict) -> dict:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    filename = params["filename"]
    step_file = OUTPUT_DIR / f"{filename}.step"
    glb_file = OUTPUT_DIR / f"{filename}.glb"
    log = ""

    try:
        source = _prepare_source(params)
        TEMP_RUNNER_PATH.write_text(source, encoding="utf-8")

        result = subprocess.run(
            [CQ_PYTHON, str(TEMP_RUNNER_PATH)],
            capture_output=True,
            text=True,
            cwd=str(BASE_DIR),
        )
        log = (result.stdout or "") + (result.stderr or "")

        if result.returncode != 0:
            return {"status": "error", "message": log.strip() or f"Subprocess exited with code {result.returncode}"}

        if not step_file.is_file() or not glb_file.is_file():
            return {
                "status": "error",
                "message": log.strip() or "Output files missing after subprocess completed",
            }

        return {
            "status": "ok",
            "step_file": f"output/{filename}.step",
            "glb_file": f"output/{filename}.glb",
            "log": log,
        }
    except Exception as exc:
        return {"status": "error", "message": log.strip() or str(exc)}
    finally:
        if TEMP_RUNNER_PATH.exists():
            TEMP_RUNNER_PATH.unlink()
