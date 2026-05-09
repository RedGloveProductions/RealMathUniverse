#!/usr/bin/env python3
from __future__ import annotations
import json, shutil, subprocess, sys, time
from pathlib import Path

VERSION = "v1.6B1_renderer_species_identity_metal_repair"
ROOT = Path(sys.argv[1]).expanduser().resolve() if len(sys.argv) > 1 else Path("/Users/Joe/Documents/RealMathUniverse")
MAIN = ROOT / "metal_renderer/Sources/RealMathUniverseMetalRenderer/main.swift"
IDENTITY_BIN = ROOT / "data/processed/species_identity_v1_6A.bin"
REPORT = ROOT / "output/v1_6B_renderer_species_identity_patch_report.json"

def die(msg, backup=None):
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps({"version": VERSION, "ok": False, "message": msg, "backup": str(backup) if backup else None, "timestamp_unix": time.time()}, indent=2))
    raise SystemExit(f"V1.6B1 PATCH FAILED: {msg}")

def backup_main():
    bdir = ROOT / "backups" / VERSION
    bdir.mkdir(parents=True, exist_ok=True)
    p = bdir / f"main.swift.{time.strftime('%Y%m%d_%H%M%S')}.bak"
    shutil.copy2(MAIN, p)
    return p

def after_line(s, anchor, block, marker):
    if marker in s: return s, False
    i = s.find(anchor)
    if i < 0: return s, False
    j = s.find("\n", i)
    if j < 0: j = len(s)
    return s[:j+1] + block + s[j+1:], True

def before(s, anchor, block, marker):
    if marker in s: return s, False
    i = s.find(anchor)
    if i < 0: return s, False
    return s[:i] + block + s[i:], True

def replace(s, old, new, label, required=False):
    if old not in s:
        if required: raise RuntimeError(f"required anchor missing: {label}")
        print("WARNING: missing anchor:", label)
        return s, False
    return s.replace(old, new, 1), True

