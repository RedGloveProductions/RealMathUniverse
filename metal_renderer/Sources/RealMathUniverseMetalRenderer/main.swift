// RMU_V1_11A_PHASE3C_DISABLE_DISC_SNAP: disables old tiny-radius shell/orbital disc snap for large geospatial volume
import AppKit
import Foundation
import Darwin


// RMU v1.9N JSON write helper
// Fixes v1.9M compile failure where patched code called rmuV19NWriteJSON(state, to: url)
// but no writeJSON helper existed in this Swift file.
func rmuV19NWriteJSON(_ object: Any, to url: URL) {
    do {
        let data = try JSONSerialization.data(withJSONObject: object, options: [.prettyPrinted, .sortedKeys])
        try FileManager.default.createDirectory(at: url.deletingLastPathComponent(), withIntermediateDirectories: true)
        try data.write(to: url, options: [.atomic])
    } catch {
        print("RMU v1.9N JSON write failed: \(url.path): \(error)")
    }
}
// v1.3D6 duplicate runtime helper cleanup applied
import ImageIO
import Metal
import MetalKit
// RMU_V1_9S_SOURCE_OF_TRUTH_REPAIR_MARKER
import simd




// RMU v1.3A1 geospatial runtime globals
// These are renderer-level runtime latches used by the geospatial crab-field startup path.
// They are file-scope on purpose so older renderer methods and extension-style patches can share the same state.
var runtimeMode: String = "geospatial_crab_field"
var geospatialEnabled: Bool = true
var simulationPaused: Bool = true
var lastGeospatialSpaceToggleUnix: Double = 0.0
var lastSpacebarToggleUnix: TimeInterval = 0.0


struct Particle {
    var position: SIMD3<Float>
}

final class ParticleFrameLoader {
    let binaryURL: URL
    let metadataURL: URL
    var lastModificationDate: Date?
    var particles: [Particle] = []
    var worldRadius: Float = 4200.0 // RMU_V1_11A_PHASE3C_DISABLE_DISC_SNAP: large open volumetric world radius
    var latestPointCount: Int = 0
    var sourceParticleCount: Int = 0
    var latestFrameIndex: Int = 0
    var latestExportCount: Int = 0
    var latestSimTime: Double = 0.0
    var latestProfile: String = "unknown"
    var latestComputeBackend: String = "unknown"
    var behaviorMode: String = "unknown"
    var minimumRadius: Double = 0.0
    var captureRadius: Double = 0.0
    var eventHorizonVisualRadius: Double = 0.34
    var respawnOnCapture: Bool = false
    var metadataVersion: String = "unknown"
    var lastMetadataUnix: Double = 0.0
    var metadataLoaded: Bool = false
    var renderSampleCount: Int = 25000
    var visualQuality: [String: Any] = [:]

    init(projectRoot: String) {
        let liveDir = URL(fileURLWithPath: projectRoot)
            .appendingPathComponent("output")
            .appendingPathComponent("metal_live")
        self.binaryURL = liveDir.appendingPathComponent("particles_xyz_f32.bin")
        self.metadataURL = liveDir.appendingPathComponent("metadata.json")
    }

    func loadIfNeeded() {
        guard let attrs = try? FileManager.default.attributesOfItem(atPath: binaryURL.path),
              let modDate = attrs[.modificationDate] as? Date else {
            metadataLoaded = false
            return
        }

        if let last = lastModificationDate, last == modDate {
            return
        }

        guard let data = try? Data(contentsOf: binaryURL) else {
            return
        }

        let floatCount = data.count / MemoryLayout<Float>.stride
        let pointCount = floatCount / 3
        if pointCount <= 0 { return }

        var loaded: [Particle] = []
        loaded.reserveCapacity(pointCount)

        data.withUnsafeBytes { rawBuffer in
            let floats = rawBuffer.bindMemory(to: Float.self)
            for i in 0..<pointCount {
                let base = i * 3
                loaded.append(Particle(position: SIMD3<Float>(floats[base], floats[base + 1], floats[base + 2])))
            }
        }

        particles = loaded
        latestPointCount = pointCount
        lastModificationDate = modDate
        loadMetadata()
    }

    func loadMetadata() {
        guard let data = try? Data(contentsOf: metadataURL),
              let json = try? JSONSerialization.jsonObject(with: data) as? [String: Any] else {
            metadataLoaded = false
            return
        }

        metadataLoaded = true

        if let version = json["version"] as? String { metadataVersion = version }
        if let radius = json["world_radius"] as? Double { worldRadius = Float(radius) }
        if let frameIndex = json["frame_index"] as? Int { latestFrameIndex = frameIndex }
        if let exportCount = json["export_count"] as? Int { latestExportCount = exportCount }
        if let simTime = json["sim_time"] as? Double { latestSimTime = simTime }
        if let profile = json["profile"] as? String { latestProfile = profile }
        if let backend = json["compute_backend"] as? String { latestComputeBackend = backend }
        if let behavior = json["behavior_mode"] as? String { behaviorMode = behavior }
        if let sourceCount = json["source_particle_count"] as? Int { sourceParticleCount = sourceCount }
        if let sampleCount = json["render_sample_count"] as? Int { renderSampleCount = sampleCount }
        if let minRadius = json["minimum_radius"] as? Double { minimumRadius = minRadius }
        if let capRadius = json["capture_radius"] as? Double { captureRadius = capRadius }
        if let horizon = json["event_horizon_visual_radius"] as? Double { eventHorizonVisualRadius = horizon }
        if let respawn = json["respawn_on_capture"] as? Bool { respawnOnCapture = respawn }
        if let visual = json["visual_quality"] as? [String: Any] { visualQuality = visual }
        if let stamp = json["timestamp_unix"] as? Double { lastMetadataUnix = stamp }
    }
}

final class HUDOverlayController: NSObject {
    let containerView: NSView
    let frameLoader: ParticleFrameLoader
    weak var renderer: MetalRenderer?

    let topPanel = NSVisualEffectView()
    let statsPanel = NSVisualEffectView()
    let controlsPanel = NSVisualEffectView()
    let fieldPanel = NSVisualEffectView()
    let microNavPanel = NSVisualEffectView()
    let depthPanel = NSVisualEffectView()
    let commandPanel = NSVisualEffectView()

    let topText = NSTextField(labelWithString: "")
    let statsText = NSTextField(labelWithString: "")
    let controlsText = NSTextField(labelWithString: "")
    let fieldText = NSTextField(labelWithString: "")
    let microNavText = NSTextField(labelWithString: "")
    let depthText = NSTextField(labelWithString: "")
    let commandText = NSTextField(labelWithString: "")

    var navButtons: [NSButton] = []

    var overlaysVisible = true
    var statsVisible = true
    var controlsVisible = true
    var fieldPanelVisible = true
    var compactMode = false

    let pages = ["HOME", "DATA", "FIELD", "COUPLING", "VCV", "NAV", "CAPTURE", "ALERTS"]
    var activePage = "HOME"

    var bottomPanelMode: String {
        return activePage.lowercased()
    }

    init(containerView: NSView, frameLoader: ParticleFrameLoader, renderer: MetalRenderer) {
        self.containerView = containerView
        self.frameLoader = frameLoader
        self.renderer = renderer
        super.init()
        buildPanels()
        updateLayout()
        updateText()
    }

    func buildPanels() {
        [topPanel, statsPanel, controlsPanel, fieldPanel, microNavPanel, depthPanel, commandPanel].forEach { configure(panel: $0) }
        [topText, statsText, controlsText, fieldText, microNavText, depthText, commandText].forEach { configureLabel($0) }

        topPanel.addSubview(topText)
        statsPanel.addSubview(statsText)
        controlsPanel.addSubview(controlsText)
        fieldPanel.addSubview(fieldText)
        microNavPanel.addSubview(microNavText)
        depthPanel.addSubview(depthText)
        commandPanel.addSubview(commandText)

        buildNavButtons()

        containerView.addSubview(topPanel)
        containerView.addSubview(statsPanel)
        containerView.addSubview(controlsPanel)
        containerView.addSubview(fieldPanel)
        containerView.addSubview(microNavPanel)
        containerView.addSubview(depthPanel)
        containerView.addSubview(commandPanel)
    }

    func buildNavButtons() {
        // v1.2B3: text-first tactical tiles.
        // Avoid Unicode icon glyphs here because the active macOS fallback font can
        // render them as random symbols/boxes on some machines.  These labels are
        // deliberately explicit, operator-readable, and MFD-style.
        let labels = [
            "HOME\nOVERVIEW",
            "DATA\nDATASET",
            "FIELD\nLAYERS",
            "COUPLING\nDRIVE",
            "VCV\nOSC",
            "NAV\nPOSITION",
            "CAPTURE\nOUTPUT",
            "ALERTS\nSTATUS"
        ]
        for i in 0..<labels.count {
            let b = NSButton(title: labels[i], target: self, action: #selector(navButtonClicked(_:)))
            b.tag = i
            b.bezelStyle = .rounded
            b.isBordered = true
            b.font = monoFont(size: 12, weight: .medium)
            b.alignment = .center
            b.wantsLayer = true
            b.layer?.cornerRadius = 9
            b.layer?.borderWidth = 1
            b.layer?.masksToBounds = true
            navButtons.append(b)
            controlsPanel.addSubview(b)
        }
    }

    @objc func navButtonClicked(_ sender: NSButton) {
        let idx = max(0, min(sender.tag, pages.count - 1))
        activePage = pages[idx]
        print("RMU console page -> \(activePage)")
        updateText()
    }

    func configure(panel: NSVisualEffectView) {
        panel.material = .hudWindow
        panel.blendingMode = .withinWindow
        panel.state = .active
        panel.wantsLayer = true
        panel.layer?.cornerRadius = 10
        panel.layer?.masksToBounds = true
        panel.layer?.borderWidth = 1
        panel.layer?.borderColor = NSColor(calibratedRed: 0.18, green: 0.32, blue: 0.42, alpha: 0.75).cgColor
        panel.layer?.backgroundColor = NSColor(calibratedRed: 0.015, green: 0.035, blue: 0.055, alpha: 0.34).cgColor
    }

    func configureLabel(_ label: NSTextField) {
        label.font = monoFont(size: 12, weight: .regular)
        label.textColor = rmuText()
        label.backgroundColor = .clear
        label.isBordered = false
        label.isEditable = false
        label.isSelectable = false
        label.lineBreakMode = .byWordWrapping
        label.maximumNumberOfLines = 0
    }

    func monoFont(size: CGFloat, weight: NSFont.Weight = .regular) -> NSFont {
        return NSFont(name: "IBM Plex Mono", size: size) ?? NSFont.monospacedSystemFont(ofSize: size, weight: weight)
    }

    func titleFont(size: CGFloat) -> NSFont {
        return NSFont(name: "Cinzel", size: size) ?? NSFont(name: "Times New Roman", size: size) ?? NSFont.systemFont(ofSize: size, weight: .semibold)
    }

    func rmuText() -> NSColor { NSColor(calibratedRed: 0.88, green: 0.93, blue: 0.96, alpha: 1.0) }
    func rmuDim() -> NSColor { NSColor(calibratedRed: 0.58, green: 0.68, blue: 0.75, alpha: 1.0) }
    func rmuCyan() -> NSColor { NSColor(calibratedRed: 0.31, green: 0.76, blue: 0.97, alpha: 1.0) }
    func rmuTeal() -> NSColor { NSColor(calibratedRed: 0.24, green: 0.84, blue: 0.78, alpha: 1.0) }
    func rmuAmber() -> NSColor { NSColor(calibratedRed: 1.00, green: 0.74, blue: 0.22, alpha: 1.0) }
    func rmuGreen() -> NSColor { NSColor(calibratedRed: 0.49, green: 1.00, blue: 0.54, alpha: 1.0) }
    func rmuYellow() -> NSColor { NSColor(calibratedRed: 1.00, green: 0.84, blue: 0.35, alpha: 1.0) }
    func rmuRed() -> NSColor { NSColor(calibratedRed: 1.00, green: 0.34, blue: 0.34, alpha: 1.0) }

    func updateLayout() {
        let bounds = containerView.bounds
        let margin: CGFloat = 10
        let topH: CGFloat = compactMode ? 34 : 42
        let bottomH: CGFloat = compactMode ? 130 : 218
        let leftW: CGFloat = compactMode ? 270 : 335
        let rightW: CGFloat = compactMode ? 260 : 305
        let microH: CGFloat = compactMode ? 0 : 125
        let commandH: CGFloat = compactMode ? 0 : 50

        topPanel.frame = NSRect(x: margin, y: bounds.height - margin - topH, width: bounds.width - margin * 2, height: topH)

        let sideTopY = bounds.height - margin - topH - margin
        let leftAvailableH = sideTopY - bottomH - commandH - margin * 3
        let mainLeftHeight = max(compactMode ? 150 : 300, leftAvailableH - microH - margin)
        statsPanel.frame = NSRect(x: margin, y: bottomH + commandH + margin * 3 + microH, width: leftW, height: mainLeftHeight)

        if compactMode {
            microNavPanel.frame = .zero
            depthPanel.frame = .zero
            commandPanel.frame = .zero
        } else {
            microNavPanel.frame = NSRect(x: margin, y: bottomH + commandH + margin * 2, width: (leftW - margin) / 2, height: microH)
            depthPanel.frame = NSRect(x: margin + (leftW - margin) / 2 + margin, y: bottomH + commandH + margin * 2, width: (leftW - margin) / 2, height: microH)
            commandPanel.frame = NSRect(x: margin, y: margin, width: bounds.width - margin * 2, height: commandH)
        }

        controlsPanel.frame = NSRect(x: bounds.width - margin - rightW, y: bottomH + commandH + margin * 2, width: rightW, height: sideTopY - bottomH - commandH - margin * 2)
        fieldPanel.frame = NSRect(x: leftW + margin * 2, y: commandH + margin * 2, width: bounds.width - leftW - rightW - margin * 4, height: bottomH)

        let inset: CGFloat = compactMode ? 10 : 14
        topText.frame = topPanel.bounds.insetBy(dx: inset, dy: 7)
        statsText.frame = statsPanel.bounds.insetBy(dx: inset, dy: inset)
        fieldText.frame = fieldPanel.bounds.insetBy(dx: inset, dy: inset)
        microNavText.frame = microNavPanel.bounds.insetBy(dx: 10, dy: 10)
        depthText.frame = depthPanel.bounds.insetBy(dx: 10, dy: 10)
        commandText.frame = commandPanel.bounds.insetBy(dx: 12, dy: 9)

        layoutNavButtonsAndDetail(inset: inset)
    }

    func layoutNavButtonsAndDetail(inset: CGFloat) {
        let cols = 2
        let spacing: CGFloat = 7
        let buttonH: CGFloat = compactMode ? 46 : 72
        let usableW = controlsPanel.bounds.width - inset * 2
        let buttonW = (usableW - spacing) / 2
        let topY = controlsPanel.bounds.height - inset - buttonH
        for i in 0..<navButtons.count {
            let row = i / cols
            let col = i % cols
            let x = inset + CGFloat(col) * (buttonW + spacing)
            let y = topY - CGFloat(row) * (buttonH + spacing)
            navButtons[i].frame = NSRect(x: x, y: y, width: buttonW, height: buttonH)
        }
        let buttonRows = CGFloat((navButtons.count + 1) / 2)
        let detailTop = topY - buttonRows * (buttonH + spacing) - 8
        controlsText.frame = NSRect(x: inset, y: inset, width: usableW, height: max(60, detailTop - inset))
    }

    func applyVisibility() {
        topPanel.isHidden = !overlaysVisible
        statsPanel.isHidden = !(overlaysVisible && statsVisible)
        controlsPanel.isHidden = !(overlaysVisible && controlsVisible)
        fieldPanel.isHidden = !(overlaysVisible && fieldPanelVisible)
        microNavPanel.isHidden = !(overlaysVisible && statsVisible) || compactMode
        depthPanel.isHidden = !(overlaysVisible && statsVisible) || compactMode
        commandPanel.isHidden = !overlaysVisible || compactMode
    }

    func toggleAll() { overlaysVisible.toggle(); applyVisibility() }
    func toggleStats() { statsVisible.toggle(); applyVisibility() }
    func toggleControls() { controlsVisible.toggle(); applyVisibility() }
    func toggleCompact() { compactMode.toggle(); updateLayout(); applyVisibility(); updateText() }

    func toggleBottomPanelMode() {
        let idx = pages.firstIndex(of: activePage) ?? 0
        activePage = pages[(idx + 1) % pages.count]
        print("RMU console page -> \(activePage)")
        updateText()
    }

    func setPage(_ page: String) {
        if pages.contains(page) { activePage = page }
        updateText()
    }

    func numberString(_ value: Any?, digits: Int = 3) -> String {
        if let n = value as? NSNumber { return String(format: "%.*f", digits, n.doubleValue) }
        if let d = value as? Double { return String(format: "%.*f", digits, d) }
        if let f = value as? Float { return String(format: "%.*f", digits, Double(f)) }
        if let i = value as? Int { return "\(i)" }
        return "n/a"
    }

    func sciString(_ value: Any?, digits: Int = 3) -> String {
        if let n = value as? NSNumber { return String(format: "%.*e", digits, n.doubleValue) }
        if let d = value as? Double { return String(format: "%.*e", digits, d) }
        if let f = value as? Float { return String(format: "%.*e", digits, Double(f)) }
        if let i = value as? Int { return "\(i)" }
        return "n/a"
    }

    func stringValue(_ value: Any?) -> String {
        if let s = value as? String { return s }
        if let b = value as? Bool { return b ? "true" : "false" }
        if let n = value as? NSNumber { return "\(n)" }
        return "n/a"
    }

    func boolValue(_ value: Any?) -> Bool {
        if let b = value as? Bool { return b }
        if let n = value as? NSNumber { return n.boolValue }
        if let s = value as? String { return ["true", "yes", "1", "on"].contains(s.lowercased()) }
        return false
    }

    func readJSON(pathParts: [String]) -> [String: Any]? {
        guard let root = renderer?.projectRoot else { return nil }
        var url = URL(fileURLWithPath: root)
        for p in pathParts { url.appendPathComponent(p) }
        guard let data = try? Data(contentsOf: url),
              let object = try? JSONSerialization.jsonObject(with: data, options: []),
              let json = object as? [String: Any] else { return nil }
        return json
    }

    func readDatasetState() -> [String: Any]? { readJSON(pathParts: ["output", "dataset_state.json"]) }
    func readCouplingState() -> [String: Any]? { readJSON(pathParts: ["output", "dataset_coupling_state.json"]) }
    func readRuntimeState() -> [String: Any]? { readJSON(pathParts: ["output", "runtime_state.json"]) }

    func runtimeStatusLabel() -> String {
        if !frameLoader.metadataLoaded { return "WAITING" }
        let rt = readRuntimeState()
        let armed = boolValue(rt?["physics_armed"])
        let paused = boolValue(rt?["simulation_paused"])
        if armed { return "ARMED" }
        if paused { return "PAUSED" }
        return "LIVE"
    }

    func runtimeModeLabel() -> String {
        let s = stringValue(readRuntimeState()?["runtime_mode"])
        return s == "n/a" ? "unknown" : s
    }

    func runtimeBehaviorLabel() -> String {
        let s = stringValue(readRuntimeState()?["behavior_mode"])
        return s == "n/a" ? frameLoader.behaviorMode : s
    }

    func runtimeArmedLabel() -> String {
        boolValue(readRuntimeState()?["physics_armed"]) ? "TRUE" : "FALSE"
    }


    func healthColor(label: String, value: Double) -> NSColor {
        let l = label.lowercased()
        if l.contains("fps") {
            if value >= 55 { return rmuGreen() }
            if value >= 40 { return rmuYellow() }
            return rmuRed()
        }
        if l.contains("frame") && l.contains("ms") {
            if value <= 16.7 { return rmuGreen() }
            if value <= 30.0 { return rmuYellow() }
            return rmuRed()
        }
        if l.contains("fallback") { return value == 0 ? rmuGreen() : rmuRed() }
        if l.contains("probability") {
            if value >= 0.15 && value <= 0.85 { return rmuGreen() }
            if value > 0.05 && value < 0.95 { return rmuYellow() }
            return rmuRed()
        }
        if l.contains("curvature") {
            if value <= 0.65 { return rmuGreen() }
            if value <= 0.90 { return rmuYellow() }
            return rmuRed()
        }
        if l.contains("temperature") || l.contains("temp") {
            if value <= 0.70 { return rmuGreen() }
            if value <= 0.88 { return rmuYellow() }
            return rmuRed()
        }
        if l.contains("higgs") {
            if value <= 0.70 { return rmuGreen() }
            if value <= 0.90 { return rmuYellow() }
            return rmuRed()
        }
        if l.contains("latency") {
            if value <= 90 { return rmuGreen() }
            if value <= 250 { return rmuYellow() }
            return rmuRed()
        }
        return rmuCyan()
    }

    func statusColor(_ text: String) -> NSColor {
        let s = text.lowercased()
        if s.contains("false") || s.contains("ok") || s.contains("live") || s.contains("active") || s.contains("armed") || s.contains("running") || s.contains("true") || s.contains("on") || s.contains("nominal") { return rmuGreen() }
        if s.contains("paused") || s.contains("stale") || s.contains("waiting") || s.contains("moderate") || s.contains("warning") { return rmuYellow() }
        if s.contains("fallback") || s.contains("missing") || s.contains("error") || s.contains("bad") || s.contains("off") || s.contains("failed") { return rmuRed() }
        return rmuText()
    }

    func append(_ attr: NSMutableAttributedString, _ text: String, color: NSColor? = nil, font: NSFont? = nil) {
        let attrs: [NSAttributedString.Key: Any] = [
            .font: font ?? monoFont(size: 12),
            .foregroundColor: color ?? rmuText()
        ]
        attr.append(NSAttributedString(string: text, attributes: attrs))
    }

    func appendKV(_ attr: NSMutableAttributedString, _ key: String, _ value: String, valueColor: NSColor? = nil, unit: String = "") {
        let label = key.padding(toLength: 18, withPad: " ", startingAt: 0)
        append(attr, label, color: rmuDim())
        append(attr, value, color: valueColor ?? rmuCyan())
        if !unit.isEmpty { append(attr, " \(unit)", color: rmuDim()) }
        append(attr, "\n", color: rmuText())
    }

    func sectionTitle(_ title: String) -> String { "▸ \(title)\n" }

    func updateNavButtonStyles() {
        for (i, button) in navButtons.enumerated() {
            let selected = pages[i] == activePage
            button.contentTintColor = selected ? rmuAmber() : rmuText()
            button.layer?.borderColor = (selected ? rmuAmber() : NSColor(calibratedRed: 0.20, green: 0.34, blue: 0.43, alpha: 0.90)).cgColor
            button.layer?.backgroundColor = (selected ? NSColor(calibratedRed: 0.18, green: 0.12, blue: 0.02, alpha: 0.44) : NSColor(calibratedRed: 0.02, green: 0.05, blue: 0.075, alpha: 0.30)).cgColor
        }
    }

    func updateText() {
        guard let renderer = renderer else { return }
        updateNavButtonStyles()

        let now = Date()
        let formatter = DateFormatter()
        formatter.dateFormat = "yyyy-MM-dd HH:mm:ss"
        formatter.timeZone = TimeZone(abbreviation: "UTC")
        let utc = formatter.string(from: now)
        let fileStatus = runtimeStatusLabel()
        let alertCount = activeAlertCount(renderer: renderer)
        let dataset = readDatasetState()
        let coupling = readCouplingState()
        let datasetLoaded = boolValue(dataset?["loaded"])
        let datasetFallback = boolValue(dataset?["fallback_active"])
        let couplingEnabled = boolValue(coupling?["enabled"]) || renderer.dataCouplingEnabled

        topText.attributedStringValue = topStatusAttributed(
            utc: utc,
            fileStatus: fileStatus,
            datasetLoaded: datasetLoaded,
            datasetFallback: datasetFallback,
            couplingEnabled: couplingEnabled,
            alertCount: alertCount,
            renderer: renderer
        )

        statsText.attributedStringValue = leftTelemetryAttributed(renderer: renderer, dataset: dataset, coupling: coupling)
        controlsText.attributedStringValue = rightControlAttributed(renderer: renderer, dataset: dataset, coupling: coupling)
        fieldText.attributedStringValue = bottomConsoleAttributed(renderer: renderer, dataset: dataset, coupling: coupling)
        microNavText.attributedStringValue = microNavAttributed(renderer: renderer, dataset: dataset)
        depthText.attributedStringValue = depthGaugeAttributed(renderer: renderer, dataset: dataset)
        commandText.attributedStringValue = commandBarAttributed(renderer: renderer)
    }

    func topStatusAttributed(utc: String, fileStatus: String, datasetLoaded: Bool, datasetFallback: Bool, couplingEnabled: Bool, alertCount: Int, renderer: MetalRenderer) -> NSAttributedString {
        let a = NSMutableAttributedString()
        append(a, " UTC \(utc)   ", color: rmuDim(), font: monoFont(size: 12))
        // RMU_V1_6G_TOP_HUD_VERSION
        append(a, "RUN RMU-1.6G4   ", color: rmuCyan(), font: monoFont(size: 12))
        append(a, fileStatus, color: statusColor(fileStatus), font: monoFont(size: 12, weight: .semibold))
        append(a, "      RMU TACTICAL RESEARCH CONSOLE      ", color: rmuText(), font: titleFont(size: 22))
        append(a, "DATA ", color: rmuDim(), font: monoFont(size: 12))
        append(a, datasetLoaded && !datasetFallback ? "ON" : (datasetFallback ? "FALLBACK" : "OFF"), color: datasetLoaded && !datasetFallback ? rmuGreen() : rmuRed(), font: monoFont(size: 12, weight: .semibold))
        append(a, "  VCV ", color: rmuDim(), font: monoFont(size: 12))
        append(a, renderer.vcvDisplayStatus(), color: statusColor(renderer.vcvDisplayStatus()), font: monoFont(size: 12, weight: .semibold))
        append(a, "  COUPLING ", color: rmuDim(), font: monoFont(size: 12))
        append(a, couplingEnabled ? "ON" : "OFF", color: couplingEnabled ? rmuGreen() : rmuYellow(), font: monoFont(size: 12, weight: .semibold))

        // RMU_V1_6G_TOP_BEHAVIOR_AUTHORITY_HUD
        let behaviorHUDCode = renderer.rmuV16GEffectiveBehaviorCode()
        let behaviorHUDEnabled = (renderer.rmuV16DBehaviorAuthorityActive || renderer.geospatialBehaviorEnabled) && behaviorHUDCode != 0
        append(a, "  BEHAVIOR ", color: rmuDim(), font: monoFont(size: 12))
        append(a, behaviorHUDEnabled ? "ON" : "OFF", color: behaviorHUDEnabled ? rmuGreen() : rmuRed(), font: monoFont(size: 12, weight: .bold))
        append(a, " CODE \(behaviorHUDCode)", color: behaviorHUDEnabled ? rmuCyan() : rmuRed(), font: monoFont(size: 12, weight: .semibold))
        append(a, " \(renderer.rmuV16GBehaviorAuthorityLabel())", color: renderer.rmuV16DBehaviorAuthorityActive ? rmuGreen() : rmuAmber(), font: monoFont(size: 12, weight: .semibold))

        append(a, "  ALERTS \(alertCount)", color: alertCount == 0 ? rmuGreen() : (alertCount < 3 ? rmuYellow() : rmuRed()), font: monoFont(size: 12, weight: .semibold))
        return a
    }

    func activeAlertCount(renderer: MetalRenderer) -> Int {
        var c = 0
        if renderer.lateFrameWarning { c += 1 }
        if renderer.vcvDisplayStatus().lowercased().contains("stale") { c += 1 }
        if let dataset = readDatasetState(), boolValue(dataset["fallback_active"]) { c += 1 }
        return c
    }

    func leftTelemetryAttributed(renderer: MetalRenderer, dataset: [String: Any]?, coupling: [String: Any]?) -> NSAttributedString {
        let a = NSMutableAttributedString()
        append(a, sectionTitle("SYSTEM"), color: rmuCyan(), font: monoFont(size: 13, weight: .semibold))
        appendKV(a, "status", runtimeStatusLabel(), valueColor: statusColor(runtimeStatusLabel()))
        appendKV(a, "backend", frameLoader.latestComputeBackend)
        appendKV(a, "fps", String(format: "%.1f", renderer.currentFPS), valueColor: healthColor(label: "fps", value: renderer.currentFPS))
        appendKV(a, "frame ms", String(format: "%.2f", renderer.currentFrameTimeMS), valueColor: healthColor(label: "frame ms", value: renderer.currentFrameTimeMS))
        appendKV(a, "profile", frameLoader.latestProfile)
        appendKV(a, "sim time", String(format: "%.2f", frameLoader.latestSimTime))
        append(a, "\n", color: rmuText())

        append(a, sectionTitle("PHYSICS"), color: rmuCyan(), font: monoFont(size: 13, weight: .semibold))
        // RMU_V1_6G4_LEFT_PHYSICS_AUTHORITY_PANEL
        appendKV(a, "behavior", renderer.rmuV16GBehaviorHUDSummary(), valueColor: renderer.rmuV16DBehaviorAuthorityActive ? rmuGreen() : rmuAmber())
        appendKV(a, "behavior src", renderer.rmuV16GBehaviorAuthorityLabel(), valueColor: renderer.rmuV16DBehaviorAuthorityActive ? rmuGreen() : rmuAmber())
        appendKV(a, "beh code", "\(renderer.rmuV16GEffectiveBehaviorCode())", valueColor: renderer.rmuV16DBehaviorAuthorityActive ? rmuCyan() : rmuAmber())
        appendKV(a, "gate", String(format: "%.2fV", renderer.rmuV16DBehaviorAuthorityGate), valueColor: renderer.rmuV16DBehaviorAuthorityActive ? rmuGreen() : rmuRed())
        appendKV(a, "field auth", renderer.rmuV16GFieldAuthoritySummary(), valueColor: rmuCyan())
        appendKV(a, "field layers", renderer.fieldLayersEnabled ? "ON" : "OFF", valueColor: statusColor(renderer.fieldLayersEnabled ? "ON" : "OFF"))
        appendKV(a, "selected", renderer.selectedFieldLayerName.uppercased(), valueColor: rmuAmber())
        appendKV(a, "selected weight", String(format: "%.2f", renderer.selectedFieldLayerWeight), valueColor: rmuAmber())
        appendKV(a, "recipe", renderer.rmuV16GFieldRecipeSummary(), valueColor: rmuCyan())
        appendKV(a, "apply", "v1.6F pre-encode", valueColor: rmuGreen())
        for i in 0..<renderer.fieldLayerNames.count {
            let name = renderer.fieldLayerNames[i]
            let val = renderer.fieldLayerWeights[i]
            let enabled = renderer.fieldLayerEnabled[i]
            appendKV(a, name, String(format: "%.2f  %@", val, enabled ? "ON" : "OFF"), valueColor: enabled ? rmuGreen() : rmuDim())
        }
        append(a, sectionTitle("DATASET"), color: rmuCyan(), font: monoFont(size: 13, weight: .semibold))
        if let ds = dataset {
            appendKV(a, "mode", stringValue(ds["mode"]), valueColor: rmuAmber())
            appendKV(a, "rows", numberString(ds["row_count"], digits: 0))
            appendKV(a, "sample", numberString(ds["sample_index"], digits: 0))
            appendKV(a, "loaded", stringValue(ds["loaded"]).uppercased(), valueColor: statusColor(stringValue(ds["loaded"])))
            appendKV(a, "fallback", stringValue(ds["fallback_active"]).uppercased(), valueColor: boolValue(ds["fallback_active"]) ? rmuRed() : rmuGreen())
        } else {
            appendKV(a, "status", "MISSING", valueColor: rmuRed())
        }
        append(a, "\n", color: rmuText())

        append(a, sectionTitle("ALERTS"), color: rmuCyan(), font: monoFont(size: 13, weight: .semibold))
        if renderer.lateFrameWarning { appendKV(a, "01 frame", "LATE", valueColor: rmuYellow()) }
        if renderer.vcvDisplayStatus().lowercased().contains("stale") { appendKV(a, "02 vcv", "STALE", valueColor: rmuYellow()) }
        if let ds = dataset, boolValue(ds["fallback_active"]) { appendKV(a, "03 data", "FALLBACK", valueColor: rmuRed()) }
        if activeAlertCount(renderer: renderer) == 0 { appendKV(a, "status", "NOMINAL", valueColor: rmuGreen()) }
        return a
    }

    func rightControlAttributed(renderer: MetalRenderer, dataset: [String: Any]?, coupling: [String: Any]?) -> NSAttributedString {
        let a = NSMutableAttributedString()
        append(a, "\(activePage) CONTROLS\n", color: rmuAmber(), font: monoFont(size: 13, weight: .semibold))
        append(a, "────────────────────────────\n", color: rmuDim())
        switch activePage {
        case "HOME":
            appendKV(a, "overview", "system + live telemetry")
            appendKV(a, "HUD cycle", "SHIFT+M")
            appendKV(a, "compact", "M")
            appendKV(a, "hide HUD", "H")
        case "DATA":
            appendKV(a, "source", (stringValue(dataset?["source_csv"]) as NSString).lastPathComponent)
            appendKV(a, "mode", stringValue(dataset?["mode"]), valueColor: rmuAmber())
            appendKV(a, "loaded", stringValue(dataset?["loaded"]).uppercased(), valueColor: statusColor(stringValue(dataset?["loaded"])))
            appendKV(a, "terminal", "rmu_data_mode.sh")
        case "FIELD":
            appendKV(a, "toggle fields", "F")
            appendKV(a, "select layer", "TAB")
            appendKV(a, "layer on/off", "SPACE")
            appendKV(a, "weight", "/  \\")
        case "COUPLING":
            appendKV(a, "coupling", renderer.dataCouplingEnabled ? "ON" : "OFF", valueColor: renderer.dataCouplingEnabled ? rmuGreen() : rmuYellow())
            appendKV(a, "toggle", "SHIFT+B")
            appendKV(a, "gain cycle", "SHIFT+G")
            appendKV(a, "gain", String(format: "%.2f", renderer.dataCouplingGain), valueColor: rmuAmber())
            appendKV(a, "smooth", String(format: "%.2f", renderer.dataCouplingSmooth))
        case "VCV":
            appendKV(a, "status", renderer.vcvDisplayStatus(), valueColor: statusColor(renderer.vcvDisplayStatus()))
            appendKV(a, "field ctrl", renderer.vcvFieldControlEnabled ? "ON" : "OFF", valueColor: statusColor(renderer.vcvFieldControlEnabled ? "ON" : "OFF"))
            appendKV(a, "toggle VCV", "SHIFT+V")
            appendKV(a, "OSC monitor", "SHIFT+O")
        case "NAV":
            appendKV(a, "pan", "arrow keys")
            appendKV(a, "rotate", "A / D")
            appendKV(a, "zoom", "W / Z  Q / E")
            appendKV(a, "camera reset", "X")
            appendKV(a, "particle reset", "SHIFT+R")
        case "CAPTURE":
            appendKV(a, "screenshot", "S")
            appendKV(a, "clean shot", "J")
            appendKV(a, "burst", "K")
            appendKV(a, "clean burst", "L")
            appendKV(a, "presentation", "Y")
        case "ALERTS":
            appendKV(a, "late frame", renderer.lateFrameWarning ? "TRUE" : "FALSE", valueColor: renderer.lateFrameWarning ? rmuYellow() : rmuGreen())
            appendKV(a, "vcv", renderer.vcvDisplayStatus(), valueColor: statusColor(renderer.vcvDisplayStatus()))
            appendKV(a, "fallback", stringValue(dataset?["fallback_active"]).uppercased(), valueColor: boolValue(dataset?["fallback_active"]) ? rmuRed() : rmuGreen())
        default:
            appendKV(a, "page", activePage)
        }
        append(a, "\nCLICK A TILE TO OPEN A SUBSYSTEM\n", color: rmuDim())
        append(a, "1/2 toggle left/right panels\n", color: rmuDim())
        append(a, "ESC quit renderer\n", color: rmuDim())
        return a
    }

    func bottomConsoleAttributed(renderer: MetalRenderer, dataset: [String: Any]?, coupling: [String: Any]?) -> NSAttributedString {
        let a = NSMutableAttributedString()
        append(a, "\(activePage) CONSOLE  >  ACTIVE PAGE: \(activePage)\n", color: rmuAmber(), font: titleFont(size: 17))
        append(a, "────────────────────────────────────────────────────────────────────────────────────────────────────────\n", color: rmuDim())
        switch activePage {
        case "HOME": bottomHome(a, renderer: renderer, dataset: dataset, coupling: coupling)
        case "DATA": bottomData(a, renderer: renderer, dataset: dataset)
        case "FIELD": bottomField(a, renderer: renderer)
        case "COUPLING": bottomCoupling(a, renderer: renderer, coupling: coupling)
        case "VCV": bottomVCV(a, renderer: renderer)
        case "NAV": bottomNav(a, renderer: renderer, dataset: dataset)
        case "CAPTURE": bottomCapture(a, renderer: renderer)
        case "ALERTS": bottomAlerts(a, renderer: renderer, dataset: dataset)
        default: bottomHome(a, renderer: renderer, dataset: dataset, coupling: coupling)
        }
        return a
    }

    func bottomHome(_ a: NSMutableAttributedString, renderer: MetalRenderer, dataset: [String: Any]?, coupling: [String: Any]?) {
        appendKV(a, "system", frameLoader.metadataLoaded ? "LIVE" : "WAITING", valueColor: statusColor(frameLoader.metadataLoaded ? "LIVE" : "WAITING"))
        appendKV(a, "fps", String(format: "%.1f", renderer.currentFPS), valueColor: healthColor(label: "fps", value: renderer.currentFPS))
        appendKV(a, "dataset", boolValue(dataset?["loaded"]) ? "LOADED" : "MISSING", valueColor: boolValue(dataset?["loaded"]) ? rmuGreen() : rmuRed())
        appendKV(a, "coupling", renderer.dataCouplingEnabled ? "ACTIVE" : "OFF", valueColor: renderer.dataCouplingEnabled ? rmuGreen() : rmuYellow())
        appendKV(a, "vcv", renderer.vcvDisplayStatus(), valueColor: statusColor(renderer.vcvDisplayStatus()))
        appendKV(a, "behavior", runtimeBehaviorLabel(), valueColor: rmuAmber())
        appendKV(a, "summary", renderer.dataCouplingPanelSummary())
    }

    func bottomData(_ a: NSMutableAttributedString, renderer: MetalRenderer, dataset: [String: Any]?) {
        guard let ds = dataset else { appendKV(a, "dataset", "MISSING", valueColor: rmuRed()); return }
        let state = ds["state"] as? [String: Any] ?? [:]
        appendKV(a, "source", (stringValue(ds["source_csv"]) as NSString).lastPathComponent)
        appendKV(a, "rows", numberString(ds["row_count"], digits: 0))
        appendKV(a, "sample", numberString(ds["sample_index"], digits: 0))
        appendKV(a, "x", numberString(state["x"], digits: 3), valueColor: rmuCyan())
        appendKV(a, "y / depth", numberString(state["y"], digits: 3), valueColor: rmuCyan())
        appendKV(a, "z", numberString(state["z"], digits: 3), valueColor: rmuCyan())
        if let n = state["curvature_density"] as? NSNumber { appendKV(a, "curvature", String(format: "%.3f", n.doubleValue), valueColor: healthColor(label: "curvature", value: n.doubleValue)) }
        if let n = state["temperature_proxy"] as? NSNumber { appendKV(a, "temperature", String(format: "%.3f", n.doubleValue), valueColor: healthColor(label: "temperature", value: n.doubleValue)) }
        if let n = state["higgs_lambda"] as? NSNumber { appendKV(a, "higgs_lambda", String(format: "%.3f", n.doubleValue), valueColor: healthColor(label: "higgs", value: n.doubleValue)) }
        if let n = state["probability_weight"] as? NSNumber { appendKV(a, "probability", String(format: "%.3f", n.doubleValue), valueColor: healthColor(label: "probability", value: n.doubleValue)) }
        appendKV(a, "fallback", stringValue(ds["fallback_active"]).uppercased(), valueColor: boolValue(ds["fallback_active"]) ? rmuRed() : rmuGreen())
        if let reg = ds["registry"] as? [String: Any], let maps = reg["mappings"] as? [String] {
            appendKV(a, "mappings", maps.prefix(5).joined(separator: ", ") + (maps.count > 5 ? ", ..." : ""))
        }
    }

    func bottomField(_ a: NSMutableAttributedString, renderer: MetalRenderer) {
        // RMU_V1_6G_PHYSICS_FIELD_BEHAVIOR_AUTHORITY_PANEL
        appendKV(a, "behavior", renderer.rmuV16GBehaviorHUDSummary(), valueColor: renderer.rmuV16DBehaviorAuthorityActive ? rmuGreen() : rmuAmber())
        appendKV(a, "field auth", renderer.rmuV16GFieldAuthoritySummary(), valueColor: rmuCyan())
        appendKV(a, "field layers", renderer.fieldLayersEnabled ? "ON" : "OFF", valueColor: statusColor(renderer.fieldLayersEnabled ? "ON" : "OFF"))
        appendKV(a, "selected", renderer.selectedFieldLayerName.uppercased(), valueColor: rmuAmber())
        appendKV(a, "selected weight", String(format: "%.2f", renderer.selectedFieldLayerWeight), valueColor: rmuAmber())
        appendKV(a, "recipe", renderer.rmuV16GFieldRecipeSummary())
        for i in 0..<renderer.fieldLayerNames.count {
            let name = renderer.fieldLayerNames[i]
            let val = renderer.fieldLayerWeights[i]
            let enabled = renderer.fieldLayerEnabled[i]
            appendKV(a, name, String(format: "%.2f  %@", val, enabled ? "ON" : "OFF"), valueColor: enabled ? rmuGreen() : rmuDim())
        }
    }

    func bottomCoupling(_ a: NSMutableAttributedString, renderer: MetalRenderer, coupling: [String: Any]?) {
        appendKV(a, "enabled", renderer.dataCouplingEnabled ? "TRUE" : "FALSE", valueColor: renderer.dataCouplingEnabled ? rmuGreen() : rmuYellow())
        appendKV(a, "gain", String(format: "%.2f", renderer.dataCouplingGain), valueColor: rmuAmber())
        appendKV(a, "smooth", String(format: "%.2f", renderer.dataCouplingSmooth))
        appendKV(a, "status", stringValue(coupling?["status"]), valueColor: statusColor(stringValue(coupling?["status"])))
        appendKV(a, "summary", stringValue(coupling?["summary"]))
        if let values = coupling?["values"] as? [String: Any] {
            for key in ["curvature_drive", "temperature_drive", "higgs_drive", "probability_drive", "vertical_drive"] {
                appendKV(a, key, numberString(values[key], digits: 3), valueColor: healthColor(label: key, value: (values[key] as? NSNumber)?.doubleValue ?? 0.0))
            }
        }
    }

    func bottomVCV(_ a: NSMutableAttributedString, renderer: MetalRenderer) {
        appendKV(a, "display", renderer.vcvDisplayStatus(), valueColor: statusColor(renderer.vcvDisplayStatus()))
        appendKV(a, "source", renderer.probabilitySource, valueColor: rmuAmber())
        appendKV(a, "field control", renderer.vcvFieldControlEnabled ? "ON" : "OFF", valueColor: statusColor(renderer.vcvFieldControlEnabled ? "ON" : "OFF"))
        // RMU_V1_6G_HUD_COMPACT_VCV_AUTHORITY_SCHEMA
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
        append(a, renderer.vcvChannelCompactSummary(), color: rmuCyan())
    }

    func bottomNav(_ a: NSMutableAttributedString, renderer: MetalRenderer, dataset: [String: Any]?) {
        let state = dataset?["state"] as? [String: Any] ?? [:]
        appendKV(a, "x / lon drive", numberString(state["x"], digits: 3), valueColor: rmuCyan())
        appendKV(a, "y / depth", numberString(state["y"], digits: 3), valueColor: rmuCyan())
        appendKV(a, "z / lat drive", numberString(state["z"], digits: 3), valueColor: rmuCyan())
        appendKV(a, "rotation", String(format: "%.1f°", renderer.rotationRadians * 180.0 / .pi), valueColor: rmuAmber())
        appendKV(a, "pan", String(format: "%.2f, %.2f", renderer.panX, renderer.panY))
        appendKV(a, "display radius", String(format: "%.2f", renderer.manualWorldRadius ?? frameLoader.worldRadius))
        appendKV(a, "range rings", renderer.curvatureOverlayEnabled ? "ON" : "OFF", valueColor: statusColor(renderer.curvatureOverlayEnabled ? "ON" : "OFF"))
    }

    func bottomCapture(_ a: NSMutableAttributedString, renderer: MetalRenderer) {
        appendKV(a, "window shot", "S")
        appendKV(a, "clean shot", "J")
        appendKV(a, "burst", "K / L")
        appendKV(a, "presentation", renderer.presentationModeEnabled ? "ON" : "OFF", valueColor: statusColor(renderer.presentationModeEnabled ? "ON" : "OFF"))
        appendKV(a, "sample request", "\(frameLoader.renderSampleCount)")
        appendKV(a, "HUD visible", overlaysVisible ? "TRUE" : "FALSE", valueColor: overlaysVisible ? rmuGreen() : rmuYellow())
    }

    func bottomAlerts(_ a: NSMutableAttributedString, renderer: MetalRenderer, dataset: [String: Any]?) {
        if activeAlertCount(renderer: renderer) == 0 { appendKV(a, "system", "NOMINAL", valueColor: rmuGreen()) }
        appendKV(a, "late frame", renderer.lateFrameWarning ? "TRUE" : "FALSE", valueColor: renderer.lateFrameWarning ? rmuYellow() : rmuGreen())
        appendKV(a, "vcv", renderer.vcvDisplayStatus(), valueColor: statusColor(renderer.vcvDisplayStatus()))
        appendKV(a, "dataset fallback", stringValue(dataset?["fallback_active"]).uppercased(), valueColor: boolValue(dataset?["fallback_active"]) ? rmuRed() : rmuGreen())
        appendKV(a, "dataset loaded", stringValue(dataset?["loaded"]).uppercased(), valueColor: boolValue(dataset?["loaded"]) ? rmuGreen() : rmuRed())
    }

    func microNavAttributed(renderer: MetalRenderer, dataset: [String: Any]?) -> NSAttributedString {
        let a = NSMutableAttributedString()
        append(a, "MICRO NAV\n", color: rmuCyan(), font: monoFont(size: 12, weight: .semibold))
        append(a, "      N\n", color: rmuDim())
        append(a, "   ┌─────┐\n", color: rmuDim())
        append(a, "W ─┤  ✦  ├─ E\n", color: rmuTeal())
        append(a, "   └─────┘\n", color: rmuDim())
        append(a, "      S\n", color: rmuDim())
        appendKV(a, "RNG", String(format: "%.2f", renderer.manualWorldRadius ?? frameLoader.worldRadius), unit: "rmu")
        return a
    }

    func depthGaugeAttributed(renderer: MetalRenderer, dataset: [String: Any]?) -> NSAttributedString {
        let a = NSMutableAttributedString()
        let state = dataset?["state"] as? [String: Any] ?? [:]
        let yVal = (state["y"] as? NSNumber)?.doubleValue ?? 0.0
        let tempVal = (state["temperature_proxy"] as? NSNumber)?.doubleValue ?? 0.0
        let bars = max(1, min(10, Int(abs(yVal) * 10.0) + 1))
        append(a, "DEPTH / STATUS\n", color: rmuCyan(), font: monoFont(size: 12, weight: .semibold))
        append(a, String(repeating: "▰", count: bars), color: healthColor(label: "temp", value: tempVal))
        append(a, String(repeating: "▱", count: max(0, 10 - bars)), color: rmuDim())
        append(a, "\n")
        appendKV(a, "y", String(format: "%.3f", yVal), valueColor: rmuCyan())
        appendKV(a, "temp", String(format: "%.3f", tempVal), valueColor: healthColor(label: "temperature", value: tempVal))
        appendKV(a, "status", boolValue(dataset?["fallback_active"]) ? "FALLBACK" : "NOMINAL", valueColor: boolValue(dataset?["fallback_active"]) ? rmuRed() : rmuGreen())
        return a
    }

    func commandBarAttributed(renderer: MetalRenderer) -> NSAttributedString {
        let a = NSMutableAttributedString()
        append(a, "COMMAND LINE  > ", color: rmuDim())
        append(a, "SHIFT+M cycle pages", color: rmuAmber())
        append(a, "   LOG LEVEL ", color: rmuDim())
        append(a, "INFO", color: rmuCyan())
        append(a, "   CPU --%   GPU --%   MEM --   NET LOCAL LOOPBACK", color: rmuDim())
        return a
    }
}



// RMU_V1_4B8_HUD_LABEL_SYNC_HELPER
func rmuVCVDisplayLabel(_ channel: Int, fallback: String) -> String {
    if channel == 13 { return "gravity_well_position" }
    if channel == 14 { return "gravity_well_strength" }
    return fallback
}

// RMU_V1_9M_COLOR_ENGINE_PATCH_INSTALLED
final class MetalRenderer: NSObject, MTKViewDelegate {
    let device: MTLDevice
    let commandQueue: MTLCommandQueue
    let pipelineState: MTLRenderPipelineState
    let frameLoader: ParticleFrameLoader
    let projectRoot: String

