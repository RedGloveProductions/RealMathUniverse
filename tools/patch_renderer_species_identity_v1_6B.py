#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

VERSION = "v1.6B_renderer_species_identity_metal"
ROOT = Path(sys.argv[1]).expanduser().resolve() if len(sys.argv) > 1 else Path("/Users/Joe/Documents/RealMathUniverse")
MAIN = ROOT / "metal_renderer" / "Sources" / "RealMathUniverseMetalRenderer" / "main.swift"
IDENTITY_BIN = ROOT / "data" / "processed" / "species_identity_v1_6A.bin"
REPORT = ROOT / "output" / "v1_6B_renderer_species_identity_patch_report.json"

def fail(msg: str) -> None:
    print("V1.6B PATCH FAILED:", msg)
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps({
        "version": VERSION,
        "ok": False,
        "message": msg,
        "timestamp_unix": time.time(),
    }, indent=2))
    raise SystemExit(1)

def backup_file(path: Path) -> Path:
    stamp = time.strftime("%Y%m%d_%H%M%S")
    bdir = ROOT / "backups" / VERSION
    bdir.mkdir(parents=True, exist_ok=True)
    dst = bdir / f"{path.name}.{stamp}.bak"
    shutil.copy2(path, dst)
    return dst

def insert_after_line(text: str, anchor: str, insertion: str, marker: str) -> tuple[str, bool]:
    if marker in text:
        return text, False
    idx = text.find(anchor)
    if idx < 0:
        return text, False
    end = text.find("\n", idx)
    if end < 0:
        end = len(text)
    return text[:end+1] + insertion + text[end+1:], True

def insert_before(text: str, anchor: str, insertion: str, marker: str) -> tuple[str, bool]:
    if marker in text:
        return text, False
    idx = text.find(anchor)
    if idx < 0:
        return text, False
    return text[:idx] + insertion + text[idx:], True

def find_matching_brace(text: str, open_brace_index: int) -> int:
    depth = 0
    in_string = False
    escape = False
    for i in range(open_brace_index, len(text)):
        ch = text[i]
        if in_string:
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == '"':
                in_string = False
            continue
        if ch == '"':
            in_string = True
            continue
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return i
    return -1

