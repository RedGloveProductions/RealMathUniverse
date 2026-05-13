from __future__ import annotations

import shutil
import subprocess
import sys
import time
from pathlib import Path


ROOT = Path("/Users/Joe/Documents/RealMathUniverse")
MAIN = ROOT / "metal_renderer/Sources/RealMathUniverseMetalRenderer/main.swift"
MARKER = "RMU_V1_11C_EXACT_BIG_ZOOM_BIG_PARTICLES"


def fail(msg: str) -> None:
    print("ERROR:", msg)
    sys.exit(1)


def replace_once(text: str, old: str, new: str, label: str) -> tuple[str, bool]:
    if old not in text:
        print(f"WARNING: anchor not found for {label}")
        return text, False
    return text.replace(old, new, 1), True


def main() -> int:
    if not MAIN.exists():
        fail(f"Missing {MAIN}")

    original = MAIN.read_text()

    if MARKER in original:
        print("v1.11C exact big zoom / big particles patch already present.")
        return 0

    backup = MAIN.with_name(
        f"main.swift.v1_11C_EXACT_big_zoom_big_particles.backup.{time.strftime('%Y%m%d_%H%M%S')}.bak"
    )
    shutil.copy2(MAIN, backup)
    print("Backup:", backup)

    s = original
    changes = []

    replacements = [
        (
            "    var pointSize: Float = 2.0",
            f"    var pointSize: Float = 32.0 // {MARKER}: basketball-sized particles",
            "default pointSize 2.0 -> 32.0",
        ),
        (
            "    func increasePointSize() { pointSize = min(pointSize + 0.5, 12.0); hud?.updateText() }",
            f"    func increasePointSize() {{ pointSize = min(pointSize + 4.0, 96.0); hud?.updateText() }} // {MARKER}",
            "increasePointSize cap 12.0 -> 96.0",
        ),
        (
            "    func decreasePointSize() { pointSize = max(pointSize - 0.5, 0.5); hud?.updateText() }",
            f"    func decreasePointSize() {{ pointSize = max(pointSize - 4.0, 2.0); hud?.updateText() }} // {MARKER}",
            "decreasePointSize step/floor adjusted",
        ),
        (
            "    func zoomOut() { let current = manualWorldRadius ?? frameLoader.worldRadius; manualWorldRadius = min(current * 1.15, 100.0); hud?.updateText() }",
            f"    func zoomOut() {{ let current = manualWorldRadius ?? frameLoader.worldRadius; manualWorldRadius = min(current * 1.75, 100000.0); hud?.updateText() }} // {MARKER}: huge zoom-out range",
            "zoomOut cap 100.0 -> 100000.0",
        ),
        (
            "    func zoomIn() { let current = manualWorldRadius ?? frameLoader.worldRadius; manualWorldRadius = max(current / 1.15, 0.25); hud?.updateText() }",
            f"    func zoomIn() {{ let current = manualWorldRadius ?? frameLoader.worldRadius; manualWorldRadius = max(current / 1.75, 0.25); hud?.updateText() }} // {MARKER}: matched large-world zoom step",
            "zoomIn divisor 1.15 -> 1.75",
        ),
        (
            "            pointSize = Float((render[\"point_size\"] as? NSNumber)?.doubleValue ?? Double(pointSize))",
            f"            pointSize = max(Float((render[\"point_size\"] as? NSNumber)?.doubleValue ?? Double(pointSize)), 32.0) // {MARKER}: saved states cannot shrink v1.11C particles",
            "state restore pointSize floored at 32.0",
        ),
    ]

    for old, new, label in replacements:
        s, changed = replace_once(s, old, new, label)
        if changed:
            changes.append(label)

    if not changes:
        print("No anchors changed. Restoring backup.")
        shutil.copy2(backup, MAIN)
        return 1

    s = f"// {MARKER}: exact-anchor camera zoom and particle scale patch\n" + s

    MAIN.write_text(s)

    print("Changes:")
    for c in changes:
        print(" -", c)

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

    print("RMU v1.11C EXACT complete. Swift build passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
