from __future__ import annotations

import shutil
import subprocess
import time
from pathlib import Path


ROOT = Path("/Users/Joe/Documents/RealMathUniverse")
MAIN = ROOT / "metal_renderer/Sources/RealMathUniverseMetalRenderer/main.swift"

MARKER = "RMU_PATCH_A_V1_11F_GATEWAY_SHIFT_FIRST"


def find_matching_brace(text: str, open_index: int) -> int:
    depth = 0
    in_string = False
    escape = False

    for i in range(open_index, len(text)):
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


def main() -> int:
    if not MAIN.exists():
        print(f"ERROR: missing {MAIN}")
        return 1

    s = MAIN.read_text()

    if MARKER in s:
        print("PATCH_A_ALREADY_PRESENT")
        return 0

    backup = MAIN.with_name(
        f"main.swift.PATCH_A_v1_11F_gateway_shift_first.{time.strftime('%Y%m%d_%H%M%S')}.bak"
    )
    shutil.copy2(MAIN, backup)
    print("Backup:", backup)

    needle = "    func rmuV18AHandleKey(_ event: NSEvent) -> Bool {"
    start = s.find(needle)

    if start < 0:
        print("ERROR: could not locate rmuV18AHandleKey")
        return 1

    open_brace = s.find("{", start)
    close_brace = find_matching_brace(s, open_brace)

    if close_brace < 0:
        print("ERROR: could not locate closing brace for rmuV18AHandleKey")
        return 1

    replacement = f'''    func rmuV18AHandleKey(_ event: NSEvent) -> Bool {{
        // {MARKER}
        // This handler is called before the older documented handleKey switch.
        // Therefore all SHIFT authority commands must be evaluated before plain camera keys.
        // Otherwise SHIFT+E becomes plain E zoom, SHIFT+A becomes rotate, etc.

        let shift = event.modifierFlags.contains(.shift)
        let control = event.modifierFlags.contains(.control)
        let chars = event.charactersIgnoringModifiers?.lowercased() ?? ""
        let panStep: Float = 0.035
        let rotStep: Float = 4.0 * .pi / 180.0

        // ESC: emergency manual/safe state.
        if event.keyCode == 53 {{
            rmuV18AEmergencyManual()
            return true
        }}

        // SPACE: run/pause only.
        if event.keyCode == 49 {{
            toggleSimulationPause()
            return true
        }}

        // ============================================================
        // SHIFT AUTHORITY COMMANDS FIRST
        // ============================================================

        if shift && chars.count == 1, let n = Int(chars), n >= 0 && n <= 7 {{
            rmuV18ASetBehavior(n)
            return true
        }}

        // SHIFT+E = behavior bypass/no-behavior toggle.
        if shift && chars == "e" {{
            rmuV18AToggleNoBehavior()
            return true
        }}

        // SHIFT+A = behavior/field auto authority toggle.
        if shift && chars == "a" {{
            rmuV18AToggleAuto()
            return true
        }}

        // SHIFT+B = dataset coupling apply/observe.
        if shift && chars == "b" {{
            rmuV18AToggleDatasetCouplingApply()
            return true
        }}

        // SHIFT+M = full manual.
        if shift && chars == "m" {{
            rmuV18AFullManual()
            return true
        }}

        // SHIFT+J = behavior queue.
        if shift && chars == "j" {{
            rmuV18AToggleBehaviorQueue()
            return true
        }}

        // SHIFT+F = field queue.
        if shift && chars == "f" {{
            rmuV18AToggleFieldQueue()
            return true
        }}

        // SHIFT+V = selected field layer.
        if shift && chars == "v" {{
            rmuV18ACycleSelectedFieldLayer()
            return true
        }}

        // SHIFT+D = dataset mode cycle.
        if shift && chars == "d" {{
            rmuV18AToggleDatasetMode()
            return true
        }}

        // SHIFT+. / SHIFT+, = active queue step.
        if shift && chars == "." {{
            rmuV18AQueueStep(
                domain: rmuV18AReadOperatorState()["active_auto_domain"] as? String ?? "behavior",
                delta: 1
            )
            return true
        }}

        if shift && chars == "," {{
            rmuV18AQueueStep(
                domain: rmuV18AReadOperatorState()["active_auto_domain"] as? String ?? "behavior",
                delta: -1
            )
            return true
        }}

        // CTRL field weight controls.
        if control && chars == "-" {{
            rmuV18AAdjustFieldWeight(delta: -0.05)
            return true
        }}

        if control && chars == "=" {{
            rmuV18AAdjustFieldWeight(delta: 0.05)
            return true
        }}

        // CTRL camera presets.
        if control && ["1", "2", "3", "4"].contains(chars) {{
            switch chars {{
            case "1":
                loadCameraPreset("gallery_orbit")
            case "2":
                loadCameraPreset("macro_disk")
            case "3":
                loadCameraPreset("wide_system")
            case "4":
                loadCameraPreset("default_camera")
            default:
                break
            }}
            return true
        }}

        // ============================================================
        // CAMERA / VIEW COMMANDS
        // ============================================================

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

        if chars == "w" || chars == "e" || chars == "]" {{
            renderer?.zoomIn()
            return true
        }}

        if chars == "z" || chars == "q" || chars == "[" {{
            renderer?.zoomOut()
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

        if chars == "x" {{
            renderer?.resetCamera()
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

        // Let the older documented handler process screenshots, HUD toggles, capture, etc.
        return false
    }}'''

    patched = s[:start] + replacement + s[close_brace + 1:]
    MAIN.write_text(patched)

    result = subprocess.run(
        ["swift", "build", "-c", "release"],
        cwd=str(ROOT / "metal_renderer"),
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )

    print(result.stdout)

    if result.returncode != 0:
        print("PATCH_A_FAIL: restoring backup")
        shutil.copy2(backup, MAIN)
        print("Restored:", backup)
        return result.returncode

    print("PATCH_A_PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
