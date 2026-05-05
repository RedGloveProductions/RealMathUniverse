#!/usr/bin/env python3
"""
Patch RealMathUniverse Metal renderer for v1.1B dataset panel awareness.

This is intentionally string-based because the current main.swift is generated in a
very compact format. The script backs up the file before the installer calls it.
If a pattern is not found, it exits non-zero so the installer can stop before a
bad Swift build is produced.
"""
from __future__ import annotations

from pathlib import Path
import sys

PROJECT_ROOT = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path('/Users/Joe/Documents/RealMathUniverse')
SWIFT = PROJECT_ROOT / 'metal_renderer' / 'Sources' / 'RealMathUniverseMetalRenderer' / 'main.swift'
MARKER = 'v1.1B DATASET PANEL PATCH'

text = SWIFT.read_text(encoding='utf-8')
if MARKER in text:
    print('main.swift already contains v1.1B dataset panel patch')
    raise SystemExit(0)

original = text

def replace_once(old: str, new: str, label: str) -> None:
    global text
    if old not in text:
        raise SystemExit(f'Pattern not found for {label}')
    text = text.replace(old, new, 1)
    print(f'patched: {label}')

# 1. Renderer dataset properties.
replace_once(
    'var activeVisualStateName = "manual" var activeScenePresetName = "manual" var vcvStatus = "not detected"',
    'var activeVisualStateName = "manual" var activeScenePresetName = "manual" /* v1.1B DATASET PANEL PATCH */ var bottomPanelMode = "field" var datasetLoaded = false var datasetEnabled = false var datasetFallbackActive = true var datasetFallbackReason = "not loaded" var datasetMode = "unknown" var datasetRowCount = 0 var datasetSampleIndex = 0 var datasetSourceCSV = "unknown" var datasetLastReadUnix: Double = 0.0 var datasetX: Double = 0.0 var datasetY: Double = 0.0 var datasetZ: Double = 0.0 var datasetT: Double = 0.0 var datasetCurvatureDensity: Double = 0.0 var datasetTemperatureProxy: Double = 0.0 var datasetHiggsLambda: Double = 0.0 var datasetProbabilityWeight: Double = 0.0 var datasetMappingCount = 0 var datasetMappings: [String] = [] var datasetColumns: [String] = [] var vcvStatus = "not detected"',
    'renderer dataset properties'
)

