from __future__ import annotations

import re
import shutil
import subprocess
import sys
import time
from pathlib import Path


ROOT = Path("/Users/Joe/Documents/RealMathUniverse")
MAIN = ROOT / "metal_renderer/Sources/RealMathUniverseMetalRenderer/main.swift"
MARKER = "RMU_V1_11A_LARGE_VOLUMETRIC_DOMAIN"


def fail(msg: str) -> None:
    print("ERROR:", msg)
    sys.exit(1)


def main() -> int:
    if not MAIN.exists():
        fail(f"Missing {MAIN}")

    original = MAIN.read_text()

    if MARKER in original:
        print("v1.11A large volumetric domain patch already present.")
        return 0

    backup = MAIN.with_name(
        f"main.swift.v1_11A_large_volumetric_domain.backup.{time.strftime('%Y%m%d_%H%M%S')}.bak"
    )
    shutil.copy2(MAIN, backup)
    print("Backup:", backup)

    s = original

    # ------------------------------------------------------------
    # 0. Make the updateParticleBufferIfNeeded particle array mutable.
    # The current code uses:
    #   let particles = frameLoader.particles
    # but v1.11A expands particle positions before buffer upload.
    # ------------------------------------------------------------
    target_func = "func updateParticleBufferIfNeeded()"
    func_idx = s.find(target_func)
    if func_idx == -1:
        fail("Could not find updateParticleBufferIfNeeded().")

    let_line = "        let particles = frameLoader.particles"
    var_line = "        var particles = frameLoader.particles // RMU_V1_11A mutable for large volumetric expansion"

    let_idx = s.find(let_line, func_idx)
    if let_idx == -1:
        if var_line in s:
            print("Particle array already mutable.")
        else:
            fail("Could not find 'let particles = frameLoader.particles' inside updateParticleBufferIfNeeded().")
    else:
        s = s[:let_idx] + var_line + s[let_idx + len(let_line):]
        print("Patched particle array from let to var.")

    # ------------------------------------------------------------
    # 1. Insert large volumetric expansion before particle buffers.
    # ------------------------------------------------------------
    anchors = [
        "guard let baseBuffer = device.makeBuffer(bytes: particles",
        "guard let liveBuffer = device.makeBuffer(bytes: particles",
        "let byteCount = particles.count * MemoryLayout<Particle>.stride"
    ]

    idx = -1
    used_anchor = None

    for anchor in anchors:
        idx = s.find(anchor, func_idx)
        if idx != -1:
            used_anchor = anchor
            break

    if idx == -1:
        fail("Could not find particle buffer creation anchor inside updateParticleBufferIfNeeded(). No changes written.")

    line_start = s.rfind("\n", 0, idx) + 1

    expansion_code = '''
        // RMU_V1_11A_LARGE_VOLUMETRIC_DOMAIN_PARTICLE_EXPANSION_BEGIN
        // Convert the compact crab field into a large volumetric geospatial domain.
        // Longitude-derived x and latitude-derived z are expanded strongly.
        // Depth-derived y is amplified, with deterministic jitter to break planar compression.
        // Disable with environment variable RMU_DISABLE_VOLUMETRIC_DOMAIN=1.
        if ProcessInfo.processInfo.environment["RMU_DISABLE_VOLUMETRIC_DOMAIN"] != "1" {
            let rmuV111AXScale: Float = 28.0
            let rmuV111AYScale: Float = 22.0
            let rmuV111AZScale: Float = 32.0
            let rmuV111AJitter: Float = 0.35
            let rmuV111ADepthJitter: Float = 3.0

            for rmuV111AIndex in particles.indices {
                let seed = Float((rmuV111AIndex % 9973) + 1)
                let jx = Float(sin(Double(seed) * 12.9898)) * rmuV111AJitter
                let jy = Float(sin(Double(seed) * 78.2330)) * rmuV111ADepthJitter
                let jz = Float(sin(Double(seed) * 37.7190)) * rmuV111AJitter

                var p = particles[rmuV111AIndex].position
                p.x = p.x * rmuV111AXScale + jx
                p.y = p.y * rmuV111AYScale + jy
                p.z = p.z * rmuV111AZScale + jz

                particles[rmuV111AIndex] = Particle(position: p)
            }

            print("RMU v1.11A large volumetric domain applied to \\(particles.count) particles")
        }
        // RMU_V1_11A_LARGE_VOLUMETRIC_DOMAIN_PARTICLE_EXPANSION_END

'''

    s = s[:line_start] + expansion_code + s[line_start:]
    print("Inserted volumetric expansion before anchor:", used_anchor)

    # ------------------------------------------------------------
    # 2. Weaken shell containment where fieldLayerWeights[4] is encoded.
    # This is nonfatal if the exact anchor is not found.
    # ------------------------------------------------------------
    shell_patterns = [
        (
            r"var\s+shell\s*=\s*fieldLayerWeights\[4\]",
            "var shell = fieldLayerWeights[4] * 0.03 // RMU_V1_11A weak shell, not wall"
        ),
        (
            r"let\s+shell\s*=\s*fieldLayerWeights\[4\]",
            "let shell = fieldLayerWeights[4] * 0.03 // RMU_V1_11A weak shell, not wall"
        )
    ]

    shell_changed = False

    for pattern, repl in shell_patterns:
        s2, n = re.subn(pattern, repl, s, count=1)
        if n:
            s = s2
            shell_changed = True
            print("Patched shell weighting.")
            break

    if not shell_changed:
        print("WARNING: did not find exact shell variable anchor. Particle expansion still installed.")

    # ------------------------------------------------------------
    # 3. Encourage velocity memory by raising too-low damping.
    # This is nonfatal if the exact anchor is not found.
    # ------------------------------------------------------------
    damping_patterns = [
        (
            r"var\s+damping\s*=\s*geospatialDamping",
            "var damping = min(max(geospatialDamping, 0.992), 0.9995) // RMU_V1_11A long-range velocity memory"
        ),
        (
            r"let\s+damping\s*=\s*geospatialDamping",
            "let damping = min(max(geospatialDamping, 0.992), 0.9995) // RMU_V1_11A long-range velocity memory"
        )
    ]

    damping_changed = False

    for pattern, repl in damping_patterns:
        s2, n = re.subn(pattern, repl, s, count=1)
        if n:
            s = s2
            damping_changed = True
            print("Patched damping memory.")
            break

    if not damping_changed:
        print("WARNING: did not find exact damping anchor.")

    MAIN.write_text(s)

    print("Patched:", MAIN)
    print("Running swift build -c release...")

    result = subprocess.run(
        ["swift", "build", "-c", "release"],
        cwd=str(ROOT / "metal_renderer"),
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT
    )

    print(result.stdout)

    if result.returncode != 0:
        print("Swift build failed. Restoring backup.")
        shutil.copy2(backup, MAIN)
        print("Restored:", backup)
        return result.returncode

    print("RMU v1.11A phase 3 complete. Swift build passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
