from __future__ import annotations

from pathlib import Path
import time
import re
import json


ROOT = Path("/Users/Joe/Documents/RealMathUniverse")
MAIN = ROOT / "metal_renderer/Sources/RealMathUniverseMetalRenderer/main.swift"

STAMP = time.strftime("%Y%m%d_%H%M%S")
OUTDIR = Path(f"/Users/Joe/Desktop/RMU_v1_11F_HUD_CONTROL_AUDIT_{STAMP}")
OUTDIR.mkdir(parents=True, exist_ok=True)

text = MAIN.read_text(errors="replace")
lines = text.splitlines()

patterns = [
    "control_state.json",
    "runtime_state.json",
    "effective_control_state.json",
    "operator_authority_state.json",
    "behavior_effect_code",
    "behaviorEffectCode",
    "behavior_source",
    "renderer_manual",
    "hud",
    "updateText",
    "BEHAVIOR",
    "behavior src",
    "behavior src",
    "field auth",
    "selected",
    "selectedFieldLayer",
    "selected_field_layer",
    "dataset",
    "dataset_coupling",
    "active_auto_domain",
    "last_hotkey_reason",
    "rmuV16DBehaviorAuthority",
    "rmuV111FApplyFinalBehaviorAuthority",
]

def snippet(index: int, radius: int = 8) -> str:
    start = max(0, index - radius)
    end = min(len(lines), index + radius + 1)
    out = []
    for i in range(start, end):
        mark = ">>" if i == index else "  "
        out.append(f"{mark} {i+1:05d}: {lines[i]}")
    return "\n".join(out)

report = []
report.append("RMU v1.11F HUD / CONTROL STATE AUDIT")
report.append("=" * 100)

for pat in patterns:
    report.append("")
    report.append("-" * 100)
    report.append(f"PATTERN: {pat}")
    count = 0
    for i, line in enumerate(lines):
        if pat.lower() in line.lower():
            count += 1
            if count > 20:
                report.append("... more hits omitted ...")
                break
            report.append(snippet(i))

# Include live state snapshots.
for name in [
    "operator_authority_state.json",
    "effective_control_state.json",
    "control_state.json",
    "runtime_state.json",
    "vcv_state.json",
]:
    p = ROOT / "output" / name
    report.append("")
    report.append("=" * 100)
    report.append(f"LIVE SNAPSHOT: {name}")
    try:
        obj = json.loads(p.read_text())
        report.append(json.dumps(obj, indent=2, sort_keys=True))
    except Exception as exc:
        report.append(f"READ ERROR: {exc}")

out = "\n".join(report) + "\n"
(OUTDIR / "HUD_CONTROL_AUDIT.txt").write_text(out)

print(f"WROTE: {OUTDIR / 'HUD_CONTROL_AUDIT.txt'}")
print(f"OUTDIR: {OUTDIR}")
