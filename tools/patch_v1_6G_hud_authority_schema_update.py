#!/usr/bin/env python3
from __future__ import annotations

import json
import shutil
import subprocess
import sys
import time
from pathlib import Path

VERSION = "v1.6G_hud_authority_schema_update"
ROOT = Path(sys.argv[1]).expanduser().resolve() if len(sys.argv) > 1 else Path("/Users/Joe/Documents/RealMathUniverse")
MAIN = ROOT / "metal_renderer" / "Sources" / "RealMathUniverseMetalRenderer" / "main.swift"
REPORT = ROOT / "output" / "v1_6G_hud_authority_schema_update_report.json"

def fail(message: str, backup: Path | None = None) -> None:
    print("V1.6G PATCH FAILED:", message)
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps({
        "version": VERSION,
        "ok": False,
        "message": message,
        "backup": str(backup) if backup else None,
        "timestamp_unix": time.time(),
    }, indent=2))
    raise SystemExit(1)

def backup_main() -> Path:
    stamp = time.strftime("%Y%m%d_%H%M%S")
    bdir = ROOT / "backups" / VERSION
    bdir.mkdir(parents=True, exist_ok=True)
    backup = bdir / f"main.swift.{stamp}.bak"
    shutil.copy2(MAIN, backup)
    return backup

def replace_once(text: str, old: str, new: str, label: str, required: bool = False) -> tuple[str, bool]:
    if old not in text:
        if required:
            raise RuntimeError(f"required anchor missing: {label}")
        print(f"WARNING: anchor missing: {label}")
        return text, False
    return text.replace(old, new, 1), True

def insert_before(text: str, anchor: str, insertion: str, marker: str, required: bool = False) -> tuple[str, bool]:
    if marker in text:
        return text, False
    idx = text.find(anchor)
    if idx < 0:
        if required:
            raise RuntimeError(f"required anchor missing: {anchor}")
        print(f"WARNING: anchor missing: {anchor}")
        return text, False
    return text[:idx] + insertion + text[idx:], True

def patch_renderer_helpers(text: str) -> tuple[str, list[str]]:
    flags: list[str] = []
    helper = """
    // RMU_V1_6G_HUD_AUTHORITY_HELPERS_BEGIN
    func rmuV16GEffectiveBehaviorCode() -> Int32 {
        return rmuV16DBehaviorAuthorityActive ? rmuV16DBehaviorAuthorityCode : behaviorEffectCode
    }

    func rmuV16GBehaviorAuthorityLabel() -> String {
        return rmuV16DBehaviorAuthorityActive ? "VCV" : "MANUAL"
    }

    func rmuV16GBehaviorHUDSummary() -> String {
        let code = rmuV16GEffectiveBehaviorCode()
        let enabled = (rmuV16DBehaviorAuthorityActive || geospatialBehaviorEnabled) && code != 0
        let gate = String(format: "%.2fV", rmuV16DBehaviorAuthorityGate)
        return "\\(enabled ? "ON" : "OFF") code \\(code) src \\(rmuV16GBehaviorAuthorityLabel()) gate \\(gate)"
    }

    func rmuV16GFieldRecipeSummary() -> String {
        var parts: [String] = []
        for i in 0..<min(fieldLayerNames.count, fieldLayerWeights.count) {
            let enabled = i < fieldLayerEnabled.count ? fieldLayerEnabled[i] : false
            let prefix = enabled ? "*" : "-"
            parts.append("\\(prefix)\\(fieldLayerNames[i].prefix(3)):\\(String(format: "%.2f", fieldLayerWeights[i]))")
        }
        return parts.joined(separator: " ")
    }

    func rmuV16GFieldAuthoritySummary() -> String {
        let layerName = selectedFieldLayerName.uppercased()
        return "scene \\(vcvSceneIndex) layer \\(selectedFieldLayerIndex + 1) \\(layerName) | \\(rmuV16GFieldRecipeSummary())"
    }

    func rmuV16GSpeciesIdentitySummary() -> String {
        let sid = rmuV16BSpeciesIDBuffer != nil ? "SID" : "sid?"
        let fam = rmuV16BFamilyIDBuffer != nil ? "FID" : "fid?"
        let weight = rmuV16BSpeciesWeightBuffer != nil ? "W" : "w?"
        return "\\(rmuV16BSpeciesIdentityStatus) | \\(sid)/\\(fam)/\\(weight)"
    }

    func rmuV16GColorAuthoritySummary() -> String {
        return "mode \\(Int(vcvAuthorityColorMode)) \\(rmuVCVColorModeDisplayName()) | draw vertex species RGB | /ch/7"
    }

    func rmuV16GVCVAuthoritySummary() -> String {
        return "\\(vcvDisplayStatus()) | bridge v1.6D1 | /ch8 scene \\(vcvSceneIndex) | /ch18 beh \\(rmuV16GEffectiveBehaviorCode()) | /ch19 \\(String(format: "%.2fV", rmuV16DBehaviorAuthorityGate)) \\(rmuV16DBehaviorAuthorityActive ? "GATED" : "MANUAL")"
    }

    func rmuV16GSystemHUDSummary() -> String {
        return "v1.6G HUD | species v1.6B | color v1.6C | bridge v1.6D1 | apply v1.6F"
    }
    // RMU_V1_6G_HUD_AUTHORITY_HELPERS_END

"""
    text, ok = insert_before(text, "    func printDiagnostics() {", helper, "RMU_V1_6G_HUD_AUTHORITY_HELPERS_BEGIN", required=True)
    flags.append(f"renderer_hud_helpers_inserted={ok}")
    return text, flags

