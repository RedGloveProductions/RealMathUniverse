"""
$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$
RealMathUniverse Benchmark Comparison Writer
Version: 0.2C

Purpose:
    Build a single comparison report from multiple run_summary JSON files.

Product:
    A JSON report showing profile, backend, GPU status, particles, field size,
    memory estimates, warmup timing, measured timing, estimated sim-only FPS,
    physics diagnostics, and pass/fail status for each profile run.
$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$
"""

from __future__ import annotations

import datetime as _dt
import json
from pathlib import Path
from typing import Any


class BenchmarkComparisonWriter:
    def __init__(self, project_root: Path):
        self.project_root = Path(project_root)
        self.output_dir = self.project_root / "output" / "run_summaries"
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def write(self, comparison_name: str, run_records: list[dict[str, Any]]) -> Path:
        stamp = _dt.datetime.utcnow().strftime("%Y%m%d_%H%M%S_UTC")
        safe_name = self._safe_token(comparison_name)

        filename = (
            f"RealMathUniverse_v0_2C_{safe_name}_"
            f"{stamp}_benchmark_comparison.json"
        )
        path = self.output_dir / filename

        report = {
            "project": "RealMathUniverse",
            "version": "0.2C",
            "report_type": "benchmark_comparison",
            "timestamp_utc": _dt.datetime.utcnow().isoformat(timespec="seconds") + "Z",
            "comparison_name": comparison_name,
            "records": run_records,
            "summary_table": [self._make_table_row(record) for record in run_records],
            "notes": [
                "FPS is simulation-loop only, not rendered visual FPS.",
                "MPS memory availability is not directly reported by PyTorch, so memory fit may be null on Mac.",
                "Warmup frames are excluded from measured frame timing."
            ]
        }

        with path.open("w", encoding="utf-8") as f:
            json.dump(report, f, indent=2)

        latest = self.output_dir / "LATEST_BENCHMARK_COMPARISON.json"
        with latest.open("w", encoding="utf-8") as f:
            json.dump(report, f, indent=2)

        return path

    def build_record_from_summary(self, profile: str, command: list[str], return_code: int, summary_path: Path | None, stdout_path: Path, stderr_path: Path) -> dict[str, Any]:
        base = {
            "profile_requested": profile,
            "return_code": int(return_code),
            "command": command,
            "summary_path": str(summary_path) if summary_path else None,
            "stdout_log": str(stdout_path),
            "stderr_log": str(stderr_path),
            "status": "passed" if return_code == 0 and summary_path else "failed",
        }

        if not summary_path or not summary_path.exists():
            base["error"] = "No run summary found for this profile."
            return base

        with summary_path.open("r", encoding="utf-8") as f:
            summary = json.load(f)

        profile_data = summary.get("profile", {})
        backend = summary.get("compute_backend", {})
        preflight = summary.get("gpu_preflight", {})
        buffers = summary.get("buffers", {})
        engine_diag = summary.get("engine_diagnostics", {})
        measured = engine_diag.get("measured_frame_timing", {})
        warmup = engine_diag.get("warmup", {})
        physics = engine_diag.get("last_physics_diagnostics", {})

        base.update({
            "summary_version": summary.get("version"),
            "timestamp_utc": summary.get("timestamp_utc"),
            "profile": profile_data.get("name"),
            "backend_name": backend.get("backend_name"),
            "device_name": backend.get("device_name"),
            "is_gpu": backend.get("is_gpu"),
            "particle_count": profile_data.get("particle_count"),
            "field_resolution": profile_data.get("field_resolution"),
            "precision": profile_data.get("precision"),
            "total_estimated_mb": buffers.get("total_estimated_mb"),
            "estimated_with_margin_mb": preflight.get("estimated_with_margin_mb"),
            "warmup_frames": warmup.get("frame_count"),
            "warmup_average_ms": warmup.get("average_frame_ms"),
            "measured_frames": measured.get("frame_count"),
            "measured_average_ms": measured.get("average_frame_ms"),
            "measured_min_ms": measured.get("min_frame_ms"),
            "measured_max_ms": measured.get("max_frame_ms"),
            "estimated_simulation_fps": measured.get("estimated_fps_from_average"),
            "speed_mean": physics.get("speed_mean"),
            "speed_max": physics.get("speed_max"),
            "force_mean": physics.get("force_mean"),
            "force_max": physics.get("force_max"),
            "elapsed_seconds": summary.get("elapsed_seconds"),
        })
        return base

    def _make_table_row(self, record: dict[str, Any]) -> dict[str, Any]:
        return {
            "profile": record.get("profile_requested"),
            "status": record.get("status"),
            "backend": record.get("backend_name"),
            "is_gpu": record.get("is_gpu"),
            "particles": record.get("particle_count"),
            "field_resolution": record.get("field_resolution"),
            "memory_mb": record.get("total_estimated_mb"),
            "measured_avg_ms": record.get("measured_average_ms"),
            "estimated_sim_fps": record.get("estimated_simulation_fps"),
            "speed_mean": record.get("speed_mean"),
            "force_mean": record.get("force_mean"),
        }

    def _safe_token(self, value: str) -> str:
        keep = []
        for ch in str(value):
            if ch.isalnum() or ch in ("_", "-"):
                keep.append(ch)
            elif ch.isspace():
                keep.append("_")
        token = "".join(keep).strip("_")
        return token or "comparison"
