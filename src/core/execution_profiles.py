"""
Execution profile system.

A profile changes fidelity, strictness, GPU expectations, particle count,
field resolution, logging, and solver requirements without changing code.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ExecutionProfile:
    name: str
    compute_backend: str
    prefer_gpu: bool
    strict_gpu: bool
    allow_cpu_fallback: bool
    strict_physics_mode: bool
    particle_count: int
    field_resolution: tuple[int, int, int]
    precision: str
    solver_fidelity: str
    logging_level: str
    require_preflight_confirmation: bool


class ExecutionProfiles:
    def __init__(self, raw_config: dict[str, Any]):
        self.raw_config = raw_config
        self.profiles = raw_config.get("profiles", {})

    def resolve(self, profile_name: str) -> ExecutionProfile:
        if profile_name not in self.profiles:
            available = ", ".join(sorted(self.profiles.keys()))
            raise ValueError(f"Unknown profile '{profile_name}'. Available: {available}")

        raw = self.profiles[profile_name]
        return ExecutionProfile(
            name=profile_name,
            compute_backend=raw["compute_backend"],
            prefer_gpu=bool(raw["prefer_gpu"]),
            strict_gpu=bool(raw["strict_gpu"]),
            allow_cpu_fallback=bool(raw["allow_cpu_fallback"]),
            strict_physics_mode=bool(raw["strict_physics_mode"]),
            particle_count=int(raw["particle_count"]),
            field_resolution=tuple(int(v) for v in raw["field_resolution"]),
            precision=str(raw["precision"]),
            solver_fidelity=str(raw["solver_fidelity"]),
            logging_level=str(raw["logging_level"]),
            require_preflight_confirmation=bool(raw.get("require_preflight_confirmation", False)),
        )
