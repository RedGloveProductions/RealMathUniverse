#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import re
import shutil
import subprocess
import time

ROOT = Path("/Users/Joe/Documents/RealMathUniverse")
MAIN = ROOT / "metal_renderer/Sources/RealMathUniverseMetalRenderer/main.swift"
VERSION = "v1.5G_renderer_scene_color_field_authority"

if not MAIN.exists():
    raise SystemExit(f"PATCH FAILED: missing {MAIN}")

stamp = time.strftime("%Y%m%d_%H%M%S")
backup_dir = ROOT / "backups" / VERSION
backup_dir.mkdir(parents=True, exist_ok=True)
backup = backup_dir / f"main.swift.{stamp}.bak"
shutil.copy2(MAIN, backup)

text = MAIN.read_text()
original = text


def insert_after_once(src: str, anchor: str, insertion: str, marker: str) -> tuple[str, bool]:
    if marker in src:
        return src, False
    idx = src.find(anchor)
    if idx < 0:
        print(f"WARNING: anchor not found: {anchor}")
        return src, False
    end = src.find("\n", idx)
    if end < 0:
        end = len(src)
    return src[:end+1] + insertion + src[end+1:], True


def replace_once(src: str, old: str, new: str, label: str) -> tuple[str, int]:
    if old not in src:
        print(f"WARNING: anchor not found: {label}")
        return src, 0
    return src.replace(old, new, 1), 1


def replace_regex_once(src: str, pattern: str, repl: str, label: str) -> tuple[str, int]:
    out, n = re.subn(pattern, repl, src, count=1, flags=re.DOTALL)
    if n == 0:
        print(f"WARNING: regex anchor not found: {label}")
    return out, n

# 1. Add explicit authority state.
state_block = """
    // RMU_V1_5G_RENDERER_SCENE_COLOR_FIELD_AUTHORITY_STATE
    var vcvAuthoritySceneIndex: Int = 1
    var vcvAuthorityColorMode: Int32 = 0
    var vcvAuthorityFieldLayerIndex: Int = 0
    var vcvAuthorityLastAppliedUnix: Double = 0.0
"""
text, ok = insert_after_once(text, "    var vcvSafeModeEnabled = false", state_block, "RMU_V1_5G_RENDERER_SCENE_COLOR_FIELD_AUTHORITY_STATE")
if not ok:
    text, ok = insert_after_once(text, "    var vcvSafeModeEnabled = true", state_block, "RMU_V1_5G_RENDERER_SCENE_COLOR_FIELD_AUTHORITY_STATE")
print("authority state inserted:", ok)

# 2. Add helpers. Anchor after v1.5F color helper if available, otherwise after v1.5E bank helper.
helper_block = """
    // RMU_V1_5G_RENDERER_SCENE_COLOR_FIELD_AUTHORITY_HELPERS
    func rmuApplyVCVSceneAuthority(_ scene: Int) {
        let clampedScene = max(1, min(6, scene))
        vcvAuthoritySceneIndex = clampedScene
        vcvSceneIndex = clampedScene

        let layerIndex = max(0, min(max(0, fieldLayerWeights.count - 1), clampedScene - 1))
        vcvAuthorityFieldLayerIndex = layerIndex

        if fieldLayerWeights.count > 0 {
            selectedFieldLayerIndex = layerIndex
        }

        switch clampedScene {
        case 1:
            behaviorEffectCode = 0
        case 2:
            behaviorEffectCode = 3
        case 3:
            behaviorEffectCode = 4
        case 4:
            behaviorEffectCode = 5
        case 5:
            behaviorEffectCode = 6
        case 6:
            behaviorEffectCode = 7
        default:
            behaviorEffectCode = 0
        }
    }

    func rmuApplyVCVColorAuthority(_ mode: Int32) {
        let clampedMode = max(Int32(0), min(Int32(4), mode))
        vcvAuthorityColorMode = clampedMode

        if vcvChannelValues.count > 6 {
            vcvChannelValues[6] = Float(clampedMode)
        }
        if vcvRawChannelValues.count > 6 {
            vcvRawChannelValues[6] = Float(clampedMode)
        }

        switch clampedMode {
        case 0:
            colorModeName = "classic"
        case 1:
            colorModeName = "thermal"
        case 2:
            colorModeName = "field"
        case 3:
            colorModeName = "species"
        case 4:
            colorModeName = "hsl"
        default:
            colorModeName = "classic"
        }
    }

    func rmuApplyVCVFieldLayerWeights(_ weights: [Float]) {
        if weights.isEmpty { return }
        let count = min(weights.count, fieldLayerWeights.count)
        if count <= 0 { return }
        for i in 0..<count {
            fieldLayerWeights[i] = weights[i]
        }
        selectedFieldLayerIndex = max(0, min(max(0, fieldLayerWeights.count - 1), vcvAuthorityFieldLayerIndex))
    }
"""
text, ok = insert_after_once(text, "    func rmuVCVColorModeDisplayName() -> String {", helper_block, "RMU_V1_5G_RENDERER_SCENE_COLOR_FIELD_AUTHORITY_HELPERS")
if not ok:
    text, ok = insert_after_once(text, "    func rmuBankStatus(_ a: Int, _ b: Int) -> String {", helper_block, "RMU_V1_5G_RENDERER_SCENE_COLOR_FIELD_AUTHORITY_HELPERS")
print("authority helpers inserted:", ok)