    var particleBuffer: MTLBuffer?

    // RMU v1.3F6: real independent geospatial particle buffers.
    // base = original crab-data position, live = simulated position, velocity = persistent per-particle motion.
    var baseParticleBuffer: MTLBuffer?
    var liveParticleBuffer: MTLBuffer?
    var velocityParticleBuffer: MTLBuffer?
    var lastUploadedParticleCount: Int = 0
    var lastUploadedModificationDate: Date? = nil
    var computePipelineState: MTLComputePipelineState?
    var geospatialDamping: Float = 0.965
    var geospatialSimDt: Float = 1.0 / 60.0

    var trailBuffers: [MTLBuffer] = []
    var trailCounts: [Int] = []

    var frameIndex: Int = 0
    var lastFPSPrintTime = CFAbsoluteTimeGetCurrent()
    var framesSincePrint = 0
    var currentFPS: Double = 0.0
    var currentFrameTimeMS: Double = 0.0
    var lateFrameWarning: Bool = false

    var pointSize: Float = 2.0
    var manualWorldRadius: Float? = nil
    var panX: Float = 0.0
    var panY: Float = 0.0
    var rotationRadians: Float = 0.0
    var colorMode: Int32 = 0

    var autoCameraEnabled = false
    var autoCameraPhase: Float = 0.0
    var lastVisualStateMessage = "none"
    var activeVisualStateName = "manual"
    var activeScenePresetName = "manual"

    var vcvStatus = "not detected"
    var probabilitySource = "internal"
    var vcvLastUpdateUnix: Double = 0.0
    var vcvLastReadTime: Double = 0.0
    var vcvFieldControlEnabled = true // RMU_V1_5A9: VCV control defaults ON; state freshness decides ACTIVE/STALE
    var vcvLastValues = "none"
    var vcvMonitorVisible = true
    var vcvSmoothingAmount: Float = 0.22
    var vcvChannelLabels: [String] = [
        "probability", "radial", "orbital", "vertical", "turbulence", "shell", "color", "scene",
        "particle_speed", "particle_mass", "particle_turbulence", "particle_cohesion", "gravity_well_position", "gravity_well_strength", "aux_15", "aux_16",

        "aux_17", "aux_18", "aux_19", "aux_20", "aux_21", "aux_22", "aux_23", "aux_24",
        "aux_25", "aux_26", "aux_27", "aux_28", "aux_29", "aux_30", "aux_31", "aux_32"
    ]
    var vcvChannelTargets: [String] = [
        "probability_value", "field_layer_weights[0]", "field_layer_weights[1]", "field_layer_weights[2]", "field_layer_weights[3]", "field_layer_weights[4]", "color_mode", "scene_index",
        "particle_speed", "particle_mass", "particle_turbulence", "particle_cohesion", "gravity_well_position", "gravity_well_strength", "aux_15", "aux_16",
        "aux_17", "aux_18", "aux_19", "aux_20", "aux_21", "aux_22", "aux_23", "aux_24",
        "aux_25", "aux_26", "aux_27", "aux_28", "aux_29", "aux_30", "aux_31", "aux_32"
    ]
    var vcvChannelEnabled: [Bool] = Array(repeating: true, count: 32)
    var vcvChannelValues: [Float] = [0, 0, 0, 0, 0, 0, 0, 0, 1.0, 1.0] + Array(repeating: 0.0, count: 22)

    // RMU_V1_5C_POLY_SPECIES_CONTROL_STATE
    var particleSpeciesProbability: [Float] = Array(repeating: 0.0, count: 22)
    var particleSpeciesColorMode: [Int32] = Array(repeating: 0, count: 22)
    var particleSpeciesSpeed: [Float] = Array(repeating: 0.0, count: 22)
    var particleSpeciesMass: [Float] = Array(repeating: 2.6, count: 22)
    var particleSpeciesMassRaw: [Float] = Array(repeating: 0.0, count: 22)
    var particleSpeciesTurbulence: [Float] = Array(repeating: 0.0, count: 22)
    var particleSpeciesCohesion: [Float] = Array(repeating: 0.0, count: 22)
    var particleSpeciesColorHSL: [Float] = Array(repeating: 0.0, count: 22 * 3)
    var particleSpeciesColorRGB: [Float] = Array(repeating: 1.0, count: 22 * 3)
    var particleSpeciesProbabilityVoiceCount: Int = 0
    var particleSpeciesColorModeVoiceCount: Int = 0
    var particleSpeciesSpeedVoiceCount: Int = 0
    var particleSpeciesMassVoiceCount: Int = 0
    var particleSpeciesTurbulenceVoiceCount: Int = 0
    var particleSpeciesCohesionVoiceCount: Int = 0
    var particleSpeciesColorVoiceCount: Int = 0
    var gravityWellPositionVec4: [Float] = Array(repeating: 0.0, count: 4)
    var vcvSceneIndex: Int = 1


    var vcvRawChannelValues: [Float] = Array(repeating: 0.0, count: 32)
    // RMU_V1_6B_SPECIES_IDENTITY_STATE_BEGIN
    var rmuV16BSpeciesIdentityLoaded: Bool = false
    var rmuV16BSpeciesIdentityRecordCount: Int = 0
    var rmuV16BSpeciesIdentityParticleCount: Int = 0
    var rmuV16BSpeciesIdentityStatus: String = "not loaded"
    var rmuV16BSpeciesIdentityLastError: String = "none"
    var rmuV16BSpeciesControlEnabled: Float = 1.0
    var rmuV16BSpeciesIDCPU: [UInt32] = []
    var rmuV16BFamilyIDCPU: [UInt32] = []
    var rmuV16BSpeciesWeightCPU: [Float] = []
    var rmuV16BSpeciesIDBuffer: MTLBuffer? = nil
    var rmuV16BFamilyIDBuffer: MTLBuffer? = nil
    var rmuV16BSpeciesWeightBuffer: MTLBuffer? = nil
    // RMU_V1_6B_SPECIES_IDENTITY_STATE_END
    // RMU_V1_5F_RENDERER_VCV_AUTHORITY_FIX
    var vcvSafeModeEnabled = false

    // RMU_V1_5G_RENDERER_SCENE_COLOR_FIELD_AUTHORITY_STATE
    var vcvAuthoritySceneIndex: Int = 1
    var vcvAuthorityColorMode: Int32 = 0
    var vcvAuthorityFieldLayerIndex: Int = 0
    var vcvAuthorityLastAppliedUnix: Double = 0.0

    // RMU_V1_5E_RENDERER_HUD_VCV_PANEL_CLEANUP_STATE
    var vcvCompactHUDMode: Bool = true
    var vcvDetailPanelVisible: Bool = false
    var vcvDetailPageIndex: Int = 0

    var particleSpeciesProbabilityVoiceCountA: Int = 0
    var particleSpeciesProbabilityVoiceCountB: Int = 0
    var particleSpeciesColorModeVoiceCountA: Int = 0
    var particleSpeciesColorModeVoiceCountB: Int = 0
    var particleSpeciesSpeedVoiceCountA: Int = 0
    var particleSpeciesSpeedVoiceCountB: Int = 0
    var particleSpeciesMassVoiceCountA: Int = 0
    var particleSpeciesMassVoiceCountB: Int = 0
    var particleSpeciesTurbulenceVoiceCountA: Int = 0
    var particleSpeciesTurbulenceVoiceCountB: Int = 0
    var particleSpeciesCohesionVoiceCountA: Int = 0
    var particleSpeciesCohesionVoiceCountB: Int = 0
    var particleSpeciesColorVoiceCountA: Int = 0
    var particleSpeciesColorVoiceCountB: Int = 0
    var vcvLastClampEvent = "none"

    var trailsEnabled = false
    var trailLength = 12
    var trailAlphaFloor: Float = 0.08
    var trailAlphaCeiling: Float = 0.42

    var gridEnabled = false
    var centerMarkerEnabled = true
    var horizonRingEnabled = true
    var curvatureOverlayEnabled = true
    var probabilityOverlayEnabled = true
    var presentationModeEnabled = false

    var fieldLayersEnabled = true
    var selectedFieldLayerIndex = 1
    var fieldLayerNames: [String] = ["radial", "orbital", "vertical", "turbulence", "shell"]
    var fieldLayerEnabled: [Bool] = [true, true, true, false, true]
    var fieldLayerWeights: [Float] = [0.03, 0.02, 1.65, 2.25, 0.00] // RMU_V1_11A_PHASE3C_DISABLE_DISC_SNAP: volumetric field defaults
    var fieldPhase: Float = 0.0

    // RMU_V1_3D2_RENDERER_BEHAVIOR_STATE
    // Renderer-authoritative geospatial behavior transforms.
    // SPACE gates these transforms. When paused, the crab CSV field remains stable.
    var behaviorEffectCode: Int32 = 1
    var geospatialSimulationPaused: Int32 = 1
    var geospatialBehaviorEnabled: Bool = true
    var geospatialRespawnOnCapture: Bool = false

    // RMU_V1_6D2_BEHAVIOR_APPLY_AUTHORITY_STATE
    var rmuV16DBehaviorAuthorityActive: Bool = false
    var rmuV16DBehaviorAuthorityCode: Int32 = 1
    var rmuV16DBehaviorAuthorityGate: Float = 0.0

    // RMU v1.3F6: Lorenz/VCV bipolar controls.
    // /ch/9  particle_speed: -5V..+5V -> -3.0..+3.0 motion scalar.
    // /ch/10 particle_mass:  -5V..+5V -> 0.20..5.00 positive inertia.
    // Anchor tether is retired from live motion; crab geography is the starting condition.
    var geospatialParticleSpeed: Float = 1.0
    var geospatialParticleMass: Float = 1.0
    var geospatialParticleTurbulence: Float = 0.0
    var geospatialParticleCohesion: Float = 0.0
    var geospatialGravityWellPosition: Float = 0.0
    var geospatialGravityWellStrength: Float = 6.0
    var geospatialAnchorStrength: Float = 0.0  // deprecated compatibility field
    var geospatialBehaviorGain: Float = 1.0
    var geospatialDisplayParticleLimit: Int = 45000

    // v1.2A: dataset-driven simulation/field coupling.
    // This is intentionally separate from the VCV /ch/1-/ch/8 contract.
    var dataCouplingEnabled = true
    var dataCouplingGain: Float = 1.0
    var dataCouplingSmooth: Float = 0.15
    var dataCouplingLastReadTime: Double = 0.0
    var dataCouplingLoaded = false
    var dataCouplingFallbackActive = true
    var dataCouplingStatus = "waiting"
    var dataCouplingFallbackReason = "not loaded"
    var dataCouplingSource = "none"
    var dataCouplingSummary = "dataset coupling waiting"
    var dataCouplingValues: [String: Float] = [
        "curvature_drive": 0.0,
        "temperature_drive": 0.25,
        "higgs_drive": 0.35,
        "probability_drive": 0.0,
        "vertical_drive": 0.0
    ]
    var dataCouplingTargets: [Float] = [0.25, 1.00, 0.10, 0.05, 0.20]

    var gridBuffer: MTLBuffer?
    var centerBuffer: MTLBuffer?
    var horizonBuffer: MTLBuffer?
    var curvatureRingBuffers: [MTLBuffer] = []
    var curvatureRingCounts: [Int] = []
    var probabilityHaloBuffer: MTLBuffer?
    var probabilityHaloCount: Int = 0

    weak var hud: HUDOverlayController?

    // RMU_V1_5E_RENDERER_HUD_VCV_PANEL_CLEANUP_HELPERS
    func rmuBankStatus(_ a: Int, _ b: Int) -> String {
        return "\(a)+\(b)"
    }

    func rmuBankStatusLine() -> String {
        return "P \(rmuBankStatus(particleSpeciesProbabilityVoiceCountA, particleSpeciesProbabilityVoiceCountB))  " +
            "CMode \(rmuBankStatus(particleSpeciesColorModeVoiceCountA, particleSpeciesColorModeVoiceCountB))  " +
            "S \(rmuBankStatus(particleSpeciesSpeedVoiceCountA, particleSpeciesSpeedVoiceCountB))  " +
            "M \(rmuBankStatus(particleSpeciesMassVoiceCountA, particleSpeciesMassVoiceCountB))  " +
            "T \(rmuBankStatus(particleSpeciesTurbulenceVoiceCountA, particleSpeciesTurbulenceVoiceCountB))  " +
            "Coh \(rmuBankStatus(particleSpeciesCohesionVoiceCountA, particleSpeciesCohesionVoiceCountB))  " +
            "Color \(rmuBankStatus(particleSpeciesColorVoiceCountA, particleSpeciesColorVoiceCountB))"
    }

    func rmuGravityVec4Summary() -> String {
        let x = gravityWellPositionVec4.count > 0 ? gravityWellPositionVec4[0] : 0.0
        let y = gravityWellPositionVec4.count > 1 ? gravityWellPositionVec4[1] : 0.0
        let z = gravityWellPositionVec4.count > 2 ? gravityWellPositionVec4[2] : 0.0
        let t = gravityWellPositionVec4.count > 3 ? gravityWellPositionVec4[3] : 0.0
        return String(format: "G4 %.2f %.2f %.2f %.2f", x, y, z, t)
    }

    // RMU_V1_9M_COLOR_ENGINE_HELPERS
    func rmuColorModeDisplayName(_ mode: Int32) -> String {
        switch Int(mode) {
        case 0: return "white_cluster"
        case 1: return "species_family"
        case 2: return "depth_temperature"
        case 3: return "field_energy"
        case 4: return "curvature_density"
        case 5: return "higgs_lambda"
        case 6: return "probability_weight"
        case 7: return "vcv_color_bank"
        case 8: return "sonar_heat"
        case 9: return "pioneer_green"
        case 10: return "amber_scope"
        default: return "mode \(mode)"
        }
    }

    func rmuVCVColorModeDisplayName() -> String {
        return rmuColorModeDisplayName(vcvAuthorityColorMode)
    }

    // RMU_V1_5G_RENDERER_SCENE_COLOR_FIELD_AUTHORITY_HELPERS
    func rmuApplyVCVSceneAuthority(_ scene: Int) {
        let clampedScene = max(1, min(6, scene))
        vcvAuthoritySceneIndex = clampedScene
        vcvSceneIndex = clampedScene

        let layerIndex = max(0, min(max(0, fieldLayerWeights.count - 1), clampedScene - 1))
        vcvAuthorityFieldLayerIndex = layerIndex

        if fieldLayerWeights.count > 0 {
            selectedFieldLayerIndex = layerIndex
        }

        // RMU_V1_6D2_REMOVE_SCENE_BEHAVIOR_STOMP
        // Scene authority controls selected scene and field layer only.
        // Behavior authority belongs to Shift+E manually or /ch/18 when /ch/19 is gated high.
    }

