#!/usr/bin/env python3
from pathlib import Path
import re
import shutil
import glob
import os

ROOT = Path("/Users/Joe/Documents/RealMathUniverse")
MAIN = ROOT / "metal_renderer/Sources/RealMathUniverseMetalRenderer/main.swift"

if not MAIN.exists():
    raise SystemExit(f"PATCH FAILED: missing {MAIN}")

text = MAIN.read_text()
original = text

def replace_function(src: str, signature: str, replacement: str) -> str:
    start = src.find(signature)
    if start < 0:
        raise SystemExit(f"PATCH FAILED: could not find function signature: {signature}")
    brace = src.find("{", start)
    if brace < 0:
        raise SystemExit(f"PATCH FAILED: could not find opening brace for: {signature}")
    depth = 0
    i = brace
    in_string = False
    escape = False
    while i < len(src):
        ch = src[i]
        if in_string:
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == '"':
                in_string = False
        else:
            if ch == '"':
                in_string = True
            elif ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    return src[:start] + replacement.rstrip() + "\n" + src[i + 1:]
        i += 1
    raise SystemExit(f"PATCH FAILED: no closing brace for {signature}")

stable_display = '''
    func vcvDisplayStatus() -> String {
        // RMU_V1_5A14_STABLE_VCV_DISPLAY_STATUS
        // Restore documented VCV status vocabulary: ACTIVE, STALE, OFF.
        // "WAITING FOR VCV" was introduced during v1.5A troubleshooting and is not part of the stable HUD contract.
        let lower = vcvStatus.lowercased()

        if lower.hasPrefix("external") || lower.contains("active") {
            return "VCV ACTIVE"
        }

        if lower.hasPrefix("stale") {
            return "VCV STALE - internal fallback"
        }

        if lower.contains("not detected") {
            return "VCV OFF - internal fallback"
        }

        if !vcvFieldControlEnabled {
            return "VCV OFF - internal fallback"
        }

        return vcvStatus
    }
'''
text = replace_function(text, "    func vcvDisplayStatus() -> String", stable_display)

# Remove any remaining literal waiting string introduced by A8/A9 patches.
text = text.replace('"WAITING FOR VCV"', '"VCV OFF - internal fallback"')
text = text.replace('"waiting for vcv"', '"vcv off - internal fallback"')

# Preserve adaptive key compatibility if already present. If not present, patch the old legacy block minimally.
if "RMU_V1_5A9_SWIFT_VCV_FILE_FRESHNESS_DETECTION" not in text and "RMU_V1_5A8_SWIFT_VCV_STATE_DETECTION" not in text:
    summary_anchor = '        if let summary = json["summary"] as? String {'
    legacy_start = text.find('        let timestamp = (json["timestamp_unix"] as? NSNumber)?.doubleValue ?? 0.0')
    if legacy_start >= 0:
        end = text.find(summary_anchor, legacy_start)
        if end < 0:
            raise SystemExit("PATCH FAILED: summary anchor not found after legacy timestamp block")
        detection = '''        // RMU_V1_5A14_COMPATIBLE_VCV_STATE_DETECTION
        let timestamp =
            (json["timestamp_unix"] as? NSNumber)?.doubleValue ??
            (json["last_update"] as? NSNumber)?.doubleValue ??
            (json["timestamp"] as? NSNumber)?.doubleValue ??
            (json["updated_at"] as? NSNumber)?.doubleValue ??
            0.0

        vcvLastUpdateUnix = timestamp
        let age = now - timestamp

        let jsonActive =
            (json["external_detected"] as? Bool) ??
            (json["active"] as? Bool) ??
            (json["fresh"] as? Bool) ??
            false

        let jsonStatus =
            ((json["status"] as? String) ??
             (json["vcv_status"] as? String) ??
             "").lowercased()

        let externalDetected =
            timestamp > 0.0 &&
            age < 3.0 &&
            (jsonActive || jsonStatus.contains("active"))

        if externalDetected {
            vcvStatus = String(format: "external %.1fs", age)
            probabilitySource = (json["probability_source"] as? String) ?? "vcv"
        } else {
            vcvStatus = String(format: "stale %.1fs", age)
            probabilitySource = "internal"
        }

'''
        text = text[:legacy_start] + detection + text[end:]

# Keep probability compatibility.
text = text.replace(
    '        if let probabilityNumber = json["probability_value"] as? NSNumber {',
    '        if let probabilityNumber = (json["probability_value"] as? NSNumber) ?? (json["probability"] as? NSNumber) {'
)

if "RMU_V1_5A14_STABLE_VCV_DISPLAY_STATUS" not in text:
    raise SystemExit("PATCH FAILED: stable VCV display marker missing")
if "WAITING FOR VCV" in text:
    raise SystemExit("PATCH FAILED: WAITING FOR VCV literal remains")

if text != original:
    MAIN.write_text(text)
    print("Patched main.swift stable VCV status vocabulary.")
else:
    print("main.swift already had the v1.5A14 status patch.")