def patch_state_loader(s):
    flags = []
    state = "\n".join([
"    // RMU_V1_6B_SPECIES_IDENTITY_STATE_BEGIN",
"    var rmuV16BSpeciesIdentityLoaded: Bool = false",
"    var rmuV16BSpeciesIdentityRecordCount: Int = 0",
"    var rmuV16BSpeciesIdentityParticleCount: Int = 0",
"    var rmuV16BSpeciesIdentityStatus: String = \"not loaded\"",
"    var rmuV16BSpeciesIdentityLastError: String = \"none\"",
"    var rmuV16BSpeciesControlEnabled: Float = 1.0",
"    var rmuV16BSpeciesIDCPU: [UInt32] = []",
"    var rmuV16BFamilyIDCPU: [UInt32] = []",
"    var rmuV16BSpeciesWeightCPU: [Float] = []",
"    var rmuV16BSpeciesIDBuffer: MTLBuffer? = nil",
"    var rmuV16BFamilyIDBuffer: MTLBuffer? = nil",
"    var rmuV16BSpeciesWeightBuffer: MTLBuffer? = nil",
"    // RMU_V1_6B_SPECIES_IDENTITY_STATE_END",
""])
    for a in ["    var vcvRawChannelValues: [Float] = Array(repeating: 0.0, count: 32)", "    var vcvChannelValues: [Float] = Array(repeating: 0.0, count: 32)"]:
        s, ok = after_line(s, a, state, "RMU_V1_6B_SPECIES_IDENTITY_STATE_BEGIN")
        if ok: break
    flags.append(f"state={'RMU_V1_6B_SPECIES_IDENTITY_STATE_BEGIN' in s}")

    loader = "\n".join([
"    // RMU_V1_6B_SPECIES_IDENTITY_LOADER_BEGIN",
"    func rmuV16BReadUInt16LE(_ bytes: [UInt8], _ offset: Int) -> UInt16 {",
"        if offset + 1 >= bytes.count { return 0 }",
"        return UInt16(bytes[offset]) | (UInt16(bytes[offset + 1]) << 8)",
"    }",
"",
"    func rmuV16BReadFloat32LE(_ bytes: [UInt8], _ offset: Int) -> Float {",
"        if offset + 3 >= bytes.count { return 0.0 }",
"        let bits = UInt32(bytes[offset]) | (UInt32(bytes[offset + 1]) << 8) | (UInt32(bytes[offset + 2]) << 16) | (UInt32(bytes[offset + 3]) << 24)",
"        return Float(bitPattern: bits)",
"    }",
"",
"    func rmuV16BPackBank32(_ source: [Float], fallback: Float) -> [Float] {",
"        var out = Array(repeating: fallback, count: 32)",
"        if source.isEmpty { return out }",
"        for i in 0..<min(32, source.count) { out[i] = source[i] }",
"        return out",
"    }",
"",
"    func rmuV16BPackColorBank96(_ source: [Float]) -> [Float] {",
"        var out = Array(repeating: Float(1.0), count: 96)",
"        if source.isEmpty { return out }",
"        for i in 0..<min(96, source.count) { out[i] = source[i] }",
"        return out",
"    }",
"",
"    func rmuV16BLoadSpeciesIdentityBuffersForParticleCount(_ particleCount: Int) {",
"        if particleCount <= 0 {",
"            rmuV16BSpeciesIdentityStatus = \"no particles\"",
"            return",
"        }",
"        if rmuV16BSpeciesIdentityLoaded && rmuV16BSpeciesIdentityParticleCount == particleCount && rmuV16BSpeciesIDBuffer != nil && rmuV16BFamilyIDBuffer != nil && rmuV16BSpeciesWeightBuffer != nil { return }",
"        let binURL = URL(fileURLWithPath: projectRoot).appendingPathComponent(\"data\").appendingPathComponent(\"processed\").appendingPathComponent(\"species_identity_v1_6A.bin\")",
"        guard let data = try? Data(contentsOf: binURL) else {",
"            rmuV16BSpeciesIdentityLoaded = false",
"            rmuV16BSpeciesIdentityStatus = \"missing species_identity_v1_6A.bin\"",
"            rmuV16BSpeciesIdentityLastError = binURL.path",
"            return",
"        }",
"        let bytes = [UInt8](data)",
"        let recordSize = 8",
"        let records = bytes.count / recordSize",
"        if records <= 0 { rmuV16BSpeciesIdentityLoaded = false; rmuV16BSpeciesIdentityStatus = \"empty species identity\"; return }",
"        var speciesIDs = Array(repeating: UInt32(0), count: particleCount)",
"        var familyIDs = Array(repeating: UInt32(0), count: particleCount)",
"        var weights = Array(repeating: Float(1.0), count: particleCount)",
"        let copyCount = min(records, particleCount)",
"        for i in 0..<copyCount {",
"            let offset = i * recordSize",
"            speciesIDs[i] = UInt32(min(rmuV16BReadUInt16LE(bytes, offset), UInt16(21)))",
"            familyIDs[i] = UInt32(min(rmuV16BReadUInt16LE(bytes, offset + 2), UInt16(6)))",
"            weights[i] = max(0.0, min(rmuV16BReadFloat32LE(bytes, offset + 4), 1.0))",
"        }",
"        if records < particleCount {",
"            for i in records..<particleCount {",
"                let j = i % max(records, 1)",
"                speciesIDs[i] = speciesIDs[j]",
"                familyIDs[i] = familyIDs[j]",
"                weights[i] = weights[j]",
"            }",
"        }",
"        rmuV16BSpeciesIDCPU = speciesIDs",
"        rmuV16BFamilyIDCPU = familyIDs",
"        rmuV16BSpeciesWeightCPU = weights",
"        let idLength = max(1, particleCount) * MemoryLayout<UInt32>.stride",
"        let weightLength = max(1, particleCount) * MemoryLayout<Float>.stride",
"        rmuV16BSpeciesIDBuffer = speciesIDs.withUnsafeBytes { device.makeBuffer(bytes: $0.baseAddress!, length: idLength, options: [.storageModeShared]) }",
"        rmuV16BFamilyIDBuffer = familyIDs.withUnsafeBytes { device.makeBuffer(bytes: $0.baseAddress!, length: idLength, options: [.storageModeShared]) }",
"        rmuV16BSpeciesWeightBuffer = weights.withUnsafeBytes { device.makeBuffer(bytes: $0.baseAddress!, length: weightLength, options: [.storageModeShared]) }",
"        rmuV16BSpeciesIdentityLoaded = rmuV16BSpeciesIDBuffer != nil && rmuV16BFamilyIDBuffer != nil && rmuV16BSpeciesWeightBuffer != nil",
"        rmuV16BSpeciesIdentityRecordCount = records",
"        rmuV16BSpeciesIdentityParticleCount = particleCount",
"        rmuV16BSpeciesIdentityStatus = records == particleCount ? \"loaded \\\\(records)/\\\\(particleCount)\" : \"loaded \\\\(records)/\\\\(particleCount) count mismatch handled\"",
"        print(\"RMU v1.6B species identity: \\\\(rmuV16BSpeciesIdentityStatus)\")",
"    }",
"    // RMU_V1_6B_SPECIES_IDENTITY_LOADER_END",
"",
""])
    for a in ["    func updateParticleBufferIfNeeded()", "    func encodeGeospatialParticleUpdate(commandBuffer:", "    func loadVCVStateIfNeeded()"]:
        s, ok = before(s, a, loader, "RMU_V1_6B_SPECIES_IDENTITY_LOADER_BEGIN")
        if ok: break
    flags.append(f"loader={'RMU_V1_6B_SPECIES_IDENTITY_LOADER_BEGIN' in s}")

    s, ok = replace(s, "        if sameUpload { return }", "\n".join([
"        if sameUpload {",
"            // RMU_V1_6B_SAME_UPLOAD_IDENTITY_CALL",
"            rmuV16BLoadSpeciesIdentityBuffersForParticleCount(particles.count)",
"            return",
"        }"]), "sameUpload", False)
    flags.append(f"sameUpload={ok or 'RMU_V1_6B_SAME_UPLOAD_IDENTITY_CALL' in s}")

    if "RMU_V1_6B_CREATE_IDENTITY_BUFFERS_AFTER_GPU_BUFFERS" not in s:
        for a in ["        velocityParticleBuffer = velocityBuffer", "        particleBuffer = liveBuffer"]:
            if a in s:
                s = s.replace(a, a + "\n        // RMU_V1_6B_CREATE_IDENTITY_BUFFERS_AFTER_GPU_BUFFERS\n        rmuV16BLoadSpeciesIdentityBuffersForParticleCount(particles.count)", 1)
                break
    flags.append(f"postGPU={'RMU_V1_6B_CREATE_IDENTITY_BUFFERS_AFTER_GPU_BUFFERS' in s}")
    return s, flags