    func rmuApplyVCVColorAuthority(_ mode: Int32) {
        let clampedMode = max(Int32(0), min(Int32(10), mode))
        vcvAuthorityColorMode = clampedMode
        colorMode = clampedMode

        if vcvChannelValues.count > 6 {
            vcvChannelValues[6] = Float(clampedMode)
        }
        if vcvRawChannelValues.count > 6 {
            vcvRawChannelValues[6] = Float(clampedMode)
        }

        lastVisualStateMessage = "color mode \(clampedMode) \(rmuColorModeDisplayName(clampedMode))"
    }

    func rmuApplyVCVFieldLayerWeights(_ weights: [Float]) {
        if weights.isEmpty { return }
        let count = min(weights.count, fieldLayerWeights.count)
        if count <= 0 { return }
        for i in 0..<count {
            fieldLayerWeights[i] = weights[i]
        }
        selectedFieldLayerIndex = max(0, min(max(0, fieldLayerWeights.count - 1), vcvAuthorityFieldLayerIndex))
    }

    func rmuVCVCompactStatusLine() -> String {
        // RMU_V1_6G_COMPACT_VCV_STATUS_LINE
        return "\(rmuV16GVCVAuthoritySummary()) | color \(rmuVCVColorModeDisplayName()) | \(rmuBankStatusLine()) | \(rmuGravityVec4Summary())"
    }

    func rmuVCVDetailPageTitle() -> String {
        switch max(0, min(4, vcvDetailPageIndex)) {
        case 0: return "VCV PAGE 1: /ch/1-/ch/9"
        case 1: return "VCV PAGE 2: /ch/10-/ch/17"
        case 2: return "VCV PAGE 3: /ch/28-/ch/32"
        case 3: return "VCV PAGE 4: Species P/S/M/T/C"
        case 4: return "VCV PAGE 5: Gravity + Field Layers"
        default: return "VCV PAGE"
        }
    }

    var selectedFieldLayerName: String {
        return fieldLayerNames[max(0, min(selectedFieldLayerIndex, fieldLayerNames.count - 1))]
    }

    var selectedFieldLayerWeight: Float {
        return fieldLayerWeights[max(0, min(selectedFieldLayerIndex, fieldLayerWeights.count - 1))]
    }

    var colorModeName: String {
        return rmuColorModeDisplayName(colorMode)
    }

    init?(view: MTKView, projectRoot: String) {
        guard let device = view.device,
              let commandQueue = device.makeCommandQueue() else { return nil }

        self.device = device
        self.commandQueue = commandQueue
        self.projectRoot = projectRoot
        self.frameLoader = ParticleFrameLoader(projectRoot: projectRoot)

        let shaderSource = """
        #include <metal_stdlib>
        using namespace metal;

        struct Particle { float3 position; };

        struct VertexOut {
            float4 position [[position]];
            float4 color;
            float pointSize [[point_size]];
        };

        vertex VertexOut vertex_main(
            const device Particle *particles [[buffer(0)]],
            constant float &worldRadius [[buffer(1)]],
            constant float &pointSize [[buffer(2)]],
            constant float &rotationRadians [[buffer(3)]],
            constant float2 &pan [[buffer(4)]],
            constant int &colorMode [[buffer(5)]],
            constant float &alpha [[buffer(6)]],
            constant int &overlayMode [[buffer(7)]],
            constant int &fieldLayersEnabled [[buffer(8)]],
            constant float4 &fieldWeightsA [[buffer(9)]],
            constant float &fieldWeightShell [[buffer(10)]],
            constant int4 &fieldEnabledA [[buffer(11)]],
            constant int &fieldEnabledShell [[buffer(12)]],
            constant float &fieldPhase [[buffer(13)]],
            constant int &behaviorEffectCode [[buffer(14)]],
            constant int &geospatialPaused [[buffer(15)]],
            constant float &anchorStrength [[buffer(16)]],
            // RMU_V1_6C_VERTEX_SPECIES_COLOR_ARGS_BEGIN
            constant uint *rmuV16CRenderSpeciesIDs [[buffer(17)]],
            constant float *rmuV16CRenderColorBank [[buffer(18)]],
            constant float &rmuV16CRenderSpeciesColorEnabled [[buffer(19)]],
            // RMU_V1_6C_VERTEX_SPECIES_COLOR_ARGS_END
            uint vertexID [[vertex_id]]
        ) {
            Particle p = particles[vertexID];
            float3 fp = p.position;
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
            // RMU_V1_6C_VERTEX_SPECIES_COLOR_SAMPLE_END

            float baseRadius = max(length(fp), 0.0001);
            float3 dir = fp / baseRadius;
            float shellMask = 0.0;

            if (fieldLayersEnabled == 1 && overlayMode == 0) {
                if (fieldEnabledA.x == 1) {
                    fp += -dir * (fieldWeightsA.x * 0.16);
                }

                if (fieldEnabledA.y == 1) {
                    float3 tangent = normalize(float3(-fp.z, 0.0, fp.x) + float3(0.0001, 0.0, 0.0001));
                    fp += tangent * (fieldWeightsA.y * 0.14);
                }

                if (fieldEnabledA.z == 1) {
                    float lift = sin(baseRadius * 2.1 + fieldPhase) * 0.22;
                    fp.y += lift * fieldWeightsA.z;
                }

                if (fieldEnabledA.w == 1) {
                    float n = sin(fp.x * 3.1 + fieldPhase) * cos(fp.y * 2.7 - fieldPhase) * sin(fp.z * 2.1 + fieldPhase * 0.5);
                    fp += float3(n * 0.10, n * 0.06, n * 0.11) * fieldWeightsA.w;
                }

                if (false) { // RMU_V1_11A_PHASE3C_DISABLE_DISC_SNAP: shell wall disabled for open volumetric domain
                    float shellRadius = worldRadius * 0.72;
                    float shellWidth = max(worldRadius * 0.08, 0.05);
                    float q = (baseRadius - shellRadius) / shellWidth;
                    shellMask = exp(-(q * q)) * fieldWeightShell;
                    fp += dir * shellMask * 0.10;
                }
            }

            // RMU_V1_3E_RUNTIME_BOUND_BEHAVIOR_TRANSFORM
            // Renderer-authoritative geospatial behavior engine.
            if (overlayMode == 0 && geospatialPaused == 0 && behaviorEffectCode != 0) {
                float runT = max(fieldPhase, 0.0);
                float grow = clamp(runT * 0.18, 0.0, 1.0);
                float orbitPulse = sin(runT * 1.35 + baseRadius * 2.0);
                float wave = sin(baseRadius * 3.2 - runT * 2.4);
                float3 tangent = normalize(float3(-fp.z, 0.0, fp.x) + float3(0.0001, 0.0, 0.0001));

                int effectiveBehaviorCode = behaviorEffectCode;

            if (effectiveBehaviorCode == 1) {
                    float theta = 0.18 * grow;
                    float cs = cos(theta);
                    float sn = sin(theta);
                    fp.xz = float2(fp.x * cs - fp.z * sn, fp.x * sn + fp.z * cs);
                    fp += tangent * (0.10 + 0.05 * orbitPulse);
                    fp += dir * (0.035 * sin(runT + baseRadius * 1.7));
                } else if (effectiveBehaviorCode == 2) {
                    float collapse = clamp(grow * 0.82, 0.0, 0.88);
                    fp *= (1.0 - collapse);
                    fp += tangent * (0.18 * (1.0 - collapse));
                } else if (effectiveBehaviorCode == 3) {
                    float theta = 1.85 * grow + baseRadius * 0.08;
                    float cs = cos(theta);
                    float sn = sin(theta);
                    fp.xz = float2(fp.x * cs - fp.z * sn, fp.x * sn + fp.z * cs);
                    fp.y *= mix(1.0, 0.08, grow);
                    fp += tangent * (0.22 + 0.08 * orbitPulse);
                } else if (effectiveBehaviorCode == 4) {
                    fp += dir * (0.55 * grow + 0.30 * wave);
                    fp.y += 0.38 * sin(runT * 2.1 + baseRadius * 2.4);
                } else if (effectiveBehaviorCode == 5) {
                    float collapse = clamp(grow * 1.05, 0.0, 0.96);
                    fp *= (1.0 - collapse);
                    fp += tangent * (0.07 * (1.0 - collapse));
                }

                baseRadius = max(length(fp), 0.0001);
                dir = fp / baseRadius;
            }

            float c = cos(rotationRadians);
            float s = sin(rotationRadians);
            float rx = fp.x * c - fp.z * s;
            float rz = fp.x * s + fp.z * c;

            float x = clamp((rx / worldRadius) + pan.x, -1.5, 1.5);
            float y = clamp((rz / worldRadius) + pan.y, -1.5, 1.5);
            float depth = clamp((fp.y / worldRadius) * 0.5 + 0.5, 0.0, 1.0);
            float radial = clamp(length(float2(rx, rz)) / worldRadius, 0.0, 1.0);

            VertexOut out;
            out.position = float4(x, y, 0.0, 1.0);

            // RMU_V1_9M_COLOR_ENGINE_SHADER_BEGIN
            float3 familyBase = float3(0.72, 0.90, 1.0);
            float speciesShift = float(rmuV16CSpeciesID % 6u) / 5.0;
            uint rmuFamily = 0u;
            if (rmuV16CSpeciesID == 0u) {
                rmuFamily = 0u;                       // crab / data baseline
            } else if (rmuV16CSpeciesID == 1u || rmuV16CSpeciesID == 2u || rmuV16CSpeciesID == 11u || rmuV16CSpeciesID == 12u) {
                rmuFamily = 1u;                       // leptons
            } else if (rmuV16CSpeciesID == 3u || rmuV16CSpeciesID == 13u || rmuV16CSpeciesID == 14u) {
                rmuFamily = 2u;                       // neutrinos
            } else if (rmuV16CSpeciesID == 4u || rmuV16CSpeciesID == 5u || rmuV16CSpeciesID == 15u || rmuV16CSpeciesID == 16u || rmuV16CSpeciesID == 17u || rmuV16CSpeciesID == 18u) {
                rmuFamily = 3u;                       // quarks
            } else if (rmuV16CSpeciesID == 6u || rmuV16CSpeciesID == 7u || rmuV16CSpeciesID == 8u || rmuV16CSpeciesID == 19u || rmuV16CSpeciesID == 20u) {
                rmuFamily = 4u;                       // boson / field / Higgs-like
            } else {
                rmuFamily = 5u;                       // hadron / meson-like
            }

            if (rmuFamily == 0u) { familyBase = float3(0.88, 0.96, 1.0); }
            else if (rmuFamily == 1u) { familyBase = float3(0.15, 0.85, 1.0); }
            else if (rmuFamily == 2u) { familyBase = float3(0.45, 0.35, 1.0); }
            else if (rmuFamily == 3u) { familyBase = float3(1.0, 0.34 + 0.30 * speciesShift, 0.10); }
            else if (rmuFamily == 4u) { familyBase = float3(0.10 + 0.55 * speciesShift, 1.0, 0.35 + 0.35 * speciesShift); }
            else { familyBase = float3(1.0, 0.62, 0.18 + 0.24 * speciesShift); }

            float fieldEnergy = clamp((fieldWeightsA.x + fieldWeightsA.y + fieldWeightsA.z + fieldWeightsA.w + fieldWeightShell) / 9.0, 0.0, 1.0);
            float curvatureBand = 0.5 + 0.5 * sin(radial * 34.0 + fieldPhase * 0.65);
            float higgsWave = 0.5 + 0.5 * sin(depth * 9.0 + radial * 14.0 + fieldPhase * 0.55);
            float probabilityWave = 0.5 + 0.5 * sin(radial * 22.0 - fieldPhase * 1.35 + depth * 7.0);
            float sonarStripe = smoothstep(0.45, 1.0, 0.5 + 0.5 * sin((1.0 - depth) * 30.0 + radial * 17.0 + fieldPhase * 1.8));

            if (overlayMode == 1) {
                out.color = float4(0.18, 0.35, 0.65, alpha);
            } else if (overlayMode == 2) {
                out.color = float4(0.30, 0.75, 1.0, alpha);
            } else if (overlayMode == 3) {
                out.color = float4(1.0, 0.55, 0.18, alpha);
            } else if (overlayMode == 4) {
                float pulse = 0.65 + 0.35 * sin(fieldPhase + radial * 18.0);
                out.color = float4(0.18 + pulse * 0.25, 0.85, 1.0, alpha);
            } else if (overlayMode == 5) {
                float heat = 0.5 + 0.5 * sin(fieldPhase * 1.7 + radial * 24.0);
                out.color = float4(1.0, 0.40 + heat * 0.35, 0.10, alpha);
            } else if (colorMode == 0) {
                out.color = float4(0.92, 0.97, 1.0, alpha);
            } else if (colorMode == 1) {
                float3 speciesAccent = normalize(familyBase + float3(0.10 * speciesShift, 0.06 * sin(speciesShift * 6.28318), 0.08 * cos(speciesShift * 6.28318)));
                out.color = float4(mix(familyBase, speciesAccent, 0.45), alpha);
            } else if (colorMode == 2) {
                out.color = float4(0.10 + depth * 0.95, 0.22 + depth * 0.55, 1.0 - depth * 0.82, alpha);
            } else if (colorMode == 3) {
                out.color = float4(0.10 + fieldEnergy * 0.90, 0.30 + fieldEnergy * 0.65, 0.95 - fieldEnergy * 0.55, alpha);
            } else if (colorMode == 4) {
                out.color = float4(0.12 + curvatureBand * 0.90, 0.95 - curvatureBand * 0.55, 0.28 + curvatureBand * 0.30, alpha);
            } else if (colorMode == 5) {
                out.color = float4(0.35 + higgsWave * 0.65, 0.10 + (1.0 - higgsWave) * 0.55, 1.0, alpha);
            } else if (colorMode == 6) {
                out.color = float4(0.18 + probabilityWave * 0.45, 1.0, 0.22 + (1.0 - probabilityWave) * 0.55, alpha);
            } else if (colorMode == 7) {
                out.color = float4(rmuV16CSpeciesColor, alpha);
            } else if (colorMode == 8) {
                out.color = float4(0.10 + sonarStripe * 0.95, 0.24 + sonarStripe * 0.62, 0.95 - sonarStripe * 0.88, alpha);
            } else if (colorMode == 9) {
                float glow = 0.55 + 0.45 * sin(fieldPhase + radial * 18.0 + depth * 4.0);
                out.color = float4(0.05 + glow * 0.18, 0.72 + glow * 0.28, 0.34 + glow * 0.26, alpha);
            } else if (colorMode == 10) {
                float glow = 0.60 + 0.40 * sin(fieldPhase * 0.9 + radial * 16.0);
                out.color = float4(1.0, 0.48 + glow * 0.32, 0.10 + glow * 0.10, alpha);
            } else {
                out.color = float4(0.92, 0.97, 1.0, alpha);
            }
            // RMU_V1_9M_COLOR_ENGINE_SHADER_END

            if (fieldLayersEnabled == 1 && overlayMode == 0 && fieldEnabledShell == 1) {
                out.color.rgb = min(out.color.rgb + float3(shellMask * 0.35, shellMask * 0.25, shellMask * 0.12), float3(1.0, 1.0, 1.0));
            }

            out.pointSize = pointSize;
            return out;
        }

        kernel void update_geospatial_particles(
            const device Particle *baseParticles [[buffer(0)]],
            device Particle *liveParticles [[buffer(1)]],
            device Particle *velocityParticles [[buffer(2)]],
            constant uint &particleCount [[buffer(3)]],
            constant float &dt [[buffer(4)]],
            constant int &behaviorEffectCode [[buffer(5)]],
            constant float &particleSpeed [[buffer(6)]],
            constant float &damping [[buffer(7)]],
            constant float4 &fieldWeightsA [[buffer(8)]],
            constant float &fieldWeightShell [[buffer(9)]],
            constant float &phase [[buffer(10)]],
            constant float &particleMass [[buffer(11)]],
            constant float &particleTurbulence [[buffer(12)]],
            constant float &particleCohesion [[buffer(13)]],
            constant int &behaviorEnabled [[buffer(14)]],
            constant int &respawnOnCapture [[buffer(15)]],
            constant float &gravityWellPosition [[buffer(18)]],
            constant float &gravityWellStrength [[buffer(19)]],
            // RMU_V1_6B_SHADER_SPECIES_ARGS_BEGIN
            constant uint *rmuV16BSpeciesIDs [[buffer(20)]],
            constant uint *rmuV16BFamilyIDs [[buffer(21)]],
            constant float *rmuV16BSpeciesWeights [[buffer(22)]],
            constant float *rmuV16BProbabilityBank [[buffer(23)]],
            constant float *rmuV16BSpeedBank [[buffer(24)]],
            constant float *rmuV16BMassBank [[buffer(25)]],
            constant float *rmuV16BTurbulenceBank [[buffer(26)]],
            constant float *rmuV16BCohesionBank [[buffer(27)]],
            constant float *rmuV16BColorBank [[buffer(28)]],
            constant float &rmuV16BSpeciesControlEnabled [[buffer(30)]],
            // RMU_V1_6B_SHADER_SPECIES_ARGS_END
            uint id [[thread_position_in_grid]]
        ) {
            if (id >= particleCount) { return; }

            // RMU_V1_6B_SHADER_EFFECTIVE_VALUES_BEGIN
            uint rmuV16BSpeciesID = 0;
            uint rmuV16BFamilyID = 0;
            float rmuV16BSpeciesWeight = 1.0;
            float rmuV16BEffectiveProbability = 1.0;
            float rmuV16BEffectiveSpeed = particleSpeed;
            float rmuV16BEffectiveMass = particleMass;
            float rmuV16BEffectiveTurbulence = particleTurbulence;
            float rmuV16BEffectiveCohesion = particleCohesion;
            float3 rmuV16BEffectiveColor = float3(1.0, 1.0, 1.0);
            if (rmuV16BSpeciesControlEnabled > 0.5) {
                rmuV16BSpeciesID = min(rmuV16BSpeciesIDs[id], 21u);
                rmuV16BFamilyID = min(rmuV16BFamilyIDs[id], 6u);
                rmuV16BSpeciesWeight = clamp(rmuV16BSpeciesWeights[id], 0.0, 1.0);
                rmuV16BEffectiveProbability = clamp(rmuV16BProbabilityBank[rmuV16BSpeciesID], 0.0, 1.0);
                rmuV16BEffectiveSpeed = mix(particleSpeed, rmuV16BSpeedBank[rmuV16BSpeciesID], rmuV16BSpeciesWeight);
                rmuV16BEffectiveMass = max(0.05, mix(particleMass, rmuV16BMassBank[rmuV16BSpeciesID], rmuV16BSpeciesWeight));
                rmuV16BEffectiveTurbulence = mix(particleTurbulence, rmuV16BTurbulenceBank[rmuV16BSpeciesID], rmuV16BSpeciesWeight);
                rmuV16BEffectiveCohesion = mix(particleCohesion, rmuV16BCohesionBank[rmuV16BSpeciesID], rmuV16BSpeciesWeight);
                uint rmuV16BColorBase = rmuV16BSpeciesID * 3u;
                rmuV16BEffectiveColor = float3(rmuV16BColorBank[rmuV16BColorBase + 0u], rmuV16BColorBank[rmuV16BColorBase + 1u], rmuV16BColorBank[rmuV16BColorBase + 2u]);
            }
            float rmuV16BJitter = (fract(sin(float(id + rmuV16BSpeciesID * 131u) * 12.9898) * 43758.5453) - 0.5);
            // RMU_V1_6B_SHADER_EFFECTIVE_VALUES_END

            float3 base = baseParticles[id].position;
            float3 pos = liveParticles[id].position;
            float3 vel = velocityParticles[id].position;

            float r = max(length(pos), 0.0001);
            float3 dir = pos / r;
            float3 baseDir = normalize(base + float3(0.0001, 0.0001, 0.0001));
            float3 tangent = normalize(float3(-pos.z, 0.0, pos.x) + float3(0.0001, 0.0, 0.0001));

            float seed = fract(sin((float(id) + 1.0) * 12.9898) * 43758.5453);
            float seed2 = fract(sin((float(id) + 17.0) * 78.233) * 23454.123);
            float seed3 = fract(sin((float(id) + 43.0) * 31.416) * 9917.777);
            float particleGain = 0.35 + seed3 * 1.65;
            float localPhase = phase * (0.75 + seed * 1.75) + seed2 * 6.2831853;

            float radialW = fieldWeightsA.x;
            float orbitalW = fieldWeightsA.y;
            float verticalW = fieldWeightsA.z;
            float turbW = fieldWeightsA.w;
            float shellW = fieldWeightShell;

            float3 force = float3(0.0);
            float speedScalar = clamp(rmuV16BEffectiveSpeed, -3.0, 3.0);
            float massScalar = max(rmuV16BEffectiveMass, 0.20);
            float turbulenceScalar = clamp(rmuV16BEffectiveTurbulence, 0.0, 2.5);
            float cohesionScalar = clamp(particleCohesion, 0.0, 3.0);

            // RMU_V1_4A_PARTICLE_SPECIES_ARCHITECTURE
            // Deterministic species assignment for the first species-aware GPU pass.
            // Full species_id buffers should replace id%22 in v1.4B.
            uint speciesID = id % 22;
            float speciesMassResponse = 1.0;
            float speciesSpeedResponse = 1.0;
            float speciesTurbulenceResponse = 1.0;
            float speciesCohesionResponse = 1.0;
            float speciesStrongCoupling = 0.15;
            float speciesCharge = 0.0;
            float speciesCurvatureCoupling = 0.55;

            if (speciesID == 1) { speciesMassResponse = 0.65; speciesSpeedResponse = 1.35; speciesTurbulenceResponse = 1.15; speciesCohesionResponse = 0.10; speciesStrongCoupling = 0.0; speciesCharge = -1.0; speciesCurvatureCoupling = 0.20; }
            else if (speciesID == 2) { speciesMassResponse = 0.65; speciesSpeedResponse = 1.35; speciesTurbulenceResponse = 1.15; speciesCohesionResponse = 0.10; speciesStrongCoupling = 0.0; speciesCharge = 1.0; speciesCurvatureCoupling = 0.20; }
            else if (speciesID == 3 || speciesID == 13 || speciesID == 14) { speciesMassResponse = 0.25; speciesSpeedResponse = 1.55; speciesTurbulenceResponse = 0.35; speciesCohesionResponse = 0.02; speciesStrongCoupling = 0.0; speciesCharge = 0.0; speciesCurvatureCoupling = 0.05; }
            else if (speciesID == 4) { speciesMassResponse = 0.75; speciesSpeedResponse = 0.90; speciesTurbulenceResponse = 0.65; speciesCohesionResponse = 1.35; speciesStrongCoupling = 1.0; speciesCharge = 0.6666667; speciesCurvatureCoupling = 0.35; }
            else if (speciesID == 5) { speciesMassResponse = 0.80; speciesSpeedResponse = 0.85; speciesTurbulenceResponse = 0.60; speciesCohesionResponse = 1.40; speciesStrongCoupling = 1.0; speciesCharge = -0.3333333; speciesCurvatureCoupling = 0.38; }
            else if (speciesID == 6) { speciesMassResponse = 0.05; speciesSpeedResponse = 1.80; speciesTurbulenceResponse = 1.25; speciesCohesionResponse = 0.00; speciesStrongCoupling = 0.0; speciesCharge = 0.0; speciesCurvatureCoupling = 0.12; }
            else if (speciesID == 7) { speciesMassResponse = 0.10; speciesSpeedResponse = 1.25; speciesTurbulenceResponse = 1.40; speciesCohesionResponse = 1.60; speciesStrongCoupling = 1.25; speciesCharge = 0.0; speciesCurvatureCoupling = 0.20; }
            else if (speciesID == 8) { speciesMassResponse = 1.40; speciesSpeedResponse = 0.45; speciesTurbulenceResponse = 0.35; speciesCohesionResponse = 0.65; speciesStrongCoupling = 0.0; speciesCharge = 0.0; speciesCurvatureCoupling = 0.65; }
            else if (speciesID == 9) { speciesMassResponse = 1.20; speciesSpeedResponse = 0.55; speciesTurbulenceResponse = 0.45; speciesCohesionResponse = 1.25; speciesStrongCoupling = 1.15; speciesCharge = 1.0; speciesCurvatureCoupling = 0.75; }
            else if (speciesID == 10) { speciesMassResponse = 1.25; speciesSpeedResponse = 0.50; speciesTurbulenceResponse = 0.40; speciesCohesionResponse = 1.30; speciesStrongCoupling = 1.15; speciesCharge = 0.0; speciesCurvatureCoupling = 0.78; }
            else if (speciesID == 15 || speciesID == 16 || speciesID == 17 || speciesID == 18) { speciesMassResponse = 1.10; speciesSpeedResponse = 0.65; speciesTurbulenceResponse = 0.52; speciesCohesionResponse = 1.42; speciesStrongCoupling = 1.10; speciesCharge = (speciesID == 16 || speciesID == 17) ? 0.6666667 : -0.3333333; speciesCurvatureCoupling = 0.65; }
            else if (speciesID == 19 || speciesID == 20) { speciesMassResponse = 1.20; speciesSpeedResponse = 0.78; speciesTurbulenceResponse = 0.58; speciesCohesionResponse = 0.25; speciesStrongCoupling = 0.0; speciesCharge = (speciesID == 19) ? 1.0 : 0.0; speciesCurvatureCoupling = 0.55; }
            else if (speciesID == 21) { speciesMassResponse = 1.00; speciesSpeedResponse = 0.75; speciesTurbulenceResponse = 0.75; speciesCohesionResponse = 1.25; speciesStrongCoupling = 1.10; speciesCharge = 0.0; speciesCurvatureCoupling = 0.55; }

            massScalar = max(0.05, massScalar * speciesMassResponse);
            turbulenceScalar = clamp(turbulenceScalar * speciesTurbulenceResponse, 0.0, 3.5);
            cohesionScalar = clamp(cohesionScalar * speciesCohesionResponse, 0.0, 4.8);

            // v1.3F6: no active anchor tether. Crab geography is the initial condition;
            // speed and mass now control free-roaming independent particles.

            // Shared field controls still matter, but are now per-particle forces.
            force += tangent * (0.010 * orbitalW * particleGain);
            force += -dir * (0.006 * radialW);
            force.y += sin(localPhase) * 0.010 * verticalW;
            force += float3(
                sin(localPhase * 1.9 + pos.x * 2.1),
                cos(localPhase * 1.3 + pos.y * 3.1),
                sin(localPhase * 1.7 + pos.z * 2.7)
            ) * (0.004 * turbW * particleGain);
            force += dir * sin(r * 2.8 - phase * 1.7 + seed) * (0.004 * shellW);

            // RMU v1.3F9B VCV-only particle force pair. This remains active when behavior is OFF.
            force += float3(
                sin(localPhase * 3.7 + pos.z * 5.1 + seed * 6.2831853),
                cos(localPhase * 2.9 + pos.x * 4.3 + seed2 * 6.2831853),
                sin(localPhase * 3.3 + pos.y * 4.7 + seed3 * 6.2831853)
            ) * (0.010 * turbulenceScalar * particleGain);
            force += -dir * (0.012 * cohesionScalar);

            // RMU_V1_4A species-aware field/VCV coupling.
            force += -dir * (0.006 * cohesionScalar * speciesStrongCoupling);
            force += float3(-pos.y, pos.x, sin(localPhase + seed * 6.2831853)) * (0.0015 * speciesCharge * particleGain);
            force += dir * (0.0020 * speciesCurvatureCoupling * radialW);

            if (speciesID == 7) {
                force += float3(
                    sin(localPhase * 6.0 + seed * 12.0),
                    cos(localPhase * 5.0 + seed2 * 10.0),
                    sin(localPhase * 7.0 + seed3 * 8.0)
                ) * (0.006 * cohesionScalar);
            }

            if (speciesID == 8) {
                force *= 0.82;
                force += -pos * (0.0015 * massScalar);
            }

            // RMU_V1_4B5_CONTROLLABLE_GRAVITY_WELL_FORCE_ACTIVE
            // /ch/13 moves the gravity well along a dramatic X/Z diagonal.
            // /ch/14 changes force enough to overpower the existing center well.
            float wellPos = clamp(gravityWellPosition, -1.0, 1.0);
            float wellStrength = clamp(gravityWellStrength, 0.0, 12.0);
            float3 gravityWellCenter = float3(wellPos * 850.0, 0.0, -wellPos * 450.0);
            float3 toWell = gravityWellCenter - pos;
            float wellDistance = max(length(toWell), 8.0);
            float3 wellDir = toWell / wellDistance;
            float3 wellTangent = normalize(float3(-wellDir.z, 0.0, wellDir.x) + 0.0001);

            force += wellDir * (0.024 * wellStrength * particleGain) / sqrt(1.0 + wellDistance * 0.002);
            force += wellTangent * (0.016 * wellStrength * orbitalW) / sqrt(1.0 + wellDistance * 0.002);

            // RMU_V1_4B controllable gravity well.
            // /ch/13 moves the well dramatically along a diagonal X/Z path.
            // /ch/14 changes the well strength enough to overpower existing behavior fields.

            // v1.3F8: first-class /ch/11 particle turbulence and /ch/12 particle cohesion.
            force += float3(
                sin(localPhase * 3.7 + pos.z * 5.1 + seed * 6.2831853),
                cos(localPhase * 2.9 + pos.x * 4.3 + seed2 * 6.2831853),
                sin(localPhase * 3.3 + pos.y * 4.7 + seed3 * 6.2831853)
            ) * (0.010 * turbulenceScalar * particleGain);
            force += -dir * (0.012 * cohesionScalar);

            int effectiveBehaviorCode = behaviorEffectCode;\n            if (effectiveBehaviorCode == 1) {
                // stable_orbit_cloud: independent orbit with strong memory.
                force += tangent * (0.022 * particleGain);
            } else if (effectiveBehaviorCode == 2) {
                // black_hole_capture: individual inward streams, anchor competes against capture.
                force += -dir * (0.040 + 0.055 * seed) * particleGain;
                force += tangent * (0.015 + 0.020 * seed2);
            } else if (effectiveBehaviorCode == 3) {
                // accretion_disk: flatten and rotate independently.
                force += tangent * (0.052 + 0.035 * seed) * particleGain;
                force.y += -pos.y * (0.060 + 0.070 * seed2);
                force += -dir * 0.010;
            } else if (effectiveBehaviorCode == 4) {
                // field_pressure_bounce: pressure waves / rebounds.
                float wave = sin(r * 5.0 - phase * 3.6 + seed * 6.2831853);
                force += dir * wave * (0.060 + 0.035 * seed2) * particleGain;
                force.y += cos(localPhase * 1.6) * 0.045 * particleGain;
            } else if (effectiveBehaviorCode == 5) {
                // infinite_collapse: aggressive independent collapse.
                force += -dir * (0.090 + 0.080 * seed) * particleGain;
                force += tangent * (0.010 * sin(localPhase));
            }

            float3 acceleration = force / massScalar;
            vel = (vel + acceleration * dt * 60.0 * speedScalar) * damping;
            pos += vel * dt * 60.0;

            // RMU v1.3F9B respawn-on-capture. Applies in all behavior states.
            if (respawnOnCapture == 1 && length(pos) < 0.18) {
                float jitterScale = 0.012;
                pos = base + float3(seed - 0.5, seed2 - 0.5, seed3 - 0.5) * jitterScale;
                vel = float3(0.0);
            }

            // Hard safety clamp, prevents particles from going into numerical infinity.
            float maxRadius = 14.0;
            float lr = length(pos);
            if (lr > maxRadius) {
                pos = normalize(pos) * maxRadius;
                vel *= 0.25;
            }

            liveParticles[id].position = pos;
            velocityParticles[id].position = vel;
        }

        fragment float4 fragment_main(VertexOut in [[stage_in]]) {
            return in.color;
        }
        """

        do {
            let library = try device.makeLibrary(source: shaderSource, options: nil)
            let vertexFunction = library.makeFunction(name: "vertex_main")
            let fragmentFunction = library.makeFunction(name: "fragment_main")
            let descriptor = MTLRenderPipelineDescriptor()
            descriptor.vertexFunction = vertexFunction
            descriptor.fragmentFunction = fragmentFunction
            descriptor.colorAttachments[0].pixelFormat = view.colorPixelFormat
            descriptor.colorAttachments[0].isBlendingEnabled = true
            descriptor.colorAttachments[0].rgbBlendOperation = .add
            descriptor.colorAttachments[0].alphaBlendOperation = .add
            descriptor.colorAttachments[0].sourceRGBBlendFactor = .sourceAlpha
            descriptor.colorAttachments[0].destinationRGBBlendFactor = .oneMinusSourceAlpha
            descriptor.colorAttachments[0].sourceAlphaBlendFactor = .sourceAlpha
            descriptor.colorAttachments[0].destinationAlphaBlendFactor = .oneMinusSourceAlpha
            self.pipelineState = try device.makeRenderPipelineState(descriptor: descriptor)
            if let computeFunction = library.makeFunction(name: "update_geospatial_particles") {
                self.computePipelineState = try? device.makeComputePipelineState(function: computeFunction)
                if self.computePipelineState == nil {
                    print("WARNING: v1.3F6 compute pipeline was not created; renderer will fall back to static draw.")
                }
            }
        } catch {
            print("Metal pipeline creation failed: \(error)")
            return nil
        }

        super.init()
        buildStaticBuffers()
    }

