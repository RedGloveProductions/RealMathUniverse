import AppKit
import Foundation
import ImageIO
import Metal
import MetalKit
import simd

struct Particle {
    var position: SIMD3<Float>
}

final class ParticleFrameLoader {
    let binaryURL: URL
    let metadataURL: URL
    var lastModificationDate: Date?
    var particles: [Particle] = []
    var worldRadius: Float = 6.0
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

final class HUDOverlayController {
    let containerView: NSView
    let frameLoader: ParticleFrameLoader
    weak var renderer: MetalRenderer?

    let statsPanel = NSVisualEffectView()
    let controlsPanel = NSVisualEffectView()
    let fieldPanel = NSVisualEffectView()
    let statsText = NSTextField(labelWithString: "")
    let controlsText = NSTextField(labelWithString: "")
    let fieldText = NSTextField(labelWithString: "")

    var overlaysVisible = true
    var statsVisible = true
    var controlsVisible = true
    var fieldPanelVisible = true
    var compactMode = false

    init(containerView: NSView, frameLoader: ParticleFrameLoader, renderer: MetalRenderer) {
        self.containerView = containerView
        self.frameLoader = frameLoader
        self.renderer = renderer
        buildPanels()
        updateLayout()
        updateText()
    }

    func buildPanels() {
        configure(panel: statsPanel)
        configure(panel: controlsPanel)
        configure(panel: fieldPanel)
        configureLabel(statsText)
        configureLabel(controlsText)
        configureLabel(fieldText)
        statsPanel.addSubview(statsText)
        controlsPanel.addSubview(controlsText)
        fieldPanel.addSubview(fieldText)
        containerView.addSubview(statsPanel)
        containerView.addSubview(controlsPanel)
        containerView.addSubview(fieldPanel)
    }

    func configure(panel: NSVisualEffectView) {
        panel.material = .hudWindow
        panel.blendingMode = .withinWindow
        panel.state = .active
        panel.wantsLayer = true
        panel.layer?.cornerRadius = 14
        panel.layer?.masksToBounds = true
    }

    func configureLabel(_ label: NSTextField) {
        label.font = NSFont.monospacedSystemFont(ofSize: 13, weight: .regular)
        label.textColor = NSColor(calibratedWhite: 0.92, alpha: 1.0)
        label.backgroundColor = .clear
        label.isBordered = false
        label.isEditable = false
        label.isSelectable = false
        label.lineBreakMode = .byWordWrapping
        label.maximumNumberOfLines = 0
    }

    func updateLayout() {
        let bounds = containerView.bounds
        let margin: CGFloat = 18
        let top: CGFloat = 18

        if compactMode {
            statsPanel.frame = NSRect(x: margin, y: bounds.height - top - 140, width: 420, height: 140)
            controlsPanel.frame = NSRect(x: bounds.width - margin - 430, y: bounds.height - top - 170, width: 430, height: 170)
            fieldPanel.frame = NSRect(x: bounds.midX - 310, y: margin, width: 620, height: 116)
        } else {
            statsPanel.frame = NSRect(x: margin, y: bounds.height - top - 430, width: 455, height: 430)
            controlsPanel.frame = NSRect(x: bounds.width - margin - 610, y: bounds.height - top - 520, width: 610, height: 520)
            fieldPanel.frame = NSRect(x: bounds.midX - 420, y: margin, width: 840, height: 156)
        }

        let inset: CGFloat = 14
        statsText.frame = statsPanel.bounds.insetBy(dx: inset, dy: inset)
        controlsText.frame = controlsPanel.bounds.insetBy(dx: inset, dy: inset)
        fieldText.frame = fieldPanel.bounds.insetBy(dx: inset, dy: inset)
    }

