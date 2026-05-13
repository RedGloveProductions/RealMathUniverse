from __future__ import annotations

import shutil
import subprocess
import sys
import time
from pathlib import Path


ROOT = Path("/Users/Joe/Documents/RealMathUniverse")
MAIN = ROOT / "metal_renderer/Sources/RealMathUniverseMetalRenderer/main.swift"
MARKER = "RMU_V1_11F_REPLACE_RMUV18A_HANDLEKEY_GATEWAY"


def find_matching_brace(text: str, open_index: int) -> int:
    depth = 0
    in_string = False
    escaped = False

    for i in range(open_index, len(text)):
        ch = text[i]

        if in_string:
            if escaped:
                escaped = False
            elif ch == "\\":
                escaped = True
            elif ch == '"':
                in_string = False
            continue

        if ch == '"':
            in_string = True
        elif ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return i

    return -1


def main() -> int:
    if not MAIN.exists():
        print(f"ERROR: missing {MAIN}")
        return 1

    s = MAIN.read_text()

    if MARKER in s:
        print("v1.11F rmuV18AHandleKey gateway already installed.")
        return 0

    backup = MAIN.with_name(
        f"main.swift.v1_11F_replace_rmuV18AHandleKey_gateway.backup.{time.strftime('%Y%m%d_%H%M%S')}.bak"
    )
    shutil.copy2(MAIN, backup)
    print("Backup:", backup)

    needle = "    func rmuV18AHandleKey(_ event: NSEvent) -> Bool {"
    start = s.find(needle)
    if start == -1:
        print("ERROR: could not find rmuV18AHandleKey function")
        return 1

    open_brace = s.find("{", start)
    end_brace = find_matching_brace(s, open_brace)
    if end_brace == -1:
        print("ERROR: could not find matching brace for rmuV18AHandleKey")
        return 1

    replacement = f'''    func rmuV18AHandleKey(_ event: NSEvent) -> Bool {{
        // {MARKER}
        // Gateway rule:
        // - SPACE remains run/pause.
        // - Camera and point-size keys are handled here because this v1.8A layer runs first.
        // - Authority/control commands require SHIFT unless explicitly noted.
        // - Unrecognized keys return false so the older documented handleKey() can process screenshots,
        //   color hotkeys, HUD toggles, presentation mode, trails, etc.

        let shift = event.modifierFlags.contains(.shift)
        let control = event.modifierFlags.contains(.control)
        let chars = event.charactersIgnoringModifiers?.lowercased() ?? ""
        let panStep: Float = 0.035
        let rotStep: Float = 4.0 * .pi / 180.0

        // Escape remains emergency manual, not app quit.
        if event.keyCode == 53 {{
            rmuV18AEmergencyManual()
            return true
        }}

        // SPACE: run/pause only.
        if event.keyCode == 49 {{
            toggleSimulationPause()
            return true
        }}

        // Corrected arrow pan. This is intentionally the reverse of the old inverted mapping.
        switch event.keyCode {{
        case 123:
            renderer?.pan(dx: panStep, dy: 0)
            return true
        case 124:
            renderer?.pan(dx: -panStep, dy: 0)
            return true
        case 125:
            renderer?.pan(dx: 0, dy: panStep)
            return true
        case 126:
            renderer?.pan(dx: 0, dy: -panStep)
            return true
        default:
            break
        }}

        // Camera controls.
        if chars == "w" || chars == "e" || chars == "]" {{
            renderer?.zoomIn()
            return true
        }}

        if chars == "z" || chars == "q" || chars == "[" {{
            renderer?.zoomOut()
            return true
        }}

        if chars == "x" {{
            renderer?.resetCamera()
            return true
        }}

        if chars == "a" {{
            renderer?.rotate(delta: -rotStep)
            return true
        }}

        if chars == "d" {{
            renderer?.rotate(delta: rotStep)
            return true
        }}

        if chars == "+" || chars == "=" {{
            renderer?.increasePointSize()
            return true
        }}

        if chars == "-" || chars == "_" {{
            renderer?.decreasePointSize()
            return true
        }}

        // Camera presets stay on CTRL+1..4.
        if control && ["1", "2", "3", "4"].contains(chars) {{
            switch chars {{
            case "1": loadCameraPreset("gallery_orbit")
            case "2": loadCameraPreset("macro_disk")
            case "3": loadCameraPreset("wide_system")
            case "4": loadCameraPreset("default_camera")
            default: break
            }}
            return true
        }}

        // Operator/authority controls.
        if shift && chars.count == 1, let n = Int(chars), n >= 0 && n <= 7 {{
            rmuV18ASetBehavior(n)
            return true
        }}

        if shift && chars == "a" {{
            rmuV18AToggleAuto()
            return true
        }}

        if shift && chars == "b" {{
            rmuV18AToggleDatasetCouplingApply()
            return true
        }}

        if shift && chars == "n" {{
            rmuV18AToggleNoBehavior()
            return true
        }}

        if shift && chars == "m" {{
            rmuV18AFullManual()
            return true
        }}

        if shift && chars == "j" {{
            rmuV18AToggleBehaviorQueue()
            return true
        }}

        if shift && chars == "f" {{
            rmuV18AToggleFieldQueue()
            return true
        }}

        if shift && chars == "v" {{
            rmuV18ACycleSelectedFieldLayer()
            return true
        }}

        if shift && chars == "." {{
            rmuV18AQueueStep(domain: rmuV18AReadOperatorState()["active_auto_domain"] as? String ?? "behavior", delta: 1)
            return true
        }}

        if shift && chars == "," {{
            rmuV18AQueueStep(domain: rmuV18AReadOperatorState()["active_auto_domain"] as? String ?? "behavior", delta: -1)
            return true
        }}

        if shift && chars == "d" {{
            rmuV18AToggleDatasetMode()
            return true
        }}

        if control && chars == "-" {{
            rmuV18AAdjustFieldWeight(delta: -0.05)
            return true
        }}

        if control && chars == "=" {{
            rmuV18AAdjustFieldWeight(delta: 0.05)
            return true
        }}

        // Let the older documented handler process all remaining non-authority keys.
        return false
    }}'''

    patched = s[:start] + replacement + s[end_brace + 1:]
    MAIN.write_text(patched)

    print("Replaced rmuV18AHandleKey gateway only.")
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

    print("v1.11F rmuV18AHandleKey gateway patch passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