    func buildStaticBuffers() {
        gridBuffer = makeGridBuffer(radius: 6.0, divisions: 12)
        centerBuffer = makeRingBuffer(radius: 0.06, count: 96)
        horizonBuffer = makeRingBuffer(radius: 0.34, count: 192)

        curvatureRingBuffers.removeAll()
        curvatureRingCounts.removeAll()
        let radii: [Float] = [0.72, 1.05, 1.55, 2.25, 3.15, 4.30, 5.65]
        for (index, radius) in radii.enumerated() {
            let count = 320 + index * 80
            if let buffer = makeWarpedRingBuffer(radius: radius, count: count, warp: 0.035 + Float(index) * 0.008) {
                curvatureRingBuffers.append(buffer)
                curvatureRingCounts.append(count)
            }
        }

        probabilityHaloCount = 4200
        probabilityHaloBuffer = makeProbabilityHaloBuffer(count: probabilityHaloCount, innerRadius: 0.75, outerRadius: 5.85)
    }

    func makeRingBuffer(radius: Float, count: Int) -> MTLBuffer? {
        var particles: [Particle] = []
        particles.reserveCapacity(count)
        for i in 0..<count {
            let t = Float(i) / Float(count) * Float.pi * 2.0
            particles.append(Particle(position: SIMD3<Float>(cos(t) * radius, 0, sin(t) * radius)))
        }
        return device.makeBuffer(bytes: particles, length: particles.count * MemoryLayout<Particle>.stride, options: [.storageModeShared])
    }

    func makeWarpedRingBuffer(radius: Float, count: Int, warp: Float) -> MTLBuffer? {
        var particles: [Particle] = []
        particles.reserveCapacity(count)
        for i in 0..<count {
            let t = Float(i) / Float(count) * Float.pi * 2.0
            let w1 = sin(t * 3.0) * warp
            let w2 = cos(t * 7.0) * warp * 0.55
            let rr = radius * (1.0 + w1 + w2)
            let y = sin(t * 5.0) * warp * 0.45
            particles.append(Particle(position: SIMD3<Float>(cos(t) * rr, y, sin(t) * rr)))
        }
        return device.makeBuffer(bytes: particles, length: particles.count * MemoryLayout<Particle>.stride, options: [.storageModeShared])
    }

    func makeProbabilityHaloBuffer(count: Int, innerRadius: Float, outerRadius: Float) -> MTLBuffer? {
        var particles: [Particle] = []
        particles.reserveCapacity(count)
        let goldenAngle = Float.pi * (3.0 - sqrt(5.0))
        for i in 0..<count {
            let f = Float(i) / Float(max(1, count - 1))
            let r = innerRadius + (outerRadius - innerRadius) * sqrt(f)
            let t = Float(i) * goldenAngle
            let wobble = 1.0 + 0.055 * sin(t * 0.31) + 0.025 * cos(t * 0.73)
            let y = sin(t * 0.13) * 0.035 + cos(r * 2.2) * 0.025
            particles.append(Particle(position: SIMD3<Float>(cos(t) * r * wobble, y, sin(t) * r * wobble)))
        }
        return device.makeBuffer(bytes: particles, length: particles.count * MemoryLayout<Particle>.stride, options: [.storageModeShared])
    }

    func makeGridBuffer(radius: Float, divisions: Int) -> MTLBuffer? {
        var particles: [Particle] = []
        let step = (radius * 2.0) / Float(divisions)
        for i in 0...divisions {
            let v = -radius + Float(i) * step
            for j in 0...divisions {
                let u = -radius + Float(j) * step
                particles.append(Particle(position: SIMD3<Float>(u, -0.01, v)))
            }
        }
        return device.makeBuffer(bytes: particles, length: particles.count * MemoryLayout<Particle>.stride, options: [.storageModeShared])
    }

    func mtkView(_ view: MTKView, drawableSizeWillChange size: CGSize) {
        hud?.updateLayout()
    }


    // RMU_V1_7I_RENDERER_MANUAL_AUTHORITY_HELPERS_BEGIN
    func rmuV17IManualAuthorityModeObject() -> [String: Any] {
        let url = URL(fileURLWithPath: projectRoot).appendingPathComponent("output").appendingPathComponent("manual_authority_mode.json")
        guard let data = try? Data(contentsOf: url), let json = try? JSONSerialization.jsonObject(with: data, options: []) as? [String: Any] else {
            return ["auto_fields_enabled": false, "auto_behavior_enabled": false, "auto_camera_enabled": false, "manual_scene_index": 0, "manual_behavior_code": 0, "manual_field_weights": ["radial": 1.0, "orbital": 1.0, "vertical": 1.0, "turbulence": 1.0, "shell": 1.0]]
        }
        return json
    }
    func rmuV17IBool(_ obj: [String: Any], _ key: String, _ fallback: Bool) -> Bool {
        if let b = obj[key] as? Bool { return b }
        if let n = obj[key] as? NSNumber { return n.boolValue }
        if let s = obj[key] as? String {
            let lowered = s.lowercased()
            if ["true", "1", "yes", "on", "auto"].contains(lowered) { return true }
            if ["false", "0", "no", "off", "manual"].contains(lowered) { return false }
        }
        return fallback
    }
    func rmuV17IFloat(_ value: Any?, _ fallback: Float) -> Float {
        if let n = value as? NSNumber { return n.floatValue }
        if let d = value as? Double { return Float(d) }
        if let f = value as? Float { return f }
        if let i = value as? Int { return Float(i) }
        if let s = value as? String, let d = Double(s) { return Float(d) }
        return fallback
    }
    func rmuV17IInt(_ value: Any?, _ fallback: Int) -> Int {
        if let n = value as? NSNumber { return n.intValue }
        if let i = value as? Int { return i }
        if let d = value as? Double { return Int(d.rounded()) }
        if let s = value as? String, let d = Double(s) { return Int(d.rounded()) }
        return fallback
    }
    func rmuV17IAutoFieldsEnabled() -> Bool { rmuV17IBool(rmuV17IManualAuthorityModeObject(), "auto_fields_enabled", false) }
    func rmuV17IAutoBehaviorEnabled() -> Bool { rmuV17IBool(rmuV17IManualAuthorityModeObject(), "auto_behavior_enabled", false) }
    func rmuV17IAutoCameraEnabled() -> Bool { rmuV17IBool(rmuV17IManualAuthorityModeObject(), "auto_camera_enabled", false) }
    func rmuV17IManualSceneIndex(_ mode: [String: Any]) -> Int { max(0, min(7, rmuV17IInt(mode["manual_scene_index"], 0))) }
    func rmuV17IManualBehaviorCode(_ mode: [String: Any]) -> Int32 { Int32(max(0, min(7, rmuV17IInt(mode["manual_behavior_code"], 0)))) }
    func rmuV17IManualFieldWeights(_ mode: [String: Any]) -> [Float] {
        guard let w = mode["manual_field_weights"] as? [String: Any] else { return [1.0, 1.0, 1.0, 1.0, 1.0] }
        return [rmuV17IFloat(w["radial"], 1.0), rmuV17IFloat(w["orbital"], 1.0), rmuV17IFloat(w["vertical"], 1.0), rmuV17IFloat(w["turbulence"], 1.0), rmuV17IFloat(w["shell"], 1.0)]
    }
    func rmuV17IEnforceRendererManualAuthority(reason: String = "unspecified") {
        let mode = rmuV17IManualAuthorityModeObject()
        let autoFields = rmuV17IBool(mode, "auto_fields_enabled", false)
        let autoBehavior = rmuV17IBool(mode, "auto_behavior_enabled", false)
        let autoCamera = rmuV17IBool(mode, "auto_camera_enabled", false)
        if !autoFields && !rmuV19ODataCouplingApplyEnabled() {
            let weights = rmuV17IManualFieldWeights(mode)
            fieldLayerWeights = Array(weights.prefix(5))
            fieldLayerEnabled = fieldLayerWeights.map { $0 > 0.0 }
            let scene = rmuV17IManualSceneIndex(mode)
            vcvSceneIndex = scene
            vcvAuthoritySceneIndex = scene
            selectedFieldLayerIndex = max(0, min(max(0, fieldLayerWeights.count - 1), scene == 0 ? 0 : scene - 1))
            fieldLayersEnabled = true
            dataCouplingStatus = "manual lock: dataset coupling not applying fields"
            lastVisualStateMessage = "v1.7I manual field authority"
        }
        if !autoBehavior {
            let code = rmuV17IManualBehaviorCode(mode)
            behaviorEffectCode = code
            rmuV16DBehaviorAuthorityActive = false
            rmuV16DBehaviorAuthorityCode = code
            rmuV16DBehaviorAuthorityGate = 0.0
        }
        if !autoCamera { autoCameraEnabled = false }
        _ = reason
    }
    // RMU_V1_7I_RENDERER_MANUAL_AUTHORITY_HELPERS_END

    // RMU_V1_7J_CONTROL_SCHEMA_HELPERS_BEGIN
    func rmuV17JControlModeObject() -> [String: Any] {
        let url = URL(fileURLWithPath: projectRoot).appendingPathComponent("output").appendingPathComponent("manual_authority_mode.json")
        guard let data = try? Data(contentsOf: url), let json = try? JSONSerialization.jsonObject(with: data, options: []) as? [String: Any] else {
            return ["auto_fields_enabled": false, "auto_behavior_enabled": false, "auto_camera_enabled": false, "linked_behavior_presets_enabled": false, "linked_scene_presets_enabled": false, "dataset_coupling_mode": "observe", "manual_scene_index": 0, "manual_behavior_code": 0, "manual_field_weights": ["radial": 1.0, "orbital": 1.0, "vertical": 1.0, "turbulence": 1.0, "shell": 1.0]]
        }
        return json
    }
    func rmuV17JBool(_ obj: [String: Any], _ key: String, _ fallback: Bool) -> Bool {
        if let b = obj[key] as? Bool { return b }
        if let n = obj[key] as? NSNumber { return n.boolValue }
        if let s = obj[key] as? String { let v=s.lowercased(); if ["true","1","yes","on","auto","apply"].contains(v) { return true }; if ["false","0","no","off","manual","observe"].contains(v) { return false } }
        return fallback
    }
    func rmuV17JFloat(_ value: Any?, _ fallback: Float) -> Float {
        if let n = value as? NSNumber { return n.floatValue }; if let d = value as? Double { return Float(d) }; if let f = value as? Float { return f }; if let i = value as? Int { return Float(i) }; if let s = value as? String, let d = Double(s) { return Float(d) }; return fallback
    }
    func rmuV17JInt(_ value: Any?, _ fallback: Int) -> Int { Int(rmuV17JFloat(value, Float(fallback)).rounded()) }
    func rmuV17JAutoFieldsEnabled() -> Bool { rmuV17JBool(rmuV17JControlModeObject(), "auto_fields_enabled", false) }
    func rmuV17JAutoBehaviorEnabled() -> Bool { rmuV17JBool(rmuV17JControlModeObject(), "auto_behavior_enabled", false) }
    func rmuV17JAutoCameraEnabled() -> Bool { rmuV17JBool(rmuV17JControlModeObject(), "auto_camera_enabled", false) }
    func rmuV17JLinkedBehaviorPresetsEnabled() -> Bool { rmuV17JBool(rmuV17JControlModeObject(), "linked_behavior_presets_enabled", false) }
    func rmuV17JDatasetCouplingApplyEnabled() -> Bool { (rmuV17JControlModeObject()["dataset_coupling_mode"] as? String ?? "observe").lowercased() == "apply" }
    func rmuV17JManualFieldWeights(_ mode: [String: Any]) -> [Float] {
        let w = mode["manual_field_weights"] as? [String: Any] ?? [:]
        return [rmuV17JFloat(w["radial"],1.0), rmuV17JFloat(w["orbital"],1.0), rmuV17JFloat(w["vertical"],1.0), rmuV17JFloat(w["turbulence"],1.0), rmuV17JFloat(w["shell"],1.0)]
    }
    func rmuV17JCanonicalChannelNumber(_ json: [String: Any], _ path: String, _ label: String? = nil) -> Float? {
        func extract(_ any: Any?) -> Float? {
            if let n = any as? NSNumber { return n.floatValue }
            if let d = any as? Double { return Float(d) }
            if let f = any as? Float { return f }
            if let i = any as? Int { return Float(i) }
            if let s = any as? String, let d = Double(s) { return Float(d) }
            if let arr = any as? [Any], let first = arr.first { return extract(first) }
            if let dict = any as? [String: Any] {
                for k in ["stable", "value", "mapped", "raw"] { if let v = extract(dict[k]) { return v } }
                if let voices = dict["voices"] as? [Any], let first = voices.first { return extract(first) }
            }
            return nil
        }
        for containerName in ["channels", "direct_channels", "native_channel_values", "raw_channels"] {
            if let c = json[containerName] as? [String: Any], let v = extract(c[path]) { return v }
        }
        if let label = label {
            if let mapped = json["mapped_values"] as? [String: Any], let v = extract(mapped[label]) { return v }
            if let v = extract(json[label]) { return v }
        }
        return nil
    }
    func rmuV17JCanonicalVoiceCount(_ json: [String: Any], _ path: String) -> Int {
        if let counts = json["channel_voice_counts"] as? [String: Any], let n = counts[path] as? NSNumber { return n.intValue }
        for containerName in ["channels", "direct_channels"] {
            if let c = json[containerName] as? [String: Any], let entry = c[path] as? [String: Any] {
                if let n = entry["voice_count"] as? NSNumber { return n.intValue }
                if let voices = entry["voices"] as? [Any] { return voices.count }
                if entry["value"] != nil || entry["mapped"] != nil || entry["raw"] != nil { return 1 }
            } else if let c = json[containerName] as? [String: Any], c[path] != nil { return 1 }
        }
        return 0
    }
    func rmuV17JPublishEffectiveControlState(reason: String) {
        // RMU_V1_8B_RENDERER_DEBUG_ONLY: do not write canonical effective_control_state.json here.
        let mode = rmuV17JControlModeObject()
        let weights = rmuV17JManualFieldWeights(mode)
        let obj: [String: Any] = ["schema": "rmu.renderer_effective_debug_state.v1_8B", "version": "v1.8B-renderer-debug-only", "updated_by": "MetalRenderer.rmuV18BRendererDebugState", "reason": reason, "timestamp_unix": Date().timeIntervalSince1970, "authority": ["field_weights": rmuV17JAutoFieldsEnabled() ? "auto" : "manual", "field_recipe": rmuV17JAutoFieldsEnabled() ? "auto" : "manual", "behavior": rmuV17JAutoBehaviorEnabled() ? "auto" : "manual", "camera": rmuV17JAutoCameraEnabled() ? "auto" : "manual", "dataset_coupling": (mode["dataset_coupling_mode"] as? String ?? "observe")], "effective": ["scene_index": rmuV17JInt(mode["manual_scene_index"], 0), "behavior_code": Int(behaviorEffectCode), "behavior_authority_gate": rmuV16DBehaviorAuthorityGate, "field_weights": ["radial": weights[0], "orbital": weights[1], "vertical": weights[2], "turbulence": weights[3], "shell": weights[4]]]]
        let url = URL(fileURLWithPath: projectRoot).appendingPathComponent("output").appendingPathComponent("renderer_effective_debug_state.json")
        if let data = try? JSONSerialization.data(withJSONObject: obj, options: [.prettyPrinted]) { try? data.write(to: url) }
    }
    func rmuV17JEnforceControlAuthority(reason: String = "unspecified") {
        let mode = rmuV17JControlModeObject()
        if !rmuV19ODataCouplingApplyEnabled() && !rmuV17JAutoFieldsEnabled() {
            let weights = rmuV17JManualFieldWeights(mode)
            fieldLayerWeights = Array(weights.prefix(5))
            fieldLayerEnabled = fieldLayerWeights.map { $0 > 0.0 }
            fieldLayersEnabled = true
            let scene = max(0, min(7, rmuV17JInt(mode["manual_scene_index"], 0)))
            vcvSceneIndex = scene; vcvAuthoritySceneIndex = scene
            selectedFieldLayerIndex = max(0, min(max(0, fieldLayerWeights.count - 1), scene == 0 ? 0 : scene - 1))
            vcvFieldControlEnabled = false
            dataCouplingEnabled = false
            dataCouplingStatus = "observe/manual locked"
            lastVisualStateMessage = "v1.7J manual field authority"
        }
        if !rmuV17JAutoBehaviorEnabled() {
            let code = Int32(max(0, min(7, rmuV17JInt(mode["manual_behavior_code"], 0))))
            behaviorEffectCode = code
            geospatialBehaviorEnabled = code != 0
            rmuV16DBehaviorAuthorityActive = false
            rmuV16DBehaviorAuthorityCode = code
            rmuV16DBehaviorAuthorityGate = 0.0
        }
        if !rmuV17JAutoCameraEnabled() { autoCameraEnabled = false }
        rmuV17JPublishEffectiveControlState(reason: reason)
    }
    // RMU_V1_7J_CONTROL_SCHEMA_HELPERS_END

    // RMU_V1_6F_PRE_ENCODE_VCV_AUTHORITY_BEGIN
    func rmuV16FApplyLiveVCVDirectAuthorityFromDisk() {
        let url = URL(fileURLWithPath: projectRoot)
            .appendingPathComponent("output")
            .appendingPathComponent("vcv_state.json")

        guard let data = try? Data(contentsOf: url),
              let json = try? JSONSerialization.jsonObject(with: data) as? [String: Any] else {
            return
        }

        func rmuV16FNumberForChannel(_ path: String) -> Float? {
            return rmuV17JCanonicalChannelNumber(json, path, nil)
        }

        func rmuV16FVoiceCountForChannel(_ path: String) -> Int {
            return rmuV17JCanonicalVoiceCount(json, path)
        }

        // /ch/8 = scene / field layer authority.
        // Important: older builds only changed selectedFieldLayerIndex, which affected HUD
        // but did not strongly change the Metal field weights. v1.6F makes /ch/8 produce
        // an actual shader-visible field recipe.
        if rmuV16FVoiceCountForChannel("/ch/8") > 0,
           let sceneValue = rmuV16FNumberForChannel("/ch/8") {
            let directScene = max(1, min(6, Int(round(sceneValue))))
            let layerIndex = max(0, min(fieldLayerWeights.count - 1, directScene - 1))

            vcvSceneIndex = directScene
            vcvAuthoritySceneIndex = directScene
            vcvAuthorityFieldLayerIndex = layerIndex
            selectedFieldLayerIndex = layerIndex
            fieldLayersEnabled = true

            // Scene-to-field recipe:
            // 1 radial, 2 orbital, 3 vertical, 4 turbulence, 5 shell, 6 combined.
            switch directScene {
            case 1:
                fieldLayerWeights = [2.25, 0.00, 0.00, 0.00, 0.00]
                fieldLayerEnabled = [true, false, false, false, false]
            case 2:
                fieldLayerWeights = [0.00, 2.25, 0.00, 0.00, 0.00]
                fieldLayerEnabled = [false, true, false, false, false]
            case 3:
                fieldLayerWeights = [0.00, 0.00, 2.25, 0.00, 0.00]
                fieldLayerEnabled = [false, false, true, false, false]
            case 4:
                fieldLayerWeights = [0.00, 0.00, 0.00, 2.25, 0.00]
                fieldLayerEnabled = [false, false, false, true, false]
            case 5:
                fieldLayerWeights = [0.00, 0.00, 0.00, 0.00, 2.25]
                fieldLayerEnabled = [false, false, false, false, true]
            case 6:
                fieldLayerWeights = [1.00, 1.00, 0.50, 0.60, 0.85]
                fieldLayerEnabled = [true, true, true, true, true]
            default:
                break
            }
        }

        // /ch/18 = behavior code, /ch/19 = behavior authority gate.
        // Apply this immediately before encode/render so controller or legacy state cannot stomp it.
        let gateValue = rmuV16FNumberForChannel("/ch/19") ?? 0.0
        let gateActive = rmuV16FVoiceCountForChannel("/ch/19") > 0 && gateValue >= 5.0

        if gateActive,
           rmuV16FVoiceCountForChannel("/ch/18") > 0,
           let behaviorValue = rmuV16FNumberForChannel("/ch/18") {
            let directBehavior = Int32(max(0, min(7, Int(round(behaviorValue)))))

            behaviorEffectCode = directBehavior
            geospatialBehaviorEnabled = true

            rmuV16DBehaviorAuthorityActive = true
            rmuV16DBehaviorAuthorityCode = directBehavior
            rmuV16DBehaviorAuthorityGate = gateValue
        } else {
            rmuV16DBehaviorAuthorityActive = false
            rmuV16DBehaviorAuthorityGate = gateValue
        }
        // RMU_V1_7I_DIRECT_AUTHORITY_FINAL_OVERRIDE
        rmuV17IEnforceRendererManualAuthority(reason: "after_vcv_direct_authority")
    }
    // RMU_V1_6F_PRE_ENCODE_VCV_AUTHORITY_END

    func encodeGeospatialParticleUpdate(commandBuffer: MTLCommandBuffer) {
        // RMU_V1_11A_PHASE3E_MINIMAL_BYPASS_OLD_DISK_COMPUTE
        // Proof mode: bypass the legacy compact-disk compute kernel.
        // Set RMU_ENABLE_LEGACY_DISK_COMPUTE=1 only when comparing against the old snap-back behavior.
        if ProcessInfo.processInfo.environment["RMU_ENABLE_LEGACY_DISK_COMPUTE"] != "1" {
            return
        }

        guard geospatialSimulationPaused == 0,
              let computePipelineState = computePipelineState,
              let base = baseParticleBuffer,
              let live = liveParticleBuffer,
              let velocity = velocityParticleBuffer,
              let encoder = commandBuffer.makeComputeCommandEncoder() else { return }

        var count = UInt32(max(0, lastUploadedParticleCount))
        if count == 0 { return }
        // RMU_V1_6B_SPECIES_ENCODER_BINDINGS_BEGIN
        rmuV16BLoadSpeciesIdentityBuffersForParticleCount(Int(count))
        guard let rmuV16BSpeciesIDBufferLive = rmuV16BSpeciesIDBuffer,
              let rmuV16BFamilyIDBufferLive = rmuV16BFamilyIDBuffer,
              let rmuV16BSpeciesWeightBufferLive = rmuV16BSpeciesWeightBuffer else {
            rmuV16BSpeciesIdentityStatus = "identity buffers unavailable during encode"
            return
        }
        let rmuV16BProbabilityBank = rmuV16BPackBank32(particleSpeciesProbability, fallback: 1.0)
        let rmuV16BSpeedBank = rmuV16BPackBank32(particleSpeciesSpeed, fallback: geospatialParticleSpeed)
        let rmuV16BMassBank = rmuV16BPackBank32(particleSpeciesMass, fallback: geospatialParticleMass)
        let rmuV16BTurbulenceBank = rmuV16BPackBank32(particleSpeciesTurbulence, fallback: geospatialParticleTurbulence)
        let rmuV16BCohesionBank = rmuV16BPackBank32(particleSpeciesCohesion, fallback: geospatialParticleCohesion)
        let rmuV16BColorBank = rmuV16BPackColorBank96(particleSpeciesColorRGB)
        var rmuV16BEnabled = rmuV16BSpeciesControlEnabled
        encoder.setBuffer(rmuV16BSpeciesIDBufferLive, offset: 0, index: 20)
        encoder.setBuffer(rmuV16BFamilyIDBufferLive, offset: 0, index: 21)
        encoder.setBuffer(rmuV16BSpeciesWeightBufferLive, offset: 0, index: 22)
        rmuV16BProbabilityBank.withUnsafeBytes { encoder.setBytes($0.baseAddress!, length: $0.count, index: 23) }
        rmuV16BSpeedBank.withUnsafeBytes { encoder.setBytes($0.baseAddress!, length: $0.count, index: 24) }
        rmuV16BMassBank.withUnsafeBytes { encoder.setBytes($0.baseAddress!, length: $0.count, index: 25) }
        rmuV16BTurbulenceBank.withUnsafeBytes { encoder.setBytes($0.baseAddress!, length: $0.count, index: 26) }
        rmuV16BCohesionBank.withUnsafeBytes { encoder.setBytes($0.baseAddress!, length: $0.count, index: 27) }
        rmuV16BColorBank.withUnsafeBytes { encoder.setBytes($0.baseAddress!, length: $0.count, index: 28) }
        encoder.setBytes(&rmuV16BEnabled, length: MemoryLayout<Float>.stride, index: 30)
        // RMU_V1_6B_SPECIES_ENCODER_BINDINGS_END

        // RMU_V1_6F_COMPUTE_PRE_ENCODE_AUTHORITY_CALL
        rmuV16FApplyLiveVCVDirectAuthorityFromDisk()
        // RMU_V1_9S_FINAL_DATASET_COUPLING_AUTHORITY
        // Dataset coupling APPLY is higher than manual/scene field recipes, but lower than explicit future emergency locks.
        if rmuV19ODataCouplingApplyEnabled() {
            loadDatasetCouplingIfNeeded()
            applyDatasetCouplingTargets()
        }

        var dt = geospatialSimDt
        var behavior = rmuV16DBehaviorAuthorityActive ? rmuV16DBehaviorAuthorityCode : behaviorEffectCode
        var particleSpeed = geospatialParticleSpeed
        var damping = min(max(geospatialDamping, 0.992), 0.9995) // RMU_V1_11A long-range velocity memory
        var weightsA = SIMD4<Float>(
            fieldLayerWeights[0],
            fieldLayerWeights[1],
            fieldLayerWeights[2],
            fieldLayerWeights[3]
        )
        var shell = fieldLayerWeights[4] * 0.03 // RMU_V1_11A weak shell, not wall
        var phase = fieldPhase

        encoder.setComputePipelineState(computePipelineState)
        encoder.setBuffer(base, offset: 0, index: 0)
        encoder.setBuffer(live, offset: 0, index: 1)
        encoder.setBuffer(velocity, offset: 0, index: 2)
        encoder.setBytes(&count, length: MemoryLayout<UInt32>.stride, index: 3)
        encoder.setBytes(&dt, length: MemoryLayout<Float>.stride, index: 4)
        encoder.setBytes(&behavior, length: MemoryLayout<Int32>.stride, index: 5)
        encoder.setBytes(&particleSpeed, length: MemoryLayout<Float>.stride, index: 6)
        encoder.setBytes(&damping, length: MemoryLayout<Float>.stride, index: 7)
        encoder.setBytes(&weightsA, length: MemoryLayout<SIMD4<Float>>.stride, index: 8)
        encoder.setBytes(&shell, length: MemoryLayout<Float>.stride, index: 9)
        encoder.setBytes(&phase, length: MemoryLayout<Float>.stride, index: 10)
        var particleMass = geospatialParticleMass
        encoder.setBytes(&particleMass, length: MemoryLayout<Float>.stride, index: 11)
        var particleTurbulence = geospatialParticleTurbulence
        encoder.setBytes(&particleTurbulence, length: MemoryLayout<Float>.stride, index: 12)
        var particleCohesion = geospatialParticleCohesion
        encoder.setBytes(&particleCohesion, length: MemoryLayout<Float>.stride, index: 13)
        // RMU_V1_6F_COMPUTE_BEHAVIOR_ENABLED_AUTHORITY
        var behaviorEnabledValue: Int32 = (rmuV16DBehaviorAuthorityActive || geospatialBehaviorEnabled) ? 1 : 0
        encoder.setBytes(&behaviorEnabledValue, length: MemoryLayout<Int32>.stride, index: 14)
        var respawnOnCaptureValue: Int32 = geospatialRespawnOnCapture ? 1 : 0
        encoder.setBytes(&respawnOnCaptureValue, length: MemoryLayout<Int32>.stride, index: 15)
        // RMU_V1_4B5_GRAVITY_WELL_ENCODER_ACTIVE_RAW_CHANNELS
        // /ch/13: raw -5V..+5V -> gravity well position -1..+1
        // /ch/14: raw -5V..+5V -> gravity well strength 0..12
        // RMU_V1_4B11_GRAVITY_ENCODER_USES_CHANNEL_VALUES
        var gravityWellPositionValue: Float = 0.0
        // RMU_V1_5F_GRAVITY_VEC4_AUTHORITY
        if gravityWellPositionVec4.count >= 1 {
            gravityWellPositionValue = max(-1.0, min(gravityWellPositionVec4[0], 1.0))
        } else if vcvChannelValues.count >= 14 {
            gravityWellPositionValue = max(-1.0, min(vcvChannelValues[13], 1.0))
        }
        var gravityWellStrengthValue: Float = 6.0
        // RMU_V1_5F_GRAVITY_STRENGTH_CH15_AUTHORITY
        if vcvChannelValues.count >= 15 {
            gravityWellStrengthValue = max(0.0, min(vcvChannelValues[14], 12.0))
        }
        encoder.setBytes(&gravityWellPositionValue, length: MemoryLayout<Float>.stride, index: 18)
        encoder.setBytes(&gravityWellStrengthValue, length: MemoryLayout<Float>.stride, index: 19)
        // RMU_V1_6F_KERNEL_BEHAVIOR_ENABLED_AUTHORITY
        var behaviorEnabledForKernel = (rmuV16DBehaviorAuthorityActive || geospatialBehaviorEnabled) ? Int32(1) : Int32(0)
        encoder.setBytes(&behaviorEnabledForKernel, length: MemoryLayout<Int32>.stride, index: 14)
        var respawnOnCaptureForKernel = geospatialRespawnOnCapture ? Int32(1) : Int32(0)
        encoder.setBytes(&respawnOnCaptureForKernel, length: MemoryLayout<Int32>.stride, index: 15)

        let threads = MTLSize(width: Int(count), height: 1, depth: 1)
        let w = min(computePipelineState.maxTotalThreadsPerThreadgroup, 256)
        let groups = MTLSize(width: w, height: 1, depth: 1)
        encoder.dispatchThreads(threads, threadsPerThreadgroup: groups)
        encoder.endEncoding()
    }