def patch_header(text: str) -> tuple[str, list[str]]:
    flags: list[str] = []
    old = """        append(a, "RUN RMU-1.3F6   ", color: rmuCyan(), font: monoFont(size: 12))"""
    new = """        // RMU_V1_6G_TOP_HUD_VERSION
        append(a, "RUN RMU-1.6G   ", color: rmuCyan(), font: monoFont(size: 12))"""
    text, ok = replace_once(text, old, new, "top HUD version", required=False)
    flags.append(f"top_hud_version_patched={ok}")
    return text, flags

def patch_top_behavior(text: str) -> tuple[str, list[str]]:
    flags: list[str] = []
    old = """        // RMU_V1_4A1_BEHAVIOR_HUD_STATUS
        // Behavior force-state must be visible in the HUD because SHIFT+E bypasses behavior
        // while leaving VCV and field forces active.
        let behaviorHUDEnabled = renderer.geospatialBehaviorEnabled && renderer.behaviorEffectCode != 0
        append(a, "  BEHAVIOR ", color: rmuDim(), font: monoFont(size: 12))
        append(a, behaviorHUDEnabled ? "ON" : "OFF", color: behaviorHUDEnabled ? rmuGreen() : rmuRed(), font: monoFont(size: 12, weight: .bold))
        append(a, " CODE \\(renderer.behaviorEffectCode)", color: behaviorHUDEnabled ? rmuCyan() : rmuRed(), font: monoFont(size: 12, weight: .semibold))"""
    new = """        // RMU_V1_6G_TOP_BEHAVIOR_AUTHORITY_HUD
        let behaviorHUDCode = renderer.rmuV16GEffectiveBehaviorCode()
        let behaviorHUDEnabled = (renderer.rmuV16DBehaviorAuthorityActive || renderer.geospatialBehaviorEnabled) && behaviorHUDCode != 0
        append(a, "  BEHAVIOR ", color: rmuDim(), font: monoFont(size: 12))
        append(a, behaviorHUDEnabled ? "ON" : "OFF", color: behaviorHUDEnabled ? rmuGreen() : rmuRed(), font: monoFont(size: 12, weight: .bold))
        append(a, " CODE \\(behaviorHUDCode)", color: behaviorHUDEnabled ? rmuCyan() : rmuRed(), font: monoFont(size: 12, weight: .semibold))
        append(a, " \\(renderer.rmuV16GBehaviorAuthorityLabel())", color: renderer.rmuV16DBehaviorAuthorityActive ? rmuGreen() : rmuAmber(), font: monoFont(size: 12, weight: .semibold))"""
    text, ok = replace_once(text, old, new, "top behavior authority HUD", required=False)
    flags.append(f"top_behavior_hud_patched={ok}")
    return text, flags

