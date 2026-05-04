"""
$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$
RealMathUniverse v0.1B GPU Preflight
Author: Joe Stem / RedGloveProductions
Version: 0.1B

Purpose:
    Estimate simulation memory requirements before major allocations happen.
    This keeps the engine GPU-first and prevents scaling profiles from silently
    attempting impossible allocations.

Process:
    - Read the active execution profile.
    - Estimate particle-buffer memory.
    - Estimate field-grid memory.
    - Estimate total memory and safety margin.
    - Compare against available device memory when the backend can report it.
    - Produce a serializable report for run_summary.json.

Product:
    A preflight report that tells the engine whether the selected profile is
    reasonable for the selected compute backend.

Important:
    This is an estimate. Exact GPU allocation behavior depends on backend,
    allocator, driver, OS, and active graphics workload.
$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any


@dataclass
class GPUPreflightReport:
    profile_name: str
    backend_name: str
    device_name: str
    is_gpu: bool
    particle_count: int
    field_resolution: list[int]
    precision: str
    bytes_per_value: int
    particle_buffer_bytes: int
    field_buffer_bytes: int
    total_estimated_bytes: int
    total_estimated_mb: float
    total_estimated_gb: float
    safety_margin: float
    estimated_with_margin_bytes: int
    estimated_with_margin_mb: float
    estimated_with_margin_gb: float
    available_device_bytes: int | None
    available_device_mb: float | None
    available_device_gb: float | None
    fits_available_memory: bool | None
    strict_gpu: bool
    allow_cpu_fallback: bool
    warnings: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class GPUPreflight:
    """
    Preflight estimator for GPU-first runs.
    """

    def __init__(self, profile, compute, gpu_config: dict[str, Any], diagnostics):
        self.profile = profile
        self.compute = compute
        self.gpu_config = gpu_config
        self.diagnostics = diagnostics

    def run(self) -> GPUPreflightReport:
        gpu_cfg = self.gpu_config.get("gpu", {})
        safety_margin = float(gpu_cfg.get("memory_safety_margin", 0.20))

        bytes_per_value = self._bytes_per_value(self.profile.precision)

        particle_count = int(self.profile.particle_count)
        nx, ny, nz = self.profile.field_resolution
        field_cells = int(nx) * int(ny) * int(nz)

        # Current v0.1B core buffers:
        # particle_positions: [N,4] float
        # particle_velocities: [N,4] float
        # particle_forces: [N,4] float
        # particle_mass: [N] float
        # particle_species: [N] int32
        particle_float_channels = 4 + 4 + 4 + 1
        particle_int_channels = 1
        particle_buffer_bytes = (
            particle_count * particle_float_channels * bytes_per_value
            + particle_count * particle_int_channels * 4
        )

        # Current v0.1B fields:
        # curvature, Higgs, temperature, probability, lambda
        field_count = 5
        field_buffer_bytes = field_cells * field_count * bytes_per_value

        total_estimated_bytes = int(particle_buffer_bytes + field_buffer_bytes)
        estimated_with_margin_bytes = int(total_estimated_bytes * (1.0 + safety_margin))

        available_device_bytes = self.compute.available_device_memory_bytes()
        fits_available_memory: bool | None
        warnings: list[str] = []

        if available_device_bytes is None:
            fits_available_memory = None
            warnings.append("Backend did not report available device memory.")
        else:
            fits_available_memory = estimated_with_margin_bytes <= available_device_bytes
            if not fits_available_memory:
                warnings.append(
                    "Estimated allocation plus safety margin exceeds reported available memory."
                )

        if not self.compute.backend_report.is_gpu:
            warnings.append("Active backend is not GPU-backed.")
            if self.profile.strict_gpu:
                warnings.append("Strict GPU profile is active but backend is not GPU-backed.")

        report = GPUPreflightReport(
            profile_name=self.profile.name,
            backend_name=self.compute.backend_report.backend_name,
            device_name=self.compute.backend_report.device_name,
            is_gpu=bool(self.compute.backend_report.is_gpu),
            particle_count=particle_count,
            field_resolution=[int(nx), int(ny), int(nz)],
            precision=self.profile.precision,
            bytes_per_value=bytes_per_value,
            particle_buffer_bytes=int(particle_buffer_bytes),
            field_buffer_bytes=int(field_buffer_bytes),
            total_estimated_bytes=total_estimated_bytes,
            total_estimated_mb=total_estimated_bytes / (1024 ** 2),
            total_estimated_gb=total_estimated_bytes / (1024 ** 3),
            safety_margin=safety_margin,
            estimated_with_margin_bytes=estimated_with_margin_bytes,
            estimated_with_margin_mb=estimated_with_margin_bytes / (1024 ** 2),
            estimated_with_margin_gb=estimated_with_margin_bytes / (1024 ** 3),
            available_device_bytes=available_device_bytes,
            available_device_mb=None if available_device_bytes is None else available_device_bytes / (1024 ** 2),
            available_device_gb=None if available_device_bytes is None else available_device_bytes / (1024 ** 3),
            fits_available_memory=fits_available_memory,
            strict_gpu=bool(self.profile.strict_gpu),
            allow_cpu_fallback=bool(self.profile.allow_cpu_fallback),
            warnings=warnings,
        )

        self._log_report(report)
        return report

    def enforce(self, report: GPUPreflightReport) -> None:
        """
        Stop impossible strict runs before allocation.
        """
        if self.profile.strict_gpu and not report.is_gpu:
            raise RuntimeError(
                "Strict GPU profile requested, but no GPU backend is active. "
                "Use preview/desktop or install a GPU backend."
            )

        if report.fits_available_memory is False and self.profile.strict_gpu:
            raise RuntimeError(
                "Strict profile memory preflight failed. Estimated allocation exceeds "
                "reported available device memory."
            )

    def _bytes_per_value(self, precision: str) -> int:
        if precision in ("float64", "double"):
            return 8
        return 4

    def _log_report(self, report: GPUPreflightReport) -> None:
        self.diagnostics.info("GPU/memory preflight report:")
        self.diagnostics.info(f"  backend: {report.backend_name}")
        self.diagnostics.info(f"  device: {report.device_name}")
        self.diagnostics.info(f"  is_gpu: {report.is_gpu}")
        self.diagnostics.info(f"  particle_count: {report.particle_count}")
        self.diagnostics.info(f"  field_resolution: {report.field_resolution}")
        self.diagnostics.info(f"  estimated core buffers: {report.total_estimated_mb:.2f} MB")
        self.diagnostics.info(
            f"  estimated with safety margin: {report.estimated_with_margin_mb:.2f} MB"
        )
        if report.available_device_mb is not None:
            self.diagnostics.info(f"  reported available memory: {report.available_device_mb:.2f} MB")
            self.diagnostics.info(f"  fits available memory: {report.fits_available_memory}")
        for warning in report.warnings:
            self.diagnostics.warn(f"  preflight warning: {warning}")