    func draw(in view: MTKView) {
        let drawStart = CFAbsoluteTimeGetCurrent()
        frameLoader.loadIfNeeded()
        updateParticleBufferIfNeeded()

        guard let drawable = view.currentDrawable,
              let renderPassDescriptor = view.currentRenderPassDescriptor else { return }

        renderPassDescriptor.colorAttachments[0].clearColor = MTLClearColor(red: 0.02, green: 0.025, blue: 0.04, alpha: 1.0)
        renderPassDescriptor.colorAttachments[0].loadAction = .clear
        renderPassDescriptor.colorAttachments[0].storeAction = .store

        guard let commandBuffer = commandQueue.makeCommandBuffer() else { return }
        encodeGeospatialParticleUpdate(commandBuffer: commandBuffer)
        guard let encoder = commandBuffer.makeRenderCommandEncoder(descriptor: renderPassDescriptor) else { return }

        encoder.setRenderPipelineState(pipelineState)

        if gridEnabled, let gb = gridBuffer {
            drawBuffer(encoder: encoder, buffer: gb, count: (12 + 1) * (12 + 1), alpha: 0.18, pointSizeOverride: 1.0, overlayMode: 1)
        }

        if probabilityOverlayEnabled && gridEnabled, let pb = probabilityHaloBuffer {
            drawBuffer(encoder: encoder, buffer: pb, count: probabilityHaloCount, alpha: 0.18, pointSizeOverride: 1.0, overlayMode: 4)
        }

        if trailsEnabled && !trailBuffers.isEmpty {
            for i in 0..<trailBuffers.count {
                let denom = max(1, trailBuffers.count - 1)
                let t = Float(i) / Float(denom)
                let alpha = trailAlphaFloor + (trailAlphaCeiling - trailAlphaFloor) * t
                drawBuffer(
                    encoder: encoder,
                    buffer: trailBuffers[i],
                    count: trailCounts[i],
                    alpha: alpha,
                    pointSizeOverride: max(0.75, pointSize * 0.75),
                    overlayMode: 0
                )
            }
        }

        if let buffer = liveParticleBuffer ?? particleBuffer, frameLoader.latestPointCount > 0 {
            drawBuffer(encoder: encoder, buffer: buffer, count: frameLoader.latestPointCount, alpha: 1.0, pointSizeOverride: pointSize, overlayMode: 0)
        }

        if curvatureOverlayEnabled && horizonRingEnabled && !curvatureRingBuffers.isEmpty {
            for i in 0..<curvatureRingBuffers.count {
                let denom = max(1, curvatureRingBuffers.count - 1)
                let t = Float(i) / Float(denom)
                let alpha: Float = 0.12 + t * 0.22
                drawBuffer(
                    encoder: encoder,
                    buffer: curvatureRingBuffers[i],
                    count: curvatureRingCounts[i],
                    alpha: alpha,
                    pointSizeOverride: 1.0 + t * 0.35,
                    overlayMode: 5
                )
            }
        }

        if centerMarkerEnabled, let cb = centerBuffer {
            drawBuffer(encoder: encoder, buffer: cb, count: 96, alpha: 0.95, pointSizeOverride: 2.0, overlayMode: 2)
        }

        if horizonRingEnabled, let hb = horizonBuffer {
            drawBuffer(encoder: encoder, buffer: hb, count: 192, alpha: 0.85, pointSizeOverride: 1.5, overlayMode: 3)
        }

        encoder.endEncoding()
        commandBuffer.present(drawable)
        commandBuffer.commit()

        currentFrameTimeMS = (CFAbsoluteTimeGetCurrent() - drawStart) * 1000.0
        lateFrameWarning = currentFrameTimeMS > 20.0 || currentFPS < 54.0

        loadVCVStateIfNeeded()
        // RMU_V1_7J_AFTER_LOAD_VCV_ENFORCE
        rmuV17JEnforceControlAuthority(reason: "after_load_vcv")
        loadDatasetCouplingIfNeeded()
        // RMU_V1_7I_CAMERA_MANUAL_GUARD_CALL
        if rmuV17IAutoCameraEnabled() { updateAutoCamera() }
        if geospatialSimulationPaused == 0 {
            fieldPhase += 0.035
        }

        frameIndex += 1
        framesSincePrint += 1
        let now = CFAbsoluteTimeGetCurrent()
        if now - lastFPSPrintTime >= 1.0 {
            currentFPS = Double(framesSincePrint) / (now - lastFPSPrintTime)
            printDiagnostics()
            hud?.updateText()
            lastFPSPrintTime = now
            framesSincePrint = 0
        }
    }

    func drawBuffer(encoder: MTLRenderCommandEncoder, buffer: MTLBuffer, count: Int, alpha: Float, pointSizeOverride: Float, overlayMode: Int32) {
        var radius = manualWorldRadius ?? frameLoader.worldRadius
        var mutablePointSize = pointSizeOverride
        var rot = rotationRadians
        var pan = SIMD2<Float>(panX, panY)
        var cm = colorMode
        var a = alpha
        var om = overlayMode
        // RMU_V1_6F_RENDER_PRE_DRAW_AUTHORITY_CALL
        rmuV16FApplyLiveVCVDirectAuthorityFromDisk()
        // RMU_V1_7I_RENDER_PRE_DRAW_FINAL_MANUAL_OVERRIDE
        rmuV17IEnforceRendererManualAuthority(reason: "render_pre_draw")
        // RMU_V1_9S_RENDER_FINAL_DATASET_COUPLING_AUTHORITY
        if rmuV19ODataCouplingApplyEnabled() {
            loadDatasetCouplingIfNeeded()
            applyDatasetCouplingTargets()
        }

        var fle = fieldLayersEnabled ? Int32(1) : Int32(0)
        var weightsA = SIMD4<Float>(
            fieldLayerWeights[0],
            fieldLayerWeights[1],
            fieldLayerWeights[2],
            fieldLayerWeights[3]
        )
        var weightShell = fieldLayerWeights[4]
        var enabledA = SIMD4<Int32>(
            fieldLayerEnabled[0] ? 1 : 0,
            fieldLayerEnabled[1] ? 1 : 0,
            fieldLayerEnabled[2] ? 1 : 0,
            fieldLayerEnabled[3] ? 1 : 0
        )
        var enabledShell = fieldLayerEnabled[4] ? Int32(1) : Int32(0)
        var phase = fieldPhase
        // v1.3F6: true motion is handled by the Metal compute kernel.
        // Keep vertex shader behavior disabled for main particles to avoid whole-cloud deformation.
        // RMU_V1_6F_RENDER_BEHAVIOR_CODE_AUTHORITY
        var behaviorCodeForShader = rmuV16DBehaviorAuthorityActive ? rmuV16DBehaviorAuthorityCode : Int32(0)
        var geospatialPausedForShader = geospatialSimulationPaused
        var anchorStrengthForShader = geospatialAnchorStrength

        encoder.setVertexBuffer(buffer, offset: 0, index: 0)

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
        // RMU_V1_6C_RENDER_SPECIES_COLOR_BINDINGS_END
        encoder.setVertexBytes(&radius, length: MemoryLayout<Float>.stride, index: 1)
        encoder.setVertexBytes(&mutablePointSize, length: MemoryLayout<Float>.stride, index: 2)
        encoder.setVertexBytes(&rot, length: MemoryLayout<Float>.stride, index: 3)
        encoder.setVertexBytes(&pan, length: MemoryLayout<SIMD2<Float>>.stride, index: 4)
        encoder.setVertexBytes(&cm, length: MemoryLayout<Int32>.stride, index: 5)
        encoder.setVertexBytes(&a, length: MemoryLayout<Float>.stride, index: 6)
        encoder.setVertexBytes(&om, length: MemoryLayout<Int32>.stride, index: 7)
        encoder.setVertexBytes(&fle, length: MemoryLayout<Int32>.stride, index: 8)
        encoder.setVertexBytes(&weightsA, length: MemoryLayout<SIMD4<Float>>.stride, index: 9)
        encoder.setVertexBytes(&weightShell, length: MemoryLayout<Float>.stride, index: 10)
        encoder.setVertexBytes(&enabledA, length: MemoryLayout<SIMD4<Int32>>.stride, index: 11)
        encoder.setVertexBytes(&enabledShell, length: MemoryLayout<Int32>.stride, index: 12)
        encoder.setVertexBytes(&phase, length: MemoryLayout<Float>.stride, index: 13)
        encoder.setVertexBytes(&behaviorCodeForShader, length: MemoryLayout<Int32>.stride, index: 14)
        encoder.setVertexBytes(&geospatialPausedForShader, length: MemoryLayout<Int32>.stride, index: 15)
        encoder.setVertexBytes(&anchorStrengthForShader, length: MemoryLayout<Float>.stride, index: 16)
        let drawCount = (overlayMode == 0 && count > geospatialDisplayParticleLimit) ? geospatialDisplayParticleLimit : count
        encoder.drawPrimitives(type: .point, vertexStart: 0, vertexCount: drawCount)
    }

    // RMU_V1_6B_SPECIES_IDENTITY_LOADER_BEGIN
    func rmuV16BReadUInt16LE(_ bytes: [UInt8], _ offset: Int) -> UInt16 {
        if offset + 1 >= bytes.count { return 0 }
        return UInt16(bytes[offset]) | (UInt16(bytes[offset + 1]) << 8)
    }

    func rmuV16BReadFloat32LE(_ bytes: [UInt8], _ offset: Int) -> Float {
        if offset + 3 >= bytes.count { return 0.0 }
        let bits = UInt32(bytes[offset]) | (UInt32(bytes[offset + 1]) << 8) | (UInt32(bytes[offset + 2]) << 16) | (UInt32(bytes[offset + 3]) << 24)
        return Float(bitPattern: bits)
    }

    func rmuV16BPackBank32(_ source: [Float], fallback: Float) -> [Float] {
        var out = Array(repeating: fallback, count: 32)
        if source.isEmpty { return out }
        for i in 0..<min(32, source.count) { out[i] = source[i] }
        return out
    }

    func rmuV16BPackColorBank96(_ source: [Float]) -> [Float] {
        var out = Array(repeating: Float(1.0), count: 96)
        if source.isEmpty { return out }
        for i in 0..<min(96, source.count) { out[i] = source[i] }
        return out
    }

    func rmuV16BLoadSpeciesIdentityBuffersForParticleCount(_ particleCount: Int) {
        if particleCount <= 0 {
            rmuV16BSpeciesIdentityStatus = "no particles"
            return
        }
        if rmuV16BSpeciesIdentityLoaded && rmuV16BSpeciesIdentityParticleCount == particleCount && rmuV16BSpeciesIDBuffer != nil && rmuV16BFamilyIDBuffer != nil && rmuV16BSpeciesWeightBuffer != nil { return }
        let binURL = URL(fileURLWithPath: projectRoot).appendingPathComponent("data").appendingPathComponent("processed").appendingPathComponent("species_identity_v1_6A.bin")
        guard let data = try? Data(contentsOf: binURL) else {
            rmuV16BSpeciesIdentityLoaded = false
            rmuV16BSpeciesIdentityStatus = "missing species_identity_v1_6A.bin"
            rmuV16BSpeciesIdentityLastError = binURL.path
            return
        }
        let bytes = [UInt8](data)
        let recordSize = 8
        let records = bytes.count / recordSize
        if records <= 0 { rmuV16BSpeciesIdentityLoaded = false; rmuV16BSpeciesIdentityStatus = "empty species identity"; return }
        var speciesIDs = Array(repeating: UInt32(0), count: particleCount)
        var familyIDs = Array(repeating: UInt32(0), count: particleCount)
        var weights = Array(repeating: Float(1.0), count: particleCount)
        let copyCount = min(records, particleCount)
        for i in 0..<copyCount {
            let offset = i * recordSize
            speciesIDs[i] = UInt32(min(rmuV16BReadUInt16LE(bytes, offset), UInt16(21)))
            familyIDs[i] = UInt32(min(rmuV16BReadUInt16LE(bytes, offset + 2), UInt16(6)))
            weights[i] = max(0.0, min(rmuV16BReadFloat32LE(bytes, offset + 4), 1.0))
        }
        if records < particleCount {
            for i in records..<particleCount {
                let j = i % max(records, 1)
                speciesIDs[i] = speciesIDs[j]
                familyIDs[i] = familyIDs[j]
                weights[i] = weights[j]
            }
        }
        rmuV16BSpeciesIDCPU = speciesIDs
        rmuV16BFamilyIDCPU = familyIDs
        rmuV16BSpeciesWeightCPU = weights
        let idLength = max(1, particleCount) * MemoryLayout<UInt32>.stride
        let weightLength = max(1, particleCount) * MemoryLayout<Float>.stride
        rmuV16BSpeciesIDBuffer = speciesIDs.withUnsafeBytes { device.makeBuffer(bytes: $0.baseAddress!, length: idLength, options: [.storageModeShared]) }
        rmuV16BFamilyIDBuffer = familyIDs.withUnsafeBytes { device.makeBuffer(bytes: $0.baseAddress!, length: idLength, options: [.storageModeShared]) }
        rmuV16BSpeciesWeightBuffer = weights.withUnsafeBytes { device.makeBuffer(bytes: $0.baseAddress!, length: weightLength, options: [.storageModeShared]) }
        rmuV16BSpeciesIdentityLoaded = rmuV16BSpeciesIDBuffer != nil && rmuV16BFamilyIDBuffer != nil && rmuV16BSpeciesWeightBuffer != nil
        rmuV16BSpeciesIdentityRecordCount = records
        rmuV16BSpeciesIdentityParticleCount = particleCount
        rmuV16BSpeciesIdentityStatus = records == particleCount ? "loaded \\(records)/\\(particleCount)" : "loaded \\(records)/\\(particleCount) count mismatch handled"
        print("RMU v1.6B species identity: \\(rmuV16BSpeciesIdentityStatus)")
    }
    // RMU_V1_6B_SPECIES_IDENTITY_LOADER_END

    func updateParticleBufferIfNeeded() {
        var particles = frameLoader.particles // RMU_V1_11A mutable for large volumetric expansion
        guard !particles.isEmpty else { return }

        let currentMod = frameLoader.lastModificationDate
        let sameUpload = particleBuffer != nil &&
            liveParticleBuffer != nil &&
            velocityParticleBuffer != nil &&
            lastUploadedParticleCount == particles.count &&
            lastUploadedModificationDate == currentMod
        if sameUpload {
            // RMU_V1_6B_SAME_UPLOAD_IDENTITY_CALL
            rmuV16BLoadSpeciesIdentityBuffersForParticleCount(particles.count)
            return
        }

        let byteCount = particles.count * MemoryLayout<Particle>.stride

        // RMU_V1_11A_LARGE_VOLUMETRIC_DOMAIN_PARTICLE_EXPANSION_BEGIN
        // Convert the compact crab field into a large volumetric geospatial domain.
        // Longitude-derived x and latitude-derived z are expanded strongly.
        // Depth-derived y is amplified, with deterministic jitter to break planar compression.
        // Disable with environment variable RMU_DISABLE_VOLUMETRIC_DOMAIN=1.
        if ProcessInfo.processInfo.environment["RMU_DISABLE_VOLUMETRIC_DOMAIN"] != "1" {
            let rmuV111AXScale: Float = 28.0
            let rmuV111AYScale: Float = 22.0
            let rmuV111AZScale: Float = 32.0
            let rmuV111AJitter: Float = 0.35
            let rmuV111ADepthJitter: Float = 3.0

            for rmuV111AIndex in particles.indices {
                let seed = Float((rmuV111AIndex % 9973) + 1)
                let jx = Float(sin(Double(seed) * 12.9898)) * rmuV111AJitter
                let jy = Float(sin(Double(seed) * 78.2330)) * rmuV111ADepthJitter
                let jz = Float(sin(Double(seed) * 37.7190)) * rmuV111AJitter

                var p = particles[rmuV111AIndex].position
                p.x = p.x * rmuV111AXScale + jx
                p.y = p.y * rmuV111AYScale + jy
                p.z = p.z * rmuV111AZScale + jz

                particles[rmuV111AIndex] = Particle(position: p)
            }

            print("RMU v1.11A large volumetric domain applied to \(particles.count) particles")
        }
        // RMU_V1_11A_LARGE_VOLUMETRIC_DOMAIN_PARTICLE_EXPANSION_END

        guard let baseBuffer = device.makeBuffer(bytes: particles, length: byteCount, options: [.storageModeShared]),
              let liveBuffer = device.makeBuffer(bytes: particles, length: byteCount, options: [.storageModeShared]) else { return }

        var zeroVelocities = Array(repeating: Particle(position: SIMD3<Float>(0, 0, 0)), count: particles.count)
        guard let velocityBuffer = device.makeBuffer(bytes: zeroVelocities, length: byteCount, options: [.storageModeShared]) else { return }

        baseParticleBuffer = baseBuffer
        liveParticleBuffer = liveBuffer
        velocityParticleBuffer = velocityBuffer
        // RMU_V1_6B_CREATE_IDENTITY_BUFFERS_AFTER_GPU_BUFFERS
        rmuV16BLoadSpeciesIdentityBuffersForParticleCount(particles.count)
        particleBuffer = liveBuffer
        lastUploadedParticleCount = particles.count
        lastUploadedModificationDate = currentMod

        // Trails are expensive at 99,966 geospatial points and destroy frame rate.
        // Keep them opt-in after the GPU particle engine is stable.
        trailBuffers.removeAll()
        trailCounts.removeAll()

        print("RMU v1.3F6 GPU particle buffers initialized: count=\(particles.count), compute=\(computePipelineState != nil), displayCap=\(geospatialDisplayParticleLimit)")
    }

    func resetGeospatialParticleState() {
        updateParticleBufferIfNeeded()
        guard let base = baseParticleBuffer,
              let live = liveParticleBuffer,
              let velocity = velocityParticleBuffer,
              lastUploadedParticleCount > 0 else {
            print("RMU v1.3F6 reset requested, but GPU particle buffers are not ready.")
            return
        }

        let byteCount = lastUploadedParticleCount * MemoryLayout<Particle>.stride
        memcpy(live.contents(), base.contents(), byteCount)
        memset(velocity.contents(), 0, byteCount)
        fieldPhase = 0.0
        clearTrails()
        print("RMU v1.3F6 particle reset: live particles restored to crab-data seed positions; velocities cleared.")
        hud?.updateText()
    }


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
        return "\(enabled ? "ON" : "OFF") code \(code) src \(rmuV16GBehaviorAuthorityLabel()) gate \(gate)"
    }

    func rmuV16GFieldRecipeSummary() -> String {
        var parts: [String] = []
        for i in 0..<min(fieldLayerNames.count, fieldLayerWeights.count) {
            let enabled = i < fieldLayerEnabled.count ? fieldLayerEnabled[i] : false
            let prefix = enabled ? "*" : "-"
            parts.append("\(prefix)\(fieldLayerNames[i].prefix(3)):\(String(format: "%.2f", fieldLayerWeights[i]))")
        }
        return parts.joined(separator: " ")
    }

    func rmuV16GFieldAuthoritySummary() -> String {
        let layerName = selectedFieldLayerName.uppercased()
        return "scene \(vcvSceneIndex) layer \(selectedFieldLayerIndex + 1) \(layerName) | \(rmuV16GFieldRecipeSummary())"
    }

    func rmuV16GSpeciesIdentitySummary() -> String {
        let sid = rmuV16BSpeciesIDBuffer != nil ? "SID" : "sid?"
        let fam = rmuV16BFamilyIDBuffer != nil ? "FID" : "fid?"
        let weight = rmuV16BSpeciesWeightBuffer != nil ? "W" : "w?"
        return "\(rmuV16BSpeciesIdentityStatus) | \(sid)/\(fam)/\(weight)"
    }

    func rmuV16GColorAuthoritySummary() -> String {
        return "mode \(Int(vcvAuthorityColorMode)) \(rmuVCVColorModeDisplayName()) | draw vertex species RGB | /ch/7"
    }

    func rmuV16GVCVAuthoritySummary() -> String {
        return "\(vcvDisplayStatus()) | bridge v1.6D1 | /ch8 scene \(vcvSceneIndex) | /ch18 beh \(rmuV16GEffectiveBehaviorCode()) | /ch19 \(String(format: "%.2fV", rmuV16DBehaviorAuthorityGate)) \(rmuV16DBehaviorAuthorityActive ? "GATED" : "MANUAL")"
    }

    func rmuV16GSystemHUDSummary() -> String {
        return "v1.6G HUD | species v1.6B | color v1.6C | bridge v1.6D1 | apply v1.6F"
    }
    // RMU_V1_6G_HUD_AUTHORITY_HELPERS_END

    func printDiagnostics() {
        print("Metal renderer | fps=\(String(format: "%.1f", currentFPS)) | points=\(frameLoader.latestPointCount) | simFrame=\(frameLoader.latestFrameIndex) | runtime=\(geospatialSimulationPaused == 0 ? "geospatial_live_running" : "geospatial_static_paused") | behaviorCode=\(behaviorEffectCode) | color=\(colorModeName) | trails=\(trailsEnabled) len=\(trailLength) | presentation=\(presentationModeEnabled) | FIELD_SYSTEM=\(fieldLayersEnabled ? "ON" : "OFF") | SELECTED=\(selectedFieldLayerName) | WEIGHT=\(String(format: "%.2f", selectedFieldLayerWeight)) | ENABLED=\(fieldLayerEnabled[selectedFieldLayerIndex]) | VCV=\(vcvDisplayStatus()) | SPEED=\(String(format: "%.2f", geospatialParticleSpeed)) | MASS=\(String(format: "%.2f", geospatialParticleMass)) | TURB=\(String(format: "%.2f", geospatialParticleTurbulence)) | COH=\(String(format: "%.2f", geospatialParticleCohesion)) | WELL=\(String(format: "%.2f", geospatialGravityWellPosition))/\(String(format: "%.2f", geospatialGravityWellStrength)) | CAP=\(geospatialDisplayParticleLimit) | SAFE=\(vcvSafeModeEnabled) | SPECIES_COLOR=VERTEX | BEH18/19=VCV_GATE_DIRECT | VCV_APPLY=v1.6F_PRE_ENCODE HUD=v1.6G | \(vcvChannelCompactSummary())")
    }

    func increasePointSize() { pointSize = min(pointSize + 0.5, 12.0); hud?.updateText() }
    func decreasePointSize() { pointSize = max(pointSize - 0.5, 0.5); hud?.updateText() }
    func zoomOut() { let current = manualWorldRadius ?? frameLoader.worldRadius; manualWorldRadius = min(current * 1.15, 100.0); hud?.updateText() }
    func zoomIn() { let current = manualWorldRadius ?? frameLoader.worldRadius; manualWorldRadius = max(current / 1.15, 0.25); hud?.updateText() }
    func pan(dx: Float, dy: Float) { panX += dx; panY += dy; hud?.updateText() }
    func rotate(delta: Float) { rotationRadians += delta; hud?.updateText() }
    func resetCamera() {
        panX = 0
        panY = 0
        rotationRadians = 0
        manualWorldRadius = nil
        autoCameraEnabled = false
        activeVisualStateName = "default_camera"
        hud?.updateText()
    }

    func applyCameraPreset(_ name: String) {
        autoCameraEnabled = false
        switch name {
        case "gallery_orbit":
            panX = 0.0
            panY = 0.0
            rotationRadians = 18.0 * .pi / 180.0
            manualWorldRadius = frameLoader.worldRadius * 1.08
        case "macro_disk":
            panX = 0.0
            panY = -0.02
            rotationRadians = 0.0
            manualWorldRadius = max(frameLoader.worldRadius * 0.58, 0.25)
        case "wide_system":
            panX = 0.0
            panY = 0.0
            rotationRadians = 0.0
            manualWorldRadius = frameLoader.worldRadius * 1.55
        default:
            panX = 0.0
            panY = 0.0
            rotationRadians = 0.0
            manualWorldRadius = nil
        }
        activeVisualStateName = name
        print("Camera preset loaded: \(name)")
        hud?.updateText()
    }

    func toggleAutoCamera() {
        autoCameraEnabled.toggle()
        activeVisualStateName = autoCameraEnabled ? "auto_camera_drift" : "manual"
        print("Auto camera drift: \(autoCameraEnabled ? "ON" : "OFF")")
        hud?.updateText()
    }

    func updateAutoCamera() {
        guard autoCameraEnabled else { return }
        autoCameraPhase += 0.0035
        let base = manualWorldRadius ?? frameLoader.worldRadius
        rotationRadians += 0.0012
        panX = sin(autoCameraPhase * 0.73) * 0.035
        panY = cos(autoCameraPhase * 0.57) * 0.025
        manualWorldRadius = max(0.25, base * (1.0 + sin(autoCameraPhase * 0.37) * 0.0008))
    }

    func smoothValue(current: Float, target: Float, amount: Float) -> Float {
        let a = max(0.0, min(amount, 1.0))
        return current + (target - current) * a
    }