# 3. Replace old scene parser block from v1.5C/v1.5E.
scene_pattern = r'''        if let sceneNumber = json\["scene_index"\] as\? NSNumber \{
            let scene = max\(1, min\(6, sceneNumber\.intValue\)\)
            vcvSceneIndex = scene
            if fieldLayerWeights\.count > 0 \{
                selectedFieldLayerIndex = max\(0, min\(fieldLayerWeights\.count - 1, scene - 1\)\)
            \}
            switch scene \{
            case 1: behaviorEffectCode = 0
            case 2: behaviorEffectCode = 3
            case 3: behaviorEffectCode = 4
            case 4: behaviorEffectCode = 5
            case 5: behaviorEffectCode = 6
            case 6: behaviorEffectCode = 7
            default: break
            \}
        \}'''
scene_repl = '''        // RMU_V1_5G_SCENE_FIELD_AUTHORITY_PARSE
        if let sceneNumber = json["scene_index"] as? NSNumber {
            rmuApplyVCVSceneAuthority(sceneNumber.intValue)
        }'''
text, n = replace_regex_once(text, scene_pattern, scene_repl, "v1.5C scene parser block")
print("scene parser replacements:", n)

# 4. Insert color authority parse.
color_insert = '''
        // RMU_V1_5G_COLOR_AUTHORITY_PARSE
        if let colorNumber = json["color_mode"] as? NSNumber {
            rmuApplyVCVColorAuthority(colorNumber.int32Value)
        } else if particleSpeciesColorMode.count > 0 {
            rmuApplyVCVColorAuthority(particleSpeciesColorMode[0])
        }
'''
if "RMU_V1_5G_COLOR_AUTHORITY_PARSE" not in text:
    anchor = '        let speedBank = rmuFloatArray("particle_species_speed", 22)'
    idx = text.find(anchor)
    if idx >= 0:
        text = text[:idx] + color_insert + text[idx:]
        print("color authority parse inserted before speedBank")
    else:
        anchor2 = '        // RMU_V1_5G_SCENE_FIELD_AUTHORITY_PARSE'
        idx = text.find(anchor2)
        if idx >= 0:
            text = text[:idx] + color_insert + text[idx:]
            print("color authority parse inserted before scene parse")
        else:
            print("WARNING: no insertion point found for color authority parse")

# 5. Field weights parse.
field_insert = '''
        // RMU_V1_5G_FIELD_LAYER_WEIGHTS_PARSE
        let vcvFieldWeights = rmuFloatArray("field_layer_weights", 8)
        if !vcvFieldWeights.isEmpty {
            rmuApplyVCVFieldLayerWeights(vcvFieldWeights)
        }
'''
if "RMU_V1_5G_FIELD_LAYER_WEIGHTS_PARSE" not in text:
    anchor = '        // RMU_V1_5G_COLOR_AUTHORITY_PARSE'
    idx = text.find(anchor)
    if idx >= 0:
        text = text[:idx] + field_insert + text[idx:]
        print("field layer weights parse inserted")
    else:
        print("WARNING: no insertion point found for field layer weights parse")

# 6. Make compact color helper use authority mode, if v1.5F helper exists.
old_color_helper_line = '        let mode = vcvChannelValues.count > 6 ? Int(vcvChannelValues[6]) : 0'
new_color_helper_line = '        let mode = Int(vcvAuthorityColorMode)'
text, n = replace_once(text, old_color_helper_line, new_color_helper_line, "color helper uses authority mode")
print("color helper authority replacements:", n)

# 7. Runtime save/restore authority fields.
runtime_anchor = '"vcv_detail_page_index": vcvDetailPageIndex'
runtime_extra = ',\n                "vcv_authority_scene_index": vcvAuthoritySceneIndex,\n                "vcv_authority_color_mode": vcvAuthorityColorMode,\n                "vcv_authority_field_layer_index": vcvAuthorityFieldLayerIndex'
if '"vcv_authority_scene_index"' not in text and runtime_anchor in text:
    text = text.replace(runtime_anchor, runtime_anchor + runtime_extra, 1)
    print("runtime authority save fields inserted")

restore_anchor = '            vcvDetailPageIndex = (vcv["vcv_detail_page_index"] as? Int) ?? vcvDetailPageIndex'
restore_extra = '\n            vcvAuthoritySceneIndex = (vcv["vcv_authority_scene_index"] as? Int) ?? vcvAuthoritySceneIndex\n            if let restoredColor = vcv["vcv_authority_color_mode"] as? NSNumber { vcvAuthorityColorMode = restoredColor.int32Value }\n            vcvAuthorityFieldLayerIndex = (vcv["vcv_authority_field_layer_index"] as? Int) ?? vcvAuthorityFieldLayerIndex'
if 'vcvAuthoritySceneIndex = (vcv[' not in text and restore_anchor in text:
    text = text.replace(restore_anchor, restore_anchor + restore_extra, 1)
    print("runtime authority restore fields inserted")

if text == original:
    print("No changes made.")
else:
    MAIN.write_text(text)

print(f"Backup: {backup}")
print("Patch markers:")
patched = MAIN.read_text(errors="replace")
for marker in [
    "RMU_V1_5G_RENDERER_SCENE_COLOR_FIELD_AUTHORITY_STATE",
    "RMU_V1_5G_RENDERER_SCENE_COLOR_FIELD_AUTHORITY_HELPERS",
    "RMU_V1_5G_SCENE_FIELD_AUTHORITY_PARSE",
    "RMU_V1_5G_COLOR_AUTHORITY_PARSE",
    "RMU_V1_5G_FIELD_LAYER_WEIGHTS_PARSE",
]:
    print(f"  {marker}: {marker in patched}")

print("\nBuilding renderer...")
try:
    subprocess.run(["swift", "build", "-c", "release"], cwd=str(ROOT / "metal_renderer"), check=True)
except subprocess.CalledProcessError:
    print("\nSwift build failed. Restore with:")
    print(f"  cp {backup} {MAIN}")
    raise

print("\nv1.5G renderer scene/color/field authority patch complete.")
