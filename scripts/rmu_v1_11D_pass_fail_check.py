from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path


ROOT = Path("/Users/Joe/Documents/RealMathUniverse")
MAIN = ROOT / "metal_renderer/Sources/RealMathUniverseMetalRenderer/main.swift"
RESOLVER = ROOT / "src/control/operator_authority_resolver.py"
BRIDGE = ROOT / "src/control/vcv_osc_bridge.py"
VCV_STATE = ROOT / "output/vcv_state.json"
EFFECTIVE_STATE = ROOT / "output/effective_control_state.json"
OPERATOR_STATE = ROOT / "output/operator_authority_state.json"


def read_text(path: Path) -> str:
    try:
        return path.read_text(errors="replace")
    except Exception:
        return ""


def read_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text())
    except Exception:
        return {}


def run_build() -> tuple[bool, str]:
    try:
        result = subprocess.run(
            ["swift", "build", "-c", "release"],
            cwd=str(ROOT / "metal_renderer"),
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=120,
        )
        return result.returncode == 0, result.stdout
    except Exception as exc:
        return False, str(exc)


def has(text: str, pattern: str) -> bool:
    return re.search(pattern, text, re.MULTILINE | re.IGNORECASE) is not None


def count(text: str, pattern: str) -> int:
    return len(re.findall(pattern, text, re.MULTILINE | re.IGNORECASE))


def find_line(text: str, pattern: str) -> str:
    for line in text.splitlines():
        if re.search(pattern, line, re.IGNORECASE):
            return line.strip()
    return ""


def check_vcv_channel(obj: dict, ch: str) -> bool:
    candidates = [
        obj.get(ch),
        obj.get(f"/ch/{ch}"),
        obj.get("channels", {}).get(ch),
        obj.get("channels", {}).get(f"/ch/{ch}"),
        obj.get("values", {}).get(ch),
        obj.get("values", {}).get(f"/ch/{ch}"),
    ]
    return any(v is not None for v in candidates)


def status_line(name: str, passed: bool, fail_condition: str) -> str:
    return f"{'PASS' if passed else 'FAIL'} | {name} | fail_if: {fail_condition}"


