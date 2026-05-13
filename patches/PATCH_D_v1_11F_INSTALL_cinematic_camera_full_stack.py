from __future__ import annotations

import re
import shutil
import subprocess
import time
from pathlib import Path


ROOT = Path("/Users/Joe/Documents/RealMathUniverse")
MAIN = ROOT / "metal_renderer/Sources/RealMathUniverseMetalRenderer/main.swift"
MARKER = "RMU_PATCH_D_V1_11F_CINEMATIC_CAMERA_FULL_STACK"


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


def insert_after_function(text: str, func_name: str, insert: str) -> tuple[str, bool]:
    idx = text.find(func_name)
    if idx < 0:
        return text, False

    open_brace = text.find("{", idx)
    if open_brace < 0:
        return text, False

    close_brace = find_matching_brace(text, open_brace)
    if close_brace < 0:
        return text, False

    return text[:close_brace + 1] + "\n\n" + insert + text[close_brace + 1:], True


def insert_inside_rmuV18_gateway_after_shift_d(text: str, insert: str) -> tuple[str, bool]:
    gateway = "    func rmuV18AHandleKey(_ event: NSEvent) -> Bool {"
    start = text.find(gateway)
    if start < 0:
        return text, False

    open_brace = text.find("{", start)
    close_brace = find_matching_brace(text, open_brace)
    if close_brace < 0:
        return text, False

    body = text[start:close_brace + 1]

    # Preferred anchor: after SHIFT+D dataset mode block.
    anchor = '''        if shift && chars == "d" {
            rmuV18AToggleDatasetMode()
            return true
        }
'''
    if anchor in body:
        new_body = body.replace(anchor, anchor + "\n" + insert + "\n", 1)
        return text[:start] + new_body + text[close_brace + 1:], True

    # Fallback: insert immediately before camera/view section or before arrow switch.
    for fallback in [
        "        // ============================================================\n        // CAMERA / VIEW COMMANDS",
        "        // Corrected camera pan.",
        "        switch event.keyCode {",
    ]:
        pos = body.find(fallback)
        if pos >= 0:
            new_body = body[:pos] + insert + "\n\n" + body[pos:]
            return text[:start] + new_body + text[close_brace + 1:], True

    return text, False


