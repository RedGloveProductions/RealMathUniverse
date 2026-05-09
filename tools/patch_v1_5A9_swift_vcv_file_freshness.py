#!/usr/bin/env python3
from pathlib import Path
import re

path = Path("metal_renderer/Sources/RealMathUniverseMetalRenderer/main.swift")
if not path.exists():
    raise SystemExit(f"PATCH FAILED: missing {path}")

text = path.read_text()
original = text

text = re.sub(
    r'var\s+vcvFieldControlEnabled\s*=\s*(?:false|true)(?:\s*//[^\n]*)?',
    'var vcvFieldControlEnabled = true // RMU_V1_5A9: VCV control defaults ON; state freshness decides ACTIVE/STALE',
    text,
    count=1
)

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

display_replacement = '''
    func vcvDisplayStatus() -> String {
        // RMU_V1_5A9_SWIFT_VCV_DISPLAY_STATUS
        let lower = vcvStatus.lowercased()

        if lower.hasPrefix("external") || lower.contains("active") {
            return vcvFieldControlEnabled ? "ACTIVE" : "ACTIVE / field OFF"
        }

        if lower.hasPrefix("waiting") {
            return "WAITING FOR VCV"
        }

        if lower.hasPrefix("stale") {
            return vcvFieldControlEnabled ? "STALE - internal fallback" : "STALE / field OFF"
        }

        if lower.contains("not detected") {
            return "WAITING FOR VCV"
        }

        return vcvStatus
    }
'''
text = replace_function(text, "    func vcvDisplayStatus() -> String", display_replacement)

new_status_block = '''
        // RMU_V1_5A9_SWIFT_VCV_FILE_FRESHNESS_DETECTION
        // The bridge writes vcv_state.json every heartbeat. Treat a freshly modified
        // state file as live even if older JSON compatibility keys disagree.
        var fileModificationUnix: Double = 0.0
        if let attrs = try? FileManager.default.attributesOfItem(atPath: url.path),
           let modDate = attrs[.modificationDate] as? Date {
            fileModificationUnix = modDate.timeIntervalSince1970
        }

        let timestamp =
            (json["timestamp_unix"] as? NSNumber)?.doubleValue ??
            (json["last_update"] as? NSNumber)?.doubleValue ??
            (json["timestamp"] as? NSNumber)?.doubleValue ??
            (json["updated_at"] as? NSNumber)?.doubleValue ??
            fileModificationUnix

        vcvLastUpdateUnix = timestamp

        let jsonAge = now - timestamp
        let fileAge = fileModificationUnix > 0.0 ? now - fileModificationUnix : 9999.0

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
            fileAge < 3.0 ||
            (timestamp > 0.0 && jsonAge < 3.0 && (jsonActive || jsonStatus.contains("active")))

        if externalDetected {
            vcvFieldControlEnabled = true
            let shownAge = min(jsonAge, fileAge)
            vcvStatus = String(format: "external %.1fs", max(0.0, shownAge))
            probabilitySource = (json["probability_source"] as? String) ?? "vcv"
        } else {
            let shownAge = min(jsonAge, fileAge)
            vcvStatus = String(format: "stale %.1fs", max(0.0, shownAge))
            probabilitySource = "internal"
        }

'''

summary_anchor = '        if let summary = json["summary"] as? String {'
if "RMU_V1_5A9_SWIFT_VCV_FILE_FRESHNESS_DETECTION" not in text:
    a8_start = text.find("        // RMU_V1_5A8_SWIFT_VCV_STATE_DETECTION")
    if a8_start >= 0:
        end = text.find(summary_anchor, a8_start)
        if end < 0:
            raise SystemExit("PATCH FAILED: summary anchor not found after A8 block")
        text = text[:a8_start] + new_status_block + text[end:]
    else:
        legacy_start = text.find('        let timestamp = (json["timestamp_unix"] as? NSNumber)?.doubleValue ?? 0.0')
        if legacy_start < 0:
            raise SystemExit("PATCH FAILED: could not find legacy or A8 status block")
        end = text.find(summary_anchor, legacy_start)
        if end < 0:
            raise SystemExit("PATCH FAILED: summary anchor not found after legacy block")
        text = text[:legacy_start] + new_status_block + text[end:]

text = text.replace(
    '        if let probabilityNumber = json["probability_value"] as? NSNumber {',
    '        if let probabilityNumber = (json["probability_value"] as? NSNumber) ?? (json["probability"] as? NSNumber) {'
)

if "RMU_V1_5A9_SWIFT_VCV_FILE_FRESHNESS_DETECTION" not in text:
    raise SystemExit("PATCH FAILED: A9 freshness marker missing")
if "RMU_V1_5A9_SWIFT_VCV_DISPLAY_STATUS" not in text:
    raise SystemExit("PATCH FAILED: A9 display marker missing")
if text == original:
    raise SystemExit("PATCH FAILED: no changes made")

path.write_text(text)
print("Patched Swift VCV detection to use vcv_state.json file freshness.")
