"""
Run summary writer.

v0.5A naming:
    RealMathUniverse_v0_5A_<profile>_<backend>_<GPU_or_CPU>_<YYYYMMDD_HHMMSS_UTC>_run_summary.json
"""

from __future__ import annotations

import datetime as _dt
import json
import re
from pathlib import Path
from dataclasses import asdict, is_dataclass


class RunSummaryWriter:
    def __init__(self, project_root: Path, diagnostics):
        self.project_root = Path(project_root)
        self.diagnostics = diagnostics
        self.summary_dir = self.project_root / "output" / "run_summaries"
        self.summary_dir.mkdir(parents=True, exist_ok=True)

    def write_summary(
        self,
        args,
        configs,
        profile,
        compute_report,
        preflight_report,
        buffers,
        solvers,
        modules,
        elapsed_seconds: float,
        engine_diagnostics: dict | None = None,
    ) -> Path:
        stamp = _dt.datetime.utcnow().strftime("%Y%m%d_%H%M%S_UTC")

        compute_plain = self._to_plain(compute_report)
        preflight_plain = self._to_plain(preflight_report)

        backend_name = self._safe_token(compute_plain.get("backend_name", "unknown"))
        profile_name = self._safe_token(getattr(profile, "name", str(args.profile)))
        gpu_tag = "GPU" if bool(compute_plain.get("is_gpu", False)) else "CPU"

        version_tag = "v0_5A"
        filename = (
            f"RealMathUniverse_{version_tag}_"
            f"{profile_name}_{backend_name}_{gpu_tag}_"
            f"{stamp}_run_summary.json"
        )

        path = self.summary_dir / filename

        summary = {
            "project": "RealMathUniverse",
            "version": "0.5A",
            "timestamp_utc": _dt.datetime.utcnow().isoformat(timespec="seconds") + "Z",
            "cli": {
                "profile": args.profile,
                "headless": bool(args.headless),
                "frames": int(args.frames),
                "continuous_until_ctrl_c": int(args.frames) == 0,
                "warmup_frames": int(getattr(args, "warmup_frames", 0)),
                "status_every": int(getattr(args, "status_every", 300)),
                "config_dir": str(args.config_dir),
            },
            "profile": asdict(profile) if is_dataclass(profile) else str(profile),
            "compute_backend": self._to_plain(compute_report),
            "gpu_preflight": self._to_plain(preflight_report),
            "buffers": buffers,
            "solvers": solvers,
            "modules": modules,
            "particle_config": configs.get("particle_config", {}),
            "relativity_config": configs.get("relativity_config", {}),
            "render_config": configs.get("render_config", {}),
            "engine_diagnostics": engine_diagnostics or {},
            "elapsed_seconds": elapsed_seconds,
            "config_files_loaded": sorted(configs.keys()),
        }

        with path.open("w", encoding="utf-8") as f:
            json.dump(summary, f, indent=2)

        latest_path = self.summary_dir / "LATEST_RUN_SUMMARY.json"
        with latest_path.open("w", encoding="utf-8") as f:
            json.dump(summary, f, indent=2)

        self.diagnostics.info(f"Latest summary alias written: {latest_path}")
        return path

    def _to_plain(self, obj):
        if obj is None:
            return None
        if hasattr(obj, "to_dict"):
            return obj.to_dict()
        if is_dataclass(obj):
            return asdict(obj)
        return obj

    def _safe_token(self, value: str) -> str:
        value = str(value).strip()
        value = value.replace(" ", "_")
        value = value.replace("-", "_")
        value = re.sub(r"[^A-Za-z0-9_]+", "", value)
        value = re.sub(r"_+", "_", value)
        return value or "unknown"
