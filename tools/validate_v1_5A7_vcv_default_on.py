#!/usr/bin/env python3
from pathlib import Path
import json, time

ROOT = Path("/Users/Joe/Documents/RealMathUniverse")
MAIN = ROOT / "metal_renderer/Sources/RealMathUniverseMetalRenderer/main.swift"
STATE = ROOT / "output/vcv_state.json"

print("RealMathUniverse v1.5A7 Swift VCV default-ON validator")
print("main.swift exists:", MAIN.exists())
if MAIN.exists():
    text = MAIN.read_text(errors="replace")
    print("vcvFieldControlEnabled default ON:", "var vcvFieldControlEnabled = true" in text)
    print("A7 marker present:", "RMU_V1_5A7" in text)
    print("SHIFT+V toggle still present:", "toggleVCV" in text or "toggle VCV" in text)

print("vcv_state exists:", STATE.exists())
if STATE.exists():
    data = json.loads(STATE.read_text())
    now = time.time()
    print("version:", data.get("version"))
    print("timestamp_unix age:", None if data.get("timestamp_unix") is None else round(now - float(data.get("timestamp_unix")), 3))
    print("external_detected:", data.get("external_detected"))
    print("probability_source:", data.get("probability_source"))
    print("active:", data.get("active"))
    print("status:", data.get("status"))
    print("fresh:", data.get("fresh"))
    print("stale:", data.get("stale"))
