"""
Physics Calibration Oracle v0.1.

The oracle answers one mapping question at a time:
    raw dataset value -> source distribution -> physics reference/range -> mapped value

v0.1 implements linear mapping and emits a report dictionary.
"""

from __future__ import annotations

import datetime as _dt


class PhysicsCalibrationOracle:
    def __init__(self, calibration_config: dict):
        self.calibration_config = calibration_config

    def linear_map(
        self,
        raw_value: float,
        source_range: tuple[float, float],
        target_range: tuple[float, float],
    ) -> float:
        source_min, source_max = source_range
        target_min, target_max = target_range
        if source_max == source_min:
            return (target_min + target_max) / 2.0
        t = (raw_value - source_min) / (source_max - source_min)
        t = max(0.0, min(1.0, t))
        return target_min + t * (target_max - target_min)

    def map_value(self, mapping_name: str, raw_value: float) -> dict:
        mappings = self.calibration_config.get("mappings", {})
        if mapping_name not in mappings:
            raise KeyError(f"Unknown calibration mapping: {mapping_name}")

        mapping = mappings[mapping_name]
        source_range = tuple(float(v) for v in mapping["source_range"])
        target_range = tuple(float(v) for v in mapping["target_range"])
        mapped_value = self.linear_map(raw_value, source_range, target_range)

        return {
            "parameter_name": mapping["target_physics_variable"],
            "mapping_name": mapping_name,
            "equation_name": mapping.get("equation_name", "not_declared"),
            "raw_value": float(raw_value),
            "source_dataset": mapping["source_dataset"],
            "source_column": mapping["source_column"],
            "source_units": mapping["source_units"],
            "source_range": list(source_range),
            "target_range": list(target_range),
            "mapping_function": mapping["mapping_function"],
            "mapped_value": mapped_value,
            "confidence": mapping["confidence"],
            "rationale": mapping["rationale"],
            "timestamp_utc": _dt.datetime.utcnow().isoformat(timespec="seconds") + "Z",
        }