def patch_physics_panel(text: str) -> tuple[str, list[str]]:
    flags: list[str] = []
    old = """        appendKV(a, "field layers", renderer.fieldLayersEnabled ? "ON" : "OFF", valueColor: statusColor(renderer.fieldLayersEnabled ? "ON" : "OFF"))
        appendKV(a, "selected", renderer.selectedFieldLayerName.uppercased(), valueColor: rmuAmber())
        appendKV(a, "recipe", renderer.fieldLayerSummary())"""
    new = """        // RMU_V1_6G_PHYSICS_FIELD_BEHAVIOR_AUTHORITY_PANEL
        appendKV(a, "behavior", renderer.rmuV16GBehaviorHUDSummary(), valueColor: renderer.rmuV16DBehaviorAuthorityActive ? rmuGreen() : rmuAmber())
        appendKV(a, "field auth", renderer.rmuV16GFieldAuthoritySummary(), valueColor: rmuCyan())
        appendKV(a, "field layers", renderer.fieldLayersEnabled ? "ON" : "OFF", valueColor: statusColor(renderer.fieldLayersEnabled ? "ON" : "OFF"))
        appendKV(a, "selected", renderer.selectedFieldLayerName.uppercased(), valueColor: rmuAmber())
        appendKV(a, "recipe", renderer.rmuV16GFieldRecipeSummary())"""
    text, ok = replace_once(text, old, new, "physics field/behavior authority panel", required=False)
    flags.append(f"physics_panel_patched={ok}")
    return text, flags

def patch_vcv_panel(text: str) -> tuple[str, list[str]]:
    flags: list[str] = []
    old = """        // RMU_V1_5E_HUD_COMPACT_VCV_BANK_STATUS
        appendKV(a, "VCV", renderer.vcvDisplayStatus(), valueColor: statusColor(renderer.vcvDisplayStatus()))
        appendKV(a, "bridge", "v1.5D split banks", valueColor: rmuCyan())
        appendKV(a, "banks", renderer.rmuBankStatusLine(), valueColor: rmuGreen())
        appendKV(a, "gravity", renderer.rmuGravityVec4Summary(), valueColor: rmuYellow())
        appendKV(a, "species id", renderer.rmuV16BSpeciesIdentityStatus, valueColor: renderer.rmuV16BSpeciesIdentityLoaded ? rmuGreen() : rmuYellow())
        appendKV(a, "safe mode", renderer.vcvSafeModeEnabled ? "ON" : "OFF", valueColor: statusColor(renderer.vcvSafeModeEnabled ? "ON" : "OFF"))
        appendKV(a, "clamp", renderer.vcvLastClampEvent)
        append(a, renderer.vcvChannelCompactSummary(), color: rmuCyan())"""
    new = """        // RMU_V1_6G_HUD_COMPACT_VCV_AUTHORITY_SCHEMA
        appendKV(a, "VCV", renderer.vcvDisplayStatus(), valueColor: statusColor(renderer.vcvDisplayStatus()))
        appendKV(a, "authority", renderer.rmuV16GVCVAuthoritySummary(), valueColor: renderer.rmuV16DBehaviorAuthorityActive ? rmuGreen() : rmuAmber())
        appendKV(a, "bridge", "v1.6D1 direct /ch/1-/ch/32", valueColor: rmuCyan())
        appendKV(a, "apply", "v1.6F pre-encode", valueColor: rmuGreen())
        appendKV(a, "behavior", renderer.rmuV16GBehaviorHUDSummary(), valueColor: renderer.rmuV16DBehaviorAuthorityActive ? rmuGreen() : rmuAmber())
        appendKV(a, "field", renderer.rmuV16GFieldAuthoritySummary(), valueColor: rmuCyan())
        appendKV(a, "species id", renderer.rmuV16GSpeciesIdentitySummary(), valueColor: renderer.rmuV16BSpeciesIdentityLoaded ? rmuGreen() : rmuYellow())
        appendKV(a, "color", renderer.rmuV16GColorAuthoritySummary(), valueColor: rmuCyan())
        appendKV(a, "banks", renderer.rmuBankStatusLine(), valueColor: rmuGreen())
        appendKV(a, "gravity", renderer.rmuGravityVec4Summary(), valueColor: rmuYellow())
        appendKV(a, "safe mode", renderer.vcvSafeModeEnabled ? "ON" : "OFF", valueColor: statusColor(renderer.vcvSafeModeEnabled ? "ON" : "OFF"))
        appendKV(a, "clamp", renderer.vcvLastClampEvent)
        append(a, renderer.vcvChannelCompactSummary(), color: rmuCyan())"""
    text, ok = replace_once(text, old, new, "VCV authority panel", required=False)
    flags.append(f"vcv_panel_patched={ok}")
    return text, flags

