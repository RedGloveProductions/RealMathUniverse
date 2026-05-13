from __future__ import annotations

import shutil
import subprocess
import sys
import time
from pathlib import Path


ROOT = Path("/Users/Joe/Documents/RealMathUniverse")
MAIN = ROOT / "metal_renderer/Sources/RealMathUniverseMetalRenderer/main.swift"
MARKER = "RMU_V1_11A_PHASE3E_MINIMAL_BYPASS_OLD_DISK_COMPUTE"


def fail(msg: str) -> None:
    print("ERROR:", msg)
    sys.exit(1)


def main() -> int:
    if not MAIN.exists():
        fail(f"Missing {MAIN}")

    original = MAIN.read_text()

    if MARKER in original:
        print("Minimal Phase 3E patch already present.")
        return 0

    backup = MAIN.with_name(
        f"main.swift.v1_11A_phase3E_minimal_bypass.backup.{time.strftime('%Y%m%d_%H%M%S')}.bak"
    )
    shutil.copy2(MAIN, backup)
    print("Backup:", backup)

    target = "    func encodeGeospatialParticleUpdate(commandBuffer: MTLCommandBuffer) {\n"
    idx = original.find(target)

    if idx == -1:
        fail("Could not find encodeGeospatialParticleUpdate(commandBuffer:) function.")

    insert_at = idx + len(target)

    insertion = f'''        // {MARKER}
        // Proof mode: bypass the legacy compact-disk compute kernel.
        // Set RMU_ENABLE_LEGACY_DISK_COMPUTE=1 only when comparing against the old snap-back behavior.
        if ProcessInfo.processInfo.environment["RMU_ENABLE_LEGACY_DISK_COMPUTE"] != "1" {{
            return
        }}

'''

    patched = original[:insert_at] + insertion + original[insert_at:]

    MAIN.write_text(patched)

    print("Inserted minimal compute bypass only.")
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

    print("RMU v1.11A Phase 3E MINIMAL complete. Swift build passed.")
    print("")
    print("Legacy disk compute is now OFF by default.")
    print("To compare against old behavior:")
    print("  RMU_ENABLE_LEGACY_DISK_COMPUTE=1 ./scripts/run_metal_session_v1_10A.sh preview 1920x1080")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
