"""
Calibration report writer placeholder.
"""

from __future__ import annotations

import json
from pathlib import Path


class CalibrationReportWriter:
    def __init__(self, output_dir: Path):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def write(self, report: dict, filename: str = "calibration_report.json") -> Path:
        path = self.output_dir / filename
        with path.open("w", encoding="utf-8") as f:
            json.dump(report, f, indent=2)
        return path