def patch_encoder(s):
    if "RMU_V1_6B_SPECIES_ENCODER_BINDINGS_BEGIN" in s: return s, ["encoder=already"]
    anchor = "        if count == 0 { return }"
    block = "\n".join([
"        // RMU_V1_6B_SPECIES_ENCODER_BINDINGS_BEGIN",
"        rmuV16BLoadSpeciesIdentityBuffersForParticleCount(Int(count))",
"        guard let rmuV16BSpeciesIDBufferLive = rmuV16BSpeciesIDBuffer,",
"              let rmuV16BFamilyIDBufferLive = rmuV16BFamilyIDBuffer,",
"              let rmuV16BSpeciesWeightBufferLive = rmuV16BSpeciesWeightBuffer else {",
"            rmuV16BSpeciesIdentityStatus = \"identity buffers unavailable during encode\"",
"            return",
"        }",
"        let rmuV16BProbabilityBank = rmuV16BPackBank32(particleSpeciesProbability, fallback: 1.0)",
"        let rmuV16BSpeedBank = rmuV16BPackBank32(particleSpeciesSpeed, fallback: geospatialParticleSpeed)",
"        let rmuV16BMassBank = rmuV16BPackBank32(particleSpeciesMass, fallback: geospatialParticleMass)",
"        let rmuV16BTurbulenceBank = rmuV16BPackBank32(particleSpeciesTurbulence, fallback: geospatialParticleTurbulence)",
"        let rmuV16BCohesionBank = rmuV16BPackBank32(particleSpeciesCohesion, fallback: geospatialParticleCohesion)",
"        let rmuV16BColorBank = rmuV16BPackColorBank96(particleSpeciesColorRGB)",
"        var rmuV16BEnabled = rmuV16BSpeciesControlEnabled",
"        encoder.setBuffer(rmuV16BSpeciesIDBufferLive, offset: 0, index: 20)",
"        encoder.setBuffer(rmuV16BFamilyIDBufferLive, offset: 0, index: 21)",
"        encoder.setBuffer(rmuV16BSpeciesWeightBufferLive, offset: 0, index: 22)",
"        rmuV16BProbabilityBank.withUnsafeBytes { encoder.setBytes($0.baseAddress!, length: $0.count, index: 23) }",
"        rmuV16BSpeedBank.withUnsafeBytes { encoder.setBytes($0.baseAddress!, length: $0.count, index: 24) }",
"        rmuV16BMassBank.withUnsafeBytes { encoder.setBytes($0.baseAddress!, length: $0.count, index: 25) }",
"        rmuV16BTurbulenceBank.withUnsafeBytes { encoder.setBytes($0.baseAddress!, length: $0.count, index: 26) }",
"        rmuV16BCohesionBank.withUnsafeBytes { encoder.setBytes($0.baseAddress!, length: $0.count, index: 27) }",
"        rmuV16BColorBank.withUnsafeBytes { encoder.setBytes($0.baseAddress!, length: $0.count, index: 28) }",
"        encoder.setBytes(&rmuV16BEnabled, length: MemoryLayout<Float>.stride, index: 30)",
"        // RMU_V1_6B_SPECIES_ENCODER_BINDINGS_END",
""])
    s, ok = replace(s, anchor, anchor + "\n" + block, "encoder count", False)
    return s, [f"encoder={ok}"]