    func updateText() {
        guard let renderer = renderer else { return }
        let dataAge = Date().timeIntervalSince1970 - frameLoader.lastMetadataUnix
        let fileStatus = frameLoader.metadataLoaded ? "LIVE" : "WAITING"
        let displayRadius = renderer.manualWorldRadius ?? frameLoader.worldRadius

        let selected = renderer.selectedFieldLayerName.uppercased()
        let selectedEnabled = renderer.fieldLayerEnabled[renderer.selectedFieldLayerIndex] ? "ON" : "OFF"
        let systemState = renderer.fieldLayersEnabled ? "ON" : "OFF"
        fieldText.stringValue = """
        FIELD LAYERS: \(systemState)        SELECTED: \(selected)        SELECTED ENABLED: \(selectedEnabled)        WEIGHT: \(String(format: "%.2f", renderer.selectedFieldLayerWeight))
        VCV: \(renderer.vcvDisplayStatus())        FIELD CTRL: \(renderer.vcvFieldControlEnabled ? "ON" : "OFF")        SAFE: \(renderer.vcvSafeModeEnabled ? "ON" : "OFF")        SMOOTH: \(String(format: "%.2f", renderer.vcvSmoothingAmount))
        \(renderer.vcvMonitorVisible ? renderer.vcvChannelCompactSummary() : "OSC MONITOR: hidden")
        CLAMP: \(renderer.vcvLastClampEvent)
        RECIPE: \(renderer.fieldLayerSummary())
        CONTROLS: F fields   TAB select   SPACE on/off   / \\ weight   SHIFT+V VCV   SHIFT+O OSC   SHIFT+C safe mode
        """

        if compactMode {
            statsText.stringValue = """
            RMU v0.9B | \(fileStatus) | \(String(format: "%.1f", renderer.currentFPS)) fps
            frame \(String(format: "%.2f", renderer.currentFrameTimeMS)) ms | late \(renderer.lateFrameWarning)
            \(frameLoader.behaviorMode) | \(renderer.colorModeName)
            points \(frameLoader.latestPointCount) / source \(frameLoader.sourceParticleCount)
            sim \(String(format: "%.1f", frameLoader.latestSimTime)) | radius \(String(format: "%.2f", displayRadius))
            trails \(renderer.trailsEnabled) len \(renderer.trailLength)
            FIELD SYSTEM: \(renderer.fieldLayersEnabled ? "ON" : "OFF")
            SELECTED: \(renderer.selectedFieldLayerName.uppercased()) weight \(String(format: "%.2f", renderer.selectedFieldLayerWeight)) enabled \(renderer.fieldLayerEnabled[renderer.selectedFieldLayerIndex])
            AUTO CAMERA: \(renderer.autoCameraEnabled ? "ON" : "OFF") | STATE: \(renderer.activeVisualStateName)
            SCENE: \(renderer.activeScenePresetName)
            VCV: \(renderer.vcvDisplayStatus()) | FIELD CTRL: \(renderer.vcvFieldControlEnabled ? "ON" : "OFF") | PROB: \(renderer.probabilitySource)
            \(renderer.vcvMonitorVisible ? renderer.vcvChannelCompactSummary() : "OSC MONITOR: hidden")
            RECIPE: \(renderer.fieldLayerSummary())
            """

            controlsText.stringValue = """
            S shot  J clean  K burst  L clean burst
            Y presentation  H hud  G grid  O rings
            F fields  TAB select  SPACE on/off
            / \\ field weight  SHIFT+V VCV  SHIFT+O OSC
            SHIFT+C safe mode  OPT+SHIFT+1-8 ch enable
            M compact  C color
            ;/' burst count  U/I interval
            8/9/0 samples 25/50/100k  X reset
            ESC quit
            """
            return
        }

        statsText.stringValue = """
        REALMATHUNIVERSE v0.9B
        status: \(fileStatus)
        renderer fps: \(String(format: "%.1f", renderer.currentFPS))
        frame time ms: \(String(format: "%.2f", renderer.currentFrameTimeMS))
        late frame warning: \(renderer.lateFrameWarning)
        renderer frame: \(renderer.frameIndex)
        point count: \(frameLoader.latestPointCount)
        source particles: \(frameLoader.sourceParticleCount)
        sim frame: \(frameLoader.latestFrameIndex)
        sim time: \(String(format: "%.2f", frameLoader.latestSimTime))
        profile: \(frameLoader.latestProfile)
        backend: \(frameLoader.latestComputeBackend)
        behavior: \(frameLoader.behaviorMode)
        respawn: \(frameLoader.respawnOnCapture)
        color mode: \(renderer.colorModeName)
        rotation: \(String(format: "%.1f", renderer.rotationRadians * 180.0 / .pi))°
        pan: \(String(format: "%.2f", renderer.panX)), \(String(format: "%.2f", renderer.panY))
        world radius: \(String(format: "%.2f", frameLoader.worldRadius))
        display radius: \(String(format: "%.2f", displayRadius))
        point size: \(String(format: "%.1f", renderer.pointSize))
        trails: \(renderer.trailsEnabled) length \(renderer.trailLength)
        grid: \(renderer.gridEnabled)
        center marker: \(renderer.centerMarkerEnabled)
        horizon ring: \(renderer.horizonRingEnabled)
        curvature overlay: \(renderer.curvatureOverlayEnabled)
        probability overlay: \(renderer.probabilityOverlayEnabled)
        presentation mode: \(renderer.presentationModeEnabled)
        FIELD SYSTEM: \(renderer.fieldLayersEnabled ? "ON" : "OFF")
        SELECTED FIELD: \(renderer.selectedFieldLayerName.uppercased())
        SELECTED WEIGHT: \(String(format: "%.2f", renderer.selectedFieldLayerWeight))
        SELECTED ENABLED: \(renderer.fieldLayerEnabled[renderer.selectedFieldLayerIndex])
        FIELD RECIPE: \(renderer.fieldLayerSummary())
        AUTO CAMERA: \(renderer.autoCameraEnabled ? "ON" : "OFF")
        ACTIVE STATE: \(renderer.activeVisualStateName)
        ACTIVE SCENE: \(renderer.activeScenePresetName)
        VCV STATUS: \(renderer.vcvStatus)
        PROBABILITY SOURCE: \(renderer.probabilitySource)
        VCV FIELD CONTROL: \(renderer.vcvFieldControlEnabled)
        VCV VALUES: \(renderer.vcvLastValues)
        VCV CHANNELS: \(renderer.vcvChannelCompactSummary())
        VCV ENABLED: \(renderer.vcvChannelEnableSummary())
        VCV SAFE MODE: \(renderer.vcvSafeModeEnabled)
        VCV LAST CLAMP: \(renderer.vcvLastClampEvent)
        LAST STATE MSG: \(renderer.lastVisualStateMessage)
        sample request: \(frameLoader.renderSampleCount)
        metadata: \(frameLoader.metadataVersion)
        metadata age: \(String(format: "%.2f", dataAge))s
        """

        controlsText.stringValue = """
        CONTROLS

        S       save screenshot
        J       save clean screenshot
        K       screenshot burst
        L       clean screenshot burst
        burst   count/interval adjusted with ;/' and U/I
        T       toggle always-on-top
        H       show/hide all HUD overlays
        Y       toggle presentation mode
        M       compact HUD mode
        ; / '   decrease / increase burst count
        U / I   decrease / increase burst interval
        1 / 2   stats / controls overlay

        3       preset: stable orbit cloud
        4       preset: black hole capture
        5       preset: accretion disk
        6       preset: field pressure bounce
        7       preset: infinite collapse
        R       toggle respawn on capture

        8       sample preset 25k
        9       sample preset 50k
        0       sample preset 100k

        P       toggle trails
        , / .   decrease / increase trail length
        N       clear trails

        F       toggle field layers
        TAB     select next field layer
        SPACE   toggle selected field layer
        /       decrease selected field weight
        \\      increase selected field weight
        SHIFT+V toggle VCV field control
        SHIFT+O toggle OSC monitor in HUD
        SHIFT+C toggle VCV safe mode/clamp
        OPT+SHIFT+1-8 toggle VCV channel enable

        G       toggle grid + probability halo
        O       toggle center marker + horizon + curvature rings
        C       cycle color mode
        V       classic white mode
        B       behavior color mode

        arrows  pan camera
        A / D   rotate camera
        W / Z   zoom in / out
        Q / E   fine zoom
        X       reset camera
        + / -   point size
        [ / ]   display radius zoom
        ESC     quit renderer
        """
    }

