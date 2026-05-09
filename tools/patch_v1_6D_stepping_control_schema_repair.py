#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

VERSION = "v1.6D_stepping_control_schema_repair"
ROOT = Path(sys.argv[1]).expanduser().resolve() if len(sys.argv) > 1 else Path("/Users/Joe/Documents/RealMathUniverse")
MAIN = ROOT / "metal_renderer" / "Sources" / "RealMathUniverseMetalRenderer" / "main.swift"
BRIDGE = ROOT / "src" / "control" / "vcv_osc_bridge.py"
REPORT = ROOT / "output" / "v1_6D_stepping_control_schema_repair_report.json"

def fail(message: str, backup: Path | None = None) -> None:
    print("V1.6D PATCH FAILED:", message)
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps({
        "version": VERSION,
        "ok": False,
        "message": message,
        "backup": str(backup) if backup else None,
        "timestamp_unix": time.time(),
    }, indent=2))
    raise SystemExit(1)

def backup(path: Path, tag: str) -> Path:
    stamp = time.strftime("%Y%m%d_%H%M%S")
    bdir = ROOT / "backups" / VERSION
    bdir.mkdir(parents=True, exist_ok=True)
    dst = bdir / f"{path.name}.{tag}.{stamp}.bak"
    shutil.copy2(path, dst)
    return dst

def patch_main() -> tuple[Path, list[str]]:
    if not MAIN.exists():
        fail(f"main.swift not found: {MAIN}")

    b = backup(MAIN, "main")
    s = MAIN.read_text()
    original = s
    flags: list[str] = []

    new_block = '''        // RMU_V1_6C_OPTIONAL_BEHAVIOR_CHANNEL_AUTHORITY_BEGIN
        // RMU_V1_6D_DIRECT_CHANNEL_BEHAVIOR_AUTHORITY
        //
        // /ch/8 remains scene/field only.
        // Shift+E/manual behavior remains authority by default.
        //
        // /ch/19 is a deliberate VCV behavior authority gate.
        // /ch/18 only drives behavior code while /ch/19 is >= 5V.
        //
        // v1.6D reads /ch/18 and /ch/19 directly from the JSON channel dictionaries instead
        // of relying on vcvChannelValues[17]/[18]. The log proved those channels are live in
        // vcv_state.json but can be missed by older fixed-width Swift arrays.
        func rmuV16DNumberForChannel(_ path: String) -> Float? {
            if let channels = json["channels"] as? [String: Any],
               let number = channels[path] as? NSNumber {
                return number.floatValue
            }
            if let nativeValues = json["native_channel_values"] as? [String: Any],
               let number = nativeValues[path] as? NSNumber {
                return number.floatValue
            }
            if let rawChannels = json["raw_channels"] as? [String: Any],
               let number = rawChannels[path] as? NSNumber {
                return number.floatValue
            }
            return nil
        }

        func rmuV16DVoiceCountForChannel(_ path: String) -> Int {
            if let voiceCounts = json["channel_voice_counts"] as? [String: Any],
               let number = voiceCounts[path] as? NSNumber {
                return number.intValue
            }
            if let nativeCounts = json["native_channel_voice_counts"] as? [String: Any],
               let number = nativeCounts[path] as? NSNumber {
                return number.intValue
            }
            if let details = json["channel_details"] as? [String: Any],
               let channelDetails = details[path] as? [String: Any],
               let number = channelDetails["voice_count"] as? NSNumber {
                return number.intValue
            }
            return 0
        }

        let rmuV16DBehaviorCodeVoices = rmuV16DVoiceCountForChannel("/ch/18")
        let rmuV16DBehaviorGateVoices = rmuV16DVoiceCountForChannel("/ch/19")
        let rmuV16DBehaviorCodeValue = rmuV16DNumberForChannel("/ch/18")
        let rmuV16DBehaviorGateValue = rmuV16DNumberForChannel("/ch/19")

        let rmuV16DBehaviorGateActive =
            rmuV16DBehaviorGateVoices > 0 &&
            (rmuV16DBehaviorGateValue ?? 0.0) >= 5.0

        if rmuV16DBehaviorGateActive && rmuV16DBehaviorCodeVoices > 0 {
            let rawBehavior = Int(round(rmuV16DBehaviorCodeValue ?? 0.0))
            behaviorEffectCode = Int32(max(0, min(7, rawBehavior)))
            geospatialBehaviorEnabled = true
        }
        // RMU_V1_6C_OPTIONAL_BEHAVIOR_CHANNEL_AUTHORITY_END'''

    bounded = r'''        // RMU_V1_6C_OPTIONAL_BEHAVIOR_CHANNEL_AUTHORITY_BEGIN.*?        // RMU_V1_6C_OPTIONAL_BEHAVIOR_CHANNEL_AUTHORITY_END'''
    s2, n = re.subn(bounded, new_block, s, count=1, flags=re.DOTALL)

    if n == 0:
        fail("Could not locate existing v1.6C optional behavior authority block.", backup=b)

    required = [
        "RMU_V1_6D_DIRECT_CHANNEL_BEHAVIOR_AUTHORITY",
        'rmuV16DNumberForChannel("/ch/18")',
        'rmuV16DNumberForChannel("/ch/19")',
        "rmuV16DBehaviorGateActive && rmuV16DBehaviorCodeVoices > 0",
    ]
    missing = [m for m in required if m not in s2]
    if missing:
        fail(f"main.swift missing required v1.6D markers before build: {missing}", backup=b)

    MAIN.write_text(s2)
    flags.append(f"main_behavior_block_replaced={n}")

    print("Building renderer...")
    try:
        subprocess.run(["swift", "build", "-c", "release"], cwd=str(ROOT / "metal_renderer"), check=True)
    except Exception as exc:
        MAIN.write_text(original)
        fail(f"Swift build failed after v1.6D main patch; restored original. Error: {exc}", backup=b)

    return b, flags

