#!/usr/bin/env python3
from __future__ import annotations
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(sys.argv[1]).expanduser().resolve() if len(sys.argv) > 1 else Path("/Users/Joe/Documents/RealMathUniverse")
MAIN = ROOT / "metal_renderer" / "Sources" / "RealMathUniverseMetalRenderer" / "main.swift"
IDENTITY_BIN = ROOT / "data" / "processed" / "species_identity_v1_6A.bin"
IDENTITY_STATE = ROOT / "output" / "species_identity_state.json"
PATCH_REPORT = ROOT / "output" / "v1_6B_renderer_species_identity_patch_report.json"
VCV_STATE = ROOT / "output" / "vcv_state.json"

MARKERS = [
    "RMU_V1_6B_SPECIES_IDENTITY_STATE_BEGIN",
    "RMU_V1_6B_SPECIES_IDENTITY_LOADER_BEGIN",
    "RMU_V1_6B_SAME_UPLOAD_IDENTITY_CALL",
    "RMU_V1_6B_CREATE_IDENTITY_BUFFERS_AFTER_GPU_BUFFERS",
    "RMU_V1_6B_SPECIES_ENCODER_BINDINGS_BEGIN",
    "RMU_V1_6B_SHADER_SPECIES_ARGS_BEGIN",
    "RMU_V1_6B_SHADER_EFFECTIVE_VALUES_BEGIN",
]

def flag(name: str, ok: bool, detail: str = "") -> bool:
    status = "OK" if ok else "FAIL"
    print(f"[{status}] {name}" + (f" :: {detail}" if detail else ""))
    return ok

def main() -> int:
    print("RealMathUniverse v1.6B Renderer Species Identity + Metal Validator")
    print("=" * 92)
    print("Project root:", ROOT)

    all_ok = True
    all_ok &= flag("main.swift exists", MAIN.exists(), str(MAIN))
    all_ok &= flag("species_identity_v1_6A.bin exists", IDENTITY_BIN.exists(), str(IDENTITY_BIN))
    if IDENTITY_BIN.exists():
        size = IDENTITY_BIN.stat().st_size
        all_ok &= flag("species_identity_v1_6A.bin byte layout", size > 0 and size % 8 == 0, f"bytes={size}, records={size//8 if size else 0}")
    all_ok &= flag("species_identity_state.json exists", IDENTITY_STATE.exists(), str(IDENTITY_STATE))
    if IDENTITY_STATE.exists() and IDENTITY_BIN.exists():
        try:
            d = json.loads(IDENTITY_STATE.read_text())
            records = int(d.get("record_count", -1))
            bin_records = IDENTITY_BIN.stat().st_size // 8
            all_ok &= flag("v1.6A manifest matches sidecar", records == bin_records, f"manifest={records}, bin={bin_records}")
        except Exception as e:
            all_ok &= flag("v1.6A manifest readable", False, str(e))

    if MAIN.exists():
        text = MAIN.read_text(errors="replace")
        for marker in MARKERS:
            all_ok &= flag(f"Swift marker {marker}", marker in text)
        all_ok &= flag("encoder buffer indices 20-22 present", "index: 20" in text and "index: 21" in text and "index: 22" in text)
        all_ok &= flag("species banks buffer indices 23-28 present", all(f"index: {i}" in text for i in range(23, 29)))
        all_ok &= flag("species enable buffer index 30 present", "index: 30" in text)

    all_ok &= flag("patch report exists", PATCH_REPORT.exists(), str(PATCH_REPORT))
    if PATCH_REPORT.exists():
        try:
            r = json.loads(PATCH_REPORT.read_text())
            all_ok &= flag("patch report ok flag", bool(r.get("ok")), r.get("version", ""))
            all_ok &= flag("swift build recorded OK", bool(r.get("swift_build_ok")))
            all_ok &= flag("shader species consumption recorded", bool(r.get("shader_species_consumption")))
        except Exception as e:
            all_ok &= flag("patch report readable", False, str(e))

    if VCV_STATE.exists():
        try:
            v = json.loads(VCV_STATE.read_text())
            print()
            print("Live VCV state snapshot:")
            print("  version:", v.get("version"))
            print("  active:", v.get("active"), "fresh:", v.get("fresh"), "stale:", v.get("stale"), "status:", v.get("status"))
            print("  scene:", v.get("scene_index"), "color:", v.get("color_mode"))
            for key in [
                "particle_species_probability",
                "particle_species_speed",
                "particle_species_mass",
                "particle_species_turbulence",
                "particle_species_cohesion",
                "particle_species_color_hex",
            ]:
                val = v.get(key)
                if isinstance(val, list):
                    print(f"  {key}: len={len(val)} first={val[:3]}")
                else:
                    print(f"  {key}: {type(val).__name__}")
        except Exception as e:
            print("Live VCV state unreadable:", e)
    else:
        print()
        print("Live VCV state snapshot: output/vcv_state.json not present yet. Start the normal session to populate it.")

    print()
    print("Swift build check:")
    try:
        subprocess.run(["swift", "build", "-c", "release"], cwd=str(ROOT / "metal_renderer"), check=True)
        all_ok &= flag("swift build -c release", True)
    except Exception as e:
        all_ok &= flag("swift build -c release", False, str(e))

    print()
    if all_ok:
        print("VALIDATION OK")
        return 0
    print("VALIDATION FAILED")
    return 1

if __name__ == "__main__":
    raise SystemExit(main())