def patch_shader(s):
    flags = []
    sig_old = "\n".join([
"            constant float &gravityWellPosition [[buffer(18)]],",
"            constant float &gravityWellStrength [[buffer(19)]],",
"            uint id [[thread_position_in_grid]]",
"        ) {"])
    sig_new = "\n".join([
"            constant float &gravityWellPosition [[buffer(18)]],",
"            constant float &gravityWellStrength [[buffer(19)]],",
"            // RMU_V1_6B_SHADER_SPECIES_ARGS_BEGIN",
"            constant uint *rmuV16BSpeciesIDs [[buffer(20)]],",
"            constant uint *rmuV16BFamilyIDs [[buffer(21)]],",
"            constant float *rmuV16BSpeciesWeights [[buffer(22)]],",
"            constant float *rmuV16BProbabilityBank [[buffer(23)]],",
"            constant float *rmuV16BSpeedBank [[buffer(24)]],",
"            constant float *rmuV16BMassBank [[buffer(25)]],",
"            constant float *rmuV16BTurbulenceBank [[buffer(26)]],",
"            constant float *rmuV16BCohesionBank [[buffer(27)]],",
"            constant float *rmuV16BColorBank [[buffer(28)]],",
"            constant float &rmuV16BSpeciesControlEnabled [[buffer(30)]],",
"            // RMU_V1_6B_SHADER_SPECIES_ARGS_END",
"            uint id [[thread_position_in_grid]]",
"        ) {"])
    if "RMU_V1_6B_SHADER_SPECIES_ARGS_BEGIN" not in s:
        s, ok = replace(s, sig_old, sig_new, "shader signature", False)
        flags.append(f"shaderArgs={ok}")
    else: flags.append("shaderArgs=already")

    guard_old = "\n".join(["            if (id >= particleCount) { return; }", "", "            float3 base = baseParticles[id].position;"])
    eff = "\n".join([
"            if (id >= particleCount) { return; }",
"",
"            // RMU_V1_6B_SHADER_EFFECTIVE_VALUES_BEGIN",
"            uint rmuV16BSpeciesID = 0;",
"            uint rmuV16BFamilyID = 0;",
"            float rmuV16BSpeciesWeight = 1.0;",
"            float rmuV16BEffectiveProbability = 1.0;",
"            float rmuV16BEffectiveSpeed = particleSpeed;",
"            float rmuV16BEffectiveMass = particleMass;",
"            float rmuV16BEffectiveTurbulence = particleTurbulence;",
"            float rmuV16BEffectiveCohesion = particleCohesion;",
"            float3 rmuV16BEffectiveColor = float3(1.0, 1.0, 1.0);",
"            if (rmuV16BSpeciesControlEnabled > 0.5) {",
"                rmuV16BSpeciesID = min(rmuV16BSpeciesIDs[id], 21u);",
"                rmuV16BFamilyID = min(rmuV16BFamilyIDs[id], 6u);",
"                rmuV16BSpeciesWeight = clamp(rmuV16BSpeciesWeights[id], 0.0, 1.0);",
"                rmuV16BEffectiveProbability = clamp(rmuV16BProbabilityBank[rmuV16BSpeciesID], 0.0, 1.0);",
"                rmuV16BEffectiveSpeed = mix(particleSpeed, rmuV16BSpeedBank[rmuV16BSpeciesID], rmuV16BSpeciesWeight);",
"                rmuV16BEffectiveMass = max(0.05, mix(particleMass, rmuV16BMassBank[rmuV16BSpeciesID], rmuV16BSpeciesWeight));",
"                rmuV16BEffectiveTurbulence = mix(particleTurbulence, rmuV16BTurbulenceBank[rmuV16BSpeciesID], rmuV16BSpeciesWeight);",
"                rmuV16BEffectiveCohesion = mix(particleCohesion, rmuV16BCohesionBank[rmuV16BSpeciesID], rmuV16BSpeciesWeight);",
"                uint rmuV16BColorBase = rmuV16BSpeciesID * 3u;",
"                rmuV16BEffectiveColor = float3(rmuV16BColorBank[rmuV16BColorBase + 0u], rmuV16BColorBank[rmuV16BColorBase + 1u], rmuV16BColorBank[rmuV16BColorBase + 2u]);",
"            }",
"            float rmuV16BJitter = (fract(sin(float(id + rmuV16BSpeciesID * 131u) * 12.9898) * 43758.5453) - 0.5);",
"            // RMU_V1_6B_SHADER_EFFECTIVE_VALUES_END",
"",
"            float3 base = baseParticles[id].position;"])
    if "RMU_V1_6B_SHADER_EFFECTIVE_VALUES_BEGIN" not in s:
        s, ok = replace(s, guard_old, eff, "shader guard body", False)
        flags.append(f"shaderBody={ok}")
    else: flags.append("shaderBody=already")

    for old, new, name in [
        ("            float speedScalar = clamp(particleSpeed, -3.0, 3.0);", "            float speedScalar = clamp(rmuV16BEffectiveSpeed, -3.0, 3.0);", "speed"),
        ("            float massScalar = max(particleMass, 0.20);", "            float massScalar = max(rmuV16BEffectiveMass, 0.20);", "mass"),
        ("            float turbulenceScalar = clamp(particleTurbulence, 0.0, 2.5);", "            float turbulenceScalar = clamp(rmuV16BEffectiveTurbulence, 0.0, 2.5);", "turb"),
        ("            float cohesionScalar = clamp(particleCohesion, 0.0, 2.5);", "            float cohesionScalar = clamp(rmuV16BEffectiveCohesion, 0.0, 2.5);", "coh"),
    ]:
        if new in s: flags.append(f"{name}=already")
        else:
            s, ok = replace(s, old, new, name, False)
            flags.append(f"{name}={ok}")
    return s, flags

