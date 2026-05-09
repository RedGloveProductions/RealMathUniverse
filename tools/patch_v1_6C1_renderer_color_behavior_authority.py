#!/usr/bin/env python3
from __future__ import annotations

import json
import shutil
import subprocess
import sys
import time
from pathlib import Path

VERSION = "v1.6C1_renderer_color_behavior_authority_repair"
ROOT = Path(sys.argv[1]).expanduser().resolve() if len(sys.argv) > 1 else Path("/Users/Joe/Documents/RealMathUniverse")
MAIN = ROOT / "metal_renderer" / "Sources" / "RealMathUniverseMetalRenderer" / "main.swift"
REPORT = ROOT / "output" / "v1_6C1_renderer_color_behavior_authority_report.json"

def fail(message: str, backup: Path | None = None) -> None:
    print("V1.6C1 PATCH FAILED:", message)
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

def insert_after(text: str, anchor: str, insertion: str, marker: str, required: bool = False) -> tuple[str, bool]:
    if marker in text:
        return text, False
    idx = text.find(anchor)
    if idx < 0:
        if required:
            raise RuntimeError(f"required anchor missing: {anchor}")
        print(f"WARNING: anchor missing: {anchor}")
        return text, False
    pos = idx + len(anchor)
    return text[:pos] + insertion + text[pos:], True

def patch_vertex_species_color(text: str) -> tuple[str, list[str]]:
    flags = []

    old_sig_tail = '''            constant float &anchorStrength [[buffer(16)]],
            uint vertexID [[vertex_id]]
        ) {'''
    new_sig_tail = '''            constant float &anchorStrength [[buffer(16)]],
            // RMU_V1_6C_VERTEX_SPECIES_COLOR_ARGS_BEGIN
            constant uint *rmuV16CRenderSpeciesIDs [[buffer(17)]],
            constant float *rmuV16CRenderColorBank [[buffer(18)]],
            constant float &rmuV16CRenderSpeciesColorEnabled [[buffer(19)]],
            // RMU_V1_6C_VERTEX_SPECIES_COLOR_ARGS_END
            uint vertexID [[vertex_id]]
        ) {'''
    if "RMU_V1_6C_VERTEX_SPECIES_COLOR_ARGS_BEGIN" not in text:
        text, ok = replace_once(text, old_sig_tail, new_sig_tail, "vertex species color args", required=True)
        flags.append(f"vertex_species_color_args_inserted={ok}")
    else:
        flags.append("vertex_species_color_args_inserted=already_present")

    old_after_base = '''            float3 fp = p.position;
            float3 baseGeospatialPosition = fp;'''
    new_after_base = '''            float3 fp = p.position;
            float3 baseGeospatialPosition = fp;

            // RMU_V1_6C_VERTEX_SPECIES_COLOR_SAMPLE_BEGIN
            uint rmuV16CSpeciesID = 0;
            float3 rmuV16CSpeciesColor = float3(1.0, 1.0, 1.0);
            if (rmuV16CRenderSpeciesColorEnabled > 0.5) {
                rmuV16CSpeciesID = min(rmuV16CRenderSpeciesIDs[vertexID], 21u);
                uint rmuV16CColorBase = rmuV16CSpeciesID * 3u;
                rmuV16CSpeciesColor = float3(
                    rmuV16CRenderColorBank[rmuV16CColorBase + 0u],
                    rmuV16CRenderColorBank[rmuV16CColorBase + 1u],
                    rmuV16CRenderColorBank[rmuV16CColorBase + 2u]
                );
            }
            // RMU_V1_6C_VERTEX_SPECIES_COLOR_SAMPLE_END'''
    if "RMU_V1_6C_VERTEX_SPECIES_COLOR_SAMPLE_BEGIN" not in text:
        text, ok = replace_once(text, old_after_base, new_after_base, "vertex species color sample", required=True)
        flags.append(f"vertex_species_color_sample_inserted={ok}")
    else:
        flags.append("vertex_species_color_sample_inserted=already_present")

    old_color_mode_3 = '''            } else if (colorMode == 3) {
                out.color = float4(0.92, 0.72 + depth * 0.25, 0.35 + radial * 0.45, alpha);
            } else if (colorMode == 4) {
                out.color = float4(1.0, 0.35 + radial * 0.55, 0.10 + depth * 0.35, alpha);'''
    new_color_mode_3 = '''            } else if (colorMode == 3) {
                // RMU_V1_6C_VERTEX_SPECIES_COLOR_MODE
                out.color = float4(rmuV16CSpeciesColor, alpha);
            } else if (colorMode == 4) {
                // RMU_V1_6C_VERTEX_SPECIES_HSL_COLOR_MODE
                out.color = float4(rmuV16CSpeciesColor, alpha);'''
    if "RMU_V1_6C_VERTEX_SPECIES_COLOR_MODE" not in text:
        text, ok = replace_once(text, old_color_mode_3, new_color_mode_3, "vertex color mode 3/4 species override", required=True)
        flags.append(f"vertex_color_modes_3_4_species_override={ok}")
    else:
        flags.append("vertex_color_modes_3_4_species_override=already_present")

    return text, flags

