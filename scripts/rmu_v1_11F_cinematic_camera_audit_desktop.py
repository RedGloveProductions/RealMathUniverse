from __future__ import annotations

import json
import re
import subprocess
import time
from pathlib import Path
from typing import Any


ROOT = Path("/Users/Joe/Documents/RealMathUniverse")
MAIN = ROOT / "metal_renderer/Sources/RealMathUniverseMetalRenderer/main.swift"
STAMP = time.strftime("%Y%m%d_%H%M%S")
OUTDIR = Path(f"/Users/Joe/Desktop/RMU_v1_11F_CINEMATIC_CAMERA_AUDIT_{STAMP}")
OUTDIR.mkdir(parents=True, exist_ok=True)

REPORT = OUTDIR / "CINEMATIC_CAMERA_AUDIT.txt"


def run_build() -> tuple[bool, str]:
    try:
        r = subprocess.run(
            ["swift", "build", "-c", "release"],
            cwd=str(ROOT / "metal_renderer"),
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=180,
        )
        return r.returncode == 0, r.stdout
    except Exception as exc:
        return False, str(exc)


def read_text(path: Path) -> str:
    try:
        return path.read_text(errors="replace")
    except Exception as exc:
        return f"<<READ ERROR {path}: {exc}>>"


def read_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text())
    except Exception:
        return {}


def snippet(lines: list[str], idx: int, radius: int = 8) -> str:
    start = max(0, idx - radius)
    end = min(len(lines), idx + radius + 1)
    out = []
    for i in range(start, end):
        mark = ">>" if i == idx else "  "
        out.append(f"{mark} {i+1:05d}: {lines[i]}")
    return "\n".join(out)


def find_hits(lines: list[str], patterns: list[str], radius: int = 8, limit: int = 120) -> str:
    out = []
    count = 0

    for i, line in enumerate(lines):
        if any(re.search(pattern, line, re.IGNORECASE) for pattern in patterns):
            count += 1
            if count > limit:
                out.append(f"... hit limit {limit}, additional hits omitted ...")
                break

            out.append("")
            out.append("-" * 100)
            out.append(snippet(lines, i, radius))

    if not out:
        return "no hits"

    return "\n".join(out)


def index_of_first(lines: list[str], pattern: str) -> int | None:
    for i, line in enumerate(lines):
        if re.search(pattern, line, re.IGNORECASE):
            return i + 1
    return None


def count_hits(text: str, pattern: str) -> int:
    return len(re.findall(pattern, text, flags=re.IGNORECASE | re.MULTILINE))


