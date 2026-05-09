#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

VERSION = "v1.6C2_behavior_authority_gate_repair"
ROOT = Path(sys.argv[1]).expanduser().resolve() if len(sys.argv) > 1 else Path("/Users/Joe/Documents/RealMathUniverse")
MAIN = ROOT / "metal_renderer" / "Sources" / "RealMathUniverseMetalRenderer" / "main.swift"
REPORT = ROOT / "output" / "v1_6C2_behavior_authority_gate_repair_report.json"

def fail(message: str, backup: Path | None = None) -> None:
    print("V1.6C2 PATCH FAILED:", message)
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps({
        "version": VERSION,
        "ok": False,
        "message": message,
        "backup": str(backup) if backup else None,
        "timestamp_unix": time.time(),
    }, indent=2))
    raise SystemExit(1)

def backup_main() -> Path:
    stamp = time.strftime("%Y%m%d_%H%M%S")
    bdir = ROOT / "backups" / VERSION
    bdir.mkdir(parents=True, exist_ok=True)
    backup = bdir / f"main.swift.{stamp}.bak"
    shutil.copy2(MAIN, backup)
    return backup

def main() -> int:
    print("=" * 72)
    print(f"RealMathUniverse {VERSION}")
    print(f"Project root: {ROOT}")
    print("=" * 72)

    if not MAIN.exists():
        fail(f"main.swift not found: {MAIN}")

    backup = backup_main()
    original = MAIN.read_text()
    text = original

    old_block_pattern = r'''        // RMU_V1_6C_OPTIONAL_BEHAVIOR_CHANNEL_AUTHORITY_BEGIN
        if let voiceCounts = json\["channel_voice_counts"\] as\? \[String: Any\] \{
            let behaviorCodeVoices = \(voiceCounts\["/ch/18"\] as\? NSNumber\)\?\.intValue \?\? 0
            let behaviorEnabledVoices = \(voiceCounts\["/ch/19"\] as\? NSNumber\)\?\.intValue \?\? 0

            if behaviorCodeVoices > 0 && vcvChannelValues\.count > 17 \{
                let rawBehavior = Int\(round\(vcvChannelValues\[17\]\)\)
                behaviorEffectCode = Int32\(max\(0, min\(7, rawBehavior\)\)\)
            \}

            if behaviorEnabledVoices > 0 && vcvChannelValues\.count > 18 \{
                geospatialBehaviorEnabled = vcvChannelValues\[18\] >= 0\.5
            \}
        \}
        // RMU_V1_6C_OPTIONAL_BEHAVIOR_CHANNEL_AUTHORITY_END'''

    new_block = '''        // RMU_V1_6C_OPTIONAL_BEHAVIOR_CHANNEL_AUTHORITY_BEGIN
        // RMU_V1_6C2_BEHAVIOR_AUTHORITY_GATE_REPAIR
        //
        // /ch/8 remains scene/field only.
        // Shift+E/manual behavior remains authority by default.
        //
        // /ch/18 only drives behavior code when /ch/19 is deliberately high.
        // /ch/19 is NOT "behavior enabled false/true" anymore. It is an authority gate.
        // This prevents an unpatched or low /ch/19 from snapping behavior OFF every VCV heartbeat.
        if let voiceCounts = json["channel_voice_counts"] as? [String: Any] {
            let behaviorCodeVoices = (voiceCounts["/ch/18"] as? NSNumber)?.intValue ?? 0
            let behaviorGateVoices = (voiceCounts["/ch/19"] as? NSNumber)?.intValue ?? 0

            let behaviorGateActive =
                behaviorGateVoices > 0 &&
                vcvChannelValues.count > 18 &&
                vcvChannelValues[18] >= 5.0

            if behaviorGateActive && behaviorCodeVoices > 0 && vcvChannelValues.count > 17 {
                let rawBehavior = Int(round(vcvChannelValues[17]))
                behaviorEffectCode = Int32(max(0, min(7, rawBehavior)))

                // If VCV is explicitly driving behavior, keep the behavior system on.
                geospatialBehaviorEnabled = true
            }
        }
        // RMU_V1_6C_OPTIONAL_BEHAVIOR_CHANNEL_AUTHORITY_END'''

    text2, n = re.subn(old_block_pattern, new_block, text, count=1, flags=re.DOTALL)

    if n == 0:
        # A marker may exist but the body may be slightly different. Replace any marker-bounded block.
        bounded = r'''        // RMU_V1_6C_OPTIONAL_BEHAVIOR_CHANNEL_AUTHORITY_BEGIN.*?        // RMU_V1_6C_OPTIONAL_BEHAVIOR_CHANNEL_AUTHORITY_END'''
        text2, n = re.subn(bounded, new_block, text, count=1, flags=re.DOTALL)

    if n == 0:
        fail("Could not locate RMU_V1_6C optional behavior authority block to repair.", backup=backup)

    required = [
        "RMU_V1_6C2_BEHAVIOR_AUTHORITY_GATE_REPAIR",
        "vcvChannelValues[18] >= 5.0",
        "geospatialBehaviorEnabled = true",
    ]
    missing = [m for m in required if m not in text2]
    if missing:
        fail(f"required repair markers missing before build: {missing}", backup=backup)

    try:
        MAIN.write_text(text2)
        print("Replaced behavior authority block.")
        print("Behavior contract:")
        print("  /ch/8  scene/field only")
        print("  Shift+E manual behavior authority by default")
        print("  /ch/19 >= 5V gates VCV behavior authority ON")
        print("  /ch/18 drives behavior code only while /ch/19 gate is high")
        print()
        print("Building renderer...")
        subprocess.run(["swift", "build", "-c", "release"], cwd=str(ROOT / "metal_renderer"), check=True)
    except Exception as exc:
        MAIN.write_text(original)
        fail(f"patch/build failed; restored original main.swift. Error: {exc}", backup=backup)

    final = MAIN.read_text(errors="replace")
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps({
        "version": VERSION,
        "ok": True,
        "timestamp_unix": time.time(),
        "project_root": str(ROOT),
        "backup": str(backup),
        "swift_build_ok": True,
        "replacements": n,
        "markers": {
            "RMU_V1_6C2_BEHAVIOR_AUTHORITY_GATE_REPAIR": "RMU_V1_6C2_BEHAVIOR_AUTHORITY_GATE_REPAIR" in final,
            "behavior_gate_threshold_5v": "vcvChannelValues[18] >= 5.0" in final,
            "manual_shift_e_preserved": "Shift+E/manual behavior remains authority by default" in final,
        },
    }, indent=2))

    print()
    print("V1.6C2 PATCH COMPLETE")
    print("Report:", REPORT)
    print("Backup:", backup)
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