    func applyVisibility() {
        statsPanel.isHidden = !(overlaysVisible && statsVisible)
        controlsPanel.isHidden = !(overlaysVisible && controlsVisible)
        fieldPanel.isHidden = !(overlaysVisible && fieldPanelVisible)
    }

    func toggleAll() { overlaysVisible.toggle(); applyVisibility() }
    func toggleStats() { statsVisible.toggle(); applyVisibility() }
    func toggleControls() { controlsVisible.toggle(); applyVisibility() }
    func toggleCompact() { compactMode.toggle(); updateLayout(); updateText() }
}

final class MetalRenderer: NSObject, MTKViewDelegate {
    let device: MTLDevice
    let commandQueue: MTLCommandQueue
    let pipelineState: MTLRenderPipelineState
    let frameLoader: ParticleFrameLoader
    let projectRoot: String

    var particleBuffer: MTLBuffer?
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
    var vcvFieldControlEnabled = false
    var vcvLastValues = "none"
    var vcvMonitorVisible = true
    var vcvSmoothingAmount: Float = 0.22
    var vcvChannelLabels: [String] = [
        "probability", "radial", "orbital", "vertical",
        "turbulence", "shell", "color", "scene"
    ]
    var vcvChannelTargets: [String] = [
        "probability_value", "field_layer_weights[0]", "field_layer_weights[1]", "field_layer_weights[2]",
        "field_layer_weights[3]", "field_layer_weights[4]", "color_mode", "scene_index"
    ]
    var vcvChannelEnabled: [Bool] = [true, true, true, true, true, true, true, true]
    var vcvChannelValues: [Float] = [0, 0, 0, 0, 0, 0, 0, 0]
    var vcvRawChannelValues: [Float] = [0, 0, 0, 0, 0, 0, 0, 0]
    var vcvSafeModeEnabled = true
    var vcvLastClampEvent = "none"