def main() -> int:
    text = read_text(MAIN)
    lines = text.splitlines()

    build_ok, build_log = run_build()
    (OUTDIR / "swift_build.log").write_text(build_log)

    checks: list[tuple[str, bool, str]] = []

    checks.append(("swift_build", build_ok, "swift build -c release must pass"))
    checks.append(("cinematic_marker_present", ("RMU_PATCH_D_V1_11F_CINEMATIC_CAMERA_MODE" in text or "RMU_PATCH_D_V1_11F_CINEMATIC_CAMERA_FULL_STACK" in text), "Patch D marker missing"))
    checks.append(("cinematic_enabled_var", "cinematicCameraEnabled" in text, "cinematicCameraEnabled var missing"))
    checks.append(("cinematic_toggle_method", "rmuV111FToggleCinematicCamera" in text, "toggle method missing"))
    checks.append(("cinematic_reset_method", "rmuV111FResetCinematicCamera" in text, "reset method missing"))
    checks.append(("cinematic_apply_method", "rmuV111FApplyCinematicCameraIfNeeded" in text, "apply method missing"))
    checks.append(("shift_c_gateway", 'shift && chars == "c"' in text, "SHIFT+C gateway missing"))
    checks.append(("shift_k_gateway", 'shift && chars == "k"' in text, "SHIFT+K gateway missing"))
    checks.append(("shift_r_absent_for_cinematic", 'shift && chars == "r"' not in text or "rmuV111FResetCinematicCamera" not in text.split('shift && chars == "r"', 1)[-1][:220], "SHIFT+R still appears to own cinematic reset"))
    checks.append(("manual_world_radius_used", "manualWorldRadius" in text, "manualWorldRadius missing"))
    checks.append(("rotation_used", "rotationRadians" in text, "rotationRadians missing"))
    checks.append(("pan_used", "panX" in text and "panY" in text, "panX/panY missing"))

    apply_line = index_of_first(lines, r"rmuV111FApplyCinematicCameraIfNeeded\(\)")
    command_buffer_line = index_of_first(lines, r"commandBuffer\.commit\(\)")
    load_vcv_line = index_of_first(lines, r"loadVCVStateIfNeeded\(\)")
    draw_line = index_of_first(lines, r"func\s+draw\s*\(")

    # If apply is only after commandBuffer.commit, it is too late for the current frame and may feel dead/stale.
    if apply_line and command_buffer_line:
        checks.append(("cinematic_apply_before_command_commit", apply_line < command_buffer_line, f"apply line {apply_line} should be before commandBuffer.commit line {command_buffer_line}"))
    else:
        checks.append(("cinematic_apply_before_command_commit", False, "could not locate apply call or commandBuffer.commit"))

    if apply_line and draw_line:
        checks.append(("cinematic_apply_inside_draw_or_render_path", apply_line > draw_line, f"apply line {apply_line} should be inside/after draw function starts at {draw_line}"))
    else:
        checks.append(("cinematic_apply_inside_draw_or_render_path", False, "could not locate draw/apply placement"))

    # Stronger visual defaults check.
    checks.append(("orbit_speed_not_too_subtle", bool(re.search(r"cinematicCameraOrbitSpeed\s*:\s*Float\s*=\s*(0\.[2-9]|[1-9])", text)), "orbit speed is probably too subtle below 0.20 rad/sec"))
    checks.append(("zoom_amplitude_not_too_subtle", bool(re.search(r"cinematicCameraZoomAmplitude\s*:\s*Float\s*=\s*(0\.[2-9]|[1-9])", text)), "zoom amplitude is probably too subtle below 0.20"))
    checks.append(("pan_amplitude_visible", bool(re.search(r"cinematicCameraPanAmplitudeX\s*:\s*Float\s*=\s*(0\.0[6-9]|0\.[1-9]|[1-9])", text)), "pan amplitude is probably too subtle"))

    # Live state snapshots.
    live = []
    for name in [
        "control_state.json",
        "runtime_state.json",
        "operator_authority_state.json",
        "effective_control_state.json",
        "vcv_state.json",
    ]:
        path = ROOT / "output" / name
        obj = read_json(path)
        live.append("")
        live.append("=" * 100)
        live.append(f"LIVE SNAPSHOT: {name}")
        live.append(json.dumps(obj, indent=2, sort_keys=True))

    summary = []
    fail_count = 0

    summary.append("RMU v1.11F CINEMATIC CAMERA AUDIT SUMMARY")
    summary.append("=" * 100)

    for name, ok, fail_if in checks:
        if not ok:
            fail_count += 1
        summary.append(f"{'PASS' if ok else 'FAIL'} | {name} | fail_if: {fail_if}")

    summary.append("=" * 100)
    summary.append(f"SUMMARY | pass={len(checks) - fail_count} fail={fail_count}")
    summary.append(f"OUTDIR | {OUTDIR}")

    body = []
    body.append("\n\n" + "=" * 100)
    body.append("CAMERA / CINEMATIC SOURCE HITS")
    body.append("=" * 100)
    body.append(find_hits(lines, [
        r"cinematicCamera",
        r"rmuV111F",
        r"manualWorldRadius",
        r"rotationRadians",
        r"panX",
        r"panY",
        r"draw\s*\(",
        r"commandBuffer\.commit",
        r"loadVCVStateIfNeeded",
        r"updateAutoCamera",
        r"SHIFT\+C",
        r"SHIFT\+K",
        r"chars == \"c\"",
        r"chars == \"k\"",
        r"chars == \"r\"",
    ], radius=8, limit=200))

    body.append("\n\n" + "=" * 100)
    body.append("LIVE STATE SNAPSHOTS")
    body.append("=" * 100)
    body.append("\n".join(live))

    out = "\n".join(summary) + "\n" + "\n".join(body) + "\n"
    REPORT.write_text(out)

    print("\n".join(summary))
    print(f"REPORT | {REPORT}")

    return 0 if fail_count == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
