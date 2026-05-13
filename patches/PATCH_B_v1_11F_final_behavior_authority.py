from __future__ import annotations

import shutil
import subprocess
import time
from pathlib import Path


ROOT = Path("/Users/Joe/Documents/RealMathUniverse")
MAIN = ROOT / "metal_renderer/Sources/RealMathUniverseMetalRenderer/main.swift"

MARKER = "RMU_PATCH_B_V1_11F_FINAL_BEHAVIOR_AUTHORITY"


def main() -> int:
    if not MAIN.exists():
        print(f"ERROR: missing {MAIN}")
        return 1

    s = MAIN.read_text()

    if MARKER in s:
        print("PATCH_B_ALREADY_PRESENT")
        return 0

    backup = MAIN.with_name(
        f"main.swift.PATCH_B_v1_11F_final_behavior_authority.{time.strftime('%Y%m%d_%H%M%S')}.bak"
    )
    shutil.copy2(MAIN, backup)
    print("Backup:", backup)

    # The documented v1.6F/v1.6G behavior authority block already exists.
    # The visible bug is that it requires /ch/19 voice_count > 0.
    # In this project, constant gates can be omitted by the bridge, while /ch/18 is present.
    # This patch changes the final behavior gate to allow the native fallback /ch/19 object
    # or an inferred high gate from the existing bridge fallback.

    old_16e = '''        let rmuV16EBehaviorGateValue = rmuV16ENumberForChannel("/ch/19") ?? 0.0
        let rmuV16EBehaviorGateActive =
            rmuV16EVoiceCountForChannel("/ch/19") > 0 &&
            rmuV16EBehaviorGateValue >= 5.0

        if rmuV16EBehaviorGateActive,
           rmuV16EVoiceCountForChannel("/ch/18") > 0,
           let behaviorValue = rmuV16ENumberForChannel("/ch/18") {'''

    new_16e = f'''        let rmuV16EBehaviorGateValue = rmuV16ENumberForChannel("/ch/19") ?? 0.0
        let rmuV16EBehaviorCodePresent = rmuV16EVoiceCountForChannel("/ch/18") > 0 || rmuV16ENumberForChannel("/ch/18") != nil
        let rmuV16EBehaviorGatePresent = rmuV16EVoiceCountForChannel("/ch/19") > 0 || rmuV16ENumberForChannel("/ch/19") != nil

        // {MARKER}
        // /ch/19 >= 5V owns behavior. If the bridge has inserted the v1.11F fallback
        // channel, voice_count may be synthetic. Treat numeric presence as valid too.
        let rmuV16EBehaviorGateActive =
            rmuV16EBehaviorGatePresent &&
            rmuV16EBehaviorGateValue >= 5.0

        if rmuV16EBehaviorGateActive,
           rmuV16EBehaviorCodePresent,
           let behaviorValue = rmuV16ENumberForChannel("/ch/18") {{'''

    if old_16e not in s:
        print("ERROR: could not find v1.6E final behavior authority block")
        shutil.copy2(backup, MAIN)
        return 1

    s = s.replace(old_16e, new_16e, 1)

    old_16f = '''        let gateValue = rmuV16FNumberForChannel("/ch/19") ?? 0.0
        let gateActive = rmuV16FVoiceCountForChannel("/ch/19") > 0 && gateValue >= 5.0

        if gateActive,
           rmuV16FVoiceCountForChannel("/ch/18") > 0,
           let behaviorValue = rmuV16FNumberForChannel("/ch/18") {'''

    new_16f = f'''        let gateValue = rmuV16FNumberForChannel("/ch/19") ?? 0.0
        let behaviorCodePresent = rmuV16FVoiceCountForChannel("/ch/18") > 0 || rmuV16FNumberForChannel("/ch/18") != nil
        let behaviorGatePresent = rmuV16FVoiceCountForChannel("/ch/19") > 0 || rmuV16FNumberForChannel("/ch/19") != nil

        // {MARKER}
        // Match v1.6E final authority semantics in the pre-encode path.
        let gateActive = behaviorGatePresent && gateValue >= 5.0

        if gateActive,
           behaviorCodePresent,
           let behaviorValue = rmuV16FNumberForChannel("/ch/18") {{'''

    if old_16f in s:
        s = s.replace(old_16f, new_16f, 1)
    else:
        print("NOTE: v1.6F duplicate behavior block not found or already changed")

    MAIN.write_text(s)

    result = subprocess.run(
        ["swift", "build", "-c", "release"],
        cwd=str(ROOT / "metal_renderer"),
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )

    print(result.stdout)

    if result.returncode != 0:
        print("PATCH_B_FAIL: restoring backup")
        shutil.copy2(backup, MAIN)
        print("Restored:", backup)
        return result.returncode

    print("PATCH_B_PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