def patch_swift_state_and_loader(text: str) -> tuple[str, list[str]]:
    flags = []

    state_block = """
    // RMU_V1_6B_SPECIES_IDENTITY_STATE_BEGIN
    var rmuV16BSpeciesIdentityLoaded: Bool = false
    var rmuV16BSpeciesIdentityRecordCount: Int = 0
    var rmuV16BSpeciesIdentityParticleCount: Int = 0
    var rmuV16BSpeciesIdentityStatus: String = "not loaded"
    var rmuV16BSpeciesIdentityLastError: String = "none"
    var rmuV16BSpeciesControlEnabled: Float = 1.0

    var rmuV16BSpeciesIDCPU: [UInt32] = []
    var rmuV16BFamilyIDCPU: [UInt32] = []
    var rmuV16BSpeciesWeightCPU: [Float] = []

    var rmuV16BSpeciesIDBuffer: MTLBuffer? = nil
    var rmuV16BFamilyIDBuffer: MTLBuffer? = nil
    var rmuV16BSpeciesWeightBuffer: MTLBuffer? = nil
    // RMU_V1_6B_SPECIES_IDENTITY_STATE_END
"""
    anchors = [
        "    var vcvRawChannelValues: [Float] = Array(repeating: 0.0, count: 32)",
        "    var lastUploadedModificationDate",
        "    var baseParticleBuffer:"
    ]
    inserted = False
    for a in anchors:
        text, ok = insert_after_line(text, a, state_block, "RMU_V1_6B_SPECIES_IDENTITY_STATE_BEGIN")
        if ok:
            inserted = True
            break
    flags.append(f"state_block_inserted={inserted or ('RMU_V1_6B_SPECIES_IDENTITY_STATE_BEGIN' in text)}")

    helper_block = """
    // RMU_V1_6B_SPECIES_IDENTITY_LOADER_BEGIN
    func rmuV16BReadUInt16LE(_ bytes: [UInt8], _ offset: Int) -> UInt16 {
        if offset + 1 >= bytes.count { return 0 }
        return UInt16(bytes[offset]) | (UInt16(bytes[offset + 1]) << 8)
    }

    func rmuV16BReadFloat32LE(_ bytes: [UInt8], _ offset: Int) -> Float {
        if offset + 3 >= bytes.count { return 0.0 }
        let bits =
            UInt32(bytes[offset]) |
            (UInt32(bytes[offset + 1]) << 8) |
            (UInt32(bytes[offset + 2]) << 16) |
            (UInt32(bytes[offset + 3]) << 24)
        return Float(bitPattern: bits)
    }

    func rmuV16BPackBank32(_ source: [Float], fallback: Float) -> [Float] {
        var out = Array(repeating: fallback, count: 32)
        if source.isEmpty { return out }
        for i in 0..<min(32, source.count) { out[i] = source[i] }
        return out
    }

    func rmuV16BPackColorBank96(_ source: [Float]) -> [Float] {
        var out = Array(repeating: Float(1.0), count: 96)
        if source.isEmpty { return out }
        for i in 0..<min(96, source.count) { out[i] = source[i] }
        return out
    }

    func rmuV16BLoadSpeciesIdentityBuffersForParticleCount(_ particleCount: Int) {
        if particleCount <= 0 {
            rmuV16BSpeciesIdentityStatus = "no particles"
            return
        }

        if rmuV16BSpeciesIdentityLoaded &&
           rmuV16BSpeciesIdentityParticleCount == particleCount &&
           rmuV16BSpeciesIDBuffer != nil &&
           rmuV16BFamilyIDBuffer != nil &&
           rmuV16BSpeciesWeightBuffer != nil {
            return
        }

        let binURL = URL(fileURLWithPath: projectRoot)
            .appendingPathComponent("data")
            .appendingPathComponent("processed")
            .appendingPathComponent("species_identity_v1_6A.bin")

        guard let data = try? Data(contentsOf: binURL) else {
            rmuV16BSpeciesIdentityLoaded = false
            rmuV16BSpeciesIdentityStatus = "missing species_identity_v1_6A.bin"
            rmuV16BSpeciesIdentityLastError = binURL.path
            return
        }

        let bytes = [UInt8](data)
        let recordSize = 8
        let records = bytes.count / recordSize
        if records <= 0 {
            rmuV16BSpeciesIdentityLoaded = false
            rmuV16BSpeciesIdentityStatus = "empty species identity"
            rmuV16BSpeciesIdentityLastError = binURL.path
            return
        }

        var speciesIDs = Array(repeating: UInt32(0), count: particleCount)
        var familyIDs = Array(repeating: UInt32(0), count: particleCount)
        var weights = Array(repeating: Float(1.0), count: particleCount)

        let copyCount = min(records, particleCount)
        for i in 0..<copyCount {
            let offset = i * recordSize
            speciesIDs[i] = UInt32(min(rmuV16BReadUInt16LE(bytes, offset), UInt16(21)))
            familyIDs[i] = UInt32(min(rmuV16BReadUInt16LE(bytes, offset + 2), UInt16(6)))
            weights[i] = max(0.0, min(rmuV16BReadFloat32LE(bytes, offset + 4), 1.0))
        }

        if records < particleCount {
            for i in records..<particleCount {
                let sourceIndex = i % max(records, 1)
                speciesIDs[i] = speciesIDs[sourceIndex]
                familyIDs[i] = familyIDs[sourceIndex]
                weights[i] = weights[sourceIndex]
            }
        }

        let idLength = max(1, particleCount) * MemoryLayout<UInt32>.stride
        let weightLength = max(1, particleCount) * MemoryLayout<Float>.stride

        rmuV16BSpeciesIDCPU = speciesIDs
        rmuV16BFamilyIDCPU = familyIDs
        rmuV16BSpeciesWeightCPU = weights

        rmuV16BSpeciesIDBuffer = speciesIDs.withUnsafeBytes {
            device.makeBuffer(bytes: $0.baseAddress!, length: idLength, options: [.storageModeShared])
        }
        rmuV16BFamilyIDBuffer = familyIDs.withUnsafeBytes {
            device.makeBuffer(bytes: $0.baseAddress!, length: idLength, options: [.storageModeShared])
        }
        rmuV16BSpeciesWeightBuffer = weights.withUnsafeBytes {
            device.makeBuffer(bytes: $0.baseAddress!, length: weightLength, options: [.storageModeShared])
        }

        rmuV16BSpeciesIdentityLoaded =
            rmuV16BSpeciesIDBuffer != nil &&
            rmuV16BFamilyIDBuffer != nil &&
            rmuV16BSpeciesWeightBuffer != nil
        rmuV16BSpeciesIdentityRecordCount = records
        rmuV16BSpeciesIdentityParticleCount = particleCount

        if records == particleCount {
            rmuV16BSpeciesIdentityStatus = "loaded \(records)/\(particleCount)"
        } else {
            rmuV16BSpeciesIdentityStatus = "loaded \(records)/\(particleCount) count mismatch handled"
        }

        print("RMU v1.6B species identity: \(rmuV16BSpeciesIdentityStatus)")
    }
    // RMU_V1_6B_SPECIES_IDENTITY_LOADER_END

"""
    method_anchors = [
        "    func updateParticleBufferIfNeeded()",
        "    func encodeGeospatialParticleUpdate(commandBuffer:",
        "    func loadVCVStateIfNeeded()"
    ]
    inserted = False
    for a in method_anchors:
        text, ok = insert_before(text, a, helper_block, "RMU_V1_6B_SPECIES_IDENTITY_LOADER_BEGIN")
        if ok:
            inserted = True
            break
    flags.append(f"loader_inserted={inserted or ('RMU_V1_6B_SPECIES_IDENTITY_LOADER_BEGIN' in text)}")

    if "RMU_V1_6B_SAME_UPLOAD_IDENTITY_CALL" not in text:
        old = "        if sameUpload { return }"
        if old in text:
            text = text.replace(old, "        if sameUpload {\n            // RMU_V1_6B_SAME_UPLOAD_IDENTITY_CALL\n            rmuV16BLoadSpeciesIdentityBuffersForParticleCount(particles.count)\n            return\n        }", 1)
            flags.append("same_upload_call_inserted=True")
        else:
            flags.append("same_upload_call_inserted=False_anchor_missing")
    else:
        flags.append("same_upload_call_inserted=already_present")

    if "RMU_V1_6B_CREATE_IDENTITY_BUFFERS_AFTER_GPU_BUFFERS" not in text:
        anchors2 = [
            "        velocityParticleBuffer = velocityBuffer",
            "        particleBuffer = liveBuffer",
        ]
        done = False
        for a in anchors2:
            if a in text:
                text = text.replace(a, a + "\n        // RMU_V1_6B_CREATE_IDENTITY_BUFFERS_AFTER_GPU_BUFFERS\n        rmuV16BLoadSpeciesIdentityBuffersForParticleCount(particles.count)", 1)
                done = True
                break
        flags.append(f"post_gpu_buffer_call_inserted={done}")
    else:
        flags.append("post_gpu_buffer_call_inserted=already_present")

    return text, flags

