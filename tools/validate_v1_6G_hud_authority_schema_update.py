#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(sys.argv[1]).expanduser().resolve() if len(sys.argv) > 1 else Path("/Users/Joe/Documents/RealMathUniverse")
MAIN = ROOT / "metal_renderer" / "Sources" / "RealMathUniverseMetalRenderer" / "main.swift"
REPORT = ROOT / "output" / "v1_6G_hud_authority_schema_update_report.json"
VCV = ROOT / "output" / "vcv_state.json"

MARKERS = [
    "RMU_V1_6G_HUD_AUTHORITY_HELPERS_BEGIN",
    "RMU_V1_6G_TOP_HUD_VERSION",
    "RMU_V1_6G_TOP_BEHAVIOR_AUTHORITY_HUD",
    "RMU_V1_6G_HUD_COMPACT_VCV_AUTHORITY_SCHEMA",
]

def flag(name: str, ok: bool, detail: str = "") -> bool:
    print(f"[{'OK' if ok else 'FAIL'}] {name}" + (f" :: {detail}" if detail else ""))
    return ok

def main() -> int:
    print("RealMathUniverse v1.6G HUD Authority Schema Validator")
    print("=" * 92)
    ok = True

    ok &= flag("main.swift exists", MAIN.exists(), str(MAIN))
    text = MAIN.read_text(errors="replace") if MAIN.exists() else ""

    for marker in MARKERS:
        ok &= flag(f"HUD marker {marker}", marker in text)

    ok &= flag("HUD version says RMU-1.6G", "RUN RMU-1.6G" in text)
    ok &= flag("HUD behavior reads effective authority", "rmuV16GEffectiveBehaviorCode()" in text and "rmuV16GBehaviorAuthorityLabel()" in text)
    ok &= flag("HUD field authority summary present", "rmuV16GFieldAuthoritySummary()" in text)
    ok &= flag("HUD species identity summary present", "rmuV16GSpeciesIdentitySummary()" in text)
    ok &= flag("HUD color authority summary present", "rmuV16GColorAuthoritySummary()" in text)
    ok &= flag("HUD shows v1.6D1 bridge", "v1.6D1 direct /ch/1-/ch/32" in text)
    ok &= flag("v1.6F apply marker still present", "RMU_V1_6F_PRE_ENCODE_VCV_AUTHORITY_BEGIN" in text)
    ok &= flag("v1.6C color still present", "RMU_V1_6C_RENDER_SPECIES_COLOR_BINDINGS_BEGIN" in text)
    ok &= flag("v1.6B species identity still present", "RMU_V1_6B_SPECIES_IDENTITY_STATE_BEGIN" in text)

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
            counts = v.get("channel_voice_counts") or {}
            channels = v.get("channels") or {}
            native = v.get("native_channels") or {}
            print()
            print("Live VCV snapshot:")
            print("  version:", v.get("version"))
            print("  active:", v.get("active"), "fresh:", v.get("fresh"), "status:", v.get("status"))
            print("  scene:", v.get("scene_index"), "color:", v.get("color_mode"))
            print("  /ch/8  label:", native.get("/ch/8"),  "voices:", counts.get("/ch/8"),  "mapped:", channels.get("/ch/8"))
            print("  /ch/18 label:", native.get("/ch/18"), "voices:", counts.get("/ch/18"), "mapped:", channels.get("/ch/18"))
            print("  /ch/19 label:", native.get("/ch/19"), "voices:", counts.get("/ch/19"), "mapped:", channels.get("/ch/19"))
            print("  behavior_authority_active:", v.get("behavior_authority_active"))
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