# 2. Dataset loading and text functions in MetalRenderer.
dataset_methods = r'''
 func datasetStateURL() -> URL { return URL(fileURLWithPath: projectRoot).appendingPathComponent("output").appendingPathComponent("dataset_state.json") }
 func loadDatasetState() { let url = datasetStateURL(); guard FileManager.default.fileExists(atPath: url.path) else { datasetLoaded = false; datasetEnabled = false; datasetFallbackActive = true; datasetFallbackReason = "missing output/dataset_state.json"; return }; do { let data = try Data(contentsOf: url); guard let json = try JSONSerialization.jsonObject(with: data) as? [String: Any] else { datasetFallbackReason = "invalid dataset_state json"; return }; datasetLastReadUnix = Date().timeIntervalSince1970; datasetEnabled = json["enabled"] as? Bool ?? false; datasetLoaded = json["loaded"] as? Bool ?? false; datasetFallbackActive = json["fallback_active"] as? Bool ?? true; datasetFallbackReason = json["fallback_reason"] as? String ?? "unknown"; datasetMode = json["mode"] as? String ?? "unknown"; datasetRowCount = json["row_count"] as? Int ?? 0; datasetSampleIndex = json["sample_index"] as? Int ?? 0; datasetSourceCSV = json["source_csv"] as? String ?? "unknown"; if let state = json["state"] as? [String: Any] { datasetX = state["x"] as? Double ?? datasetX; datasetY = state["y"] as? Double ?? datasetY; datasetZ = state["z"] as? Double ?? datasetZ; datasetT = state["t"] as? Double ?? datasetT; datasetCurvatureDensity = state["curvature_density"] as? Double ?? datasetCurvatureDensity; datasetTemperatureProxy = state["temperature_proxy"] as? Double ?? datasetTemperatureProxy; datasetHiggsLambda = state["higgs_lambda"] as? Double ?? datasetHiggsLambda; datasetProbabilityWeight = state["probability_weight"] as? Double ?? datasetProbabilityWeight }; if let registry = json["registry"] as? [String: Any] { datasetMappingCount = registry["mapping_count"] as? Int ?? datasetMappingCount; datasetMappings = registry["mappings"] as? [String] ?? datasetMappings; if let stats = registry["source_stats"] as? [String: Any] { datasetColumns = Array(stats.keys).sorted() } } } catch { datasetFallbackActive = true; datasetFallbackReason = "dataset read error: \(error)" } }
 func datasetStatusLine() -> String { if datasetFallbackActive { return "FALLBACK: \(datasetFallbackReason)" }; if datasetLoaded { return "LIVE" }; return "WAITING" }
 func toggleBottomPanelMode() { bottomPanelMode = (bottomPanelMode == "data") ? "field" : "data"; print("Bottom panel mode: \(bottomPanelMode)") }
 func datasetPanelText() -> String { let age = max(0.0, Date().timeIntervalSince1970 - datasetLastReadUnix); let csvName = URL(fileURLWithPath: datasetSourceCSV).lastPathComponent; let mappingList = datasetMappings.prefix(4).joined(separator: ", "); let columnList = datasetColumns.joined(separator: ", "); return """
 DATA MODE: \(datasetStatusLine()) ENABLED: \(datasetEnabled ? "ON" : "OFF") MODE: \(datasetMode)
 SOURCE: \(csvName) ROWS: \(datasetRowCount) SAMPLE: \(datasetSampleIndex) AGE: \(String(format: "%.2f", age))s
 XYZ/T: x \(String(format: "%.3f", datasetX)) y \(String(format: "%.3f", datasetY)) z \(String(format: "%.3f", datasetZ)) t \(String(format: "%.0f", datasetT))
 FIELDS: curvature \(String(format: "%.3f", datasetCurvatureDensity)) temp \(String(format: "%.3f", datasetTemperatureProxy)) higgs λ \(String(format: "%.3f", datasetHiggsLambda)) prob \(String(format: "%.3f", datasetProbabilityWeight))
 MAPPINGS: \(datasetMappingCount) active | \(mappingList)
 COLUMNS: \(columnList)
 CONTROLS: SHIFT+P field/data panel SHIFT+N data on/off | terminal: ./scripts/rmu_data_mode.sh on/off/toggle/status
 """ }
'''
replace_once('func mtkView(_ view: MTKView, drawableSizeWillChange size: CGSize) { hud?.updateLayout() }', dataset_methods + ' func mtkView(_ view: MTKView, drawableSizeWillChange size: CGSize) { hud?.updateLayout() }', 'MetalRenderer dataset methods')

# 3. Load dataset state once per draw.
replace_once(
    'func draw(in view: MTKView) { let drawStart = CFAbsoluteTimeGetCurrent() frameLoader.loadIfNeeded() updateParticleBufferIfNeeded()',
    'func draw(in view: MTKView) { let drawStart = CFAbsoluteTimeGetCurrent() frameLoader.loadIfNeeded() loadDatasetState() updateParticleBufferIfNeeded()',
    'draw loads dataset_state.json'
)

# 4. Field panel can become data panel.
replace_once(
    'fieldText.stringValue = """ FIELD LAYERS:',
    'if renderer.bottomPanelMode == "data" { fieldText.stringValue = renderer.datasetPanelText() } else { fieldText.stringValue = """ FIELD LAYERS:',
    'bottom panel data mode start'
)
replace_once(
    'SHIFT+C safe mode """ if compactMode {',
    'SHIFT+C safe mode SHIFT+P data panel """ } if compactMode {',
    'bottom panel data mode end'
)