    var trailsEnabled = true
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
    var fieldLayerWeights: [Float] = [0.25, 1.00, 0.10, 0.05, 0.20]
    var fieldPhase: Float = 0.0

    var gridBuffer: MTLBuffer?
    var centerBuffer: MTLBuffer?
    var horizonBuffer: MTLBuffer?
    var curvatureRingBuffers: [MTLBuffer] = []
    var curvatureRingCounts: [Int] = []
    var probabilityHaloBuffer: MTLBuffer?
    var probabilityHaloCount: Int = 0

    weak var hud: HUDOverlayController?

    var selectedFieldLayerName: String {
        return fieldLayerNames[max(0, min(selectedFieldLayerIndex, fieldLayerNames.count - 1))]
    }

    var selectedFieldLayerWeight: Float {
        return fieldLayerWeights[max(0, min(selectedFieldLayerIndex, fieldLayerWeights.count - 1))]
    }

    var colorModeName: String {
        switch colorMode {
        case 1: return "depth"
        case 2: return "radial"
        case 3: return "behavior"
        case 4: return "thermal"
        default: return "classic"
        }
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
            uint vertexID [[vertex_id]]
        ) {
            Particle p = particles[vertexID];
            float3 fp = p.position;

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

                if (fieldEnabledShell == 1) {
                    float shellRadius = worldRadius * 0.72;
                    float shellWidth = max(worldRadius * 0.08, 0.05);
                    float q = (baseRadius - shellRadius) / shellWidth;
                    shellMask = exp(-(q * q)) * fieldWeightShell;
                    fp += dir * shellMask * 0.10;
                }
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
            } else if (colorMode == 1) {
                out.color = float4(0.25 + depth * 0.75, 0.45 + depth * 0.45, 1.0, alpha);
            } else if (colorMode == 2) {
                out.color = float4(0.25 + radial * 0.75, 0.8 - radial * 0.25, 1.0 - radial * 0.65, alpha);
            } else if (colorMode == 3) {
                out.color = float4(0.92, 0.72 + depth * 0.25, 0.35 + radial * 0.45, alpha);
            } else if (colorMode == 4) {
                out.color = float4(1.0, 0.35 + radial * 0.55, 0.10 + depth * 0.35, alpha);
            } else {
                out.color = float4(0.72 + depth * 0.28, 0.82 + depth * 0.18, 1.0, alpha);
            }

            if (fieldLayersEnabled == 1 && overlayMode == 0 && fieldEnabledShell == 1) {
                out.color.rgb = min(out.color.rgb + float3(shellMask * 0.35, shellMask * 0.25, shellMask * 0.12), float3(1.0, 1.0, 1.0));
            }

            out.pointSize = pointSize;
            return out;
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

