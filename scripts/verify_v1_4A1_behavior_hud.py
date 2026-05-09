#!/usr/bin/env python3
from __future__ import annotations
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
swift_path = ROOT / "metal_renderer" / "Sources" / "RealMathUniverseMetalRenderer" / "main.swift"
swift = swift_path.read_text(encoding="utf-8", errors="replace")

print("RealMathUniverse v1.4A1 Behavior HUD Status verifier")
print("HUD marker present:", "RMU_V1_4A1_BEHAVIOR_HUD_STATUS" in swift)
print("BEHAVIOR label present:", 'append(a, "  BEHAVIOR "' in swift)
print("behavior HUD uses geospatialBehaviorEnabled:", "renderer.geospatialBehaviorEnabled" in swift)
print("behavior HUD shows behaviorEffectCode:", "renderer.behaviorEffectCode" in swift)
print("toggleBehaviorEngine refreshes HUD:", "func toggleBehaviorEngine()" in swift and "hud?.updateText()" in swift[swift.find("func toggleBehaviorEngine()"):swift.find("func toggleBehaviorEngine()")+1200])