def patch_compact_status(text: str) -> tuple[str, list[str]]:
    flags: list[str] = []
    old = """        return "\\(vcvDisplayStatus()) | v1.5D | scene \\(vcvSceneIndex) | color \\(rmuVCVColorModeDisplayName()) | \\(rmuBankStatusLine()) | \\(rmuGravityVec4Summary())\""""
    new = """        // RMU_V1_6G_COMPACT_VCV_STATUS_LINE
        return "\\(rmuV16GVCVAuthoritySummary()) | color \\(rmuVCVColorModeDisplayName()) | \\(rmuBankStatusLine()) | \\(rmuGravityVec4Summary())\""""
    text, ok = replace_once(text, old, new, "compact VCV status line", required=False)
    flags.append(f"compact_status_patched={ok}")
    return text, flags

def patch_print_diagnostics(text: str) -> tuple[str, list[str]]:
    flags: list[str] = []
    changed = False
    if "VCV_APPLY=v1.6E_DIRECT" in text:
        text = text.replace("VCV_APPLY=v1.6E_DIRECT", "VCV_APPLY=v1.6F_PRE_ENCODE HUD=v1.6G", 1)
        changed = True
    elif "VCV_APPLY=v1.6F_PRE_ENCODE" in text and "HUD=v1.6G" not in text:
        text = text.replace("VCV_APPLY=v1.6F_PRE_ENCODE", "VCV_APPLY=v1.6F_PRE_ENCODE HUD=v1.6G", 1)
        changed = True
    flags.append(f"diagnostics_hud_token_patched={changed}")
    return text, flags

def main() -> int:
    print("=" * 72)
    print(f"RealMathUniverse {VERSION}")
    print(f"Project root: {ROOT}")
    print("=" * 72)

    if not MAIN.exists():
        fail(f"main.swift not found: {MAIN}")

    backup = backup_main()
    original = MAIN.read_text()
    text = original
    flags: list[str] = []

    try:
        text, f = patch_renderer_helpers(text); flags += f
        text, f = patch_header(text); flags += f
        text, f = patch_top_behavior(text); flags += f
        text, f = patch_physics_panel(text); flags += f
        text, f = patch_vcv_panel(text); flags += f
        text, f = patch_compact_status(text); flags += f
        text, f = patch_print_diagnostics(text); flags += f

        required = [
            "RMU_V1_6G_HUD_AUTHORITY_HELPERS_BEGIN",
            "RMU_V1_6G_TOP_HUD_VERSION",
            "RMU_V1_6G_TOP_BEHAVIOR_AUTHORITY_HUD",
            "RMU_V1_6G_HUD_COMPACT_VCV_AUTHORITY_SCHEMA",
        ]
        missing = [m for m in required if m not in text]
        if missing:
            raise RuntimeError(f"missing required v1.6G HUD markers: {missing}")

        MAIN.write_text(text)

        print("Patch flags:")
        for flag in flags:
            print("  " + flag)

        print()
        print("Building renderer...")
        subprocess.run(["swift", "build", "-c", "release"], cwd=str(ROOT / "metal_renderer"), check=True)

    except Exception as exc:
        MAIN.write_text(original)
        fail(f"patch/build failed; restored original main.swift. Error: {exc}", backup=backup)

    final = MAIN.read_text(errors="replace")
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps({
        "version": VERSION,
        "ok": True,
        "timestamp_unix": time.time(),
        "project_root": str(ROOT),
        "backup": str(backup),
        "swift_build_ok": True,
        "flags": flags,
        "markers": {
            marker: marker in final
            for marker in [
                "RMU_V1_6G_HUD_AUTHORITY_HELPERS_BEGIN",
                "RMU_V1_6G_TOP_HUD_VERSION",
                "RMU_V1_6G_TOP_BEHAVIOR_AUTHORITY_HUD",
                "RMU_V1_6G_PHYSICS_FIELD_BEHAVIOR_AUTHORITY_PANEL",
                "RMU_V1_6G_HUD_COMPACT_VCV_AUTHORITY_SCHEMA",
                "RMU_V1_6G_COMPACT_VCV_STATUS_LINE",
            ]
        }
    }, indent=2))

    print()
    print("V1.6G PATCH COMPLETE")
    print("Report:", REPORT)
    print("Backup:", backup)
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
