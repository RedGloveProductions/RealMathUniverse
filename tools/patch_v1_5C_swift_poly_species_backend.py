#!/usr/bin/env python3
from __future__ import annotations
from pathlib import Path

ROOT = Path("/Users/Joe/Documents/RealMathUniverse")
MAIN = ROOT / "metal_renderer/Sources/RealMathUniverseMetalRenderer/main.swift"
if not MAIN.exists():
    raise SystemExit(f"PATCH FAILED: missing {MAIN}")

text = MAIN.read_text()
original = text

def insert_after_anchor(src: str, anchors: list[str], insertion: str) -> str:
    if insertion.strip() in src:
        return src
    for anchor in anchors:
        idx = src.find(anchor)
        if idx >= 0:
            end = src.find("\n", idx)
            if end < 0:
                end = len(src)
            return src[:end+1] + insertion + src[end+1:]
    raise SystemExit(f"PATCH FAILED: could not find anchors {anchors}")

state_vars = '''
    // RMU_V1_5C_POLY_SPECIES_CONTROL_STATE
    var particleSpeciesProbability: [Float] = Array(repeating: 0.0, count: 22)
    var particleSpeciesColorMode: [Int32] = Array(repeating: 0, count: 22)
    var particleSpeciesSpeed: [Float] = Array(repeating: 0.0, count: 22)
    var particleSpeciesMass: [Float] = Array(repeating: 2.6, count: 22)
    var particleSpeciesTurbulence: [Float] = Array(repeating: 0.0, count: 22)
    var particleSpeciesCohesion: [Float] = Array(repeating: 0.0, count: 22)
    var particleSpeciesColorHSL: [Float] = Array(repeating: 0.0, count: 22 * 3)
    var particleSpeciesColorRGB: [Float] = Array(repeating: 1.0, count: 22 * 3)
    var particleSpeciesProbabilityVoiceCount: Int = 0
    var particleSpeciesColorModeVoiceCount: Int = 0
    var particleSpeciesSpeedVoiceCount: Int = 0
    var particleSpeciesMassVoiceCount: Int = 0
    var particleSpeciesTurbulenceVoiceCount: Int = 0
    var particleSpeciesCohesionVoiceCount: Int = 0
    var particleSpeciesColorVoiceCount: Int = 0
    var gravityWellPositionVec4: [Float] = Array(repeating: 0.0, count: 4)
    var vcvSceneIndex: Int = 1
'''
if "RMU_V1_5C_POLY_SPECIES_CONTROL_STATE" not in text:
    text = insert_after_anchor(text, ["var vcvChannelValues", "var vcvRawChannelValues", "var vcvStatus"], state_vars)

