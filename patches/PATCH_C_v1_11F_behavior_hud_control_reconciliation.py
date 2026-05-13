from __future__ import annotations

import re
import shutil
import subprocess
import time
from pathlib import Path


ROOT = Path("/Users/Joe/Documents/RealMathUniverse")
MAIN = ROOT / "metal_renderer/Sources/RealMathUniverseMetalRenderer/main.swift"
MARKER = "RMU_PATCH_C_V1_11F_BEHAVIOR_HUD_CONTROL_RECONCILIATION"


def main() -> int:
    if not MAIN.exists():
        print(f"ERROR: missing {MAIN}")
        return 1

    s = MAIN.read_text()

    if MARKER in s:
        print("PATCH_C_ALREADY_PRESENT")
        return 0

    backup = MAIN.with_name(
        f"main.swift.PATCH_C_v1_11F_behavior_hud_control_reconciliation.{time.strftime('%Y%m%d_%H%M%S')}.bak"
    )
    shutil.copy2(MAIN, backup)
    print("Backup:", backup)

    changes: list[str] = []

    # ------------------------------------------------------------------
    # C1. Protect v1.7I manual authority from stomping active VCV behavior.
    # Existing block:
    #   if !autoBehavior {
    #       let code = ...
    #       behaviorEffectCode = code
    #       rmuV16DBehaviorAuthorityActive = false
    #       ...
    #   }
    #
    # If VCV /ch19 is active, that block must not run.
    # ------------------------------------------------------------------
    old_v17i = "        if !autoBehavior {\n            let code = rmuV17IManualBehaviorCode(mode)"
    new_v17i = f"""        if !autoBehavior && !rmuV16DBehaviorAuthorityActive {{
            // {MARKER}: do not let v1.7I manual authority stomp active /ch19 VCV behavior.
            let code = rmuV17IManualBehaviorCode(mode)"""

    if old_v17i in s:
        s = s.replace(old_v17i, new_v17i, 1)
        changes.append("protected v1.7I manual behavior stomp")
    else:
        print("NOTE: v1.7I manual behavior block anchor not found or already changed")

    # ------------------------------------------------------------------
    # C2. Protect v1.7J manual authority from stomping active VCV behavior.
    # This is the block seen in the audit around rmuV17JEnforceControlAuthority.
    # ------------------------------------------------------------------
    old_v17j = "        if !rmuV17JAutoBehaviorEnabled() {\n            let code = Int32(max(0, min(7, rmuV17JInt(mode[\"manual_behavior_code\"], 0))))"
    new_v17j = f"""        if !rmuV17JAutoBehaviorEnabled() && !rmuV16DBehaviorAuthorityActive {{
            // {MARKER}: do not let v1.7J manual authority stomp active /ch19 VCV behavior.
            let code = Int32(max(0, min(7, rmuV17JInt(mode["manual_behavior_code"], 0))))"""

    if old_v17j in s:
        s = s.replace(old_v17j, new_v17j, 1)
        changes.append("protected v1.7J manual behavior stomp")
    else:
        print("NOTE: v1.7J manual behavior block anchor not found or already changed")

    # ------------------------------------------------------------------
    # C3. Make control_state.json report the effective renderer behavior source/code.
    # The audit shows control_state was still reporting renderer_manual and code 1
    # even while effective_control_state had VCV behavior.
    #
    # We patch the final writeControlState field assignment from renderer-local stale
    # behaviorEffectCode to rmuV16GEffectiveBehaviorCode() and VCV/MANUAL source.
    # ------------------------------------------------------------------
    old_control_code = '        state["behavior_effect_code"] = renderer?.behaviorEffectCode ?? 0'
    new_control_code = f'''        // {MARKER}: report effective behavior, not stale renderer-local manual code.
        state["behavior_effect_code"] = renderer?.rmuV16GEffectiveBehaviorCode() ?? 0
        state["behavior_authority_source"] = (renderer?.rmuV16DBehaviorAuthorityActive ?? false) ? "vcv_ch19_gate_ch18_behavior" : "renderer_manual"
        state["behavior_authority_gate"] = renderer?.rmuV16DBehaviorAuthorityGate ?? 0.0
        state["behavior_authority_code"] = renderer?.rmuV16DBehaviorAuthorityCode ?? 0'''

    if old_control_code in s:
        s = s.replace(old_control_code, new_control_code, 1)
        changes.append("patched writeControlState effective behavior report")
    else:
        print("NOTE: control_state behavior_effect_code anchor not found or already changed")

    # Some builds also hardcode state["behavior_source"] = behaviorSource.
    # Add a VCV-aware override immediately after that assignment if present.
    old_behavior_source = '        state["behavior_source"] = behaviorSource'
    new_behavior_source = f'''        state["behavior_source"] = behaviorSource
        // {MARKER}: override control_state behavior_source when VCV owns behavior.
        if renderer?.rmuV16DBehaviorAuthorityActive ?? false {{
            state["behavior_source"] = "vcv_ch19_gate_ch18_behavior"
        }}'''

    if old_behavior_source in s:
        s = s.replace(old_behavior_source, new_behavior_source, 1)
        changes.append("patched writeControlState behavior_source override")
    else:
        print("NOTE: behavior_source assignment anchor not found or already changed")

    # ------------------------------------------------------------------
    # C4. Improve HUD summary strings so the HUD tells the truth.
    # Keep the existing functions, but add clearer source names.
    # ------------------------------------------------------------------
    old_label_func = '''    func rmuV16GBehaviorAuthorityLabel() -> String {
        return rmuV16DBehaviorAuthorityActive ? "VCV" : "MANUAL"
    }'''

    new_label_func = f'''    func rmuV16GBehaviorAuthorityLabel() -> String {{
        // {MARKER}: explicit behavior authority label for HUD.
        return rmuV16DBehaviorAuthorityActive ? "VCV /ch19→/ch18" : "MANUAL/HOTKEY"
    }}'''

    if old_label_func in s:
        s = s.replace(old_label_func, new_label_func, 1)
        changes.append("patched HUD behavior authority label")
    else:
        print("NOTE: HUD behavior authority label function anchor not found or already changed")

    if not changes:
        print("ERROR: no Patch C changes applied")
        shutil.copy2(backup, MAIN)
        return 1

    MAIN.write_text(s)

    print("Changes:")
    for c in changes:
        print(" -", c)

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
        print("PATCH_C_FAIL: restoring backup")
        shutil.copy2(backup, MAIN)
        print("Restored:", backup)
        return result.returncode

    print("PATCH_C_PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
