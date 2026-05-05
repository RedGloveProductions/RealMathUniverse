"""
RealMathUniverse v1.1B
Calibrated Dataset Driver

Loads the merged crab/navigation CSV, computes source ranges, applies calibration
mappings, and writes a compact dataset_state.json for the rest of the engine.

This module is intentionally tolerant:
    - missing CSV -> default fallback state
    - unknown column names -> uses candidates and derived density when possible
    - invalid numeric values -> skipped for stats/sampling
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple
import csv
import json
import math
import random
import time

from src.calibration.calibration_registry import CalibrationRegistry, compute_source_stats
from src.calibration.calibration_report_writer_v1_1A import write_calibration_report


DEFAULT_STATE = {
    "curvature_density": 0.15,
    "temperature_proxy": 0.25,
    "higgs_lambda": 0.35,
    "probability_weight": 0.50,
    "x": 0.0,
    "y": 0.0,
    "z": 0.0,
    "t": 0.0,
}


class CalibratedDatasetDriver:
    def __init__(self, project_root: Path):
        self.project_root = Path(project_root)
        self.config_path = self.project_root / "config" / "dataset_mode_config.json"
        self.calibration_path = self.project_root / "config" / "calibration_maps.json"
        self.config = self._load_json(self.config_path, {})
        self.source_csv = self.project_root / self.config.get("source_csv", "data/raw/merged_navdata.csv")
        self.output_state_file = self.project_root / self.config.get("output_state_file", "output/dataset_state.json")
        self.report_dir = self.project_root / self.config.get("report_dir", "output/calibration_reports")
        self.rows: List[Dict[str, str]] = []
        self.columns: List[str] = []
        self.registry = CalibrationRegistry(self.calibration_path)
        self.column_for_mapping: Dict[str, str] = {}
        self.loaded = False
        self.fallback_reason = "not_loaded"
        self._sample_index = 0

    @staticmethod
    def _load_json(path: Path, default: Dict[str, Any]) -> Dict[str, Any]:
        try:
            if path.exists():
                with path.open("r", encoding="utf-8") as f:
                    return json.load(f)
        except Exception:
            return dict(default)
        return dict(default)

    @staticmethod
    def _safe_float(value: Any) -> Optional[float]:
        if value is None:
            return None
        try:
            out = float(str(value).strip())
        except Exception:
            return None
        return out if math.isfinite(out) else None

    def load(self) -> bool:
        if not self.source_csv.exists():
            self.loaded = False
            self.fallback_reason = f"missing_csv:{self.source_csv}"
            return False

        try:
            with self.source_csv.open("r", encoding="utf-8-sig", newline="") as f:
                reader = csv.DictReader(f)
                self.columns = list(reader.fieldnames or [])
                self.rows = [row for row in reader]
        except Exception as exc:
            self.loaded = False
            self.fallback_reason = f"csv_read_error:{exc}"
            return False

        if not self.rows or not self.columns:
            self.loaded = False
            self.fallback_reason = "empty_csv_or_no_headers"
            return False

        self._derive_density_if_needed()
        self.columns = list(self.rows[0].keys())
        self._register_mapping_columns_and_stats()
        self.loaded = True
        self.fallback_reason = "none"
        return True

    def _derive_density_if_needed(self) -> None:
        # If a density column is already present, do nothing.
        lower_columns = {self._normalize_column_name(c) for c in self.columns}
        if {"trackdensity", "density", "clusterdensity", "pointdensity"} & lower_columns:
            return

        lat_col = self._find_first_column(["Latitude", "latitude", "lat", "Lat", "LAT", "z", "Z"])
        lon_col = self._find_first_column(["Longitude", "longitude", "lon", "Lon", "LON", "lng", "Lng", "LNG", "x", "X"])
        if not lat_col or not lon_col:
            return

        lat_values = [self._safe_float(r.get(lat_col)) for r in self.rows]
        lon_values = [self._safe_float(r.get(lon_col)) for r in self.rows]
        clean_pairs = [(lat, lon) for lat, lon in zip(lat_values, lon_values) if lat is not None and lon is not None]
        if not clean_pairs:
            return

        lats = [p[0] for p in clean_pairs]
        lons = [p[1] for p in clean_pairs]
        lat_min, lat_max = min(lats), max(lats)
        lon_min, lon_max = min(lons), max(lons)
        grid_size = 64

        def cell_for(lat: float, lon: float) -> Tuple[int, int]:
            if math.isclose(lat_min, lat_max):
                iy = grid_size // 2
            else:
                iy = int((lat - lat_min) / (lat_max - lat_min) * (grid_size - 1))
            if math.isclose(lon_min, lon_max):
                ix = grid_size // 2
            else:
                ix = int((lon - lon_min) / (lon_max - lon_min) * (grid_size - 1))
            return max(0, min(grid_size - 1, ix)), max(0, min(grid_size - 1, iy))

        counts: Dict[Tuple[int, int], int] = {}
        row_cells: List[Optional[Tuple[int, int]]] = []
        for row in self.rows:
            lat = self._safe_float(row.get(lat_col))
            lon = self._safe_float(row.get(lon_col))
            if lat is None or lon is None:
                row_cells.append(None)
                continue
            cell = cell_for(lat, lon)
            row_cells.append(cell)
            counts[cell] = counts.get(cell, 0) + 1

        for row, cell in zip(self.rows, row_cells):
            row["track_density"] = str(counts.get(cell, 0) if cell is not None else 0)

    def _normalize_column_name(self, name: Any) -> str:
        text = str(name or "").strip().casefold()
        return "".join(ch for ch in text if ch.isalnum())

    def _find_first_column(self, candidates: Sequence[str]) -> Optional[str]:
        lower_to_actual = {str(c).strip().casefold(): c for c in self.columns}
        normalized_to_actual = {self._normalize_column_name(c): c for c in self.columns}
        for candidate in candidates:
            key = str(candidate).strip().casefold()
            if key in lower_to_actual:
                return lower_to_actual[key]
            norm_key = self._normalize_column_name(candidate)
            if norm_key in normalized_to_actual:
                return normalized_to_actual[norm_key]
        return None

    def _register_mapping_columns_and_stats(self) -> None:
        self.column_for_mapping.clear()
        for mapping in self.registry.mappings:
            source_col = self.registry.choose_source_column(mapping, self.columns)
            if not source_col:
                continue
            values = [row.get(source_col) for row in self.rows]
            try:
                self.registry.set_source_stats(source_col, values)
                self.column_for_mapping[str(mapping.get("mapping_name"))] = source_col
            except ValueError:
                continue

    def _row_for_time(self) -> Dict[str, str]:
        if not self.rows:
            return {}
        row = self.rows[self._sample_index % len(self.rows)]
        self._sample_index += 1
        return row

    def build_state(self, enabled: bool = True) -> Dict[str, Any]:
        if not enabled:
            return self.fallback_state("disabled_by_control")

        if not self.loaded:
            loaded_now = self.load()
            if not loaded_now:
                return self.fallback_state(self.fallback_reason)

        row = self._row_for_time()
        mapped: Dict[str, float] = {}
        mapping_results: List[Dict[str, Any]] = []

        for mapping in self.registry.mappings:
            name = str(mapping.get("mapping_name", "unnamed_mapping"))
            source_col = self.column_for_mapping.get(name)
            if not source_col:
                continue
            try:
                result = self.registry.map_value(mapping, source_col, row.get(source_col))
            except Exception:
                continue
            target = result.target_variable
            mapped[target] = result.mapped_value
            mapping_results.append(result.to_dict())

        state = dict(DEFAULT_STATE)
        state.update({
            "x": mapped.get("x_coordinate", DEFAULT_STATE["x"]),
            "y": mapped.get("y_coordinate", DEFAULT_STATE["y"]),
            "z": mapped.get("z_coordinate", DEFAULT_STATE["z"]),
            "temperature_proxy": mapped.get("temperature_field", DEFAULT_STATE["temperature_proxy"]),
            "curvature_density": mapped.get("curvature_density", DEFAULT_STATE["curvature_density"]),
            "higgs_lambda": mapped.get("higgs_lambda_field", DEFAULT_STATE["higgs_lambda"]),
            "probability_weight": mapped.get("probability_weight", DEFAULT_STATE["probability_weight"]),
            "t": float(self._sample_index),
        })

        return {
            "version": "1.1B",
            "timestamp_unix": time.time(),
            "enabled": True,
            "loaded": True,
            "mode": "crab_nav_csv",
            "fallback_active": False,
            "fallback_reason": "none",
            "source_csv": str(self.source_csv),
            "row_count": len(self.rows),
            "sample_index": self._sample_index,
            "state": state,
            "mapping_results": mapping_results,
            "registry": self.registry.describe(),
        }

    def fallback_state(self, reason: str) -> Dict[str, Any]:
        fallback_defaults = dict(DEFAULT_STATE)
        fallback_defaults.update(self.config.get("fallback_defaults", {}))
        return {
            "version": "1.1B",
            "timestamp_unix": time.time(),
            "enabled": False,
            "loaded": False,
            "mode": self.config.get("fallback_mode", "default_synthetic"),
            "fallback_active": True,
            "fallback_reason": reason,
            "source_csv": str(self.source_csv),
            "row_count": 0,
            "sample_index": 0,
            "state": fallback_defaults,
            "mapping_results": [],
            "registry": self.registry.describe(),
        }

    def write_state(self, state: Dict[str, Any]) -> None:
        self.output_state_file.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.output_state_file.with_suffix(self.output_state_file.suffix + ".tmp")
        with tmp.open("w", encoding="utf-8") as f:
            json.dump(state, f, indent=2, sort_keys=True)
        tmp.replace(self.output_state_file)

    def write_report(self) -> Optional[Path]:
        if not self.loaded:
            return None
        report = {
            "version": "1.1B",
            "source_csv": str(self.source_csv),
            "row_count": len(self.rows),
            "columns": self.columns,
            "column_for_mapping": self.column_for_mapping,
            "registry": self.registry.describe(),
        }
        return write_calibration_report(self.report_dir, report, prefix="v1_1B_calibration")