parser_block = '''
        // RMU_V1_5C_POLY_SPECIES_CONTROL_PARSE
        func rmuFloatArray(_ key: String, _ maxCount: Int) -> [Float] {
            guard let arr = json[key] as? [Any] else { return [] }
            var out: [Float] = []
            for item in arr.prefix(maxCount) {
                if let n = item as? NSNumber { out.append(n.floatValue) }
                else if let d = item as? Double { out.append(Float(d)) }
                else if let f = item as? Float { out.append(f) }
                else if let i = item as? Int { out.append(Float(i)) }
            }
            return out
        }

        func rmuIntArray(_ key: String, _ maxCount: Int) -> [Int32] {
            guard let arr = json[key] as? [Any] else { return [] }
            var out: [Int32] = []
            for item in arr.prefix(maxCount) {
                if let n = item as? NSNumber { out.append(n.int32Value) }
                else if let i = item as? Int { out.append(Int32(i)) }
                else if let d = item as? Double { out.append(Int32(d)) }
            }
            return out
        }

        func rmuCopyFloats(_ values: [Float], _ target: inout [Float], _ count: Int) {
            if values.isEmpty { return }
            for i in 0..<min(count, min(values.count, target.count)) { target[i] = values[i] }
        }

        func rmuCopyInts(_ values: [Int32], _ target: inout [Int32], _ count: Int) {
            if values.isEmpty { return }
            for i in 0..<min(count, min(values.count, target.count)) { target[i] = values[i] }
        }

        let probabilityBank = rmuFloatArray("particle_species_probability", 22)
        rmuCopyFloats(probabilityBank, &particleSpeciesProbability, 22)
        if let n = json["particle_species_probability_voice_count"] as? NSNumber { particleSpeciesProbabilityVoiceCount = n.intValue }

        let colorModeBank = rmuIntArray("particle_species_color_mode", 22)
        rmuCopyInts(colorModeBank, &particleSpeciesColorMode, 22)
        if let n = json["particle_species_color_mode_voice_count"] as? NSNumber { particleSpeciesColorModeVoiceCount = n.intValue }

        let speedBank = rmuFloatArray("particle_species_speed", 22)
        rmuCopyFloats(speedBank, &particleSpeciesSpeed, 22)
        if let n = json["particle_species_speed_voice_count"] as? NSNumber { particleSpeciesSpeedVoiceCount = n.intValue }

        let massBank = rmuFloatArray("particle_species_mass", 22)
        rmuCopyFloats(massBank, &particleSpeciesMass, 22)
        if let n = json["particle_species_mass_voice_count"] as? NSNumber { particleSpeciesMassVoiceCount = n.intValue }
        if !particleSpeciesMass.isEmpty {
            let total = particleSpeciesMass.reduce(Float(0.0), +)
            geospatialParticleMass = total / Float(max(1, particleSpeciesMass.count))
        }

        let turbulenceBank = rmuFloatArray("particle_species_turbulence", 22)
        rmuCopyFloats(turbulenceBank, &particleSpeciesTurbulence, 22)
        if let n = json["particle_species_turbulence_voice_count"] as? NSNumber { particleSpeciesTurbulenceVoiceCount = n.intValue }

        let cohesionBank = rmuFloatArray("particle_species_cohesion", 22)
        rmuCopyFloats(cohesionBank, &particleSpeciesCohesion, 22)
        if let n = json["particle_species_cohesion_voice_count"] as? NSNumber { particleSpeciesCohesionVoiceCount = n.intValue }

        if let hslNested = json["particle_species_color_hsl"] as? [[Any]] {
            var flat: [Float] = []
            for triple in hslNested.prefix(22) {
                for item in triple.prefix(3) {
                    if let n = item as? NSNumber { flat.append(n.floatValue) }
                    else if let d = item as? Double { flat.append(Float(d)) }
                }
            }
            rmuCopyFloats(flat, &particleSpeciesColorHSL, 66)
        }

        if let rgbNested = json["particle_species_color_rgb"] as? [[Any]] {
            var flat: [Float] = []
            for triple in rgbNested.prefix(22) {
                for item in triple.prefix(3) {
                    if let n = item as? NSNumber { flat.append(n.floatValue) }
                    else if let d = item as? Double { flat.append(Float(d)) }
                }
            }
            rmuCopyFloats(flat, &particleSpeciesColorRGB, 66)
        }
        if let n = json["particle_species_color_hsl_voice_count"] as? NSNumber { particleSpeciesColorVoiceCount = n.intValue }

        let gravityVec4 = rmuFloatArray("gravity_well_position_vec4", 4)
        rmuCopyFloats(gravityVec4, &gravityWellPositionVec4, 4)

        if let sceneNumber = json["scene_index"] as? NSNumber {
            let scene = max(1, min(6, sceneNumber.intValue))
            vcvSceneIndex = scene
            if fieldLayerWeights.count > 0 {
                selectedFieldLayerIndex = max(0, min(fieldLayerWeights.count - 1, scene - 1))
            }
            switch scene {
            case 1: behaviorEffectCode = 0
            case 2: behaviorEffectCode = 3
            case 3: behaviorEffectCode = 4
            case 4: behaviorEffectCode = 5
            case 5: behaviorEffectCode = 6
            case 6: behaviorEffectCode = 7
            default: break
            }
        }
'''
if "RMU_V1_5C_POLY_SPECIES_CONTROL_PARSE" not in text:
    loader_idx = text.find("func loadVCVStateIfNeeded()")
    if loader_idx < 0:
        raise SystemExit("PATCH FAILED: loadVCVStateIfNeeded() not found")
    insert_idx = -1
    for anchor in ['if let probabilityNumber', 'if let summary', 'let timestamp', 'vcvLastUpdateUnix']:
        pos = text.find(anchor, loader_idx)
        if pos >= 0:
            insert_idx = pos
            break
    if insert_idx < 0:
        raise SystemExit("PATCH FAILED: no safe insertion point inside loadVCVStateIfNeeded")
    text = text[:insert_idx] + parser_block + "\n" + text[insert_idx:]

repls = {
    '"/ch/1 probability"': '"/ch/1 probability_bank"',
    '"/ch/7 color"': '"/ch/7 color_mode_bank"',
    '"/ch/9 particle_speed"': '"/ch/9 particle_speed_bank"',
    '"/ch/10 particle_mass"': '"/ch/10 species_mass_bank_A"',
    '"/ch/11 particle_turbulence"': '"/ch/11 species_mass_bank_B"',
    '"/ch/12 particle_cohesion"': '"/ch/12 particle_turbulence_bank"',
    '"/ch/13 gravity_well_position"': '"/ch/13 particle_cohesion_bank"',
    '"/ch/14 gravity_well_strength"': '"/ch/14 gravity_well_position_vec4"',
    '"/ch/15 aux_15"': '"/ch/15 gravity_well_strength"',
    '"/ch/16 aux_16"': '"/ch/16 species_color_hsl_bank_A"',
    '"/ch/17 aux_17"': '"/ch/17 species_color_hsl_bank_B"',
}
for old, new in repls.items():
    text = text.replace(old, new)

if text != original:
    MAIN.write_text(text)
    print("Swift main.swift patched for v1.5C poly species backend parsing.")
else:
    print("Swift main.swift already had v1.5C markers; no changes made.")
