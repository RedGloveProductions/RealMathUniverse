#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(sys.argv[1]).expanduser().resolve() if len(sys.argv) > 1 else Path("/Users/Joe/Documents/RealMathUniverse")
MAIN = ROOT / "metal_renderer" / "Sources" / "RealMathUniverseMetalRenderer" / "main.swift"
REPORT = ROOT / "output" / "v1_6C1_renderer_color_behavior_authority_report.json"
VCV = ROOT / "output" / "vcv_state.json"

MARKERS = [
    "RMU_V1_6C_VERTEX_SPECIES_COLOR_ARGS_BEGIN",
    "RMU_V1_6C_VERTEX_SPECIES_COLOR_SAMPLE_BEGIN",
    "RMU_V1_6C_VERTEX_SPECIES_COLOR_MODE",
    "RMU_V1_6C_RENDER_SPECIES_COLOR_BINDINGS_BEGIN",
    "RMU_V1_6C_OPTIONAL_BEHAVIOR_CHANNEL_AUTHORITY_BEGIN",
]

def flag(name: str, ok: bool, detail: str = "") -> bool:
    print(f"[{'OK' if ok else 'FAIL'}] {name}" + (f" :: {detail}" if detail else ""))
    return ok

def main() -> int:
    print("RealMathUniverse v1.6C1 Renderer Color + Behavior Authority Validator")
    print("=" * 92)
    ok = True

    ok &= flag("main.swift exists", MAIN.exists(), str(MAIN))
    text = MAIN.read_text(errors="replace") if MAIN.exists() else ""

    for marker in MARKERS:
        ok &= flag(f"Swift marker {marker}", marker in text)

    ok &= flag("vertex buffers 17/18/19 present", "index: 17" in text and "index: 18" in text and "index: 19" in text)
    ok &= flag("species color used in vertex shader", "float4(rmuV16CSpeciesColor, alpha)" in text)
    ok &= flag("render species binding uses count not drawCount before declaration", "rmuV16BLoadSpeciesIdentityBuffersForParticleCount(Int(count))" in text)
    ok &= flag("optional behavior channels present", '"/ch/18"' in text and '"/ch/19"' in text)
    ok &= flag("v1.6B species identity still present", "RMU_V1_6B_SPECIES_IDENTITY_STATE_BEGIN" in text and "RMU_V1_6B_SPECIES_ENCODER_BINDINGS_BEGIN" in text)

    ok &= flag("patch report exists", REPORT.exists(), str(REPORT))
    if REPORT.exists():
        try:
            r = json.loads(REPORT.read_text())
            ok &= flag("patch report ok", bool(r.get("ok")), r.get("version", ""))
            ok &= flag("swift build recorded OK", bool(r.get("swift_build_ok")))
        except Exception as exc:
            ok &= flag("patch report readable", False, str(exc))

    if VCV.exists():
        try:
            v = json.loads(VCV.read_text())
            print()
            print("Live VCV snapshot:")
            print("  version:", v.get("version"))
            print("  active:", v.get("active"), "fresh:", v.get("fresh"), "status:", v.get("status"))
            print("  scene:", v.get("scene_index"), "color:", v.get("color_mode"))
            print("  /ch/18 voices:", (v.get("channel_voice_counts") or {}).get("/ch/18"))
            print("  /ch/19 voices:", (v.get("channel_voice_counts") or {}).get("/ch/19"))
        except Exception as exc:
            print("VCV snapshot unreadable:", exc)

    print()
    print("Swift build check:")
    try:
        subprocess.run(["swift", "build", "-c", "release"], cwd=str(ROOT / "metal_renderer"), check=True)
        ok &= flag("swift build -c release", True)
    except Exception as exc:
        ok &= flag("swift build -c release", False, str(exc))

    print()
    if ok:
        print("VALIDATION OK")
        return 0
    print("VALIDATION FAILED")
    return 1

if __name__ == "__main__":
    raise SystemExit(main())
