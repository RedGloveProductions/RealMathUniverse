from __future__ import annotations

import shutil
import subprocess
import time
from pathlib import Path


ROOT = Path("/Users/Joe/Documents/RealMathUniverse")
MAIN = ROOT / "metal_renderer/Sources/RealMathUniverseMetalRenderer/main.swift"

MARKER = "RMU_PATCH_D2_V1_11F_CINEMATIC_RESET_SHIFT_K"


def main() -> int:
    if not MAIN.exists():
        print(f"ERROR: missing {MAIN}")
        return 1

    s = MAIN.read_text()

    if MARKER in s:
        print("PATCH_D2_ALREADY_PRESENT")
        return 0

    backup = MAIN.with_name(
        f"main.swift.PATCH_D2_v1_11F_cinematic_reset_shift_k.{time.strftime('%Y%m%d_%H%M%S')}.bak"
    )
    shutil.copy2(MAIN, backup)
    print("Backup:", backup)

    old = '''        if shift && chars == "r" {
            renderer?.rmuV111FResetCinematicCamera()
            return true
        }'''

    new = f'''        // {MARKER}: SHIFT+K resets cinematic camera baseline.
        // SHIFT+R is intentionally avoided because it conflicts with existing controls.
        if shift && chars == "k" {{
            renderer?.rmuV111FResetCinematicCamera()
            return true
        }}'''

    if old not in s:
        print("ERROR: SHIFT+R cinematic reset block not found.")
        print("Searching for nearby cinematic controls:")
        for i, line in enumerate(s.splitlines(), start=1):
            if "rmuV111FResetCinematicCamera" in line or "cinematic camera controls" in line or 'chars == "r"' in line:
                print(f"{i}: {line}")
        shutil.copy2(backup, MAIN)
        return 1

    s = s.replace(old, new, 1)

    # Update nearby comments if present.
    s = s.replace(
        "SHIFT+R      Reset cinematic camera baseline/path",
        "SHIFT+K      Reset cinematic camera baseline/path",
    )
    s = s.replace(
        "SHIFT+R    reset cinematic camera baseline",
        "SHIFT+K    reset cinematic camera baseline",
    )
    s = s.replace(
        "SHIFT+R    reset cinematic camera path",
        "SHIFT+K    reset cinematic camera path",
    )

    MAIN.write_text(s)

    print("Changed cinematic reset hotkey from SHIFT+R to SHIFT+K.")
    print("Running swift build -c release...")

    result = subprocess.run(
        ["swift", "build", "-c", "release"],
        cwd=str(ROOT / "metal_renderer"),
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )

    print(result.stdout)

    if result.returncode != 0:
        print("PATCH_D2_FAIL: restoring backup")
        shutil.copy2(backup, MAIN)
        print("Restored:", backup)
        return result.returncode

    print("PATCH_D2_PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
