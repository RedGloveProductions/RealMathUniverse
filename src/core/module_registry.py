"""
Module registry with graceful degradation.

v0.3A update:
    - initialize_modules can pass headless state to modules that accept it.
    - update_modules can run the renderer after physics modules.
    - modules that still use initialize() with no args continue to work.
"""

from __future__ import annotations

from importlib import import_module
from typing import Any


class ModuleRegistry:
    def __init__(
        self,
        module_config: dict[str, Any],
        configs: dict[str, dict[str, Any]],
        profile,
        compute,
        buffer_registry,
        solver_registry,
        diagnostics,
    ):
        self.module_config = module_config
        self.configs = configs
        self.profile = profile
        self.compute = compute
        self.buffer_registry = buffer_registry
        self.solver_registry = solver_registry
        self.diagnostics = diagnostics
        self.modules: dict[str, Any] = {}
        self.skipped: dict[str, str] = {}
        self.failed: dict[str, str] = {}

    def load_modules(self) -> None:
        for name, raw in self.module_config.get("modules", {}).items():
            enabled = bool(raw.get("enabled", True))
            required = bool(raw.get("required", False))
            module_path = raw.get("module")
            class_name = raw.get("class")

            if not enabled:
                self.skipped[name] = "disabled_by_config"
                self.diagnostics.info(f"Module skipped: {name} disabled by config")
                continue

            try:
                if not module_path or not class_name:
                    raise ValueError("Missing module path or class name.")

                module = import_module(module_path)
                cls = getattr(module, class_name)
                instance = cls(
                    name=name,
                    configs=self.configs,
                    profile=self.profile,
                    compute=self.compute,
                    buffer_registry=self.buffer_registry,
                    solver_registry=self.solver_registry,
                    diagnostics=self.diagnostics,
                )
                self.modules[name] = instance
                self.diagnostics.info(f"Loaded module '{name}' -> {module_path}.{class_name}")

            except Exception as exc:
                self.failed[name] = str(exc)
                message = f"Failed to load module '{name}': {exc}"
                if required or self.profile.strict_physics_mode:
                    raise RuntimeError(message) from exc
                self.diagnostics.warn(message)

    def initialize_modules(self, headless: bool = False) -> None:
        for name, module in self.modules.items():
            if hasattr(module, "initialize"):
                self.diagnostics.info(f"Initializing module: {name}")
                try:
                    module.initialize(headless=headless)
                except TypeError:
                    module.initialize()

    def update_modules(self, dt: float, sim_time: float) -> None:
        # Run non-render modules first so renderer sees the latest particle state.
        for name, module in self.modules.items():
            if name == "renderer_3d":
                continue
            if hasattr(module, "update"):
                module.update(dt=dt, sim_time=sim_time)

        renderer = self.modules.get("renderer_3d")
        if renderer is not None and hasattr(renderer, "update"):
            renderer.update(dt=dt, sim_time=sim_time)

    def shutdown_modules(self) -> None:
        for name, module in self.modules.items():
            if hasattr(module, "shutdown"):
                self.diagnostics.info(f"Shutting down module: {name}")
                module.shutdown()

    def describe(self) -> dict[str, Any]:
        return {
            "loaded": sorted(self.modules.keys()),
            "skipped": self.skipped,
            "failed": self.failed,
        }
