#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import re
import shutil
import subprocess
import time

ROOT = Path("/Users/Joe/Documents/RealMathUniverse")
MAIN = ROOT / "metal_renderer/Sources/RealMathUniverseMetalRenderer/main.swift"
VERSION = "v1.5E_renderer_hud_vcv_panel_cleanup"

if not MAIN.exists():
    raise SystemExit(f"PATCH FAILED: missing {MAIN}")

stamp = time.strftime("%Y%m%d_%H%M%S")
backup_dir = ROOT / "backups" / VERSION
backup_dir.mkdir(parents=True, exist_ok=True)
backup = backup_dir / f"main.swift.{stamp}.bak"
shutil.copy2(MAIN, backup)

text = MAIN.read_text()
original = text

def insert_after_once(src: str, anchor: str, insertion: str, marker: str) -> str:
    if marker in src:
        return src
    idx = src.find(anchor)
    if idx < 0:
        raise SystemExit(f"PATCH FAILED: anchor not found: {anchor}")
    end = src.find("\n", idx)
    if end < 0:
        end = len(src)
    return src[:end+1] + insertion + src[end+1:]

def replace_once(src: str, old: str, new: str, label: str) -> str:
    if old not in src:
        print(f"WARNING: replacement anchor not found: {label}")
        return src
    return src.replace(old, new, 1)

def find_matching_brace(src: str, open_brace_idx: int) -> int:
    depth = 0
    in_string = False
    escape = False
    for i in range(open_brace_idx, len(src)):
        ch = src[i]
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
    raise SystemExit("PATCH FAILED: matching brace not found")

def replace_string_function(src: str, func_name: str, new_func: str) -> tuple[str, bool]:
    m = re.search(rf"\n\s*func\s+{re.escape(func_name)}\s*\([^)]*\)\s*->\s*String\s*\{{", src)
    if not m:
        return src, False
    open_idx = src.find("{", m.start())
    close_idx = find_matching_brace(src, open_idx)
    return src[:m.start()+1] + new_func.rstrip() + "\n" + src[close_idx+1:], True

state_block = """
    // RMU_V1_5E_RENDERER_HUD_VCV_PANEL_CLEANUP_STATE
    var vcvCompactHUDMode: Bool = true
    var vcvDetailPanelVisible: Bool = false
    var vcvDetailPageIndex: Int = 0

    var particleSpeciesProbabilityVoiceCountA: Int = 0
    var particleSpeciesProbabilityVoiceCountB: Int = 0
    var particleSpeciesColorModeVoiceCountA: Int = 0
    var particleSpeciesColorModeVoiceCountB: Int = 0
    var particleSpeciesSpeedVoiceCountA: Int = 0
    var particleSpeciesSpeedVoiceCountB: Int = 0
    var particleSpeciesMassVoiceCountA: Int = 0
    var particleSpeciesMassVoiceCountB: Int = 0
    var particleSpeciesTurbulenceVoiceCountA: Int = 0
    var particleSpeciesTurbulenceVoiceCountB: Int = 0
    var particleSpeciesCohesionVoiceCountA: Int = 0
    var particleSpeciesCohesionVoiceCountB: Int = 0
    var particleSpeciesColorVoiceCountA: Int = 0
    var particleSpeciesColorVoiceCountB: Int = 0
"""
text = insert_after_once(text, "    var vcvSafeModeEnabled = true", state_block, "RMU_V1_5E_RENDERER_HUD_VCV_PANEL_CLEANUP_STATE")

