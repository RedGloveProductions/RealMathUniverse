#!/usr/bin/env python3
from __future__ import annotations
import re, sys, shutil
from pathlib import Path
EXT = r'''

// RMU_V1_8A_OPERATOR_AUTHORITY_EXTENSION_BEGIN
extension AppDelegate {
    func rmuV18AOperatorURL() -> URL { URL(fileURLWithPath: projectRoot).appendingPathComponent("output").appendingPathComponent("operator_authority_state.json") }
    func rmuV18AReadOperatorState() -> [String: Any] {
        let url = rmuV18AOperatorURL()
        guard let data = try? Data(contentsOf: url), let obj = try? JSONSerialization.jsonObject(with: data, options: []), let json = obj as? [String: Any] else { return [:] }
        return json
    }
    func rmuV18AWriteOperatorState(_ patch: [String: Any], reason: String) {
        var state = rmuV18AReadOperatorState(); state["schema"] = "rmu.operator_authority_state.v1_8A"; state["version"] = "v1.8A"; state["updated_by"] = "swift_hotkey_v1_8A"; state["last_hotkey_reason"] = reason; state["updated_unix"] = Date().timeIntervalSince1970
        for (k, v) in patch { state[k] = v }
        let url = rmuV18AOperatorURL(); try? FileManager.default.createDirectory(at: url.deletingLastPathComponent(), withIntermediateDirectories: true); writeJSON(state, to: url); print("RMU v1.8A operator hotkey: \(reason)"); hud?.updateText()
    }
    func rmuV18AWeights() -> [String: Double] { let s = rmuV18AReadOperatorState(); return s["manual_field_weights"] as? [String: Double] ?? ["radial": 1.0, "orbital": 1.0, "vertical": 1.0, "turbulence": 1.0, "shell": 1.0] }
    func rmuV18ASetBehavior(_ code: Int) { let c = max(0, min(7, code)); var patch: [String: Any] = ["manual_behavior_code": c, "auto_behavior_enabled": false, "no_behavior_enabled": c == 0]; if c != 0 { patch["last_manual_behavior_code"] = c }; rmuV18AWriteOperatorState(patch, reason: "manual_behavior_\(c)") }
    func rmuV18AToggleNoBehavior() { let s = rmuV18AReadOperatorState(); let off = s["no_behavior_enabled"] as? Bool ?? false; if off { let last = s["last_manual_behavior_code"] as? Int ?? 1; rmuV18AWriteOperatorState(["no_behavior_enabled": false, "manual_behavior_code": max(1,last), "auto_behavior_enabled": false], reason: "restore_behavior") } else { let cur = s["manual_behavior_code"] as? Int ?? 0; rmuV18AWriteOperatorState(["no_behavior_enabled": true, "manual_behavior_code": 0, "last_manual_behavior_code": cur == 0 ? (s["last_manual_behavior_code"] as? Int ?? 1) : cur, "auto_behavior_enabled": false], reason: "no_behavior") } }
    func rmuV18AToggleAuto() { let s = rmuV18AReadOperatorState(); let on = !((s["auto_fields_enabled"] as? Bool ?? false) || (s["auto_behavior_enabled"] as? Bool ?? false)); rmuV18AWriteOperatorState(["auto_fields_enabled": on, "auto_behavior_enabled": on, "no_behavior_enabled": on ? false : (s["no_behavior_enabled"] as? Bool ?? false), "queues_paused": false], reason: on ? "auto_on" : "auto_off") }
    func rmuV18AFullManual() { rmuV18AWriteOperatorState(["auto_fields_enabled": false, "auto_behavior_enabled": false, "auto_camera_enabled": false, "queues_paused": true, "dataset_coupling_mode": "observe"], reason: "full_manual") }
    func rmuV18AEmergencyManual() { rmuV18AWriteOperatorState(["auto_fields_enabled": false, "auto_behavior_enabled": false, "auto_camera_enabled": false, "no_behavior_enabled": true, "manual_behavior_code": 0, "queues_paused": true, "dataset_coupling_mode": "observe"], reason: "emergency_manual") }
    func rmuV18AToggleBehaviorQueue() { let s = rmuV18AReadOperatorState(); let on = !(s["auto_behavior_enabled"] as? Bool ?? false); rmuV18AWriteOperatorState(["auto_behavior_enabled": on, "no_behavior_enabled": on ? false : (s["no_behavior_enabled"] as? Bool ?? false)], reason: on ? "behavior_queue_on" : "behavior_queue_off") }
    func rmuV18AToggleFieldQueue() { let s = rmuV18AReadOperatorState(); let on = !(s["auto_fields_enabled"] as? Bool ?? false); rmuV18AWriteOperatorState(["auto_fields_enabled": on], reason: on ? "field_queue_on" : "field_queue_off") }
    func rmuV18ACycleAutoDomain() { let s = rmuV18AReadOperatorState(); let cur = s["active_auto_domain"] as? String ?? "behavior"; let next = cur == "behavior" ? "field" : (cur == "field" ? "all" : "behavior"); rmuV18AWriteOperatorState(["active_auto_domain": next], reason: "active_auto_domain_\(next)") }
    func rmuV18AAdjustAutoSpeed(delta: Double) { let s = rmuV18AReadOperatorState(); let dom = s["active_auto_domain"] as? String ?? "behavior"; var p: [String: Any] = [:]; if dom == "behavior" || dom == "all" { p["behavior_step_seconds"] = max(5.0, min(300.0, (s["behavior_step_seconds"] as? Double ?? 30.0) + delta)) }; if dom == "field" || dom == "all" { p["field_step_seconds"] = max(5.0, min(300.0, (s["field_step_seconds"] as? Double ?? 20.0) + delta)) }; rmuV18AWriteOperatorState(p, reason: "auto_speed_adjust") }
    func rmuV18AQueueStep(domain: String, delta: Int) { rmuV18AWriteOperatorState(["command": ["action": "queue_step", "domain": domain, "delta": delta, "id": UUID().uuidString]], reason: "queue_step_\(domain)_\(delta)") }
    func rmuV18AAdjustFieldWeight(delta: Double) { let s = rmuV18AReadOperatorState(); let layer = s["selected_field_layer"] as? String ?? "radial"; var weights = rmuV18AWeights(); weights[layer] = max(0.0, min(10.0, (weights[layer] ?? 1.0) + delta)); rmuV18AWriteOperatorState(["manual_field_weights": weights, "auto_fields_enabled": false], reason: "field_weight_\(layer)") }
    func rmuV18ACycleSelectedFieldLayer() { let order = ["radial", "orbital", "vertical", "turbulence", "shell"]; let s = rmuV18AReadOperatorState(); let cur = s["selected_field_layer"] as? String ?? "radial"; let idx = order.firstIndex(of: cur) ?? 0; let next = order[(idx + 1) % order.count]; rmuV18AWriteOperatorState(["selected_field_layer": next], reason: "selected_field_layer_\(next)") }
    func rmuV18AToggleDatasetMode() { let modes = ["off", "observe", "propose", "apply"]; let s = rmuV18AReadOperatorState(); let cur = s["dataset_coupling_mode"] as? String ?? "observe"; let idx = modes.firstIndex(of: cur) ?? 1; let next = modes[(idx + 1) % modes.count]; rmuV18AWriteOperatorState(["dataset_coupling_mode": next], reason: "dataset_mode_\(next)") }
    func rmuV18AHandleKey(_ event: NSEvent) -> Bool {
        let shift = event.modifierFlags.contains(.shift); let control = event.modifierFlags.contains(.control); let chars = event.charactersIgnoringModifiers?.lowercased() ?? ""; let panStep: Float = 0.035; let rotStep: Float = 4.0 * .pi / 180.0
        if event.keyCode == 53 { rmuV18AEmergencyManual(); return true }
        if event.keyCode == 49 { toggleSimulationPause(); return true }
        if event.keyCode == 48 { rmuV18ACycleAutoDomain(); return true }
        switch event.keyCode { case 123: renderer?.pan(dx: -panStep, dy: 0); return true; case 124: renderer?.pan(dx: panStep, dy: 0); return true; case 125: renderer?.pan(dx: 0, dy: -panStep); return true; case 126: renderer?.pan(dx: 0, dy: panStep); return true; default: break }
        if control && ["1","2","3","4"].contains(chars) { switch chars { case "1": loadCameraPreset("gallery_orbit"); case "2": loadCameraPreset("macro_disk"); case "3": loadCameraPreset("wide_system"); case "4": loadCameraPreset("default_camera"); default: break }; return true }
        if chars.count == 1, let n = Int(chars), n >= 0 && n <= 7 { rmuV18ASetBehavior(n); return true }
        if shift && chars == "e" { rmuV18AToggleNoBehavior(); return true }
        if chars == "m" { rmuV18AFullManual(); return true }
        if chars == "a" { rmuV18AToggleAuto(); return true }
        if chars == "n" { rmuV18AToggleNoBehavior(); return true }
        if chars == "b" { rmuV18AToggleBehaviorQueue(); return true }
        if shift && chars == "b" { rmuV18AWriteOperatorState(["command": ["action": "clear_queues", "id": UUID().uuidString]], reason: "clear_behavior_queue"); return true }
        if chars == "f" { rmuV18AToggleFieldQueue(); return true }
        if shift && chars == "f" { rmuV18AWriteOperatorState(["auto_fields_enabled": false], reason: "force_field_manual"); return true }
        if chars == "v" { rmuV18ACycleSelectedFieldLayer(); return true }
        if chars == "[" { rmuV18AQueueStep(domain: "field", delta: -1); return true }
        if chars == "]" { rmuV18AQueueStep(domain: "field", delta: 1); return true }
        if chars == "." { rmuV18AQueueStep(domain: rmuV18AReadOperatorState()["active_auto_domain"] as? String ?? "behavior", delta: 1); return true }
        if chars == "," { rmuV18AQueueStep(domain: rmuV18AReadOperatorState()["active_auto_domain"] as? String ?? "behavior", delta: -1); return true }
        if shift && (chars == "-" || chars == "_") { rmuV18AAdjustAutoSpeed(delta: 5.0); return true }
        if shift && (chars == "=" || chars == "+") { rmuV18AAdjustAutoSpeed(delta: -5.0); return true }
        if shift && chars == "0" { rmuV18AWriteOperatorState(["behavior_step_seconds": 30.0, "field_step_seconds": 20.0], reason: "reset_auto_speed"); return true }
        if chars == "-" { rmuV18AAdjustFieldWeight(delta: -0.05); return true }
        if chars == "=" { rmuV18AAdjustFieldWeight(delta: 0.05); return true }
        if chars == "p" { let s = rmuV18AReadOperatorState(); rmuV18AWriteOperatorState(["queues_paused": !(s["queues_paused"] as? Bool ?? false)], reason: "toggle_queues_paused"); return true }
        if chars == "d" { if shift { rmuV18AWriteOperatorState(["dataset_coupling_mode": "observe"], reason: "dataset_observe") } else { rmuV18AToggleDatasetMode() }; return true }
        if chars == "g" { rmuV18AWriteOperatorState(["dataset_gain_adjust_request": shift ? "down" : "up"], reason: "dataset_gain_request"); return true }
        if chars == "o" { let s = rmuV18AReadOperatorState(); rmuV18AWriteOperatorState(["vcv_event_recording_enabled": !(s["vcv_event_recording_enabled"] as? Bool ?? true)], reason: "toggle_vcv_event_recording"); return true }
        if shift && chars == "o" { rmuV18AWriteOperatorState(["command": ["action": "clear_queues", "id": UUID().uuidString]], reason: "clear_all_queues"); return true }
        if chars == "h" { if shift { hud?.toggleBottomPanelMode() } else { hud?.toggleAll() }; hud?.updateText(); return true }
        if chars == "u" { hud?.toggleBottomPanelMode(); return true }
        if chars == "k" { if control { captureBurst(clean: false, total: burstCount, interval: burstInterval) } else { saveWindowScreenshot(clean: shift) }; return true }
        if chars == "r" { renderer?.resetGeospatialParticleState(); if shift { writeRuntimeState(source: "v1_8A_shift_r_reset") }; return true }
        if chars == "c" { if shift { rmuV18AWriteOperatorState(["auto_camera_enabled": !(rmuV18AReadOperatorState()["auto_camera_enabled"] as? Bool ?? false)], reason: "toggle_auto_camera") } else { renderer?.resetCamera() }; return true }
        if chars == "w" { renderer?.zoomIn(); return true }
        if chars == "s" { renderer?.zoomOut(); return true }
        if chars == "a" { renderer?.rotate(delta: -rotStep); return true }
        if chars == "d" { renderer?.rotate(delta: rotStep); return true }
        if chars == "q" { NSApplication.shared.terminate(nil); return true }
        return true
    }
}
// RMU_V1_8A_OPERATOR_AUTHORITY_EXTENSION_END
'''
def patch(path: Path):
    src=path.read_text(); backup=path.with_suffix(path.suffix+'.v1_8A_operator_authority.bak')
    if not backup.exists(): shutil.copy2(path, backup)
    src=re.sub(r'\n\s*// RMU_V1_7H_AUTO_HOTKEY_KEYDOWN_BEGIN.*?// RMU_V1_7H_AUTO_HOTKEY_KEYDOWN_END\n','\n',src,flags=re.S)
    src=re.sub(r'\n?// RMU_V1_7H_AUTO_HOTKEY_HELPER_BEGIN.*?// RMU_V1_7H_AUTO_HOTKEY_HELPER_END\n?','\n',src,flags=re.S)
    if '// RMU_V1_8A_HANDLEKEY_OVERRIDE' not in src: src=src.replace('    func handleKey(_ event: NSEvent) {','    func handleKey(_ event: NSEvent) {\n        // RMU_V1_8A_HANDLEKEY_OVERRIDE\n        if rmuV18AHandleKey(event) { return }',1)
    if 'RMU_V1_8A_OPERATOR_AUTHORITY_EXTENSION_BEGIN' not in src:
        idx=src.find('\nlet app = NSApplication.shared')
        if idx<0: raise SystemExit('Could not find app start marker')
        src=src[:idx]+EXT+src[idx:]
    path.write_text(src)
if __name__=='__main__':
    if len(sys.argv)!=2: raise SystemExit('Usage: patch_main_swift_v1_8A.py /path/to/main.swift')
    patch(Path(sys.argv[1]))
