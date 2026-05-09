#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(sys.argv[1]).expanduser().resolve() if len(sys.argv) > 1 else Path("/Users/Joe/Documents/RealMathUniverse")
MAIN = ROOT / "metal_renderer" / "Sources" / "RealMathUniverseMetalRenderer" / "main.swift"
BRIDGE = ROOT / "src" / "control" / "vcv_osc_bridge.py"
VCV = ROOT / "output" / "vcv_state.json"
REPORT = ROOT / "output" / "v1_6D_stepping_control_schema_repair_report.json"

def flag(name: str, ok: bool, detail: str = "") -> bool:
    print(f"[{'OK' if ok else 'FAIL'}] {name}" + (f" :: {detail}" if detail else ""))
    return ok

def main() -> int:
    print("RealMathUniverse v1.6D Stepping Control Schema Repair Validator")
    print("=" * 92)
    ok = True

    text = MAIN.read_text(errors="replace") if MAIN.exists() else ""
    bridge = BRIDGE.read_text(errors="replace") if BRIDGE.exists() else ""

    ok &= flag("main.swift exists", MAIN.exists(), str(MAIN))
    ok &= flag("v1.6D direct behavior marker", "RMU_V1_6D_DIRECT_CHANNEL_BEHAVIOR_AUTHORITY" in text)
    ok &= flag("direct /ch/18 read present", 'rmuV16DNumberForChannel("/ch/18")' in text)
    ok &= flag("direct /ch/19 read present", 'rmuV16DNumberForChannel("/ch/19")' in text)
    ok &= flag("/ch/19 gate threshold 5V present", ">= 5.0" in text)
    ok &= flag("behavior only applies behind gate", "rmuV16DBehaviorGateActive && rmuV16DBehaviorCodeVoices > 0" in text)
    ok &= flag("behavior gate enables behavior", "geospatialBehaviorEnabled = true" in text)

    ok &= flag("v1.6C color still present", "RMU_V1_6C_VERTEX_SPECIES_COLOR_MODE" in text and "RMU_V1_6C_RENDER_SPECIES_COLOR_BINDINGS_BEGIN" in text)
    ok &= flag("v1.6B species identity still present", "RMU_V1_6B_SPECIES_IDENTITY_STATE_BEGIN" in text and "RMU_V1_6B_SPECIES_ENCODER_BINDINGS_BEGIN" in text)

    if BRIDGE.exists():
        ok &= flag("bridge labels behavior code/gate present", "behavior_code" in bridge and "behavior_authority_gate" in bridge)
    else:
        print("[WARN] bridge file not found, label validation skipped")

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
            print("  /ch/18 voices:", counts.get("/ch/18"), "mapped:", channels.get("/ch/18"), "label:", native.get("/ch/18"))
            print("  /ch/19 voices:", counts.get("/ch/19"), "mapped:", channels.get("/ch/19"), "label:", native.get("/ch/19"))
            if (channels.get("/ch/19") or 0) >= 5:
                print("  behavior gate state: VCV AUTHORITY ACTIVE")
            else:
                print("  behavior gate state: MANUAL SHIFT+E AUTHORITY")
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