helper_block = """
    // RMU_V1_5E_RENDERER_HUD_VCV_PANEL_CLEANUP_HELPERS
    func rmuBankStatus(_ a: Int, _ b: Int) -> String {
        return "\\(a)+\\(b)"
    }

    func rmuBankStatusLine() -> String {
        return "P \\(rmuBankStatus(particleSpeciesProbabilityVoiceCountA, particleSpeciesProbabilityVoiceCountB))  " +
            "CMode \\(rmuBankStatus(particleSpeciesColorModeVoiceCountA, particleSpeciesColorModeVoiceCountB))  " +
            "S \\(rmuBankStatus(particleSpeciesSpeedVoiceCountA, particleSpeciesSpeedVoiceCountB))  " +
            "M \\(rmuBankStatus(particleSpeciesMassVoiceCountA, particleSpeciesMassVoiceCountB))  " +
            "T \\(rmuBankStatus(particleSpeciesTurbulenceVoiceCountA, particleSpeciesTurbulenceVoiceCountB))  " +
            "Coh \\(rmuBankStatus(particleSpeciesCohesionVoiceCountA, particleSpeciesCohesionVoiceCountB))  " +
            "Color \\(rmuBankStatus(particleSpeciesColorVoiceCountA, particleSpeciesColorVoiceCountB))"
    }

    func rmuGravityVec4Summary() -> String {
        let x = gravityWellPositionVec4.count > 0 ? gravityWellPositionVec4[0] : 0.0
        let y = gravityWellPositionVec4.count > 1 ? gravityWellPositionVec4[1] : 0.0
        let z = gravityWellPositionVec4.count > 2 ? gravityWellPositionVec4[2] : 0.0
        let t = gravityWellPositionVec4.count > 3 ? gravityWellPositionVec4[3] : 0.0
        return String(format: "G4 %.2f %.2f %.2f %.2f", x, y, z, t)
    }

    func rmuVCVCompactStatusLine() -> String {
        return "\\(vcvDisplayStatus()) | v1.5D | scene \\(vcvSceneIndex) | color \\(colorModeName) | \\(rmuBankStatusLine()) | \\(rmuGravityVec4Summary())"
    }

    func rmuVCVDetailPageTitle() -> String {
        switch max(0, min(4, vcvDetailPageIndex)) {
        case 0: return "VCV PAGE 1: /ch/1-/ch/9"
        case 1: return "VCV PAGE 2: /ch/10-/ch/17"
        case 2: return "VCV PAGE 3: /ch/28-/ch/32"
        case 3: return "VCV PAGE 4: Species P/S/M/T/C"
        case 4: return "VCV PAGE 5: Gravity + Field Layers"
        default: return "VCV PAGE"
        }
    }
"""
text = insert_after_once(text, "    weak var hud: HUDOverlayController?", helper_block, "RMU_V1_5E_RENDERER_HUD_VCV_PANEL_CLEANUP_HELPERS")

new_summary = """
    func vcvChannelCompactSummary() -> String {
        // RMU_V1_5E_COMPACT_CHANNEL_SUMMARY
        if vcvDetailPanelVisible {
            return "\\(rmuVCVCompactStatusLine()) | \\(rmuVCVDetailPageTitle())"
        }
        return rmuVCVCompactStatusLine()
    }
"""
text, did_summary = replace_string_function(text, "vcvChannelCompactSummary", new_summary)
print("vcvChannelCompactSummary replaced:", did_summary)

old_safe = '        appendKV(a, "safe mode", renderer.vcvSafeModeEnabled ? "ON" : "OFF", valueColor: statusColor(renderer.vcvSafeModeEnabled ? "ON" : "OFF"))'
new_safe = """        // RMU_V1_5E_HUD_COMPACT_VCV_BANK_STATUS
        appendKV(a, "VCV", renderer.vcvDisplayStatus(), valueColor: statusColor(renderer.vcvDisplayStatus()))
        appendKV(a, "bridge", "v1.5D split banks", valueColor: rmuCyan())
        appendKV(a, "banks", renderer.rmuBankStatusLine(), valueColor: rmuGreen())
        appendKV(a, "gravity", renderer.rmuGravityVec4Summary(), valueColor: rmuYellow())
        appendKV(a, "safe mode", renderer.vcvSafeModeEnabled ? "ON" : "OFF", valueColor: statusColor(renderer.vcvSafeModeEnabled ? "ON" : "OFF"))"""
text = replace_once(text, old_safe, new_safe, "HUD safe-mode block")