    func vcvDisplayStatus() -> String {
        // RMU_V1_5A14_STABLE_VCV_DISPLAY_STATUS
        // Restore documented VCV status vocabulary: ACTIVE, STALE, OFF.
        // "VCV OFF - internal fallback" was introduced during v1.5A troubleshooting and is not part of the stable HUD contract.
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





    func vcvChannelLabel(_ index: Int) -> String {
        guard index >= 0 && index < vcvChannelLabels.count else { return "unknown" }
        return vcvChannelLabels[index]
    }

    func vcvChannelTarget(_ index: Int) -> String {
        guard index >= 0 && index < vcvChannelTargets.count else { return "unknown" }
        return vcvChannelTargets[index]
    }

    func vcvChannelCompactSummary() -> String {
        // RMU_V1_5E_COMPACT_CHANNEL_SUMMARY
        if vcvDetailPanelVisible {
            return "\(rmuVCVCompactStatusLine()) | \(rmuVCVDetailPageTitle())"
        }
        return rmuVCVCompactStatusLine()
    }


    func vcvChannelEnableSummary() -> String {
        var parts: [String] = []
        for i in 0..<min(vcvChannelEnabled.count, vcvChannelLabels.count) {
            parts.append("/ch/\(i + 1) \(vcvChannelLabels[i]):\(vcvChannelEnabled[i] ? "on" : "off")")
        }
        return parts.joined(separator: " | ")
    }

    func clampVCVFieldWeight(_ value: Float, channelIndex: Int) -> Float {
        let clamped = max(0.0, min(value, 3.0))
        if abs(clamped - value) > 0.0001 {
            vcvLastClampEvent = "/ch/\(channelIndex + 1) \(vcvChannelLabel(channelIndex)) clamped \(String(format: "%.2f", value)) -> \(String(format: "%.2f", clamped))"
        }
        return clamped
    }

    func clampVCVColorMode(_ value: Int) -> Int32 {
        let clamped = max(0, min(value, 10))
        if clamped != value {
            vcvLastClampEvent = "/ch/7 color clamped \(value) -> \(clamped)"
        }
        return Int32(clamped)
    }

    func clampVCVSceneIndex(_ value: Int) -> Int {
        let clamped = max(1, min(value, 6))
        if clamped != value {
            vcvLastClampEvent = "/ch/8 scene clamped \(value) -> \(clamped)"
        }
        return clamped
    }

    func toggleVCVMonitor() {
        vcvMonitorVisible.toggle()
        print("OSC monitor: \(vcvMonitorVisible ? "ON" : "OFF")")
        hud?.updateText()
    }

    func toggleVCVSafeMode() {
        vcvSafeModeEnabled.toggle()
        print("VCV safe mode: \(vcvSafeModeEnabled ? "ON" : "OFF")")
        hud?.updateText()
    }

    func toggleVCVChannel(index: Int) {
        guard index >= 0 && index < vcvChannelEnabled.count else { return }
        vcvChannelEnabled[index].toggle()
        print("VCV channel /ch/\(index + 1) \(vcvChannelLabel(index)) -> \(vcvChannelEnabled[index] ? "enabled" : "disabled")")
        hud?.updateText()
    }

    // RMU_V1_5A7_NOTE: vcvFieldControlEnabled now defaults ON; SHIFT+V still toggles it.
    func loadVCVStateIfNeeded() {
        let now = Date().timeIntervalSince1970
        if now - vcvLastReadTime < 0.20 { return }
        vcvLastReadTime = now

        let url = URL(fileURLWithPath: projectRoot)
            .appendingPathComponent("output")
            .appendingPathComponent("vcv_state.json")

        guard let data = try? Data(contentsOf: url),
              let json = try? JSONSerialization.jsonObject(with: data, options: []) as? [String: Any] else {
            vcvStatus = "not detected"
            probabilitySource = "internal"
            return
        }


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

        if let summary = json["summary"] as? String {
            vcvLastValues = summary
        }

        
        // RMU_V1_5C_POLY_SPECIES_CONTROL_PARSE
        func rmuFloatArray(_ key: String, _ maxCount: Int) -> [Float] {
            guard let arr = json[key] as? [Any] else { return [] }
            var out: [Float] = []
            for item in arr.prefix(maxCount) {
                if let n = item as? NSNumber { out.append(n.floatValue) }
                else if let d = item as? Double { out.append(Float(d)) }
                else if let f = item as? Float { out.append(f) }
                else if let i = item as? Int { out.append(Float(i)) }
            }
            return out
        }

        func rmuIntArray(_ key: String, _ maxCount: Int) -> [Int32] {
            guard let arr = json[key] as? [Any] else { return [] }
            var out: [Int32] = []
            for item in arr.prefix(maxCount) {
                if let n = item as? NSNumber { out.append(n.int32Value) }
                else if let i = item as? Int { out.append(Int32(i)) }
                else if let d = item as? Double { out.append(Int32(d)) }
            }
            return out
        }

        func rmuCopyFloats(_ values: [Float], _ target: inout [Float], _ count: Int) {
            if values.isEmpty { return }
            for i in 0..<min(count, min(values.count, target.count)) { target[i] = values[i] }
        }

        func rmuCopyInts(_ values: [Int32], _ target: inout [Int32], _ count: Int) {
            if values.isEmpty { return }
            for i in 0..<min(count, min(values.count, target.count)) { target[i] = values[i] }
        }

        let probabilityBank = rmuFloatArray("particle_species_probability", 22)
        rmuCopyFloats(probabilityBank, &particleSpeciesProbability, 22)
        if let n = json["particle_species_probability_voice_count"] as? NSNumber { particleSpeciesProbabilityVoiceCount = n.intValue }
        if let n = json["particle_species_probability_voice_count_A"] as? NSNumber { particleSpeciesProbabilityVoiceCountA = n.intValue }
        if let n = json["particle_species_probability_voice_count_B"] as? NSNumber { particleSpeciesProbabilityVoiceCountB = n.intValue }

        let colorModeBank = rmuIntArray("particle_species_color_mode", 22)
        rmuCopyInts(colorModeBank, &particleSpeciesColorMode, 22)
        if let n = json["particle_species_color_mode_voice_count"] as? NSNumber { particleSpeciesColorModeVoiceCount = n.intValue }
        if let n = json["particle_species_color_mode_voice_count_A"] as? NSNumber { particleSpeciesColorModeVoiceCountA = n.intValue }
        if let n = json["particle_species_color_mode_voice_count_B"] as? NSNumber { particleSpeciesColorModeVoiceCountB = n.intValue }



        // RMU_V1_5G_FIELD_LAYER_WEIGHTS_PARSE
        let vcvFieldWeights = rmuFloatArray("field_layer_weights", 8)
        if !vcvFieldWeights.isEmpty {
            let count = min(vcvFieldWeights.count, fieldLayerWeights.count)
            if count > 0 {
                for i in 0..<count {
                    fieldLayerWeights[i] = vcvFieldWeights[i]
                }
            }
        }
        // RMU_V1_5G_COLOR_AUTHORITY_PARSE
        if let colorNumber = json["color_mode"] as? NSNumber {
            let c = max(Int32(0), min(Int32(10), colorNumber.int32Value))
            if vcvChannelValues.count > 6 {
                vcvChannelValues[6] = Float(c)
            }
            if vcvRawChannelValues.count > 6 {
                vcvRawChannelValues[6] = Float(c)
            }
        } else if particleSpeciesColorMode.count > 0 {
            let c = max(Int32(0), min(Int32(10), particleSpeciesColorMode[0]))
            if vcvChannelValues.count > 6 {
                vcvChannelValues[6] = Float(c)
            }
            if vcvRawChannelValues.count > 6 {
                vcvRawChannelValues[6] = Float(c)
            }
        }
        let speedBank = rmuFloatArray("particle_species_speed", 22)
        rmuCopyFloats(speedBank, &particleSpeciesSpeed, 22)
        if let n = json["particle_species_speed_voice_count"] as? NSNumber { particleSpeciesSpeedVoiceCount = n.intValue }
        if let n = json["particle_species_speed_voice_count_A"] as? NSNumber { particleSpeciesSpeedVoiceCountA = n.intValue }
        if let n = json["particle_species_speed_voice_count_B"] as? NSNumber { particleSpeciesSpeedVoiceCountB = n.intValue }

        let massBank = rmuFloatArray("particle_species_mass", 22)
        rmuCopyFloats(massBank, &particleSpeciesMass, 22)
        if let n = json["particle_species_mass_voice_count"] as? NSNumber { particleSpeciesMassVoiceCount = n.intValue }
        if let n = json["particle_species_mass_voice_count_A"] as? NSNumber { particleSpeciesMassVoiceCountA = n.intValue }
        if let n = json["particle_species_mass_voice_count_B"] as? NSNumber { particleSpeciesMassVoiceCountB = n.intValue }
        if !particleSpeciesMass.isEmpty {
            let total = particleSpeciesMass.reduce(Float(0.0), +)
            geospatialParticleMass = total / Float(max(1, particleSpeciesMass.count))
        }

        let turbulenceBank = rmuFloatArray("particle_species_turbulence", 22)
        rmuCopyFloats(turbulenceBank, &particleSpeciesTurbulence, 22)
        if let n = json["particle_species_turbulence_voice_count"] as? NSNumber { particleSpeciesTurbulenceVoiceCount = n.intValue }
        if let n = json["particle_species_turbulence_voice_count_A"] as? NSNumber { particleSpeciesTurbulenceVoiceCountA = n.intValue }
        if let n = json["particle_species_turbulence_voice_count_B"] as? NSNumber { particleSpeciesTurbulenceVoiceCountB = n.intValue }

        let cohesionBank = rmuFloatArray("particle_species_cohesion", 22)
        rmuCopyFloats(cohesionBank, &particleSpeciesCohesion, 22)
        if let n = json["particle_species_cohesion_voice_count"] as? NSNumber { particleSpeciesCohesionVoiceCount = n.intValue }
        if let n = json["particle_species_cohesion_voice_count_A"] as? NSNumber { particleSpeciesCohesionVoiceCountA = n.intValue }
        if let n = json["particle_species_cohesion_voice_count_B"] as? NSNumber { particleSpeciesCohesionVoiceCountB = n.intValue }

        if let hslNested = json["particle_species_color_hsl"] as? [[Any]] {
            var flat: [Float] = []
            for triple in hslNested.prefix(22) {
                for item in triple.prefix(3) {
                    if let n = item as? NSNumber { flat.append(n.floatValue) }
                    else if let d = item as? Double { flat.append(Float(d)) }
                }
            }
            rmuCopyFloats(flat, &particleSpeciesColorHSL, 66)
        }

        if let rgbNested = json["particle_species_color_rgb"] as? [[Any]] {
            var flat: [Float] = []
            for triple in rgbNested.prefix(22) {
                for item in triple.prefix(3) {
                    if let n = item as? NSNumber { flat.append(n.floatValue) }
                    else if let d = item as? Double { flat.append(Float(d)) }
                }
            }
            rmuCopyFloats(flat, &particleSpeciesColorRGB, 66)
        }
        if let n = json["particle_species_color_hsl_voice_count"] as? NSNumber { particleSpeciesColorVoiceCount = n.intValue }
        if let n = json["particle_species_color_hsl_voice_count_A"] as? NSNumber { particleSpeciesColorVoiceCountA = n.intValue }
        if let n = json["particle_species_color_hsl_voice_count_B"] as? NSNumber { particleSpeciesColorVoiceCountB = n.intValue }

        let gravityVec4 = rmuFloatArray("gravity_well_position_vec4", 4)
        rmuCopyFloats(gravityVec4, &gravityWellPositionVec4, 4)

        // RMU_V1_5G_SCENE_FIELD_AUTHORITY_PARSE
        // RMU_V1_6C_OPTIONAL_BEHAVIOR_CHANNEL_AUTHORITY_BEGIN
        // RMU_V1_6D_DIRECT_CHANNEL_BEHAVIOR_AUTHORITY
        //
        // /ch/8 remains scene/field only.
        // Shift+E/manual behavior remains authority by default.
        //
        // /ch/19 is a deliberate VCV behavior authority gate.
        // /ch/18 only drives behavior code while /ch/19 is >= 5V.
        //
        // v1.6D reads /ch/18 and /ch/19 directly from the JSON channel dictionaries instead
        // of relying on vcvChannelValues[17]/[18]. The log proved those channels are live in
        // vcv_state.json but can be missed by older fixed-width Swift arrays.
        func rmuV16DNumberForChannel(_ path: String) -> Float? {
            if let channels = json["channels"] as? [String: Any],
               let number = channels[path] as? NSNumber {
                return number.floatValue
            }
            if let nativeValues = json["native_channel_values"] as? [String: Any],
               let number = nativeValues[path] as? NSNumber {
                return number.floatValue
            }
            if let rawChannels = json["raw_channels"] as? [String: Any],
               let number = rawChannels[path] as? NSNumber {
                return number.floatValue
            }
            return nil
        }

        func rmuV16DVoiceCountForChannel(_ path: String) -> Int {
            if let voiceCounts = json["channel_voice_counts"] as? [String: Any],
               let number = voiceCounts[path] as? NSNumber {
                return number.intValue
            }
            if let nativeCounts = json["native_channel_voice_counts"] as? [String: Any],
               let number = nativeCounts[path] as? NSNumber {
                return number.intValue
            }
            if let details = json["channel_details"] as? [String: Any],
               let channelDetails = details[path] as? [String: Any],
               let number = channelDetails["voice_count"] as? NSNumber {
                return number.intValue
            }
            return 0
        }

        let rmuV16DBehaviorCodeVoices = rmuV16DVoiceCountForChannel("/ch/18")
        let rmuV16DBehaviorGateVoices = rmuV16DVoiceCountForChannel("/ch/19")
        let rmuV16DBehaviorCodeValue = rmuV16DNumberForChannel("/ch/18")
        let rmuV16DBehaviorGateValue = rmuV16DNumberForChannel("/ch/19")

        let rmuV16DBehaviorGateActive =
            rmuV16DBehaviorGateVoices > 0 &&
            (rmuV16DBehaviorGateValue ?? 0.0) >= 5.0

        if rmuV16DBehaviorGateActive && rmuV16DBehaviorCodeVoices > 0 {
            // RMU_V1_6D2_APPLY_DIRECT_BEHAVIOR_AUTHORITY
            let rawBehavior = Int(round(rmuV16DBehaviorCodeValue ?? 0.0))
            let clampedBehavior = Int32(max(0, min(7, rawBehavior)))
            rmuV16DBehaviorAuthorityActive = true
            rmuV16DBehaviorAuthorityCode = clampedBehavior
            rmuV16DBehaviorAuthorityGate = rmuV16DBehaviorGateValue ?? 0.0
            behaviorEffectCode = clampedBehavior
            geospatialBehaviorEnabled = true
        } else {
            rmuV16DBehaviorAuthorityActive = false
            rmuV16DBehaviorAuthorityGate = rmuV16DBehaviorGateValue ?? 0.0
        }
        // RMU_V1_6C_OPTIONAL_BEHAVIOR_CHANNEL_AUTHORITY_END

        // RMU_V1_6E_DIRECT_RENDERER_APPLY_PASS_BEGIN
        //
        // Final authority pass. This reads direct /ch/N values from vcv_state.json
        // after all older parser logic has run. It prevents old fixed arrays,
        // stale scene helpers, or legacy behavior code from missing live VCV values.
        //
        // /ch/8  = scene / field layer
        // /ch/18 = behavior code
        // /ch/19 = behavior authority gate
        func rmuV16ENumberForChannel(_ path: String) -> Float? {
            if let channels = json["channels"] as? [String: Any],
               let number = channels[path] as? NSNumber {
                return number.floatValue
            }
            if let nativeValues = json["native_channel_values"] as? [String: Any],
               let number = nativeValues[path] as? NSNumber {
                return number.floatValue
            }
            if let rawChannels = json["raw_channels"] as? [String: Any],
               let rawList = rawChannels[path] as? [Any],
               let first = rawList.first as? NSNumber {
                return first.floatValue
            }
            return nil
        }

        func rmuV16EVoiceCountForChannel(_ path: String) -> Int {
            if let counts = json["channel_voice_counts"] as? [String: Any],
               let number = counts[path] as? NSNumber {
                return number.intValue
            }
            if let nativeCounts = json["native_channel_voice_counts"] as? [String: Any],
               let number = nativeCounts[path] as? NSNumber {
                return number.intValue
            }
            return 0
        }

        if let sceneValue = rmuV16ENumberForChannel("/ch/8"),
           rmuV16EVoiceCountForChannel("/ch/8") > 0 {
            let directScene = max(1, min(6, Int(round(sceneValue))))
            vcvSceneIndex = directScene

            if fieldLayerWeights.count > 0 {
                selectedFieldLayerIndex = max(0, min(fieldLayerWeights.count - 1, directScene - 1))
            }
        }

        let rmuV16EBehaviorGateValue = rmuV16ENumberForChannel("/ch/19") ?? 0.0
        let rmuV16EBehaviorGateActive =
            rmuV16EVoiceCountForChannel("/ch/19") > 0 &&
            rmuV16EBehaviorGateValue >= 5.0

        if rmuV16EBehaviorGateActive,
           rmuV16EVoiceCountForChannel("/ch/18") > 0,
           let behaviorValue = rmuV16ENumberForChannel("/ch/18") {
            let directBehavior = Int32(max(0, min(7, Int(round(behaviorValue)))))
            behaviorEffectCode = directBehavior
            geospatialBehaviorEnabled = true

            rmuV16DBehaviorAuthorityActive = true
            rmuV16DBehaviorAuthorityCode = directBehavior
            rmuV16DBehaviorAuthorityGate = rmuV16EBehaviorGateValue
        }
        // RMU_V1_6E_DIRECT_RENDERER_APPLY_PASS_END


        if let sceneNumber = json["scene_index"] as? NSNumber {
            let scene = max(1, min(6, sceneNumber.intValue))
            vcvSceneIndex = scene

            if fieldLayerWeights.count > 0 {
                selectedFieldLayerIndex = max(0, min(fieldLayerWeights.count - 1, scene - 1))
            }

            // RMU_V1_6B2_BEHAVIOR_AUTHORITY_REPAIR
            // /ch/8 controls scene and field-layer selection only.
            // Do not overwrite behaviorEffectCode here.
            // Shift+E/manual behavior controls remain the authority for behavior cycling.
        }

if let probabilityNumber = (json["probability_value"] as? NSNumber) ?? (json["probability"] as? NSNumber) {
            let raw = Float(probabilityNumber.doubleValue)
            vcvRawChannelValues[0] = raw
            vcvChannelValues[0] = vcvSafeModeEnabled ? max(0.0, min(raw, 1.0)) : raw
        }

        if let weights = json["field_layer_weights"] as? [NSNumber], weights.count == fieldLayerWeights.count {
            for i in 0..<fieldLayerWeights.count {
                let raw = Float(weights[i].doubleValue)
                let channelIndex = i + 1
                vcvRawChannelValues[channelIndex] = raw
                let target = vcvSafeModeEnabled ? clampVCVFieldWeight(raw, channelIndex: channelIndex) : raw
                vcvChannelValues[channelIndex] = target
                if vcvFieldControlEnabled && externalDetected && vcvChannelEnabled[channelIndex] {
                    fieldLayerWeights[i] = smoothValue(current: fieldLayerWeights[i], target: target, amount: vcvSmoothingAmount)
                }
            }
            if vcvFieldControlEnabled && externalDetected {
                lastVisualStateMessage = "VCV generic field input active"
            }
        }

        if let colorNumber = json["color_mode"] as? NSNumber {
            let rawColor = colorNumber.intValue
            let c = vcvSafeModeEnabled ? clampVCVColorMode(rawColor) : Int32(rawColor)
            vcvRawChannelValues[6] = Float(rawColor)
            vcvChannelValues[6] = Float(c)
            if vcvFieldControlEnabled && externalDetected && vcvChannelEnabled[6] {
                colorMode = c
            }
        }


        // RMU_V1_9M_COLOR_OVERRIDE_FINAL_APPLY
        var rmuV19MColorCandidate: Int? = nil
        if let topColor = json["color_mode"] as? NSNumber {
            rmuV19MColorCandidate = topColor.intValue
        }
        if rmuV19MColorCandidate == nil,
           let channelsDict = json["channels"] as? [String: Any],
           let ch7 = channelsDict["/ch/7"] as? [String: Any] {
            if let n = (ch7["value"] as? NSNumber) ?? (ch7["mapped"] as? NSNumber) ?? (ch7["raw"] as? NSNumber) {
                rmuV19MColorCandidate = n.intValue
            }
        }
        let rmuV19MColorURL = URL(fileURLWithPath: projectRoot)
            .appendingPathComponent("output")
            .appendingPathComponent("color_override_state.json")
        if let colorData = try? Data(contentsOf: rmuV19MColorURL),
           let colorJSON = try? JSONSerialization.jsonObject(with: colorData, options: []) as? [String: Any],
           let colorNumber = colorJSON["color_mode"] as? NSNumber {
            rmuV19MColorCandidate = colorNumber.intValue
        }
        if let rawColor = rmuV19MColorCandidate {
            let c = vcvSafeModeEnabled ? clampVCVColorMode(rawColor) : Int32(max(0, min(10, rawColor)))
            vcvRawChannelValues[6] = Float(rawColor)
            vcvChannelValues[6] = Float(c)
            rmuApplyVCVColorAuthority(c)
        }

        if let sceneNumber = json["scene_index"] as? NSNumber {
            let rawScene = sceneNumber.intValue
            let scene = vcvSafeModeEnabled ? clampVCVSceneIndex(rawScene) : rawScene
            vcvRawChannelValues[7] = Float(rawScene)
            vcvChannelValues[7] = Float(scene)
        }

        // RMU_V1_3F5_SPEED_MASS_PARSE: /ch/9 particle speed and /ch/10 particle mass from bipolar Lorenz/VCV OSC.
        func bipolarSpeedFromRaw(_ raw: Float) -> Float {
            return max(-3.0, min((raw / 5.0) * 3.0, 3.0))
        }
        func massFromBipolarRaw(_ raw: Float) -> Float {
            let n = max(0.0, min((raw + 5.0) / 10.0, 1.0))
            return 0.20 + n * 4.80
        }

        var speedMappedOptional: Float? = nil
        var speedRawOptional: Float? = nil
        if let n = json["particle_speed"] as? NSNumber {
            speedMappedOptional = Float(n.doubleValue)
        }
        if let n = json["particle_speed_raw"] as? NSNumber {
            speedRawOptional = Float(n.doubleValue)
        } else if let rawChannelValues = json["raw_channels"] as? [NSNumber], rawChannelValues.count >= 9 {
            speedRawOptional = Float(rawChannelValues[8].doubleValue)
        } else if let rawChannelValues = json["raw_channel_values"] as? [NSNumber], rawChannelValues.count >= 9 {
            speedRawOptional = Float(rawChannelValues[8].doubleValue)
        }
        if speedMappedOptional == nil, let raw = speedRawOptional {
            speedMappedOptional = bipolarSpeedFromRaw(raw)
        }
        if let speedMapped = speedMappedOptional {
            let clamped = max(-3.0, min(speedMapped, 3.0))
            if vcvRawChannelValues.count >= 9 { vcvRawChannelValues[8] = speedRawOptional ?? clamped }
            if vcvChannelValues.count >= 9 { vcvChannelValues[8] = clamped }
            if externalDetected && vcvChannelEnabled.count >= 9 && vcvChannelEnabled[8] {
                geospatialParticleSpeed = smoothValue(current: geospatialParticleSpeed, target: clamped, amount: vcvSmoothingAmount)
            }
        }

        var massMappedOptional: Float? = nil
        var massRawOptional: Float? = nil
        if let n = json["particle_mass"] as? NSNumber {
            massMappedOptional = Float(n.doubleValue)
        }
        if let n = json["particle_mass_raw"] as? NSNumber {
            massRawOptional = Float(n.doubleValue)
        } else if let rawChannelValues = json["raw_channels"] as? [NSNumber], rawChannelValues.count >= 10 {
            massRawOptional = Float(rawChannelValues[9].doubleValue)
        } else if let rawChannelValues = json["raw_channel_values"] as? [NSNumber], rawChannelValues.count >= 10 {
            massRawOptional = Float(rawChannelValues[9].doubleValue)
        }
        if massMappedOptional == nil, let raw = massRawOptional {
            massMappedOptional = massFromBipolarRaw(raw)
        }
        if let massMapped = massMappedOptional {
            let clamped = max(0.20, min(massMapped, 5.00))
            if vcvRawChannelValues.count >= 10 { vcvRawChannelValues[9] = massRawOptional ?? clamped }
            if vcvChannelValues.count >= 10 { vcvChannelValues[9] = clamped }
            if externalDetected && vcvChannelEnabled.count >= 10 && vcvChannelEnabled[9] {
                geospatialParticleMass = smoothValue(current: geospatialParticleMass, target: clamped, amount: vcvSmoothingAmount)
            }
        }
        // RMU_V1_3F8_TURB_COH_PARSE: /ch/11 particle turbulence and /ch/12 particle cohesion.
        func turbulenceFromBipolarRaw(_ raw: Float) -> Float {
            let n = max(0.0, min((raw + 5.0) / 10.0, 1.0))
            return max(0.0, min(n * 2.50, 2.50))
        }
        func cohesionFromBipolarRaw(_ raw: Float) -> Float {
            let n = max(0.0, min((raw + 5.0) / 10.0, 1.0))
            return max(0.0, min(n * 3.00, 3.00))
        }

        var turbulenceMappedOptional: Float? = nil
        var turbulenceRawOptional: Float? = nil
        if let n = json["particle_turbulence"] as? NSNumber { turbulenceMappedOptional = Float(n.doubleValue) }
        if let n = json["particle_turbulence_raw"] as? NSNumber { turbulenceRawOptional = Float(n.doubleValue) }
        else if let rawChannelValues = json["raw_channels"] as? [NSNumber], rawChannelValues.count >= 11 { turbulenceRawOptional = Float(rawChannelValues[10].doubleValue) }
        else if let rawChannelValues = json["raw_channel_values"] as? [NSNumber], rawChannelValues.count >= 11 { turbulenceRawOptional = Float(rawChannelValues[10].doubleValue) }
        if turbulenceMappedOptional == nil, let raw = turbulenceRawOptional { turbulenceMappedOptional = turbulenceFromBipolarRaw(raw) }
        if let turbulenceMapped = turbulenceMappedOptional {
            let clamped = max(0.0, min(turbulenceMapped, 2.50))
            if vcvRawChannelValues.count >= 11 { vcvRawChannelValues[10] = turbulenceRawOptional ?? clamped }
            if vcvChannelValues.count >= 11 { vcvChannelValues[10] = clamped }
            if externalDetected && vcvChannelEnabled.count >= 11 && vcvChannelEnabled[10] { geospatialParticleTurbulence = smoothValue(current: geospatialParticleTurbulence, target: clamped, amount: vcvSmoothingAmount) }
        }

        var cohesionMappedOptional: Float? = nil
        var cohesionRawOptional: Float? = nil
        if let n = json["particle_cohesion"] as? NSNumber { cohesionMappedOptional = Float(n.doubleValue) }
        if let n = json["particle_cohesion_raw"] as? NSNumber { cohesionRawOptional = Float(n.doubleValue) }
        else if let rawChannelValues = json["raw_channels"] as? [NSNumber], rawChannelValues.count >= 12 { cohesionRawOptional = Float(rawChannelValues[11].doubleValue) }
        else if let rawChannelValues = json["raw_channel_values"] as? [NSNumber], rawChannelValues.count >= 12 { cohesionRawOptional = Float(rawChannelValues[11].doubleValue) }
        if cohesionMappedOptional == nil, let raw = cohesionRawOptional { cohesionMappedOptional = cohesionFromBipolarRaw(raw) }
        if let cohesionMapped = cohesionMappedOptional {
            let clamped = max(0.0, min(cohesionMapped, 3.00))
            if vcvRawChannelValues.count >= 12 { vcvRawChannelValues[11] = cohesionRawOptional ?? clamped }
            if vcvChannelValues.count >= 12 { vcvChannelValues[11] = clamped }
            if externalDetected && vcvChannelEnabled.count >= 12 && vcvChannelEnabled[11] { geospatialParticleCohesion = smoothValue(current: geospatialParticleCohesion, target: clamped, amount: vcvSmoothingAmount) }
        }
    
        // RMU_V1_4B11_LOADVCVSTATE_CH13_CH14_DIRECT_FIX
        // Direct renderer-side propagation for /ch/13 and /ch/14.
        // The Python bridge JSON has already been verified correct. This block mirrors
        // the working /ch/9-/ch/12 pattern by copying bridge state into the renderer arrays.
        func rmuV14B11GravityPositionFromRaw(_ raw: Float) -> Float {
            return max(-1.0, min(raw / 5.0, 1.0))
        }

        func rmuV14B11GravityStrengthFromRaw(_ raw: Float) -> Float {
            let normalized = max(0.0, min((raw + 5.0) / 10.0, 1.0))
            return max(0.0, min(normalized * 12.0, 12.0))
        }

        var rmuCh13Raw: Float? = nil
        var rmuCh13Mapped: Float? = nil
        if let n = json["gravity_well_position_raw"] as? NSNumber {
            rmuCh13Raw = Float(n.doubleValue)
        } else if let rawChannelValues = json["raw_channels"] as? [NSNumber], rawChannelValues.count >= 13 {
            rmuCh13Raw = Float(rawChannelValues[12].doubleValue)
        } else if let rawChannelValues = json["raw_channel_values"] as? [NSNumber], rawChannelValues.count >= 13 {
            rmuCh13Raw = Float(rawChannelValues[12].doubleValue)
        }
        if let n = json["gravity_well_position"] as? NSNumber {
            rmuCh13Mapped = Float(n.doubleValue)
        } else if let raw = rmuCh13Raw {
            rmuCh13Mapped = rmuV14B11GravityPositionFromRaw(raw)
        }
        if let raw = rmuCh13Raw, vcvRawChannelValues.count >= 13 {
            vcvRawChannelValues[12] = raw
        }
        if let mapped = rmuCh13Mapped, vcvChannelValues.count >= 13 {
            vcvChannelValues[12] = max(-1.0, min(mapped, 1.0))
        }

        var rmuCh14Raw: Float? = nil
        var rmuCh14Mapped: Float? = nil
        if let n = json["gravity_well_strength_raw"] as? NSNumber {
            rmuCh14Raw = Float(n.doubleValue)
        } else if let rawChannelValues = json["raw_channels"] as? [NSNumber], rawChannelValues.count >= 14 {
            rmuCh14Raw = Float(rawChannelValues[13].doubleValue)
        } else if let rawChannelValues = json["raw_channel_values"] as? [NSNumber], rawChannelValues.count >= 14 {
            rmuCh14Raw = Float(rawChannelValues[13].doubleValue)
        }
        if let n = json["gravity_well_strength"] as? NSNumber {
            rmuCh14Mapped = Float(n.doubleValue)
        } else if let raw = rmuCh14Raw {
            rmuCh14Mapped = rmuV14B11GravityStrengthFromRaw(raw)
        }
        if let raw = rmuCh14Raw, vcvRawChannelValues.count >= 14 {
            vcvRawChannelValues[13] = raw
        }
        if let mapped = rmuCh14Mapped, vcvChannelValues.count >= 14 {
            vcvChannelValues[13] = max(0.0, min(mapped, 12.0))
        }

}



    // RMU_V1_9O_DATASET_COUPLING_OPERATOR_AUTHORITY_BEGIN
    func rmuV19OReadJSONDict(_ parts: [String]) -> [String: Any] {
        var url = URL(fileURLWithPath: projectRoot)
        for part in parts { url.appendPathComponent(part) }
        guard let data = try? Data(contentsOf: url),
              let obj = try? JSONSerialization.jsonObject(with: data, options: []) as? [String: Any] else { return [:] }
        return obj
    }

    func rmuV19OWriteJSONDict(_ obj: [String: Any], _ parts: [String]) {
        var url = URL(fileURLWithPath: projectRoot)
        for part in parts { url.appendPathComponent(part) }
        try? FileManager.default.createDirectory(at: url.deletingLastPathComponent(), withIntermediateDirectories: true)
        if let data = try? JSONSerialization.data(withJSONObject: obj, options: [.prettyPrinted, .sortedKeys]) {
            try? data.write(to: url, options: [.atomic])
        }
    }

    func rmuV19ODatasetCouplingMode() -> String {
        let op = rmuV19OReadJSONDict(["output", "operator_authority_state.json"])
        if let s = op["dataset_coupling_mode"] as? String, !s.isEmpty { return s.lowercased() }
        let manual = rmuV19OReadJSONDict(["output", "manual_authority_mode.json"])
        if let s = manual["dataset_coupling_mode"] as? String, !s.isEmpty { return s.lowercased() }
        let dc = rmuV19OReadJSONDict(["output", "dataset_coupling_state.json"])
        if let s = dc["mode"] as? String, !s.isEmpty { return s.lowercased() }
        if let b = dc["enabled"] as? Bool { return b ? "apply" : "observe" }
        return "observe"
    }

    func rmuV19ODataCouplingApplyEnabled() -> Bool {
        let mode = rmuV19ODatasetCouplingMode()
        return mode == "apply" || mode == "on" || mode == "active" || mode == "enabled"
    }

    func rmuV19OSetDatasetCouplingMode(_ requestedMode: String, reason: String = "renderer_toggle") {
        let mode = requestedMode.lowercased() == "apply" ? "apply" : "observe"
        let enabled = mode == "apply"
        var op = rmuV19OReadJSONDict(["output", "operator_authority_state.json"])
        op["dataset_coupling_mode"] = mode
        op["dataset_coupling_enabled"] = enabled
        op["auto_fields_enabled"] = enabled
        op["active_auto_domain"] = enabled ? "dataset_coupling" : (op["active_auto_domain"] ?? "manual")
        op["last_hotkey_reason"] = "dataset_coupling_\(mode)_\(reason)"
        op["updated_by"] = "MetalRenderer.v1_9O"
        op["updated_unix"] = Date().timeIntervalSince1970
        rmuV19OWriteJSONDict(op, ["output", "operator_authority_state.json"])

        var manual = rmuV19OReadJSONDict(["output", "manual_authority_mode.json"])
        manual["dataset_coupling_mode"] = mode
        manual["auto_fields_enabled"] = enabled
        manual["updated_by"] = "MetalRenderer.v1_9O"
        manual["updated_unix"] = Date().timeIntervalSince1970
        rmuV19OWriteJSONDict(manual, ["output", "manual_authority_mode.json"])

        var dc = rmuV19OReadJSONDict(["output", "dataset_coupling_state.json"])
        dc["mode"] = mode
        dc["enabled"] = enabled
        dc["apply_enabled"] = enabled
        dc["status"] = enabled ? "active" : "observe"
        dc["summary"] = enabled ? "dataset coupling apply enabled by v1.9O" : "dataset coupling observe only by v1.9O"
        dc["updated_by"] = "MetalRenderer.v1_9O"
        dc["updated_unix"] = Date().timeIntervalSince1970
        rmuV19OWriteJSONDict(dc, ["output", "dataset_coupling_state.json"])
    }
    // RMU_V1_9O_DATASET_COUPLING_OPERATOR_AUTHORITY_END

    func datasetCouplingStateURL() -> URL {
        URL(fileURLWithPath: projectRoot)
            .appendingPathComponent("output")
            .appendingPathComponent("dataset_coupling_state.json")
    }

    func clampDataWeight(_ value: Float) -> Float {
        max(0.0, min(value, 3.0))
    }

    func loadDatasetCouplingIfNeeded() {
        let now = Date().timeIntervalSince1970
        if now - dataCouplingLastReadTime < 0.20 { return }
        dataCouplingLastReadTime = now

        let url = datasetCouplingStateURL()
        guard let data = try? Data(contentsOf: url),
              let json = try? JSONSerialization.jsonObject(with: data, options: []) as? [String: Any] else {
            dataCouplingLoaded = false
            dataCouplingFallbackActive = true
            dataCouplingStatus = "missing coupling state"
            dataCouplingFallbackReason = "output/dataset_coupling_state.json not readable"
            dataCouplingSummary = "dataset coupling missing"
            return
        }

        dataCouplingLoaded = (json["loaded"] as? Bool) ?? false
        dataCouplingFallbackActive = (json["fallback_active"] as? Bool) ?? true
        dataCouplingStatus = (json["status"] as? String) ?? (dataCouplingLoaded ? "loaded" : "fallback")
        dataCouplingFallbackReason = (json["fallback_reason"] as? String) ?? "none"
        dataCouplingSource = (json["source"] as? String) ?? "dataset_coupling_state.json"
        dataCouplingSummary = (json["summary"] as? String) ?? "dataset coupling active"

        // RMU_V1_9M_DATASET_COUPLING_AUTHORITY_SYNC
        // The external HUD and Shift+B now drive dataset coupling through operator_authority_state.json.
        // "apply" means dataset coupling may actually drive field-layer weights; observe/off means read-only.
        dataCouplingEnabled = rmuV17JDatasetCouplingApplyEnabled()

        if let gainNumber = json["gain"] as? NSNumber {
            dataCouplingGain = Float(gainNumber.doubleValue)
        }
        if let smoothNumber = json["smooth"] as? NSNumber {
            dataCouplingSmooth = max(0.01, min(Float(smoothNumber.doubleValue), 1.0))
        }
        if let values = json["values"] as? [String: Any] {
            for (key, value) in values {
                if let n = value as? NSNumber { dataCouplingValues[key] = Float(n.doubleValue) }
            }
        }
        if let targets = json["field_layer_targets"] as? [NSNumber], targets.count == fieldLayerWeights.count {
            dataCouplingTargets = targets.map { clampDataWeight(Float($0.doubleValue)) }
        }

        // RMU_V1_9M_DATASET_COUPLING_APPLY_GUARD
        let rmuV19MCouplingMode = (rmuV17JControlModeObject()["dataset_coupling_mode"] as? String ?? "observe").lowercased()
        let rmuV19MApply = rmuV19MCouplingMode == "apply"
        dataCouplingEnabled = rmuV19MApply
        if !rmuV19MApply {
            dataCouplingStatus = rmuV19MCouplingMode == "off" ? "off" : "observe"
            dataCouplingSummary = "dataset coupling \(dataCouplingStatus); read-only, not applied"
            return
        }
        if dataCouplingLoaded && !dataCouplingFallbackActive {
            dataCouplingStatus = "active"
            dataCouplingSummary = "dataset coupling apply mode active"
            applyDatasetCouplingTargets()
        }
    }

    func applyDatasetCouplingTargets() {
        guard dataCouplingTargets.count == fieldLayerWeights.count else { return }
        for i in 0..<fieldLayerWeights.count {
            let target = clampDataWeight(dataCouplingTargets[i] * max(0.0, dataCouplingGain))
            fieldLayerWeights[i] = smoothValue(current: fieldLayerWeights[i], target: target, amount: dataCouplingSmooth)
        }
        if (dataCouplingValues["temperature_drive"] ?? 0.0) > 0.05 {
            fieldLayerEnabled[3] = true
        }
        lastVisualStateMessage = "dataset coupling active"
    }

    func toggleDataCoupling() {
        let nextMode = rmuV19ODataCouplingApplyEnabled() ? "observe" : "apply"
        rmuV19OSetDatasetCouplingMode(nextMode, reason: "shift_b")
        dataCouplingEnabled = nextMode == "apply"
        dataCouplingStatus = dataCouplingEnabled ? "active" : "observe"
        dataCouplingSummary = dataCouplingEnabled ? "dataset coupling apply enabled" : "dataset coupling observe only"
        print("Dataset coupling: \(dataCouplingEnabled ? "ON/APPLY" : "OBSERVE/OFF")")
        hud?.updateText()
    }

    func cycleDataCouplingGain() {
        let options: [Float] = [0.25, 0.50, 1.00, 1.50, 2.00]
        let currentIndex = options.enumerated().min(by: { abs($0.element - dataCouplingGain) < abs($1.element - dataCouplingGain) })?.offset ?? 2
        let next = (currentIndex + 1) % options.count
        dataCouplingGain = options[next]
        print("Dataset coupling gain: \(String(format: "%.2f", dataCouplingGain))")
        hud?.updateText()
    }

    func dataCouplingPanelSummary() -> String {
        let c = dataCouplingValues["curvature_drive"] ?? 0.0
        let temp = dataCouplingValues["temperature_drive"] ?? 0.0
        let h = dataCouplingValues["higgs_drive"] ?? 0.0
        let p = dataCouplingValues["probability_drive"] ?? 0.0
        let v = dataCouplingValues["vertical_drive"] ?? 0.0
        return "COUPLING: \(dataCouplingEnabled ? "ON" : "OFF")  loaded \(dataCouplingLoaded)  fallback \(dataCouplingFallbackActive)  gain \(String(format: "%.2f", dataCouplingGain))  smooth \(String(format: "%.2f", dataCouplingSmooth)) | drive C \(String(format: "%.3f", c)) T \(String(format: "%.3f", temp)) H \(String(format: "%.3f", h)) P \(String(format: "%.3f", p)) Y \(String(format: "%.3f", v))"
    }

    func datasetCouplingControlState() -> [String: Any] {
        return [
            "version": "1.2A",
            "enabled": dataCouplingEnabled,
            "loaded": dataCouplingLoaded,
            "fallback_active": dataCouplingFallbackActive,
            "fallback_reason": dataCouplingFallbackReason,
            "status": dataCouplingStatus,
            "source": dataCouplingSource,
            "gain": dataCouplingGain,
            "smooth": dataCouplingSmooth,
            "summary": dataCouplingSummary,
            "values": dataCouplingValues,
            "field_layer_targets": dataCouplingTargets,
            "applied_field_layer_weights": fieldLayerWeights
        ]
    }

    func toggleVCVFieldControl() {
        vcvFieldControlEnabled.toggle()
        probabilitySource = vcvFieldControlEnabled ? "hybrid" : "internal"
        print("VCV field control: \(vcvFieldControlEnabled ? "ON" : "OFF")")
        hud?.updateText()
    }

    func visualStateDictionary(name: String, slot: Int? = nil) -> [String: Any] {
        return [
            "version": "1.2B",
            "name": name,
            "slot": slot as Any,
            "created_unix": Date().timeIntervalSince1970,
            "camera": [
                "pan_x": panX,
                "pan_y": panY,
                "rotation_radians": rotationRadians,
                "manual_world_radius": manualWorldRadius as Any,
                "auto_camera_enabled": autoCameraEnabled
            ],
            "render": [
                "point_size": pointSize,
                "color_mode": colorMode,
                "trails_enabled": trailsEnabled,
                "trail_length": trailLength,
                "grid_enabled": gridEnabled,
                "center_marker_enabled": centerMarkerEnabled,
                "horizon_ring_enabled": horizonRingEnabled,
                "curvature_overlay_enabled": curvatureOverlayEnabled,
                "probability_overlay_enabled": probabilityOverlayEnabled
            ],
            "vcv": [
                "vcv_field_control_enabled": vcvFieldControlEnabled,
                "probability_source": probabilitySource,
                "vcv_monitor_visible": vcvMonitorVisible,
                "vcv_smoothing_amount": vcvSmoothingAmount,
                "vcv_channel_enabled": vcvChannelEnabled,
                "vcv_channel_labels": vcvChannelLabels,
                "vcv_channel_targets": vcvChannelTargets,
                "vcv_safe_mode_enabled": false,
                "vcv_compact_hud_mode": vcvCompactHUDMode,
                "vcv_detail_panel_visible": vcvDetailPanelVisible,
                "vcv_detail_page_index": vcvDetailPageIndex,
                "vcv_authority_scene_index": vcvAuthoritySceneIndex,
                "vcv_authority_color_mode": vcvAuthorityColorMode,
                "vcv_authority_field_layer_index": vcvAuthorityFieldLayerIndex
            ],
            "fields": [
                "field_layers_enabled": fieldLayersEnabled,
                "selected_field_layer_index": selectedFieldLayerIndex,
                "field_layer_names": fieldLayerNames,
                "field_layer_enabled": fieldLayerEnabled,
                "field_layer_weights": fieldLayerWeights
            ]
        ]
    }

    func applyVisualState(_ state: [String: Any], fallbackName: String) {
        if let camera = state["camera"] as? [String: Any] {
            panX = Float((camera["pan_x"] as? NSNumber)?.doubleValue ?? 0.0)
            panY = Float((camera["pan_y"] as? NSNumber)?.doubleValue ?? 0.0)
            rotationRadians = Float((camera["rotation_radians"] as? NSNumber)?.doubleValue ?? 0.0)
            if let radiusNumber = camera["manual_world_radius"] as? NSNumber {
                manualWorldRadius = Float(radiusNumber.doubleValue)
            } else {
                manualWorldRadius = nil
            }
            autoCameraEnabled = (camera["auto_camera_enabled"] as? Bool) ?? false
        }

        if let render = state["render"] as? [String: Any] {
            pointSize = Float((render["point_size"] as? NSNumber)?.doubleValue ?? Double(pointSize))
            colorMode = Int32((render["color_mode"] as? NSNumber)?.intValue ?? Int(colorMode))
            trailsEnabled = (render["trails_enabled"] as? Bool) ?? trailsEnabled
            trailLength = (render["trail_length"] as? NSNumber)?.intValue ?? trailLength
            gridEnabled = (render["grid_enabled"] as? Bool) ?? gridEnabled
            centerMarkerEnabled = (render["center_marker_enabled"] as? Bool) ?? centerMarkerEnabled
            horizonRingEnabled = (render["horizon_ring_enabled"] as? Bool) ?? horizonRingEnabled
            curvatureOverlayEnabled = (render["curvature_overlay_enabled"] as? Bool) ?? curvatureOverlayEnabled
            probabilityOverlayEnabled = (render["probability_overlay_enabled"] as? Bool) ?? probabilityOverlayEnabled
        }

        if let vcv = state["vcv"] as? [String: Any] {
            vcvFieldControlEnabled = (vcv["vcv_field_control_enabled"] as? Bool) ?? vcvFieldControlEnabled
            probabilitySource = (vcv["probability_source"] as? String) ?? probabilitySource
            vcvMonitorVisible = (vcv["vcv_monitor_visible"] as? Bool) ?? vcvMonitorVisible
            if let smoothingNumber = vcv["vcv_smoothing_amount"] as? NSNumber {
                vcvSmoothingAmount = max(0.0, min(Float(smoothingNumber.doubleValue), 1.0))
            }
            if let enabled = vcv["vcv_channel_enabled"] as? [Bool], enabled.count == vcvChannelEnabled.count {
                vcvChannelEnabled = enabled
            }
            if let labels = vcv["vcv_channel_labels"] as? [String], labels.count == vcvChannelLabels.count {
                vcvChannelLabels = labels
            }
            if let targets = vcv["vcv_channel_targets"] as? [String], targets.count == vcvChannelTargets.count {
                vcvChannelTargets = targets
            }
            // RMU_V1_5F_SAFE_MODE_RUNTIME_OVERRIDE
            // v1.5D+ bridge output is already mapped/clamped. Do not resurrect old SAFE=true runtime state.
            vcvSafeModeEnabled = false
            vcvCompactHUDMode = (vcv["vcv_compact_hud_mode"] as? Bool) ?? vcvCompactHUDMode
            vcvDetailPanelVisible = (vcv["vcv_detail_panel_visible"] as? Bool) ?? vcvDetailPanelVisible
            vcvDetailPageIndex = (vcv["vcv_detail_page_index"] as? Int) ?? vcvDetailPageIndex
            vcvAuthoritySceneIndex = (vcv["vcv_authority_scene_index"] as? Int) ?? vcvAuthoritySceneIndex
            if let restoredColor = vcv["vcv_authority_color_mode"] as? NSNumber { vcvAuthorityColorMode = restoredColor.int32Value }
            vcvAuthorityFieldLayerIndex = (vcv["vcv_authority_field_layer_index"] as? Int) ?? vcvAuthorityFieldLayerIndex
        }

        if let fields = state["fields"] as? [String: Any] {
            fieldLayersEnabled = (fields["field_layers_enabled"] as? Bool) ?? fieldLayersEnabled
            selectedFieldLayerIndex = (fields["selected_field_layer_index"] as? NSNumber)?.intValue ?? selectedFieldLayerIndex
            if let enabled = fields["field_layer_enabled"] as? [Bool], enabled.count == fieldLayerEnabled.count {
                fieldLayerEnabled = enabled
            }
            if let weights = fields["field_layer_weights"] as? [NSNumber], weights.count == fieldLayerWeights.count {
                fieldLayerWeights = weights.map { Float($0.doubleValue) }
            }
        }

        selectedFieldLayerIndex = max(0, min(selectedFieldLayerIndex, fieldLayerNames.count - 1))
        activeVisualStateName = (state["name"] as? String) ?? fallbackName
        hud?.updateText()
    }

    func cycleColor() { colorMode = (colorMode + 1) % 11; hud?.updateText() }
    func setColor(_ mode: Int32) { colorMode = mode; hud?.updateText() }
    func toggleTrails() { trailsEnabled.toggle(); if !trailsEnabled { trailBuffers.removeAll(); trailCounts.removeAll() }; hud?.updateText() }
    func clearTrails() { trailBuffers.removeAll(); trailCounts.removeAll(); hud?.updateText() }
    func increaseTrailLength() { trailLength = min(trailLength + 2, 48); hud?.updateText() }
    func decreaseTrailLength() {
        trailLength = max(trailLength - 2, 0)
        if trailBuffers.count > trailLength {
            trailBuffers = Array(trailBuffers.suffix(trailLength))
            trailCounts = Array(trailCounts.suffix(trailLength))
        }
        hud?.updateText()
    }
    func toggleGrid() {
        gridEnabled.toggle()
        print("Grid/probability overlay: \(gridEnabled ? "ON" : "OFF")")
        hud?.updateText()
    }

    func toggleRings() {
        centerMarkerEnabled.toggle()
        horizonRingEnabled.toggle()
        curvatureOverlayEnabled = horizonRingEnabled
        print("Rings/curvature overlay: \(horizonRingEnabled ? "ON" : "OFF")")
        hud?.updateText()
    }

    func toggleFieldLayers() {
        fieldLayersEnabled.toggle()
        print("============================================================")
        print("FIELD LAYERS SYSTEM: \(fieldLayersEnabled ? "ON" : "OFF")")
        print("SELECTED FIELD: \(selectedFieldLayerName.uppercased())  WEIGHT: \(String(format: "%.2f", selectedFieldLayerWeight))")
        print("FIELD RECIPE: \(fieldLayerSummary())")
        print("============================================================")
        hud?.updateText()
    }

    func cycleSelectedFieldLayer() {
        selectedFieldLayerIndex = (selectedFieldLayerIndex + 1) % fieldLayerNames.count
        print("SELECTED FIELD LAYER -> \(selectedFieldLayerName.uppercased()) | enabled=\(fieldLayerEnabled[selectedFieldLayerIndex]) | weight=\(String(format: "%.2f", selectedFieldLayerWeight))")
        hud?.updateText()
    }

    func toggleSelectedFieldLayer() {
        fieldLayerEnabled[selectedFieldLayerIndex].toggle()
        print("FIELD LAYER TOGGLE -> \(selectedFieldLayerName.uppercased()) enabled=\(fieldLayerEnabled[selectedFieldLayerIndex])")
        hud?.updateText()
    }

    func increaseSelectedFieldLayerWeight() {
        fieldLayerWeights[selectedFieldLayerIndex] = min(fieldLayerWeights[selectedFieldLayerIndex] + 0.05, 3.0)
        print("Layer \(selectedFieldLayerName) weight: \(String(format: "%.2f", selectedFieldLayerWeight))")
        hud?.updateText()
    }

    func decreaseSelectedFieldLayerWeight() {
        fieldLayerWeights[selectedFieldLayerIndex] = max(fieldLayerWeights[selectedFieldLayerIndex] - 0.05, 0.0)
        print("Layer \(selectedFieldLayerName) weight: \(String(format: "%.2f", selectedFieldLayerWeight))")
        hud?.updateText()
    }

    func applyFieldRecipe(radial: Float, orbital: Float, vertical: Float, turbulence: Float, shell: Float, turbulenceEnabled: Bool = false) {
        fieldLayerWeights = [radial, orbital, vertical, turbulence, shell]
        fieldLayerEnabled = [radial > 0.0, orbital > 0.0, vertical > 0.0, turbulenceEnabled && turbulence > 0.0, shell > 0.0]
        print("Field recipe applied: \(fieldLayerSummary())")
        hud?.updateText()
    }

    func fieldLayerSummary() -> String {
        var tokens: [String] = []
        for i in 0..<fieldLayerNames.count {
            let prefix = fieldLayerEnabled[i] ? fieldLayerNames[i].prefix(1).uppercased() : fieldLayerNames[i].prefix(1).lowercased()
            tokens.append("\(prefix):\(String(format: "%.2f", fieldLayerWeights[i]))")
        }
        return tokens.joined(separator: " ")
    }
}

final class KeyCatcherWindow: NSWindow {
    override var canBecomeKey: Bool { true }
    override var canBecomeMain: Bool { true }
    override func keyDown(with event: NSEvent) {

        if let delegate = NSApp.delegate as? AppDelegate {
            delegate.handleKey(event)
        } else {
            super.keyDown(with: event)
        }
    }
}

struct OverlaySnapshot {
    let hudOverlaysVisible: Bool
    let hudStatsVisible: Bool
    let hudControlsVisible: Bool
    let hudFieldPanelVisible: Bool
    let gridEnabled: Bool
    let curvatureOverlayEnabled: Bool
    let probabilityOverlayEnabled: Bool
    let centerMarkerEnabled: Bool
    let horizonRingEnabled: Bool
}

final class AppDelegate: NSObject, NSApplicationDelegate {
    var window: KeyCatcherWindow?
    var renderer: MetalRenderer?
    var hud: HUDOverlayController?
    var alwaysOnTop = false
    var projectRoot = "/Users/Joe/Documents/RealMathUniverse"
    var currentRespawn = false
    var currentBehaviorEnabled = true
    var currentBehaviorMode = "stable_orbit_cloud"
    var behaviorSource = "renderer_manual"
    var behaviorLock = false
    var burstCount = 5
    var burstInterval: TimeInterval = 0.40
    var cleanCaptureDelay: TimeInterval = 0.08
    var borderlessWindow = false
    var hiddenTitlebar = false
    let sessionID: String = {
        let formatter = DateFormatter()
        formatter.dateFormat = "yyyyMMdd_HHmmss"
        formatter.timeZone = TimeZone(abbreviation: "UTC")
        return formatter.string(from: Date()) + "_UTC"
    }()
    var savedPresentationSnapshot: OverlaySnapshot?