def main() -> int:
    if not MAIN.exists():
        print(f"ERROR: missing {MAIN}")
        return 1

    s = MAIN.read_text()

    if MARKER in s:
        print("PATCH_D_ALREADY_PRESENT")
        return 0

    backup = MAIN.with_name(
        f"main.swift.PATCH_D_v1_11F_install_cinematic_camera_full_stack.{time.strftime('%Y%m%d_%H%M%S')}.bak"
    )
    shutil.copy2(MAIN, backup)
    print("Backup:", backup)

    changes: list[str] = []

    # ------------------------------------------------------------------
    # D1. State variables. Insert after behaviorEffectCode, which audit confirms exists.
    # ------------------------------------------------------------------
    state_anchor = "    var behaviorEffectCode: Int32 = 1"
    state_insert = f'''    var behaviorEffectCode: Int32 = 1

    // {MARKER}_STATE_BEGIN
    var cinematicCameraEnabled: Bool = false
    var cinematicCameraStartUnix: Double = Date().timeIntervalSince1970
    var cinematicCameraBaseRadius: Float = 0.0
    var cinematicCameraBaseRotationRadians: Float = 0.0
    var cinematicCameraBasePanX: Float = 0.0
    var cinematicCameraBasePanY: Float = 0.0

    // deliberately visible values for large v1.11 world scale
    var cinematicCameraOrbitSpeed: Float = 0.24
    var cinematicCameraZoomAmplitude: Float = 0.28
    var cinematicCameraPanAmplitudeX: Float = 0.12
    var cinematicCameraPanAmplitudeY: Float = 0.07
    // {MARKER}_STATE_END'''

    if state_anchor not in s:
        print("ERROR: could not find behaviorEffectCode anchor for cinematic state")
        shutil.copy2(backup, MAIN)
        return 1

    s = s.replace(state_anchor, state_insert, 1)
    changes.append("installed cinematic camera renderer state")

    # ------------------------------------------------------------------
    # D2. Methods. Insert after rotate(delta:) if available.
    # ------------------------------------------------------------------
    methods = f'''    // {MARKER}_METHODS_BEGIN
    func rmuV111FCaptureCinematicBaseline() {{
        cinematicCameraStartUnix = Date().timeIntervalSince1970
        cinematicCameraBaseRadius = manualWorldRadius ?? frameLoader.worldRadius
        if cinematicCameraBaseRadius <= 0.0 {{
            cinematicCameraBaseRadius = 4200.0
        }}
        cinematicCameraBaseRotationRadians = rotationRadians
        cinematicCameraBasePanX = panX
        cinematicCameraBasePanY = panY
    }}

    func rmuV111FWriteCinematicCameraState(_ note: String) {{
        let state: [String: Any] = [
            "schema": "rmu.cinematic_camera_state.v1_11F",
            "version": "v1.11F",
            "enabled": cinematicCameraEnabled,
            "note": note,
            "updated_unix": Date().timeIntervalSince1970,
            "manual_world_radius": manualWorldRadius ?? frameLoader.worldRadius,
            "rotation_radians": rotationRadians,
            "pan_x": panX,
            "pan_y": panY,
            "orbit_speed": cinematicCameraOrbitSpeed,
            "zoom_amplitude": cinematicCameraZoomAmplitude,
            "pan_amplitude_x": cinematicCameraPanAmplitudeX,
            "pan_amplitude_y": cinematicCameraPanAmplitudeY
        ]

        let url = URL(fileURLWithPath: projectRoot)
            .appendingPathComponent("output")
            .appendingPathComponent("cinematic_camera_state.json")

        do {{
            let data = try JSONSerialization.data(withJSONObject: state, options: [.prettyPrinted])
            try data.write(to: url)
        }} catch {{
            // Nonfatal. Camera should never crash because debug-state write failed.
        }}
    }}

    func rmuV111FToggleCinematicCamera() {{
        cinematicCameraEnabled.toggle()
        if cinematicCameraEnabled {{
            rmuV111FCaptureCinematicBaseline()
            lastVisualStateMessage = "cinematic camera ON"
        }} else {{
            lastVisualStateMessage = "cinematic camera OFF"
        }}
        rmuV111FWriteCinematicCameraState("toggle")
        hud?.updateText()
    }}

    func rmuV111FResetCinematicCamera() {{
        rmuV111FCaptureCinematicBaseline()
        lastVisualStateMessage = cinematicCameraEnabled ? "cinematic camera reset" : "cinematic camera baseline reset"
        rmuV111FWriteCinematicCameraState("reset")
        hud?.updateText()
    }}

    func rmuV111FApplyCinematicCameraIfNeeded() {{
        guard cinematicCameraEnabled else {{ return }}

        let now = Date().timeIntervalSince1970
        let t = Float(now - cinematicCameraStartUnix)

        let baseRadius = cinematicCameraBaseRadius > 0.0
            ? cinematicCameraBaseRadius
            : (manualWorldRadius ?? frameLoader.worldRadius)

        let radiusPulse = 1.0 + cinematicCameraZoomAmplitude * sin(t * 0.17)
        manualWorldRadius = max(0.25, min(baseRadius * radiusPulse, 100000.0))

        rotationRadians = cinematicCameraBaseRotationRadians + (t * cinematicCameraOrbitSpeed)
        panX = cinematicCameraBasePanX + cinematicCameraPanAmplitudeX * sin(t * 0.31)
        panY = cinematicCameraBasePanY + cinematicCameraPanAmplitudeY * cos(t * 0.27)

        rmuV111FWriteCinematicCameraState("frame_apply")
    }}

    func rmuV111FCinematicCameraSummary() -> String {{
        return cinematicCameraEnabled
            ? "CINEMATIC ON orbit \\(String(format: "%.2f", cinematicCameraOrbitSpeed))"
            : "CINEMATIC OFF"
    }}
    // {MARKER}_METHODS_END'''

    s, ok = insert_after_function(s, "    func rotate(delta: Float)", methods)
    if not ok:
        print("ERROR: could not insert cinematic methods after rotate(delta:)")
        shutil.copy2(backup, MAIN)
        return 1
    changes.append("installed cinematic camera methods")

    # ------------------------------------------------------------------
    # D3. Gateway controls: SHIFT+C toggle, SHIFT+K reset.
    # ------------------------------------------------------------------
    key_insert = f'''        // {MARKER}: cinematic camera controls.
        // SHIFT+C toggles cinematic camera.
        // SHIFT+K resets the cinematic baseline/path. SHIFT+R is intentionally avoided.
        if shift && chars == "c" {{
            renderer?.rmuV111FToggleCinematicCamera()
            return true
        }}

        if shift && chars == "k" {{
            renderer?.rmuV111FResetCinematicCamera()
            return true
        }}'''

    s, ok = insert_inside_rmuV18_gateway_after_shift_d(s, key_insert)
    if not ok:
        print("ERROR: could not insert SHIFT+C / SHIFT+K into rmuV18AHandleKey")
        shutil.copy2(backup, MAIN)
        return 1
    changes.append("installed SHIFT+C / SHIFT+K key gateway")

    # ------------------------------------------------------------------
    # D4. Apply camera at the very front of draw(in:).
    # ------------------------------------------------------------------
    draw_patterns = [
        r"(    func draw\(in view: MTKView\) \{\n)",
        r"(    func draw\(in\s+view:\s+MTKView\)\s*\{\n)",
    ]

    draw_patched = False
    for pattern in draw_patterns:
        s2, n = re.subn(
            pattern,
            r"\1        rmuV111FApplyCinematicCameraIfNeeded() // " + MARKER + r": before camera matrices/render encoding" + "\n",
            s,
            count=1,
        )
        if n == 1:
            s = s2
            draw_patched = True
            changes.append("installed draw-stage cinematic apply call")
            break

    if not draw_patched:
        print("ERROR: could not find draw(in view: MTKView) anchor")
        shutil.copy2(backup, MAIN)
        return 1

    # ------------------------------------------------------------------
    # D5. HUD/system summary if the known function exists.
    # ------------------------------------------------------------------
    old_summary = '''    func rmuV16GSystemHUDSummary() -> String {
        return "v1.6G HUD | species v1.6B | color v1.6C | bridge v1.6D1 | apply v1.6F"
    }'''

    new_summary = f'''    func rmuV16GSystemHUDSummary() -> String {{
        // {MARKER}: expose cinematic camera status.
        return "v1.6G HUD | species v1.6B | color v1.6C | bridge v1.6D1 | apply v1.6F | \\(rmuV111FCinematicCameraSummary())"
    }}'''

    if old_summary in s:
        s = s.replace(old_summary, new_summary, 1)
        changes.append("patched system HUD summary")
    else:
        print("NOTE: system HUD summary anchor not found; cinematic still installed")

    MAIN.write_text(s)

    print("Changes:")
    for change in changes:
        print(" -", change)

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
        print("PATCH_D_FAIL: restoring backup")
        shutil.copy2(backup, MAIN)
        print("Restored:", backup)
        return result.returncode

    print("PATCH_D_PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
