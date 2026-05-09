#!/usr/bin/env python3
from pathlib import Path
import re

path = Path("metal_renderer/Sources/RealMathUniverseMetalRenderer/main.swift")
if not path.exists():
    raise SystemExit(f"PATCH FAILED: missing {path}")

text = path.read_text()
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
                    return src[:start] + replacement.rstrip() + "\n" + src[i+1:]
        i += 1
    raise SystemExit(f"PATCH FAILED: could not find closing brace for: {signature}")

text = re.sub(
    r'var\s+vcvFieldControlEnabled\s*=\s*(?:false|true)(?:\s*//[^\n]*)?',
    'var vcvFieldControlEnabled = true // RMU_V1_5A8: default ON; active bridge auto-enables in loadVCVStateIfNeeded',
    text,
    count=1
)

new_display = '''
    func vcvDisplayStatus() -> String {
        // RMU_V1_5A8_SWIFT_VCV_STATUS_DISPLAY
        // Display should reflect bridge-detection state first.
        // Field-control ON/OFF is secondary; it is not proof that OSC is absent.
        let lower = vcvStatus.lowercased()

        if lower.hasPrefix("external") || lower.contains("active") {
            return vcvFieldControlEnabled ? "ACTIVE" : "ACTIVE / field OFF"
        }

        if lower.hasPrefix("stale") {
            return vcvFieldControlEnabled ? "STALE - internal fallback" : "STALE / field OFF"
        }

        if lower.contains("not detected") {
            return vcvFieldControlEnabled ? "WAITING FOR VCV" : "VCV OFF - internal fallback"
        }

        return vcvFieldControlEnabled ? vcvStatus : "VCV OFF - internal fallback"
    }
'''
text = replace_function(text, "    func vcvDisplayStatus() -> String", new_display)

old_block = '''        let timestamp = (json["timestamp_unix"] as? NSNumber)?.doubleValue ?? 0.0
        vcvLastUpdateUnix = timestamp
        let age = now - timestamp
        let externalDetected = ((json["external_detected"] as? Bool) ?? false) && age < 3.0

        if externalDetected {
            vcvStatus = String(format: "external %.1fs", age)
            probabilitySource = (json["probability_source"] as? String) ?? "vcv"
        } else {
            vcvStatus = String(format: "stale %.1fs", age)
            probabilitySource = "internal"
        }
'''
new_block = '''        // RMU_V1_5A8_SWIFT_VCV_STATE_DETECTION
        // Support both original Swift keys and adaptive bridge keys.
        // If JSON says active/fresh and the timestamp is current, Swift must not report VCV OFF.
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
            (json["online"] as? Bool) ??
            (json["connected"] as? Bool) ??
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
            vcvFieldControlEnabled = true
            vcvStatus = String(format: "external %.1fs", age)
            probabilitySource = (json["probability_source"] as? String) ?? "vcv"
        } else {
            vcvStatus = String(format: "stale %.1fs", age)
            probabilitySource = "internal"
        }
'''
if old_block in text:
    text = text.replace(old_block, new_block, 1)
elif "RMU_V1_5A8_SWIFT_VCV_STATE_DETECTION" in text:
    print("VCV state-detection block already patched.")
else:
    # Anchor replacement without large regex: find start/end by known nearby literals.
    start = text.find('        let timestamp = (json["timestamp_unix"] as? NSNumber)?.doubleValue ?? 0.0')
    if start < 0:
        raise SystemExit("PATCH FAILED: timestamp block start not found")
    end_marker = '        if let summary = json["summary"] as? String {'
    end = text.find(end_marker, start)
    if end < 0:
        raise SystemExit("PATCH FAILED: timestamp block end marker not found")
    text = text[:start] + new_block + "\n" + text[end:]

text = text.replace(
    '        if let probabilityNumber = json["probability_value"] as? NSNumber {',
    '        if let probabilityNumber = (json["probability_value"] as? NSNumber) ?? (json["probability"] as? NSNumber) {'
)

if "RMU_V1_5A8_SWIFT_VCV_STATUS_DISPLAY" not in text:
    raise SystemExit("PATCH FAILED: display marker missing")
if "RMU_V1_5A8_SWIFT_VCV_STATE_DETECTION" not in text:
    raise SystemExit("PATCH FAILED: state detection marker missing")
if text == original:
    raise SystemExit("PATCH FAILED: no changes made")

path.write_text(text)
print("Patched main.swift for robust VCV ACTIVE detection and display.")
