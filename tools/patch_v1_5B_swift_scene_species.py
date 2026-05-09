#!/usr/bin/env python3
from pathlib import Path
ROOT=Path('/Users/Joe/Documents/RealMathUniverse')
MAIN=ROOT/'metal_renderer/Sources/RealMathUniverseMetalRenderer/main.swift'
if not MAIN.exists(): raise SystemExit(f'SWIFT PATCH FAILED: missing {MAIN}')
text=MAIN.read_text(); orig=text
def insert_after(src,needle,ins):
    if ins.strip() in src: return src
    idx=src.find(needle)
    if idx<0: raise SystemExit(f'SWIFT PATCH FAILED: missing anchor {needle}')
    end=src.find('\n',idx)
    return src[:end+1]+ins+src[end+1:]
props='''\n    // RMU_V1_5B_SPECIES_MASS_STATE\n    var particleSpeciesMass: [Float] = Array(repeating: 2.6, count: 22)\n    var particleSpeciesMassRaw: [Float] = Array(repeating: 0.0, count: 22)\n    var particleSpeciesMassVoiceCount: Int = 0\n    var vcvSceneIndex: Int = 1\n'''
if 'RMU_V1_5B_SPECIES_MASS_STATE' not in text:
    if 'var vcvChannelValues' in text: text=insert_after(text,'var vcvChannelValues',props)
    elif 'var vcvRawChannelValues' in text: text=insert_after(text,'var vcvRawChannelValues',props)
    else: raise SystemExit('SWIFT PATCH FAILED: no vcvChannelValues anchor')
pos=text.find('func loadVCVStateIfNeeded()')
if pos<0: raise SystemExit('SWIFT PATCH FAILED: loadVCVStateIfNeeded not found')
block='''\n        // RMU_V1_5B_SPECIES_MASS_AND_SCENE_PARSE\n        if let speciesAny = json["particle_species_mass"] as? [Any] {\n            var loaded: [Float] = []\n            for item in speciesAny {\n                if let n = item as? NSNumber { loaded.append(n.floatValue) }\n                else if let d = item as? Double { loaded.append(Float(d)) }\n                else if let f = item as? Float { loaded.append(f) }\n            }\n            if !loaded.isEmpty {\n                for i in 0..<min(22, loaded.count) { particleSpeciesMass[i] = loaded[i] }\n                particleSpeciesMassVoiceCount = min(22, loaded.count)\n                let total = particleSpeciesMass.reduce(Float(0.0), +)\n                geospatialParticleMass = total / Float(max(1, particleSpeciesMass.count))\n            }\n        }\n        if let speciesRawAny = json["particle_species_mass_raw"] as? [Any] {\n            var loadedRaw: [Float] = []\n            for item in speciesRawAny {\n                if let n = item as? NSNumber { loadedRaw.append(n.floatValue) }\n                else if let d = item as? Double { loadedRaw.append(Float(d)) }\n                else if let f = item as? Float { loadedRaw.append(f) }\n            }\n            if !loadedRaw.isEmpty { for i in 0..<min(22, loadedRaw.count) { particleSpeciesMassRaw[i] = loadedRaw[i] } }\n        }\n        if let sceneNumber = json["scene_index"] as? NSNumber {\n            let scene = max(1, min(6, sceneNumber.intValue))\n            vcvSceneIndex = scene\n            if fieldLayerWeights.count > 0 { selectedFieldLayerIndex = max(0, min(fieldLayerWeights.count - 1, scene - 1)) }\n            switch scene {\n            case 1: behaviorEffectCode = 0\n            case 2: behaviorEffectCode = 3\n            case 3: behaviorEffectCode = 4\n            case 4: behaviorEffectCode = 5\n            case 5: behaviorEffectCode = 6\n            case 6: behaviorEffectCode = 7\n            default: break\n            }\n        }\n'''
if 'RMU_V1_5B_SPECIES_MASS_AND_SCENE_PARSE' not in text:
    anchors=['if let probabilityNumber =','let timestamp =','vcvLastUpdateUnix =']
    for a in anchors:
        idx=text.find(a,pos)
        if idx>=0:
            text=text[:idx]+block+'\n'+text[idx:]; break
    else: raise SystemExit('SWIFT PATCH FAILED: no loader insertion anchor')
# literal label repair only
for old,new in [('/ch/10 particle_mass','/ch/10 species_mass_bank_A'),('/ch/11 particle_turbulence','/ch/11 species_mass_bank_B'),('/ch/12 particle_cohesion','/ch/12 particle_turbulence'),('/ch/13 gravity_well_position','/ch/13 particle_cohesion'),('/ch/14 gravity_well_strength','/ch/14 gravity_well_position'),('/ch/15 adaptive_aux_15','/ch/15 gravity_well_strength')]:
    text=text.replace('"'+old+'"','"'+new+'"')
if text!=orig: MAIN.write_text(text); print('Swift main.swift patched for v1.5B species mass parse + scene index application.')
else: print('Swift already had v1.5B markers; no changes made.')
