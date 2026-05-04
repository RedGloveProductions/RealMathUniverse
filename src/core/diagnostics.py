"""
Diagnostics and run logging.

This is intentionally simple for v0.1. Later it can become structured logging,
JSONL events, profiler hooks, and frame timing.
"""

from __future__ import annotations

import datetime as _dt
import traceback
from pathlib import Path


class Diagnostics:
    def __init__(self, project_root: Path):
        self.project_root = Path(project_root)
        self.log_dir = self.project_root / "output" / "logs"
        self.log_dir.mkdir(parents=True, exist_ok=True)
        stamp = _dt.datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        self.log_path = self.log_dir / f"run_{stamp}_utc.log"

    def _write(self, level: str, message: str) -> None:
        stamp = _dt.datetime.utcnow().isoformat(timespec="seconds") + "Z"
        line = f"[{stamp}] [{level}] {message}"
        print(line)
        with self.log_path.open("a", encoding="utf-8") as f:
            f.write(line + "\n")

    def info(self, message: str) -> None:
        self._write("INFO", message)

    def warn(self, message: str) -> None:
        self._write("WARN", message)

    def error(self, message: str) -> None:
        self._write("ERROR", message)

    def write_crash_report(self, exc: Exception) -> Path:
        crash_path = self.log_dir / "last_crash_report.txt"
        with crash_path.open("w", encoding="utf-8") as f:
            f.write("RealMathUniverse crash report\n")
            f.write("=" * 80 + "\n")
            f.write(str(exc) + "\n\n")
            f.write(traceback.format_exc())
        self.error(f"Crash report written: {crash_path}")
        return crash_path
