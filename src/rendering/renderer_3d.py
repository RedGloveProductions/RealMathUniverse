"""
$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$
RealMathUniverse Renderer Module
Version: 0.4A

Backends:
    - metal_export: exports particle frames for external Swift/Metal renderer.
    - pygame: diagnostic CPU/Pygame renderer from v0.3A.

Default:
    metal_export

Important:
    The Metal path currently uses a binary file bridge. It is not yet zero-copy,
    but it moves the visible renderer to a real MetalKit GPU renderer now and
    preserves the renderer abstraction for later optimization.
$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$
"""

from __future__ import annotations

import time
from pathlib import Path

from src.rendering.metal_frame_exporter import MetalFrameExporter


class Renderer3DModule:
    def __init__(self, name, configs, profile, compute, buffer_registry, solver_registry, diagnostics):
        self.name = name
        self.configs = configs
        self.profile = profile
        self.compute = compute
        self.buffer_registry = buffer_registry
        self.solver_registry = solver_registry
        self.diagnostics = diagnostics

        self.enabled = False
        self.backend = "metal_export"
        self.project_root = Path(__file__).resolve().parents[2]

        self.metal_exporter = None

        self.pygame = None
        self.screen = None
        self.clock = None
        self.font = None
        self.frame_count = 0
        self.render_times_ms: list[float] = []
        self.last_render_ms = 0.0

    def initialize(self, headless: bool = False) -> None:
        cfg = self.configs["render_config"]["render"]
        self.enabled = bool(cfg.get("enabled", True))
        self.backend = str(cfg.get("backend", "metal_export"))

        if not self.enabled:
            self.diagnostics.info("Renderer disabled by config.")
            return

        if self.backend == "metal_export":
            self.metal_exporter = MetalFrameExporter(
                project_root=self.project_root,
                configs=self.configs,
                profile=self.profile,
                compute=self.compute,
                buffer_registry=self.buffer_registry,
                diagnostics=self.diagnostics,
            )
            self.diagnostics.info(
                "Renderer backend: metal_export. "
                "Run the Swift Metal renderer in a second terminal to view frames."
            )
            return

        if self.backend == "pygame":
            if headless:
                self.diagnostics.info("Pygame renderer inactive because headless mode is enabled.")
                self.enabled = False
                return
            self._initialize_pygame()
            return

        self.diagnostics.warn(f"Unknown render backend '{self.backend}'. Renderer disabled.")
        self.enabled = False

    def update(self, dt: float, sim_time: float) -> None:
        if not self.enabled:
            return

        if self.backend == "metal_export" and self.metal_exporter is not None:
            self.metal_exporter.update(sim_time=sim_time)
            return

        if self.backend == "pygame":
            self._update_pygame(dt=dt, sim_time=sim_time)

    def shutdown(self) -> None:
        if self.backend == "metal_export" and self.metal_exporter is not None:
            payload = self.metal_exporter.diagnostics_payload()
            self.diagnostics.info(
                f"Metal export timing | exports={payload['export_count']} "
                f"avg={payload['average_export_ms']:.3f}ms max={payload['max_export_ms']:.3f}ms "
                f"file={payload['binary_path']}"
            )
            return

        if self.enabled and self.pygame is not None:
            self.pygame.quit()

        if self.render_times_ms:
            avg = sum(self.render_times_ms) / len(self.render_times_ms)
            self.diagnostics.info(
                f"Pygame renderer timing | frames={len(self.render_times_ms)} "
                f"avg={avg:.3f}ms max={max(self.render_times_ms):.3f}ms"
            )

    def _initialize_pygame(self) -> None:
        cfg = self.configs["render_config"]["render"]
        try:
            import pygame
            self.pygame = pygame
            pygame.init()
            pygame.font.init()

            width = int(cfg.get("width", 1920))
            height = int(cfg.get("height", 1080))
            flags = 0
            if bool(cfg.get("fullscreen", False)):
                flags |= pygame.FULLSCREEN

            self.screen = pygame.display.set_mode((width, height), flags)
            pygame.display.set_caption("RealMathUniverse v0.4A Pygame Fallback Renderer")
            self.clock = pygame.time.Clock()
            self.font = pygame.font.SysFont("Menlo", 16)

            self.diagnostics.info(
                f"Pygame fallback renderer initialized: {width}x{height}, "
                f"sample_count={cfg.get('render_sample_count', 25000)}"
            )
        except Exception as exc:
            self.enabled = False
            self.diagnostics.warn(f"Pygame renderer failed to initialize and will be disabled: {exc}")

    def _update_pygame(self, dt: float, sim_time: float) -> None:
        start = time.perf_counter()

        pygame = self.pygame
        cfg = self.configs["render_config"]["render"]

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.enabled = False
                pygame.display.quit()
                return
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                self.enabled = False
                pygame.display.quit()
                return

        width, height = self.screen.get_size()
        self.screen.fill((5, 7, 12))

        points = self._get_sampled_particle_positions()
        self._draw_particles(points, width, height)
        self._draw_hud(sim_time=sim_time, width=width, height=height)

        pygame.display.flip()
        target_fps = int(cfg.get("target_render_fps", 60))
        if target_fps > 0:
            self.clock.tick(target_fps)

        self.frame_count += 1
        self.last_render_ms = (time.perf_counter() - start) * 1000.0
        self.render_times_ms.append(self.last_render_ms)

    def _get_sampled_particle_positions(self):
        cfg = self.configs["render_config"]["render"]
        sample_count = int(cfg.get("render_sample_count", 25000))
        positions = self.buffer_registry.get("particle_positions")
        n = int(positions.shape[0])
        if n <= 0:
            return []

        stride = max(1, n // max(1, sample_count))
        sampled = positions[0:n:stride, 0:3]

        if hasattr(sampled, "detach"):
            return sampled.detach().cpu().numpy()
        if hasattr(sampled, "get"):
            return sampled.get()
        return sampled

    def _draw_particles(self, points, width: int, height: int) -> None:
        cfg = self.configs["render_config"]["render"]
        world_radius = float(cfg.get("render_world_radius", 6.0))
        point_radius = int(cfg.get("point_radius", 1))
        max_points = int(cfg.get("render_sample_count", 25000))

        cx = width * 0.5
        cy = height * 0.5
        scale = min(width, height) / (2.0 * world_radius)

        pygame = self.pygame

        count = min(len(points), max_points)
        for i in range(count):
            x = float(points[i][0])
            y = float(points[i][1])
            z = float(points[i][2])

            sx = int(cx + x * scale)
            sy = int(cy + z * scale)

            if sx < 0 or sx >= width or sy < 0 or sy >= height:
                continue

            brightness = int(max(80, min(255, 160 + y * 35)))
            color = (brightness, brightness, 255)
            pygame.draw.circle(self.screen, color, (sx, sy), point_radius)

    def _draw_hud(self, sim_time: float, width: int, height: int) -> None:
        cfg = self.configs["render_config"]["render"]
        if not bool(cfg.get("hud_enabled", True)) or self.font is None:
            return

        measured_fps = self.clock.get_fps() if self.clock else 0.0
        lines = [
            "RealMathUniverse v0.4A Pygame Fallback Renderer",
            f"profile: {self.profile.name}",
            f"backend: {self.compute.backend_report.backend_name}",
            f"particles: {self.profile.particle_count:,}",
            f"render sample: {cfg.get('render_sample_count', 25000):,}",
            f"sim time: {sim_time:.3f}",
            f"render ms: {self.last_render_ms:.3f}",
            f"display fps: {measured_fps:.1f}",
            "ESC closes renderer"
        ]

        y = 10
        for line in lines:
            surface = self.font.render(line, True, (230, 235, 245))
            self.screen.blit(surface, (10, y))
            y += 18
