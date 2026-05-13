from __future__ import annotations

import shutil
import subprocess
import time
from pathlib import Path


ROOT = Path("/Users/Joe/Documents/RealMathUniverse")
MAIN = ROOT / "metal_renderer/Sources/RealMathUniverseMetalRenderer/main.swift"
MARKER = "RMU_V1_11D_REMOVE_LATE_S_ZOOMOUT"


def main() -> int:
    original = MAIN.read_text()

    if MARKER in original:
        print("v1.11D late S zoom-out repair already present.")
        return 0

    backup = MAIN.with_name(
        f"main.swift.v1_11D_remove_late_s_zoomout.backup.{time.strftime('%Y%m%d_%H%M%S')}.bak"
    )
    shutil.copy2(MAIN, backup)
    print("Backup:", backup)

    old = '        if chars == "s" { renderer?.zoomOut(); return true }'
    new = f'        // {MARKER}: S no longer zooms out in late v1.8A handler. Use Z/Q/[ for zoom out.'

    if old not in original:
        print("ERROR: exact late S zoomOut line not found.")
        return 1

    patched = original.replace(old, new, 1)
    MAIN.write_text(patched)

    print("Removed late S zoomOut mapping.")
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
        print("Swift build failed. Restoring backup.")
        shutil.copy2(backup, MAIN)
        print("Restored:", backup)
        return result.returncode

    print("v1.11D late S zoom-out repair passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
