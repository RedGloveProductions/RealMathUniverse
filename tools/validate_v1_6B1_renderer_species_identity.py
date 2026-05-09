#!/usr/bin/env python3
from __future__ import annotations
import json, subprocess, sys
from pathlib import Path
ROOT=Path(sys.argv[1]).expanduser().resolve() if len(sys.argv)>1 else Path("/Users/Joe/Documents/RealMathUniverse")
MAIN=ROOT/"metal_renderer/Sources/RealMathUniverseMetalRenderer/main.swift"
BIN=ROOT/"data/processed/species_identity_v1_6A.bin"
STATE=ROOT/"output/species_identity_state.json"
REPORT=ROOT/"output/v1_6B_renderer_species_identity_patch_report.json"
VCV=ROOT/"output/vcv_state.json"
MARKERS=["RMU_V1_6B_SPECIES_IDENTITY_STATE_BEGIN","RMU_V1_6B_SPECIES_IDENTITY_LOADER_BEGIN","RMU_V1_6B_SAME_UPLOAD_IDENTITY_CALL","RMU_V1_6B_CREATE_IDENTITY_BUFFERS_AFTER_GPU_BUFFERS","RMU_V1_6B_SPECIES_ENCODER_BINDINGS_BEGIN","RMU_V1_6B_SHADER_SPECIES_ARGS_BEGIN","RMU_V1_6B_SHADER_EFFECTIVE_VALUES_BEGIN"]
def flag(n, ok, d=""):
    print(f"[{'OK' if ok else 'FAIL'}] {n}" + (f" :: {d}" if d else ""))
    return ok
def main():
    ok=True
    print("RealMathUniverse v1.6B1 Renderer Species Identity + Metal Validator")
    print("="*92)
    print("Project root:", ROOT)
    ok &= flag("main.swift exists", MAIN.exists(), str(MAIN))
    ok &= flag("species_identity_v1_6A.bin exists", BIN.exists(), str(BIN))
    if BIN.exists():
        size=BIN.stat().st_size
        ok &= flag("species sidecar byte layout", size>0 and size%8==0, f"bytes={size}, records={size//8 if size else 0}")
    ok &= flag("species_identity_state.json exists", STATE.exists(), str(STATE))
    if STATE.exists() and BIN.exists():
        d=json.loads(STATE.read_text())
        ok &= flag("v1.6A manifest matches sidecar", int(d.get("record_count",-1))==BIN.stat().st_size//8)
    text=MAIN.read_text(errors="replace") if MAIN.exists() else ""
    for m in MARKERS: ok &= flag(f"Swift marker {m}", m in text)
    ok &= flag("encoder buffer indices 20-22 present", all(f"index: {i}" in text for i in range(20,23)))
    ok &= flag("species bank buffer indices 23-28 present", all(f"index: {i}" in text for i in range(23,29)))
    ok &= flag("species enable buffer index 30 present", "index: 30" in text)
    ok &= flag("Metal shader consumes species IDs", "rmuV16BSpeciesIDs[id]" in text and "rmuV16BEffectiveSpeed" in text and "rmuV16BEffectiveMass" in text)
    ok &= flag("patch report exists", REPORT.exists(), str(REPORT))
    if REPORT.exists():
        r=json.loads(REPORT.read_text())
        ok &= flag("patch report ok", bool(r.get("ok")), r.get("version",""))
        ok &= flag("swift build recorded OK", bool(r.get("swift_build_ok")))
        ok &= flag("shader species consumption recorded", bool(r.get("shader_species_consumption")))
    if VCV.exists():
        v=json.loads(VCV.read_text())
        print("\nLive VCV snapshot:")
        print("  version:", v.get("version"))
        print("  active:", v.get("active"), "fresh:", v.get("fresh"), "stale:", v.get("stale"), "status:", v.get("status"))
        print("  scene:", v.get("scene_index"), "color:", v.get("color_mode"))
    print("\nSwift build check:")
    try:
        subprocess.run(["swift","build","-c","release"], cwd=str(ROOT/"metal_renderer"), check=True)
        ok &= flag("swift build -c release", True)
    except Exception as exc:
        ok &= flag("swift build -c release", False, str(exc))
    print()
    if ok:
        print("VALIDATION OK"); return 0
    print("VALIDATION FAILED"); return 1
if __name__=="__main__": raise SystemExit(main())