def main() -> int:
    main_swift = read_text(MAIN)
    resolver = read_text(RESOLVER)
    bridge = read_text(BRIDGE)
    vcv = read_json(VCV_STATE)
    effective = read_json(EFFECTIVE_STATE)
    operator = read_json(OPERATOR_STATE)

    build_ok, build_out = run_build()

    checks: list[tuple[str, bool, str]] = []

    checks.append((
        "Swift release build",
        build_ok,
        "swift build -c release returns nonzero",
    ))

    checks.append((
        "v1.11B volumetric kernel present",
        "RMU_V1_11B_TRUE_VOLUMETRIC_KERNEL" in main_swift,
        "missing RMU_V1_11B_TRUE_VOLUMETRIC_KERNEL marker",
    ))

    checks.append((
        "Legacy disk compute bypass/replacement present",
        has(main_swift, r"RMU_ENABLE_LEGACY_DISK_COMPUTE") and has(main_swift, r"rmuV111BUpdateVolumetricParticlesCPU\(\)"),
        "encodeGeospatialParticleUpdate does not route to v1.11B unless legacy env var is set",
    ))

    checks.append((
        "Large world radius present",
        has(main_swift, r"var\s+worldRadius\s*:\s*Float\s*=\s*4200\.0"),
        "worldRadius is not 4200.0",
    ))

    checks.append((
        "Shell wall disabled",
        has(main_swift, r"if\s*\(\s*false\s*\).*shell wall disabled"),
        "old shell wall branch still active",
    ))

    checks.append((
        "Volumetric expansion present",
        "RMU_V1_11A_LARGE_VOLUMETRIC_DOMAIN_PARTICLE_EXPANSION_BEGIN" in main_swift,
        "large particle expansion block missing",
    ))

    point_line = find_line(main_swift, r"var\s+pointSize\s*:\s*Float")
    point_ok = bool(re.search(r"var\s+pointSize\s*:\s*Float\s*=\s*(3[0-9]|[4-9][0-9]|[1-9][0-9]{2,})", point_line))
    checks.append((
        "Particle default size increased",
        point_ok,
        "pointSize default is below 30.0 or anchor missing",
    ))

    zoom_line = find_line(main_swift, r"func\s+zoomOut")
    zoom_ok = "100000.0" in zoom_line or "50000.0" in zoom_line
    checks.append((
        "Zoom-out ceiling expanded",
        zoom_ok,
        "zoomOut cap is still old small value",
    ))

    checks.append((
        "Old S zoom-out mapping absent from late handler",
        not has(main_swift, r'if\s+chars\s*==\s*"s"\s*\{\s*renderer\?\.zoomOut\(\)'),
        "late handler still maps S to zoomOut",
    ))

    checks.append((
        "Primary S zoom-out mapping absent",
        not has(main_swift, r'case\s+"s"\s*:\s*renderer\?\.zoomOut\(\)'),
        "primary key handler still maps S to zoomOut",
    ))

    checks.append((
        "Point-size hotkey functions exist",
        has(main_swift, r"func\s+increasePointSize\(") and has(main_swift, r"func\s+decreasePointSize\("),
        "increase/decrease point-size functions missing",
    ))

    checks.append((
        "Round particle shader not implemented yet",
        has(main_swift, r"point_coord|circle|discard|smoothstep"),
        "large particles still render as square Metal points",
    ))

    checks.append((
        "VCV channel 7 referenced",
        "/ch/7" in resolver or "/ch/7" in bridge or "ch/7" in resolver or "ch/7" in bridge,
        "/ch/7 color control not referenced in resolver or bridge",
    ))

    checks.append((
        "VCV channel 8 referenced",
        "/ch/8" in resolver or "/ch/8" in bridge or "ch/8" in resolver or "ch/8" in bridge,
        "/ch/8 behavior gate/trigger not referenced in resolver or bridge",
    ))

    checks.append((
        "VCV channel 18 referenced",
        "/ch/18" in resolver or "/ch/18" in bridge or "ch/18" in resolver or "ch/18" in bridge,
        "/ch/18 behavior code source not referenced in resolver or bridge",
    ))

    checks.append((
        "VCV channel 19 referenced",
        "/ch/19" in resolver or "/ch/19" in bridge or "ch/19" in resolver or "ch/19" in bridge,
        "/ch/19 color gate not referenced in resolver or bridge",
    ))

    checks.append((
        "Runtime vcv_state has channel 7",
        check_vcv_channel(vcv, "7"),
        "output/vcv_state.json has no /ch/7 value",
    ))

    checks.append((
        "Runtime vcv_state has channel 8",
        check_vcv_channel(vcv, "8"),
        "output/vcv_state.json has no /ch/8 value",
    ))

    checks.append((
        "Runtime vcv_state has channel 18",
        check_vcv_channel(vcv, "18"),
        "output/vcv_state.json has no /ch/18 value",
    ))

    checks.append((
        "Runtime vcv_state has channel 19",
        check_vcv_channel(vcv, "19"),
        "output/vcv_state.json has no /ch/19 value",
    ))

    eff_text = json.dumps(effective, sort_keys=True)
    op_text = json.dumps(operator, sort_keys=True)

    checks.append((
        "Effective state has behavior authority",
        "behavior" in eff_text,
        "effective_control_state.json lacks behavior authority/state",
    ))

    checks.append((
        "Operator state has dataset/coupling authority",
        "dataset" in op_text or "coupling" in op_text,
        "operator_authority_state.json lacks dataset/coupling authority",
    ))

    print("RMU v1.11D PASS/FAIL CHECK")
    print("=" * 72)

    failures = 0
    for name, passed, fail_condition in checks:
        if not passed:
            failures += 1
        print(status_line(name, passed, fail_condition))

    print("=" * 72)
    print(f"SUMMARY | pass={len(checks) - failures} fail={failures}")

    if not build_ok:
        print("BUILD_HEAD")
        print("\n".join(build_out.splitlines()[:30]))

    return 0 if failures == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