def patch_encoder(text: str) -> tuple[str, list[str]]:
    flags = []
    if "RMU_V1_6B_SPECIES_ENCODER_BINDINGS_BEGIN" in text:
        flags.append("encoder_bindings=already_present")
        return text, flags

    anchors = [
        "        var count = UInt32(max(0, lastUploadedParticleCount))\n        if count == 0 { return }",
        "        if count == 0 { return }"
    ]
    insertion = """

        // RMU_V1_6B_SPECIES_ENCODER_BINDINGS_BEGIN
        rmuV16BLoadSpeciesIdentityBuffersForParticleCount(Int(count))
        guard let rmuV16BSpeciesIDBufferLive = rmuV16BSpeciesIDBuffer,
              let rmuV16BFamilyIDBufferLive = rmuV16BFamilyIDBuffer,
              let rmuV16BSpeciesWeightBufferLive = rmuV16BSpeciesWeightBuffer else {
            rmuV16BSpeciesIdentityStatus = "identity buffers unavailable during encode"
            return
        }

        var rmuV16BProbabilityBank = rmuV16BPackBank32(particleSpeciesProbability, fallback: 1.0)
        var rmuV16BSpeedBank = rmuV16BPackBank32(particleSpeciesSpeed, fallback: geospatialParticleSpeed)
        var rmuV16BMassBank = rmuV16BPackBank32(particleSpeciesMass, fallback: geospatialParticleMass)
        var rmuV16BTurbulenceBank = rmuV16BPackBank32(particleSpeciesTurbulence, fallback: geospatialParticleTurbulence)
        var rmuV16BCohesionBank = rmuV16BPackBank32(particleSpeciesCohesion, fallback: geospatialParticleCohesion)
        var rmuV16BColorBank = rmuV16BPackColorBank96(particleSpeciesColorRGB)
        var rmuV16BEnabled = rmuV16BSpeciesControlEnabled

        encoder.setBuffer(rmuV16BSpeciesIDBufferLive, offset: 0, index: 20)
        encoder.setBuffer(rmuV16BFamilyIDBufferLive, offset: 0, index: 21)
        encoder.setBuffer(rmuV16BSpeciesWeightBufferLive, offset: 0, index: 22)
        rmuV16BProbabilityBank.withUnsafeBytes { encoder.setBytes($0.baseAddress!, length: $0.count, index: 23) }
        rmuV16BSpeedBank.withUnsafeBytes { encoder.setBytes($0.baseAddress!, length: $0.count, index: 24) }
        rmuV16BMassBank.withUnsafeBytes { encoder.setBytes($0.baseAddress!, length: $0.count, index: 25) }
        rmuV16BTurbulenceBank.withUnsafeBytes { encoder.setBytes($0.baseAddress!, length: $0.count, index: 26) }
        rmuV16BCohesionBank.withUnsafeBytes { encoder.setBytes($0.baseAddress!, length: $0.count, index: 27) }
        rmuV16BColorBank.withUnsafeBytes { encoder.setBytes($0.baseAddress!, length: $0.count, index: 28) }
        encoder.setBytes(&rmuV16BEnabled, length: MemoryLayout<Float>.stride, index: 30)
        // RMU_V1_6B_SPECIES_ENCODER_BINDINGS_END
"""
    done = False
    for a in anchors:
        idx = text.find(a)
        if idx >= 0:
            end = idx + len(a)
            text = text[:end] + insertion + text[end:]
            done = True
            break
    flags.append(f"encoder_bindings_inserted={done}")
    return text, flags