def patch_render_encoder_species_color(text: str) -> tuple[str, list[str]]:
    flags = []

    old = '''        encoder.setVertexBuffer(buffer, offset: 0, index: 0)'''
    # v1.6C1 repair: this must use `count`, not `drawCount`, because drawCount is declared later
    # in the current renderer. The species ID buffer is safe to bind at full count because drawCount
    # never exceeds count.
    new = '''        encoder.setVertexBuffer(buffer, offset: 0, index: 0)

        // RMU_V1_6C_RENDER_SPECIES_COLOR_BINDINGS_BEGIN
        // v1.6C1 repair: use count here because drawCount is declared later in this render function.
        rmuV16BLoadSpeciesIdentityBuffersForParticleCount(Int(count))
        if let rmuV16CRenderSpeciesIDBuffer = rmuV16BSpeciesIDBuffer {
            encoder.setVertexBuffer(rmuV16CRenderSpeciesIDBuffer, offset: 0, index: 17)
        } else {
            let fallbackIDs = Array(repeating: UInt32(0), count: max(1, Int(count)))
            if let fallbackIDBuffer = device.makeBuffer(bytes: fallbackIDs, length: fallbackIDs.count * MemoryLayout<UInt32>.stride, options: [.storageModeShared]) {
                encoder.setVertexBuffer(fallbackIDBuffer, offset: 0, index: 17)
            }
        }

        let rmuV16CRenderColorBank = rmuV16BPackColorBank96(particleSpeciesColorRGB)
        var rmuV16CRenderSpeciesColorEnabled: Float = 1.0
        rmuV16CRenderColorBank.withUnsafeBytes {
            encoder.setVertexBytes($0.baseAddress!, length: $0.count, index: 18)
        }
        encoder.setVertexBytes(&rmuV16CRenderSpeciesColorEnabled, length: MemoryLayout<Float>.stride, index: 19)
        // RMU_V1_6C_RENDER_SPECIES_COLOR_BINDINGS_END'''
    if "RMU_V1_6C_RENDER_SPECIES_COLOR_BINDINGS_BEGIN" not in text:
        text, ok = replace_once(text, old, new, "render species color vertex bindings", required=True)
        flags.append(f"render_species_color_bindings_inserted={ok}")
    else:
        flags.append("render_species_color_bindings_inserted=already_present")

    return text, flags

def patch_behavior_channels(text: str) -> tuple[str, list[str]]:
    flags = []

    anchor = '''        // RMU_V1_5G_SCENE_FIELD_AUTHORITY_PARSE'''
    insertion = '''
        // RMU_V1_6C_OPTIONAL_BEHAVIOR_CHANNEL_AUTHORITY_BEGIN
        if let voiceCounts = json["channel_voice_counts"] as? [String: Any] {
            let behaviorCodeVoices = (voiceCounts["/ch/18"] as? NSNumber)?.intValue ?? 0
            let behaviorEnabledVoices = (voiceCounts["/ch/19"] as? NSNumber)?.intValue ?? 0

            if behaviorCodeVoices > 0 && vcvChannelValues.count > 17 {
                let rawBehavior = Int(round(vcvChannelValues[17]))
                behaviorEffectCode = Int32(max(0, min(7, rawBehavior)))
            }

            if behaviorEnabledVoices > 0 && vcvChannelValues.count > 18 {
                geospatialBehaviorEnabled = vcvChannelValues[18] >= 0.5
            }
        }
        // RMU_V1_6C_OPTIONAL_BEHAVIOR_CHANNEL_AUTHORITY_END

'''
    if "RMU_V1_6C_OPTIONAL_BEHAVIOR_CHANNEL_AUTHORITY_BEGIN" not in text:
        text, ok = insert_after(text, anchor, insertion, "RMU_V1_6C_OPTIONAL_BEHAVIOR_CHANNEL_AUTHORITY_BEGIN", required=True)
        flags.append(f"optional_behavior_channel_authority_inserted={ok}")
    else:
        flags.append("optional_behavior_channel_authority_inserted=already_present")

    return text, flags

def patch_report_runtime(text: str) -> tuple[str, list[str]]:
    flags = []
    old = '''| SAFE=\\(vcvSafeModeEnabled) | \\(vcvChannelCompactSummary())")'''
    new = '''| SAFE=\\(vcvSafeModeEnabled) | SPECIES_COLOR=VERTEX | BEH18/19=OPTIONAL | \\(vcvChannelCompactSummary())")'''
    if "SPECIES_COLOR=VERTEX" not in text:
        text, ok = replace_once(text, old, new, "console species color/behavior hint", required=False)
        flags.append(f"console_hint_inserted={ok}")
    else:
        flags.append("console_hint_inserted=already_present")
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
        text, f = patch_vertex_species_color(text); flags += f
        text, f = patch_render_encoder_species_color(text); flags += f
        text, f = patch_behavior_channels(text); flags += f
        text, f = patch_report_runtime(text); flags += f

        required = [
            "RMU_V1_6C_VERTEX_SPECIES_COLOR_ARGS_BEGIN",
            "RMU_V1_6C_VERTEX_SPECIES_COLOR_SAMPLE_BEGIN",
            "RMU_V1_6C_VERTEX_SPECIES_COLOR_MODE",
            "RMU_V1_6C_RENDER_SPECIES_COLOR_BINDINGS_BEGIN",
            "RMU_V1_6C_OPTIONAL_BEHAVIOR_CHANNEL_AUTHORITY_BEGIN",
        ]
        missing = [m for m in required if m not in text]
        if missing:
            raise RuntimeError(f"missing markers before build: {missing}")

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
        "markers": {
            marker: (marker in final)
            for marker in [
                "RMU_V1_6C_VERTEX_SPECIES_COLOR_ARGS_BEGIN",
                "RMU_V1_6C_VERTEX_SPECIES_COLOR_SAMPLE_BEGIN",
                "RMU_V1_6C_VERTEX_SPECIES_COLOR_MODE",
                "RMU_V1_6C_RENDER_SPECIES_COLOR_BINDINGS_BEGIN",
                "RMU_V1_6C_OPTIONAL_BEHAVIOR_CHANNEL_AUTHORITY_BEGIN",
            ]
        },
        "flags": flags,
    }, indent=2))

    print()
    print("V1.6C1 PATCH COMPLETE")
    print("Report:", REPORT)
    print("Backup:", backup)
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
