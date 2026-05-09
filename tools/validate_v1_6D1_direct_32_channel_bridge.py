#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(sys.argv[1]).expanduser().resolve() if len(sys.argv) > 1 else Path("/Users/Joe/Documents/RealMathUniverse")
BRIDGE = ROOT / "src/control/vcv_osc_bridge.py"
STATE = ROOT / "output/vcv_state.json"
MAIN = ROOT / "metal_renderer/Sources/RealMathUniverseMetalRenderer/main.swift"


def flag(name: str, ok: bool, detail: str = "") -> bool:
    print(f"[{'OK' if ok else 'FAIL'}] {name}" + (f" :: {detail}" if detail else ""))
    return ok


def main() -> int:
    print("RealMathUniverse v1.6D1 Direct 32-Channel Bridge Validator")
    print("=" * 92)
    ok = True

    bridge_text = BRIDGE.read_text(errors="replace") if BRIDGE.exists() else ""
    main_text = MAIN.read_text(errors="replace") if MAIN.exists() else ""

    ok &= flag("bridge exists", BRIDGE.exists(), str(BRIDGE))
    ok &= flag("bridge version marker", "v1.6D1_direct_32_channel_bridge" in bridge_text)
    ok &= flag("bridge accepts /ch/1..32", "for i in range(1, 33)" in bridge_text)
    ok &= flag("bridge labels /ch/18", '"/ch/18": "behavior_code"' in bridge_text)
    ok &= flag("bridge labels /ch/19", '"/ch/19": "behavior_authority_gate"' in bridge_text)
    ok &= flag("bridge writes direct channels dict", '"channels": channels_out' in bridge_text)
    ok &= flag("renderer direct behavior read still present", "RMU_V1_6D_DIRECT_CHANNEL_BEHAVIOR_AUTHORITY" in main_text)

    if STATE.exists():
        try:
            state = json.loads(STATE.read_text())
            age = time.time() - STATE.stat().st_mtime
            channels = state.get("channels") or {}
            raw = state.get("raw_channels") or {}
            counts = state.get("channel_voice_counts") or {}
            native = state.get("native_channels") or {}
            print()
            print("Live VCV state:")
            print("  version:", state.get("version"))
            print("  age:", round(age, 3))
            print("  active:", state.get("active"), "fresh:", state.get("fresh"), "status:", state.get("status"))
            print("  scene:", state.get("scene_index"), "color:", state.get("color_mode"))
            print("  /ch/18 label:", native.get("/ch/18"))
            print("  /ch/18 voices:", counts.get("/ch/18"), "mapped:", channels.get("/ch/18"), "raw:", raw.get("/ch/18"))
            print("  /ch/19 label:", native.get("/ch/19"))
            print("  /ch/19 voices:", counts.get("/ch/19"), "mapped:", channels.get("/ch/19"), "raw:", raw.get("/ch/19"))
            print("  behavior_authority_active:", state.get("behavior_authority_active"))

            if state.get("version") == "v1.6D1_direct_32_channel_bridge":
                ok &= flag("live state is v1.6D1", True)
            else:
                ok &= flag("live state is v1.6D1", False, str(state.get("version")))

            if counts.get("/ch/19", 0) > 0:
                ok &= flag("/ch/19 has live voices", True)
            else:
                print("[WARN] /ch/19 currently has 0 voices. Patch 10V into /ch/19 for VCV behavior authority.")
        except Exception as exc:
            ok &= flag("live state readable", False, str(exc))
    else:
        print()
        print("[WARN] output/vcv_state.json not found yet. Start the RMU session, then rerun validator.")

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
