from __future__ import annotations

import shutil
import subprocess
import sys
import time
from pathlib import Path


ROOT = Path("/Users/Joe/Documents/RealMathUniverse")
MAIN = ROOT / "metal_renderer/Sources/RealMathUniverseMetalRenderer/main.swift"
MARKER = "RMU_V1_11B_TRUE_VOLUMETRIC_KERNEL"


def fail(message: str) -> None:
    print("ERROR:", message)
    sys.exit(1)


def main() -> int:
    if not MAIN.exists():
        fail(f"Missing {MAIN}")

    original = MAIN.read_text()

    if MARKER in original:
        print("v1.11B true volumetric kernel patch already present.")
        return 0

    backup = MAIN.with_name(
        f"main.swift.v1_11B_true_volumetric_kernel.backup.{time.strftime('%Y%m%d_%H%M%S')}.bak"
    )
    shutil.copy2(MAIN, backup)
    print("Backup:", backup)

    s = original

    target = "    func encodeGeospatialParticleUpdate(commandBuffer: MTLCommandBuffer) {\n"
    idx = s.find(target)

    if idx == -1:
        fail("Could not find encodeGeospatialParticleUpdate(commandBuffer:) function.")

    # Insert the new method immediately before the existing compute function.
    method = r'''
    // RMU_V1_11B_TRUE_VOLUMETRIC_KERNEL_METHOD_BEGIN
    // Open-world volumetric motion path.
    // This deliberately avoids the old base-radius / shell / compact disk attractor.
    // It updates live positions and velocity memory directly in shared buffers.
    func rmuV111BUpdateVolumetricParticlesCPU() {
        guard let liveBuffer = liveParticleBuffer,
              let velocityBuffer = velocityParticleBuffer else {
            return
        }

        let stride = MemoryLayout<Particle>.stride
        let liveCount = liveBuffer.length / stride
        let velocityCount = velocityBuffer.length / stride
        let count = min(liveCount, velocityCount)

        if count <= 0 {
            return
        }

        let live = liveBuffer.contents().bindMemory(to: Particle.self, capacity: count)
        let velocity = velocityBuffer.contents().bindMemory(to: Particle.self, capacity: count)

        let t = Float(Date().timeIntervalSince1970.truncatingRemainder(dividingBy: 100000.0))

        let radialWeight = fieldLayerWeights.count > 0 ? max(0.0, fieldLayerWeights[0]) : 0.03
        let orbitalWeight = fieldLayerWeights.count > 1 ? max(0.0, fieldLayerWeights[1]) : 0.02
        let verticalWeight = fieldLayerWeights.count > 2 ? max(0.0, fieldLayerWeights[2]) : 1.65
        let turbulenceWeight = fieldLayerWeights.count > 3 ? max(0.0, fieldLayerWeights[3]) : 2.25

        // Large open domain. These values intentionally match the v1.11A config scale.
        let softRadius: Float = 4200.0
        let absoluteFailsafeRadius: Float = 15000.0

        // Motion tuning.
        let baseTurbulence: Float = 0.0125
        let baseVertical: Float = 0.0040
        let baseCohesion: Float = 0.000006
        let baseSwirl: Float = 0.000035
        let farReturn: Float = 0.00011
        let damping: Float = 0.99865
        let speedLimit: Float = 9.5

        // Non-vertical rotation axis so "orbit" is a 3D tendency, not an X/Z disk.
        let swirlAxisRaw = SIMD3<Float>(0.43, 0.71, 0.56)
        let swirlAxisLen = max(0.0001, simd_length(swirlAxisRaw))
        let swirlAxis = swirlAxisRaw / swirlAxisLen

        for i in 0..<count {
            var p = live[i].position
            var v = velocity[i].position

            if !p.x.isFinite || !p.y.isFinite || !p.z.isFinite {
                p = SIMD3<Float>(0, 0, 0)
                v = SIMD3<Float>(0, 0, 0)
            }

            if !v.x.isFinite || !v.y.isFinite || !v.z.isFinite {
                v = SIMD3<Float>(0, 0, 0)
            }

            let seed = Float((i % 9973) + 1)

            // Deterministic pseudo-noise. This avoids random CPU allocations and keeps behavior repeatable.
            let n = SIMD3<Float>(
                sin(seed * 12.9898 + t * 0.37),
                sin(seed * 78.2330 + t * 0.41),
                sin(seed * 37.7190 + t * 0.53)
            )

            let n2 = SIMD3<Float>(
                cos(seed * 4.123 + t * 0.17),
                sin(seed * 9.871 + t * 0.23),
                cos(seed * 2.337 + t * 0.31)
            )

            // True 3D turbulence. This is the primary visible motion.
            v += n * (baseTurbulence * turbulenceWeight)

            // Extra vertical diffusion so the cloud does not flatten.
            v.y += sin(seed * 0.013 + t * 0.71) * baseVertical * verticalWeight
            v += n2 * (0.0020 * verticalWeight)

            // Weak 3D swirl. This is deliberately not a disk orbit.
            let radius = simd_length(p)
            if radius > 0.001 {
                let dir = p / radius
                let swirl = simd_cross(swirlAxis, dir)
                v += swirl * (baseSwirl * orbitalWeight * min(radius / softRadius, 2.0))

                // Very weak cohesion only as a field tendency.
                // This is not a shell and not a boundary.
                v -= dir * (baseCohesion * radialWeight)
            }

            // Soft far-field return only when particles drift far beyond the large cube.
            // This prevents numerical loss without making a visible wall.
            if radius > softRadius {
                let dir = p / max(radius, 0.001)
                let excess = min((radius - softRadius) / softRadius, 3.0)
                v -= dir * (farReturn * excess)
            }

            // Absolute failsafe only. This is not a visual boundary.
            if radius > absoluteFailsafeRadius {
                p *= 0.92
                v *= 0.25
            }

            // Velocity memory.
            v *= damping

            // Speed clamp to prevent a few particles from numerically exploding.
            let speed = simd_length(v)
            if speed > speedLimit {
                v = (v / max(speed, 0.0001)) * speedLimit
            }

            p += v

            live[i] = Particle(position: p)
            velocity[i] = Particle(position: v)
        }
    }
    // RMU_V1_11B_TRUE_VOLUMETRIC_KERNEL_METHOD_END

'''

    s = s[:idx] + method + s[idx:]

    # Now replace the minimal v1.11A bypass inside encodeGeospatialParticleUpdate
    # with the new v1.11B update call.
    old_minimal = '''        // RMU_V1_11A_PHASE3E_MINIMAL_BYPASS_OLD_DISK_COMPUTE
        // Proof mode: bypass the legacy compact-disk compute kernel.
        // Set RMU_ENABLE_LEGACY_DISK_COMPUTE=1 only when comparing against the old snap-back behavior.
        if ProcessInfo.processInfo.environment["RMU_ENABLE_LEGACY_DISK_COMPUTE"] != "1" {
            return
        }

'''

    new_v111b = '''        // RMU_V1_11B_TRUE_VOLUMETRIC_KERNEL
        // Default v1.11B path: use open-world volumetric update.
        // Set RMU_ENABLE_LEGACY_DISK_COMPUTE=1 only for comparison with the old snap-back kernel.
        if ProcessInfo.processInfo.environment["RMU_ENABLE_LEGACY_DISK_COMPUTE"] != "1" {
            rmuV111BUpdateVolumetricParticlesCPU()
            return
        }

'''

    if old_minimal not in s:
        fail("Could not find the v1.11A minimal bypass block to replace. No changes written.")

    s = s.replace(old_minimal, new_v111b, 1)

    s = f"// {MARKER}: open-world live position + velocity update, no legacy disk snap\n" + s

    MAIN.write_text(s)

    print("Inserted v1.11B true volumetric CPU update path.")
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

    print("RMU v1.11B true volumetric kernel patch complete. Swift build passed.")
    print("")
    print("Default behavior:")
    print("  SPACE runs the new open-world volumetric update.")
    print("")
    print("Legacy comparison only:")
    print("  RMU_ENABLE_LEGACY_DISK_COMPUTE=1 ./scripts/run_metal_session_v1_10A.sh preview 1920x1080")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