    func applicationDidFinishLaunching(_ notification: Notification) {
        let args = CommandLine.arguments
        if let idx = args.firstIndex(of: "--project-root"), idx + 1 < args.count {
            projectRoot = args[idx + 1]
        }

        let width: Int
        let height: Int
        if let idx = args.firstIndex(of: "--size"), idx + 1 < args.count {
            let parts = args[idx + 1].split(separator: "x")
            width = Int(parts.first ?? "1920") ?? 1920
            height = Int(parts.dropFirst().first ?? "1080") ?? 1080
        } else {
            width = 1920
            height = 1080
        }

        alwaysOnTop = args.contains("--always-on-top")
        borderlessWindow = args.contains("--borderless")
        hiddenTitlebar = args.contains("--hidden-titlebar")
        ensureDefaultControlState()

        guard let device = MTLCreateSystemDefaultDevice() else {
            fatalError("Metal is not available on this system.")
        }

        let visible = NSScreen.main?.visibleFrame ?? NSRect(x: 0, y: 0, width: width, height: height)
        let frame = NSRect(
            x: visible.midX - CGFloat(width) / 2.0,
            y: visible.midY - CGFloat(height) / 2.0,
            width: CGFloat(width),
            height: CGFloat(height)
        )

        var styleMask: NSWindow.StyleMask = [.resizable]
        if borderlessWindow {
            styleMask.insert(.borderless)
        } else {
            styleMask.formUnion([.titled, .closable, .miniaturizable, .resizable])
            if hiddenTitlebar {
                styleMask.insert(.fullSizeContentView)
            }
        }

        let window = KeyCatcherWindow(contentRect: frame, styleMask: styleMask, backing: .buffered, defer: false)
        window.title = "RealMathUniverse Metal Renderer v1.6G4"
        window.center()
        window.isReleasedWhenClosed = false
        if alwaysOnTop { window.level = .floating }
        if hiddenTitlebar && !borderlessWindow {
            window.titleVisibility = .hidden
            window.titlebarAppearsTransparent = true
            window.isMovableByWindowBackground = true
        }

        let container = NSView(frame: frame)
        container.wantsLayer = true

        let metalView = MTKView(frame: container.bounds, device: device)
        metalView.autoresizingMask = [.width, .height]
        metalView.colorPixelFormat = .bgra8Unorm
        metalView.clearColor = MTLClearColor(red: 0.02, green: 0.025, blue: 0.04, alpha: 1.0)
        metalView.preferredFramesPerSecond = 60
        metalView.framebufferOnly = false

        guard let renderer = MetalRenderer(view: metalView, projectRoot: projectRoot) else {
            fatalError("Failed to create Metal renderer.")
        }
        // RMU_V1_3D2_INITIAL_RENDERER_GEOSTATE
        runtimeMode = canonicalRuntimeMode()
        renderer.geospatialSimulationPaused = simulationPaused ? 1 : 0
        renderer.behaviorEffectCode = effectiveBehaviorEffectCode(for: currentBehaviorMode)
        writeRuntimeState(source: "startup")

        metalView.delegate = renderer
        container.addSubview(metalView)

        let hud = HUDOverlayController(containerView: container, frameLoader: renderer.frameLoader, renderer: renderer)
        renderer.hud = hud

        window.contentView = container
        self.window = window
        self.renderer = renderer
        self.hud = hud

        NSApp.setActivationPolicy(.regular)
        NSApp.activate(ignoringOtherApps: true)
        window.makeKeyAndOrderFront(nil)
        window.orderFrontRegardless()

        print("RealMathUniverse Metal Renderer v1.6G4")
        print("Project root: \(projectRoot)")
        print("Field layers: F toggles system, TAB selects layer, SHIFT+SPACE toggles selected layer, / and \\ adjust selected weight")
        print("Session ID: \(sessionID)")
        print("Keys: S shot | J clean | K burst | L clean burst | Y presentation | F field layers | TAB select field | SHIFT+SPACE toggle field | /\\ weight | P trails | ESC quit")
        if borderlessWindow { print("Window mode: borderless") }
        if hiddenTitlebar { print("Window mode: hidden titlebar") }

        DispatchQueue.main.asyncAfter(deadline: .now() + 0.25) {
            NSApp.activate(ignoringOtherApps: true)
            window.makeKeyAndOrderFront(nil)
            window.orderFrontRegardless()
        }
    }

    func applicationShouldTerminateAfterLastWindowClosed(_ sender: NSApplication) -> Bool { true }

    func handleKey(_ event: NSEvent) {
        // RMU_V1_8A_HANDLEKEY_OVERRIDE
        if rmuV18AHandleKey(event) { return }
        if event.keyCode == 53 {
            NSApplication.shared.terminate(nil)
            return
        }

        let panStep: Float = 0.035
        let rotStep: Float = 4.0 * .pi / 180.0

        switch event.keyCode {
        case 48:
            renderer?.cycleSelectedFieldLayer()
            return
        case 49:
            // v1.3D8: SPACE toggles geospatial run/pause. SHIFT+SPACE keeps old field-layer toggle.
            if event.modifierFlags.contains(.shift) {
                renderer?.toggleSelectedFieldLayer()
            } else {
                toggleSimulationPause()
            }
            return
        case 123: renderer?.pan(dx: -panStep, dy: 0)
        case 124: renderer?.pan(dx: panStep, dy: 0)
        case 125: renderer?.pan(dx: 0, dy: -panStep)
        case 126: renderer?.pan(dx: 0, dy: panStep)
        default: break
        }

        guard let characters = event.charactersIgnoringModifiers?.lowercased() else { return }
        let shiftDown = event.modifierFlags.contains(.shift)
        let optionDown = event.modifierFlags.contains(.option)

        let controlDown = event.modifierFlags.contains(.control)

        if ["1", "2", "3", "4", "5", "6", "7", "8"].contains(characters), optionDown && shiftDown {
            if let slot = Int(characters) {
                renderer?.toggleVCVChannel(index: slot - 1)
                return
            }
        }

        if ["1", "2", "3", "4", "5", "6"].contains(characters), optionDown {
            if let slot = Int(characters) {
                loadScenePreset(slot: slot)
                return
            }
        }
        if ["1", "2", "3", "4", "5"].contains(characters), controlDown && shiftDown {
            if let slot = Int(characters) {
                saveVisualState(slot: slot)
                return
            }
        }

        if ["1", "2", "3", "4", "5"].contains(characters), controlDown && !shiftDown {
            if let slot = Int(characters) {
                loadVisualState(slot: slot)
                return
            }
        }

        if characters == "m", shiftDown {
            hud?.toggleBottomPanelMode()
            writeControlState(extra: ["bottom_panel_mode": hud?.bottomPanelMode ?? "unknown"])
            return
        }

        if characters == "d", shiftDown {
            renderer?.toggleAutoCamera()
            return
        }

        if characters == "v", shiftDown {
            renderer?.toggleVCVFieldControl()
            return
        }

        if characters == "o", shiftDown {
            renderer?.toggleVCVMonitor()
            return
        }

        if characters == "c", shiftDown {
            renderer?.toggleVCVSafeMode()
            return
        }

        if characters == "b", shiftDown {
            renderer?.toggleDataCoupling()
            writeControlState(extra: ["dataset_coupling_enabled": renderer?.dataCouplingEnabled ?? false])
            return
        }

        if characters == "g", shiftDown {
            renderer?.cycleDataCouplingGain()
            writeControlState(extra: ["dataset_coupling_gain": renderer?.dataCouplingGain ?? 1.0])
            return
        }

        if characters == "e", shiftDown {
            toggleBehaviorEngine()
            return
        }

        if characters == "r", shiftDown {
            renderer?.resetGeospatialParticleState()
            writeRuntimeState(source: "particle_reset")
            writeControlState(extra: [
                "particle_reset": "manual_shift_r",
                "particle_reset_unix": Date().timeIntervalSince1970,
                "runtime_mode": geospatialRuntimeModeString(),
                "particle_speed": renderer?.geospatialParticleSpeed ?? 1.0,
                "particle_mass": renderer?.geospatialParticleMass ?? 1.0
            ])
            return
        }

        if shiftDown {
            switch characters {
            case "6": loadCameraPreset("gallery_orbit"); return
            case "7": loadCameraPreset("macro_disk"); return
            case "8": loadCameraPreset("wide_system"); return
            case "9": loadCameraPreset("default_camera"); return
            default: break
            }
        }

        switch characters {
        case "s": saveWindowScreenshot(clean: false)
        case "j": saveWindowScreenshot(clean: true)
        case "k": captureBurst(clean: false, total: burstCount, interval: burstInterval)
        case "l": captureBurst(clean: true, total: burstCount, interval: burstInterval)
        case "t": alwaysOnTop.toggle(); window?.level = alwaysOnTop ? .floating : .normal
        case "h": hud?.toggleAll(); hud?.updateText()
        case "f": renderer?.toggleFieldLayers()
        case "y": togglePresentationMode()
        case "m": hud?.toggleCompact()
        case ";": decreaseBurstCount()
        case "'": increaseBurstCount()
        case "u": decreaseBurstInterval()
        case "i": increaseBurstInterval()
        case "1": hud?.toggleStats()
        case "2": hud?.toggleControls()
        case "3": writePreset(behavior: "stable_orbit_cloud", respawn: false, pointSize: 2.0, radiusMultiplier: 1.0, colorMode: 0)
        case "4": writePreset(behavior: "black_hole_capture", respawn: false, pointSize: 2.5, radiusMultiplier: 0.85, colorMode: 3)
        case "5": writePreset(behavior: "accretion_disk", respawn: false, pointSize: 2.0, radiusMultiplier: 1.05, colorMode: 2)
        case "6": writePreset(behavior: "field_pressure_bounce", respawn: true, pointSize: 2.0, radiusMultiplier: 1.10, colorMode: 4)
        case "7": writePreset(behavior: "infinite_collapse", respawn: true, pointSize: 2.0, radiusMultiplier: 1.0, colorMode: 1)
        case "8": writeSamplePreset(25000)
        case "9": writeSamplePreset(50000)
        case "0": writeSamplePreset(100000)
        case "r":
            currentRespawn.toggle()
            renderer?.geospatialRespawnOnCapture = currentRespawn
            writeRuntimeState(source: "respawn_toggle")
            writeControlState(respawnOnly: true)
        case "p": renderer?.toggleTrails()
        case "n": renderer?.clearTrails()
        case ",": renderer?.decreaseTrailLength()
        case ".": renderer?.increaseTrailLength()
        case "g": renderer?.toggleGrid()
        case "o": renderer?.toggleRings()
        case "c": renderer?.cycleColor()
        case "v": renderer?.setColor(0)
        case "b": renderer?.setColor(3)
        case "w": renderer?.zoomIn()
        case "z": renderer?.zoomOut()
        case "q": renderer?.zoomOut()
        case "e": renderer?.zoomIn()
        case "a": renderer?.rotate(delta: -rotStep)
        case "d": renderer?.rotate(delta: rotStep)
        case "x": renderer?.resetCamera()
        case "+", "=": renderer?.increasePointSize()
        case "-": renderer?.decreasePointSize()
        case "[": renderer?.zoomOut()
        case "]": renderer?.zoomIn()
        case "/": renderer?.decreaseSelectedFieldLayerWeight()
        case "\\": renderer?.increaseSelectedFieldLayerWeight()
        default: break
        }
    }

    func toggleBehaviorEngine() {
        currentBehaviorEnabled.toggle()
        renderer?.geospatialBehaviorEnabled = currentBehaviorEnabled
        renderer?.behaviorEffectCode = effectiveBehaviorEffectCode(for: currentBehaviorMode)

        writeRuntimeState(source: "behavior_toggle")
        writeControlState(extra: [
            "behavior_enabled": currentBehaviorEnabled,
            "behavior_effect_code": renderer?.behaviorEffectCode ?? 0,
            "behavior_bypass_authority": "renderer_shift_e"
        ])

        print("RMU v1.3F9G behavior engine: \(currentBehaviorEnabled ? "ON" : "OFF") | behaviorEffectCode=\(renderer?.behaviorEffectCode ?? -1)")
        hud?.updateText()
    }



    func datasetStateURL() -> URL {
        URL(fileURLWithPath: projectRoot).appendingPathComponent("output").appendingPathComponent("dataset_state.json")
    }

    func readDatasetStateForControl() -> [String: Any]? {
        let url = datasetStateURL()
        guard let data = try? Data(contentsOf: url),
              let object = try? JSONSerialization.jsonObject(with: data, options: []),
              let json = object as? [String: Any] else { return nil }
        return json
    }

    func behaviorStateURL() -> URL {
        URL(fileURLWithPath: projectRoot).appendingPathComponent("output").appendingPathComponent("behavior_state.json")
    }

    func readBehaviorStateForControl() -> [String: Any]? {
        let url = behaviorStateURL()
        guard let data = try? Data(contentsOf: url),
              let object = try? JSONSerialization.jsonObject(with: data, options: []),
              let json = object as? [String: Any] else { return nil }
        return json
    }


    func writeBehaviorState(behavior: String, source: String = "renderer_manual") {
        currentBehaviorMode = behavior
        behaviorSource = source
        behaviorLock = false
        let url = behaviorStateURL()
        let now = Date().timeIntervalSince1970
        let obj: [String: Any] = [
            "version": "1.3F6",
            "behavior_mode": behavior,
            "behavior_source": source,
            "behavior_lock": false,
            "behavior_enabled": renderer?.geospatialBehaviorEnabled ?? true,
            "behavior_timestamp_unix": now,
            "collapse_behavior": [
                "behavior_mode": behavior,
                "source": source,
                "locked": false,
                "timestamp_unix": now
            ],
            "updated_by": "metal_renderer_v1_3D11_behavior_state",
            "timestamp_unix": now
        ]
        rmuV19NWriteJSON(obj, to: url)
    }


    func controlStateURL() -> URL {
        URL(fileURLWithPath: projectRoot).appendingPathComponent("output").appendingPathComponent("control_state.json")
    }

    func ensureDefaultControlState() {
        let url = controlStateURL()
        if FileManager.default.fileExists(atPath: url.path) { return }
        try? FileManager.default.createDirectory(at: url.deletingLastPathComponent(), withIntermediateDirectories: true)
        rmuV19NWriteJSON([
            "role": "report_only_not_authority",
            "not_authority": true,
            "behavior_mode": currentBehaviorMode,
            "behavior_source": behaviorSource,
            "behavior_lock": behaviorLock,
            "behavior_timestamp_unix": Date().timeIntervalSince1970,
            "collapse_behavior": [
                "behavior_mode": currentBehaviorMode,
                "source": behaviorSource,
                "locked": behaviorLock
            ],
            "respawn_on_capture": false,
            "render_sample_count": 25000,
            "trails_enabled": true,
            "trail_length": 12,
            "grid_enabled": false,
            "updated_by": "metal_renderer_v1_3D11_default_control_state",
            "timestamp_unix": Date().timeIntervalSince1970
        ], to: url)
    }

    func scenePresetDir() -> URL {
        let dir = URL(fileURLWithPath: projectRoot)
            .appendingPathComponent("config")
            .appendingPathComponent("presets")
        try? FileManager.default.createDirectory(at: dir, withIntermediateDirectories: true)
        return dir
    }

    func scenePresetURL() -> URL {
        return scenePresetDir().appendingPathComponent("scene_presets.json")
    }

    func loadScenePreset(slot: Int) {
        guard let renderer = renderer else { return }
        let names = [
            1: "deep_orbit",
            2: "black_hole_gallery",
            3: "collapse_burst",
            4: "field_pressure_demo",
            5: "clean_accretion_disk",
            6: "wide_probability_cloud"
        ]

        guard let name = names[slot] else { return }

        switch slot {
        case 1:
            writePreset(behavior: "stable_orbit_cloud", respawn: false, pointSize: 2.0, radiusMultiplier: 1.20, colorMode: 1)
            renderer.applyCameraPreset("gallery_orbit")
            renderer.trailsEnabled = true
            renderer.trailLength = 18
            renderer.gridEnabled = false
            renderer.horizonRingEnabled = true
            renderer.curvatureOverlayEnabled = true
            renderer.probabilityOverlayEnabled = false
        case 2:
            writePreset(behavior: "black_hole_capture", respawn: false, pointSize: 2.3, radiusMultiplier: 0.88, colorMode: 3)
            renderer.applyCameraPreset("macro_disk")
            renderer.trailsEnabled = true
            renderer.trailLength = 24
            renderer.gridEnabled = false
            renderer.horizonRingEnabled = true
            renderer.curvatureOverlayEnabled = true
            renderer.probabilityOverlayEnabled = false
        case 3:
            writePreset(behavior: "infinite_collapse", respawn: true, pointSize: 2.0, radiusMultiplier: 0.95, colorMode: 4)
            renderer.applyCameraPreset("gallery_orbit")
            renderer.trailsEnabled = true
            renderer.trailLength = 30
            renderer.gridEnabled = false
            renderer.horizonRingEnabled = true
            renderer.curvatureOverlayEnabled = true
            renderer.probabilityOverlayEnabled = true
        case 4:
            writePreset(behavior: "field_pressure_bounce", respawn: true, pointSize: 2.1, radiusMultiplier: 1.05, colorMode: 4)
            renderer.applyCameraPreset("wide_system")
            renderer.trailsEnabled = true
            renderer.trailLength = 16
            renderer.gridEnabled = true
            renderer.horizonRingEnabled = true
            renderer.curvatureOverlayEnabled = true
            renderer.probabilityOverlayEnabled = true
        case 5:
            writePreset(behavior: "accretion_disk", respawn: false, pointSize: 2.0, radiusMultiplier: 1.03, colorMode: 2)
            renderer.applyCameraPreset("macro_disk")
            renderer.trailsEnabled = true
            renderer.trailLength = 22
            renderer.gridEnabled = false
            renderer.horizonRingEnabled = false
            renderer.curvatureOverlayEnabled = false
            renderer.probabilityOverlayEnabled = false
        case 6:
            writePreset(behavior: "stable_orbit_cloud", respawn: true, pointSize: 1.7, radiusMultiplier: 1.55, colorMode: 1)
            renderer.applyCameraPreset("wide_system")
            renderer.trailsEnabled = true
            renderer.trailLength = 12
            renderer.gridEnabled = true
            renderer.horizonRingEnabled = true
            renderer.curvatureOverlayEnabled = true
            renderer.probabilityOverlayEnabled = true
        default:
            break
        }

        renderer.activeScenePresetName = name
        renderer.lastVisualStateMessage = "scene loaded: \(name)"
        writeControlState(extra: ["scene_preset": name])
        print("Scene preset loaded: \(slot) \(name)")
        hud?.updateText()
    }