    func draw(in view: MTKView) {
        let drawStart = CFAbsoluteTimeGetCurrent()
        frameLoader.loadIfNeeded()
        updateParticleBufferIfNeeded()

        guard let drawable = view.currentDrawable,
              let renderPassDescriptor = view.currentRenderPassDescriptor else { return }

        renderPassDescriptor.colorAttachments[0].clearColor = MTLClearColor(red: 0.02, green: 0.025, blue: 0.04, alpha: 1.0)
        renderPassDescriptor.colorAttachments[0].loadAction = .clear
        renderPassDescriptor.colorAttachments[0].storeAction = .store

        guard let commandBuffer = commandQueue.makeCommandBuffer(),
              let encoder = commandBuffer.makeRenderCommandEncoder(descriptor: renderPassDescriptor) else { return }

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

        if let buffer = particleBuffer, frameLoader.latestPointCount > 0 {
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
        updateAutoCamera()
        fieldPhase += 0.015

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

        encoder.setVertexBuffer(buffer, offset: 0, index: 0)
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
        encoder.drawPrimitives(type: .point, vertexStart: 0, vertexCount: count)
    }

    func updateParticleBufferIfNeeded() {
        let particles = frameLoader.particles
        guard !particles.isEmpty else { return }
        let byteCount = particles.count * MemoryLayout<Particle>.stride
        guard let newBuffer = device.makeBuffer(bytes: particles, length: byteCount, options: [.storageModeShared]) else { return }
        particleBuffer = newBuffer

        if trailsEnabled {
            trailBuffers.append(newBuffer)
            trailCounts.append(frameLoader.latestPointCount)
            while trailBuffers.count > trailLength {
                trailBuffers.removeFirst()
                trailCounts.removeFirst()
            }
        }
    }

    func printDiagnostics() {
        print("Metal renderer | fps=\(String(format: "%.1f", currentFPS)) | points=\(frameLoader.latestPointCount) | simFrame=\(frameLoader.latestFrameIndex) | behavior=\(frameLoader.behaviorMode) | color=\(colorModeName) | trails=\(trailsEnabled) len=\(trailLength) | presentation=\(presentationModeEnabled) | FIELD_SYSTEM=\(fieldLayersEnabled ? "ON" : "OFF") | SELECTED=\(selectedFieldLayerName) | WEIGHT=\(String(format: "%.2f", selectedFieldLayerWeight)) | ENABLED=\(fieldLayerEnabled[selectedFieldLayerIndex]) | VCV=\(vcvDisplayStatus()) | SAFE=\(vcvSafeModeEnabled) | \(vcvChannelCompactSummary())")
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
        if !vcvFieldControlEnabled {
            if vcvStatus.hasPrefix("external") { return "ACTIVE / field OFF" }
            if vcvStatus.hasPrefix("stale") { return "STALE / field OFF" }
            return "OFF / not detected"
        }
        if vcvStatus.hasPrefix("external") { return "ACTIVE" }
        if vcvStatus.hasPrefix("stale") { return "STALE - internal fallback" }
        return "OFF - internal fallback"
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
        var parts: [String] = []
        for i in 0..<min(vcvChannelValues.count, vcvChannelLabels.count) {
            let offMark = vcvChannelEnabled[i] ? "" : "x"
            let label = vcvChannelLabels[i]
            let raw = vcvRawChannelValues[i]
            let val = vcvChannelValues[i]
            parts.append("/ch/\(i + 1)\(offMark) \(label)=\(String(format: "%.2f", val)) raw=\(String(format: "%.2f", raw))")
        }
        return "OSC: " + parts.joined(separator: " | ")
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
        let clamped = max(0, min(value, 4))
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

        let timestamp = (json["timestamp_unix"] as? NSNumber)?.doubleValue ?? 0.0
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

        if let summary = json["summary"] as? String {
            vcvLastValues = summary
        }

        if let probabilityNumber = json["probability_value"] as? NSNumber {
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

        if let sceneNumber = json["scene_index"] as? NSNumber {
            let rawScene = sceneNumber.intValue
            let scene = vcvSafeModeEnabled ? clampVCVSceneIndex(rawScene) : rawScene
            vcvRawChannelValues[7] = Float(rawScene)
            vcvChannelValues[7] = Float(scene)
        }
    }

    func toggleVCVFieldControl() {
        vcvFieldControlEnabled.toggle()
        probabilitySource = vcvFieldControlEnabled ? "hybrid" : "internal"
        print("VCV field control: \(vcvFieldControlEnabled ? "ON" : "OFF")")
        hud?.updateText()
    }

    func visualStateDictionary(name: String, slot: Int? = nil) -> [String: Any] {
        return [
            "version": "0.9B",
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
                "vcv_safe_mode_enabled": vcvSafeModeEnabled
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
            vcvSafeModeEnabled = (vcv["vcv_safe_mode_enabled"] as? Bool) ?? vcvSafeModeEnabled
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

    func cycleColor() { colorMode = (colorMode + 1) % 5; hud?.updateText() }
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
        window.title = "RealMathUniverse Metal Renderer v0.9B"
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

        print("RealMathUniverse Metal Renderer v0.9B")
        print("Project root: \(projectRoot)")
        print("Field layers: F toggles system, TAB selects layer, SPACE toggles selected layer, / and \\ adjust selected weight")
        print("Session ID: \(sessionID)")
        print("Keys: S shot | J clean | K burst | L clean burst | Y presentation | F field layers | TAB select field | SPACE toggle field | /\\ weight | P trails | ESC quit")
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
            renderer?.toggleSelectedFieldLayer()
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
        case "r": currentRespawn.toggle(); writeControlState(respawnOnly: true)
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

    func controlStateURL() -> URL {
        URL(fileURLWithPath: projectRoot).appendingPathComponent("output").appendingPathComponent("control_state.json")
    }

    func ensureDefaultControlState() {
        let url = controlStateURL()
        if FileManager.default.fileExists(atPath: url.path) { return }
        try? FileManager.default.createDirectory(at: url.deletingLastPathComponent(), withIntermediateDirectories: true)
        writeJSON([
            "behavior_mode": "stable_orbit_cloud",
            "respawn_on_capture": false,
            "render_sample_count": 25000,
            "trails_enabled": true,
            "trail_length": 12,
            "grid_enabled": false,
            "updated_by": "metal_renderer_v0_9B1",
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

    func writePreset(behavior: String, respawn: Bool, pointSize: Float, radiusMultiplier: Float, colorMode: Int32) {
        currentRespawn = respawn
        renderer?.pointSize = pointSize
        renderer?.setColor(colorMode)
        if let base = renderer?.frameLoader.worldRadius {
            renderer?.manualWorldRadius = base * radiusMultiplier
        }
        applyFieldRecipeForBehavior(behavior)
        writeControlState(behavior: behavior)
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
        writeJSON(state, to: url)
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

        if let behavior = behavior { state["behavior_mode"] = behavior }
        state["respawn_on_capture"] = currentRespawn
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
        state["updated_by"] = "metal_renderer_v0_9B1"
        state["timestamp_unix"] = Date().timeIntervalSince1970
        writeJSON(state, to: url)
        print("Control state written by metal_renderer_v0_9B1: \(state)")
        hud?.updateText()
    }

    func writeJSON(_ object: [String: Any], to url: URL) {
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
        manifestDir().appendingPathComponent("RealMathUniverse_v0_9B_capture_manifest_\(sessionID).json")
    }

    func markdownSummaryURL() -> URL {
        manifestDir().appendingPathComponent("RealMathUniverse_v0_9B_session_summary_\(sessionID).md")
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

            let behavior = self.sanitized(self.renderer?.frameLoader.behaviorMode ?? "unknown")
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

            let fileName = "RealMathUniverse_v0_9B_\(behavior)_\(color)_\(sample)_\(captureType)\(burstSuffix)_\(stamp)_UTC.png"
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
        manifest["renderer_version"] = "v0.9B"
        manifest["project_root"] = projectRoot
        manifest["window_mode"] = currentWindowModeLabel()
        manifest["captures"] = captures
        manifest["capture_count"] = captures.count
        manifest["last_updated_utc"] = iso.string(from: Date())
        writeJSON(manifest, to: url)
        writeSessionSummaryMarkdown(captures: captures, lastUpdatedUTC: iso.string(from: Date()))
    }

    func writeSessionSummaryMarkdown(captures: [[String: Any]], lastUpdatedUTC: String) {
        var lines: [String] = []
        lines.append("# RealMathUniverse v0.9B Session Summary")
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

let app = NSApplication.shared
let delegate = AppDelegate()
app.delegate = delegate
app.run()
