#!/usr/bin/env python3
"""
RealMathUniverse v1.7H Swift Auto Hotkey Patcher

Attempts to add SHIFT+A auto/manual toggle into the Swift renderer.
The patch is idempotent and backs up main.swift before changing it.
"""

from __future__ import annotations

import argparse
import re
import shutil
from datetime import datetime
from pathlib import Path

MARKER_HELPER_BEGIN = "// RMU_V1_7H_AUTO_HOTKEY_HELPER_BEGIN"
MARKER_HELPER_END = "// RMU_V1_7H_AUTO_HOTKEY_HELPER_END"
MARKER_KEY_BEGIN = "// RMU_V1_7H_AUTO_HOTKEY_KEYDOWN_BEGIN"
MARKER_KEY_END = "// RMU_V1_7H_AUTO_HOTKEY_KEYDOWN_END"

HELPER = r'''

// RMU_V1_7H_AUTO_HOTKEY_HELPER_BEGIN
func rmuV17HToggleAutoAuthorityMode() {
    let envRoot = ProcessInfo.processInfo.environment["RMU_ROOT"]
    let rootPath = envRoot ?? "/Users/Joe/Documents/RealMathUniverse"
    let modeURL = URL(fileURLWithPath: rootPath).appendingPathComponent("output/manual_authority_mode.json")

    var mode: [String: Any] = [:]
    if let data = try? Data(contentsOf: modeURL),
       let parsed = (try? JSONSerialization.jsonObject(with: data, options: [])) as? [String: Any] {
        mode = parsed
    }

    let fieldsAuto = (mode["auto_fields_enabled"] as? Bool) ?? false
    let behaviorAuto = (mode["auto_behavior_enabled"] as? Bool) ?? false
    let next = !(fieldsAuto || behaviorAuto)

    mode["schema"] = "rmu.manual_authority_mode.v1"
    mode["version"] = "1.7H-auto-hotkey-toggle"
    mode["auto_fields_enabled"] = next
    mode["auto_behavior_enabled"] = next
    mode["auto_camera_enabled"] = false

    if mode["manual_scene_index"] == nil { mode["manual_scene_index"] = 0 }
    if mode["manual_behavior_code"] == nil { mode["manual_behavior_code"] = 0 }
    if mode["manual_field_weights"] == nil {
        mode["manual_field_weights"] = [
            "radial": 1.0,
            "orbital": 1.0,
            "vertical": 1.0,
            "turbulence": 1.0,
            "shell": 1.0
        ]
    }

    let iso = ISO8601DateFormatter().string(from: Date())
    mode["last_toggle_utc"] = iso
    mode["last_toggle_source"] = "Swift SHIFT+A v1.7H"

    do {
        let output = try JSONSerialization.data(withJSONObject: mode, options: [.prettyPrinted, .sortedKeys])
        try FileManager.default.createDirectory(at: modeURL.deletingLastPathComponent(), withIntermediateDirectories: true)
        try output.write(to: modeURL, options: [.atomic])
        if next {
            print("RMU v1.7H AUTO MODE: ON | fields=auto behavior=auto camera=manual")
        } else {
            print("RMU v1.7H AUTO MODE: OFF | fields=manual behavior=manual camera=manual")
        }
    } catch {
        print("RMU v1.7H AUTO HOTKEY ERROR: \(error)")
    }
}
// RMU_V1_7H_AUTO_HOTKEY_HELPER_END
'''


def patch_main_swift(path: Path) -> bool:
    text = path.read_text(encoding="utf-8")
    original = text

    if "import Foundation" not in text:
        imports = list(re.finditer(r"^import\s+\w+\s*$", text, flags=re.MULTILINE))
        if imports:
            last = imports[-1]
            text = text[:last.end()] + "\nimport Foundation" + text[last.end():]
        else:
            text = "import Foundation\n" + text

    if MARKER_HELPER_BEGIN not in text:
        # Insert helper after imports.
        imports = list(re.finditer(r"^import\s+\w+\s*$", text, flags=re.MULTILINE))
        if imports:
            last = imports[-1]
            text = text[:last.end()] + HELPER + text[last.end():]
        else:
            text = HELPER + "\n" + text

    # Patch every keyDown(with event: NSEvent)-style method.
    pattern = re.compile(r"(override\s+func\s+keyDown\s*\(\s*with\s+([A-Za-z_][A-Za-z0-9_]*)\s*:\s*NSEvent\s*\)\s*\{)")

    def repl(match: re.Match[str]) -> str:
        full = match.group(1)
        event_name = match.group(2)
        # Avoid inserting twice immediately after this method opening.
        following = text[match.end():match.end()+800]
        if MARKER_KEY_BEGIN in following:
            return full
        insert = f'''
        {MARKER_KEY_BEGIN}
        let rmuV17HKey = {event_name}.charactersIgnoringModifiers?.lowercased() ?? ""
        if rmuV17HKey == "a" && {event_name}.modifierFlags.contains(.shift) {{
            rmuV17HToggleAutoAuthorityMode()
            return
        }}
        {MARKER_KEY_END}
'''
        return full + insert

    text2, count = pattern.subn(repl, text)
    text = text2

    if count == 0:
        print("WARNING: No Swift keyDown(with event: NSEvent) method found. Terminal toggle scripts still work.")

    if text == original:
        print("main.swift already patched or no changes needed.")
        return False

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup = path.with_suffix(path.suffix + f".v1_7H_auto_hotkey.{stamp}.bak")
    shutil.copy2(path, backup)
    path.write_text(text, encoding="utf-8")
    print(f"Patched {path}")
    print(f"Backup: {backup}")
    print(f"keyDown methods seen: {count}")
    return True


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("project_root")
    args = parser.parse_args()
    root = Path(args.project_root).expanduser().resolve()
    main_swift = root / "metal_renderer" / "Sources" / "RealMathUniverseMetalRenderer" / "main.swift"
    if not main_swift.exists():
        print(f"ERROR: main.swift not found: {main_swift}")
        return 1
    patch_main_swift(main_swift)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
