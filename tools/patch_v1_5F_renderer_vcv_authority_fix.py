#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import re
import shutil
import subprocess
import time

ROOT = Path("/Users/Joe/Documents/RealMathUniverse")
MAIN = ROOT / "metal_renderer/Sources/RealMathUniverseMetalRenderer/main.swift"
VERSION = "v1.5F_renderer_vcv_authority_fix"

if not MAIN.exists():
    raise SystemExit(f"PATCH FAILED: missing {MAIN}")

stamp = time.strftime("%Y%m%d_%H%M%S")
backup_dir = ROOT / "backups" / VERSION
backup_dir.mkdir(parents=True, exist_ok=True)
backup = backup_dir / f"main.swift.{stamp}.bak"
shutil.copy2(MAIN, backup)

text = MAIN.read_text()
original = text

def replace_all(src: str, old: str, new: str, label: str) -> tuple[str, int]:
    count = src.count(old)
    if count == 0:
        print(f"WARNING: anchor not found: {label}")
        return src, 0
    return src.replace(old, new), count

def replace_once(src: str, old: str, new: str, label: str) -> tuple[str, int]:
    if old not in src:
        print(f"WARNING: anchor not found: {label}")
        return src, 0
    return src.replace(old, new, 1), 1

# 1. Safe mode is not allowed to be the v1.5D authority gate.
text, n = replace_once(
    text,
    "    var vcvSafeModeEnabled = true",
    "    // RMU_V1_5F_RENDERER_VCV_AUTHORITY_FIX\n    var vcvSafeModeEnabled = false",
    "safe mode default false",
)
print("safe default replacements:", n)

old_restore = '            vcvSafeModeEnabled = (vcv["vcv_safe_mode_enabled"] as? Bool) ?? vcvSafeModeEnabled'
new_restore = '            // RMU_V1_5F_SAFE_MODE_RUNTIME_OVERRIDE\n            // v1.5D+ bridge output is already mapped/clamped. Do not resurrect old SAFE=true runtime state.\n            vcvSafeModeEnabled = false'
text, n = replace_once(text, old_restore, new_restore, "safe mode restore override")
print("safe restore replacements:", n)

text, n = replace_all(
    text,
    '"vcv_safe_mode_enabled": vcvSafeModeEnabled',
    '"vcv_safe_mode_enabled": false',
    "safe mode saved false",
)
print("safe save replacements:", n)

old_toggle = '        vcvSafeModeEnabled.toggle()\n        print("VCV safe mode: \\\\(vcvSafeModeEnabled ? \\"ON\\" : \\"OFF\\")")'
new_toggle = '        // RMU_V1_5F_SAFE_MODE_TOGGLE_DISABLED\n        vcvSafeModeEnabled = false\n        print("VCV safe mode disabled for v1.5D split-bank authority")'
text, n = replace_once(text, old_toggle, new_toggle, "safe mode toggle disabled")
print("safe toggle replacements:", n)

# 2. Gravity authority fix.
old_gravity_pos = '        if vcvChannelValues.count >= 13 {\n            gravityWellPositionValue = max(-1.0, min(vcvChannelValues[12], 1.0))\n        }'
new_gravity_pos = '        // RMU_V1_5F_GRAVITY_VEC4_AUTHORITY\n        if gravityWellPositionVec4.count >= 1 {\n            gravityWellPositionValue = max(-1.0, min(gravityWellPositionVec4[0], 1.0))\n        } else if vcvChannelValues.count >= 14 {\n            gravityWellPositionValue = max(-1.0, min(vcvChannelValues[13], 1.0))\n        }'
text, n = replace_once(text, old_gravity_pos, new_gravity_pos, "gravity position vec4 authority")
print("gravity position replacements:", n)

old_gravity_strength = '        if vcvChannelValues.count >= 14 {\n            gravityWellStrengthValue = max(0.0, min(vcvChannelValues[13], 12.0))\n        }'
new_gravity_strength = '        // RMU_V1_5F_GRAVITY_STRENGTH_CH15_AUTHORITY\n        if vcvChannelValues.count >= 15 {\n            gravityWellStrengthValue = max(0.0, min(vcvChannelValues[14], 12.0))\n        }'
text, n = replace_once(text, old_gravity_strength, new_gravity_strength, "gravity strength /ch15 authority")
print("gravity strength replacements:", n)

# 3. Compact color display helper.
helper_marker = "RMU_V1_5F_COLOR_MODE_DISPLAY_HELPER"
if helper_marker not in text:
    anchor = "    func rmuVCVCompactStatusLine() -> String {"
    idx = text.find(anchor)
    if idx >= 0:
        helper = '''
    // RMU_V1_5F_COLOR_MODE_DISPLAY_HELPER
    func rmuVCVColorModeDisplayName() -> String {
        let mode = vcvChannelValues.count > 6 ? Int(vcvChannelValues[6]) : 0
        switch mode {
        case 0: return "classic"
        case 1: return "thermal"
        case 2: return "field"
        case 3: return "species"
        case 4: return "hsl"
        default: return "mode \\(mode)"
        }
    }

'''
        text = text[:idx] + helper + text[idx:]
        print("inserted VCV color display helper")
    else:
        print("WARNING: rmuVCVCompactStatusLine anchor not found; color helper not inserted")

text, n = replace_once(
    text,
    'return "\\(vcvDisplayStatus()) | v1.5D | scene \\(vcvSceneIndex) | color \\(colorModeName) | \\(rmuBankStatusLine()) | \\(rmuGravityVec4Summary())"',
    'return "\\(vcvDisplayStatus()) | v1.5D | scene \\(vcvSceneIndex) | color \\(rmuVCVColorModeDisplayName()) | \\(rmuBankStatusLine()) | \\(rmuGravityVec4Summary())"',
    "compact color display from VCV mode",
)
print("compact color replacements:", n)

# Optional mutable colorModeName binding.
if "RMU_V1_5F_COLOR_MODE_NAME_BINDING" not in text:
    color_anchor = "            vcvChannelValues[6] = Float(c)"
    idx = text.find(color_anchor)
    if idx >= 0 and re.search(r"\\bvar\\s+colorModeName\\b", text):
        line_end = text.find("\\n", idx)
        insertion = "\\n            // RMU_V1_5F_COLOR_MODE_NAME_BINDING\\n            colorModeName = rmuVCVColorModeDisplayName()"
        text = text[:line_end] + insertion + text[line_end:]
        print("inserted colorModeName binding")
    else:
        print("colorModeName binding skipped; mutable var not detected or anchor missing")

if text == original:
    print("No changes made.")
else:
    MAIN.write_text(text)

print(f"Backup: {backup}")
print("Patch markers:")
patched = MAIN.read_text(errors="replace")
for marker in [
    "RMU_V1_5F_RENDERER_VCV_AUTHORITY_FIX",
    "RMU_V1_5F_SAFE_MODE_RUNTIME_OVERRIDE",
    "RMU_V1_5F_GRAVITY_VEC4_AUTHORITY",
    "RMU_V1_5F_GRAVITY_STRENGTH_CH15_AUTHORITY",
]:
    print(f"  {marker}: {marker in patched}")

print()
print("Building renderer...")
try:
    subprocess.run(["swift", "build", "-c", "release"], cwd=str(ROOT / "metal_renderer"), check=True)
except subprocess.CalledProcessError:
    print()
    print("Swift build failed. Restore with:")
    print(f"  cp {backup} {MAIN}")
    raise

print()
print("v1.5F renderer VCV authority fix complete.")