def patch_shader(text: str) -> tuple[str, list[str]]:
    flags = []
    if "RMU_V1_6B_SHADER_SPECIES_ARGS_BEGIN" in text and "RMU_V1_6B_SHADER_EFFECTIVE_VALUES_BEGIN" in text:
        flags.append("shader_patch=already_present")
        return text, flags

    kernel_match = re.search(r'kernel\s+void\s+([A-Za-z0-9_]*[Gg]eospatial[A-Za-z0-9_]*|[A-Za-z0-9_]*[Pp]article[A-Za-z0-9_]*Update[A-Za-z0-9_]*)\s*\(', text)
    if not kernel_match:
        kernel_match = re.search(r'kernel\s+void\s+updateGeospatialParticles\s*\(', text)
    if not kernel_match:
        flags.append("shader_kernel_found=False")
        return text, flags

    paren_start = text.find("(", kernel_match.end()-1)
    depth = 0
    paren_end = -1
    for i in range(paren_start, len(text)):
        if text[i] == "(":
            depth += 1
        elif text[i] == ")":
            depth -= 1
            if depth == 0:
                paren_end = i
                break
    if paren_end < 0:
        flags.append("shader_signature_parse=False")
        return text, flags

    open_brace = text.find("{", paren_end)
    if open_brace < 0:
        flags.append("shader_body_parse=False")
        return text, flags
    close_brace = find_matching_brace(text, open_brace)
    if close_brace < 0:
        flags.append("shader_body_matching_brace=False")
        return text, flags

    signature = text[paren_start+1:paren_end]
    body = text[open_brace+1:close_brace]

    if "RMU_V1_6B_SHADER_SPECIES_ARGS_BEGIN" not in signature:
        species_args = """
    // RMU_V1_6B_SHADER_SPECIES_ARGS_BEGIN
    , constant uint *rmuV16BSpeciesIDs [[buffer(20)]]
    , constant uint *rmuV16BFamilyIDs [[buffer(21)]]
    , constant float *rmuV16BSpeciesWeights [[buffer(22)]]
    , constant float *rmuV16BProbabilityBank [[buffer(23)]]
    , constant float *rmuV16BSpeedBank [[buffer(24)]]
    , constant float *rmuV16BMassBank [[buffer(25)]]
    , constant float *rmuV16BTurbulenceBank [[buffer(26)]]
    , constant float *rmuV16BCohesionBank [[buffer(27)]]
    , constant float *rmuV16BColorBank [[buffer(28)]]
    , constant float &rmuV16BSpeciesControlEnabled [[buffer(30)]]
    // RMU_V1_6B_SHADER_SPECIES_ARGS_END
"""
        signature = signature.rstrip() + species_args
        flags.append("shader_args_inserted=True")

    if "RMU_V1_6B_SHADER_EFFECTIVE_VALUES_BEGIN" not in body:
        id_name = None
        for pat in [r'uint\s+(\w+)\s*=\s*gid', r'uint\s+(\w+)\s*=\s*id', r'uint\s+(\w+)\s*=\s*thread_position_in_grid']:
            m = re.search(pat, body)
            if m:
                id_name = m.group(1)
                break
        if id_name is None:
            id_name = "id"

        guard_patterns = [
            rf'if\s*\(\s*{re.escape(id_name)}\s*>=\s*count\s*\)\s*\{{\s*return;\s*\}}',
            rf'if\s*\(\s*{re.escape(id_name)}\s*>=\s*count\s*\)\s*return;',
            r'if\s*\(\s*id\s*>=\s*count\s*\)\s*\{\s*return;\s*\}',
            r'if\s*\(\s*id\s*>=\s*count\s*\)\s*return;'
        ]
        insert_pos = -1
        for pat in guard_patterns:
            m = re.search(pat, body)
            if m:
                insert_pos = m.end()
                break

        if insert_pos < 0:
            flags.append("shader_body_insert_anchor=False")
        else:
            effective = f"""

    // RMU_V1_6B_SHADER_EFFECTIVE_VALUES_BEGIN
    uint rmuV16BSpeciesID = 0;
    uint rmuV16BFamilyID = 0;
    float rmuV16BSpeciesWeight = 1.0;
    float rmuV16BEffectiveProbability = 1.0;
    float rmuV16BEffectiveSpeed = particleSpeed;
    float rmuV16BEffectiveMass = particleMass;
    float rmuV16BEffectiveTurbulence = 0.0;
    float rmuV16BEffectiveCohesion = 0.0;
    float3 rmuV16BEffectiveColor = float3(1.0, 1.0, 1.0);

    if (rmuV16BSpeciesControlEnabled > 0.5) {{
        rmuV16BSpeciesID = min(rmuV16BSpeciesIDs[{id_name}], 21u);
        rmuV16BFamilyID = min(rmuV16BFamilyIDs[{id_name}], 6u);
        rmuV16BSpeciesWeight = clamp(rmuV16BSpeciesWeights[{id_name}], 0.0, 1.0);

        rmuV16BEffectiveProbability = clamp(rmuV16BProbabilityBank[rmuV16BSpeciesID], 0.0, 1.0);
        rmuV16BEffectiveSpeed = mix(particleSpeed, rmuV16BSpeedBank[rmuV16BSpeciesID], rmuV16BSpeciesWeight);
        rmuV16BEffectiveMass = max(0.05, mix(particleMass, rmuV16BMassBank[rmuV16BSpeciesID], rmuV16BSpeciesWeight));
        rmuV16BEffectiveTurbulence = rmuV16BTurbulenceBank[rmuV16BSpeciesID] * rmuV16BSpeciesWeight;
        rmuV16BEffectiveCohesion = rmuV16BCohesionBank[rmuV16BSpeciesID] * rmuV16BSpeciesWeight;
        uint rmuV16BColorBase = rmuV16BSpeciesID * 3u;
        rmuV16BEffectiveColor = float3(
            rmuV16BColorBank[rmuV16BColorBase + 0u],
            rmuV16BColorBank[rmuV16BColorBase + 1u],
            rmuV16BColorBank[rmuV16BColorBase + 2u]
        );
    }}
    // RMU_V1_6B_SHADER_EFFECTIVE_VALUES_END
    // RMU_V1_6B_SHADER_SPECIES_FORCE_HINT_BEGIN
    float rmuV16BJitter = (fract(sin(float({id_name} + rmuV16BSpeciesID * 131u) * 12.9898) * 43758.5453) - 0.5);
    // RMU_V1_6B_SHADER_SPECIES_FORCE_HINT_END
"""
            body = body[:insert_pos] + effective + body[insert_pos:]
            flags.append("shader_effective_values_inserted=True")

            body = re.sub(r'\bparticleSpeed\b', 'rmuV16BEffectiveSpeed', body)
            body = re.sub(r'\bparticleMass\b', 'rmuV16BEffectiveMass', body)
            body = body.replace("float rmuV16BEffectiveSpeed = rmuV16BEffectiveSpeed;", "float rmuV16BEffectiveSpeed = particleSpeed;")
            body = body.replace("float rmuV16BEffectiveMass = rmuV16BEffectiveMass;", "float rmuV16BEffectiveMass = particleMass;")
            flags.append("shader_particleSpeed_particleMass_scoped_rewrite=True")

    new_text = text[:paren_start+1] + signature + text[paren_end:open_brace+1] + body + text[close_brace:]
    flags.append("shader_kernel_found=True")
    return new_text, flags

