"""
RealMathUniverse v1.1A
Calibration Report Writer
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict
from datetime import datetime, timezone
import json


def utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_UTC")


def write_calibration_report(report_dir: Path, report: Dict[str, Any], prefix: str = "dataset_calibration") -> Path:
    report_dir = Path(report_dir)
    report_dir.mkdir(parents=True, exist_ok=True)
    path = report_dir / f"{prefix}_{utc_stamp()}.json"
    with path.open("w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, sort_keys=True)
    return path