def patch_diag(s):
    anchor = "        appendKV(a, \"gravity\", renderer.rmuGravityVec4Summary(), valueColor: rmuYellow())"
    if "RMU_V1_6B_DIAGNOSTICS_SPECIES_IDENTITY" in s: return s, ["diag=already"]
    block = "\n".join([
anchor,
"        // RMU_V1_6B_DIAGNOSTICS_SPECIES_IDENTITY",
"        appendKV(a, \"species id\", renderer.rmuV16BSpeciesIdentityStatus, valueColor: renderer.rmuV16BSpeciesIdentityLoaded ? rmuGreen() : rmuYellow())"])
    s, ok = replace(s, anchor, block, "hud diag", False)
    return s, [f"diag={ok}"]

def missing(s):
    markers = ["RMU_V1_6B_SPECIES_IDENTITY_STATE_BEGIN","RMU_V1_6B_SPECIES_IDENTITY_LOADER_BEGIN","RMU_V1_6B_SAME_UPLOAD_IDENTITY_CALL","RMU_V1_6B_CREATE_IDENTITY_BUFFERS_AFTER_GPU_BUFFERS","RMU_V1_6B_SPECIES_ENCODER_BINDINGS_BEGIN","RMU_V1_6B_SHADER_SPECIES_ARGS_BEGIN","RMU_V1_6B_SHADER_EFFECTIVE_VALUES_BEGIN"]
    return [m for m in markers if m not in s]

