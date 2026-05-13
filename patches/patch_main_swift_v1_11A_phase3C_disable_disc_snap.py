from __future__ import annotations

import re
import shutil
import subprocess
import sys
import time
from pathlib import Path


ROOT = Path("/Users/Joe/Documents/RealMathUniverse")
MAIN = ROOT / "metal_renderer/Sources/RealMathUniverseMetalRenderer/main.swift"
MARKER = "RMU_V1_11A_PHASE3C_DISABLE_DISC_SNAP"


def fail(message: str) -> None:
    print("ERROR:", message)
    sys.exit(1)


def main() -> int:
    if not MAIN.exists():
        fail(f"Missing {MAIN}")

    original = MAIN.read_text()

    if MARKER in original:
        print("Phase 3C patch already present.")
        return 0

    backup = MAIN.with_name(
        f"main.swift.v1_11A_phase3C_disable_disc_snap.backup.{time.strftime('%Y%m%d_%H%M%S')}.bak"
    )
    shutil.copy2(MAIN, backup)
    print("Backup:", backup)

    s = original
    changes = []

    # ------------------------------------------------------------------
    # 1. Increase worldRadius.
    #
    # Existing audit:
    #   var worldRadius: Float = 6.0
    #
    # That radius is far too small after v1.11A expands the data domain.
    # Any shader or CPU force using worldRadius will collapse the expanded
    # positions back toward a tiny orbital/shell system.
    # ------------------------------------------------------------------
    s2, n = re.subn(
        r"var\s+worldRadius\s*:\s*Float\s*=\s*6\.0",
        f"var worldRadius: Float = 4200.0 // {MARKER}: large open volumetric world radius",
        s,
        count=1,
    )
    if n:
        s = s2
        changes.append("worldRadius 6.0 -> 4200.0")
    else:
        print("WARNING: exact worldRadius default anchor not found.")

    # ------------------------------------------------------------------
    # 2. Replace default field weights.
    #
    # Existing audit:
    #   var fieldLayerWeights: [Float] = [0.25, 1.00, 0.10, 0.05, 0.20]
    #
    # That default is orbital/shell friendly. Use a volumetric profile.
    # ------------------------------------------------------------------
    s2, n = re.subn(
        r"var\s+fieldLayerWeights\s*:\s*\[Float\]\s*=\s*\[0\.25,\s*1\.00,\s*0\.10,\s*0\.05,\s*0\.20\]",
        f"var fieldLayerWeights: [Float] = [0.03, 0.02, 1.65, 2.25, 0.00] // {MARKER}: volumetric field defaults",
        s,
        count=1,
    )
    if n:
        s = s2
        changes.append("fieldLayerWeights default -> volumetric profile")
    else:
        print("WARNING: exact fieldLayerWeights default anchor not found.")

    # ------------------------------------------------------------------
    # 3. Disable the Metal shader shell wall.
    #
    # Existing audit found:
    #   if (fieldEnabledShell == 1) {
    #       float shellRadius = worldRadius * 0.72;
    #       float shellWidth = max(worldRadius * 0.08, 0.05);
    #       float q = (baseRadius - shellRadius) / shellWidth;
    #       shellMask = exp(-(q * q)) * fieldWeightShell;
    #
    # Replace that condition with impossible false condition. This keeps
    # the shader source structure intact but stops shellMask from creating
    # a visible radius band/wall.
    # ------------------------------------------------------------------
    s2, n = re.subn(
        r"if\s*\(\s*fieldEnabledShell\s*==\s*1\s*\)\s*\{",
        f"if (false) {{ // {MARKER}: shell wall disabled for open volumetric domain",
        s,
        count=1,
    )
    if n:
        s = s2
        changes.append("disabled first shader shell wall condition")
    else:
        print("WARNING: shader shell condition not found.")

    # ------------------------------------------------------------------
    # 4. Neutralize selected field layer if scene logic chooses SHELL.
    #
    # Existing HUD showed:
    #   scene 7 layer 5 SHELL
    #
    # If selectedFieldLayerIndex is forced to shell, the HUD and control
    # layer can keep reporting shell even after weights are reduced. This
    # does not break the UI, it only prevents shell from being a selected
    # wall in open-world mode.
    # ------------------------------------------------------------------
    neutralizer_anchor = "func rmuCurrentSelectedFieldWeight()"
    anchor_idx = s.find(neutralizer_anchor)

    if anchor_idx != -1:
        brace_idx = s.find("{", anchor_idx)
        if brace_idx != -1:
            insert_at = brace_idx + 1
            neutralizer = f'''
        // {MARKER}: shell cannot be the active selected layer in large-volume mode.
        if ProcessInfo.processInfo.environment["RMU_DISABLE_VOLUMETRIC_DOMAIN"] != "1" {{
            if selectedFieldLayerIndex >= 4 {{
                selectedFieldLayerIndex = 3
            }}
        }}
'''
            s = s[:insert_at] + neutralizer + s[insert_at:]
            changes.append("neutralized selected SHELL field layer inside rmuCurrentSelectedFieldWeight()")
        else:
            print("WARNING: could not find opening brace for rmuCurrentSelectedFieldWeight().")
    else:
        print("WARNING: rmuCurrentSelectedFieldWeight() not found.")

    # ------------------------------------------------------------------
    # 5. Add a visible marker near the top of the file.
    # ------------------------------------------------------------------
    s = f"// {MARKER}: disables old tiny-radius shell/orbital disc snap for large geospatial volume\n" + s

    MAIN.write_text(s)

    print("Changes:")
    for change in changes:
        print(" -", change)

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

    print("RMU v1.11A Phase 3C complete. Swift build passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
