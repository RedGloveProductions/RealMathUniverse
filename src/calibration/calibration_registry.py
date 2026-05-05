"""
RealMathUniverse v1.1B
Calibration Registry + Mapping Functions

Purpose:
    Convert real dataset values into declared simulation/physics proxy values.
    This prevents raw dataset numbers from being thrown directly into fields.

No third-party dependencies are required.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple
import json
import math
import statistics


Number = float


@dataclass
class SourceStats:
    count: int
    minimum: Number
    maximum: Number
    mean: Number
    median: Number
    p01: Number
    p05: Number
    p95: Number
    p99: Number

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class MappingResult:
    mapping_name: str
    source_column: str
    source_value: Number
    target_variable: str
    mapped_value: Number
    mapping_function: str
    clamped: bool
    confidence: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def _safe_float(value: Any) -> Optional[Number]:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        if math.isfinite(float(value)):
            return float(value)
        return None
    text = str(value).strip()
    if not text:
        return None
    try:
        out = float(text)
    except ValueError:
        return None
    return out if math.isfinite(out) else None


def percentile(sorted_values: Sequence[Number], percent: Number) -> Number:
    """Return percentile using linear interpolation."""
    if not sorted_values:
        raise ValueError("Cannot compute percentile of empty values.")
    if len(sorted_values) == 1:
        return float(sorted_values[0])
    p = max(0.0, min(100.0, float(percent)))
    index = (len(sorted_values) - 1) * (p / 100.0)
    lower = math.floor(index)
    upper = math.ceil(index)
    if lower == upper:
        return float(sorted_values[int(index)])
    weight = index - lower
    return float(sorted_values[lower] * (1.0 - weight) + sorted_values[upper] * weight)


def compute_source_stats(values: Iterable[Any]) -> SourceStats:
    numeric = [_safe_float(v) for v in values]
    clean = sorted(v for v in numeric if v is not None)
    if not clean:
        raise ValueError("No numeric values available for source stats.")
    return SourceStats(
        count=len(clean),
        minimum=float(clean[0]),
        maximum=float(clean[-1]),
        mean=float(statistics.fmean(clean)),
        median=float(statistics.median(clean)),
        p01=percentile(clean, 1),
        p05=percentile(clean, 5),
        p95=percentile(clean, 95),
        p99=percentile(clean, 99),
    )


def clamp(value: Number, low: Number, high: Number) -> Number:
    return max(low, min(high, value))


def linear_remap(value: Number, source_min: Number, source_max: Number, target_min: Number, target_max: Number) -> Number:
    if math.isclose(source_min, source_max):
        return (target_min + target_max) / 2.0
    return target_min + (value - source_min) * (target_max - target_min) / (source_max - source_min)


def sigmoid_remap(value: Number, source_min: Number, source_max: Number, target_min: Number, target_max: Number, k: Number = 8.0) -> Number:
    if math.isclose(source_min, source_max):
        return (target_min + target_max) / 2.0
    center = (source_min + source_max) / 2.0
    scale = max(abs(source_max - source_min), 1e-12)
    normalized = (value - center) / scale
    sig = 1.0 / (1.0 + math.exp(-k * normalized))
    return target_min + sig * (target_max - target_min)


def log_remap(value: Number, source_min: Number, source_max: Number, target_min: Number, target_max: Number, eps: Number = 1e-9) -> Number:
    safe_value = max(value, 0.0) + eps
    safe_min = max(source_min, 0.0) + eps
    safe_max = max(source_max, 0.0) + eps
    return linear_remap(math.log(safe_value), math.log(safe_min), math.log(safe_max), target_min, target_max)


def normalize_column_name(name: Any) -> str:
    """Normalize headers for alias matching: casefold and remove punctuation/spacing."""
    text = str(name or "").strip().casefold()
    return "".join(ch for ch in text if ch.isalnum())


class CalibrationRegistry:
    def __init__(self, mapping_config_path: Path):
        self.mapping_config_path = Path(mapping_config_path)
        self.mapping_config = self._load_json(self.mapping_config_path)
        self.mappings: List[Dict[str, Any]] = list(self.mapping_config.get("mappings", []))
        self.source_stats: Dict[str, SourceStats] = {}

    @staticmethod
    def _load_json(path: Path) -> Dict[str, Any]:
        if not path.exists():
            return {"version": "1.1B", "mappings": []}
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)

    def get_mapping(self, mapping_name: str) -> Optional[Dict[str, Any]]:
        for mapping in self.mappings:
            if mapping.get("mapping_name") == mapping_name:
                return mapping
        return None

    def choose_source_column(self, mapping: Dict[str, Any], available_columns: Sequence[str]) -> Optional[str]:
        # v1.1B: forgiving alias matching. This handles Depth, depth, DEPTH,
        # Elevation, water depth, track_density, TrackDensity, etc.
        available_lower = {str(c).strip().casefold(): c for c in available_columns}
        available_normalized = {normalize_column_name(c): c for c in available_columns}

        candidates = list(mapping.get("source_column_candidates", []))
        exact = mapping.get("source_column")
        if exact:
            candidates.append(exact)

        for candidate in candidates:
            raw_key = str(candidate).strip().casefold()
            if raw_key in available_lower:
                return available_lower[raw_key]
            norm_key = normalize_column_name(candidate)
            if norm_key in available_normalized:
                return available_normalized[norm_key]
        return None

    def set_source_stats(self, source_column: str, values: Iterable[Any]) -> SourceStats:
        stats = compute_source_stats(values)
        self.source_stats[source_column] = stats
        return stats

    def map_value(self, mapping: Dict[str, Any], source_column: str, source_value: Any) -> MappingResult:
        value = _safe_float(source_value)
        if value is None:
            raise ValueError(f"Source value for {source_column!r} is not numeric: {source_value!r}")

        stats = self.source_stats.get(source_column)
        if stats is None:
            raise ValueError(f"No source stats have been registered for {source_column!r}")

        target_range = mapping.get("target_reference_range", [0.0, 1.0])
        target_min = float(target_range[0])
        target_max = float(target_range[1])

        range_method = str(mapping.get("source_range_method", "observed_min_max"))
        if range_method == "percentile_1_to_99":
            source_min, source_max = stats.p01, stats.p99
        elif range_method == "percentile_5_to_95":
            source_min, source_max = stats.p05, stats.p95
        else:
            source_min, source_max = stats.minimum, stats.maximum

        fn = str(mapping.get("mapping_function", "linear"))
        if fn in {"linear", "percentile_linear"}:
            mapped = linear_remap(value, source_min, source_max, target_min, target_max)
        elif fn == "log":
            mapped = log_remap(value, source_min, source_max, target_min, target_max)
        elif fn == "sigmoid":
            mapped = sigmoid_remap(value, source_min, source_max, target_min, target_max)
        else:
            raise ValueError(f"Unsupported mapping_function: {fn}")

        did_clamp = bool(mapping.get("clamp", True))
        if did_clamp:
            low, high = sorted((target_min, target_max))
            mapped = clamp(mapped, low, high)

        return MappingResult(
            mapping_name=str(mapping.get("mapping_name", "unnamed_mapping")),
            source_column=source_column,
            source_value=value,
            target_variable=str(mapping.get("target_physics_variable", "unknown_target")),
            mapped_value=float(mapped),
            mapping_function=fn,
            clamped=did_clamp,
            confidence=str(mapping.get("confidence", "experimental")),
        )

    def describe(self) -> Dict[str, Any]:
        return {
            "mapping_config_path": str(self.mapping_config_path),
            "mapping_count": len(self.mappings),
            "mappings": [m.get("mapping_name", "unnamed_mapping") for m in self.mappings],
            "source_stats": {k: v.to_dict() for k, v in self.source_stats.items()},
        }