# 5. Add HUD method for explicit toggling if needed.
replace_once(
    'func toggleCompact() { compactMode.toggle(); updateLayout(); updateText() } } final class MetalRenderer:',
    'func toggleCompact() { compactMode.toggle(); updateLayout(); updateText() } func toggleBottomPanelMode() { renderer?.toggleBottomPanelMode(); updateText() } } final class MetalRenderer:',
    'HUD toggleBottomPanelMode method'
)

# 6. Add keys: SHIFT+P panel switch, SHIFT+N data runtime on/off.
replace_once(
    'if characters == "c", shiftDown { renderer?.toggleVCVSafeMode() return }',
    'if characters == "c", shiftDown { renderer?.toggleVCVSafeMode() return } if characters == "p", shiftDown { renderer?.toggleBottomPanelMode(); hud?.updateText(); return } if characters == "n", shiftDown { toggleDatasetRuntimeMode(); return }',
    'SHIFT+P and SHIFT+N keys'
)

# 7. Add AppDelegate runtime toggle function before controlStateURL.
runtime_toggle = r'''
 func toggleDatasetRuntimeMode() { let url = URL(fileURLWithPath: projectRoot).appendingPathComponent("runtime").appendingPathComponent("data_mode_state.json"); try? FileManager.default.createDirectory(at: url.deletingLastPathComponent(), withIntermediateDirectories: true); var state: [String: Any] = [:]; if let data = try? Data(contentsOf: url), let existing = try? JSONSerialization.jsonObject(with: data) as? [String: Any] { state = existing }; let current = state["enabled"] as? Bool ?? true; state["version"] = "1.1B"; state["enabled"] = !current; state["mode"] = state["mode"] as? String ?? "crab_nav_csv"; state["updated_by"] = "metal_renderer_shift_n"; state["timestamp_unix"] = Date().timeIntervalSince1970; writeJSON(state, to: url); renderer?.lastVisualStateMessage = "data mode \(!current ? "ON" : "OFF")"; print("Dataset runtime mode: \(!current ? "ON" : "OFF")"); hud?.updateText() }
'''
replace_once('func controlStateURL() -> URL {', runtime_toggle + ' func controlStateURL() -> URL {', 'AppDelegate dataset runtime toggle')

# 8. Write current dataset state into control_state.json when renderer writes controls.
replace_once(
    'state["renderer_scene"] = renderer?.activeScenePresetName ?? "manual" var vcvState: [String: Any] = [:]',
    'state["renderer_scene"] = renderer?.activeScenePresetName ?? "manual" var datasetState: [String: Any] = [:]; datasetState["bottom_panel_mode"] = renderer?.bottomPanelMode ?? "field"; datasetState["enabled"] = renderer?.datasetEnabled ?? false; datasetState["loaded"] = renderer?.datasetLoaded ?? false; datasetState["fallback_active"] = renderer?.datasetFallbackActive ?? true; datasetState["fallback_reason"] = renderer?.datasetFallbackReason ?? "unknown"; datasetState["mode"] = renderer?.datasetMode ?? "unknown"; datasetState["row_count"] = renderer?.datasetRowCount ?? 0; datasetState["sample_index"] = renderer?.datasetSampleIndex ?? 0; datasetState["x"] = renderer?.datasetX ?? 0.0; datasetState["y"] = renderer?.datasetY ?? 0.0; datasetState["z"] = renderer?.datasetZ ?? 0.0; datasetState["curvature_density"] = renderer?.datasetCurvatureDensity ?? 0.0; datasetState["temperature_proxy"] = renderer?.datasetTemperatureProxy ?? 0.0; datasetState["higgs_lambda"] = renderer?.datasetHiggsLambda ?? 0.0; datasetState["probability_weight"] = renderer?.datasetProbabilityWeight ?? 0.0; state["dataset"] = datasetState; var vcvState: [String: Any] = [:]',
    'control_state dataset block'
)

SWIFT.write_text(text, encoding='utf-8')
print('v1.1B Metal dataset panel patch applied:', SWIFT)
