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
    let statsText = NSTextField(labelWithString: "")
    let controlsText = NSTextField(labelWithString: "")

    var overlaysVisible = true
    var statsVisible = true
    var controlsVisible = true
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
        configureLabel(statsText)
        configureLabel(controlsText)
        statsPanel.addSubview(statsText)
        controlsPanel.addSubview(controlsText)
        containerView.addSubview(statsPanel)
        containerView.addSubview(controlsPanel)
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
        } else {
            statsPanel.frame = NSRect(x: margin, y: bounds.height - top - 430, width: 455, height: 430)
            controlsPanel.frame = NSRect(x: bounds.width - margin - 610, y: bounds.height - top - 520, width: 610, height: 520)
        }

        let inset: CGFloat = 14
        statsText.frame = statsPanel.bounds.insetBy(dx: inset, dy: inset)
        controlsText.frame = controlsPanel.bounds.insetBy(dx: inset, dy: inset)
    }

    func updateText() {
        guard let renderer = renderer else { return }
        let dataAge = Date().timeIntervalSince1970 - frameLoader.lastMetadataUnix
        let fileStatus = frameLoader.metadataLoaded ? "LIVE" : "WAITING"
        let displayRadius = renderer.manualWorldRadius ?? frameLoader.worldRadius

        if compactMode {
            statsText.stringValue = """
            RMU v0.6C | \(fileStatus) | \(String(format: "%.1f", renderer.currentFPS)) fps
            frame \(String(format: "%.2f", renderer.currentFrameTimeMS)) ms | late \(renderer.lateFrameWarning)
            \(frameLoader.behaviorMode) | \(renderer.colorModeName)
            points \(frameLoader.latestPointCount) / source \(frameLoader.sourceParticleCount)
            sim \(String(format: "%.1f", frameLoader.latestSimTime)) | radius \(String(format: "%.2f", displayRadius))
            trails \(renderer.trailsEnabled) len \(renderer.trailLength)
            """

            controlsText.stringValue = """
            S shot  J clean  K burst  L clean burst
            Y/F presentation  H hud  G grid  O rings
            M compact  N clear trails  C color
            ;/' burst count  U/I interval
            8/9/0 samples 25/50/100k  X reset
            ESC quit
            """
            return
        }

        statsText.stringValue = """
        REALMATHUNIVERSE v0.6C
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
        presentation mode: \(renderer.presentationModeEnabled)
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
        Y / F   toggle presentation mode
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

        G       toggle grid
        O       toggle center marker + horizon ring
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

    var trailsEnabled = true
    var trailLength = 12
    var trailAlphaFloor: Float = 0.08
    var trailAlphaCeiling: Float = 0.42

    var gridEnabled = false
    var centerMarkerEnabled = true
    var horizonRingEnabled = true
    var presentationModeEnabled = false
    var gridBuffer: MTLBuffer?
    var centerBuffer: MTLBuffer?
    var horizonBuffer: MTLBuffer?

    weak var hud: HUDOverlayController?

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
            uint vertexID [[vertex_id]]
        ) {
            Particle p = particles[vertexID];

            float c = cos(rotationRadians);
            float s = sin(rotationRadians);
            float rx = p.position.x * c - p.position.z * s;
            float rz = p.position.x * s + p.position.z * c;

            float x = clamp((rx / worldRadius) + pan.x, -1.5, 1.5);
            float y = clamp((rz / worldRadius) + pan.y, -1.5, 1.5);
            float depth = clamp((p.position.y / worldRadius) * 0.5 + 0.5, 0.0, 1.0);
            float radial = clamp(length(float2(rx, rz)) / worldRadius, 0.0, 1.0);

            VertexOut out;
            out.position = float4(x, y, 0.0, 1.0);

            if (overlayMode == 1) {
                out.color = float4(0.18, 0.35, 0.65, alpha);
            } else if (overlayMode == 2) {
                out.color = float4(0.30, 0.75, 1.0, alpha);
            } else if (overlayMode == 3) {
                out.color = float4(1.0, 0.55, 0.18, alpha);
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

        encoder.setVertexBuffer(buffer, offset: 0, index: 0)
        encoder.setVertexBytes(&radius, length: MemoryLayout<Float>.stride, index: 1)
        encoder.setVertexBytes(&mutablePointSize, length: MemoryLayout<Float>.stride, index: 2)
        encoder.setVertexBytes(&rot, length: MemoryLayout<Float>.stride, index: 3)
        encoder.setVertexBytes(&pan, length: MemoryLayout<SIMD2<Float>>.stride, index: 4)
        encoder.setVertexBytes(&cm, length: MemoryLayout<Int32>.stride, index: 5)
        encoder.setVertexBytes(&a, length: MemoryLayout<Float>.stride, index: 6)
        encoder.setVertexBytes(&om, length: MemoryLayout<Int32>.stride, index: 7)
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
        print("Metal renderer | fps=\(String(format: "%.1f", currentFPS)) | points=\(frameLoader.latestPointCount) | simFrame=\(frameLoader.latestFrameIndex) | behavior=\(frameLoader.behaviorMode) | color=\(colorModeName) | trails=\(trailsEnabled) len=\(trailLength) | presentation=\(presentationModeEnabled)")
    }

    func increasePointSize() { pointSize = min(pointSize + 0.5, 12.0); hud?.updateText() }
    func decreasePointSize() { pointSize = max(pointSize - 0.5, 0.5); hud?.updateText() }
    func zoomOut() { let current = manualWorldRadius ?? frameLoader.worldRadius; manualWorldRadius = min(current * 1.15, 100.0); hud?.updateText() }
    func zoomIn() { let current = manualWorldRadius ?? frameLoader.worldRadius; manualWorldRadius = max(current / 1.15, 0.25); hud?.updateText() }
    func pan(dx: Float, dy: Float) { panX += dx; panY += dy; hud?.updateText() }
    func rotate(delta: Float) { rotationRadians += delta; hud?.updateText() }
    func resetCamera() { panX = 0; panY = 0; rotationRadians = 0; manualWorldRadius = nil; hud?.updateText() }
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
    func toggleGrid() { gridEnabled.toggle(); hud?.updateText() }
    func toggleRings() { centerMarkerEnabled.toggle(); horizonRingEnabled.toggle(); hud?.updateText() }
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
    let gridEnabled: Bool
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
        window.title = "RealMathUniverse Metal Renderer v0.6C"
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

        print("RealMathUniverse Metal Renderer v0.6C")
        print("Project root: \(projectRoot)")
        print("Session ID: \(sessionID)")
        print("Keys: S shot | J clean | K burst | L clean burst | H HUD | Y/F presentation | ;/' burst count | U/I interval | P trails | G grid | O rings | ESC quit")
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
        case 123: renderer?.pan(dx: -panStep, dy: 0)
        case 124: renderer?.pan(dx: panStep, dy: 0)
        case 125: renderer?.pan(dx: 0, dy: -panStep)
        case 126: renderer?.pan(dx: 0, dy: panStep)
        default: break
        }

        guard let characters = event.charactersIgnoringModifiers?.lowercased() else { return }

        switch characters {
        case "s": saveWindowScreenshot(clean: false)
        case "j": saveWindowScreenshot(clean: true)
        case "k": captureBurst(clean: false, total: burstCount, interval: burstInterval)
        case "l": captureBurst(clean: true, total: burstCount, interval: burstInterval)
        case "t": alwaysOnTop.toggle(); window?.level = alwaysOnTop ? .floating : .normal
        case "h": hud?.toggleAll(); hud?.updateText()
        case "y", "f": togglePresentationMode()
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
            "updated_by": "metal_renderer_v0_6B",
            "timestamp_unix": Date().timeIntervalSince1970
        ], to: url)
    }

    func writePreset(behavior: String, respawn: Bool, pointSize: Float, radiusMultiplier: Float, colorMode: Int32) {
        currentRespawn = respawn
        renderer?.pointSize = pointSize
        renderer?.setColor(colorMode)
        if let base = renderer?.frameLoader.worldRadius {
            renderer?.manualWorldRadius = base * radiusMultiplier
        }
        writeControlState(behavior: behavior)
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
        state["updated_by"] = "metal_renderer_v0_6B"
        state["timestamp_unix"] = Date().timeIntervalSince1970
        writeJSON(state, to: url)
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
        manifestDir().appendingPathComponent("RealMathUniverse_v0_6C_capture_manifest_\(sessionID).json")
    }

    func markdownSummaryURL() -> URL {
        manifestDir().appendingPathComponent("RealMathUniverse_v0_6C_session_summary_\(sessionID).md")
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
            gridEnabled: renderer?.gridEnabled ?? false,
            centerMarkerEnabled: renderer?.centerMarkerEnabled ?? true,
            horizonRingEnabled: renderer?.horizonRingEnabled ?? true
        )
    }

    func applyOverlaySnapshot(_ snapshot: OverlaySnapshot) {
        hud?.overlaysVisible = snapshot.hudOverlaysVisible
        hud?.statsVisible = snapshot.hudStatsVisible
        hud?.controlsVisible = snapshot.hudControlsVisible
        hud?.applyVisibility()
        renderer?.gridEnabled = snapshot.gridEnabled
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

            let fileName = "RealMathUniverse_v0_6C_\(behavior)_\(color)_\(sample)_\(captureType)\(burstSuffix)_\(stamp)_UTC.png"
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
            "burst_interval_setting": burstInterval
        ]

        captures.append(entry)
        manifest["session_id"] = sessionID
        manifest["renderer_version"] = "v0.6C"
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
        lines.append("# RealMathUniverse v0.6C Session Summary")
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
