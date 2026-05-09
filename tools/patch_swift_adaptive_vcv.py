#!/usr/bin/env python3
# ================================================================
# RealMathUniverse v1.5A Swift adaptive VCV patcher
# Conservative source patcher. Backs up main.swift first.
# ================================================================

from __future__ import annotations

import re
import shutil
import sys
from pathlib import Path

PROJECT_ROOT = Path("/Users/Joe/Documents/RealMathUniverse")
MAIN_SWIFT = PROJECT_ROOT / "metal_renderer/Sources/RealMathUniverseMetalRenderer/main.swift"


def die(msg: str, code: int = 1) -> None:
    print(f"SWIFT PATCH: {msg}")
    sys.exit(code)


def main() -> None:
    if not MAIN_SWIFT.exists():
        die(f"main.swift not found at {MAIN_SWIFT}")

    text = MAIN_SWIFT.read_text()
    original = text

    backup = MAIN_SWIFT.with_suffix(".swift.v1_5A_adaptive_backup")
    if not backup.exists():
        shutil.copy2(MAIN_SWIFT, backup)
        print(f"SWIFT PATCH: backup written to {backup}")

    globals_block = '''
// RMU_V1_5A_ADAPTIVE_VCV_GLOBALS_BEGIN
var adaptiveGravityWellPosition = SIMD3<Float>(0.0, 0.0, 0.0)
var adaptiveGravityWellPositionRaw = SIMD3<Float>(0.0, 0.0, 0.0)
var adaptiveGravityWellStrength: Float = 0.0
var adaptiveGravityWellStrengthRaw: Float = 0.0
// RMU_V1_5A_ADAPTIVE_VCV_GLOBALS_END
'''
    if "RMU_V1_5A_ADAPTIVE_VCV_GLOBALS_BEGIN" not in text:
        m = re.search(r"(var\s+gravityWellStrength\w*\s*:\s*Float\s*=\s*[-0-9.]+.*?\n)", text)
        if m:
            text = text[:m.end()] + globals_block + text[m.end():]
        else:
            m = re.search(r"(import\s+MetalKit\s*\n|import\s+Cocoa\s*\n|import\s+Foundation\s*\n)", text)
            if not m:
                die("could not find a safe global insertion anchor")
            text = text[:m.end()] + globals_block + text[m.end():]

    helper = '''
// RMU_V1_5A_ADAPTIVE_VCV_HELPERS_BEGIN
func rmuV15FloatArray(_ value: Any?) -> [Float]? {
    if let arr = value as? [Any] {
        return arr.compactMap { item in
            if let d = item as? Double { return Float(d) }
            if let f = item as? Float { return f }
            if let i = item as? Int { return Float(i) }
            if let n = item as? NSNumber { return n.floatValue }
            return nil
        }
    }
    if let arr = value as? [Double] { return arr.map { Float($0) } }
    if let arr = value as? [Float] { return arr }
    return nil
}

func rmuV15Float(_ value: Any?) -> Float? {
    if let d = value as? Double { return Float(d) }
    if let f = value as? Float { return f }
    if let i = value as? Int { return Float(i) }
    if let n = value as? NSNumber { return n.floatValue }
    return nil
}
// RMU_V1_5A_ADAPTIVE_VCV_HELPERS_END
'''
    if "RMU_V1_5A_ADAPTIVE_VCV_HELPERS_BEGIN" not in text:
        idx = text.find("func loadVCVStateIfNeeded")
        if idx < 0:
            die("loadVCVStateIfNeeded not found; not patching Swift")
        text = text[:idx] + helper + "\n" + text[idx:]

    adaptive_parse = '''
        // RMU_V1_5A_ADAPTIVE_VCV_PARSE_BEGIN
        // v1.5A reads adaptive polyphonic vec3 gravity-well data from vcv_state.json.
        if let vec = rmuV15FloatArray(vcv["gravity_well_position_vec3"]), vec.count >= 3 {
            adaptiveGravityWellPosition = SIMD3<Float>(
                max(-1.0, min(vec[0], 1.0)),
                max(-1.0, min(vec[1], 1.0)),
                max(-1.0, min(vec[2], 1.0))
            )
            if vcvChannelValues.count >= 13 { vcvChannelValues[12] = adaptiveGravityWellPosition.x }
            if vcvChannelValues.count >= 15 { vcvChannelValues[14] = adaptiveGravityWellPosition.y }
            if vcvChannelValues.count >= 16 { vcvChannelValues[15] = adaptiveGravityWellPosition.z }
        } else if let x = rmuV15Float(vcv["gravity_well_position"]) {
            adaptiveGravityWellPosition.x = max(-1.0, min(x, 1.0))
            if vcvChannelValues.count >= 13 { vcvChannelValues[12] = adaptiveGravityWellPosition.x }
        }

        if let rawVec = rmuV15FloatArray(vcv["gravity_well_position_raw_vec3"]), rawVec.count >= 3 {
            adaptiveGravityWellPositionRaw = SIMD3<Float>(rawVec[0], rawVec[1], rawVec[2])
            if vcvRawChannelValues.count >= 13 { vcvRawChannelValues[12] = adaptiveGravityWellPositionRaw.x }
            if vcvRawChannelValues.count >= 15 { vcvRawChannelValues[14] = adaptiveGravityWellPositionRaw.y }
            if vcvRawChannelValues.count >= 16 { vcvRawChannelValues[15] = adaptiveGravityWellPositionRaw.z }
        }

        if let s = rmuV15Float(vcv["gravity_well_strength"]) {
            adaptiveGravityWellStrength = max(0.0, min(s, 12.0))
            if vcvChannelValues.count >= 14 { vcvChannelValues[13] = adaptiveGravityWellStrength }
        }
        if let sr = rmuV15Float(vcv["gravity_well_strength_raw"]) {
            adaptiveGravityWellStrengthRaw = sr
            if vcvRawChannelValues.count >= 14 { vcvRawChannelValues[13] = adaptiveGravityWellStrengthRaw }
        }
        // RMU_V1_5A_ADAPTIVE_VCV_PARSE_END
'''
    if "RMU_V1_5A_ADAPTIVE_VCV_PARSE_BEGIN" not in text:
        func_idx = text.find("func loadVCVStateIfNeeded")
        if func_idx < 0:
            die("loadVCVStateIfNeeded not found")
        insert_at = -1
        for a in ["gravity_well_strength_raw", "gravity_well_strength", "vcvChannelValues[13]", "vcvRawChannelValues[13]"]:
            pos = text.find(a, func_idx)
            if pos >= 0:
                line_end = text.find("\n", pos)
                insert_at = max(insert_at, line_end + 1)
        if insert_at < 0:
            brace = text.find("{", func_idx)
            if brace < 0:
                die("could not locate loadVCVStateIfNeeded opening brace")
            insert_at = brace + 1
        text = text[:insert_at] + adaptive_parse + text[insert_at:]

    encoder_block = '''
        // RMU_V1_5A_ADAPTIVE_GRAVITY_ENCODER_BEGIN
        var rmuV15GravityWellPositionVec3 = adaptiveGravityWellPosition
        encoder.setBytes(&rmuV15GravityWellPositionVec3, length: MemoryLayout<SIMD3<Float>>.stride, index: 18)
        var rmuV15GravityWellStrength = adaptiveGravityWellStrength
        encoder.setBytes(&rmuV15GravityWellStrength, length: MemoryLayout<Float>.stride, index: 19)
        // RMU_V1_5A_ADAPTIVE_GRAVITY_ENCODER_END
'''
    if "RMU_V1_5A_ADAPTIVE_GRAVITY_ENCODER_BEGIN" not in text:
        pos = text.find("GRAVITY_WELL_ENCODER")
        if pos < 0:
            pos = text.find("encoder.setBytes(&gravityWellStrength")
        if pos >= 0:
            line_end = text.find("\n", pos)
            if line_end < 0:
                line_end = pos
            text = text[:line_end + 1] + encoder_block + text[line_end + 1:]
        else:
            print("SWIFT PATCH: WARNING: could not find gravity encoder anchor; JSON/HUD arrays patched, shader encoder may need manual patching.")

    text = text.replace(
        "constant float &gravityWellPosition [[buffer(18)]],",
        "constant float3 &gravityWellPosition [[buffer(18)]],"
    )
    text = text.replace("gravityWellPosition)", "gravityWellPosition.x)")
    text = text.replace("gravityWellPosition;", "gravityWellPosition.x;")

    if text == original:
        die("no Swift changes were made; source may already be patched or anchors changed", 2)

    MAIN_SWIFT.write_text(text)
    print("SWIFT PATCH: main.swift patched for v1.5A adaptive VCV support")
    print("SWIFT PATCH: run: cd /Users/Joe/Documents/RealMathUniverse/metal_renderer && swift build -c release")


if __name__ == "__main__":
    main()