def patch_bridge_labels() -> tuple[Path | None, list[str]]:
    flags: list[str] = []
    if not BRIDGE.exists():
        flags.append("bridge_labels_skipped=bridge_not_found")
        return None, flags

    b = backup(BRIDGE, "bridge")
    s = BRIDGE.read_text()
    original = s

    replacements = {
        "adaptive_aux_18": "behavior_code",
        "adaptive_aux_19": "behavior_authority_gate",
    }
    for old, new in replacements.items():
        if old in s:
            s = s.replace(old, new)
            flags.append(f"bridge_label_{old}_to_{new}=True")
        else:
            flags.append(f"bridge_label_{old}_to_{new}=not_found")

    if s != original:
        BRIDGE.write_text(s)
        subprocess.run(["python3", "-m", "py_compile", str(BRIDGE)], cwd=str(ROOT), check=True)
    return b, flags

def main() -> int:
    print("=" * 72)
    print(f"RealMathUniverse {VERSION}")
    print(f"Project root: {ROOT}")
    print("=" * 72)

    main_backup, main_flags = patch_main()
    bridge_backup, bridge_flags = patch_bridge_labels()

    report = {
        "version": VERSION,
        "ok": True,
        "timestamp_unix": time.time(),
        "project_root": str(ROOT),
        "main_swift": str(MAIN),
        "main_backup": str(main_backup),
        "bridge": str(BRIDGE),
        "bridge_backup": str(bridge_backup) if bridge_backup else None,
        "swift_build_ok": True,
        "flags": main_flags + bridge_flags,
        "contract": {
            "/ch/8": "scene / field layer only",
            "/ch/18": "behavior_code, stepped 0..7, only read when /ch/19 gate is high",
            "/ch/19": "behavior_authority_gate, low/unplugged = manual Shift+E, >=5V = VCV behavior authority",
        },
    }
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(report, indent=2))

    print()
    print("V1.6D PATCH COMPLETE")
    print("Report:", REPORT)
    print("Main backup:", main_backup)
    if bridge_backup:
        print("Bridge backup:", bridge_backup)
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