    func behaviorEffectCode(for behavior: String) -> Int32 {
        switch behavior {
        case "stable_orbit_cloud": return 1
        case "black_hole_capture": return 2
        case "accretion_disk": return 3
        case "field_pressure_bounce": return 4
        case "infinite_collapse": return 5
        default: return 1
        }
    }

    func effectiveBehaviorEffectCode(for behavior: String) -> Int32 {
        return currentBehaviorEnabled ? behaviorEffectCode(for: behavior) : 0
    }


    func runtimeStateURL() -> URL {
        URL(fileURLWithPath: projectRoot).appendingPathComponent("output").appendingPathComponent("runtime_state.json")
    }

    func canonicalRuntimeMode() -> String {
        if !geospatialEnabled { return "standard_simulation" }
        return simulationPaused ? "geospatial_static_paused" : "geospatial_live_running"
    }

    func geospatialRuntimeObject(source: String = "renderer") -> [String: Any] {
        runtimeMode = canonicalRuntimeMode()
        let now = Date().timeIntervalSince1970
        return [
            "version": "1.3F6",
            "runtime_mode": runtimeMode,
            "geospatial_enabled": geospatialEnabled,
            "simulation_paused": simulationPaused,
            "physics_armed": !simulationPaused,
            "spacebar_mode": "run_pause_geospatial",
            "particle_speed": renderer?.geospatialParticleSpeed ?? 1.0,
            "particle_mass": renderer?.geospatialParticleMass ?? 1.0,
            "particle_turbulence": renderer?.geospatialParticleTurbulence ?? 0.0,
            "particle_cohesion": renderer?.geospatialParticleCohesion ?? 0.0,
            "gravity_well_position": renderer?.geospatialGravityWellPosition ?? 0.0,
            "gravity_well_strength": renderer?.geospatialGravityWellStrength ?? 6.0,
            "particle_source_authority": "renderer_geospatial_authority",
            "particle_source_mode": "crab_nav_csv_particles",
            "particle_source_csv": "/Users/Joe/Documents/RealMathUniverse/data/raw/merged_navdata.csv",
            "behavior_mode": currentBehaviorMode,
            "behavior_lock": behaviorLock,
            "behavior_source": behaviorSource,
            "respawn_on_capture": currentRespawn,
            "updated_by": "metal_renderer_v1_3D7_runtime_authority",
            "source": source,
            "timestamp_unix": now
        ]
    }




    func geospatialRuntimeStateURL() -> URL {
        URL(fileURLWithPath: projectRoot).appendingPathComponent("output").appendingPathComponent("geospatial_runtime_state.json")
    }

















    func readRuntimePausedFromFile() -> Bool {
        let url = runtimeStateURL()
        guard let data = try? Data(contentsOf: url),
              let object = try? JSONSerialization.jsonObject(with: data, options: []),
              let json = object as? [String: Any] else {
            return simulationPaused
        }
        if let paused = json["simulation_paused"] as? Bool { return paused }
        if let paused = json["simulation_paused"] as? NSNumber { return paused.boolValue }
        if let paused = json["simulation_paused"] as? String {
            let lowered = paused.lowercased()
            if ["true", "1", "yes", "paused"].contains(lowered) { return true }
            if ["false", "0", "no", "running"].contains(lowered) { return false }
        }
        return simulationPaused
    }

    func geospatialRuntimeModeString() -> String {
        return simulationPaused ? "geospatial_static_paused" : "geospatial_live_running"
    }

    func writeRuntimeState(source: String = "renderer") {
        let now = Date().timeIntervalSince1970
        let obj: [String: Any] = [
            "version": "1.3F6",
            "runtime_mode": geospatialRuntimeModeString(),
            "geospatial_enabled": geospatialEnabled,
            "simulation_paused": simulationPaused,
            "physics_armed": !simulationPaused,
            "spacebar_mode": "run_pause_geospatial",
            "particle_speed": renderer?.geospatialParticleSpeed ?? 1.0,
            "particle_mass": renderer?.geospatialParticleMass ?? 1.0,
            "particle_source_authority": "renderer_geospatial_authority",
            "particle_source_mode": "crab_nav_csv_particles",
            "particle_source_csv": "/Users/Joe/Documents/RealMathUniverse/data/raw/merged_navdata.csv",
            "behavior_mode": currentBehaviorMode,
            "behavior_lock": false,
            "behavior_source": "renderer_manual",
            "species_architecture_version": "v1.4A",
            "species_architecture_enabled": true,
            "species_count": 22,
            "species_assignment": "deterministic_id_mod_22",
            "respawn_on_capture": currentRespawn,
            "updated_by": "metal_renderer_v1_3F6_particle_reset_runtime",
            "source": source,
            "timestamp_unix": now
        ]
        rmuV19NWriteJSON(obj, to: runtimeStateURL())
        rmuV19NWriteJSON(obj, to: geospatialRuntimeStateURL())
    }



    func toggleSimulationPause() {
        let now = Date().timeIntervalSince1970
        if now - lastGeospatialSpaceToggleUnix < 0.35 {
            print("SPACE ignored by v1.3D11 debounce")
            return
        }
        lastGeospatialSpaceToggleUnix = now

        let currentlyPaused = readRuntimePausedFromFile()
        simulationPaused = !currentlyPaused
        behaviorLock = false

        renderer?.geospatialSimulationPaused = simulationPaused ? 1 : 0
        if !simulationPaused { renderer?.fieldPhase = 0.0 }
        renderer?.behaviorEffectCode = effectiveBehaviorEffectCode(for: currentBehaviorMode)

        writeRuntimeState(source: "spacebar")
        writeControlState(extra: [
            "runtime_mode": geospatialRuntimeModeString(),
            "geospatial_enabled": geospatialEnabled,
            "simulation_paused": simulationPaused,
            "physics_armed": !simulationPaused,
            "particle_source_authority": "renderer_geospatial_authority",
            "particle_source_mode": "crab_nav_csv_particles",
            "spacebar_mode": "run_pause_geospatial",
            "behavior_lock": false,
            "updated_by_spacebar": "metal_renderer_v1_3F6_particle_reset_runtime"
        ])
        print("Geospatial runtime: \(simulationPaused ? "PAUSED" : "RUNNING") behavior=\(currentBehaviorMode)")
        hud?.updateText()
    }


    func writePreset(behavior: String, respawn: Bool, pointSize: Float, radiusMultiplier: Float, colorMode: Int32) {
        // RMU_V1_7J_WRITEPRESET_DECOUPLED
        currentBehaviorMode = behavior
        currentRespawn = respawn
        renderer?.geospatialRespawnOnCapture = respawn
        renderer?.behaviorEffectCode = effectiveBehaviorEffectCode(for: behavior)
        renderer?.fieldPhase = 0.0
        simulationPaused = readRuntimePausedFromFile()
        renderer?.geospatialSimulationPaused = simulationPaused ? 1 : 0
        writeRuntimeState(source: "behavior_preset")
        if renderer?.rmuV17JLinkedBehaviorPresetsEnabled() ?? false {
            renderer?.pointSize = pointSize
            renderer?.setColor(colorMode)
            if let base = renderer?.frameLoader.worldRadius {
                renderer?.manualWorldRadius = base * radiusMultiplier
            }
            applyFieldRecipeForBehavior(behavior)
        } else {
            renderer?.lastVisualStateMessage = "v1.7J behavior-only preset; linked field/camera/color disabled"
        }
        writeBehaviorState(behavior: behavior, source: "renderer_manual")
        writeControlState(behavior: behavior)
        renderer?.rmuV17JEnforceControlAuthority(reason: "after_writePreset")
    }

    func applyFieldRecipeForBehavior(_ behavior: String) {
        guard let renderer = renderer else { return }
        switch behavior {
        case "stable_orbit_cloud":
            renderer.applyFieldRecipe(radial: 0.25, orbital: 1.00, vertical: 0.10, turbulence: 0.05, shell: 0.20, turbulenceEnabled: false)
        case "black_hole_capture":
            renderer.applyFieldRecipe(radial: 0.95, orbital: 0.75, vertical: 0.20, turbulence: 0.08, shell: 0.40, turbulenceEnabled: true)
        case "accretion_disk":
            renderer.applyFieldRecipe(radial: 0.35, orbital: 1.10, vertical: 0.25, turbulence: 0.10, shell: 0.30, turbulenceEnabled: true)
        case "field_pressure_bounce":
            renderer.applyFieldRecipe(radial: 0.55, orbital: 0.35, vertical: 0.45, turbulence: 0.30, shell: 0.15, turbulenceEnabled: true)
        case "infinite_collapse":
            renderer.applyFieldRecipe(radial: 1.15, orbital: 0.40, vertical: 0.12, turbulence: 0.15, shell: 0.45, turbulenceEnabled: true)
        default:
            break
        }
    }

    func visualStateDir() -> URL {
        let dir = URL(fileURLWithPath: projectRoot)
            .appendingPathComponent("config")
            .appendingPathComponent("visual_states")
        try? FileManager.default.createDirectory(at: dir, withIntermediateDirectories: true)
        return dir
    }

    func visualStateURL(slot: Int) -> URL {
        return visualStateDir().appendingPathComponent("slot_\(slot).json")
    }

    func saveVisualState(slot: Int) {
        guard let renderer = renderer else { return }
        let state = renderer.visualStateDictionary(name: "slot_\(slot)", slot: slot)
        let url = visualStateURL(slot: slot)
        rmuV19NWriteJSON(state, to: url)
        renderer.activeVisualStateName = "saved_slot_\(slot)"
        renderer.lastVisualStateMessage = "saved slot \(slot)"
        print("Visual state saved to slot \(slot): \(url.path)")
        hud?.updateText()
    }

    func loadVisualState(slot: Int) {
        guard let renderer = renderer else { return }
        let url = visualStateURL(slot: slot)
        guard FileManager.default.fileExists(atPath: url.path) else {
            renderer.lastVisualStateMessage = "slot \(slot) empty"
            print("Visual state slot \(slot) is empty: \(url.path)")
            hud?.updateText()
            return
        }

        do {
            let data = try Data(contentsOf: url)
            let object = try JSONSerialization.jsonObject(with: data, options: [])
            guard let state = object as? [String: Any] else {
                renderer.lastVisualStateMessage = "slot \(slot) invalid"
                print("Visual state slot \(slot) invalid JSON object")
                hud?.updateText()
                return
            }
            renderer.applyVisualState(state, fallbackName: "slot_\(slot)")
            renderer.lastVisualStateMessage = "loaded slot \(slot)"
            print("Visual state loaded from slot \(slot): \(url.path)")
            hud?.updateText()
        } catch {
            renderer.lastVisualStateMessage = "slot \(slot) load failed"
            print("Failed to load visual state slot \(slot): \(error)")
            hud?.updateText()
        }
    }

    func loadCameraPreset(_ name: String) {
        renderer?.applyCameraPreset(name)
    }

    func writeSamplePreset(_ count: Int) {
        writeControlState(extra: ["render_sample_count": count])
        renderer?.clearTrails()
        print("Sample preset requested: \(count)")
    }


    func writeControlState(behavior: String? = nil, respawnOnly: Bool = false, extra: [String: Any] = [:]) {
        var state: [String: Any] = [:]
        let url = controlStateURL()

        if let data = try? Data(contentsOf: url),
           let existing = try? JSONSerialization.jsonObject(with: data) as? [String: Any] {
            state = existing
        }

        if let behavior = behavior {
            currentBehaviorMode = behavior
            behaviorSource = "renderer_manual"
            // v1.3D7: control-state behavior selection should not hard-lock runtime behavior.
            behaviorLock = false
        } else {
            // RMU_V1_7J_CONTROL_STATE_REPORT_ONLY
            // control_state.json and behavior_state.json are reports/latches only here.
            // They must not resurrect stale behavior into renderer authority.
        }

        state["role"] = "report_only_not_authority"
        state["not_authority"] = true
        state["behavior_mode"] = currentBehaviorMode
        state["behavior_source"] = behaviorSource
        state["behavior_lock"] = behaviorLock
        state["behavior_enabled"] = currentBehaviorEnabled
        state["behavior_effect_code"] = renderer?.behaviorEffectCode ?? 0
        state["behavior_bypass_authority"] = "renderer_shift_e"
        state["behavior_timestamp_unix"] = Date().timeIntervalSince1970
        state["collapse_behavior"] = [
            "behavior_mode": currentBehaviorMode,
            "source": behaviorSource,
            "locked": behaviorLock,
            "timestamp_unix": Date().timeIntervalSince1970
        ]
        state["respawn_on_capture"] = currentRespawn
        state["runtime_mode"] = canonicalRuntimeMode()
        state["geospatial_enabled"] = geospatialEnabled
        state["simulation_paused"] = simulationPaused
        state["physics_armed"] = !simulationPaused
        state["spacebar_mode"] = "run_pause_geospatial"
        state["particle_source_authority"] = "renderer_geospatial_authority"
        state["particle_source_mode"] = "crab_nav_csv_particles"
        for (key, value) in extra { state[key] = value }
        state["renderer_scene"] = renderer?.activeScenePresetName ?? "manual"
        var vcvState: [String: Any] = [:]
        vcvState["status"] = renderer?.vcvStatus ?? "not detected"
        vcvState["probability_source"] = renderer?.probabilitySource ?? "internal"
        vcvState["field_control_enabled"] = renderer?.vcvFieldControlEnabled ?? false
        vcvState["display_status"] = renderer?.vcvDisplayStatus() ?? "OFF"
        vcvState["monitor_visible"] = renderer?.vcvMonitorVisible ?? false
        vcvState["smoothing_amount"] = renderer?.vcvSmoothingAmount ?? 0.0
        vcvState["safe_mode_enabled"] = renderer?.vcvSafeModeEnabled ?? true
        vcvState["last_clamp_event"] = renderer?.vcvLastClampEvent ?? "none"
        vcvState["channel_labels"] = renderer?.vcvChannelLabels ?? []
        vcvState["channel_targets"] = renderer?.vcvChannelTargets ?? []
        vcvState["channel_values"] = renderer?.vcvChannelValues ?? []
        vcvState["raw_channel_values"] = renderer?.vcvRawChannelValues ?? []
        vcvState["channel_enabled"] = renderer?.vcvChannelEnabled ?? []
        state["vcv"] = vcvState
        if let datasetState = readDatasetStateForControl() {
            state["dataset"] = datasetState
            if let dsState = datasetState["state"] as? [String: Any] {
                state["dataset_values"] = dsState
            }
        } else {
            state["dataset"] = [
                "loaded": false,
                "fallback_active": true,
                "fallback_reason": "dataset_state.json not readable by renderer"
            ]
        }
        if let renderer = renderer {
            state["dataset_coupling"] = renderer.datasetCouplingControlState()
        }
        state["bottom_panel_mode"] = hud?.bottomPanelMode ?? "field"
        state["particle_speed"] = renderer?.geospatialParticleSpeed ?? 1.0
        state["particle_mass"] = renderer?.geospatialParticleMass ?? 1.0
        state["particle_turbulence"] = renderer?.geospatialParticleTurbulence ?? 0.0
        state["particle_cohesion"] = renderer?.geospatialParticleCohesion ?? 0.0
        state["display_particle_limit"] = renderer?.geospatialDisplayParticleLimit ?? 70000
        state["updated_by"] = "metal_renderer_v1_3F6_control_state"
        state["timestamp_unix"] = Date().timeIntervalSince1970
        rmuV19NWriteJSON(state, to: url)
        print("Control state written by metal_renderer_v1_3F6_control_state: \(state)")
        hud?.updateText()
    }

    func rmuV19NWriteJSON(_ object: [String: Any], to url: URL) {
        do {
            let data = try JSONSerialization.data(withJSONObject: object, options: [.prettyPrinted])
            let tmpURL = url.deletingLastPathComponent().appendingPathComponent(url.lastPathComponent + ".tmp")
            try data.write(to: tmpURL)
            if FileManager.default.fileExists(atPath: url.path) {
                try FileManager.default.removeItem(at: url)
            }
            try FileManager.default.moveItem(at: tmpURL, to: url)
        } catch {
            print("Failed to write JSON: \(error)")
        }
    }

    func screenshotsDir() -> URL {
        let dir = URL(fileURLWithPath: projectRoot)
            .appendingPathComponent("output")
            .appendingPathComponent("screenshots")
            .appendingPathComponent("metal")
            .appendingPathComponent(sessionID)
        try? FileManager.default.createDirectory(at: dir, withIntermediateDirectories: true)
        return dir
    }

    func manifestDir() -> URL {
        let dir = URL(fileURLWithPath: projectRoot)
            .appendingPathComponent("output")
            .appendingPathComponent("manifests")
        try? FileManager.default.createDirectory(at: dir, withIntermediateDirectories: true)
        return dir
    }

    func manifestURL() -> URL {
        manifestDir().appendingPathComponent("RealMathUniverse_v1_2B2_capture_manifest_\(sessionID).json")
    }

    func markdownSummaryURL() -> URL {
        manifestDir().appendingPathComponent("RealMathUniverse_v1_2B2_session_summary_\(sessionID).md")
    }

    func sanitized(_ value: String) -> String {
        let allowed = CharacterSet.alphanumerics.union(CharacterSet(charactersIn: "-_"))
        return value.lowercased().map { ch in
            String(ch).rangeOfCharacter(from: allowed) != nil ? String(ch) : "_"
        }.joined()
    }

    func sampleLabel(_ count: Int) -> String {
        if count >= 1000 { return "\(count / 1000)k" }
        return "\(count)"
    }

    func currentWindowModeLabel() -> String {
        if borderlessWindow { return "borderless" }
        if hiddenTitlebar { return "hidden_titlebar" }
        return "standard"
    }

    func currentOverlaySnapshot() -> OverlaySnapshot {
        OverlaySnapshot(
            hudOverlaysVisible: hud?.overlaysVisible ?? true,
            hudStatsVisible: hud?.statsVisible ?? true,
            hudControlsVisible: hud?.controlsVisible ?? true,
            hudFieldPanelVisible: hud?.fieldPanelVisible ?? true,
            gridEnabled: renderer?.gridEnabled ?? false,
            curvatureOverlayEnabled: renderer?.curvatureOverlayEnabled ?? true,
            probabilityOverlayEnabled: renderer?.probabilityOverlayEnabled ?? true,
            centerMarkerEnabled: renderer?.centerMarkerEnabled ?? true,
            horizonRingEnabled: renderer?.horizonRingEnabled ?? true
        )
    }

    func applyOverlaySnapshot(_ snapshot: OverlaySnapshot) {
        hud?.overlaysVisible = snapshot.hudOverlaysVisible
        hud?.statsVisible = snapshot.hudStatsVisible
        hud?.controlsVisible = snapshot.hudControlsVisible
        hud?.fieldPanelVisible = snapshot.hudFieldPanelVisible
        hud?.applyVisibility()
        renderer?.gridEnabled = snapshot.gridEnabled
        renderer?.curvatureOverlayEnabled = snapshot.curvatureOverlayEnabled
        renderer?.probabilityOverlayEnabled = snapshot.probabilityOverlayEnabled
        renderer?.centerMarkerEnabled = snapshot.centerMarkerEnabled
        renderer?.horizonRingEnabled = snapshot.horizonRingEnabled
        hud?.updateText()
    }

    func togglePresentationMode() {
        guard let renderer = renderer else { return }
        if renderer.presentationModeEnabled {
            renderer.presentationModeEnabled = false
            if let snapshot = savedPresentationSnapshot {
                applyOverlaySnapshot(snapshot)
            }
            savedPresentationSnapshot = nil
            print("Presentation mode OFF")
        } else {
            savedPresentationSnapshot = currentOverlaySnapshot()
            renderer.presentationModeEnabled = true
            hud?.overlaysVisible = false
            hud?.applyVisibility()
            renderer.gridEnabled = false
            renderer.curvatureOverlayEnabled = false
            renderer.probabilityOverlayEnabled = false
            renderer.centerMarkerEnabled = false
            renderer.horizonRingEnabled = false
            hud?.updateText()
            print("Presentation mode ON")
        }
    }

    func saveWindowScreenshot(clean: Bool, burstIndex: Int? = nil, burstTotal: Int? = nil) {
        guard let window = window else {
            print("Screenshot failed: no window.")
            return
        }

        let performCapture = {
            let windowID = CGWindowID(window.windowNumber)
            guard let cgImage = CGWindowListCreateImage(.null, [.optionIncludingWindow], windowID, [.boundsIgnoreFraming, .bestResolution]) else {
                print("Screenshot failed: CGWindowListCreateImage returned nil.")
                return
            }

            let behavior = self.sanitized(self.canonicalRuntimeMode())
            let color = self.sanitized(self.renderer?.colorModeName ?? "classic")
            let sample = self.sampleLabel(self.renderer?.frameLoader.renderSampleCount ?? 0)
            let captureType = clean ? "clean" : "window"
            let formatter = DateFormatter()
            formatter.dateFormat = "yyyyMMdd_HHmmss"
            formatter.timeZone = TimeZone(abbreviation: "UTC")
            let stamp = formatter.string(from: Date())
            let burstSuffix: String
            if let burstIndex = burstIndex, let burstTotal = burstTotal {
                burstSuffix = String(format: "_b%02dof%02d", burstIndex, burstTotal)
            } else {
                burstSuffix = ""
            }

            let fileName = "RealMathUniverse_v1_3F6_\(behavior)_\(color)_\(sample)_\(captureType)\(burstSuffix)_\(stamp)_UTC.png"
            let url = self.screenshotsDir().appendingPathComponent(fileName)
            guard let destination = CGImageDestinationCreateWithURL(url as CFURL, "public.png" as CFString, 1, nil) else {
                print("Screenshot failed: could not create destination.")
                return
            }

            CGImageDestinationAddImage(destination, cgImage, nil)
            if CGImageDestinationFinalize(destination) {
                self.appendCaptureManifestEntry(fileURL: url, clean: clean, burstIndex: burstIndex, burstTotal: burstTotal)
                print("Screenshot saved: \(url.path)")
            } else {
                print("Screenshot failed: finalize failed.")
            }
        }

        if clean {
            let snapshot = currentOverlaySnapshot()
            hud?.overlaysVisible = false
            hud?.applyVisibility()
            renderer?.gridEnabled = false
            renderer?.centerMarkerEnabled = false
            renderer?.horizonRingEnabled = false
            DispatchQueue.main.asyncAfter(deadline: .now() + cleanCaptureDelay) {
                performCapture()
                self.applyOverlaySnapshot(snapshot)
            }
        } else {
            performCapture()
        }
    }

    func captureBurst(clean: Bool, total: Int, interval: TimeInterval) {
        guard total > 0 else { return }
        print("Starting \(clean ? "clean" : "window") burst: \(total) captures")
        captureBurstStep(clean: clean, index: 1, total: total, interval: interval)
    }

    func captureBurstStep(clean: Bool, index: Int, total: Int, interval: TimeInterval) {
        saveWindowScreenshot(clean: clean, burstIndex: index, burstTotal: total)
        guard index < total else { return }
        DispatchQueue.main.asyncAfter(deadline: .now() + interval) {
            self.captureBurstStep(clean: clean, index: index + 1, total: total, interval: interval)
        }
    }

    func appendCaptureManifestEntry(fileURL: URL, clean: Bool, burstIndex: Int?, burstTotal: Int?) {
        var manifest: [String: Any] = [:]
        var captures: [[String: Any]] = []
        let url = manifestURL()

        if let data = try? Data(contentsOf: url),
           let existing = try? JSONSerialization.jsonObject(with: data) as? [String: Any] {
            manifest = existing
            if let existingCaptures = existing["captures"] as? [[String: Any]] {
                captures = existingCaptures
            }
        }

        let iso = ISO8601DateFormatter()
        iso.timeZone = TimeZone(abbreviation: "UTC")

        let entry: [String: Any] = [
            "timestamp_unix": Date().timeIntervalSince1970,
            "timestamp_utc": iso.string(from: Date()),
            "filename": fileURL.lastPathComponent,
            "runtime_mode": canonicalRuntimeMode(),
            "particle_speed": renderer?.geospatialParticleSpeed ?? 1.0,
            "particle_mass": renderer?.geospatialParticleMass ?? 1.0,
            "relative_path": "output/screenshots/metal/\(sessionID)/\(fileURL.lastPathComponent)",
            "behavior_mode": renderer?.frameLoader.behaviorMode ?? "unknown",
            "color_mode": renderer?.colorModeName ?? "unknown",
            "render_sample_count": renderer?.frameLoader.renderSampleCount ?? 0,
            "point_count": renderer?.frameLoader.latestPointCount ?? 0,
            "source_particle_count": renderer?.frameLoader.sourceParticleCount ?? 0,
            "sim_frame": renderer?.frameLoader.latestFrameIndex ?? 0,
            "sim_time": renderer?.frameLoader.latestSimTime ?? 0.0,
            "fps": renderer?.currentFPS ?? 0.0,
            "clean_capture": clean,
            "burst_index": burstIndex ?? 1,
            "burst_total": burstTotal ?? 1,
            "window_mode": currentWindowModeLabel(),
            "presentation_mode": renderer?.presentationModeEnabled ?? false,
            "frame_time_ms": renderer?.currentFrameTimeMS ?? 0.0,
            "late_frame_warning": renderer?.lateFrameWarning ?? false,
            "trail_length": renderer?.trailLength ?? 0,
            "trails_enabled": renderer?.trailsEnabled ?? false,
            "grid_enabled": renderer?.gridEnabled ?? false,
            "center_marker_enabled": renderer?.centerMarkerEnabled ?? false,
            "horizon_ring_enabled": renderer?.horizonRingEnabled ?? false,
            "burst_count_setting": burstCount,
            "burst_interval_setting": burstInterval,
            "active_visual_state_name": renderer?.activeVisualStateName ?? "unknown",
            "auto_camera_enabled": renderer?.autoCameraEnabled ?? false,
            "active_scene_preset": renderer?.activeScenePresetName ?? "manual",
            "vcv_status": renderer?.vcvStatus ?? "not detected",
            "probability_source": renderer?.probabilitySource ?? "internal",
            "camera": [
                "pan_x": renderer?.panX ?? 0.0,
                "pan_y": renderer?.panY ?? 0.0,
                "rotation_radians": renderer?.rotationRadians ?? 0.0,
                "manual_world_radius": renderer?.manualWorldRadius as Any
            ],
            "field_layers_enabled": renderer?.fieldLayersEnabled ?? false,
            "selected_field_layer": renderer?.selectedFieldLayerName ?? "unknown",
            "selected_field_layer_weight": renderer?.selectedFieldLayerWeight ?? 0.0,
            "field_layer_summary": renderer?.fieldLayerSummary() ?? "",
            "field_layer_enabled_flags": renderer?.fieldLayerEnabled.map { $0 ? 1 : 0 } ?? [],
            "field_layer_weights": renderer?.fieldLayerWeights ?? [],
            "curvature_overlay_enabled": renderer?.curvatureOverlayEnabled ?? false,
            "probability_overlay_enabled": renderer?.probabilityOverlayEnabled ?? false
        ]

        captures.append(entry)
        manifest["session_id"] = sessionID
        manifest["renderer_version"] = "v1.2B3"
        manifest["project_root"] = projectRoot
        manifest["window_mode"] = currentWindowModeLabel()
        manifest["captures"] = captures
        manifest["capture_count"] = captures.count
        manifest["last_updated_utc"] = iso.string(from: Date())
        rmuV19NWriteJSON(manifest, to: url)
        writeSessionSummaryMarkdown(captures: captures, lastUpdatedUTC: iso.string(from: Date()))
    }

    func writeSessionSummaryMarkdown(captures: [[String: Any]], lastUpdatedUTC: String) {
        var lines: [String] = []
        lines.append("# RealMathUniverse v1.2B3 Session Summary")
        lines.append("")
        lines.append("- Session ID: \(sessionID)")
        lines.append("- Last updated UTC: \(lastUpdatedUTC)")
        lines.append("- Project root: \(projectRoot)")
        lines.append("- Window mode: \(currentWindowModeLabel())")
        lines.append("- Capture count: \(captures.count)")
        lines.append("- Burst count setting: \(burstCount)")
        lines.append("- Burst interval setting: \(String(format: "%.2f", burstInterval)) seconds")
        lines.append("")
        lines.append("## Captures")
        lines.append("")
        lines.append("| # | File | Behavior | Color | Sample | Clean | FPS | Frame ms |")
        lines.append("|---:|---|---|---|---:|---|---:|---:|")
        for (index, capture) in captures.enumerated() {
            let filename = capture["filename"] as? String ?? "unknown"
            let behavior = capture["behavior_mode"] as? String ?? "unknown"
            let color = capture["color_mode"] as? String ?? "unknown"
            let sample = capture["render_sample_count"] as? Int ?? 0
            let clean = capture["clean_capture"] as? Bool ?? false
            let fps = capture["fps"] as? Double ?? 0.0
            let frameMS = capture["frame_time_ms"] as? Double ?? 0.0
            lines.append("| \(index + 1) | \(filename) | \(behavior) | \(color) | \(sample) | \(clean) | \(String(format: "%.1f", fps)) | \(String(format: "%.2f", frameMS)) |")
        }
        lines.append("")
        let body = lines.joined(separator: "\n") + "\n"
        do {
            try body.write(to: markdownSummaryURL(), atomically: true, encoding: .utf8)
        } catch {
            print("Failed to write markdown session summary: \(error)")
        }
    }

    func increaseBurstCount() {
        burstCount = min(burstCount + 1, 30)
        print("Burst count: \(burstCount)")
        hud?.updateText()
    }

    func decreaseBurstCount() {
        burstCount = max(burstCount - 1, 1)
        print("Burst count: \(burstCount)")
        hud?.updateText()
    }

    func increaseBurstInterval() {
        burstInterval = min(burstInterval + 0.10, 5.00)
        print("Burst interval: \(String(format: "%.2f", burstInterval))")
        hud?.updateText()
    }

    func decreaseBurstInterval() {
        burstInterval = max(burstInterval - 0.10, 0.10)
        print("Burst interval: \(String(format: "%.2f", burstInterval))")
        hud?.updateText()
    }
}


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
        let url = rmuV18AOperatorURL(); try? FileManager.default.createDirectory(at: url.deletingLastPathComponent(), withIntermediateDirectories: true); rmuV19NWriteJSON(state, to: url); print("RMU v1.8A operator hotkey: \(reason)"); hud?.updateText()
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
    func rmuV18AToggleDatasetCouplingApply() { let s = rmuV18AReadOperatorState(); let cur = (s["dataset_coupling_mode"] as? String ?? "observe").lowercased(); let turnOn = cur != "apply"; rmuV18AWriteOperatorState(["dataset_coupling_mode": turnOn ? "apply" : "observe", "auto_fields_enabled": turnOn, "active_auto_domain": turnOn ? "field" : (s["active_auto_domain"] as? String ?? "behavior")], reason: turnOn ? "dataset_coupling_apply_on" : "dataset_coupling_observe_off") }
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
        if shift && chars == "b" { rmuV18AToggleDatasetCouplingApply(); return true }
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

let app = NSApplication.shared
let delegate = AppDelegate()
app.delegate = delegate
app.run()


// v1.3F7 note:
// HUD should expose TURB = particleTurbulence and COH = particleCohesion near particle speed/mass readouts.
// Renderer force stack should add turbulence force and cohesion force before damping and position integration.