def patch_diagnostics(text: str) -> tuple[str, list[str]]:
    flags = []
    if "RMU_V1_6B_DIAGNOSTICS_SPECIES_IDENTITY" in text:
        flags.append("diagnostics=already_present")
        return text, flags

    target = "vcvChannelCompactSummary())\\\")"
    if target in text:
        repl = "vcvChannelCompactSummary()) | SPECIES_ID=\\\(rmuV16BSpeciesIdentityStatus) | SID_BUF=\\\(rmuV16BSpeciesIDBuffer != nil) | FID_BUF=\\\(rmuV16BFamilyIDBuffer != nil) | W_BUF=\\\(rmuV16BSpeciesWeightBuffer != nil)\\\") // RMU_V1_6B_DIAGNOSTICS_SPECIES_IDENTITY"
        text = text.replace(target, repl, 1)
        flags.append("diagnostics_printDiagnostics_inserted=True")
    else:
        flags.append("diagnostics_printDiagnostics_inserted=False_anchor_missing")
    return text, flags

def main() -> int:
    print("=" * 72)
    print(f"RealMathUniverse {VERSION}")
    print(f"Project root: {ROOT}")
    print("=" * 72)

    if not MAIN.exists():
        fail(f"main.swift not found: {MAIN}")
    if not IDENTITY_BIN.exists():
        fail(f"species identity sidecar not found: {IDENTITY_BIN}. Run v1.6A first.")
    if IDENTITY_BIN.stat().st_size == 0 or IDENTITY_BIN.stat().st_size % 8 != 0:
        fail(f"invalid species identity sidecar size: {IDENTITY_BIN.stat().st_size}")

    backup = backup_file(MAIN)
    text = MAIN.read_text()
    original = text
    all_flags = []

    text, flags = patch_swift_state_and_loader(text)
    all_flags += flags
    text, flags = patch_encoder(text)
    all_flags += flags
    text, flags = patch_shader(text)
    all_flags += flags
    text, flags = patch_diagnostics(text)
    all_flags += flags

    required_markers = [
        "RMU_V1_6B_SPECIES_IDENTITY_STATE_BEGIN",
        "RMU_V1_6B_SPECIES_IDENTITY_LOADER_BEGIN",
        "RMU_V1_6B_SPECIES_ENCODER_BINDINGS_BEGIN",
    ]

    missing = [m for m in required_markers if m not in text]
    if missing:
        MAIN.write_text(original)
        fail(f"required Swift markers missing after patch: {missing}")

    shader_ok = "RMU_V1_6B_SHADER_SPECIES_ARGS_BEGIN" in text and "RMU_V1_6B_SHADER_EFFECTIVE_VALUES_BEGIN" in text
    if not shader_ok:
        print("WARNING: shader species args/effective block not found. The patch installed CPU/encoder buffers but did not locate the kernel.")
        print("The validator will mark SHADER_SPECIES_CONSUMPTION as false.")

    if text != original:
        MAIN.write_text(text)

    print("Patch flags:")
    for flag in all_flags:
        print("  " + flag)

    print()
    print("Building renderer...")
    build_ok = False
    try:
        subprocess.run(["swift", "build", "-c", "release"], cwd=str(ROOT / "metal_renderer"), check=True)
        build_ok = True
    except subprocess.CalledProcessError as e:
        shutil.copy2(backup, MAIN)
        fail(f"swift build failed; restored backup {backup}. Error: {e}")

    report = {
        "version": VERSION,
        "ok": True,
        "timestamp_unix": time.time(),
        "project_root": str(ROOT),
        "main_swift": str(MAIN),
        "backup": str(backup),
        "species_identity_bin": str(IDENTITY_BIN),
        "species_identity_records": IDENTITY_BIN.stat().st_size // 8,
        "swift_build_ok": build_ok,
        "shader_species_consumption": shader_ok,
        "flags": all_flags,
        "markers": {m: (m in MAIN.read_text(errors="replace")) for m in [
            "RMU_V1_6B_SPECIES_IDENTITY_STATE_BEGIN",
            "RMU_V1_6B_SPECIES_IDENTITY_LOADER_BEGIN",
            "RMU_V1_6B_SPECIES_ENCODER_BINDINGS_BEGIN",
            "RMU_V1_6B_SHADER_SPECIES_ARGS_BEGIN",
            "RMU_V1_6B_SHADER_EFFECTIVE_VALUES_BEGIN",
            "RMU_V1_6B_DIAGNOSTICS_SPECIES_IDENTITY",
        ]},
    }
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(report, indent=2))

    print()
    print("V1.6B PATCH COMPLETE")
    print(f"Report: {REPORT}")
    print(f"Backup: {backup}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