parse_pairs = [
    ('if let n = json["particle_species_probability_voice_count"] as? NSNumber { particleSpeciesProbabilityVoiceCount = n.intValue }',
     '        if let n = json["particle_species_probability_voice_count_A"] as? NSNumber { particleSpeciesProbabilityVoiceCountA = n.intValue }\n        if let n = json["particle_species_probability_voice_count_B"] as? NSNumber { particleSpeciesProbabilityVoiceCountB = n.intValue }'),
    ('if let n = json["particle_species_color_mode_voice_count"] as? NSNumber { particleSpeciesColorModeVoiceCount = n.intValue }',
     '        if let n = json["particle_species_color_mode_voice_count_A"] as? NSNumber { particleSpeciesColorModeVoiceCountA = n.intValue }\n        if let n = json["particle_species_color_mode_voice_count_B"] as? NSNumber { particleSpeciesColorModeVoiceCountB = n.intValue }'),
    ('if let n = json["particle_species_speed_voice_count"] as? NSNumber { particleSpeciesSpeedVoiceCount = n.intValue }',
     '        if let n = json["particle_species_speed_voice_count_A"] as? NSNumber { particleSpeciesSpeedVoiceCountA = n.intValue }\n        if let n = json["particle_species_speed_voice_count_B"] as? NSNumber { particleSpeciesSpeedVoiceCountB = n.intValue }'),
    ('if let n = json["particle_species_mass_voice_count"] as? NSNumber { particleSpeciesMassVoiceCount = n.intValue }',
     '        if let n = json["particle_species_mass_voice_count_A"] as? NSNumber { particleSpeciesMassVoiceCountA = n.intValue }\n        if let n = json["particle_species_mass_voice_count_B"] as? NSNumber { particleSpeciesMassVoiceCountB = n.intValue }'),
    ('if let n = json["particle_species_turbulence_voice_count"] as? NSNumber { particleSpeciesTurbulenceVoiceCount = n.intValue }',
     '        if let n = json["particle_species_turbulence_voice_count_A"] as? NSNumber { particleSpeciesTurbulenceVoiceCountA = n.intValue }\n        if let n = json["particle_species_turbulence_voice_count_B"] as? NSNumber { particleSpeciesTurbulenceVoiceCountB = n.intValue }'),
    ('if let n = json["particle_species_cohesion_voice_count"] as? NSNumber { particleSpeciesCohesionVoiceCount = n.intValue }',
     '        if let n = json["particle_species_cohesion_voice_count_A"] as? NSNumber { particleSpeciesCohesionVoiceCountA = n.intValue }\n        if let n = json["particle_species_cohesion_voice_count_B"] as? NSNumber { particleSpeciesCohesionVoiceCountB = n.intValue }'),
    ('if let n = json["particle_species_color_hsl_voice_count"] as? NSNumber { particleSpeciesColorVoiceCount = n.intValue }',
     '        if let n = json["particle_species_color_hsl_voice_count_A"] as? NSNumber { particleSpeciesColorVoiceCountA = n.intValue }\n        if let n = json["particle_species_color_hsl_voice_count_B"] as? NSNumber { particleSpeciesColorVoiceCountB = n.intValue }'),
]
for anchor, extra in parse_pairs:
    marker = extra.splitlines()[0].strip()
    if marker not in text:
        text = replace_once(text, anchor, anchor + "\n" + extra, marker)

runtime_anchor = '                "vcv_safe_mode_enabled": vcvSafeModeEnabled'
if '"vcv_compact_hud_mode"' not in text and runtime_anchor in text:
    text = text.replace(runtime_anchor, runtime_anchor + ',\n                "vcv_compact_hud_mode": vcvCompactHUDMode,\n                "vcv_detail_panel_visible": vcvDetailPanelVisible,\n                "vcv_detail_page_index": vcvDetailPageIndex', 1)

restore_anchor = '            vcvSafeModeEnabled = (vcv["vcv_safe_mode_enabled"] as? Bool) ?? vcvSafeModeEnabled'
if 'vcvCompactHUDMode = (vcv["vcv_compact_hud_mode"]' not in text and restore_anchor in text:
    text = text.replace(restore_anchor, restore_anchor + '\n            vcvCompactHUDMode = (vcv["vcv_compact_hud_mode"] as? Bool) ?? vcvCompactHUDMode\n            vcvDetailPanelVisible = (vcv["vcv_detail_panel_visible"] as? Bool) ?? vcvDetailPanelVisible\n            vcvDetailPageIndex = (vcv["vcv_detail_page_index"] as? Int) ?? vcvDetailPageIndex', 1)

if text == original:
    print("No changes made.")
else:
    MAIN.write_text(text)

print(f"Backup: {backup}")
print("Building renderer...")
try:
    subprocess.run(["swift", "build", "-c", "release"], cwd=str(ROOT / "metal_renderer"), check=True)
except subprocess.CalledProcessError:
    print(f"Swift build failed. Restore with:\ncp {backup} {MAIN}")
    raise

validator = ROOT / "tools" / "validate_v1_5D_split_banks.py"
if validator.exists():
    subprocess.run(["python3", str(validator)], cwd=str(ROOT), check=False)

print("v1.5E renderer/HUD VCV cleanup complete.")