def main():
    print("="*72)
    print(f"RealMathUniverse {VERSION}")
    print(f"Project root: {ROOT}")
    print("="*72)
    if not MAIN.exists(): die(f"missing main.swift: {MAIN}")
    if not IDENTITY_BIN.exists(): die(f"missing v1.6A sidecar: {IDENTITY_BIN}")
    if IDENTITY_BIN.stat().st_size <= 0 or IDENTITY_BIN.stat().st_size % 8 != 0: die(f"bad sidecar byte size: {IDENTITY_BIN.stat().st_size}")
    backup = backup_main()
    original = MAIN.read_text()
    s = original
    flags = []
    try:
        for fn in [patch_state_loader, patch_encoder, patch_shader, patch_diag]:
            s, f = fn(s); flags += f
        miss = missing(s)
        if miss: raise RuntimeError(f"missing required markers: {miss}")
        MAIN.write_text(s)
        print("Patch flags:")
        for f in flags: print("  " + f)
        print("\nBuilding renderer...")
        subprocess.run(["swift","build","-c","release"], cwd=str(ROOT/"metal_renderer"), check=True)
    except Exception as exc:
        MAIN.write_text(original)
        subprocess.run(["swift","build","-c","release"], cwd=str(ROOT/"metal_renderer"), check=False)
        die(f"patch/build failed; restored original main.swift. Error: {exc}", backup=backup)
    final = MAIN.read_text(errors="replace")
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps({"version":VERSION,"ok":True,"timestamp_unix":time.time(),"project_root":str(ROOT),"backup":str(backup),"species_identity_records":IDENTITY_BIN.stat().st_size//8,"swift_build_ok":True,"shader_species_consumption":"RMU_V1_6B_SHADER_SPECIES_ARGS_BEGIN" in final and "RMU_V1_6B_SHADER_EFFECTIVE_VALUES_BEGIN" in final,"flags":flags}, indent=2))
    print("\nV1.6B1 PATCH COMPLETE")
    print("Report:", REPORT)
    print("Backup:", backup)
if __name__=="__main__": main()
